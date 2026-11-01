"""Sole-executor frozen core run. Importing this module never invokes inference."""
from __future__ import annotations

import argparse
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import threading
import time

from scripts.study_v7.requests import canonical, digest
from scripts.subscription_followup.budget import (FollowupLedger, freeze_policy, request_spec,
    usage_cost, BudgetExceeded, WINDOW_SECONDS)
from scripts.subscription_followup.transport import invoke, validate_payload, write_once

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = Path('/Users/langqi/Developer/Projects/Decision Context Benchmark')
VERSION = 'subscription-followup-core-executor-1'


class FileGuard:
    def __init__(self):
        self.cache = {}
        self.lock = threading.RLock()

    def check(self, path, expected):
        path = Path(path).resolve()
        with self.lock:
            stat = path.stat()
            fingerprint = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
            if self.cache.get((str(path), expected)) != fingerprint:
                if digest(path.read_bytes()) != expected:
                    raise PermissionError('Frozen bytes changed: ' + str(path))
                self.cache[(str(path), expected)] = fingerprint


class Permit:
    """Bind a reviewed roster, code, authorization and new ledger before transport."""
    def __init__(self, manifest_path, authorization_path, review_path, execution):
        self.manifest_path, self.authorization_path, self.review_path = map(Path,
            (manifest_path, authorization_path, review_path))
        self.manifest_bytes = self.manifest_path.read_bytes()
        self.manifest_sha256 = digest(self.manifest_bytes)
        self.manifest = json.loads(self.manifest_bytes)
        self.authorization = json.loads(self.authorization_path.read_text())
        self.authorization_sha256 = digest(self.authorization_path.read_bytes())
        self.review_sha256 = digest(self.review_path.read_bytes())
        self.review = json.loads(self.review_path.read_text())
        self.execution = Path(execution).resolve()
        if self.execution != (ROOT / self.manifest['execution_directory']).resolve():
            raise PermissionError('Execution directory differs from the frozen manifest')
        if not self.execution.is_relative_to(ROOT / 'data/raw/subscription-followup'):
            raise PermissionError('Only the new follow-up raw namespace may be written')
        self.guard = FileGuard()
        self.credential_root = CANONICAL
        self.plan_path = (ROOT / self.manifest['plan']['path']).resolve()
        self.guard.check(self.plan_path, self.manifest['plan']['sha256'])
        self.plan = json.loads(self.plan_path.read_text())
        self.groups = self.plan['groups']
        self.cells = {}
        self.cell_group = {}
        for group in self.groups:
            for cell in group['cells']:
                key = cell['cell_id']
                if key in self.cells:
                    raise PermissionError('Duplicate scientific cell')
                if cell['group_id'] != group['group_id'] or cell['payload_sha256'] != digest(canonical(cell['payload'])):
                    raise PermissionError('Frozen group/payload identity differs')
                validate_payload(cell['config'], cell['payload'])
                self.cells[key] = digest(canonical(cell))
                self.cell_group[key] = group
        self.ledger = None
        self.monotonic_start = None
        self.monotonic_remaining = WINDOW_SECONDS
        self.check()

    def check(self):
        self.guard.check(self.manifest_path, self.manifest_sha256)
        self.guard.check(self.authorization_path, self.authorization_sha256)
        self.guard.check(self.review_path, self.review_sha256)
        self.guard.check(self.plan_path, self.manifest['plan']['sha256'])
        for name, sha in self.manifest['frozen_files'].items():
            self.guard.check(ROOT / name, sha)
        for name, item in self.manifest['closed_evidence'].items():
            self.guard.check(item['path'], item['sha256'])
        if (self.execution / 'STOP.json').exists():
            raise PermissionError('New follow-up stop seal is present')
        r = self.authorization
        if (r.get('experimental_inference_authorized') is not True or
            r.get('authorization_source') != 'explicit_owner_instruction' or
            r.get('manifest_sha256') != self.manifest_sha256 or
            r.get('openai_subscription_only') is not True or
            r.get('allow_paid_openai_api') is not False or
            r.get('allow_purchases_or_recharge') is not False or
            r.get('window_seconds') != WINDOW_SECONDS or
            not r.get('owner_instruction') or r.get('max_general_calls') != 4410 or
            r.get('max_audit_calls') != 100):
            raise PermissionError('Explicit bounded owner authorization does not match')
        if (self.review.get('manifest_sha256') != self.manifest_sha256 or
            self.review.get('status') != 'pass' or self.review.get('remaining_findings')):
            raise PermissionError('Exact frozen contract needs a completed read-only review')
        if self.manifest.get('workers') != 4 or self.manifest.get('window_seconds') != WINDOW_SECONDS:
            raise PermissionError('Frozen concurrency/window changed')
        if self.manifest['lanes']['second_source']['enabled'] or self.manifest['lanes']['isolated_agent']['enabled']:
            raise PermissionError('This core executor cannot run another lane')
        if self.ledger is not None and self.ledger.remaining_seconds() <= 0:
            raise BudgetExceeded('Durable inference clock expired')
        if self.monotonic_start is not None and time.monotonic() - self.monotonic_start >= self.monotonic_remaining:
            raise BudgetExceeded('Monotonic inference clock expired')
        return True

    def specs(self, group):
        return [request_spec(self.policy, lane=group['lane'], group_id=group['group_id'],
            batch_id=group['group_id'], stage=group['stage'], cell_id=c['cell_id'],
            config=c['config'], payload=c['payload']) for c in group['cells']]

    def check_dispatch(self, cell, specification):
        self.check()
        if self.ledger is None or self.cells.get(cell.get('cell_id')) != digest(canonical(cell)):
            raise PermissionError('Cell is outside the reviewed frozen roster')
        group = self.cell_group[cell['cell_id']]
        expected = next(s for s in self.specs(group) if s['cell_id'] == cell['cell_id'])
        if specification != expected:
            raise PermissionError('Dispatch specification differs from frozen membership')
        for prior in self.specs(group):
            if prior['key'] == specification['key']:
                break
            entry = self.ledger.entry(prior['key'])
            if entry is None or entry['status'] not in ('settled', 'unknown_usage'):
                raise PermissionError('Within-group frozen order violated')
        entry = self.ledger.entry(specification['key'])
        if entry is None or entry['status'] != 'dispatched' or any(entry.get(k) != v for k, v in specification.items()):
            raise PermissionError('No exact durable once-only dispatch intent')


