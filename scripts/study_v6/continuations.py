"""Explicit reviewed continuation of remaining frozen first attempts.

This module never sends a request and never retries a failed key. Preparation is
inert. Activation requires a committed sanitized receipt and a cooldown, journals
authorization durably, then archives the exact stop. Unknown-usage holds remain.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from email.utils import parsedate_to_datetime
import fcntl
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6 import plan
from scripts.study_v6.accounting import BudgetLedger
from scripts.study_v6.common import ROOT, canonical_bytes, sha256
from scripts.study_v6.evidence import immutable, load

VERSION = 'v6-remaining-first-attempt-continuation-1'
MINIMUM_COOLDOWN_SECONDS = 60


class ContinuationError(PermissionError):
    pass


def require(condition, message):
    if not condition:
        raise ContinuationError(message)


def _relative(path, root):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        raise ContinuationError('Continuation evidence must stay inside the project') from None


def _freeze(split, root, checker=None):
    if checker is not None:
        return checker(split, Path(root))
    require(Path(root).resolve() == ROOT.resolve(), 'A fixture project requires an explicit fixture freeze checker')
    from scripts.study_v6.freeze import verify
    return verify(split)


def _caps(policy):
    return {k: policy[k] for k in ('prior_accounted_usd', 'provider_caps_usd', 'v6_caps_usd', 'allocations_usd')}


def _validate_failure(record, request, entry, directory, stop_hash):
    parsed = record.get('result', {}).get('parsed', {})
    result = record.get('result', {})
    observation = result.get('observation', {})
    http = observation.get('http_status')
    interrupted = (parsed.get('status') == 'interrupted_unknown' and
                   result.get('interrupted_dispatch_intent_preserved') is True and
                   not result.get('reserved_raw_conflict_retained'))
    transport = (parsed.get('status') in ('http_error', 'transport_error') and
                 type(http) is int and http in (0, 200, 500, 502, 503, 504) and
                 (http not in (0, 200) or bool(observation.get('transport_exit_code'))) and
                 (http != 200 or parsed.get('status') == 'transport_error'))
    require(record.get('key') == request['key'] and record.get('attempt') == 0 and
        record.get('first_attempt_primary') is True and result.get('stop_required') is True and
        parsed.get('valid') is False and parsed.get('prediction') is None and parsed.get('score') is None and
        (transport or interrupted),
        'Only an invalid transient HTTP0/500/502/503/504 or HTTP200 transport-error first attempt permits continuation')
    require(entry['status'] in ('settled', 'unknown_usage'), 'Failure must be terminal; unknown usage stays reserved')
    require(not record.get('costs', {}).get('unexpected_pricing_tier') and not record.get('accounting_error'),
            'Pricing/accounting mismatches cannot permit transient continuation')
    folder = Path(directory)/'attempts'/request['key']
    if interrupted:
        require({'request.json', 'started.json'} <= set(result.get('raw_hashes', {})),
                'No-response interruption requires complete retained request/start provenance')
        require((folder/'request.json').read_bytes() == canonical_bytes(request['payload']),
                'Interrupted request differs from the frozen native request')
        started = load(folder/'started.json')
        from scripts.study_v6.routes import ROUTES
        require(started.get('config') == request['config'] and started.get('attempt_key') == request['key'] and
                started.get('payload_sha256') == request['request_sha256'] and started.get('route') == ROUTES[request['config']],
                'Interrupted native route/request provenance is incomplete')
        require(not (folder/'completed.json').exists() and all(not (folder/name).exists() or not (folder/name).read_bytes()
                for name in ('response.raw','response.partial','response-headers.partial')),
                'Only a no-response interruption can continue; partial native streams require separate resolution')
    # A service can return a nonstandard status for auth/quota/model failures.
    # Refuse these explicit error codes; an operator cannot approve around them.
    raw = Path(directory) / 'attempts' / request['key'] / 'response.raw'
    body = raw.read_text().lower() if raw.exists() else ''
    forbidden = ('quota', 'billing', 'payment_required', 'invalid_api_key', 'authentication',
                 'model_not_found', 'unsupported_model', 'price_mismatch', 'evidence_corrupt')
    require(not any(code in body for code in forbidden), 'Auth/model/price/evidence/quota failures are outside continuation scope')
    from scripts.study_v6.verify_execution import _audit_attempt
    reparsed, retained = _audit_attempt(request, entry, Path(directory), stop_hash)
    require(retained == record and reparsed == parsed, 'Transient failure failed independent raw verification')


def _remaining(requests, prefix):
    statuses = {}
    for line in prefix.splitlines():
        event = json.loads(line)
        kind, data = event['kind'], event['data']
        if kind == 'reserve':
            for row in data['new_requests']:
                statuses[row['key']] = 'reserved'
        elif kind == 'dispatch':
            statuses[data['key']] = 'dispatched'
        elif kind == 'settle':
            statuses[data['key']] = 'terminal'
        elif kind == 'cancel_reserved':
            statuses[data['key']] = 'cancelled'
    require(not any(statuses.get(k) == 'dispatched' for k in requests),
            'Unresolved dispatch intents must be terminalized before preparing continuation')
    require(not any(statuses.get(k) == 'cancelled' for k in requests),
            'A positively closed/cancelled cohort cannot resume under this continuation')
    return sorted(k for k in requests if statuses.get(k) != 'terminal')


def _receipt(manifest, digest, relative_manifest):
    return {'version': VERSION, 'kind': 'reviewed_continuation_of_remaining_frozen_first_attempts',
        'manifest_path': relative_manifest, 'manifest_sha256': digest,
        'stop_sha256': manifest['stop_sha256'], 'failure_evidence_sha256': manifest['failure_evidence_sha256'],
        'freeze_sha256': manifest['freeze_sha256'], 'frozen_plan_sha256': manifest['frozen_plan_sha256'],
        'remaining_request_scope_count': len(manifest['remaining_request_keys']),
        'not_before_epoch': manifest['not_before_epoch'], 'reason': manifest['reason'],
        'caps_unchanged': True, 'failed_attempt_retried': False, 'predictions_used_for_extension': False}


def _receipt_path(root, digest):
    return Path(root) / 'results/study-v6-execution/continuations' / (digest + '.json')


def _committed(path, root):
    relative = _relative(path, root)
    value = subprocess.run(['git', 'show', 'HEAD:' + relative], cwd=root, capture_output=True)
    require(value.returncode == 0 and value.stdout == Path(path).read_bytes(),
            'The exact sanitized continuation receipt must be committed before activation')


def _required_wait(record, now, minimum):
    require(type(minimum) in (int,float) and math.isfinite(minimum) and minimum >= MINIMUM_COOLDOWN_SECONDS,
            'Cooldown cannot be shorter than the frozen minimum')
    value = (record['result'].get('observation', {}).get('response_headers') or {}).get('retry-after')
    wait = float(minimum)
    if value:
        try:
            wait = max(wait, float(value))
        except ValueError:
            try:
                wait = max(wait, parsedate_to_datetime(value).timestamp()-now)
            except (ValueError, TypeError, OverflowError):
                raise ContinuationError('Unparseable provider cooldown must be resolved before continuation') from None
    require(math.isfinite(wait), 'Invalid provider cooldown')
    return wait


def prepare(source_stop=None, reason=None, *, directory=plan.DEST, project_root=ROOT,
            cooldown_seconds=MINIMUM_COOLDOWN_SECONDS, now_epoch=None, freeze_checker=None):
    """Prepare an inert raw manifest and sanitized receipt; never activate or send."""
    root, directory = Path(project_root), Path(directory)
    source_stop = Path(source_stop) if source_stop is not None else directory / 'STOP.json'
    require(source_stop.resolve() == (directory/'STOP.json').resolve() and source_stop.is_file(),
            'Prepare requires the current exact active stop')
    require(isinstance(reason, str) and reason.strip(), 'A concrete operational review reason is required')
    stop = load(source_stop)
    key = stop.get('request_key')
    ledger_path = directory / 'budget.jsonl'
    ledger = BudgetLedger(ledger_path).snapshot()
    require(key in ledger['entries'], 'Active stop lacks a reserved first-attempt request')
    entry = ledger['entries'][key]
    record_path = directory/'attempts'/key/'execution-record.json'
    require(record_path.is_file(), 'A terminal retained failure record is required')
    record = load(record_path)
    split = record['split']
    receipt, frozen = _freeze(split, root, freeze_checker)
    requests = {r['key']: r for r in frozen['requests']}
    require(key in requests, 'Failure is outside the committed frozen first-attempt plan')
    stop_hash = sha256(source_stop.read_bytes())
    _validate_failure(record, requests[key], entry, directory, stop_hash)
    require(not any(x in str(stop.get('reason','')).lower() for x in
        ('accounting','price','quota','model','auth','evidence','corrupt','missing','runtime')),
        'Source stop describes an excluded systemic failure')
    require(not any(e['status'] == 'cancelled_unsent' and e['evidence_sha256'] == stop_hash
                    for e in ledger['entries'].values()), 'This stop already positively closed its remaining cohort')
    prefix = ledger_path.read_bytes()
    remaining = _remaining(requests, prefix)
    require(key not in remaining, 'Failed first attempt cannot enter continuation request scope')
    now = time.time() if now_epoch is None else now_epoch
    require(type(now) in (int,float) and math.isfinite(now) and now > 0, 'Invalid continuation preparation clock')
    wait = _required_wait(record, now, cooldown_seconds)
    freeze_path = root/'results/study-v6-execution'/(split+'-freeze-v1.json')
    plan_path = root/receipt['raw_plan']
    manifest = {'version': VERSION, 'split': split, 'failed_key': key,
        'failure_evidence_sha256': sha256(record_path.read_bytes()), 'stop_sha256': stop_hash,
        'source_stop_path': _relative(source_stop, root),
        'freeze_path': _relative(freeze_path, root), 'freeze_sha256': sha256(freeze_path.read_bytes()),
        'frozen_plan_path': _relative(plan_path, root), 'frozen_plan_sha256': sha256(plan_path.read_bytes()),
        'remaining_request_keys': remaining, 'remaining_request_keys_sha256': sha256(canonical_bytes(remaining)),
        'unchanged_caps': _caps(ledger['policy']), 'ledger_prefix_bytes': len(prefix),
        'ledger_prefix_sha256': sha256(prefix), 'prepared_at_epoch': now,
        'not_before_epoch': now+wait, 'minimum_cooldown_seconds': MINIMUM_COOLDOWN_SECONDS,
        'requested_cooldown_seconds': cooldown_seconds,
        'reason': reason.strip(), 'failed_key_never_retried': True, 'new_prediction_recovery': False}
    manifest['eligibility_basis'] = ('preserved_dispatch_intent_with_no_response_received' if
        record['result'].get('interrupted_dispatch_intent_preserved') else 'retained_transient_http_transport_failure')
    body = canonical_bytes(manifest)+b'\n'
    digest = sha256(body)
    path = directory/'continuations'/(digest+'.json')
    immutable(path, body)
    tracked = _receipt_path(root, digest)
    immutable(tracked, _receipt(manifest, digest, _relative(path, root)))
    return {'manifest_path': str(path), 'receipt_path': str(tracked), 'manifest_sha256': digest,
            'remaining_request_scope_count': len(remaining), 'not_before_epoch': manifest['not_before_epoch'],
            'activation_requires_committed_receipt': True}


def validate_link(manifest_path, *, directory=plan.DEST, project_root=ROOT,
                  freeze_checker=None, require_archive=False):
    """Read-only validation shared by activation, resumption and independent audit."""
    root, directory, path = Path(project_root), Path(directory), Path(manifest_path)
    manifest = load(path)
    digest = sha256(path.read_bytes())
    require(manifest['version'] == VERSION and manifest['failed_key_never_retried'] is True and
            manifest['new_prediction_recovery'] is False, 'Unknown continuation or retry semantics')
    require(path.resolve() == (directory/'continuations'/(digest+'.json')).resolve(),
            'Continuation manifest path does not bind its exact content hash')
    receipt_path = _receipt_path(root, digest)
    require(load(receipt_path) == _receipt(manifest, digest, _relative(path, root)), 'Continuation receipt differs from manifest')
    _committed(receipt_path, root)
    freeze_receipt, frozen = _freeze(manifest['split'], root, freeze_checker)
    require(sha256((root/manifest['freeze_path']).read_bytes()) == manifest['freeze_sha256'] and
        sha256((root/manifest['frozen_plan_path']).read_bytes()) == manifest['frozen_plan_sha256'] and
        _relative(root/freeze_receipt['raw_plan'], root) == manifest['frozen_plan_path'],
        'Continuation changes its original committed freeze or exact requests')
    ledger_path = directory/'budget.jsonl'
    ledger = BudgetLedger(ledger_path).snapshot()
    require(_caps(ledger['policy']) == manifest['unchanged_caps'], 'Continuation changed provider caps/allocations/accounting')
    prefix = ledger_path.read_bytes()[:manifest['ledger_prefix_bytes']]
    require(len(prefix) == manifest['ledger_prefix_bytes'] and sha256(prefix) == manifest['ledger_prefix_sha256'],
            'Continuation preparation journal prefix changed')
    requests = {r['key']: r for r in frozen['requests']}
    require(_remaining(requests, prefix) == manifest['remaining_request_keys'] and
        sha256(canonical_bytes(manifest['remaining_request_keys'])) == manifest['remaining_request_keys_sha256'] and
        manifest['failed_key'] not in manifest['remaining_request_keys'], 'Continuation changed its exact remaining first-attempt scope')
    key = manifest['failed_key']
    require(key in requests and key in ledger['entries'], 'Continuation failure is not a frozen reserved request')
    record_path = directory/'attempts'/key/'execution-record.json'
    require(sha256(record_path.read_bytes()) == manifest['failure_evidence_sha256'], 'Reviewed transient failure evidence changed')
    archived = directory/'stops'/(manifest['stop_sha256']+'.json')
    active = directory/'STOP.json'
    stop_path = archived if archived.exists() else active
    require(stop_path.is_file() and sha256(stop_path.read_bytes()) == manifest['stop_sha256'], 'Reviewed exact stop is not retained')
    require(not require_archive or archived.is_file(), 'Journaled continuation has not finished archiving its exact stop')
    require(load(stop_path).get('request_key') == key and not any(x in str(load(stop_path).get('reason','')).lower()
        for x in ('accounting','price','quota','model','auth','evidence','corrupt','missing','runtime')),
        'Continuation source stop changed its request or excluded failure class')
    record = load(record_path)
    _validate_failure(record, requests[key], ledger['entries'][key], directory, manifest['stop_sha256'])
    require(manifest['not_before_epoch'] >= manifest['prepared_at_epoch']+
        _required_wait(record, manifest['prepared_at_epoch'], manifest['requested_cooldown_seconds']),
        'Manifest weakened a provider-requested or reviewed cooldown')
    return manifest, ledger, receipt_path


@contextmanager
def _executor_lock(directory):
    with (Path(directory)/'sole-executor.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def _sync_directory(path):
    descriptor = os.open(Path(path), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def activate(manifest_path, *, directory=plan.DEST, project_root=ROOT,
             now_epoch=None, freeze_checker=None, after_journal=None):
    """Explicit activation only. ``after_journal`` is a crash-injection fixture."""
    root, directory, path = Path(project_root), Path(directory), Path(manifest_path)
    with _executor_lock(directory):
        manifest, snapshot, tracked = validate_link(path, directory=directory, project_root=root, freeze_checker=freeze_checker)
        now = time.time() if now_epoch is None else now_epoch
        require(type(now) in (int,float) and math.isfinite(now) and now > 0, 'Invalid continuation activation clock')
        require(now >= manifest['not_before_epoch'], 'Reviewed provider cooldown is not complete')
        require(manifest['not_before_epoch'] >= manifest['prepared_at_epoch']+MINIMUM_COOLDOWN_SECONDS,
                'Manifest weakened the minimum cooldown')
        key, digest = manifest['failed_key'], sha256(path.read_bytes())
        previous = snapshot['continuations'].get(key)
        if previous is None:
            require(sha256((directory/'budget.jsonl').read_bytes()) == manifest['ledger_prefix_sha256'],
                    'Budget journal changed since preparation; preserve this draft and prepare a fresh review')
        else:
            require(previous['manifest_sha256'] == digest, 'A different continuation already owns this failed first attempt')
        ledger = BudgetLedger(directory/'budget.jsonl', history_root=root)
        event = ledger.record_continuation(key, failure_record=load(directory/'attempts'/key/'execution-record.json'),
            failure_evidence_sha256=manifest['failure_evidence_sha256'], stop_sha256=manifest['stop_sha256'],
            manifest_sha256=digest, manifest_path=_relative(path, root),
            receipt_path=_relative(tracked, root), receipt_sha256=sha256(tracked.read_bytes()), activated_at_epoch=now)
        if after_journal is not None:
            after_journal()
        active, archived = directory/'STOP.json', directory/'stops'/(manifest['stop_sha256']+'.json')
        archived.parent.mkdir(parents=True, exist_ok=True)
        if archived.exists():
            require(sha256(archived.read_bytes()) == manifest['stop_sha256'], 'Archived stop changed')
        if active.exists():
            require(sha256(active.read_bytes()) == manifest['stop_sha256'], 'A different active stop cannot be cleared')
            os.replace(active, archived)
            _sync_directory(directory)
            _sync_directory(archived.parent)
        require(archived.exists(), 'Activation must preserve the exact archived stop')
        return {'activated': True, 'manifest_sha256': digest, 'failed_key_retried': False,
                'remaining_request_scope_count': len(manifest['remaining_request_keys']),
                'activation_epoch': event['activated_at_epoch']}


def approved_failure(key, ledger, directory=plan.DEST, project_root=ROOT, *, freeze_checker=None):
    """True only for reading/skipping an approved old failure; never permission to send it."""
    snapshot = ledger.snapshot() if isinstance(ledger, BudgetLedger) else ledger
    event = snapshot.get('continuations', {}).get(key)
    if event is None:
        return False
    manifest, current, tracked = validate_link(Path(project_root)/event['manifest_path'],
        directory=directory, project_root=project_root, freeze_checker=freeze_checker, require_archive=True)
    require(event == current['continuations'].get(key) and event['failed_key'] == manifest['failed_key'] == key and
        event['manifest_sha256'] == sha256((Path(project_root)/event['manifest_path']).read_bytes()) and
        event['failure_evidence_sha256'] == manifest['failure_evidence_sha256'] and
        event['stop_sha256'] == manifest['stop_sha256'] and
        event['receipt_path'] == _relative(tracked, project_root) and
        event['receipt_sha256'] == sha256(tracked.read_bytes()) and
        event['activated_at_epoch'] >= manifest['not_before_epoch'], 'Continuation event/evidence/cooldown mismatch')
    return True


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest='action', required=True)
    p = sub.add_parser('prepare')
    p.add_argument('--reason', required=True)
    p.add_argument('--source-stop', type=Path)
    p = sub.add_parser('activate')
    p.add_argument('manifest', type=Path)
    args = parser.parse_args()
    result = prepare(args.source_stop, args.reason) if args.action == 'prepare' else activate(args.manifest)
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
