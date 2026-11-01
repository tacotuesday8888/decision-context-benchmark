"""Admission and immutable v6 execution freezes. No request dispatch is possible here."""
from __future__ import annotations

import argparse
import collections
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import ROOT, RAW, read, canonical_bytes, sha256
from scripts.study_v6 import plan, routes
from scripts.study_v6.evidence import immutable, load, file_receipt
from scripts.study_v6.accounting import reconcile_history, verify_history


def admission():
    """Recompute final adjudicated admission, not the preserved candidate snapshots."""
    from scripts.study_v6.verify_resolution import verify
    receipt = ROOT / 'results/study-v6-review-resolution/resolution-final.json'
    if not receipt.is_file():
        raise PermissionError('Complete independent adjudication and final v3 admission are required')
    value = load(receipt)
    if not value['review_resolution_complete'] or not value['adjudication_completed']:
        raise PermissionError('Final review gate pending')
    verify(require_cache=True, with_adjudication=True)
    for script in ('resolve_review.py', 'resolved_plan.py'):
        subprocess.run([sys.executable, str(ROOT / 'scripts/study_v6' / script),
                        '--with-adjudication', '--verify'], cwd=ROOT, check=True, capture_output=True)
    return value


def scientific_hashes():
    paths = set()
    for directory in ('study_v6', 'study_v5', 'expanded_v2', 'expanded_execution', 'laya_v2', 'nimble_v2'):
        paths.update((ROOT / 'scripts' / directory).glob('*.py'))
    paths.update((ROOT / 'tests/study_v6').glob('*.py'))
    paths.update(ROOT / name for name in (
        'scripts/controls_v4/nimble_runtime.py', 'scripts/response_metadata.py',
        'scripts/smoke_access.py', 'scripts/provider_access.py', 'scripts/chatgpt_signin.py',
        'scripts/source_discovery/prepare_review.py', 'results/laya-v2/model-artifacts.json',
        'docs/study-v6/DESIGN.md', 'docs/study-v6/SOURCES.md', 'docs/study-v6/METHODS-COMPARISON.md',
        'docs/study-v6/REVIEW.md', 'docs/study-v6-review-resolution/POLICY.json',
        'docs/study-v6-execution/ANALYSIS-PLAN.md', 'docs/study-v6-execution/OPERATIONS.md',
        'docs/study-v6-execution/SOURCE-CHECK.md',
        'docs/controls-v4/MODEL-ROUTES.md', '.github/workflows/study-v6.yml'))
    return {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in sorted(paths)}


def committed(hashes):
    for name, expected in hashes.items():
        process = subprocess.run(['git', 'show', 'HEAD:' + name], cwd=ROOT, capture_output=True)
        if process.returncode or sha256(process.stdout) != expected:
            raise PermissionError('Scientific code/specification must be committed before freezing: ' + name)
    return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip()


def price_gate():
    receipt = load(plan.RESULTS / 'price-verification-v2.json')
    if receipt['base_input_usd_per_million'] != {'openai': '.10', 'typesafe': '.042'}:
        raise PermissionError('Price mismatch requires a new bounded plan')
    if receipt['reservation_input_usd_per_million'] != {'openai': '.50', 'typesafe': '.084'}:
        raise PermissionError('Reservation price mismatch')
    for source in receipt['official_evidence'].values():
        if sha256((ROOT / source['path']).read_bytes()) != source['sha256']:
            raise ValueError('Official price snapshot changed')
    return receipt


def development_amendment(hashes=None, *, base_freeze=None, require_committed=True):
    """Resolve the separately preserved development-only operational lineage."""
    from scripts.study_v6.development_amendment import verify
    return verify(base_freeze=base_freeze, current_hashes=hashes,
        require_committed=require_committed, project_root=ROOT, directory=plan.DEST)


