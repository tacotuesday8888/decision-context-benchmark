"""V7 manifest inspection and explicitly owner-authorized later execution.

All current manifests are paused. Default invocation performs offline hash checks.
Even --execute is inert without an owner instruction, exact frozen hashes, separate
bounded provider budgets, a declared cutoff and (for confirmation) route validation.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import fcntl
import json
import os
from pathlib import Path
import re
import threading
import time
from scripts.study_v7.requests import PANEL, canonical, digest, materialize
from scripts.study_v7.budget import BudgetLedger, policy, reservation, usage_cost
from scripts.study_v6.routes import _exclusive

ROOT = Path(__file__).resolve().parents[2]
CANONICAL = ROOT.parent / 'Decision Context Benchmark'
RAW = ROOT / 'data/raw/study-v7'
DEFAULT_MANIFEST = ROOT / 'results/study-v7/run-manifest.json'
DEFAULT_AUTHORIZATION = ROOT / 'results/study-v7/run-authorization.json'
PHASES = {
    'development': ('development_main', 'development_external', 'development_sol_main', 'development_sol_external'),
    'audit': ('audit',),
    'confirmation': ('main_native', 'main_general', 'external_native', 'external_general', 'main_sol', 'external_sol'),
    'repeat': ('repeat_native', 'repeat_general', 'repeat_sol'),
}


def _read(path):
    return json.loads(Path(path).read_text())


def _inside(path, parent):
    path, parent = Path(path).resolve(), Path(parent).resolve()
    if path != parent and parent not in path.parents:
        raise ValueError('Artifact path escapes its authorized tree')
    return path


def _project_path(value):
    path = Path(value)
    return _inside(path if path.is_absolute() else ROOT / path, ROOT)


def verify_manifest(path):
    manifest = _read(path)
    if manifest.get('version') != 'study-v7-run-1':
        raise ValueError('Unsupported v7 run manifest')
    plan_path = _inside(_project_path(manifest['plan_path']), RAW)
    if digest(plan_path.read_bytes()) != manifest['plan_sha256']:
        raise ValueError('Request plan hash changed')
    plan = _read(plan_path)
    if plan.get('experimental_inference_authorized') is not False:
        raise ValueError('Preparation plan must preserve its original paused state')
    rows = {}
    for source in manifest['source_files']:
        source_path = _inside(_project_path(source['path']), RAW)
        if digest(source_path.read_bytes()) != source['sha256']:
            raise ValueError('Locked source bytes changed')
        for line in source_path.open():
            row = json.loads(line)
            if row['id'] in rows:
                raise ValueError('Duplicate locked source row')
            rows[row['id']] = row
    for name, sha in manifest['historical_accounting'].get('evidence_sha256', {}).items():
        history_path = _inside(CANONICAL / name, CANONICAL)
        if digest(history_path.read_bytes()) != sha:
            raise ValueError('Historical spending changed; reconcile before authorization')
    # Bind payload construction code/configuration, not only the saved plan.
    for name, sha in manifest.get('execution_code_sha256', {}).items():
        if digest(_project_path(name).read_bytes()) != sha:
            raise ValueError('Frozen execution code changed')
    return manifest, plan, rows


def _stop_policy(receipt):
    """A continuation acknowledges exact old stops; a new stop remains final."""
    def valid_name(name):
        return isinstance(name, str) and re.fullmatch(r'stop(?:-[A-Za-z0-9_.-]+)?\.json', name) is not None
    name = receipt.get('stop_record_name', 'stop.json')
    acknowledged = receipt.get('acknowledged_stops', {})
    if not valid_name(name) or not isinstance(acknowledged, dict):
        raise PermissionError('Invalid immutable stop-record policy')
    for old_name, sha in acknowledged.items():
        if (not valid_name(old_name) or old_name == name or not isinstance(sha, str) or
                re.fullmatch(r'[0-9a-f]{64}', sha) is None):
            raise PermissionError('Acknowledged stops require distinct safe names and exact SHA256 hashes')
    return name, acknowledged


def _check_stops(execution, receipt):
    """Never delete/rewrite stops; any unacknowledged current/new stop blocks."""
    name, acknowledged = _stop_policy(receipt)
    execution = Path(execution)
    for old_name, sha in acknowledged.items():
        path = execution / old_name
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != sha:
            raise PermissionError('Acknowledged historical stop is missing or changed: ' + old_name)
    for path in execution.glob('stop*.json'):
        if path.name not in acknowledged:
            raise PermissionError('Unacknowledged preserved v7 stop blocks dispatch: ' + path.name)
    return execution / name


def _pause_policy(receipt):
    name = receipt.get('pause_record_name', 'paused-sol_subscription.json')
    acknowledged = receipt.get('acknowledged_pauses', {})
    pattern = r'paused-sol_subscription(?:-[A-Za-z0-9_.-]+)?\.json'
    if not isinstance(name, str) or re.fullmatch(pattern, name) is None or not isinstance(acknowledged, dict):
        raise PermissionError('Invalid immutable subscription pause policy')
    for old_name, sha in acknowledged.items():
        if (not isinstance(old_name, str) or re.fullmatch(pattern, old_name) is None or old_name == name or
                not isinstance(sha, str) or re.fullmatch(r'[0-9a-f]{64}', sha) is None):
            raise PermissionError('Acknowledged pauses require distinct safe names and exact SHA256 hashes')
    return name, acknowledged


def _paused_configurations(execution, receipt):
    _, acknowledged = _pause_policy(receipt)
    execution = Path(execution)
    for name, sha in acknowledged.items():
        path = execution / name
        if path.is_symlink() or not path.is_file() or digest(path.read_bytes()) != sha:
            raise PermissionError('Acknowledged subscription pause is missing or changed: ' + name)
    # Every new unacknowledged pause closes only the isolated subscription lane.
    return {'sol_subscription'} if any(p.name not in acknowledged for p in execution.glob('paused-*.json')) else set()


class OwnerPermit:
    """Validated immutable owner receipt; not an environment toggle or API login."""
    def __init__(self, authorization_path, manifest_path, phase):
        self.authorization_path = Path(authorization_path).resolve()
        self.manifest_path = Path(manifest_path).resolve()
        self.manifest, self.plan, self.rows = verify_manifest(self.manifest_path)
        self.manifest_sha256 = digest(self.manifest_path.read_bytes())
        self.receipt = _read(self.authorization_path)
        self.authorization_sha256 = digest(self.authorization_path.read_bytes())
        self.credential_root = CANONICAL
        self.phase = phase
        self.ledger = None
        self.execution_profile = self.plan.get('execution_profile', 'original-paid-sol-preparation')
        self.active_configurations = set(self.plan.get('active_configurations', self.plan.get('model_configurations', PANEL)))
        self.check()

    def check(self):
        r = self.receipt
        _stop_policy(r)
        _pause_policy(r)
        if digest(self.authorization_path.read_bytes()) != self.authorization_sha256:
            raise PermissionError('Owner authorization changed during execution')
        if digest(self.manifest_path.read_bytes()) != self.manifest_sha256:
            raise PermissionError('Frozen manifest changed during execution')
        if (r.get('experimental_inference_authorized') is not True or
                r.get('resume_experimental_inference') is not True or
                r.get('authorization_source') != 'explicit_owner_instruction' or
                not isinstance(r.get('owner_instruction'), str) or not r['owner_instruction'].strip()):
            raise PermissionError('Experimental inference is paused; explicit bounded owner resume is required')
        if r.get('manifest_sha256') != self.manifest_sha256 or r.get('plan_sha256') != self.manifest['plan_sha256']:
            raise PermissionError('Owner authorization does not bind this exact frozen study')
        if r.get('execution_profile') is not None and r['execution_profile'] != self.execution_profile:
            raise PermissionError('Owner receipt execution profile differs from the frozen plan')
        if r.get('allow_paid_sol_api') is False and 'sol_responses' in self.active_configurations:
            raise PermissionError('Owner receipt forbids paid Sol API irrespective of plan profile')
        if self.execution_profile == 'cheap-api-sol-subscription':
            if r.get('execution_profile') != self.execution_profile or r.get('allow_paid_sol_api') is not False:
                raise PermissionError('Active owner profile forbids paid Sol API and must explicitly match subscription profile')
            if 'sol_responses' in self.active_configurations:
                raise PermissionError('Paid Sol is excluded from the active owner profile')
        if self.phase not in r.get('authorized_phases', []):
            raise PermissionError('Requested phase lacks bounded authorization')
        if r.get('allow_subscription_fallback') is not False or r.get('allow_purchases_or_recharge') is not False:
            raise PermissionError('Purchases and subscription fallback are forbidden')
        if not r.get('approved_at_utc') or not r.get('admission_deadline_utc'):
            raise PermissionError('Owner approval time and outcome-blind admission cutoff required')
        datetime.fromisoformat(r['approved_at_utc'].replace('Z', '+00:00'))
        deadline = datetime.fromisoformat(r['admission_deadline_utc'].replace('Z', '+00:00'))
        if deadline.tzinfo is None:
            raise PermissionError('Cutoff must have explicit timezone')
        if not r.get('caps_usd') or not r.get('incremental_caps_usd') or not r.get('allocations_usd'):
            raise PermissionError('Separate bounded cumulative/incremental/phase allocations required')
        if r.get('historical_accounted_usd') != self.manifest['historical_accounting']['prior_accounted_usd']:
            raise PermissionError('Owner budget does not include reconciled historical spending')
        if self.phase in ('confirmation', 'repeat', 'all'):
            validation = self.manifest.get('route_validation') or {}
            if validation.get('completed') is not True or validation.get('plan_sha256') != self.manifest['plan_sha256']:
                raise PermissionError('Authorized development must verify routes/settings/throughput before confirmation')
            validated = set(validation.get('validated_configurations', []))
            unsupported = set(validation.get('unsupported_configurations', {}))
            if validated & unsupported or validated | unsupported != self.active_configurations:
                raise PermissionError('Every active configuration needs a validated or explicit unsupported disposition')
            # Only the separately scheduled subscription comparator may remain
            # unsupported while confirmation proceeds. Either native route (or
            # another mixed core configuration) must be resolved before admitting
            # confirmation, rather than crashing inside a reserved mixed batch.
            core_unsupported = unsupported - {'sol_subscription'}
            if core_unsupported:
                raise PermissionError('Core configuration unsupported before confirmation: ' +
                                      ', '.join(sorted(core_unsupported)))
        return True

    def admission_open(self):
        deadline = datetime.fromisoformat(self.receipt['admission_deadline_utc'].replace('Z', '+00:00'))
        return datetime.now(timezone.utc) < deadline

    def check_request(self, record, payload):
        self.check()
        if record['config'] not in self.active_configurations:
            raise PermissionError('Inactive configuration is not authorized')
        if (self.execution_profile == 'cheap-api-sol-subscription' or self.receipt.get('allow_paid_sol_api') is False) and record['config'] == 'sol_responses':
            raise PermissionError('Paid Sol API is forbidden')
        if record['config'] in (self.manifest.get('route_validation') or {}).get('unsupported_configurations', {}):
            raise PermissionError('Configuration is explicitly unsupported; no inference dispatch')
        if self.plan['requests'].get(record['key']) != record or digest(canonical(payload)) != record['payload_sha256']:
            raise PermissionError('Request differs from owner-bound first/repeat manifest')
        if record['allocation'] not in self.allowed_allocations:
            raise PermissionError('Request is outside the authorized execution phase')

    def check_dispatch(self, record, payload):
        self.check_request(record, payload)
        if self.ledger is None:
            raise PermissionError('Dispatch requires the single executor budget journal')
        entry = self.ledger.entry(record['key'])
        if (entry is None or entry['status'] != 'dispatched' or
                entry['request_sha256'] != record['payload_sha256'] or entry.get('config') != record['config']):
            raise PermissionError('Dispatch requires the exact durable group reservation and dispatch intent')

    @property
    def allowed_allocations(self):
        names = tuple(a for values in PHASES.values() for a in values) if self.phase == 'all' else PHASES[self.phase]
        return tuple(a for a in names if a in self.plan['schedules'])


def _settle_finished(ledger, key, request, directory):
    """Recover completed evidence only; interrupted dispatch is never resent."""
    completed = directory / 'completed.json'
    if completed.exists():
        result = _read(completed)
        if result.get('request_sha256') != request['payload_sha256']:
            raise ValueError('Completed attempt payload changed')
        if (result.get('namespace') != request['namespace'] or
                result.get('first_attempt_primary') is not (request['namespace'] == 'first')):
            raise ValueError('Completed attempt replicate namespace or primary status changed')
        cost = usage_cost(request['config'], result.get('parsed', {}).get('usage') or {})
        try:
            ledger.settle(key, cost, evidence_sha256=digest(completed.read_bytes()))
        except ValueError:
            ledger.settle(key, None, evidence_sha256=digest(completed.read_bytes()))
            result['stop_required'] = True
        # A crash may occur after invoke saved completed.json and before the
        # executor applied its billing rule. Recover exactly the same stop/hold
        # decision without rewriting the original first-attempt evidence.
        if (PANEL[request['config']]['provider'] is not None and cost is None and
                result.get('parsed', {}).get('status') != 'unsupported_over_limit'):
            result['stop_required'] = True
        return result
    interrupted = directory / 'interrupted.json'
    directory.mkdir(parents=True, exist_ok=True)
    if not interrupted.exists():
        _exclusive(interrupted, {'key': key, 'status': 'interrupted_unknown', 'valid': False,
            'prediction': None, 'first_attempt_primary': request['namespace'] == 'first',
            'namespace': request['namespace'], 'payload_sha256': request['payload_sha256'],
            'inference_not_retried': True, 'unknown_charge_hold_retained': True})
    retained = _read(interrupted)
    if (retained.get('key') != key or retained.get('namespace') != request['namespace'] or
            retained.get('payload_sha256') != request['payload_sha256'] or
            retained.get('first_attempt_primary') is not (request['namespace'] == 'first')):
        raise ValueError('Interrupted attempt identity or replicate namespace changed')
    ledger.settle(key, None, evidence_sha256=digest(interrupted.read_bytes()))
    return {'parsed': {'status': 'interrupted_unknown', 'valid': False, 'prediction': None}, 'stop_required': True}


def execute(permit):
    """Single process owns dispatch; provider workers share one locked ledger."""
    from scripts.study_v7.routes import invoke
    execution = RAW / 'execution-v1'
    execution.mkdir(parents=True, exist_ok=True)
    process_lock = (execution / 'executor.lock').open('a+b')
    try:
        fcntl.flock(process_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        process_lock.close()
        raise PermissionError('Another v7 executor owns dispatch') from None
    stop_path = execution / _stop_policy(permit.receipt)[0]
    stop = threading.Event()
    paused = _paused_configurations(execution, permit.receipt)
    pause_lock = threading.Lock()
    runtime_cache = {}
    runtime_lock = threading.Lock()
    def guard():
        permit.check()
        _check_stops(execution, permit.receipt)
    try:
        guard()
        r = permit.receipt
        frozen = policy(r['historical_accounted_usd'], r['caps_usd'], r['incremental_caps_usd'],
            r['allocations_usd'], permit.manifest['historical_accounting'].get('evidence_sha256'))
        ledger = BudgetLedger(execution / 'accounting.jsonl', frozen, guard=guard, history_root=CANONICAL)
        permit.ledger = ledger
        for allocation in permit.allowed_allocations:
            groups = [{'group': g['group'], 'requests': [reservation(permit.plan['requests'][key])
                for key in g['request_keys']]} for g in permit.plan['schedules'].get(allocation, [])]
            ledger.register_schedule(allocation, groups)
        def attempt(key):
            if stop.is_set():
                return None
            request = permit.plan['requests'][key]
            if request['config'] == 'sol_subscription':
                paused.update(_paused_configurations(execution, permit.receipt))
            if request['config'] in paused:
                return None
            state = ledger.entry(key)['status']
            directory = execution / 'attempts' / key
            if state in ('settled', 'unknown_usage'):
                return None
            if state == 'dispatched':
                result = _settle_finished(ledger, key, request, directory)
            else:
                body = materialize(request, permit.rows)
                permit.check_request(request, body)
                ledger.mark_dispatched(key)
                # Local model loading/forward calls serialize with each other;
                # API workers still run concurrently under the same reservations.
                if request['config'] == 'protectai_local':
                    with runtime_lock:
                        result = invoke(request['config'], body, execution / 'attempts', key,
                            permit=permit, request_record=request, runtime_cache=runtime_cache)
                else:
                    result = invoke(request['config'], body, execution / 'attempts', key,
                        permit=permit, request_record=request, runtime_cache=runtime_cache)
                completed = directory / 'completed.json'
                cost = usage_cost(request['config'], result['parsed'].get('usage') or {})
                try:
                    ledger.settle(key, cost, evidence_sha256=digest(completed.read_bytes()))
                except ValueError:
                    ledger.settle(key, None, evidence_sha256=digest(completed.read_bytes()))
                    result['stop_required'] = True
                if (PANEL[request['config']]['provider'] is not None and cost is None and
                        result['parsed'].get('status') != 'unsupported_over_limit'):
                    result['stop_required'] = True
            if result.get('stop_required'):
                if request['config'] == 'sol_subscription':
                    with pause_lock:
                        paused.add('sol_subscription')
                        pause_path = execution / _pause_policy(permit.receipt)[0]
                        if not pause_path.exists():
                            _exclusive(pause_path, {'configuration': 'sol_subscription',
                                'reason': result['parsed'].get('status'), 'request_key': key,
                                'paid_fallback_forbidden': True, 'cheap_routes_continue': True,
                                'recorded_at': datetime.now(timezone.utc).isoformat()})
                else:
                    stop.set()
            return result
        for allocation in permit.allowed_allocations:
            allocation_configs = {permit.plan['requests'][key]['config']
                for g in permit.plan['schedules'].get(allocation, []) for key in g['request_keys']}
            if allocation_configs and allocation_configs <= paused:
                continue
            if allocation_configs and allocation_configs <= set((permit.manifest.get('route_validation') or {}).get('unsupported_configurations', {})):
                continue
            while not stop.is_set():
                if allocation_configs and allocation_configs <= paused:
                    break
                # An interrupted admitted group is resumed through never-sent
                # first attempts only; previous dispatch intents are not retries.
                progress = ledger.progress(allocation)
                previous = progress['previous_group']
                if progress['unfinished_request_keys']:
                    keys = [q['key'] for q in previous['requests']]
                else:
                    batch = ledger.reserve_next_group(allocation, admission_open=permit.admission_open())
                    if batch['status'] != 'admitted':
                        break
                    keys = batch['request_keys']
                with ThreadPoolExecutor(max_workers=4) as workers:
                    futures = [workers.submit(attempt, key) for key in keys]
                    for future in as_completed(futures):
                        future.result()
                if stop.is_set():
                    _exclusive(stop_path, {'status': 'stopped', 'reason': 'systemic_route_or_unknown_usage',
                        'allocation': allocation, 'first_attempts_preserved': True,
                        'recorded_at': datetime.now(timezone.utc).isoformat()})
                    break
            if stop.is_set():
                break
        return {'status': 'stopped' if stop.is_set() else 'bounded_phase_finished',
            'phase': permit.phase, 'paused_configurations': sorted(paused), 'accounting': ledger.snapshot()}
    finally:
        fcntl.flock(process_lock, fcntl.LOCK_UN)
        process_lock.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest', type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument('--authorization', type=Path, default=DEFAULT_AUTHORIZATION)
    parser.add_argument('--phase', choices=(*PHASES, 'all'), default='development')
    parser.add_argument('--execute', action='store_true', help='Still requires explicit bounded owner authorization')
    args = parser.parse_args(argv)
    if not args.execute:
        manifest, plan, rows = verify_manifest(args.manifest)
        print(json.dumps({'status': 'offline_only', 'experimental_inference_authorized': False,
            'counts': plan['counts'], 'selected_source_rows': len(rows),
            'plan_sha256': manifest['plan_sha256'], 'network_or_model_calls': 0}, indent=2))
        return
    permit = OwnerPermit(args.authorization, args.manifest, args.phase)
    result = execute(permit)
    print(json.dumps({'status': result['status'], 'phase': result['phase'],
        'paused_configurations': result.get('paused_configurations', []),
        'accounted_usd': result['accounting']['all_in_accounted_usd']}, indent=2))


if __name__ == '__main__':
    main()
