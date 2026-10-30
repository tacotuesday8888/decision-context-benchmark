"""Analyze completed arms only, using the predeclared source-specific estimands."""
import argparse
import csv
import importlib.util
import json
from collections import defaultdict
from pathlib import Path
import numpy as np
from source_audit import sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'
spec = importlib.util.spec_from_file_location('extension_metrics', Path(__file__).with_name('statistics.py'))
metrics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(metrics)


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def collect(config):
    manifest = {r['id']: r for r in read(OUT / 'collection-manifest-v1.jsonl')}
    jobs = [j for j in read(OUT / 'confirmation-jobs-v1.jsonl') if j['config'] == config]
    if not jobs:
        raise ValueError('Unknown configuration')
    snapshot = OUT / 'analysis' / (config + '-ledger.json')
    ledger_path = snapshot if snapshot.exists() else OUT / 'inference-ledger-v1.json'
    ledger = {e['key']: e for e in json.loads(ledger_path.read_text())['entries']}
    used_entries = []
    rows = []
    for job in jobs:
        key = sha(json.dumps(job, sort_keys=True))[:24]
        path = OUT / 'confirmation' / config / (key + '.json')
        if not path.exists():
            raise ValueError('Arm incomplete: missing ' + key)
        record = json.loads(path.read_text())
        if record['job'] != job or record['status'] not in ('completed', 'failed'):
            raise ValueError('Arm contains unplanned or in-flight evidence')
        entry = ledger['confirmation:' + config + ':' + key]
        used_entries.append(entry)
        if entry['status'] != 'settled':
            raise ValueError('Arm still has an unsettled reservation')
        datum = manifest[job['id']]
        parsed = record.get('parsed', {})
        row = dict(job, dataset=datum['dataset'], gold=datum['gold'], groups=datum['groups'],
            candidate_sha256=datum['candidate_sha256'],
            record_path=str(path.relative_to(ROOT)), record_sha256=sha(path.read_bytes()),
            status=parsed.get('status', 'runtime_error'), valid=parsed.get('valid', False),
            prediction=parsed.get('prediction'), score=parsed.get('score'),
            elapsed_seconds=record['elapsed_seconds'], usage=parsed.get('usage', {}),
            access_route=record['access_route'], windows=parsed.get('windows'),
            conservative_accounted_usd=entry['accounted_usd'])
        if config in ('luna_chat', 'astra_chat') and row['score'] is not None:
            raise ValueError('Boolean arm unexpectedly carries probability')
        rows.append(row)
    if not snapshot.exists():
        snapshot.parent.mkdir(exist_ok=True)
        snapshot.write_text(json.dumps({'scope': 'Settled entries for this completed confirmation arm only; not final all-provider accounting.', 'entries': used_entries}, indent=2, sort_keys=True) + '\n')
    return rows


def paired(rows, left, right, metric):
    lookup = {(r['id'], r['condition']): r for r in rows}
    ids = sorted({r['id'] for r in rows if (r['id'], left) in lookup and (r['id'], right) in lookup})
    values, tasks, texts, second = [], [], [], []
    lower, upper, all_tasks = [], [], []
    for identity in ids:
        a, b = lookup[(identity, left)], lookup[(identity, right)]

        def value(r):
            if metric == 'error':
                return float(r['prediction'] != r['gold']) if r['valid'] else None
            if r['status'] in ('ok', 'tie') and metrics.valid_probability(r['score']):
                return metrics.losses(r['gold'], r['score'])['brier']
            return None

        av, bv = value(a), value(b)
        lower.append((av if av is not None else 0) - (bv if bv is not None else 1))
        upper.append((av if av is not None else 1) - (bv if bv is not None else 0))
        all_tasks.append(a['groups']['task'])
        if av is None or bv is None:
            continue
        values.append(av - bv)
        tasks.append(a['groups']['task'])
        texts.append(a['candidate_sha256'])
        second.append(a['groups']['attack_family'] if a['dataset'].startswith('injecagent') else a['candidate_sha256'])
    result = {'left': left, 'right': right, 'metric': metric, 'planned_pairs': len(ids),
              'complete_pairs': len(values), 'negative_means': 'lower error/Brier with left condition'}
    if values:
        result.update(task_weighted=metrics.crossed_interval(values, tasks, second),
                      text_weighted_estimate=metrics.text_mean(values, texts),
                      unweighted_estimate=float(np.mean(values)))
    else:
        result.update(task_weighted=None, text_weighted_estimate=None, unweighted_estimate=None)
    result['all_planned_task_weighted_bounds'] = [metrics.task_mean(lower, all_tasks), metrics.task_mean(upper, all_tasks)] if ids else None
    return result


def analyze(config):
    rows = collect(config)
    groups = defaultdict(list)
    for row in rows:
        groups[row['dataset']].append(row)
    result = {'config': config, 'status': 'completed_arm_only', 'logical_requests': len(rows),
        'distinct_candidates': len({r['candidate_sha256'] for r in rows}),
        'task_candidate_pairs': len({r['id'] for r in rows}),
        'record_hashes': {r['record_path']: r['record_sha256'] for r in rows},
        'strata': [], 'interpretation': 'No pooled winner; conditional source-specific estimates. Other arms may still be running.'}
    for name, part in sorted(groups.items()):
        conditions = []
        for condition in ('candidate', 'task', 'format', 'reminder', 'scrambled'):
            selected = [r for r in part if r['condition'] == condition]
            if not selected:
                continue
            scores = metrics.forecast(selected)
            scores['interpretation'] = ('Unavailable: Boolean outputs' if config in ('luna_chat', 'astra_chat') else 'Uncalibrated maximum detector window score' if config == 'protectai_local' else 'Native probability forecast; no calibration assumed')
            conditions.append({'condition': condition, **metrics.classification(selected), 'forecast': scores})
        effects = []
        if config != 'protectai_local':
            effects.append({'scope': 'full_collection', **paired(part, 'task', 'candidate', 'error')})
            if config not in ('luna_chat', 'astra_chat'):
                effects.append({'scope': 'full_collection', **paired(part, 'task', 'candidate', 'brier')})
            control_ids = {r['id'] for r in part if r['condition'] == 'format'}
            subset = [r for r in part if r['id'] in control_ids]
            for comparator in ('candidate', 'format', 'reminder', 'scrambled'):
                for metric in (['error'] if config in ('luna_chat', 'astra_chat') else ['error', 'brier']):
                    effects.append({'scope': 'preselected_controls', **paired(subset, 'task', comparator, metric)})
        result['strata'].append({'dataset': name, 'conditions': conditions, 'paired_effects': effects})
    directory = OUT / 'analysis'
    directory.mkdir(exist_ok=True)
    (directory / (config + '.json')).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    fields = ['config', 'dataset', 'id', 'condition', 'gold', 'status', 'valid', 'prediction', 'score',
              'candidate_sha256', 'record_path', 'elapsed_seconds', 'access_route', 'windows', 'conservative_accounted_usd']
    with (directory / (config + '-per-example.csv')).open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction='ignore', lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)
    print(json.dumps({'config': config, 'analyzed_requests': len(rows), 'source_strata': len(groups)}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    analyze(parser.parse_args().config)
