"""Sole-executor v6 runner: frozen inputs, paired budgets, durable first attempts.

No prediction or source label enters scheduling/admission. A saved systemic stop
requires a separate documented resolution; this module never retries a request.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import fcntl
import gc
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6 import plan, routes
from scripts.study_v6.accounting import BudgetLedger, AccountingError
from scripts.study_v6.common import ROOT, sha256, canonical_bytes
from scripts.study_v6.evidence import exclusive, immutable, load
from scripts.study_v6.pricing import usage_cost


def spec(request):
    return {k: request[k] for k in ('key', 'provider', 'reserved_usd', 'request_sha256', 'config', 'split')}


@contextmanager
def executor_lock(directory):
    directory.mkdir(parents=True, exist_ok=True)
    with (directory / 'sole-executor.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


class Executor:
    """Evidence state machine; injectable transport only for deterministic fixtures."""
    def __init__(self, frozen, ledger, directory, *, invoke=routes.invoke, runtime_factory=routes.make_runtime):
        self.frozen, self.ledger, self.directory = frozen, ledger, Path(directory)
        self.requests = {r['key']: r for r in frozen['requests']}
        self.invoke, self.runtime_factory = invoke, runtime_factory
        self.runtimes = {}
        self.stop_path = self.directory / 'STOP.json'
        self.executed = 0
        if len(self.requests) != len(frozen['requests']):
            raise ValueError('Duplicate frozen requests')
        ledger_keys = set(self.ledger.snapshot()['entries'])
        if any(p.name not in ledger_keys for p in (self.directory / 'attempts').glob('*') if p.is_dir()):
            self.stop('Retained raw attempt absent from journal; accounting integrity unresolved')

    def stop(self, reason, key=None):
        receipt = {'reason': reason, 'request_key': key,
                   'created_at_utc': datetime.now(timezone.utc).isoformat(),
                   'automatic_retry': False, 'remaining_dispatch_blocked': True}
        if not self.stop_path.exists():
            exclusive(self.stop_path, receipt)
        # Preserve every hold until an explicit reviewed continuation or an
        # accounting-only terminal closure. A transient failure must not force
        # unsent members of its already-reserved whole group to disappear.
        raise PermissionError('Execution stopped: ' + reason)

    def check_stop(self):
        if self.stop_path.exists():
            raise PermissionError('Immutable systemic stop requires documented resolution')

    def close_stopped(self):
        """Accounting/evidence only. Never invoke a transport under a saved stop."""
        if not self.stop_path.exists():
            raise PermissionError('A preserved stop is required for accounting-only closure')
        stop_hash = sha256(self.stop_path.read_bytes())
        for key, entry in self.ledger.snapshot()['entries'].items():
            if entry['status'] == 'reserved':
                folder = self.directory / 'attempts' / key
                if folder.exists():
                    # Conflicting raw artifacts defeat proof of "unsent". Record
                    # an accounting-only ambiguous intent, never a network call.
                    self.ledger.mark_dispatched(key)
                    request = self.requests[key]
                    result = {'parsed': {'status': 'interrupted_unknown', 'valid': False, 'prediction': None},
                        'request_sha256': request['request_sha256'],
                        'raw_hashes': {p.name: sha256(p.read_bytes()) for p in sorted(folder.glob('*')) if p.is_file()},
                        'stop_required': True, 'reserved_raw_conflict_retained': True}
                    self._record(request, result)
                else:
                    self.ledger.cancel_reserved(key, evidence_sha256=stop_hash)
            elif entry['status'] == 'dispatched':
                request = self.requests[key]
                folder = self.directory / 'attempts' / key
                completed = folder / 'completed.json'
                if completed.exists():
                    result = self._load_evidence(completed, key)
                    self._verify_result(request, result)
                else:
                    result = {'parsed': {'status': 'interrupted_unknown', 'valid': False, 'prediction': None},
                        'request_sha256': request['request_sha256'],
                        'raw_hashes': {p.name: sha256(p.read_bytes()) for p in sorted(folder.glob('*')) if p.is_file()},
                        'stop_required': True, 'interrupted_dispatch_intent_preserved': True}
                self._record(request, result)
        return self.ledger.snapshot()

    def _record(self, request, result):
        provider = request['provider']
        try:
            costs = usage_cost(provider, result['parsed'].get('usage')) if provider else {
                'accounted_usd': '0', 'actual_billed_usd': None,
                'basis': 'Existing subscription/local route; zero incremental metered API charge'}
        except (KeyError, TypeError, ValueError):
            self.stop('Malformed retained usage; accounting unresolved', request['key'])
        charged = self.ledger.snapshot()['entries'][request['key']]['allocation']
        record = {'version': plan.VERSION, 'key': request['key'], 'config': request['config'],
            'split': request['split'], 'allocation': request['allocation'], 'batch': request['batch'],
            'charged_allocation': charged,
            'request_sha256': request['request_sha256'], 'attempt': 0, 'result': result,
            'costs': costs, 'reserved_usd': request['reserved_usd'],
            'first_attempt_primary': True}
        path = self.directory / 'attempts' / request['key'] / 'execution-record.json'
        try:
            immutable(path, record)
        except (OSError, TypeError, ValueError):
            self.stop('Execution record missing, conflicting or unwritable', request['key'])
        try:
            self.ledger.settle(request['key'], costs['accounted_usd'], evidence_sha256=sha256(path.read_bytes()))
        except AccountingError:
            self.stop('Usage/accounting mismatch; raw evidence and reservation retained', request['key'])
        return record

    def _load_evidence(self, path, key):
        try:
            value = load(path)
            if not isinstance(value, dict):
                raise ValueError('Evidence object required')
            return value
        except (OSError, TypeError, ValueError):
            self.stop('Retained raw execution evidence is missing or unreadable', key)

    def _terminal_gate(self, record, key):
        if record['result']['stop_required']:
            from scripts.study_v6.continuations import approved_failure
            if not approved_failure(key, self.ledger, self.directory, ROOT):
                self.stop('Preserved first-attempt route failure', key)
        if record['costs'].get('unexpected_pricing_tier'):
            self.stop('Unexpected long-input pricing tier; actual multiplier accounted', key)
        if record['config'] in plan.PROVIDERS and record['costs']['accounted_usd'] is None and record['result']['parsed']['status'] in ('ok', 'tie'):
            self.stop('Completed paid decision has unresolved usage accounting; reservation retained', key)

    def dispatch(self, key):
        self.check_stop()
        request = self.requests[key]
        if request.get('inference_eligible') is not True:
            raise PermissionError('Request failed frozen execution eligibility')
        if sha256(canonical_bytes(request['payload'])) != request['request_sha256']:
            self.stop('Frozen request corrupt', key)
        entry = self.ledger.snapshot()['entries'].get(key)
        if entry is None:
            if (self.directory / 'attempts' / key).exists():
                self.stop('Raw attempt lacks reservation; journal integrity unresolved', key)
            raise PermissionError('No atomic reservation before dispatch')
        folder = self.directory / 'attempts' / key
        record_path = folder / 'execution-record.json'
        if entry['status'] in ('settled', 'unknown_usage'):
            try:
                record_matches = sha256(record_path.read_bytes()) == entry['evidence_sha256']
            except OSError:
                record_matches = False
            if not record_matches:
                self.stop('Terminal accounting lacks identical raw execution evidence', key)
            record = self._load_evidence(record_path, key)
            self._verify_result(request, record['result'])
            self._terminal_gate(record, key)
            return record
        if entry['status'] == 'cancelled_unsent':
            self.stop('Cancelled systemic-failure cohort cannot advance', key)
        if entry['status'] == 'dispatched':
            completed = folder / 'completed.json'
            if completed.exists():
                result = self._load_evidence(completed, key)
                self._verify_result(request, result)
                record = self._record(request, result)
                self._terminal_gate(record, key)
                return record
            # A crash could occur even before opening a socket. Absence of a
            # terminal raw response cannot prove zero provider usage.
            files = {p.name: sha256(p.read_bytes()) for p in sorted(folder.glob('*')) if p.is_file()}
            result = {'parsed': {'status': 'interrupted_unknown', 'valid': False, 'prediction': None},
                'request_sha256': request['request_sha256'], 'raw_hashes': files,
                'stop_required': True, 'interrupted_dispatch_intent_preserved': True}
            record = self._record(request, result)
            self.stop('Interrupted first attempt retained; no resend', key)
        if entry['status'] != 'reserved' or folder.exists():
            self.stop('Reservation/raw attempt state conflict', key)
        config = request['config']
        if config not in self.runtimes:
            # Credential/access errors still get their own preserved first attempt;
            # local metadata loading errors occur before dispatch intent.
            try:
                self.runtimes[config] = self.runtime_factory(config)
            except Exception as error:
                self.stop('Local runtime gate failed: ' + type(error).__name__, key)
        self.ledger.mark_dispatched(key)
        try:
            result = self.invoke(config, request['payload'], self.directory / 'attempts', key,
                                 runtime=self.runtimes[config])
        except Exception as error:
            # Never assume an exception means no request was sent. Preserve intent;
            # resumption will convert it to unknown usage without dispatching again.
            self.stop('Transport raised after dispatch intent: ' + type(error).__name__, key)
        self._verify_result(request, result)
        record = self._record(request, result)
        self.executed += 1
        print(json.dumps({'config': config, 'split': request['split'], 'allocation': request['allocation'],
                          'first_attempts_this_process': self.executed,
                          'disposition': result['parsed']['status']}), flush=True)
        self._terminal_gate(record, key)
        return record

    def _verify_result(self, request, result):
        try:
            if result['request_sha256'] != request['request_sha256']:
                raise ValueError('Raw request hash differs from freeze')
            if not isinstance(result['parsed'], dict) or not isinstance(result['parsed']['status'], str) or type(result['stop_required']) is not bool:
                raise ValueError('Malformed result disposition')
            folder = self.directory / 'attempts' / request['key']
            for name, digest in result['raw_hashes'].items():
                if Path(name).name != name or sha256((folder / name).read_bytes()) != digest:
                    raise ValueError('Retained raw response evidence changed')
        except (OSError, KeyError, TypeError, ValueError):
            self.stop('Retained raw response evidence missing, changed or malformed', request['key'])

    def development(self):
        self.check_stop()
        requests = [r for r in self.requests.values() if r['split'] == 'development']
        # Keep only one Python local model resident. No extra inference or model
        # API request is used for unloading; native keep_alive remains fixed.
        for config in plan.CONFIGS:
            for request in requests:
                if request['config'] == config:
                    # Development has a smaller envelope than its aggregate byte
                    # holds. Reserve each fixed request immediately before its
                    # first attempt, settling it before the next admission.
                    self.ledger.reserve_batch('development:request:' + request['key'],
                                              'development', [spec(request)])
                    self.dispatch(request['key'])
            self.runtimes.pop(config, None)
            gc.collect()

    def paid(self, allocation):
        self.check_stop()
        entries = self.frozen['schedules'][allocation]
        scheduled = []
        for group in entries:
            keys = group['request_keys']
            if not group['all_requests_supported']:
                # This exclusion is fixed before execution, not a cost-based skip.
                continue
            if any(k not in self.requests for k in keys):
                raise ValueError('Whole-group request omitted from frozen eligibility')
            scheduled.append({'group': group['batch'], 'requests': [spec(self.requests[k]) for k in keys]})
        self.ledger.register_schedule(allocation, scheduled)
        state = self.ledger.snapshot()['schedules'][allocation]
        # Resume the last admitted group before asking the cost-only allocator to
        # advance. Completed/unknown first attempts are read, never resent.
        if state['admitted']:
            for request in state['groups'][state['admitted'] - 1]['requests']:
                self.dispatch(request['key'])
        while True:
            admission = self.ledger.reserve_next_group(allocation)
            if admission['status'] != 'admitted':
                print(json.dumps({'allocation': allocation, 'budget_disposition': admission['status'],
                                  'admitted_groups': self.ledger.snapshot()['schedules'][allocation]['admitted']}), flush=True)
                return admission
            for key in admission['request_keys']:
                self.dispatch(key)

    def comparator(self, config):
        self.check_stop()
        if config not in plan.COMPARATORS + ('protectai_local',):
            raise ValueError('Comparator configuration required')
        requests = [r for r in self.requests.values() if r['split'] == 'confirmation'
                    and r['config'] == config]
        if requests:
            self.ledger.reserve_unmetered_batch('comparators:' + config, [spec(r) for r in requests])
        for request in requests:
            self.dispatch(request['key'])


def run(action, config=None):
    from scripts.study_v6.freeze import verify
    split = 'development' if action == 'development' or (action == 'close-stopped' and
             not (plan.RESULTS / 'confirmation-freeze-v1.json').exists()) else 'confirmation'
    with executor_lock(plan.DEST):
        _, frozen = verify(split)
        from scripts.study_v6.runtime import verify as verify_runtime
        verify_runtime(load(plan.RESULTS / 'runtime-versions-v1.json'))
        ledger = BudgetLedger(plan.DEST / 'budget.jsonl', load(plan.DEST / 'inherited-accounting.json'), history_root=ROOT)
        executor = Executor(frozen, ledger, plan.DEST)
        if action == 'close-stopped':
            executor.close_stopped()
        elif action == 'development':
            executor.development()
        elif action in ('main', 'supporting'):
            executor.paid(action)
        else:
            executor.comparator(config)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('development', 'main', 'supporting', 'comparator', 'close-stopped'))
    parser.add_argument('--config', choices=plan.COMPARATORS + ('protectai_local',))
    args = parser.parse_args()
    if args.action == 'comparator' and not args.config:
        parser.error('--config required for comparator')
    run(args.action, args.config)