def offline_gate(hashes):
    amendment = development_amendment(hashes)
    name = 'offline-verification-v4.json' if amendment else 'offline-verification-v3.json'
    receipt = load(plan.RESULTS / name)
    if receipt.get('checks_passed') is not True or receipt.get('scientific_hashes') != hashes:
        raise PermissionError('Offline verification is missing or stale')
    return receipt


def setup_gate():
    access = load(plan.DEST / 'noninference-access-v1.json')
    expected = {'openai_api', 'typesafe_api', 'openai_subscription'}
    if set(access['providers']) != expected or access['inference_calls'] != 0:
        raise PermissionError('Non-inference access receipt is missing or inconsistent')
    if any(p.get('authentication_verified') is not True for p in access['providers'].values()):
        raise PermissionError('Required existing authentication is unavailable')
    sub = access['providers']['openai_subscription']
    if not (sub['luna_catalog_seen'] and sub['astra_catalog_seen']):
        raise PermissionError('Authorized subscription catalogue lacks a retained model')
    local = load(plan.DEST / 'nimble-local-metadata.json')
    if local['runtime'] != '0.40.13' or local['model'].get('digest') != routes.PANEL['nimble_local']['revision']:
        raise PermissionError('Pinned local Nimble metadata changed')
    return {'authentication_verified_without_inference': True,
            'native_decision_access_requires_development': True, 'nimble_identity_verified': True}


def prefreeze_audit_gate():
    amendment = development_amendment()
    name = 'prefreeze-audit-v3.json' if amendment else 'prefreeze-audit-v2.json'
    receipt = load(plan.RESULTS / name)
    if (receipt.get('checks_passed') is not True or receipt.get('new_model_calls') != 0 or
            receipt.get('model_outputs_inspected') is not False):
        raise PermissionError('Independent offline request/cohort audit is incomplete')
    for source in receipt['inputs'].values():
        if sha256((ROOT / source['path']).read_bytes()) != source['sha256']:
            raise ValueError('Audited prefreeze input changed: ' + source['path'])
    return receipt


def prepare(*, protectai_tokenizer=None):
    """Save final intended requests with full-input dispositions before any calls."""
    resolved = admission()
    price_gate()
    from scripts.study_v6.grouping_gate import finalize as finalize_grouping
    rows, grouping = finalize_grouping()
    provisional = plan.build(rows, review_subgroups=plan.load_review_subgroups())
    audit = {(r['id'], r['condition']): r for r in read(RAW / 'laya-token-audit.jsonl')}
    coverage, lookup = [], {}
    for request in provisional['requests']:
        config = request['config']
        for ref in request['refs']:
            cov = routes.coverage(config, request['payload'],
                laya_audit=audit.get((ref['id'], ref['condition'])) if config == 'laya_local' else None,
                tokenizer=protectai_tokenizer if config == 'protectai_local' else None,
                allow_server_gate=config not in ('laya_local', 'protectai_local'))
            cov['status'] = cov['coverage_status']
            record = dict(cov, id=ref['id'], config=config, condition=ref['condition'], split=request['split'])
            coverage.append(record)
            lookup[(ref['id'], config, ref['condition'])] = cov
    result = plan.build(rows, coverage=lookup, review_subgroups=plan.load_review_subgroups())
    # No pending route capability can quietly become permission at execution.
    pending = [c for c in coverage if c['coverage_status'].startswith('pending')]
    if pending:
        raise PermissionError('Exact coverage remains pending for ' + str(len(pending)) + ' cells')
    manifests = {'intended-plan.json': result, 'coverage.json': coverage,
                 'inherited-accounting.json': reconcile_history(ROOT)}
    for name, value in manifests.items():
        immutable(plan.DEST / name, value)
    from scripts.study_v6.runtime import capture
    immutable(plan.RESULTS / 'runtime-versions-v1.json', capture())
    summary = dict(plan.summary(result),
        final_resolution_sha256=sha256((ROOT / 'results/study-v6-review-resolution/resolution-final.json').read_bytes()),
        execution_grouping_admission=grouping,
        intended_plan=file_receipt(plan.DEST / 'intended-plan.json', ROOT),
        coverage=file_receipt(plan.DEST / 'coverage.json', ROOT),
        inherited_accounting=file_receipt(plan.DEST / 'inherited-accounting.json', ROOT),
        coverage_methods=dict(collections.Counter(c['coverage_status'] for c in coverage)),
        capacity_limitation='Hosted and Nimble full unchanged inputs use explicit native server gates, not claimed preflight tokenizer certification; native overflows/failures remain separate missing dispositions.',
        preserved_byte_reservation_proxy_not_a_certified_token_bound=True,
        final_admitted_review_rows=resolved['review_eligible_rows'],
        final_execution_admitted_rows=sum(plan.admitted(r) for r in rows))
    immutable(plan.RESULTS / 'request-plan-v1.json', summary)
    return summary


