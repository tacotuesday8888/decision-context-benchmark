"""Independent provenance, partition and duplicate checks; no inference."""
import json
import re
from collections import defaultdict
from pathlib import Path
from source_audit import content, normalize, sha

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/extension-v3'
RAW = ROOT / 'data/raw/extension-v3'


def read(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def shingles(text):
    words = re.findall(r'\w+', text.casefold())
    return {tuple(words[i:i + 5]) for i in range(max(0, len(words) - 4))}


def validate():
    raw = RAW / 'prepared-collection-v1.jsonl'
    rows = read(raw)
    summary = json.loads((OUT / 'collection-summary-v1.json').read_text())
    assert sha(raw.read_bytes()) == summary['collection_sha256']
    manifest = read(OUT / 'collection-manifest-v1.jsonl')
    assert manifest == [{k: v for k, v in r.items() if k not in ('candidate', 'trusted_task')} for r in rows]
    assert len({r['id'] for r in rows}) == len(rows)
    cache = {}
    for row in rows:
        assert row['split'] == 'confirmation' and row['license'] == 'MIT'
        assert row['conditions'] == ['candidate', 'task']
        source = row['source']
        if row['dataset'].startswith('injecagent'):
            path = RAW / 'InjecAgent' / source['path']
        elif row['dataset'].startswith('agentdyn'):
            path = RAW / 'AgentDyn' / source['path']
        else:
            path = RAW / source['path']
        if path not in cache:
            assert sha(path.read_bytes()) == source['file_sha256']
            cache[path] = read(path) if path.suffix == '.jsonl' else json.loads(path.read_text())
        original = cache[path]
        if row['dataset'].startswith('injecagent'):
            original = original[source['row_index']]
            candidate, task, label = original['Tool Response'], original['User Instruction'], 1
        elif row['dataset'].startswith('agentdyn'):
            assert original['user_task_id'].startswith('user_task_')
            candidate = content(original['messages'][source['message_index']])
            task = next(content(m) for m in original['messages'] if m['role'] == 'user')
            label = int(bool(original['attack_type']))
            if label:
                assert any(normalize(value) in normalize(candidate) for value in original['injections'].values())
            else:
                assert original['injections'] == {}
        else:
            original = original[source['row_index']]
            assert original['label_evidence'] == 'default_environment_ground_truth_replay_no_injection'
            candidate, task, label = original['candidate'], original['trusted_task'], 0
        assert (row['candidate'], row['trusted_task'], row['gold']) == (candidate, task, label)
        assert sha(candidate) == row['candidate_sha256'] and sha(task) == row['task_sha256']

    prior = read(ROOT / 'data/expanded-v2/collection.jsonl') + read(ROOT / 'data/pilot.jsonl')
    prior_shingles = [(r['id'], shingles(r['candidate'])) for r in prior]
    overlaps = []
    unique = {r['candidate_sha256']: r for r in rows}
    for row in unique.values():
        current = shingles(row['candidate'])
        if not current:
            continue
        for old_id, old in prior_shingles:
            if not old or min(len(current), len(old)) / max(len(current), len(old)) < .8:
                continue
            intersection = len(current & old)
            similarity = intersection / (len(current) + len(old) - intersection)
            if similarity >= .8:
                overlaps.append({'new_id': row['id'], 'old_id': old_id, 'jaccard': similarity})
    assert not overlaps, 'Near-duplicate previous-study contamination requires exclusion/version update'
    # Report shared text across tasks instead of falsely claiming independent rows.
    tasks_per_text = defaultdict(set)
    labels_per_text = defaultdict(set)
    for row in rows:
        tasks_per_text[row['normalized_sha256']].add(row['groups']['task'])
        labels_per_text[row['normalized_sha256']].add(row['gold'])
    assert all(len(labels) == 1 for labels in labels_per_text.values()), 'Context-sensitive conflicting labels require review'
    return {'status': 'passed', 'rows_checked': len(rows), 'source_files_checked': len(cache),
        'distinct_texts_checked': len(unique), 'prior_examples_checked': len(prior),
        'prior_5gram_jaccard_08_overlaps': overlaps,
        'texts_shared_between_tasks': sum(len(tasks) > 1 for tasks in tasks_per_text.values()),
        'maximum_tasks_sharing_text': max(map(len, tasks_per_text.values())),
        'injecagent_attack_instructions_covered': len({r['groups']['attack_family'] for r in rows if r['dataset'].startswith('injecagent')}),
        'collection_sha256': sha(raw.read_bytes()),
        'limitation': 'Checks source fidelity and source-construction labels; not independent human relabeling or proof of real-world maliciousness.'}


if __name__ == '__main__':
    report = validate()
    (OUT / 'collection-validation-v1.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps(report, indent=2))
