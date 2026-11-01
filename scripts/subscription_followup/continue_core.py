"""Operational unsent-only continuation; original core records stay immutable."""
from __future__ import annotations

import argparse
import copy
from datetime import datetime, timedelta, timezone
import fcntl
import json
from pathlib import Path

from scripts.study_v7.requests import canonical, digest
from scripts.subscription_followup.budget import FollowupLedger
from scripts.subscription_followup.run import ROOT, Permit, Executor
from scripts.subscription_followup.transport import write_once

VERSION = 'subscription-followup-core-continuation-1'
ORIGINAL_MANIFEST_SHA = 'b300dee09c2b116b203523cf8d8922ba55665491d3ac127a8fefe8607c5e8fcb'
ORIGINAL_JOURNAL_SHA = '05cf42e643a72dc0d248f593d46fddcea41b40d5b81315f5c71dce2999420426'
OVERLOAD_KEY = '15bfd5786205d9dc7879026c2f64b6565009e198acffabdacf07a655a8153453'


def read(path):
    return json.loads(Path(path).read_text())


def descriptor(path):
    path = Path(path).resolve()
    return {'path': str(path), 'sha256': digest(path.read_bytes())}


def save_same(path, value):
    path = Path(path)
    body = canonical(value)
    if path.exists():
        if path.read_bytes() != body:
            raise PermissionError('Preparation refuses changed existing bytes: ' + str(path))
        return
    write_once(path, body)