def development_operational_gate(intended):
    """Check access/schema, never correctness; preserve any first-attempt failures."""
    records, native_records, reviewed_failures, capacity_failures, case_failures = [], [], [], [], []
    ledger = None
    by_key = {r['key']: r for r in intended['requests']}
    for request in by_key.values():
        if request['split'] != 'development' or not request['coverage_supported']:
            continue
        folder = plan.DEST / 'attempts' / request['key']
        path = folder / 'execution-record.json'
        if not path.exists():
            raise PermissionError('Development operational check missing: ' + request['config'])
        record = load(path)
        result = record['result']
        if result['request_sha256'] != request['request_sha256']:
            raise ValueError('Development request changed')
        if result['parsed']['status'] not in ('ok', 'tie', 'unsupported_over_limit'):
            if not routes.requires_stop(result['parsed']):
                case_failures.append(request['key'])
            else:
                from scripts.study_v6.accounting import BudgetLedger
                from scripts.study_v6.continuations import approved_failure
                from scripts.study_v6.development_amendment import approved_failure as amended_capacity_failure
                ledger = ledger or BudgetLedger(plan.DEST / 'budget.jsonl', history_root=ROOT)
                if amended_capacity_failure(request['key'], ledger, plan.DEST, ROOT):
                    capacity_failures.append(request['key'])
                elif approved_failure(request['key'], ledger, plan.DEST, ROOT):
                    reviewed_failures.append(request['key'])
                else:
                    raise PermissionError('Development route needs documented operational resolution: ' + request['config'])
        records.append(file_receipt(path, ROOT))
        native = folder / 'completed.json'
        if native.exists():
            native_records.append(file_receipt(native, ROOT))
    successful = {by_key[Path(r['path']).parent.name]['config'] for r in records
                  if load(ROOT / r['path'])['result']['parsed']['status'] in ('ok', 'tie')}
    if successful != set(plan.CONFIGS):
        raise PermissionError('Every retained configuration needs a reviewed development interface success')
    continuation_evidence = []
    if ledger:
        state = ledger.snapshot()
        events = list(state.get('continuations', {}).values()) + list(state.get('development_amendments', {}).values())
        for event in events:
            for name in ('manifest_path', 'receipt_path'):
                continuation_evidence.append(file_receipt(ROOT / event[name], ROOT))
            continuation_evidence.append(file_receipt(plan.DEST / 'stops' / (event['stop_sha256'] + '.json'), ROOT))
    return {'correctness_not_used': True, 'first_attempt_records': records,
            'native_completion_records': native_records, 'continuation_evidence': continuation_evidence,
            'reviewed_transient_failures': len(reviewed_failures),
            'reviewed_development_capacity_failures': len(capacity_failures),
            'retained_case_failures': len(case_failures),
            'failed_requests_resent': False, 'successful_configuration_count': len(successful)}


