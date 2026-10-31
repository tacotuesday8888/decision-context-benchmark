"""Recompute no-inference size/budget/coverage planning after review resolution."""
import argparse
import collections
import json
import math
import statistics
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import ROOT, RAW, OUT, read, rank, sha256, canonical_bytes, preserve_write
from scripts.study_v6.resolve_review import DEST, RESULTS
from scripts.study_v6.feasibility import group_prefix, PRIMARY_CONDITIONS, LIMITS, RATES
from scripts.study_v5.prompts import conditions, native_payload
from scripts.study_v5.feasibility import reconcile


def plan(rows, token_audit):
    eligible = [r for r in rows if r['review_eligible']]
    confirmation = [r for r in eligible if r['split_proposal'] == 'confirmation']
    main = [r for r in confirmation if r['source'] == 'browsesafe']
    order = sorted({r['group'] for r in main}, key=lambda g: rank('budget-order:' + g))
    prefix, costs, group_costs = group_prefix(main, LIMITS['primary_each_provider'], lambda _: PRIMARY_CONDITIONS)
    comparator_groups = set(order[:100])
    comparator = [r for r in main if r['group'] in comparator_groups]
    index = {}
    for record in token_audit:
        key = (record['id'], record['condition'])
        if key in index:
            raise ValueError('Duplicate tokenizer audit cell')
        index[key] = record
    coverage = []
    for row in eligible:
        for condition in conditions(row):
            record = index[(row['id'], condition)]
            payload_hash = sha256(canonical_bytes(native_payload(row, condition, 'laya_local')))
            if record['payload_sha256'] != payload_hash:
                raise ValueError('Laya cached coverage does not match exact current request')
            coverage.append({k: record[k] for k in ('id', 'condition', 'coverage_status', 'payload_sha256',
                            'state_tokens', 'head_tokens', 'truncated')})
    coverage_by_id = collections.defaultdict(list)
    for cell in coverage:
        coverage_by_id[cell['id']].append(cell)
    laya_complete = {i for i, cells in coverage_by_id.items() if not any(c['truncated'] for c in cells)}
    secondary = {}
    for source in ('aib', 'spml', 'infuse', 'nvidia', 'scope'):
        part = [r for r in confirmation if r['source'] == source]
        groups = sorted({r['group'] for r in part}, key=lambda g: rank('budget-order:' + g))[:12]
        secondary[source] = [{'group': g, 'ids': sorted(r['id'] for r in part if r['group'] == g)} for g in groups]
    counts = collections.Counter(r['source'] for r in eligible if r['id'] not in laya_complete)
    normal = statistics.NormalDist()
    precision = []
    for n in sorted({len(order), len(prefix)} - {0}):
        for q in (.1, .25, .5):
            z = normal.inv_cdf(1-.05/12)
            precision.append({'independent_units_assumed': n, 'discordance_assumed': q,
                'approx_80pct_power_delta_pp_six_tests': 100*(z+normal.inv_cdf(.8))*math.sqrt(q/n),
                'approx_simultaneous_95_halfwidth_pp_six_tests': 100*z*math.sqrt(q/n)})
    result = {'version': 'v6-resolved-planning-1', 'review_eligible_rows': len(eligible),
        'primary_review_cleared_target_groups_before_route_coverage': len(order),
        'primary_review_cleared_target_rows_before_route_coverage': len(main),
        'upfront_reservation_prefix_groups': len(prefix),
        'upfront_reservation_prefix_rows': sum(r['group'] in set(prefix) for r in main),
        'upfront_reservation_prefix_usd': costs,
        'comparator_first_groups': len(comparator_groups), 'comparator_rows': len(comparator),
        'laya_comparator_complete_six_condition_rows': sum(r['id'] in laya_complete for r in comparator),
        'laya_review_eligible_unsupported_any_condition_rows_by_source': dict(counts),
        'laya_exact_payload_cells_rechecked_without_forward_pass': len(coverage),
        'secondary_group_candidates_before_supporting_cost_stop': {
            s: {'groups': len(items), 'rows': sum(len(x['ids']) for x in items)} for s, items in secondary.items()},
        'sources_without_review_eligible_development_groups': [s for s in sorted({r['source'] for r in eligible})
            if not any(r['source'] == s and r['split_proposal'] == 'development' for r in eligible)],
        'precision_scenarios': precision, 'planning_rates_per_million': RATES,
        'limits': LIMITS, 'new_model_calls': 0, 'new_inference_spend_usd': 0,
        'inference_ready': False,
        'limitations': ['Byte reservation is a planning proxy, not a proven tokenizer upper bound.',
            'Actual usage can release reservations; the prefix is not a mandatory sample ceiling.',
            'Other routes still require exact full-input coverage checks and operational validation.',
            'Sources with no development groups receive no source development calls; do not move confirmation rows to development.',
            'Fewer than 20 independent groups means descriptive secondary results, not a confirmatory claim.',
            'Precision scenarios assume independent equal units and are not achieved power for unequal grouped errors.']}
    manifests = {'primary-target': [{'group': g, 'ids': sorted(r['id'] for r in main if r['group'] == g)} for g in order],
        'primary-reservation-prefix': group_costs, 'laya-reviewed-coverage': coverage,
        'secondary-candidates': [{'source': s, **item} for s, items in secondary.items() for item in items]}
    return result, manifests


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    parser.add_argument('--with-adjudication', action='store_true')
    args = parser.parse_args()
    dest = RAW / 'review-resolution-v3' if args.with_adjudication else DEST
    resolution_path = RESULTS / ('resolution-final.json' if args.with_adjudication else 'resolution.json')
    resolution = json.loads(resolution_path.read_text())
    if not resolution['review_resolution_complete']:
        raise ValueError('Do not create an execution planning cohort from pending caveat adjudication')
    resolved = dest / 'resolved.jsonl'
    if sha256(resolved.read_bytes()) != resolution['outputs']['resolved']['sha256']:
        raise ValueError('Resolved corpus changed')
    token_path = RAW / 'laya-token-audit.jsonl'
    if sha256(token_path.read_bytes()) != resolution['inputs']['token_audit']['sha256']:
        raise ValueError('Tokenizer audit changed')
    result, manifests = plan(read(resolved), read(token_path))
    result['accounting_at_preparation'] = reconcile()
    result['resolution_receipt_sha256'] = sha256(resolution_path.read_bytes())
    result['manifests'] = {}
    for name, records in manifests.items():
        path = dest / (name + '.jsonl')
        body = b''.join(canonical_bytes(r)+b'\n' for r in records)
        if args.verify:
            if path.read_bytes() != body:
                raise ValueError('Planning manifest changed: ' + name)
        else:
            preserve_write(path, body)
        result['manifests'][name] = {'path': str(path.relative_to(ROOT)), 'sha256': sha256(body), 'records': len(records)}
    path = RESULTS / ('planning-final.json' if args.with_adjudication else 'planning.json')
    body = json.dumps(result, indent=2, sort_keys=True).encode()+b'\n'
    if args.verify:
        if path.read_bytes() != body:
            raise ValueError('Planning receipt changed; inspect ledgers rather than overwrite a prior receipt')
    else:
        preserve_write(path, body, raw=False)
    print(json.dumps({k: v for k, v in result.items() if k not in ('manifests', 'precision_scenarios', 'accounting_at_preparation')}))


if __name__ == '__main__':
    main()