def prepare():
    original_manifest = ROOT / 'results/subscription-followup/run-manifest-core-v1.json'
    original = read(original_manifest)
    if digest(original_manifest.read_bytes()) != ORIGINAL_MANIFEST_SHA:
        raise PermissionError('Original core manifest differs')
    old_execution = ROOT / original['execution_directory']
    journal = old_execution / 'accounting.jsonl'
    if digest(journal.read_bytes()) != ORIGINAL_JOURNAL_SHA:
        raise PermissionError('Original terminal journal differs')
    probe = object.__new__(FollowupLedger)
    probe.path, probe._cache = journal, None
    state = probe._read()
    snapshot = read(old_execution / 'final-ledger-snapshot.json')
    if (not snapshot['terminal'] or any(snapshot['incremental_accounted_usd'][p] != '0'
            for p in ('openai', 'typesafe')) or read(old_execution / 'STOP.json')['journal_sha256'] != ORIGINAL_JOURNAL_SHA):
        raise PermissionError('Original core is not closed at unchanged zero-dollar increment')
    for key in state:
        if key in snapshot and state[key] != snapshot[key]:
            raise PermissionError('Original snapshot differs from journal replay: ' + key)
    plan = read(ROOT / original['plan']['path'])
    cells = {c['cell_id']: c for g in plan['groups'] for c in g['cells']}
    actual, cancelled = {}, {}
    actual_stages = {'preflight': 0, 'main': 0, 'repeat': 0, 'audit': 0}
    for key, entry in state['entries'].items():
        cell = cells.get(entry['cell_id'])
        if cell is None or entry['request_sha256'] != cell['payload_sha256']:
            raise PermissionError('Old entry is outside the original scientific roster')
        directory = old_execution / 'attempts' / key
        if entry['status'] in ('settled', 'unknown_usage'):
            completed_path = directory / 'completed.json'
            result = read(completed_path)
            if (digest(completed_path.read_bytes()) != entry['evidence_sha256'] or
                any(result.get(k) != v for k, v in {'key': key, 'cell_id': cell['cell_id'],
                    'namespace': cell['namespace'], 'config': cell['config'],
                    'request_sha256': cell['payload_sha256']}.items())):
                raise PermissionError('Old completion identity/evidence differs')
            for name, sha in result['raw_hashes'].items():
                if Path(name).name != name or digest((directory / name).read_bytes()) != sha:
                    raise PermissionError('Old actual raw evidence changed')
            actual[cell['cell_id']] = {'key': key, 'stage': entry['split'],
                'evidence_sha256': entry['evidence_sha256']}
            actual_stages[entry['split']] += 1
        elif entry['status'] == 'cancelled_unsent':
            cancellation = old_execution / 'unsent-closeout.json'
            if (directory.exists() or digest(cancellation.read_bytes()) != entry['evidence_sha256'] or
                key not in read(cancellation)['keys']):
                raise PermissionError('Cancelled cell lacks positive never-dispatched proof')
            cancelled[cell['cell_id']] = key
        else:
            raise PermissionError('Unresolved old admission cannot continue')
    if len(actual) != 464 or len(cancelled) != 10 or actual_stages != {'preflight': 10, 'main': 454, 'repeat': 0, 'audit': 0}:
        raise PermissionError('Exact source closure counts differ')
    overload_path = old_execution / 'attempts' / OVERLOAD_KEY / 'completed.json'
    overload = read(overload_path)
    if not structured_overload(overload):
        raise PermissionError('Continuation does not bind the observed availability failure')
    gate = old_execution / 'preflight-validation.json'
    if read(gate) != {'manifest_sha256': ORIGINAL_MANIFEST_SHA,
                      'valid_technical_outputs': 10, 'correctness_used_as_gate': False}:
        raise PermissionError('Original ten-cell technical gate differs')
    groups = []
    for old_group in plan['groups']:
        group = copy.deepcopy(old_group)
        group['cells'] = [c for c in group['cells'] if c['cell_id'] not in actual]
        if group['cells']:
            groups.append(group)
    remaining = {c['cell_id'] for g in groups for c in g['cells']}
    if actual.keys() & remaining or set(cells) != actual.keys() | remaining or len(remaining) != 4046:
        raise PermissionError('Continuation is not the exact original unsent complement')
    updated = copy.deepcopy(plan)
    updated.update(version='subscription-followup-core-plan-2',
                   run_namespace='subscription-followup-20261101-v2', groups=groups,
                   counts={'preflight': 0, 'main': 3546, 'repeat': 400, 'audit': 100},
                   total_cells=4046, continuation_of_manifest_sha256=ORIGINAL_MANIFEST_SHA)
    updated['group_counts'] = {stage: sum(g['stage'] == stage for g in groups) for stage in updated['counts']}
    plan_path = ROOT / 'data/raw/subscription-followup/core-plan-v2.json'
    save_same(plan_path, updated)
    anchor = state['window_started_at_utc']
    deadline = (datetime.fromisoformat(anchor) + timedelta(seconds=18000)).isoformat()
    receipt = {'version': VERSION, 'reason': 'exact_structured_server_overload_after_original_stop',
        'postcollection_operational_amendment': True, 'accuracy_used_to_choose_change': False,
        'original_manifest_sha256': ORIGINAL_MANIFEST_SHA, 'original_journal_sha256': ORIGINAL_JOURNAL_SHA,
        'original_stop_sha256': digest((old_execution / 'STOP.json').read_bytes()),
        'original_snapshot_sha256': digest((old_execution / 'final-ledger-snapshot.json').read_bytes()),
        'original_plan_sha256': original['plan']['sha256'],
        'new_plan_sha256': digest(plan_path.read_bytes()),
        'prior_actual_stage_counts': actual_stages, 'prior_actual_cells': len(actual),
        'proven_unsent_cancelled_cells': len(cancelled), 'never_admitted_cells': 4036,
        'original_deadline_utc': deadline,
        'continuation_cell_ids_sha256': digest(canonical(sorted(remaining))),
        'never_retry_dispatched': True,
        'original_actual_cells': actual, 'original_actual_counts': actual_stages,
        'original_cancelled_unsent_cells': cancelled, 'original_never_admitted_cells': 4036,
        'original_unique_cells': 4510, 'remaining_cells': 4046, 'remaining_counts': updated['counts'],
        'original_window_started_at_utc': anchor, 'admission_deadline_utc': deadline,
        'original_preflight_validation': descriptor(gate), 'failed_first_outcome': descriptor(overload_path),
        'failed_request_key': OVERLOAD_KEY, 'failure_code': 'server_is_overloaded',
        'failure_http_status': 200, 'failure_type': 'service_unavailable_error',
        'no_dispatched_or_failed_cell_retried': True, 'scientific_roster_payloads_analysis_unchanged': True,
        'plan': {'path': str(plan_path.relative_to(ROOT)), 'sha256': digest(plan_path.read_bytes()),
                 'bytes': plan_path.stat().st_size}}
    receipt_path = ROOT / 'results/subscription-followup/continuation-receipt-v2.json'
    save_same(receipt_path, receipt)
    return receipt