class Executor:
    def __init__(self, permit):
        self.permit = permit
        self.execution = permit.execution
        self.attempts = self.execution / 'attempts'
        self.attempts.mkdir(parents=True, exist_ok=True)
        self.lock = threading.RLock()
        self.pause = threading.Event()
        self.fatal = threading.Event()
        self.reason = None
        self.service_failures = []
        self.consecutive_service_failures = 0
        self.completed = Counter()
        self.restore()

    def event(self, kind, **fields):
        row = {'kind': kind, 'at_utc': datetime.now(timezone.utc).isoformat(), **fields}
        with self.lock:
            with (self.execution / 'runtime-events.jsonl').open('ab') as stream:
                stream.write(canonical(row) + b'\n')
                stream.flush()
                __import__('os').fsync(stream.fileno())
            if kind != 'valid_response':
                print(json.dumps(row), flush=True)

    def restore(self):
        # A new process cannot infer restart permission from completion files or
        # runtime events. In-process service continuation needs no recovery.
        # Any prior attempt requires separately reviewed offline reconciliation.
        if any(self.attempts.iterdir()):
            raise PermissionError('Prior attempts require offline reconciliation; automatic restart admission denied')
        snapshot = self.permit.ledger.snapshot()
        if snapshot['entries'] or snapshot['window_started_at_utc'] is not None:
            raise PermissionError('Retained journal requires offline reconciliation; never reset or replay')

    def observe(self, group, result):
        parsed = result['parsed']
        status = parsed['status']
        http = result['observation'].get('http_status', 0)
        with self.lock:
            self.completed[status] += 1
            if parsed.get('valid'):
                self.consecutive_service_failures = 0
                self.event('valid_response', key=result['key'], stage=group['stage'])
            elif 500 <= http <= 599:
                self.consecutive_service_failures += 1
                headers = result['observation'].get('response_headers', {})
                raw_retry = headers.get('retry-after', '120')
                try:
                    retry = max(120., float(raw_retry))
                except (ValueError, TypeError):
                    try:
                        from email.utils import parsedate_to_datetime
                        retry = max(120., (parsedate_to_datetime(raw_retry) - datetime.now(timezone.utc)).total_seconds())
                    except (ValueError, TypeError, OverflowError):
                        retry = 120.
                row = {'key': result['key'], 'http_status': http, 'retry_after_seconds': retry}
                self.service_failures.append(row)
                self.event('service_failure', **row)
                self.pause.set()
                if retry > 600 or self.consecutive_service_failures >= 3 or len(self.service_failures) > 5:
                    self.reason = ('provider_retry_interval_exceeds_bound' if retry > 600
                                   else 'bounded_service_recovery_exhausted')
                    self.fatal.set()
            else:
                self.reason = 'technical_or_access_failure:' + status
                self.event('fatal_failure', key=result['key'], status=status, http_status=http,
                           error_code=parsed.get('error_code'))
                self.fatal.set()
            total = sum(self.completed.values())
            if total % 20 == 0 or not parsed.get('valid'):
                self.event('progress', completed=total, status_counts=dict(self.completed),
                           remaining_seconds=round(self.permit.ledger.remaining_seconds(), 2))

    def group(self, group):
        if self.fatal.is_set() or self.pause.is_set():
            return
        self.permit.check()
        specifications = self.permit.specs(group)
        for cell, spec in zip(group['cells'], specifications):
            if self.fatal.is_set() or self.pause.is_set():
                return
            entry = self.permit.ledger.entry(spec['key'])
            if entry['status'] in ('settled', 'unknown_usage'):
                continue
            if entry['status'] != 'reserved':
                raise PermissionError('Preserved dispatch must never be replayed')
            with self.lock:
                if self.fatal.is_set() or self.pause.is_set():
                    return
                self.permit.check()
                self.permit.ledger.mark_dispatched(spec['key'])
                if self.permit.monotonic_start is None:
                    self.permit.monotonic_remaining = self.permit.ledger.remaining_seconds()
                    self.permit.monotonic_start = time.monotonic()
            result = invoke(cell, spec, self.attempts, permit=self.permit)
            actual = usage_cost(cell['config'], result['parsed'].get('usage'))
            if result.get('native_request_sent') is False:
                actual = '0'
            completed_path = self.attempts / spec['key'] / 'completed.json'
            self.permit.ledger.settle(spec['key'], actual, evidence_sha256=digest(completed_path.read_bytes()))
            self.observe(group, result)

    def stage(self, name, workers):
        groups = [g for g in self.permit.groups if g['stage'] == name]
        while True:
            if self.fatal.is_set():
                return
            self.pause.clear()
            with ThreadPoolExecutor(max_workers=workers) as pool:
                pending = set()
                iterator = iter(groups)
                exhausted = False
                while pending or not exhausted:
                    while len(pending) < workers and not exhausted and not self.pause.is_set() and not self.fatal.is_set():
                        group = next(iterator, None)
                        if group is None:
                            exhausted = True
                            break
                        # Central producer alone admits the frozen rank prefix.
                        with self.lock:
                            if self.pause.is_set() or self.fatal.is_set():
                                exhausted = True
                                break
                            self.permit.check()
                            self.permit.ledger.reserve_group(group['lane'], group['group_id'],
                                self.permit.specs(group), batch_id=group['group_id'])
                        pending.add(pool.submit(self.group, group))
                    if not pending:
                        break
                    done, pending = wait(pending, return_when=FIRST_COMPLETED)
                    for future in done:
                        try:
                            future.result()
                        except Exception:
                            self.fatal.set()
                            self.reason = 'worker_exception'
                            raise
                    if self.pause.is_set() or self.fatal.is_set():
                        exhausted = True
            if not self.pause.is_set() or self.fatal.is_set():
                return
            if name == 'preflight':
                self.reason = 'preflight_technical_failure'
                self.fatal.set()
                return
            delay = max(row['retry_after_seconds'] for row in self.service_failures[-workers:])
            self.event('bounded_cooldown', seconds=delay, recovery_count=len(self.service_failures))
            deadline = time.monotonic() + delay
            while time.monotonic() < deadline:
                self.permit.check()
                time.sleep(min(30., max(0., deadline - time.monotonic())))

    def close(self):
        snapshot = self.permit.ledger.snapshot()
        cancellation = self.execution / 'unsent-closeout.json'
        reserved = [key for key, e in snapshot['entries'].items() if e['status'] == 'reserved']
        if reserved:
            write_once(cancellation, {'manifest_sha256': self.permit.manifest_sha256,
                'keys': sorted(reserved), 'reason': self.reason or 'collection_closed',
                'positive_evidence': 'entry remained reserved; durable dispatch API was never invoked'})
            sha = digest(cancellation.read_bytes())
            for key in reserved:
                self.permit.ledger.cancel_reserved(key, sha)
        final = self.permit.ledger.snapshot()
        write_once(self.execution / 'final-ledger-snapshot.json', final)
        write_once(self.execution / 'STOP.json', {'version': VERSION, 'status': 'closed',
            'manifest_sha256': self.permit.manifest_sha256, 'reason': self.reason or 'planned_core_complete',
            'finished_at': datetime.now(timezone.utc).isoformat(),
            'journal_sha256': digest((self.execution / 'accounting.jsonl').read_bytes())})
        self.event('bounded_core_finished', reason=self.reason or 'planned_core_complete',
                   status_counts=dict(self.completed), planned_cells=len(self.permit.cells))


