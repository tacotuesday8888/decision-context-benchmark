"""Exploratory paired forecasts; offline, fixed bins, no evaluation fitting.

Draw weights are generated from the complete source stratum, independently of model
outputs. Missing forecasts get zero weight only at aggregation, never fabricated scores.
"""
import json
import math
from functools import lru_cache
import numpy as np
from execute import OUT, DATA, PANEL, jsonl, save, sha, verify_preparation
from probability_metrics import forecast_metrics

SEED = 20261026
DRAWS = 10000


def native_score(cell):
    if not cell or cell.get('status') not in ('ok', 'tie'):
        return None
    p = cell.get('score')
    return float(p) if not isinstance(p, bool) and isinstance(p, (int, float)) and math.isfinite(p) and 0 <= p <= 1 else None


@lru_cache(maxsize=32)
def draw_weights(signature, draws=DRAWS):
    """Identical full-stratum cluster draws across conditions and models."""
    rng = np.random.default_rng(SEED)
    weights = np.zeros((draws, len(signature)), dtype=np.int16)
    units = []
    for stratum in sorted({s[0] for s in signature}):
        indices = [i for i, s in enumerate(signature) if s[0] == stratum]
        keys = sorted({signature[i][1] for i in indices})
        w = rng.multinomial(len(keys), np.full(len(keys), 1 / len(keys)), size=draws)
        for i in indices:
            weights[:, i] = w[:, keys.index(signature[i][1])]
        units.append({'stratum': stratum, 'clusters': len(keys)})
    return weights, units


def design(rows, axis):
    if axis in ('document', 'attack_family'):
        signature = tuple(('all', r['groups'][axis]) for r in rows)
    else:
        signature = tuple((str(r['gold']), r['groups']['team' if r['gold'] else ('topic' if 'topic' in r['groups'] else 'fixture')]) for r in rows)
    return signature


def interval(rows, values, axis):
    """Mean over available paired candidates; absent values stay absent."""
    signature = design(rows, axis)
    weights, units = draw_weights(signature)
    selected = np.array([v is not None for v in values])
    occupied = {s: len({signature[i][1] for i in range(len(rows)) if selected[i] and signature[i][0] == s}) for s in {x[0] for x in signature}}
    result = {'axis': axis, 'units': units, 'observed_clusters': occupied, 'interval': None}
    if not selected.any() or any(n < 2 for n in occupied.values()):
        return dict(result, reason='Fewer than two observed clusters in at least one class/stratum; no population interval')
    denominator = weights[:, selected].sum(axis=1)
    numerator = weights @ np.array([0.0 if v is None else v for v in values])
    keep = denominator > 0
    return dict(result, interval=np.quantile(numerator[keep] / denominator[keep], [.025, .975]).tolist(), draws=DRAWS, valid_draws=int(keep.sum()))


def axes(rows):
    return ('document', 'attack_family') if rows[0]['dataset'].startswith('bipia-') else ('class_clusters',)


def paired_forecasts(rows, base, other):
    pairs = [(native_score(base.get(r['id'])), native_score(other.get(r['id']))) for r in rows]
    selected = [i for i, (a, b) in enumerate(pairs) if a is not None and b is not None]
    losses = [None if a is None or b is None else (b-r['gold'])**2-(a-r['gold'])**2 for r, (a,b) in zip(rows,pairs)]
    return {'eligible_n': len(rows), 'common_score_n': len(selected),
            'missing_base_n': sum(a is None for a,b in pairs), 'missing_context_n': sum(b is None for a,b in pairs),
            'missing_either_n': len(rows)-len(selected),
            'base': forecast_metrics([(pairs[i][0], rows[i]['gold']) for i in selected]),
            'context': forecast_metrics([(pairs[i][1], rows[i]['gold']) for i in selected]),
            'brier_delta': float(np.mean([v for v in losses if v is not None])) if selected else None,
            'intervals': [interval(rows, losses, a) for a in axes(rows)]}


def reliability(rows, cells):
    scores = [native_score(cells.get(r['id'])) for r in rows]
    result = forecast_metrics([(p, r['gold']) for r,p in zip(rows,scores) if p is not None])
    result['eligible_n'] = len(rows)
    result['missing_score_n'] = len(rows)-result['n']
    for j, bucket in enumerate(result['calibration']):
        values = [r['gold'] if p is not None and min(int(p*5),4)==j else None for r,p in zip(rows,scores)]
        bucket['observed_fraction_intervals'] = [interval(rows,values,a) for a in axes(rows)]
    return result


def main():
    verify_preparation()
    rows = sorted([r for r in jsonl(DATA/'collection.jsonl') if r['split']=='eval'], key=lambda r:r['id'])
    actual = {}; hashes = {}
    for config in PANEL:
        for path in sorted((OUT/'evaluation'/config).glob('*-*.json')):
            record = json.loads(path.read_text())
            if 'parsed' not in record: continue
            hashes[str(path.relative_to(OUT))] = sha(path.read_bytes())
            key = (config,record['id'],record['condition'])
            if key not in actual or record['attempt'] > actual[key]['attempt']: actual[key]=record
    contrasts=[]; summaries=[]
    native = [c for c,p in PANEL.items() if p['kind']!='chat']
    for config in native:
        for dataset in sorted({r['dataset'] for r in rows}):
            source=[r for r in rows if r['dataset']==dataset]
            conditions=['candidate'] if config=='protectai_local' else sorted({c for r in source for c in r['conditions']})
            cells={c:{r['id']:actual[(config,r['id'],c)]['parsed'] for r in source if (config,r['id'],c) in actual} for c in conditions}
            for c in conditions:
                eligible=[r for r in source if c in r['conditions']]
                summaries.append({'config':config,'dataset':dataset,'condition':c,**reliability(eligible,cells[c])})
            for a,b in [('candidate','task'),('candidate','source'),('task','both'),('source','both')]:
                if a not in cells or b not in cells:continue
                eligible=[r for r in source if a in r['conditions'] and b in r['conditions']]
                contrasts.append({'config':config,'dataset':dataset,'contrast':b+' minus '+a,
                    'execution_complete':all((config,r['id'],c) in actual for r in eligible for c in (a,b)),
                    **paired_forecasts(eligible,cells[a],cells[b])})
    save(OUT/'forecast-summary.json',{'analysis_version':'exploratory-forecast-v1','seed':SEED,'draws':DRAWS,
        'probability_analysis_preregistered':False,'scores_imputed':False,'boolean_chats_excluded':True,
        'collection_sha256':sha((DATA/'collection.jsonl').read_bytes()),'record_hashes':hashes,
        'summaries':summaries,'paired_contrasts':contrasts,
        'interval_note':'Pointwise percentile intervals. Fixed source-wide draws shared across models/conditions; missing forecasts excluded with denominators. LLMail classes sampled separately. No population interval for one observed cluster.'})
    print(json.dumps({'forecast_strata':len(summaries),'contrasts':len(contrasts),'record_count':len(hashes)}))

if __name__=='__main__':main()
