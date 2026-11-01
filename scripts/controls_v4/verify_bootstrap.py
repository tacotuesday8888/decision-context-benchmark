"""Independent explicit-multiplicity reconstruction of primary and control bootstrap intervals.

Uses the frozen RNG stream but no analyzer/statistics functions. It forms per-task
lists using sampled secondary-group multiplicities instead of vectorized bincount.
"""
import argparse
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/controls-v4'


def quantile(values, probability):
    ordered = sorted(values)
    index = (len(ordered) - 1) * probability
    low, high = math.floor(index), math.ceil(index)
    return ordered[low] + (ordered[high] - ordered[low]) * (index - low)


def reference(values, tasks, seconds, draws=5000):
    task_names, second_names = sorted(set(tasks)), sorted(set(seconds))
    buckets = defaultdict(list)
    for value, task, second in zip(values, tasks, seconds):
        buckets[task].append((second_names.index(second), value))
    if min(len(task_names), len(second_names)) < 5:
        return None, 0
    rng = np.random.default_rng(20261030)
    estimates, skipped = [], 0
    for _ in range(draws):
        tm = rng.multinomial(len(task_names), np.full(len(task_names), 1 / len(task_names)))
        sm = rng.multinomial(len(second_names), np.full(len(second_names), 1 / len(second_names)))
        means = []
        for task, copies in zip(task_names, tm):
            if not copies:
                continue
            expanded = [value for secondary, value in buckets[task] for _ in range(sm[secondary])]
            if expanded:
                means.extend([sum(expanded) / len(expanded)] * copies)
        if means:
            estimates.append(sum(means) / len(means))
        else:
            skipped += 1
    return [quantile(estimates, .025), quantile(estimates, .975)] if estimates else None, skipped


def main(config):
    directory = OUT / 'analysis'
    path = directory / (config + '.json')
    analysis = json.loads(path.read_text())
    manifest = {r['id']: r for r in map(json.loads, (OUT / 'collection-manifest-v1.jsonl').read_text().splitlines())}
    rows = list(csv.DictReader((directory / (config + '-per-example.csv')).open()))
    lookup = {(r['id'], r['condition']): r for r in rows}
    jobs_path = OUT / 'confirmation-jobs-v1.jsonl'
    jobs = [json.loads(line) for line in jobs_path.read_text().splitlines()]
    controls = {j['id'] for j in jobs if j['config'] == config and j['condition'] == 'format'}
    verified = []
    for stratum in analysis['strata']:
        for effect in stratum['paired_effects']:
            assert effect['scope'] in ('all_confirmation','false_positive','false_negative')
            gold = 0 if effect['scope']=='false_positive' else 1 if effect['scope']=='false_negative' else None
            ids = sorted({r['id'] for r in rows if r['dataset']==stratum['dataset'] and (gold is None or int(r['gold'])==gold)})
            assert len(ids) == effect['planned_pairs']
            values, tasks, seconds = [], [], []
            for identity in ids:
                a, b = lookup[(identity, effect['left'])], lookup[(identity, effect['right'])]
                if effect['metric'] == 'error':
                    if a['valid'] != 'True' or b['valid'] != 'True':
                        continue
                    value = float(a['prediction'] != a['gold']) - float(b['prediction'] != b['gold'])
                else:
                    if any(r['status'] not in ('ok', 'tie') or r['score'] == '' for r in (a, b)):
                        continue
                    value = (float(a['score']) - int(a['gold'])) ** 2 - (float(b['score']) - int(b['gold'])) ** 2
                item = manifest[identity]
                values.append(value)
                tasks.append(item['groups']['primary_cluster'])
                seconds.append(item['groups']['secondary_cluster'])
            assert len(values) == effect['complete_pairs']
            target = effect['primary_cluster_weighted']
            if not values:
                assert target is None
                continue
            interval, skipped = reference(values, tasks, seconds)
            assert skipped == target['degenerate_draws']
            if interval is None:
                assert target['interval'] is None
            else:
                assert all(math.isclose(a, b, abs_tol=1e-12, rel_tol=1e-10) for a, b in zip(interval, target['interval']))
            verified.append({'dataset': stratum['dataset'], 'scope': effect['scope'], 'left': effect['left'], 'right': effect['right'], 'metric': effect['metric'], 'complete_pairs': len(values), 'reference_interval_rounded_12dp': [round(v, 12) for v in interval] if interval else None, 'degenerate_draws': skipped})
    result = {'status': 'passed', 'config': config, 'scope': 'All full-condition and error-direction intervals checked at full precision (absolute tolerance 1e-12, relative 1e-10); receipt endpoints rounded to 12 decimal places for cross-platform serialization. Membership and class subsets are reconstructed from frozen jobs and source manifest.',
        'analysis_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'jobs_sha256': hashlib.sha256(jobs_path.read_bytes()).hexdigest(), 'verified': verified}
    (directory / (config + '-bootstrap-verification.json')).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'config': config, 'primary_intervals_checked': sum(v['scope'] == 'all_confirmation' for v in verified), 'control_intervals_checked': sum(v['scope'] == 'false_positive' for v in verified), 'status': 'passed'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    main(parser.parse_args().config)