def freeze(split):
    if split not in ('development', 'confirmation'):
        raise ValueError('Unknown split')
    admission()
    price_gate()
    setup = setup_gate()
    prefreeze_audit_gate()
    from scripts.study_v6.grouping_gate import verify as verify_grouping
    _, grouping = verify_grouping()
    hashes = scientific_hashes()
    amendment = development_amendment(hashes)
    offline_gate(hashes)
    head = committed(hashes)
    intended = load(plan.DEST / 'intended-plan.json')
    if amendment:
        if split != 'confirmation':
            raise PermissionError('Preserve the original development freeze; its amendment is a separate lineage')
        from scripts.study_v6.development_amendment import apply_confirmation_coverage
        intended = apply_confirmation_coverage(intended)
    current_history = reconcile_history(ROOT)
    if current_history != load(plan.DEST / 'inherited-accounting.json'):
        raise PermissionError('Spending changed after planning')
    refs = [plan.RESULTS / 'request-plan-v1.json', plan.RESULTS / 'price-verification-v2.json',
            plan.RESULTS / ('offline-verification-v4.json' if amendment else 'offline-verification-v3.json'),
            plan.RESULTS / 'runtime-versions-v1.json',
            plan.RESULTS / ('prefreeze-audit-v3.json' if amendment else 'prefreeze-audit-v2.json'),
            plan.DEST / 'noninference-access-v1.json', plan.DEST / 'nimble-local-metadata.json',
            plan.RESULTS / 'grouping-admission-v1.json',
            plan.DEST / 'intended-plan.json', plan.DEST / 'coverage.json', plan.DEST / 'inherited-accounting.json',
            ROOT / 'results/study-v6-review-resolution/resolution-final.json',
            ROOT / 'results/study-v6-review-resolution/planning-final.json']
    if amendment:
        refs += [plan.RESULTS / 'development-amendment-v6.0.1.json',
                 plan.DEST / 'development-amendment-v6.0.1.json']
    resolution = load(ROOT / 'results/study-v6-review-resolution/resolution-final.json')
    refs += [ROOT / v['path'] for v in resolution['inputs'].values()]
    refs += [ROOT / v['path'] for v in resolution['outputs'].values()]
    refs += [ROOT / v['path'] for v in grouping['inputs'].values()]
    refs += [ROOT / v['path'] for v in grouping['outputs'].values()]
    refs += list((ROOT / 'results/study-v6').glob('*.json'))
    unsupported_batches = {g['batch'] for allocation in ('main', 'supporting')
        for g in intended['schedules'][allocation] if not g['all_requests_supported']}
    selected = [dict(c, inference_eligible=c['coverage_supported'] and c['batch'] not in unsupported_batches)
                for c in intended['cells'] if c['split'] == split]
    for cell in selected:
        if cell['coverage_status'] in ('pending', 'pending_native_coverage'):
            raise PermissionError('Pending coverage cannot freeze')
    request_keys = {c['request_key'] for c in selected if c['inference_eligible']}
    requests = [dict(r, inference_eligible=True) for r in intended['requests'] if r['key'] in request_keys]
    raw_manifest = plan.DEST / (split + '-frozen-plan.json')
    immutable(raw_manifest, {'version': plan.VERSION, 'split': split, 'cells': selected,
                             'requests': requests, 'schedules': intended['schedules']})
    refs.append(raw_manifest)
    output = {'version': plan.VERSION, 'split': split, 'code_commit': head,
        'scientific_hashes': hashes, 'evidence': {str(p.relative_to(ROOT)): sha256(p.read_bytes()) for p in sorted(set(refs))},
        'raw_plan': str(raw_manifest.relative_to(ROOT)), 'frozen_cells': len(selected),
        'eligible_cells': sum(c['inference_eligible'] for c in selected), 'unique_eligible_requests': len(requests),
        'operational_limits_usd': {'main': 9, 'supporting': 2, 'development': .5, 'recovery': .5, 'total_per_provider': 12},
        'global_provider_caps_usd': {'openai': 15, 'typesafe': 20}, 'automatic_retries': 0,
        'paid_fallback': False, 'created_at_utc': datetime.now(timezone.utc).isoformat()}
    output['setup'] = setup
    if split == 'confirmation':
        output['development'] = development_operational_gate(intended)
        dev = plan.RESULTS / 'development-freeze-v1.json'
        output['development_freeze_sha256'] = sha256(dev.read_bytes())
        ledger_bytes = (plan.DEST / 'budget.jsonl').read_bytes()
        output['ledger_before_confirmation_sha256'] = sha256(ledger_bytes)
        output['ledger_before_confirmation_bytes'] = len(ledger_bytes)
        if amendment:
            output['development_amendment_sha256'] = sha256(
                (plan.RESULTS / 'development-amendment-v6.0.1.json').read_bytes())
            output['development_capacity_amendment'] = {
                'version': amendment['version'],
                'scientific_requests_unchanged': True,
                'prospective_native_byte_gate': 'nimble_local',
                'original_development_first_attempts_preserved': True}
    immutable(plan.RESULTS / (split + '-freeze-v1.json'), output)
    return output


