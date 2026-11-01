"""Two explicit pre-confirmation development capacity amendments, v6.0.1/2.

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
VERSION_2 = 'dev-amendment-v6.0.2'
BASENAME_2 = 'development-amendment-v6.0.2.json'
VERSIONS = (VERSION, VERSION_2)
EXPECTED_REQUESTS = 460
EXPECTED_PRESERVED_ATTEMPTS = 407
EXPECTED_REMAINING_REQUESTS = 53
EXPECTED_CONTEXT_PRESERVED_ATTEMPTS = 423
EXPECTED_CONTEXT_REMAINING_REQUESTS = 37
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
CONTEXT_STATIC_FILES = {
    'static-returned-error-refs.txt': 'd231fc82367458726940b2e30ff0e2ba586b9a78df491950b5b0ddefe3365292',
    'static-context-reconstruction.json': 'd1d919bdf327420c47fb62ce0d925c04ae0a9884b4e1a08d1e9432a4de5cf1f0',
}
CONTEXT_BINARIES = {
    'ollama': {'path': str(TRUSTED_BINARY), 'sha256': TRUSTED_BINARY_SHA256, 'bytes': TRUSTED_BINARY_BYTES},
    'llama_server': {'path': '/Applications/Ollama.app/Contents/Resources/llama-server',
        'sha256': '00089aaa72646759fbaae9fa38ab0e47a984b40cf9e3d544dcea9db455d4e154', 'bytes': 19724368},
    'llama_server_library': {'path': '/Applications/Ollama.app/Contents/Resources/libllama-server-impl.dylib',
        'sha256': '470a20dee08000a1ce899d82fe56facae8cd83e7be8b886479a8015b471aa7f5', 'bytes': 4057776},
}


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


def _version(value):
    value = {'v6.0.1': VERSION, 'v6.0.2': VERSION_2}.get(value, value)
    require(value in VERSIONS, 'Only the two explicit development amendment versions are supported')
    return value


def _paths(root, directory, version=VERSION):
    root, directory = Path(root), Path(directory)
    _relative(directory, root)
    results = root / 'results/study-v6-execution'
    basename = BASENAME if _version(version) == VERSION else BASENAME_2
    return directory / basename, results / basename, results / 'development-freeze-v1.json'


def _existing(root, directory):
    found = []
    known = {BASENAME, BASENAME_2}
    for folder in (Path(directory), Path(root) / 'results/study-v6-execution'):
        require(all(path.name in known for path in folder.glob('development-amendment-v*.json')),
                'Unknown development amendment lineage is forbidden')
    for version in VERSIONS:
        raw, tracked, _ = _paths(root, directory, version)
        if raw.exists() or tracked.exists():
            require(raw.is_file() and tracked.is_file(), 'Incomplete amendment manifest/receipt pair')
            found.append(version)
    require(found != [VERSION_2], 'A context amendment cannot exist without its exact byte-limit parent')
    return found


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


def _replacements(original, current, version=VERSION):
    require(not (set(original) - set(current)), 'Amendment cannot remove scientific files')
    added = set(current) - set(original)
    changed = {name for name in current if name not in original or current[name] != original[name]}
    require(added == (ADDITIONS if version == VERSION else set()) and changed <= ALLOWED_CHANGES,
            'Scientific changes/additions exceed the explicit operational amendment allowlist')
    if version == VERSION:
        require(ADDITIONS <= changed, 'Amendment implementation and fixtures must be explicit additions')
    else:
        require(changed and 'scripts/study_v6/development_amendment.py' in changed,
                'The context amendment requires an explicit existing-file operational revision')
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


def _journal_prefix(prefix, requests, version=VERSION, parent=None):
    state = {}
    parent_events = []
    dispatched = set()
    for line in prefix.splitlines():
        event = json.loads(line)
        kind, data = event['kind'], event['data']
        if kind == 'reserve':
            for request in data['new_requests']:
                require(request['key'] in requests, 'Pre-amendment journal contains a nondevelopment request')
                state[request['key']] = 'reserved'
        elif kind == 'dispatch':
            require(data['key'] not in dispatched and state.get(data['key']) == 'reserved',
                    'A development first attempt cannot be dispatched twice')
            dispatched.add(data['key'])
            state[data['key']] = 'dispatched'
        elif kind == 'settle':
            state[data['key']] = 'terminal'
        elif kind == 'cancel_reserved':
            state[data['key']] = 'cancelled'
        elif kind == 'development_capacity_continuation':
            require(version == VERSION_2 and parent is not None and data['failed_key'] == parent['failed_key'] and
                data['manifest_sha256'] == parent['_raw_sha256'] and
                data.get('capacity_kind', 'native_request_bytes') == 'native_request_bytes',
                'The context prefix may inherit only its exact byte-limit parent activation')
            parent_events.append(data)
    require(all(value == 'terminal' for value in state.values()),
            'All original dispatched attempts must be terminal; no cancellations or pending holds')
    require(len(parent_events) == (1 if version == VERSION_2 else 0), 'Unexpected capacity activation lineage in prefix')
    expected = EXPECTED_PRESERVED_ATTEMPTS if version == VERSION else EXPECTED_CONTEXT_PRESERVED_ATTEMPTS
    expected_remaining = EXPECTED_REMAINING_REQUESTS if version == VERSION else EXPECTED_CONTEXT_REMAINING_REQUESTS
    require(len(state) == expected, 'Unexpected preserved development attempt count')
    remaining = sorted(set(requests) - set(state))
    require(len(remaining) == expected_remaining, 'Exact remaining development first-attempt scope changed')
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


def _failure(root, directory, requests, ledger, key, version=VERSION):
    require(key in requests and key in ledger['entries'], 'Capacity failure is not an original reserved first attempt')
    request, entry = requests[key], ledger['entries'][key]
    path = Path(directory) / 'attempts' / key / 'execution-record.json'
    record = load(path)
    result = record.get('result', {})
    parsed, observation = result.get('parsed', {}), result.get('observation', {})
    body = (path.parent / 'response.raw').read_bytes()
    from scripts.study_v6.routes import native_byte_coverage
    byte_gate = native_byte_coverage(request['payload'])
    require(request['config'] == 'nimble_local' and request['split'] == 'development' and request['provider'] is None,
            'Only the historical local native Nimble development capacity failure is eligible')
    require(record.get('key') == key and record.get('attempt') == 0 and record.get('first_attempt_primary') is True and
        record.get('config') == 'nimble_local' and record.get('split') == 'development' and
        parsed.get('status') == 'http_error' and
        parsed.get('valid') is False and parsed.get('prediction') is None and parsed.get('score') is None and
        result.get('stop_required') is True and
        observation.get('transport_exit_code') == 0 and result.get('access_route') == 'local' and
        result.get('paid_request') is False and result.get('raw_hashes', {}).get('response.raw') == sha256(body),
        'Only an exact retained invalid native Nimble capacity first attempt permits an amendment')
    if version == VERSION:
        require(result.get('parser_version') is None and observation.get('http_status') == 413 and
            body == NIMBLE_LEGACY_CAPACITY_BODY and sha256(body) == NIMBLE_LEGACY_CAPACITY_SHA256 and
            byte_gate['supported'] is False and byte_gate['limit_bytes'] == 65536,
            'Only the exact retained legacy Nimble HTTP413 byte-limit response permits the first amendment')
    else:
        from scripts.study_v6.routes import native_context_capacity_error
        require(result.get('parser_version') == 'v6-routes-2' and observation.get('http_status') == 400 and
            result.get('local_preflight') is False and result.get('native_request_sent') is True and
            byte_gate['supported'] is True and result.get('native_byte_coverage') == byte_gate and
            native_context_capacity_error(body) is not None,
            'Only the retained parser-two native Nimble HTTP400 token-context rejection permits the second amendment')
    require(entry['status'] == 'settled' and entry['provider'] is None and
        entry['evidence_sha256'] == sha256(path.read_bytes()) and
        all(money(entry[name]) == 0 for name in ('actual_usd', 'accounted_usd', 'reserved_usd')),
        'The historical local failure must retain its exact settled zero accounting')
    return record, path


def _gate_receipts(root, directory, current, *, version=VERSION, require_committed=True, archived_commit=None):
    result = Path(root) / 'results/study-v6-execution'
    offline_name, audit_name = (('offline-verification-v4.json', 'prefreeze-audit-v3.json') if version == VERSION else
                               ('offline-verification-v5.json', 'prefreeze-audit-v4.json'))
    offline_path, audit_path = result / offline_name, result / audit_name
    offline, audit = load(offline_path), load(audit_path)
    require(offline.get('checks_passed') is True and offline.get('scientific_hashes') == current,
            'Exact stage scientific code lacks its complete offline verification')
    require(audit.get('checks_passed') is True and audit.get('new_model_calls') == 0 and
        audit.get('model_outputs_inspected') is False and audit.get('checks') and all(v is True for v in audit['checks'].values()),
        'Independent stage prefreeze audit is incomplete or inspected experimental outcomes')
    expected_plan = Path(directory) / 'intended-plan.json'
    require(audit.get('inputs', {}).get('intended_plan', {}).get('path') == _relative(expected_plan, root),
            'Independent amendment audit must bind the preserved intended plan')
    for receipt in audit['inputs'].values():
        relative = receipt['path']
        if archived_commit is not None and relative in current:
            require(receipt['sha256'] == current[relative], 'Archived audit code digest differs from its stage source')
            _at_commit(root, archived_commit, {relative: receipt['sha256']})
        else:
            require(sha256(_path(root, relative).read_bytes()) == receipt['sha256'],
                    'Independent amendment audit has a stale noncode input')
    paths = {str(path.relative_to(root)): sha256(path.read_bytes()) for path in (offline_path, audit_path)}
    if require_committed:
        _commit(root, paths)
    return paths


def _operational_evidence(root, directory, *, version=VERSION, require_committed=True):
    doc = Path(root) / ('docs/study-v6-execution/AMENDMENT-v6.0.1.md' if version == VERSION else
                       'docs/study-v6-execution/AMENDMENT-v6.0.2.md')
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
    if version == VERSION_2:
        context_folder = Path(directory) / 'amendment-context-limit-evidence-v2'
        result['context_static_files'] = {}
        for name, expected in CONTEXT_STATIC_FILES.items():
            path = context_folder / name
            require(path.is_file() and sha256(path.read_bytes()) == expected, 'Pinned context-capacity evidence changed')
            result['context_static_files'][name] = {'path': _relative(path, root), 'sha256': expected}
        context = load(context_folder / 'static-context-reconstruction.json')
        require(context.get('schema') == 'nimble-native-context-limit-static-v2' and
            context.get('binaries') == CONTEXT_BINARIES, 'Context evidence does not match explicit trusted runtime binaries')
        for binary in CONTEXT_BINARIES.values():
            path = Path(binary['path'])
            require(path.is_file() and path.stat().st_size == binary['bytes'] and
                sha256(path.read_bytes()) == binary['sha256'], 'Explicit trusted context runtime binary changed')
        result['trusted_context_binaries'] = copy.deepcopy(CONTEXT_BINARIES)
    if require_committed:
        _commit(root, {_relative(doc, root): result['amendment_doc']['sha256']})
    return result


def _receipt(manifest, manifest_hash, relative):
    result = {'version': manifest['version'], 'kind': 'reviewed_preconfirmation_development_capacity_amendment',
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
    if manifest['version'] == VERSION_2:
        result.update({name: manifest[name] for name in ('parent_manifest_path', 'parent_manifest_sha256',
            'parent_receipt_path', 'parent_receipt_sha256', 'capacity_kind', 'requested_tokens', 'available_tokens')})
        result['reason'] = 'Preserve the parser-two native Nimble development context rejection and continue only the exact remaining original first attempts under parser three.'
    return result


def prepare(*, project_root=ROOT, directory=plan.DEST, current_hashes=None,
            require_committed=True, now_epoch=None, version=None):
    """Prepare inert immutable lineage. No activation, stop removal or inference."""
    root, directory = Path(project_root).resolve(), Path(directory).resolve()
    if root == ROOT.resolve():
        require(require_committed, 'Production amendment preparation requires committed scientific code')
    found = _existing(root, directory)
    selected = _version(version) if version is not None else (VERSION if not found else VERSION_2)
    require(selected not in found, 'Preserve the existing amendment; no further lineage beyond the two explicit versions')
    require((not found and selected == VERSION) or (found == [VERSION] and selected == VERSION_2),
            'Prepare only the next explicit amendment in dependency order')
    raw_path, tracked, base_path = _paths(root, directory, selected)
    require(not (root / 'results/study-v6-execution/confirmation-freeze-v1.json').exists(),
            'This operational amendment must precede all confirmation freezing/execution')
    original, frozen, requests, _, raw_plan = _original(root, directory, require_committed=require_committed)
    current = current_hashes if current_hashes is not None else _hashes(root)
    parent = None
    previous_hashes = original['scientific_hashes']
    if selected == VERSION_2:
        parents = _validate_chain(root, directory, base_freeze=original, current_hashes=None,
            require_committed=require_committed, archived_parent_only=True)
        parent = parents[0]
        previous_hashes = parent['expected_hashes']
    replacements = _replacements(previous_hashes, current, selected)
    _worktree(root, current)
    head = _commit(root, current) if require_committed else 'fixture-uncommitted'
    gates = _gate_receipts(root, directory, current, version=selected, require_committed=require_committed)
    operational = _operational_evidence(root, directory, version=selected, require_committed=require_committed)
    ledger = BudgetLedger(directory / 'budget.jsonl').snapshot()
    if parent is None:
        require(not ledger.get('development_amendments'), 'A capacity amendment already owns this development lineage')
    else:
        require(set(ledger.get('development_amendments', {})) == {parent['manifest']['failed_key']},
                'Only the exact activated first amendment may precede the context amendment')
        _activation_proof(parent, ledger, root, directory, require_archive=True)
    prefix = (directory / 'budget.jsonl').read_bytes()
    parent_context = None if parent is None else dict(parent['manifest'], _raw_sha256=parent['raw_sha256'])
    existing, remaining = _journal_prefix(prefix, requests, selected, parent_context)
    if parent is not None:
        require(set(remaining) < set(parent['manifest']['remaining_request_keys']),
                'The context stage must narrow the exact original remaining scope')
    require(set(ledger['entries']) == set(existing), 'Live development journal differs from exact terminal prefix')
    stop_path = directory / 'STOP.json'
    require(stop_path.is_file(), 'The original active systemic STOP must be retained')
    stop = load(stop_path)
    key = stop.get('request_key')
    require(key in existing and key not in remaining, 'Historical failed key cannot enter the remaining scope')
    record, record_path = _failure(root, directory, requests, ledger, key, selected)
    inventory = _attempt_inventory(root, directory, requests, ledger, existing)
    require({p.name for p in (directory / 'attempts').iterdir() if p.is_dir()} == set(existing),
            'Unplanned or unjournaled original attempt directory exists')
    now = time.time() if now_epoch is None else now_epoch
    require(type(now) in (int, float) and math.isfinite(now) and now > 0, 'Explicit finite amendment preparation time required')
    manifest = {'version': selected, 'split': 'development', 'code_commit': head,
        'base_freeze_path': _relative(base_path, root), 'base_freeze_sha256': sha256(base_path.read_bytes()),
        'base_frozen_plan_path': _relative(raw_plan, root), 'base_frozen_plan_sha256': sha256(raw_plan.read_bytes()),
        'base_scientific_hashes': original['scientific_hashes'], 'replacement_hashes': replacements,
        'gate_receipts': gates, 'operational_evidence': operational,
        'failed_key': key, 'failure_evidence_sha256': sha256(record_path.read_bytes()),
        'raw_response_sha256': record['result']['raw_hashes']['response.raw'],
        'stop_sha256': sha256(stop_path.read_bytes()), 'original_request_count': len(requests),
        'preserved_first_attempt_count': len(existing), 'preserved_attempts': inventory,
        'remaining_request_keys': remaining, 'remaining_request_keys_sha256': sha256(canonical_bytes(remaining)),
        'unchanged_caps': _caps(ledger['policy']), 'ledger_prefix_bytes': len(prefix),
        'ledger_prefix_sha256': sha256(prefix), 'prepared_at_epoch': now, 'not_before_epoch': now,
        'failed_key_never_retried': True, 'original_http_error_preserved': True,
        'predictions_used_for_extension': False, 'new_prediction_recovery': False}
    if parent is not None:
        from scripts.study_v6.routes import native_context_capacity_error
        counts = native_context_capacity_error((record_path.parent / 'response.raw').read_bytes())
        manifest.update(parent_manifest_path=_relative(parent['raw_path'], root),
            parent_manifest_sha256=parent['raw_sha256'], parent_receipt_path=_relative(parent['tracked_path'], root),
            parent_receipt_sha256=sha256(parent['tracked_path'].read_bytes()),
            parent_scientific_hashes=previous_hashes, capacity_kind='native_context_tokens', **counts)
    digest = immutable(raw_path, manifest)
    immutable(tracked, _receipt(manifest, digest, _relative(raw_path, root)))
    return {'manifest_path': str(raw_path), 'receipt_path': str(tracked), 'manifest_sha256': digest,
            'remaining_request_scope_count': len(remaining), 'activation_requires_committed_receipt': True}


def _event_matches(entry, event, root):
    manifest, raw_path, tracked = entry['manifest'], entry['raw_path'], entry['tracked_path']
    expected = {'failed_key': manifest['failed_key'], 'failure_evidence_sha256': manifest['failure_evidence_sha256'],
        'stop_sha256': manifest['stop_sha256'], 'manifest_sha256': entry['raw_sha256'],
        'manifest_path': _relative(raw_path, root), 'receipt_path': _relative(tracked, root),
        'receipt_sha256': sha256(tracked.read_bytes()), 'raw_response_sha256': manifest['raw_response_sha256']}
    require(all(event.get(k) == v for k, v in expected.items()), 'Journaled capacity activation changed its exact lineage')
    if manifest['version'] == VERSION:
        require(event.get('capacity_kind', 'native_request_bytes') == 'native_request_bytes', 'Wrong parent capacity kind')
    else:
        require(event.get('capacity_kind') == 'native_context_tokens' and
            all(event.get(k) == manifest[k] for k in ('requested_tokens', 'available_tokens')),
            'Wrong context capacity kind or native token counts')
    when = event.get('activated_at_epoch')
    require(type(when) in (int, float) and math.isfinite(when) and when >= manifest['not_before_epoch'],
            'Capacity activation precedes its explicit reviewed preparation')


def _activation_proof(entry, ledger, root, directory, *, require_archive):
    manifest = entry['manifest']
    event = ledger.get('development_amendments', {}).get(manifest['failed_key'])
    require(event is not None, 'Parent capacity amendment must be activated before the child')
    _event_matches(entry, event, root)
    if require_archive:
        path = Path(directory) / 'stops' / (manifest['stop_sha256'] + '.json')
        require(path.is_file() and sha256(path.read_bytes()) == manifest['stop_sha256'],
                'Activated capacity lineage requires the exact archived systemic stop')


def _validate_chain(root, directory, *, base_freeze=None, current_hashes=None,
                    require_committed=True, archived_parent_only=False):
    found = _existing(root, directory)
    if not found:
        return []
    require(not archived_parent_only or found == [VERSION], 'Child preparation requires only its preserved first parent')
    original, frozen, requests, base_path, raw_plan = _original(root, directory, base_freeze, require_committed=require_committed)
    ledger = BudgetLedger(directory / 'budget.jsonl').snapshot()
    journal = (directory / 'budget.jsonl').read_bytes()
    previous_hashes, entries = original['scientific_hashes'], []
    for index, version in enumerate(found):
        raw_path, tracked, _ = _paths(root, directory, version)
        manifest = load(raw_path)
        entry = {'manifest': manifest, 'raw_path': raw_path, 'tracked_path': tracked,
                 'raw_sha256': sha256(raw_path.read_bytes())}
        parent = entries[-1] if entries else None
        latest = index == len(found) - 1 and not archived_parent_only
        require(manifest.get('version') == version and manifest.get('split') == 'development' and
            manifest.get('failed_key_never_retried') is True and manifest.get('original_http_error_preserved') is True and
            manifest.get('predictions_used_for_extension') is False and manifest.get('new_prediction_recovery') is False,
            'Unknown development amendment semantics')
        require(load(tracked) == _receipt(manifest, entry['raw_sha256'], _relative(raw_path, root)),
                'Sanitized committed amendment receipt differs from raw lineage')
        require(manifest['base_freeze_path'] == _relative(base_path, root) and
            manifest['base_freeze_sha256'] == sha256(base_path.read_bytes()) and
            manifest['base_frozen_plan_path'] == _relative(raw_plan, root) and
            manifest['base_frozen_plan_sha256'] == sha256(raw_plan.read_bytes()) and
            manifest['base_scientific_hashes'] == original['scientific_hashes'], 'Original development lineage changed')
        expected = dict(previous_hashes, **manifest['replacement_hashes'])
        require(_replacements(previous_hashes, expected, version) == manifest['replacement_hashes'],
                'Stage replacement hashes exceed their exact operational allowlist')
        if parent is not None:
            require(manifest['parent_manifest_path'] == _relative(parent['raw_path'], root) and
                manifest['parent_manifest_sha256'] == parent['raw_sha256'] and
                manifest['parent_receipt_path'] == _relative(parent['tracked_path'], root) and
                manifest['parent_receipt_sha256'] == sha256(parent['tracked_path'].read_bytes()) and
                manifest['parent_scientific_hashes'] == previous_hashes,
                'Context amendment changed its immutable parent lineage')
            _activation_proof(parent, ledger, root, directory, require_archive=True)
        gates = _gate_receipts(root, directory, expected, version=version, require_committed=require_committed,
            archived_commit=None if latest else manifest['code_commit'])
        require(gates == manifest['gate_receipts'], 'Stage offline/audit receipts changed')
        require(_operational_evidence(root, directory, version=version, require_committed=require_committed)
                == manifest['operational_evidence'], 'Stage document or static evidence changed')
        if require_committed:
            _at_commit(root, manifest['code_commit'], expected)
            _commit(root, {_relative(tracked, root): sha256(tracked.read_bytes())})
        require(_caps(ledger['policy']) == manifest['unchanged_caps'], 'Capacity chain changed caps or inherited accounting')
        size = manifest['ledger_prefix_bytes']
        require(type(size) is int and len(journal) >= size and sha256(journal[:size]) == manifest['ledger_prefix_sha256'],
                'Original append-only stage journal prefix changed')
        parent_context = None if parent is None else dict(parent['manifest'], _raw_sha256=parent['raw_sha256'])
        existing, remaining = _journal_prefix(journal[:size], requests, version, parent_context)
        require(remaining == manifest['remaining_request_keys'] and
            sha256(canonical_bytes(remaining)) == manifest['remaining_request_keys_sha256'] and
            len(requests) == manifest['original_request_count'] and len(existing) == manifest['preserved_first_attempt_count'],
            'Capacity stage remaining scope or preserved first-attempt count changed')
        require(manifest['failed_key'] in existing and manifest['failed_key'] not in remaining,
                'A failed first attempt cannot enter an amended remaining scope')
        if parent is not None:
            require(manifest['failed_key'] in parent['manifest']['remaining_request_keys'] and
                set(remaining) == set(parent['manifest']['remaining_request_keys']) - set(existing),
                'Context stage must continue only the first parent unsent scope')
        record, record_path = _failure(root, directory, requests, ledger, manifest['failed_key'], version)
        require(sha256(record_path.read_bytes()) == manifest['failure_evidence_sha256'] and
            record['result']['raw_hashes']['response.raw'] == manifest['raw_response_sha256'], 'Historical failure evidence changed')
        if version == VERSION_2:
            from scripts.study_v6.routes import native_context_capacity_error
            counts = native_context_capacity_error((record_path.parent / 'response.raw').read_bytes())
            require(manifest.get('capacity_kind') == 'native_context_tokens' and
                all(manifest.get(k) == v for k, v in counts.items()), 'Context manifest native counts/cause changed')
        require(_attempt_inventory(root, directory, requests, ledger, existing) == manifest['preserved_attempts'],
                'Preserved first-attempt inventory changed or gained files')
        archived = directory / 'stops' / (manifest['stop_sha256'] + '.json')
        stop_path = archived if archived.exists() else directory / 'STOP.json'
        require(stop_path.is_file() and sha256(stop_path.read_bytes()) == manifest['stop_sha256'] and
            load(stop_path).get('request_key') == manifest['failed_key'], 'Exact stage systemic STOP is not retained')
        authorized = False
        for line in journal[size:].splitlines():
            event = json.loads(line)
            if event['kind'] == 'development_capacity_continuation' and event['data']['failed_key'] == manifest['failed_key']:
                require(not authorized, 'Duplicate capacity activation event')
                _event_matches(entry, event['data'], root)
                authorized = True
            elif event['kind'] == 'dispatch' and event['data']['key'] in requests:
                require(authorized and event['data']['key'] in remaining,
                        'Post-stage development dispatch is unapproved or repeats an original attempt')
        entry['expected_hashes'] = expected
        entries.append(entry)
        previous_hashes = expected
    require(set(ledger.get('development_amendments', {})) <= {entry['manifest']['failed_key'] for entry in entries},
            'Journal contains an unknown capacity-amendment lineage')
    if not archived_parent_only:
        current = current_hashes if current_hashes is not None else _hashes(root)
        require(current == previous_hashes, 'Latest operational lineage does not match exact current scientific hashes')
        _worktree(root, current)
        if require_committed:
            _commit(root, current)
    return entries


def verify(base_freeze=None, current_hashes=None, require_committed=True, *,
           project_root=ROOT, directory=plan.DEST):
    """Verify both stages; return latest effective original-to-current overlay."""
    entries = _validate_chain(Path(project_root).resolve(), Path(directory).resolve(),
        base_freeze=base_freeze, current_hashes=current_hashes, require_committed=require_committed)
    if not entries:
        return None
    latest = copy.deepcopy(entries[-1]['manifest'])
    if latest['version'] == VERSION_2:
        original = latest['base_scientific_hashes']
        latest['replacement_hashes'] = {k: v for k, v in entries[-1]['expected_hashes'].items() if original.get(k) != v}
    return latest


def validate_link(manifest_path=None, *, directory=plan.DEST, project_root=ROOT,
                  require_archive=False, require_committed=True, **_):
    root, directory = Path(project_root).resolve(), Path(directory).resolve()
    entries = _validate_chain(root, directory, require_committed=require_committed)
    require(entries, 'Development amendment is missing')
    selected = entries[-1] if manifest_path is None else next((entry for entry in entries
        if Path(manifest_path).resolve() == entry['raw_path'].resolve()), None)
    require(selected is not None, 'Only one of the two exact retained manifests may be requested')
    manifest, tracked = selected['manifest'], selected['tracked_path']
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
        raw_path, _, _ = _paths(Path(project_root).resolve(), Path(directory).resolve(), manifest['version'])
        _event_matches({'manifest': manifest, 'raw_path': raw_path, 'tracked_path': tracked,
                        'raw_sha256': sha256(raw_path.read_bytes())}, event, project_root)
        require(manifest['failed_key'] == key and
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
             now_epoch=None, after_journal=None, version=None):
    """Journal authorization before archiving STOP. Never dispatch any request."""
    root, directory = Path(project_root).resolve(), Path(directory).resolve()
    if version is not None:
        selected_path, _, _ = _paths(root, directory, _version(version))
        require(manifest_path is None or Path(manifest_path).resolve() == selected_path.resolve(), 'Manifest/version mismatch')
        manifest_path = selected_path
    with _sole_lock(directory):
        manifest, snapshot, tracked = validate_link(manifest_path, directory=directory, project_root=root)
        require(manifest['version'] == _existing(root, directory)[-1], 'Activate only the latest exact operational stage')
        raw_path, _, _ = _paths(root, directory, manifest['version'])
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
        typed = {} if manifest['version'] == VERSION else {'capacity_kind': 'native_context_tokens',
            'raw_response_body': (directory / 'attempts' / manifest['failed_key'] / 'response.raw').read_bytes()}
        event = ledger.record_development_capacity_continuation(manifest['failed_key'], failure_record=record,
            failure_evidence_sha256=manifest['failure_evidence_sha256'], stop_sha256=manifest['stop_sha256'],
            manifest_sha256=sha256(raw_path.read_bytes()), manifest_path=_relative(raw_path, root),
            receipt_path=_relative(tracked, root), receipt_sha256=sha256(tracked.read_bytes()),
            activated_at_epoch=now, raw_response_sha256=manifest['raw_response_sha256'], **typed)
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
        return {'activated': True, 'version': manifest['version'], 'failed_key_retried': False,
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
    parser.add_argument('--version', choices=('v6.0.1', 'v6.0.2'))
    args = parser.parse_args()
    if args.action == 'prepare':
        result = prepare(version=args.version)
    elif args.action == 'activate':
        result = activate(args.manifest, version=args.version)
    else:
        manifest = verify()
        result = {'verified': manifest is not None, 'version': manifest['version'] if manifest else None}
    print(json.dumps(result, sort_keys=True))


if __name__ == '__main__':
    main()
