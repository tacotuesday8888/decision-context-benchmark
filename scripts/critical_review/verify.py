"""Offline review of compact outcomes, with optional retained local evidence checks.

Writes only a new review receipt. Frozen estimators are replayed, never patched.
The separately implemented seed audit checks the declared rate-interval seed.
"""
import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import platform

import numpy as np
import scipy
from scipy import stats

from scripts.subscription_followup import analyze_core, extension_math

ROOT = Path(__file__).resolve().parents[2]
CONTROLS = ('format', 'reminder', 'length')
CONDITIONS = ('format', 'task', 'reminder', 'length')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text())


def lines(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines()]


def replay_differences(actual, expected, path=''):
    if isinstance(actual, dict) and isinstance(expected, dict):
        if actual.keys() != expected.keys():
            return [{'path': path, 'kind': 'keys differ'}]
        return [d for k in actual for d in replay_differences(actual[k], expected[k], path + '/' + str(k))]
    if isinstance(actual, list) and isinstance(expected, list):
        if len(actual) != len(expected):
            return [{'path': path, 'kind': 'length differs'}]
        return [d for i, (a, b) in enumerate(zip(actual, expected)) for d in replay_differences(a, b, path + '/' + str(i))]
    if actual == expected:
        return []
    result = {'path': path, 'actual': actual, 'expected': expected}
    if type(actual) is float and type(expected) is float:
        result['absolute_difference'] = abs(actual - expected)
    return [result]


def check_replay(actual, expected):
    differences = replay_differences(actual, expected)
    if differences:
        raise AssertionError(json.dumps({'differences': len(differences), 'first_20': differences[:20]}, indent=2))


