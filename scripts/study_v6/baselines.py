"""Frozen, zero-cost candidate-only diagnostics on the intended v6 population.

These are literal rules, not learned detectors or model confidence estimates.
Rules are fixed in the v5 design; no words are added after observing errors.
Source rows are counted once, irrespective of scheduled models/conditions.  The
main cohort is the entire frozen BrowseSafe++ target; secondary cohorts are the
predeclared supporting candidates.  Cross-route comparisons must use the existing
same-row/pair intersection analysis, never pooled headline accuracy.
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import RAW, ROOT, canonical_bytes, sha256
from scripts.study_v6.resolve_review import source_label

VERSION = 'v6-literal-baselines-1'
CONFIGS = ('constant_allow', 'constant_block', 'lexical_shortcut')
LEXICAL_PHRASES = ('ignore previous', 'system prompt', 'do not tell', 'new task')


def predict(config, candidate):
    if not isinstance(candidate, str):
        raise ValueError('Candidate must be the complete source string')
    if config == 'constant_allow':
        return 0
    if config == 'constant_block':
        return 1
    if config == 'lexical_shortcut':
        text = candidate.casefold()
        return int(any(phrase in text for phrase in LEXICAL_PHRASES))
    raise ValueError('Unknown fixed baseline')


def selected_ids(intended_plan):
    """Main target plus scheduled secondary groups, without repeated row counts."""
    selected = {}
    schedules = intended_plan['schedules']
    for allocation, entries in (('main', schedules['main']), ('supporting', schedules['supporting'])):
        for entry in entries:
            if allocation == 'supporting' and entry['kind'] != 'secondary':
                continue
            if allocation == 'main' and entry['source'] != 'browsesafe':
                raise ValueError('Main baseline target must be BrowseSafe++')
            for identity in entry['ids']:
                metadata = (entry['source'], entry['group'])
                if identity in selected and selected[identity] != metadata:
                    raise ValueError('A selected row changed source or final group')
                selected[identity] = metadata
    return selected


def build(rows, intended_plan, *, review_resolution_complete=False):
    """Pure generation after verified final admission; no model/API operations.

    The caller must verify the immutable final resolution and intended-plan hashes.
    The CLI enforces those file bindings.  Explicit admission is required even for
    these free rules so provisional caveated rows cannot become apparent results.
    """
    if review_resolution_complete is not True:
        raise PermissionError('Complete final caveat adjudication/admission is required')
    selected = selected_ids(intended_plan)
    lookup = {row['id']: row for row in rows}
    if len(lookup) != len(rows) or not set(selected) <= set(lookup):
        raise ValueError('Duplicate or missing source rows')
    planned_by_id = collections.defaultdict(list)
    for cell in intended_plan['cells']:
        if cell['split'] == 'confirmation' and cell['id'] in selected:
            planned_by_id[cell['id']].append(cell)
    if set(planned_by_id) != set(selected):
        raise ValueError('Selected baseline target has no intended confirmation cell')
    cells, records, source_counts = [], [], collections.defaultdict(list)
    for identity, (source, group) in sorted(selected.items()):
        row = lookup[identity]
        gold = row.get('semantic_gold')
        if (row.get('review_eligible') is not True or row.get('exclusion_reasons') or
                row.get('split_proposal') != 'confirmation' or type(gold) is not int or gold not in (0, 1)):
            raise ValueError('Baseline selected an unadmitted or nonconfirmation row')
        upstream = source_label(row['upstream_label'])
        if upstream != gold:
            raise ValueError('Final admitted label must retain reviewed source agreement')
        if row['source'] != source or row['group'] != group:
            raise ValueError('Frozen target differs from resolved source/group')
        pair = row.get('pair_id') or row.get('provenance', {}).get('pair_id')
        planned = planned_by_id[identity]
        first = planned[0]
        invariant = ('source', 'group', 'gold', 'upstream_label', 'pair_id', 'review_subgroups')
        if any({field: item.get(field) for field in invariant} !=
               {field: first.get(field) for field in invariant} for item in planned):
            raise ValueError('Intended source metadata changes across models or conditions')
        if (first['source'], first['group'], first['gold'], first.get('pair_id')) != (source, group, gold, pair):
            raise ValueError('Intended labels/pairs differ from final resolved admission')
        if first.get('upstream_label') != upstream:
            raise ValueError('Source-label provenance changed')
        source_counts[source].append(row)
        candidate_hash = sha256(row['candidate'].encode())
        for config in CONFIGS:
            request_key = sha256(canonical_bytes([VERSION, 'confirmation', config, candidate_hash]))
            cell = {'id': identity, 'source': source, 'group': group, 'gold': gold,
                'semantic_gold': gold, 'upstream_label': upstream,
                'label_basis': row.get('label_basis'), 'setting': row['setting'], 'pair_id': pair,
                'review_subgroups': dict(first.get('review_subgroups', {})),
                'config': config, 'condition': 'candidate', 'split': 'confirmation',
                'allocation': 'literal_baselines', 'coverage_supported': True,
                'coverage_status': 'complete_literal_rule', 'inference_eligible': True,
                'request_key': request_key, 'candidate_sha256': candidate_hash,
                'access_route': 'local_literal_rule', 'model_inference': False, 'cost_usd': '0'}
            cells.append(cell)
            records.append({'id': identity, 'config': config, 'condition': 'candidate',
                'request_key': request_key, 'attempt': 0, 'status': 'ok', 'valid': True,
                'prediction': predict(config, row['candidate']), 'score': None,
                'access_route': 'local_literal_rule', 'model_inference': False, 'cost_usd': '0'})
    receipt = {'version': VERSION, 'rules': {'constant_allow': 0, 'constant_block': 1,
        'lexical_shortcut': {'phrases': list(LEXICAL_PHRASES), 'matching': 'candidate.casefold() substring OR'}},
        'selected_unique_rows': len(selected), 'planned_baseline_cells': len(cells),
        'by_source': {source: {'rows': len(part), 'groups': len({row['group'] for row in part}),
            'class_rows': {str(label): sum(row['semantic_gold'] == label for row in part) for label in (0, 1)}}
            for source, part in sorted(source_counts.items())},
        'incremental_api_cost_usd': '0', 'new_model_calls': 0,
        'scope': 'Source-specific candidate-only diagnostics. Compare routes only on identical supported source/pair intersections.',
        'confidence': 'Boolean literal rules; no probability or calibration claim.'}
    return {'cells': cells, 'records': records, 'receipt': receipt}


def read_rows(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _write(path, data):
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Refuse to overwrite changed baseline evidence')
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--resolved', required=True, type=Path)
    parser.add_argument('--resolution', required=True, type=Path)
    parser.add_argument('--intended-plan', required=True, type=Path)
    parser.add_argument('--plan-sha256', required=True)
    parser.add_argument('--output-dir', required=True, type=Path)
    parser.add_argument('--write', action='store_true', help='Write only after the committed confirmation freeze verifies')
    args = parser.parse_args()
    if not args.write:
        parser.error('Baseline evidence generation requires --write and a verified committed confirmation freeze')
    from scripts.study_v6.freeze import verify
    frozen, _ = verify('confirmation')
    for path in (args.resolved, args.resolution, args.intended_plan):
        relative = str(path.resolve().relative_to(ROOT))
        if frozen['evidence'].get(relative) != sha256(path.read_bytes()):
            raise ValueError('Baseline input is not pinned by the confirmation freeze')
    resolution = json.loads(args.resolution.read_text())
    if not resolution.get('review_resolution_complete') or not resolution.get('adjudication_completed'):
        raise PermissionError('The complete distinct adjudication and final admission are required')
    if sha256(args.resolved.read_bytes()) != resolution['outputs']['resolved']['sha256']:
        raise ValueError('Resolved source file differs from final admission receipt')
    if sha256(args.intended_plan.read_bytes()) != args.plan_sha256:
        raise ValueError('Intended plan hash mismatch')
    # Per-row labels and mappings remain under the ignored raw corpus tree.
    if not args.output_dir.resolve().is_relative_to(RAW.resolve()):
        raise ValueError('Baseline per-row evidence must remain in ignored study-v6 raw storage')
    result = build(read_rows(args.resolved), json.loads(args.intended_plan.read_text()), review_resolution_complete=True)
    for name in ('cells', 'records'):
        _write(args.output_dir / (name + '.jsonl'), b''.join(canonical_bytes(row) + b'\n' for row in result[name]))
    result['receipt']['inputs'] = {str(path): sha256(path.read_bytes()) for path in
        (args.resolved, args.resolution, args.intended_plan)}
    _write(args.output_dir / 'receipt.json', json.dumps(result['receipt'], indent=2, sort_keys=True).encode() + b'\n')
    print(json.dumps({key: result['receipt'][key] for key in ('selected_unique_rows', 'planned_baseline_cells', 'new_model_calls', 'incremental_api_cost_usd')}))


if __name__ == '__main__':
    main()
