"""Paired descriptive development audit. No selection or significance claims."""
from collections import defaultdict
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3/local-diagnostic-v1'


def analyze():
    frozen = json.loads((OUT / 'freeze.json').read_text())
    baseline = {}
    for model in ('laya', 'nimble'):
        for path in (ROOT / 'results/expanded-execution/checks' / (model + '_local')).glob('*-0.json'):
            r = json.loads(path.read_text())
            if r['split'] != 'dev':
                raise ValueError('Non-development baseline')
            baseline[(model, r['id'], r['condition'])] = (str(path.relative_to(ROOT)), r['parsed'])
    observations, groups = [], defaultdict(list)
    for path in sorted(OUT.glob('*.json')):
        r = json.loads(path.read_text())
        if 'job' not in r:
            continue
        j = r['job']
        if j not in frozen['jobs'] or j['split'] != 'dev' or r['status'] != 'completed':
            raise ValueError('Unplanned, non-development or incomplete record')
        bp, old = baseline[(j['model'], j['id'], j['condition'])]
        new = r['parsed']
        observations.append({k: j[k] for k in ('model', 'variant', 'id', 'condition', 'dataset', 'gold')} | {
            'record': str(path.relative_to(ROOT)), 'baseline_record': bp,
            'old_score': old['score'], 'new_score': new['score'],
            'old_prediction': old['prediction'], 'new_prediction': new['prediction'],
            'brier_change': (new['score'] - j['gold']) ** 2 - (old['score'] - j['gold']) ** 2,
        })
    if len(observations) != len(frozen['jobs']):
        raise ValueError('Incomplete diagnostic')
    for row in observations:
        groups[(row['model'], row['variant'], row['dataset'], row['condition'])].append(row)
    summaries = []
    for (model, variant, dataset, condition), rows in sorted(groups.items()):
        summaries.append({'model': model, 'variant': variant, 'dataset': dataset, 'condition': condition,
            'n': len(rows), 'prediction_changes': sum(r['old_prediction'] != r['new_prediction'] for r in rows),
            'old_errors': sum(r['old_prediction'] != r['gold'] for r in rows),
            'new_errors': sum(r['new_prediction'] != r['gold'] for r in rows),
            'mean_brier_change': sum(r['brier_change'] for r in rows) / len(rows)})
    return {'status': 'complete', 'new_requests': len(observations), 'distinct_candidates': 7,
            'paid_cost_usd': 0, 'held_out_requests': 0, 'by_source_condition': summaries,
            'observations': observations,
            'interpretation': 'Operationally selected tiny development sample; descriptive sensitivity only. Negative Brier change means improvement on these cells, not generalization.'}


if __name__ == '__main__':
    summary = analyze()
    (OUT / 'summary.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: v for k, v in summary.items() if k not in ('observations', 'by_source_condition')}, indent=2))
