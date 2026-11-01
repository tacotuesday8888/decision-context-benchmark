"""One explicit pre-confirmation development capacity amendment, v6.0.1.

The original development freeze, every existing first attempt, exact payloads,
source cohort, journal prefix and systemic stop remain immutable. This module
never calls a model and never retries a key. The old HTTP413 remains http_error.
Activation journals a separate, narrowly proved capacity continuation before
archiving the original STOP. The transient-continuation policy is unchanged.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import fcntl
import json
import math
import os
from pathlib import Path
import re
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import ROOT, canonical_bytes, sha256
from scripts.study_v6 import plan
from scripts.study_v6.accounting import (BudgetLedger, money, NIMBLE_LEGACY_CAPACITY_BODY,
                                         NIMBLE_LEGACY_CAPACITY_SHA256)
from scripts.study_v6.evidence import immutable, load

VERSION = 'dev-amendment-v6.0.1'
BASENAME = 'development-amendment-v6.0.1.json'
EXPECTED_REQUESTS = 460
EXPECTED_PRESERVED_ATTEMPTS = 407
EXPECTED_REMAINING_REQUESTS = 53
ADDITIONS = {'scripts/study_v6/development_amendment.py',
             'tests/study_v6/test_development_amendment.py'}
ALLOWED_CHANGES = ADDITIONS | {
    'scripts/study_v6/freeze.py', 'scripts/study_v6/run.py',
    'scripts/study_v6/accounting.py', 'scripts/study_v6/verify_execution.py',
    'scripts/study_v6/routes.py', 'tests/study_v6/test_freeze.py',
    'tests/study_v6/test_runner.py', 'tests/study_v6/test_accounting.py',
    'tests/study_v6/test_execution_verification.py', 'tests/study_v6/test_routes.py',
}
STATIC_FILES = {
    'static-disassembly.txt': 'b18c4a4fec3c96486e875a949da32d92bd6d922a1d45942fd0faea64897c66e1',
    'static-reconstruction.json': 'bbe663e57c3ccefdb1a8536d9a057178de56eea2304c2ba03b66c1ef911a9b03',
    'plan-capacity-counts.json': '7eaeddd13f4f14ba3cd7669153366e35613c267c3564028e1049f7cd4792e83b',
}
TRUSTED_BINARY = Path('/Applications/Ollama.app/Contents/Resources/ollama')
TRUSTED_BINARY_SHA256 = '270089e59e1d411ac4d0987154b4e95f48b29a81c9d274833c6b766d6df88300'
TRUSTED_BINARY_BYTES = 77644752


class AmendmentError(PermissionError):
    pass


def require(value, message):
    if not value:
        raise AmendmentError(message)


def _relative(path, root):
    try:
        return str(Path(path).resolve().relative_to(Path(root).resolve()))
    except ValueError:
        raise AmendmentError('Amendment evidence must remain inside the project') from None


def _path(root, relative):
    require(isinstance(relative, str) and not Path(relative).is_absolute() and '..' not in Path(relative).parts,
            'Unsafe amendment evidence path')
    path = Path(root) / relative
    _relative(path, root)
    return path


def _paths(root, directory):
    root, directory = Path(root), Path(directory)
    _relative(directory, root)
    results = root / 'results/study-v6-execution'
    return directory / BASENAME, results / BASENAME, results / 'development-freeze-v1.json'


def _hashes(root):
    # Import only the pure inventory function; never call freeze.verify here.
    from scripts.study_v6.freeze import scientific_hashes
    return scientific_hashes()


def _commit(root, hashes):
    for relative, expected in hashes.items():
        result = subprocess.run(['git', 'show', 'HEAD:' + relative], cwd=root, capture_output=True)
        require(result.returncode == 0 and sha256(result.stdout) == expected,
                'Exact amendment scientific code/receipt must be committed: ' + relative)
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()


def _at_commit(root, commit, hashes):
    require(isinstance(commit, str) and re.fullmatch(r'[0-9a-f]{40,64}', commit),
            'An exact immutable Git commit identity is required')
    for relative, expected in hashes.items():
        result = subprocess.run(['git', 'show', commit + ':' + relative], cwd=root, capture_output=True)
        require(result.returncode == 0 and sha256(result.stdout) == expected,
                'Committed amendment lineage source cannot be recovered unchanged')


def _worktree(root, hashes):
    for relative, expected in hashes.items():
        require(sha256(_path(root, relative).read_bytes()) == expected,
                'Actual scientific worktree differs from supplied current hashes')


def _caps(policy):
    return {key: policy[key] for key in
            ('prior_accounted_usd', 'provider_caps_usd', 'v6_caps_usd', 'allocations_usd')}


def _replacements(original, current):
    require(not (set(original) - set(current)), 'Amendment cannot remove scientific files')
    added = set(current) - set(original)
    changed = {name for name in current if name not in original or current[name] != original[name]}
    require(added == ADDITIONS and changed <= ALLOWED_CHANGES,
            'Scientific changes/additions exceed the explicit operational amendment allowlist')
    require(ADDITIONS <= changed, 'Amendment implementation and fixtures must be explicit additions')
    return {name: current[name] for name in sorted(changed)}


def _original(root, directory, supplied=None, *, require_committed=True):
    _, _, path = _paths(root, directory)
    original = load(path)
    require(original.get('split') == 'development', 'Preserved original development freeze required')
    if supplied is not None:
        require(original == supplied, 'Supplied development freeze differs from original retained bytes')
    for name, expected in original['evidence'].items():
        require(sha256(_path(root, name).read_bytes()) == expected, 'Original frozen evidence changed: ' + name)
    if require_committed:
        _commit(root, {_relative(path, root): sha256(path.read_bytes())})
        _at_commit(root, original['code_commit'], original['scientific_hashes'])
    raw_plan = _path(root, original['raw_plan'])
    require(original['evidence'].get(original['raw_plan']) == sha256(raw_plan.read_bytes()),
            'Original raw development plan is not hash-bound')
    frozen = load(raw_plan)
    requests = {r['key']: r for r in frozen['requests']}
    require(len(requests) == len(frozen['requests']) == EXPECTED_REQUESTS,
            'The original complete development request set must remain intact')
    require(all(r['split'] == 'development' and r['inference_eligible'] is True for r in requests.values()),
            'Only the original eligible development first attempts can be amended')
    return original, frozen, requests, path, raw_plan


def _journal_prefix(prefix, requests):
    state = {}
    for line in prefix.splitlines():
        event = json.loads(line)
        kind, data = event['kind'], event['data']
        if kind == 'reserve':
            for request in data['new_requests']:
                require(request['key'] in requests, 'Pre-amendment journal contains a nondevelopment request')
                state[request['key']] = 'reserved'
        elif kind == 'dispatch':
            state[data['key']] = 'dispatched'
        elif kind == 'settle':
            state[data['key']] = 'terminal'
        elif kind == 'cancel_reserved':
            state[data['key']] = 'cancelled'
        elif kind == 'development_capacity_continuation':
            raise AmendmentError('Capacity amendment preparation cannot inherit an earlier capacity activation')
    require(all(value == 'terminal' for value in state.values()),
            'All original dispatched attempts must be terminal; no cancellations or pending holds')
    require(len(state) == EXPECTED_PRESERVED_ATTEMPTS, 'Unexpected preserved development attempt count')
    remaining = sorted(set(requests) - set(state))
    require(len(remaining) == EXPECTED_REMAINING_REQUESTS, 'Exact remaining development first-attempt scope changed')
    return sorted(state), remaining


def _attempt_inventory(root, directory, requests, ledger, keys):
    from scripts.study_v6.verify_execution import _audit_attempt
    inventory = []
    for key in keys:
        require(key in ledger['entries'], 'Original journal entry disappeared')
        _, _ = _audit_attempt(requests[key], ledger['entries'][key], directory, set())
        folder = Path(directory) / 'attempts' / key
        inventory.append({'key': key, 'files': {_relative(path, root): sha256(path.read_bytes())
            for path in sorted(folder.iterdir()) if path.is_file()}})
    return inventory


def _failure(root, directory, requests, ledger, key):
    require(key in requests and key in ledger['entries'], 'Capacity failure is not an original reserved first attempt')
    request, entry = requests[key], ledger['entries'][key]
    path = Path(directory) / 'attempts' / key / 'execution-record.json'
    record = load(path)
    result = record.get('result', {})
    parsed, observation = result.get('parsed', {}), result.get('observation', {})
    body = (path.parent / 'response.raw').read_bytes()
    from scripts.study_v6.routes import native_byte_coverage
    byte_gate = native_byte_coverage(request['payload'])
    require(byte_gate['supported'] is False and byte_gate['limit_bytes'] == 65536,
            'Historical failed payload must independently exceed the exact pinned native byte limit')
    require(request['config'] == 'nimble_local' and request['split'] == 'development' and request['provider'] is None,
            'Only the historical local native Nimble development capacity failure is eligible')
    require(record.get('key') == key and record.get('attempt') == 0 and record.get('first_attempt_primary') is True and
        record.get('config') == 'nimble_local' and record.get('split') == 'development' and
        result.get('parser_version') is None and parsed.get('status') == 'http_error' and
        parsed.get('valid') is False and parsed.get('prediction') is None and parsed.get('score') is None and
        result.get('stop_required') is True and observation.get('http_status') == 413 and
        observation.get('transport_exit_code') == 0 and result.get('access_route') == 'local' and
        result.get('paid_request') is False and body == NIMBLE_LEGACY_CAPACITY_BODY and
        result.get('raw_hashes', {}).get('response.raw') == NIMBLE_LEGACY_CAPACITY_SHA256,
        'Only the exact retained legacy Nimble HTTP413 byte-limit response permits this amendment')
    require(entry['status'] == 'settled' and entry['provider'] is None and
        entry['evidence_sha256'] == sha256(path.read_bytes()) and
        all(money(entry[name]) == 0 for name in ('actual_usd', 'accounted_usd', 'reserved_usd')),
        'The historical local failure must retain its exact settled zero accounting')
    return record, path


def _gate_receipts(root, directory, current, *, require_committed=True):
    result = Path(root) / 'results/study-v6-execution'
    offline_path, audit_path = result / 'offline-verification-v4.json', result / 'prefreeze-audit-v3.json'
    offline, audit = load(offline_path), load(audit_path)
    require(offline.get('checks_passed') is True and offline.get('scientific_hashes') == current,
            'Current exact scientific code lacks complete offline-v4 verification')
    require(audit.get('checks_passed') is True and audit.get('new_model_calls') == 0 and
        audit.get('model_outputs_inspected') is False and audit.get('checks') and all(v is True for v in audit['checks'].values()),
        'Independent prefreeze-v3 audit is incomplete or inspected experimental outcomes')
    expected_plan = Path(directory) / 'intended-plan.json'
    require(audit.get('inputs', {}).get('intended_plan', {}).get('path') == _relative(expected_plan, root),
            'Independent amendment audit must bind the preserved intended plan')
    for receipt in audit['inputs'].values():
        require(sha256(_path(root, receipt['path']).read_bytes()) == receipt['sha256'],
                'Independent amendment audit has a stale input')
    paths = {str(path.relative_to(root)): sha256(path.read_bytes()) for path in (offline_path, audit_path)}
    if require_committed:
        _commit(root, paths)
    return paths


def _operational_evidence(root, directory, *, require_committed=True):
    doc = Path(root) / 'docs/study-v6-execution/AMENDMENT-v6.0.1.md'
    require(doc.is_file(), 'The explicit nonfrozen operational amendment document is required')
    result = {'amendment_doc': {'path': _relative(doc, root), 'sha256': sha256(doc.read_bytes())}, 'static_files': {}}
    folder = Path(directory) / 'amendment-byte-limit-evidence-v1'
    for name, expected in STATIC_FILES.items():
        path = folder / name
        require(path.is_file() and sha256(path.read_bytes()) == expected, 'Pinned static native-byte evidence changed')
        result['static_files'][name] = {'path': _relative(path, root), 'sha256': expected}
    reconstruction = load(folder / 'static-reconstruction.json')
    binary = reconstruction.get('binary', {})
    require(reconstruction.get('schema') == 'nimble-native-byte-limit-static-v1' and
        binary.get('real_path') == str(TRUSTED_BINARY) and binary.get('sha256') == TRUSTED_BINARY_SHA256 and
        binary.get('bytes') == TRUSTED_BINARY_BYTES,
        'Static byte rule is not bound to the explicitly trusted pinned Ollama binary')
    # This is the sole explicit outside-project file read. Never follow a path
    # supplied by the raw amendment/receipt; no executable bytes are copied.
    require(TRUSTED_BINARY.is_file() and TRUSTED_BINARY.stat().st_size == TRUSTED_BINARY_BYTES and
        sha256(TRUSTED_BINARY.read_bytes()) == TRUSTED_BINARY_SHA256, 'Pinned native runtime binary changed')
    result['trusted_local_binary'] = {'path': str(TRUSTED_BINARY), 'sha256': TRUSTED_BINARY_SHA256,
                                      'bytes': TRUSTED_BINARY_BYTES}
    if require_committed:
        _commit(root, {_relative(doc, root): result['amendment_doc']['sha256']})
    return result


def _receipt(manifest, manifest_hash, relative):
    return {'version': VERSION, 'kind': 'reviewed_preconfirmation_development_capacity_amendment',
        'manifest_path': relative, 'manifest_sha256': manifest_hash,
        'base_freeze_sha256': manifest['base_freeze_sha256'],
        'base_frozen_plan_sha256': manifest['base_frozen_plan_sha256'],
        'stop_sha256': manifest['stop_sha256'], 'failure_evidence_sha256': manifest['failure_evidence_sha256'],
        'raw_response_sha256': manifest['raw_response_sha256'],
        'original_request_count': manifest['original_request_count'],
        'preserved_first_attempt_count': manifest['preserved_first_attempt_count'],
        'remaining_first_attempt_count': len(manifest['remaining_request_keys']),
        'replacement_hashes': manifest['replacement_hashes'], 'gate_receipts': manifest['gate_receipts'],
        'operational_evidence': manifest['operational_evidence'],
        'code_commit': manifest['code_commit'], 'caps_unchanged': True, 'failed_key_retried': False,
        'original_http_error_preserved': True, 'prompts_models_labels_groups_splits_unchanged': True,
        'predictions_used_for_extension': False, 'new_model_calls': 0,
        'reason': 'Exact native Nimble development HTTP413 byte rejection; prospectively gate unchanged requests and continue only the original unsent first attempts.'}


def prepare(*, project_root=ROOT, directory=plan.DEST, current_hashes=None,
            require_committed=True, now_epoch=None):
    """Prepare inert immutable lineage. No activation, stop removal or inference."""
    root, directory = Path(project_root).resolve(), Path(directory).resolve()
    if root == ROOT.resolve():
        require(require_committed, 'Production amendment preparation requires committed scientific code')
    raw_path, tracked, base_path = _paths(root, directory)
    require(not (root / 'results/study-v6-execution/confirmation-freeze-v1.json').exists(),
            'This operational amendment must precede all confirmation freezing/execution')
    original, frozen, requests, _, raw_plan = _original(root, directory, require_committed=require_committed)
    current = current_hashes if current_hashes is not None else _hashes(root)
    replacements = _replacements(original['scientific_hashes'], current)
    _worktree(root, current)
    head = _commit(root, current) if require_committed else 'fixture-uncommitted'
    gates = _gate_receipts(root, directory, current, require_committed=require_committed)
    operational = _operational_evidence(root, directory, require_committed=require_committed)
    ledger = BudgetLedger(directory / 'budget.jsonl').snapshot()
    require(not ledger.get('development_amendments'), 'A capacity amendment already owns this development lineage')
    prefix = (directory / 'budget.jsonl').read_bytes()
    existing, remaining = _journal_prefix(prefix, requests)
    require(set(ledger['entries']) == set(existing), 'Live development journal differs from exact terminal prefix')
    stop_path = directory / 'STOP.json'
    require(stop_path.is_file(), 'The original active systemic STOP must be retained')
    stop = load(stop_path)
    key = stop.get('request_key')
    require(key in existing and key not in remaining, 'Historical failed key cannot enter the remaining scope')
    record, record_path = _failure(root, directory, requests, ledger, key)
    inventory = _attempt_inventory(root, directory, requests, ledger, existing)
    require({p.name for p in (directory / 'attempts').iterdir() if p.is_dir()} == set(existing),
            'Unplanned or unjournaled original attempt directory exists')
    now = time.time() if now_epoch is None else now_epoch
    require(type(now) in (int, float) and math.isfinite(now) and now > 0, 'Explicit finite amendment preparation time required')
    manifest = {'version': VERSION, 'split': 'development', 'code_commit': head,
        'base_freeze_path': _relative(base_path, root), 'base_freeze_sha256': sha256(base_path.read_bytes()),
        'base_frozen_plan_path': _relative(raw_plan, root), 'base_frozen_plan_sha256': sha256(raw_plan.read_bytes()),
        'base_scientific_hashes': original['scientific_hashes'], 'replacement_hashes': replacements,
        'gate_receipts': gates, 'operational_evidence': operational,
        'failed_key': key, 'failure_evidence_sha256': sha256(record_path.read_bytes()),
        'raw_response_sha256': NIMBLE_LEGACY_CAPACITY_SHA256,
        'stop_sha256': sha256(stop_path.read_bytes()), 'original_request_count': len(requests),
        'preserved_first_attempt_count': len(existing), 'preserved_attempts': inventory,
        'remaining_request_keys': remaining, 'remaining_request_keys_sha256': sha256(canonical_bytes(remaining)),
        'unchanged_caps': _caps(ledger['policy']), 'ledger_prefix_bytes': len(prefix),
        'ledger_prefix_sha256': sha256(prefix), 'prepared_at_epoch': now, 'not_before_epoch': now,
        'failed_key_never_retried': True, 'original_http_error_preserved': True,
        'predictions_used_for_extension': False, 'new_prediction_recovery': False}
    digest = immutable(raw_path, manifest)
    immutable(tracked, _receipt(manifest, digest, _relative(raw_path, root)))
    return {'manifest_path': str(raw_path), 'receipt_path': str(tracked), 'manifest_sha256': digest,
            'remaining_request_scope_count': len(remaining), 'activation_requires_committed_receipt': True}


def verify(base_freeze=None, current_hashes=None, require_committed=True, *,
           project_root=ROOT, directory=plan.DEST):
    """Validate the exact amendment lineage without calling freeze.verify."""
    root, directory = Path(project_root).resolve(), Path(directory).resolve()
    raw_path, tracked, _ = _paths(root, directory)
    if not raw_path.exists() and not tracked.exists():
        return None
    require(raw_path.is_file() and tracked.is_file(), 'Incomplete amendment manifest/receipt pair')
    manifest = load(raw_path)
    require(manifest.get('version') == VERSION and manifest.get('split') == 'development' and
        manifest.get('failed_key_never_retried') is True and manifest.get('original_http_error_preserved') is True and
        manifest.get('predictions_used_for_extension') is False and manifest.get('new_prediction_recovery') is False,
        'Unknown development amendment semantics')
    require(load(tracked) == _receipt(manifest, sha256(raw_path.read_bytes()), _relative(raw_path, root)),
            'Sanitized committed amendment receipt differs from raw lineage')
    original, frozen, requests, base_path, raw_plan = _original(root, directory, base_freeze, require_committed=require_committed)
    require(manifest['base_freeze_path'] == _relative(base_path, root) and
        manifest['base_freeze_sha256'] == sha256(base_path.read_bytes()) and
        manifest['base_frozen_plan_path'] == _relative(raw_plan, root) and
        manifest['base_frozen_plan_sha256'] == sha256(raw_plan.read_bytes()) and
        manifest['base_scientific_hashes'] == original['scientific_hashes'], 'Original development lineage changed')
    current = current_hashes if current_hashes is not None else _hashes(root)
    require(_replacements(original['scientific_hashes'], current) == manifest['replacement_hashes'],
            'Amendment scientific replacement hashes changed')
    _worktree(root, current)
    gates = _gate_receipts(root, directory, current, require_committed=require_committed)
    require(gates == manifest['gate_receipts'], 'Amendment verification receipts changed')
    require(_operational_evidence(root, directory, require_committed=require_committed) == manifest['operational_evidence'],
            'Operational amendment document/static evidence changed')
    if require_committed:
        _commit(root, current)
        _at_commit(root, manifest['code_commit'], current)
        _commit(root, {_relative(tracked, root): sha256(tracked.read_bytes())})
    ledger = BudgetLedger(directory / 'budget.jsonl').snapshot()
    require(_caps(ledger['policy']) == manifest['unchanged_caps'], 'Amendment changed cumulative caps or inherited accounting')
    journal = (directory / 'budget.jsonl').read_bytes()
    size = manifest['ledger_prefix_bytes']
    require(type(size) is int and len(journal) >= size and sha256(journal[:size]) == manifest['ledger_prefix_sha256'],
            'Original append-only development journal prefix changed')
    existing, remaining = _journal_prefix(journal[:size], requests)
    require(remaining == manifest['remaining_request_keys'] and
        sha256(canonical_bytes(remaining)) == manifest['remaining_request_keys_sha256'] and
        len(requests) == manifest['original_request_count'] and len(existing) == manifest['preserved_first_attempt_count'],
        'Amendment remaining scope or preserved attempt count changed')
    require(manifest['failed_key'] in existing and manifest['failed_key'] not in remaining,
            'The failed first attempt must never be resent')
    _failure(root, directory, requests, ledger, manifest['failed_key'])
    require(_attempt_inventory(root, directory, requests, ledger, existing) == manifest['preserved_attempts'],
            'Original first-attempt/raw inventory changed, gained files or omitted attempts')
    active, archived = directory / 'STOP.json', directory / 'stops' / (manifest['stop_sha256'] + '.json')
    stop_path = archived if archived.exists() else active
    require(stop_path.is_file() and sha256(stop_path.read_bytes()) == manifest['stop_sha256'] and
            load(stop_path).get('request_key') == manifest['failed_key'], 'Exact original systemic stop not retained')
    for line in journal[size:].splitlines():
        event = json.loads(line)
        if event['kind'] == 'dispatch' and event['data']['key'] in requests:
            require(event['data']['key'] in remaining, 'Post-amendment development dispatch repeats an original attempt')
    return manifest


def validate_link(manifest_path=None, *, directory=plan.DEST, project_root=ROOT,
                  require_archive=False, require_committed=True, **_):
    raw_path, tracked, _ = _paths(Path(project_root).resolve(), Path(directory).resolve())
    require(manifest_path is None or Path(manifest_path).resolve() == raw_path.resolve(),
            'Only the exact fixed development amendment manifest is permitted')
    manifest = verify(require_committed=require_committed, project_root=project_root, directory=directory)
    require(manifest is not None, 'Development amendment is missing')
    ledger = BudgetLedger(Path(directory) / 'budget.jsonl').snapshot()
    if require_archive:
        require((Path(directory) / 'stops' / (manifest['stop_sha256'] + '.json')).is_file(),
                'Journaled amendment must retain the archived exact original stop')
    return manifest, ledger, tracked


def approved_failure(key, ledger, directory, project_root=ROOT, **_):
    snapshot = ledger.snapshot() if hasattr(ledger, 'snapshot') else ledger
    event = snapshot.get('development_amendments', {}).get(key)
    if event is None:
        return False
    try:
        manifest, current, tracked = validate_link(event['manifest_path'] if Path(event['manifest_path']).is_absolute()
            else Path(project_root) / event['manifest_path'], directory=directory, project_root=project_root,
            require_archive=True)
        raw_path, _, _ = _paths(Path(project_root).resolve(), Path(directory).resolve())
        expected = {'failed_key': key, 'failure_evidence_sha256': manifest['failure_evidence_sha256'],
            'stop_sha256': manifest['stop_sha256'], 'manifest_sha256': sha256(raw_path.read_bytes()),
            'manifest_path': _relative(raw_path, project_root), 'receipt_path': _relative(tracked, project_root),
            'receipt_sha256': sha256(tracked.read_bytes()), 'raw_response_sha256': manifest['raw_response_sha256']}
        require(manifest['failed_key'] == key and all(event.get(k) == v for k, v in expected.items()) and
            current['development_amendments'].get(key) == event,
            'Journaled capacity amendment does not match its exact committed lineage')
        return True
    except (OSError, ValueError, KeyError, TypeError, AmendmentError):
        return False


@contextmanager
def _sole_lock(directory):
    with (Path(directory) / 'sole-executor.lock').open('a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def activate(manifest_path=None, *, directory=plan.DEST, project_root=ROOT,
             now_epoch=None, after_journal=None):
    """Journal authorization before archiving STOP. Never dispatch any request."""
    root, directory = Path(project_root).resolve(), Path(directory).resolve()
    with _sole_lock(directory):
        manifest, snapshot, tracked = validate_link(manifest_path, directory=directory, project_root=root)
        raw_path, _, _ = _paths(root, directory)
        previous = snapshot.get('development_amendments', {}).get(manifest['failed_key'])
        if previous is None:
            require(sha256((directory / 'budget.jsonl').read_bytes()) == manifest['ledger_prefix_sha256'],
                    'Journal changed after amendment preparation; no activation is permitted')
            require(not (root / 'results/study-v6-execution/confirmation-freeze-v1.json').exists(),
                    'Activate the operational amendment before confirmation')
            require((directory / 'STOP.json').is_file() and
                sha256((directory / 'STOP.json').read_bytes()) == manifest['stop_sha256'] and
                not (directory / 'stops' / (manifest['stop_sha256'] + '.json')).exists(),
                'First activation requires the exact active stop without an unexplained archive')
        now = time.time() if now_epoch is None else now_epoch
        require(type(now) in (int, float) and math.isfinite(now) and now >= manifest['not_before_epoch'], 'Invalid capacity activation time')
        record = load(directory / 'attempts' / manifest['failed_key'] / 'execution-record.json')
        ledger = BudgetLedger(directory / 'budget.jsonl', history_root=root)
        event = ledger.record_development_capacity_continuation(manifest['failed_key'], failure_record=record,
            failure_evidence_sha256=manifest['failure_evidence_sha256'], stop_sha256=manifest['stop_sha256'],
            manifest_sha256=sha256(raw_path.read_bytes()), manifest_path=_relative(raw_path, root),
            receipt_path=_relative(tracked, root), receipt_sha256=sha256(tracked.read_bytes()),
            activated_at_epoch=now, raw_response_sha256=manifest['raw_response_sha256'])
        if after_journal is not None:
            after_journal()
        active, archived = directory / 'STOP.json', directory / 'stops' / (manifest['stop_sha256'] + '.json')
        archived.parent.mkdir(parents=True, exist_ok=True)
        if active.exists():
            require(sha256(active.read_bytes()) == manifest['stop_sha256'], 'A different active stop cannot be cleared')
            os.replace(active, archived)
            for path in (directory, archived.parent):
                descriptor = os.open(path, os.O_RDONLY)
                try:
                    os.fsync(descriptor)
                finally:
                    os.close(descriptor)
        require(archived.is_file() and sha256(archived.read_bytes()) == manifest['stop_sha256'],
                'The exact original stop must remain archived')
        return {'activated': True, 'version': VERSION, 'failed_key_retried': False,
                'remaining_request_scope_count': len(manifest['remaining_request_keys']),
                'activation_epoch': event['activated_at_epoch']}


def apply_confirmation_coverage(intended):
    """Prospective Nimble-only byte gate, intact pairs, unchanged full target."""
    from scripts.study_v6.routes import native_byte_coverage
    result = copy.deepcopy(intended)
    requests = {r['key']: r for r in result['requests']}
    nimble = [c for c in result['cells'] if c['split'] == 'confirmation' and c['config'] == 'nimble_local']
    blocks = {}
    for cell in nimble:
        gate = native_byte_coverage(requests[cell['request_key']]['payload'])
        cell['native_byte_coverage'] = gate
        if not gate['supported']:
            cell['coverage_supported'] = False
            cell['coverage_status'] = gate['coverage_status']
        pair = cell['pair_id'] if cell.get('pair_id') is not None else cell['id']
        blocks.setdefault((cell['source'], str(pair)), []).append(cell)
    for cells in blocks.values():
        if not all(c['coverage_supported'] for c in cells):
            for cell in cells:
                cell['coverage_supported'] = False
                if cell['native_byte_coverage']['supported']:
                    cell['coverage_status'] = 'unsupported_paired_native_byte_limit'
    by_request, by_batch = {}, {}
    for cell in result['cells']:
        by_request.setdefault(cell['request_key'], []).append(cell)
        by_batch.setdefault((cell['allocation'], cell['batch']), []).append(cell)
    for request in result['requests']:
        if request['split'] == 'confirmation' and request['config'] == 'nimble_local':
            request['coverage_supported'] = any(c['coverage_supported'] for c in by_request[request['key']])
    for allocation, groups in result['schedules'].items():
        for group in groups:
            cells = by_batch.get((allocation, group['batch']), [])
            if cells:
                group['all_requests_supported'] = all(c['coverage_supported'] for c in cells)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('prepare', 'verify', 'activate'))
    parser.add_argument('manifest', nargs='?', type=Path)
    args = parser.parse_args()
    if args.action == 'prepare':
        result = prepare()
    elif args.action == 'activate':
        result = activate(args.manifest)
    else:
        manifest = verify()
        result = {'verified': manifest is not None, 'version': VERSION}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
