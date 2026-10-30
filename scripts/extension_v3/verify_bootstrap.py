"""Independent explicit-multiplicity reconstruction of primary bootstrap intervals.

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
OUT = ROOT / 'results/extension-v3'


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
    rng = np.random.default_rng(20261029)
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
    verified = []
    for stratum in analysis['strata']:
        for effect in stratum['paired_effects']:
            if effect['scope'] != 'full_collection':
                continue
            ids = sorted({r['id'] for r in rows if r['dataset'] == stratum['dataset']})
            values, tasks, seconds = [], [], []
            for identity in ids:
                a, b = lookup[(identity, 'task')], lookup[(identity, 'candidate')]
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
                tasks.append(item['groups']['task'])
                seconds.append(item['groups']['attack_family'] if item['dataset'].startswith('injecagent') else item['candidate_sha256'])
            target = effect['task_weighted']
            if not values:
                assert target is None
                continue
            interval, skipped = reference(values, tasks, seconds)
            assert skipped == target['degenerate_draws']
            if interval is None:
                assert target['interval'] is None
            else:
                assert all(math.isclose(a, b, abs_tol=1e-12, rel_tol=1e-10) for a, b in zip(interval, target['interval']))
            verified.append({'dataset': stratum['dataset'], 'metric': effect['metric'], 'complete_pairs': len(values), 'interval': interval, 'degenerate_draws': skipped})
    result = {'status': 'passed', 'config': config, 'scope': 'All primary full-collection intervals; control intervals share the tested estimator but are not independently recomputed here.',
        'analysis_sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'verifier_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'verified': verified}
    (directory / (config + '-bootstrap-verification.json')).write_text(json.dumps(result, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'config': config, 'primary_intervals_checked': len(verified), 'status': 'passed'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True)
    main(parser.parse_args().config)
