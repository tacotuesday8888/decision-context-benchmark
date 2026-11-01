"""Bounded v7 accounting I/O cache; the durable journal format is unchanged.

Integration is explicit: put this mixin before the existing ledger parent, call
``verify_full_journal`` before whole-group admission, and use
``verify_historical_file`` for fixed historical hashes. Snapshot/restart always
perform a full prefix validation. The existing OS ledger lock and the executor
process lock remain authoritative; no provider/cap/schedule policy is changed.

Assumptions: ordinary local filesystem stat semantics (ctime cannot be restored
by an unprivileged writer), cooperative writers use the existing flock, and one
executor dispatches. This is an I/O cache, not protection against a privileged
attacker controlling both process memory and filesystem metadata. Unexpected
changes still require full retained-prefix verification; file replacement,
shrinkage, corrupt/torn tails and historical hash changes fail closed.
"""
from __future__ import annotations
import hashlib
import json
import os
from pathlib import Path

from scripts.study_v6.accounting import AccountingError, ZERO_HASH, canonical, digest


def fingerprint(path):
    s = Path(path).stat()
    return (s.st_dev, s.st_ino, s.st_size, s.st_mtime_ns, s.st_ctime_ns)


def _event(line, index, previous):
    try:
        value = json.loads(line)
        sha = value.pop('sha256')
        if (sha != digest(canonical(value)) or value['index'] != index or
                value['previous_sha256'] != previous):
            raise AccountingError('Journal hash, prefix chain or sequence changed')
        return value, sha
    except (ValueError, UnicodeDecodeError, KeyError, TypeError):
        raise AccountingError('Unreadable journal event') from None


class V7LedgerCacheMixin:
    """Reuse event application and locks; avoid rereading an unchanged journal."""
    def _invalidate_journal_cache(self):
        self._v7_journal_cache = None
        self._v7_journal_failed = True

    def _read(self, *, force_full=False):
        if getattr(self, '_v7_journal_failed', False):
            raise AccountingError('Journal cache invalidated after a failed read/apply/write; reopen for full replay')
        try:
            return self._read_cached(force_full=force_full)
        except BaseException:
            self._invalidate_journal_cache()
            raise

    def _read_cached(self, *, force_full=False):
        cache = getattr(self, '_v7_journal_cache', None)
        try:
            before = fingerprint(self.path)
        except FileNotFoundError:
            if cache is not None:
                raise AccountingError('Preserved journal was removed') from None
            return None
        if cache is not None:
            if before[:2] != cache['fingerprint'][:2]:
                raise AccountingError('Journal file identity changed')
            if before == cache['fingerprint'] and not force_full:
                return cache['state']
        body = self.path.read_bytes()
        after = fingerprint(self.path)
        if after != before or len(body) != after[2]:
            raise AccountingError('Journal changed during retained-prefix verification')
        if not body or not body.endswith(b'\n'):
            raise AccountingError('Empty or torn journal; preserve evidence')
        if cache is None:
            state, start, index, hasher = None, 0, 0, hashlib.sha256()
        else:
            start = cache['fingerprint'][2]
            if len(body) < start:
                raise AccountingError('Journal shrank; preserved accounting was removed')
            # memoryview avoids an additional potentially large prefix copy.
            if hashlib.sha256(memoryview(body)[:start]).digest() != cache['hasher'].digest():
                raise AccountingError('Retained journal prefix changed')
            state, index, hasher = cache['state'], cache['state']['events'], cache['hasher'].copy()
        tail = body[start:]
        for i, line in enumerate(tail.splitlines(), index):
            event, sha = _event(line, i, ZERO_HASH if state is None else state['head_sha256'])
            state = self._apply(state, event['kind'], event['data'])
            state['head_sha256'], state['events'] = sha, i+1
        hasher.update(tail)
        self._v7_journal_cache = {'fingerprint': after, 'hasher': hasher, 'state': state}
        return state

    def _append(self, state, kind, data):
        try:
            return self._append_cached(state, kind, data)
        except BaseException:
            self._invalidate_journal_cache()
            raise

    def _append_cached(self, state, kind, data):
        # The parent calls this while holding the unchanged ledger OS lock.
        current = self._read()
        if ((state is None) != (current is None) or
                (state is not None and (state['events'], state['head_sha256']) !=
                 (current['events'], current['head_sha256']))):
            raise AccountingError('Append does not use the current locked journal head')
        cache = getattr(self, '_v7_journal_cache', None)
        old_size = 0 if cache is None else cache['fingerprint'][2]
        value = {'index': 0 if state is None else state['events'],
            'previous_sha256': ZERO_HASH if state is None else state['head_sha256'],
            'kind': kind, 'data': data}
        value['sha256'] = digest(canonical(value))
        line = canonical(value) + b'\n'
        fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o600)
        try:
            initial = os.fstat(fd)
            if initial.st_size != old_size or (cache is not None and
                    (initial.st_dev, initial.st_ino) != cache['fingerprint'][:2]):
                raise AccountingError('Journal changed before durable append')
            if os.write(fd, line) != len(line):
                raise AccountingError('Partial journal write; preserve torn evidence')
            os.fsync(fd)
        finally:
            os.close(fd)
        directory = os.open(self.path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
        before = fingerprint(self.path)
        if before[2] != old_size + len(line):
            raise AccountingError('Unexpected file size after durable append')
        if cache is not None and before[:2] != cache['fingerprint'][:2]:
            raise AccountingError('Journal replacement during append')
        with self.path.open('rb') as stream:
            stream.seek(old_size)
            retained = stream.read()
        after = fingerprint(self.path)
        if after != before or retained != line:
            raise AccountingError('Durable appended tail differs from the exact event')
        event, sha = _event(retained, value['index'], value['previous_sha256'])
        result = self._apply(state, event['kind'], event['data'])
        result['head_sha256'], result['events'] = sha, event['index']+1
        hasher = hashlib.sha256() if cache is None else cache['hasher'].copy()
        hasher.update(retained)
        self._v7_journal_cache = {'fingerprint': after, 'hasher': hasher, 'state': result}
        return result

    def verify_full_journal(self):
        """Force full retained-prefix validation under the existing ledger lock."""
        with self._locked():
            state = self._read(force_full=True)
            return None if state is None else {'events': state['events'], 'head_sha256': state['head_sha256'],
                'journal_sha256': self._v7_journal_cache['hasher'].hexdigest()}

    def snapshot(self):
        self.verify_full_journal()
        return super().snapshot()

    def verify_historical_file(self, path, expected_sha256, *, force_full=False):
        """First/changed fixed evidence is SHA-verified; unchanged evidence is stat-bound."""
        path = Path(path)
        cache = getattr(self, '_v7_history_cache', None)
        if cache is None:
            self._v7_history_cache = cache = {}
        before = fingerprint(path)
        old = cache.get(str(path))
        if not force_full and old == (before, expected_sha256):
            return True
        actual = digest(path.read_bytes())
        after = fingerprint(path)
        if before != after or actual != expected_sha256:
            raise AccountingError('Historical spending evidence changed')
        cache[str(path)] = (after, expected_sha256)
        return True
