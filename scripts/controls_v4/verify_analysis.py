"""Independent stdlib arithmetic verification from immutable raw records.

Does not import the analyzer or its numerical estimator implementation. Bootstrap
intervals remain covered by estimator tests; this checks underlying denominators,
point estimates, missing-response bounds, reliability bins and record hashes.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/controls-v4'


def mean(values):
    return sum(values) / len(values) if values else None


def grouped(values, keys):
    buckets = defaultdict(list)
    for value, key in zip(values, keys):
        buckets[key].append(value)
    return mean([mean(v) for v in buckets.values()])


def equal(actual, expected):
    if expected is None:
        assert actual is None, (actual, expected)
    elif isinstance(expected, float):
        assert math.isclose(actual, expected, rel_tol=1e-10, abs_tol=1e-12), (actual, expected)
    else:
        assert actual == expected, (actual, expected)


def loss(row, metric):
    parsed = row['parsed']
    if metric == 'error':
        return float(parsed['prediction'] != row['gold']) if parsed.get('valid') else None
    score = parsed.get('score')
    if parsed.get('status') in ('ok', 'tie') and type(score) in (int, float) and math.isfinite(score) and 0 <= score <= 1:
        return (score - row['gold']) ** 2
    return None


def verify(config):
    report_path = OUT / 'analysis' / (config + '.json')
    report = json.loads(report_path.read_text())
    manifest = {r['id']: r for r in map(json.loads, (OUT / 'collection-manifest-v1.jsonl').read_text().splitlines())}
    jobs = [r for r in map(json.loads, (OUT / 'confirmation-jobs-v1.jsonl').read_text().splitlines()) if r['config'] == config]
    rows = []
    paths = set()
    csv_path = OUT / 'analysis' / (config + '-per-example.csv')
    csv_rows = list(csv.DictReader(csv_path.open()))
    csv_lookup = {(r['id'], r['condition']): r for r in csv_rows}
    assert len(csv_rows) == len(csv_lookup) == len(jobs)
    ledger = {r['key']: r for r in json.loads((OUT / 'analysis' / (config + '-ledger.json')).read_text())['entries']}
    for job in jobs:
        key = hashlib.sha256(json.dumps(job, sort_keys=True).encode()).hexdigest()[:24]
        path = OUT / 'confirmation' / config / (key + '.json')
        relative = str(path.relative_to(ROOT))
        paths.add(relative)
        equal(hashlib.sha256(path.read_bytes()).hexdigest(), report['record_hashes'][relative])
        record = json.loads(path.read_text())
        equal(record['job'], job)
        assert record['status'] in ('completed', 'failed')
        parsed = record.get('parsed', {})
        csv_row = csv_lookup[(job['id'], job['condition'])]
        datum = manifest[job['id']]
        expected_csv = dict(config=config, dataset=datum['dataset'], id=job['id'], condition=job['condition'],
            gold=datum['gold'], status=parsed.get('status', 'runtime_error'), valid=parsed.get('valid', False),
            prediction=parsed.get('prediction'), score=parsed.get('score'), candidate_sha256=datum['candidate_sha256'],
            record_path=relative, elapsed_seconds=record['elapsed_seconds'], access_route=record['access_route'],
            windows=parsed.get('windows'), conservative_accounted_usd=ledger['confirmation:'+config+':'+key]['accounted_usd'])
        assert csv_row == {k:'' if v is None else str(v) for k,v in expected_csv.items()}, relative
        rows.append(dict(manifest[job['id']], condition=job['condition'], parsed=record.get('parsed', {})))
    equal(paths, set(report['record_hashes']))
    equal(report['logical_requests'], len(rows))
    equal(report['distinct_candidates'], len({r['candidate_sha256'] for r in rows}))
    equal(report['task_candidate_pairs'], len({r['id'] for r in rows}))
    equal({s['dataset'] for s in report['strata']}, {r['dataset'] for r in rows})
    comparisons = 0
    for stratum in report['strata']:
        part = [r for r in rows if r['dataset'] == stratum['dataset']]
        for condition in stratum['conditions']:
            selected = [r for r in part if r['condition'] == condition['condition']]
            valid = [r for r in selected if r['parsed'].get('valid')]
            negatives = [r for r in valid if r['gold'] == 0]
            positives = [r for r in valid if r['gold'] == 1]
            fp = sum(r['parsed']['prediction'] == 1 for r in negatives)
            fn = sum(r['parsed']['prediction'] == 0 for r in positives)
            for field, expected in dict(planned=len(selected), valid=len(valid), negative_valid=len(negatives), positive_valid=len(positives), false_positives=fp, false_negatives=fn,
                abstentions=sum(r['parsed'].get('status') == 'tie' for r in selected),
                operational_or_missing=sum(r['parsed'].get('status') not in ('ok', 'tie') for r in selected)).items():
                equal(condition[field], expected)
            fpr = fp / len(negatives) if negatives else None
            fnr = fn / len(positives) if positives else None
            equal(condition['fpr'], fpr)
            equal(condition['fnr'], fnr)
            equal(condition['balanced_accuracy'], 1 - (fpr + fnr) / 2 if fpr is not None and fnr is not None else None)
            correct = len(valid) - fp - fn
            for actual, expected in zip(condition['accuracy_bounds_all_planned'], [correct / len(selected), (correct + len(selected) - len(valid)) / len(selected)]):
                equal(actual, expected)
            forecast = [r for r in selected if loss(r, 'brier') is not None]
            scores = condition['forecast']
            equal(scores['n_forecasts'], len(forecast))
            equal(scores['brier'], mean([loss(r, 'brier') for r in forecast]))
            logs = []
            for row in forecast:
                p = max(1e-6, min(1 - 1e-6, row['parsed']['score']))
                logs.append(-math.log(p if row['gold'] else 1 - p))
            equal(scores['log_loss'], mean(logs))
            for index, bucket in enumerate(scores['reliability']):
                members = [r for r in forecast if min(9, int(10 * r['parsed']['score'])) == index]
                equal(bucket['n'], len(members))
                equal(bucket['mean_score'], mean([r['parsed']['score'] for r in members]))
                equal(bucket['observed_fraction'], mean([r['gold'] for r in members]))
        lookup = {(r['id'], r['condition']): r for r in part}
        for effect in stratum['paired_effects']:
            ids = {r['id'] for r in part}
            if effect['scope'] in ('false_positive','false_negative'):
                gold = 0 if effect['scope']=='false_positive' else 1
                ids = {r['id'] for r in part if r['gold']==gold}
            values, tasks, texts, lower, upper, all_tasks, original_tasks = [], [], [], [], [], [], []
            for identity in sorted(ids):
                a, b = lookup[(identity, effect['left'])], lookup[(identity, effect['right'])]
                av, bv = loss(a, effect['metric']), loss(b, effect['metric'])
                all_tasks.append(a['groups']['primary_cluster'])
                lower.append((av if av is not None else 0) - (bv if bv is not None else 1))
                upper.append((av if av is not None else 1) - (bv if bv is not None else 0))
                if av is not None and bv is not None:
                    values.append(av - bv)
                    tasks.append(a['groups']['primary_cluster'])
                    original_tasks.append(a['groups']['task'])
                    texts.append(a['candidate_sha256'])
            equal(effect['planned_pairs'], len(ids))
            equal(effect['complete_pairs'], len(values))
            equal(effect['unweighted_estimate'], mean(values))
            equal(effect['text_weighted_estimate'], grouped(values, texts))
            equal(effect['equal_task_estimate'], grouped(values, original_tasks))
            equal(effect['primary_cluster_weighted']['estimate'] if effect['primary_cluster_weighted'] else None, grouped(values, tasks))
            for actual, expected in zip(effect['all_planned_primary_cluster_weighted_bounds'], [grouped(lower, all_tasks), grouped(upper, all_tasks)]):
                equal(actual, expected)
            comparisons += 1
    receipt = {'config': config, 'raw_records_checked': len(rows), 'csv_rows_checked': len(csv_rows), 'paired_comparisons_checked': comparisons,
        'analysis_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'status': 'passed', 'scope': 'Independent raw-record point estimates, denominators, bounds and reliability arithmetic; bootstrap implementation separately unit-tested.'}
    (OUT / 'analysis' / (config + '-verification.json')).write_text(json.dumps(receipt, indent=2, sort_keys=True) + '\n')
    print(json.dumps(receipt))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    verify(parser.parse_args().config)