def write_new(path, value):
    body = (json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n').encode()
    path = Path(path)
    if path.exists():
        if path.read_bytes() != body:
            raise ValueError('Refusing to replace different review output: ' + str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(body)


def errors_by_group(rows):
    groups = defaultdict(dict)
    for row in rows:
        key = (row['config'], row['condition'], row['gold'])
        assert key not in groups[row['group_id']]
        groups[row['group_id']][key] = int(row['prediction'] != row['gold']) if row['valid'] else None
    return groups


def contrast(group, model, control):
    return [group[model, condition, label] for condition in (control, 'task') for label in (0, 1)]


def difference(values):
    assert None not in values
    return (values[0] + values[1] - values[2] - values[3]) / 2


def bounds(groups, model, control):
    lower = upper = 0
    for group in groups.values():
        for value, weight in zip(contrast(group, model, control), (.5, .5, -.5, -.5)):
            lower += min(0, weight) if value is None else value * weight
            upper += max(0, weight) if value is None else value * weight
    return [lower / len(groups), upper / len(groups)]


def independent_effects(rows, saved, *, source=False):
    groups = errors_by_group(rows)
    entries = saved['contrasts'] if source else saved['sol_contrasts']
    primary = 'primary_shared16' if source else 'primary_complete8'
    result = []
    for entry in entries:
        model, control = entry['config'], entry['control']
        ids = sorted(g for g, values in groups.items()
                     if all(v is not None for k, v in values.items() if source or k[0] == 'sol_subscription'))
        values = [difference(contrast(groups[g], model, control)) for g in ids]
        expected = entry[primary]
        assert ids == expected['cohort']['group_ids']
        mean = sum(values) / len(values)
        assert abs(mean - expected['mean']) < 1e-14
        full_bounds = bounds(groups, model, control)
        assert np.allclose(full_bounds, entry['all_planned_missing_error_bounds']['range'], atol=1e-14, rtol=0)
        result.append({'model': model, 'control': control, 'groups': len(ids),
                       'mean_pp': mean * 100, 'all_planned_bounds_pp': [x * 100 for x in full_bounds]})
    return result


def rate_intervals(groups, ids, model, condition, seed, purpose, draws=20000):
    """Independent explicit seed implementation of the frozen empirical method."""
    vectors = []
    for gid in ids:
        clean = groups[gid][model, condition, 0]
        attack = groups[gid][model, condition, 1]
        vectors.append([clean or 0, int(clean is not None), attack or 0, int(attack is not None)])
    support, counts = np.unique(np.asarray(vectors, dtype=float), axis=0, return_counts=True)
    derived = int.from_bytes(hashlib.sha256(f'{seed}\0{purpose}'.encode()).digest()[:8], 'big')
    totals = np.random.default_rng(derived).multinomial(len(ids), counts / len(ids), size=draws) @ support
    clean_ok, attack_ok = totals[:, 1] > 0, totals[:, 3] > 0
    both = clean_ok & attack_ok
    samples = {'fpr': totals[clean_ok, 0] / totals[clean_ok, 1],
               'fnr': totals[attack_ok, 2] / totals[attack_ok, 3],
               'balanced_error': (totals[both, 0] / totals[both, 1] + totals[both, 2] / totals[both, 3]) / 2}
    return {name: np.quantile(value, [.025, .975], method='linear').tolist() for name, value in samples.items()}


def seed_audit(rows, saved):
    groups = errors_by_group(rows)
    results = []
    for field, purpose in [('shared16_metrics', 'shared16'), ('model8_metrics', 'model_complete8'),
                           ('all_planned_available_output_metrics', 'all_planned_available')]:
        for model in extension_math.MODELS:
            ids = (saved['shared_complete16']['group_ids'] if field == 'shared16_metrics' else
                   saved['model_complete8'][model]['group_ids'] if field == 'model8_metrics' else
                   saved['planned']['group_ids'])
            for condition in CONDITIONS:
                metadata = saved[field][model][condition]['rate_intervals']
                rp = f'{purpose}/{model}/{condition}/classification-rates'
                assert metadata['seed'] == extension_math.SEED and metadata['purpose'] == rp
                actual = rate_intervals(groups, ids, model, condition, extension_math.SEED, rp)
                counterfactual = rate_intervals(groups, ids, model, condition, analyze_core.SEED, rp)
                for metric in actual:
                    assert actual[metric] == metadata[metric]['pointwise_95']
                    results.append({'path': f'{field}/{model}/{condition}/rate_intervals/{metric}',
                                    'preserved_endpoint': actual[metric], 'counterfactual_core_seed_endpoint': counterfactual[metric]})
    changes = [r for r in results if r['preserved_endpoint'] != r['counterfactual_core_seed_endpoint']]
    return {'version': 'rate-seed-independent-verification-1',
            'status': 'Declared extension seed verified; initial review finding F2 rejected',
            'actual_and_recorded_rng_seed': extension_math.SEED,
            'intervals_verified': len(results), 'counterfactual_core_seed_changed_intervals': len(changes),
            'numerical_or_metadata_correction_required': False,
            'intervals': results}


def compact_review():
    core_dir = ROOT / 'results/subscription-followup-execution'
    source_dir = ROOT / 'results/subscription-followup-extensions-execution'
    hashes = {}
    for folder in (core_dir, source_dir):
        proof = read(folder / 'compact-outcomes-provenance.json')
        for name, expected in proof['files'].items():
            assert sha(folder / name) == expected
            hashes[str((folder / name).relative_to(ROOT))] = expected
    rows = lines(core_dir / 'main-first-outcomes.jsonl')
    source_rows = lines(source_dir / 'source-first-outcomes.jsonl')
    core = read(core_dir / 'core-analysis-v1.json')
    source = read(source_dir / 'source.json')
    regenerated_core = analyze_core.analyze_main(rows)
    seeded_differences = replay_differences(regenerated_core, core['main'])
    from scripts.critical_review.sampling_replay import replay
    original_intervals, sampling = replay()
    # A new, explicitly archived-draw replay; never mutate the frozen estimator or JSON.
    # Every other field still has to match exactly, including all primary intervals.
    target = regenerated_core['all_planned_available_output_metrics']['jev_firstparty']['task']['rate_intervals']
    for metric, endpoints in original_intervals.items():
        target[metric]['pointwise_95'] = endpoints
    check_replay(regenerated_core, core['main'])
    check_replay(extension_math.analyze_source(source_rows), source)
    repeats = lines(core_dir / 'repeat-outcomes.jsonl')
    repeated = {}
    index = {(r['group_id'], r['id'], r['condition']): r for r in rows if r['config'] == 'sol_subscription'}
    for condition in CONDITIONS:
        valid = [(index[r['group_id'], r['id'], condition], r) for r in repeats
                 if r['condition'] == condition and r['valid'] and index[r['group_id'], r['id'], condition]['valid']]
        count = sum(a['prediction'] != b['prediction'] for a, b in valid)
        assert count == core['repeat_disagreement'][condition]['numerator']
        assert len(valid) == core['repeat_disagreement'][condition]['denominator']
        repeated[condition] = {'changed': count, 'both_valid': len(valid)}
    details = core['annotation_blind_ai_audit']['details']
    disagreement = lambda r: any(int(r['injection_' + s]) != r['original_labels'][s] for s in ('A', 'B'))
    flagged = sorted(r['group_id'] for r in details if r['ambiguous'] or disagreement(r) or r['invalid_literal_span_count'])
    actors = [r for r in lines(source_dir / 'pilot-outcomes.jsonl') if r['kind'] == 'actor']
    assert len(actors) == 48 and all(r['answer']['action'] == 'none' for r in actors)
    procurement = [r for r in actors if r['task_id'] == 'procurement' and r.get('gate_disposition') != 'block']
    assert len(procurement) == 3 and all(r['answer']['final_answer'] == '12 units; 5 business days' for r in procurement)
    return {'version': 'critical-review-offline-verification-2', 'input_hashes': hashes,
            'software': {'numpy': np.__version__, 'scipy': scipy.__version__, 'platform': platform.platform(),
                         'python': platform.python_version()},
            'exact_frozen_core_and_source_replays': True,
            'seeded_core_replay_exact': not seeded_differences,
            'seeded_core_replay_differences': seeded_differences,
            'core_sampling_replay': sampling,
            'independent_core_effects': independent_effects(rows, core['main']),
            'independent_source_effects': independent_effects(source_rows, source, source=True),
            'repeat_counts': repeated, 'human_review_flagged_groups': flagged,
            'audit_ambiguous_pairs': sum(r['ambiguous'] for r in details),
            'audit_disagreement_pairs': sum(disagreement(r) for r in details),
            'pilot_actor_packets_checked': 48, 'pilot_correct_units_rejected_packets': 3,
            'rate_seed_verification': seed_audit(source_rows, source)}


def stream_answer(body):
    events = [json.loads(line[6:]) for line in body.splitlines() if line.startswith('data: {')]
    finals = [e['response'] for e in events if e.get('type') == 'response.completed']
    assert len(finals) == 1
    text = ''.join(c['text'] for item in finals[0]['output'] for c in item.get('content', []) if c.get('type') == 'output_text')
    if not text:
        # The subscription stream can emit text.done with an empty final output list.
        text = ''.join(e['text'] for e in events if e.get('type') == 'response.output_text.done')
    return json.loads(text)


def raw_spotcheck(root):
    """Selected transports, all failed core calls, audit exceptions and pilot units.

    Reads only named evidence files. Never opens credential stores or headers.
    """
    raw = Path(root) / 'data/raw/subscription-followup'
    plans = [read(raw / name) for name in ('core-plan-v1.json', 'extensions-plan-v1.json')]
    cells = {c['cell_id']: c for plan in plans for g in plan['groups'] for c in g['cells']}
    candidates = defaultdict(set)
    for cell in cells.values():
        if cell.get('stage') == 'secondary' or cell['cell_id'].startswith('core:main:'):
            p = cell['payload']
            state = json.loads(p['state'] if 'state' in p else p['input'][0]['content'])
            candidates[cell['id']].add(state['CANDIDATE'])
            assert set(state) == {'CANDIDATE', 'CANDIDATE_ROLE', 'TRUSTED_USER_TASK'}
    assert all(len(values) == 1 for values in candidates.values())
    chosen = []
    buckets = set()
    exceptions = {'browsesafe-v7:08576', 'browsesafe-v7:24123', 'browsesafe-v7:17411', 'browsesafe-v7:16952'}
    for run in ('execution-v1', 'execution-v2', 'execution-extensions-v1'):
        for path in sorted((raw / run / 'attempts').glob('*/completed.json')):
            result = read(path)
            cell = cells[result['cell_id']]
            parsed = result['parsed']
            bucket = (run, result['config'], parsed['status'])
            required = (not parsed['valid'] or result['cell_id'].startswith('pilot:procurement:') or
                        (cell.get('condition') == 'blind_audit' and cell['source_group_id'] in exceptions))
            if not required and bucket in buckets:
                continue
            buckets.add(bucket)
            for name in ('request.json', 'response.raw', 'started.json'):
                assert sha(path.parent / name) == result['raw_hashes'][name]
            request = read(path.parent / 'request.json')
            body = (path.parent / 'response.raw').read_text()
            if result['config'] == 'jev_firstparty':
                value = json.loads(body)['answers']['injection']['noul']
                assert value == parsed['score']
                assert (value == .5) == (parsed['status'] == 'tie')
            elif parsed['valid']:
                assert stream_answer(body) == parsed['answer']
            else:
                assert parsed.get('error_code') in body
            if cell.get('kind') != 'actor':
                assert request == cell['payload']
            chosen.append({'run': run, 'cell_id': result['cell_id'], 'status': parsed['status'],
                           'request_sha256': sha(path.parent / 'request.json'),
                           'response_sha256': sha(path.parent / 'response.raw')})
    return {'candidate_identities_checked': len(candidates), 'candidate_fixed_across_conditions': True,
            'selected_raw_attempts': chosen, 'scope': 'Selected transport reparse/hash check, not a full journal audit'}


def native_review(root):
    raw = Path(root) / 'data/raw/study-v7'
    plan = read(raw / 'request-plan-v7.0.2.json')
    saved = read(ROOT / 'results/study-v7-execution/primary-analysis.json')
    groups = defaultdict(dict)
    for cell in plan['cells']:
        if not (cell['source'] == 'browsesafe' and cell['config'] in ('jev_firstparty', 'luna_decisions')
                and cell['split'] == 'confirmation' and cell['namespace'] == 'first'):
            continue
        result = read(raw / 'execution-v1/attempts' / cell['request_key'] / 'completed.json')
        parsed = result['parsed']
        assert result['request_sha256'] == plan['requests'][cell['request_key']]['payload_sha256']
        groups[cell['group_id']][cell['config'], cell['condition'], cell['upstream_label']] = (
            int(parsed['prediction'] != cell['upstream_label']) if parsed['valid'] else None)
    complete = sorted(g for g, values in groups.items() if all(v is not None for v in values.values()))
    assert len(groups) == 3000 and complete == saved['primary_complete_group_ids']
    estimates, pvalues = [], []
    for entry in saved['contrasts']:
        m, c = entry['config'], entry['control']
        values = [difference(contrast(groups[g], m, c)) for g in complete]
        mean = float(np.mean(values))
        p = float(stats.ttest_1samp(values, 0).pvalue)
        pvalues.append(p)
        assert abs(mean - entry['primary']['test']['mean']) < 1e-14
        assert np.allclose(bounds(groups, m, c), entry['all_planned_error_difference_bounds'], atol=1e-14, rtol=0)
        estimates.append({'model': m, 'control': c, 'mean_pp': 100 * mean, 'p_raw': p})
    adjusted = [None] * 6
    prior = 0
    for rank, i in enumerate(sorted(range(6), key=lambda i: pvalues[i])):
        prior = max(prior, min(1, (6 - rank) * pvalues[i]))
        adjusted[i] = prior
    for out, entry, p in zip(estimates, saved['contrasts'], adjusted):
        out['p_holm6'] = p
        assert abs(p - entry['primary']['holm6']['adjusted_p']) < 1e-12
    return {'first_cells_read': sum(map(len, groups.values())), 'planned_groups': len(groups),
            'shared_groups': len(complete), 'contrasts': estimates,
            'scope': 'Independent arithmetic from retained parsed first attempts; no full native raw reparse'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--followup-root', type=Path)
    parser.add_argument('--v7-root', type=Path)
    args = parser.parse_args()
    result = compact_review()
    if args.followup_root:
        result['raw_spotcheck'] = raw_spotcheck(args.followup_root)
    if args.v7_root:
        result['native_arithmetic'] = native_review(args.v7_root)
    write_new(args.output, result)
    print('Offline review passed; wrote', args.output)
    print('Sampling diagnostics:', json.dumps(result['core_sampling_replay'], sort_keys=True))
    print('Seeded core replay differences:', json.dumps(result['seeded_core_replay_differences'], sort_keys=True))


if __name__ == '__main__':
    main()