def structured_overload(result):
    p, observation = result.get('parsed', {}), result.get('observation', {})
    return (result.get('config') == 'sol_subscription' and observation.get('http_status') == 200
        and observation.get('transport_exit_code') == 0 and p.get('status') == 'provider_failed'
        and p.get('termination') == 'failed' and p.get('returned_model') == 'gpt-6.1-sol'
        and p.get('error_code') == 'server_is_overloaded'
        and p.get('error_type') == 'service_unavailable_error')


class ContinuationPermit(Permit):
    def check(self):
        super().check()
        deadline = datetime.fromisoformat(self.manifest['continuation']['admission_deadline_utc'])
        if datetime.now(timezone.utc) >= deadline:
            raise PermissionError('Original five-hour deadline ended')
        return True


class ContinuationExecutor(Executor):
    def __init__(self, permit):
        super().__init__(permit)
        self.service_failures = [{'key': OVERLOAD_KEY, 'http_status': 200,
            'error_code': 'server_is_overloaded', 'retry_after_seconds': 120.}]
        self.consecutive_service_failures = 0  # Three valid in-flight responses followed the old failure.

    def restore(self):
        snapshot = self.permit.ledger.snapshot()
        if (any(self.attempts.iterdir()) or snapshot['entries'] or
            snapshot['window_started_at_utc'] != self.permit.manifest['continuation']['original_window_started_at_utc']):
            raise PermissionError('Continuation restart is denied; no outcome/intent may replay')

    def observe(self, group, result):
        if not structured_overload(result):
            return super().observe(group, result)
        with self.lock:
            self.completed[result['parsed']['status']] += 1
            self.consecutive_service_failures += 1
            value = result['observation'].get('response_headers', {}).get('retry-after', '120')
            try:
                retry = max(120., float(value))
            except (ValueError, TypeError):
                try:
                    from email.utils import parsedate_to_datetime
                    retry = max(120., (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds())
                except (ValueError, TypeError, OverflowError):
                    retry = 120.
            row = {'key': result['key'], 'http_status': 200, 'error_code': 'server_is_overloaded',
                   'retry_after_seconds': retry}
            self.service_failures.append(row)
            self.event('service_failure', **row)
            self.pause.set()
            if retry > 600 or self.consecutive_service_failures >= 3 or len(self.service_failures) > 5:
                self.reason = ('provider_retry_interval_exceeds_bound' if retry > 600
                               else 'bounded_service_recovery_exhausted')
                self.fatal.set()


def execute(manifest, authorization, review):
    from scripts.subscription_followup.continuation_budget import freeze_continuation_policy, ContinuationLedger
    raw = read(manifest)
    execution = ROOT / raw['execution_directory']
    execution.mkdir(parents=True, exist_ok=True)
    with (execution / '.sole-executor.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        p = ContinuationPermit(manifest, authorization, review, execution)
        p.policy = freeze_continuation_policy(manifest, prior_receipt_path=raw['closed_evidence']['receipt']['path'],
                                              prior_journal_path=raw['closed_evidence']['journal']['path'])
        p.ledger = ContinuationLedger(execution / 'accounting.jsonl', p.policy)
        p.monotonic_remaining = p.ledger.remaining_seconds()
        runner = ContinuationExecutor(p)
        try:
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
    parser.add_argument('--prepare', action='store_true')
    parser.add_argument('--manifest')
    parser.add_argument('--authorization')
    parser.add_argument('--review')
    args = parser.parse_args()
    if args.prepare:
        value = prepare()
        print(json.dumps({k: value[k] for k in ('remaining_cells', 'remaining_counts',
            'original_window_started_at_utc', 'admission_deadline_utc', 'plan')}, indent=2))
    elif args.manifest and args.authorization and args.review:
        execute(args.manifest, args.authorization, args.review)
    else:
        parser.error('Provide --prepare or all three execution files')