def execute(manifest, authorization, review):
    raw = json.loads(Path(manifest).read_text())
    execution = ROOT / raw['execution_directory']
    execution.mkdir(parents=True, exist_ok=True)
    with (execution / '.sole-executor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        permit = Permit(manifest, authorization, review, execution)
        permit.policy = freeze_policy(manifest, prior_receipt_path=raw['closed_evidence']['receipt']['path'],
                                     prior_journal_path=raw['closed_evidence']['journal']['path'])
        permit.ledger = FollowupLedger(execution / 'accounting.jsonl', permit.policy)
        permit.monotonic_remaining = permit.ledger.remaining_seconds()
        runner = Executor(permit)
        try:
            runner.stage('preflight', 1)
            preflight = [c for g in permit.groups if g['stage'] == 'preflight' for c in g['cells']]
            valid = 0
            for g in (g for g in permit.groups if g['stage'] == 'preflight'):
                for s in permit.specs(g):
                    p = runner.attempts / s['key'] / 'completed.json'
                    valid += int(p.exists() and json.loads(p.read_text())['parsed'].get('valid') is True)
            if valid != len(preflight) or valid != 10:
                runner.reason = runner.reason or 'preflight_technical_failure'
                runner.fatal.set()
            else:
                gate = execution / 'preflight-validation.json'
                if not gate.exists():
                    write_once(gate, {'manifest_sha256': permit.manifest_sha256,
                        'valid_technical_outputs': valid, 'correctness_used_as_gate': False})
                for stage in ('main', 'repeat', 'audit'):
                    runner.stage(stage, raw['workers'])
                    if runner.fatal.is_set():
                        break
        except Exception as error:
            runner.reason = 'executor_stop:' + type(error).__name__
            runner.event('executor_stop', error_type=type(error).__name__)
            raise
        finally:
            runner.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--manifest', required=True)
    parser.add_argument('--authorization', required=True)
    parser.add_argument('--review', required=True)
    args = parser.parse_args()
    execute(args.manifest, args.authorization, args.review)