def verify(split, *, require_committed=True):
    path = plan.RESULTS / (split + '-freeze-v1.json')
    frozen = load(path)
    hashes = scientific_hashes()
    expected = dict(frozen['scientific_hashes'])
    if split == 'development':
        amendment = development_amendment(hashes, base_freeze=frozen, require_committed=require_committed)
        if amendment:
            expected.update(amendment['replacement_hashes'])
    if expected != hashes:
        raise PermissionError('Frozen scientific code/specification changed')
    for name, digest in frozen['evidence'].items():
        if sha256((ROOT / name).read_bytes()) != digest:
            raise ValueError('Frozen evidence changed: ' + name)
    verify_history(load(plan.DEST / 'inherited-accounting.json'), ROOT)
    if require_committed:
        committed({str(path.relative_to(ROOT)): sha256(path.read_bytes())})
    if split == 'confirmation':
        amendment_hash = frozen.get('development_amendment_sha256')
        if amendment_hash is not None:
            if sha256((plan.RESULTS / 'development-amendment-v6.0.1.json').read_bytes()) != amendment_hash:
                raise ValueError('Development operational amendment changed')
            if development_amendment(hashes, require_committed=require_committed) is None:
                raise ValueError('Confirmation requires its pinned development amendment')
        if sha256((plan.RESULTS / 'development-freeze-v1.json').read_bytes()) != frozen['development_freeze_sha256']:
            raise ValueError('Development freeze changed')
        dev = frozen['development']
        for record in dev['first_attempt_records'] + dev.get('native_completion_records', []) + dev.get('continuation_evidence', []):
            if sha256((ROOT / record['path']).read_bytes()) != record['sha256']:
                raise ValueError('Development first attempt changed')
        ledger = (plan.DEST / 'budget.jsonl').read_bytes()
        size = frozen['ledger_before_confirmation_bytes']
        if len(ledger) < size or sha256(ledger[:size]) != frozen['ledger_before_confirmation_sha256']:
            raise ValueError('The frozen pre-confirmation journal prefix changed or was truncated')
    return frozen, load(ROOT / frozen['raw_plan'])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('action', choices=('prepare', 'freeze-development', 'freeze-confirmation',
                                          'verify-development', 'verify-confirmation'))
    args = parser.parse_args()
    if args.action == 'prepare':
        # Tokenization only: existing pinned local weights are never loaded here.
        from transformers import AutoTokenizer
        p = routes.PANEL['protectai_local']
        tokenizer = AutoTokenizer.from_pretrained(p['model'], revision=p['revision'], local_files_only=True, trust_remote_code=False)
        result = prepare(protectai_tokenizer=tokenizer)
    elif args.action.startswith('freeze-'):
        result = freeze(args.action.split('-', 1)[1])
    else:
        frozen, _ = verify(args.action.split('-', 1)[1])
        result = {'verified': True, 'split': frozen['split'], 'eligible_cells': frozen['eligible_cells']}
    print(json.dumps({k: result[k] for k in ('version', 'split', 'frozen_cells', 'eligible_cells', 'inference_ready', 'verified') if k in result}))


if __name__ == '__main__':
    main()
