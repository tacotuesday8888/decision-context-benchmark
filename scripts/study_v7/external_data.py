"""Pinned PromptShield preparation. Downloads data; never imports inference code."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
import sys
from urllib.request import urlopen

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import Union, near_links, norm

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/study-v7'
OUT = ROOT / 'results/study-v7'
CANONICAL = ROOT.parent / 'Decision Context Benchmark'
SEED = 'study-v7-plan-20261101'
REPO = 'hendzh/PromptShield'
REV = 'a5234cb1f5cdb256600cab64b8c961195b5e8404'
TEST_SHA = '526207c2485829d9961407011d7f4cd929569e7f285dc8396b3f385e0608bc70'
HISTORY = (
    'data/raw/pilot.jsonl', 'data/expanded-v2/collection.jsonl',
    'data/raw/expanded-v2/pre-query-audit-collection.jsonl',
    'data/raw/extension-v3/prepared-collection-v1.jsonl',
    'data/raw/controls-v4/prepared-collection-v1.jsonl',
    'data/raw/study-v5/prepared-review.jsonl', 'data/raw/study-v5/scope-pairs.jsonl',
    'data/raw/study-v6/prepared.jsonl',
    'data/raw/study-v6/browse-train-selected.jsonl',
    'data/raw/source-discovery/spml-review-v1.jsonl',
    'data/raw/source-discovery/aib-review-v1.jsonl',
)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rank(source, purpose, identity):
    return digest('\0'.join((SEED, source, purpose, str(identity))).encode())


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')).encode()


def save(path, data):
    """Never silently rewrite a locked artifact."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() != data:
            raise ValueError(f'Immutable artifact differs: {path.name}')
    else:
        with path.open('xb') as handle:
            handle.write(data)


def write_rows(path, rows):
    save(path, b''.join(canonical(row) + b'\n' for row in rows))


def historical(root=CANONICAL):
    """Only source inputs are read; no response, correctness, or analysis files."""
    unique, receipts = {}, []
    for name in HISTORY:
        path = root / name
        body = path.read_bytes()  # Fail closed on incomplete historical inventory.
        receipt = {'path': name, 'sha256': digest(body), 'empty_candidates': 0}
        receipts.append(receipt)
        for line in body.splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            candidate = (row.get('content_markdown') if name.endswith('browse-train-selected.jsonl')
                         else row.get('detector_payload', {}).get('submitted_user_prompt')
                         if name.endswith('spml-review-v1.jsonl') else row.get('candidate'))
            if name.endswith('aib-review-v1.jsonl'):
                payload=row['detector_payload']
                indexes=set(payload['candidate_message_indexes'])
                candidates=[m['content'] for m in payload['source_conversation_inputs'] if m['original_index'] in indexes]
                if len(candidates)!=len(indexes) or any(not isinstance(c,str) for c in candidates):
                    raise ValueError('Historical AIB source candidate indexes differ')
                for value in candidates:
                    if value.strip():
                        unique.setdefault(norm(value),{'id':'historical:'+digest(value.encode()),'prompt':value,'split':'historical'})
                continue
            if not isinstance(candidate, str):
                raise ValueError('Historical candidate absent')
            if not candidate.strip():
                receipt['empty_candidates'] += 1
                continue  # Cannot be a relative of a nonempty released request.
            unique.setdefault(norm(candidate), {'id': 'historical:' + digest(candidate.encode()),
                                               'prompt': candidate, 'split': 'historical'})
    return list(unique.values()), receipts


def validate(data, split):
    if not isinstance(data, list):
        raise ValueError('Expected released JSON list')
    rows = []
    for i, row in enumerate(data):
        if set(row) != {'prompt', 'label'} or not isinstance(row['prompt'], str):
            raise ValueError('Source schema differs from prompt:str,label:int')
        if type(row['label']) is not int or row['label'] not in (0, 1):
            raise ValueError('Nonbinary original source label')
        if not row['prompt'].strip():
            raise ValueError('Empty source prompt')
        rows.append({'id': f'promptshield:{split}:{i}', 'prompt': row['prompt'],
                     'upstream_label': row['label'], 'split': split, 'source_index': i})
    return rows


def close(rows, history, *, near=.8, historical_near=.5):
    """Global connected closure precedes label quotas or split allocation."""
    all_rows = history + rows
    offset = len(history)
    union, seen, exact_labels, edges = Union(len(all_rows)), {}, collections.defaultdict(set), []
    for i, row in enumerate(all_rows):
        key = norm(row['prompt'])
        if i >= offset:
            exact_labels[key].add(row['upstream_label'])
        if key in seen:
            j = seen[key]
            union.join(i, j)
            edges.append({'a': all_rows[j]['id'], 'b': row['id'], 'kind': 'normalized_exact'})
        else:
            seen[key] = i
    # Collapse exact duplicates before the expensive exact lexical similarity join.
    representatives = list(seen.values())
    historical_reps = [i for i in representatives if i < offset]
    current_reps = [i for i in representatives if i >= offset]
    # Every historical node is already excluded: historical/historical edges add
    # no information. Keep both current/current and historical/current joins exact.
    if len(all_rows) >= 50:
        from scripts.study_v7.main_data import compact_near_links
        current_links = compact_near_links([all_rows[i]['prompt'] for i in current_reps], near)
        combined = historical_reps + current_reps
        cross_links = compact_near_links([all_rows[i]['prompt'] for i in combined], historical_near,
                                        historical_count=len(historical_reps))
        links = [(current_reps[a], current_reps[b], s, 'near') for a,b,s in current_links]
        links += [(combined[a], combined[b], s, 'historical_near') for a,b,s in cross_links]
    else:
        links = []
        for a,b,score in near_links([all_rows[i]['prompt'] for i in representatives], historical_near):
            j,i = representatives[a],representatives[b]
            is_historical = j < offset or i < offset
            if not (j < offset and i < offset) and score >= (historical_near if is_historical else near):
                links.append((j,i,score,'historical_near' if is_historical else 'near'))
    for j,i,score,kind in links:
        union.join(i,j)
        edges.append({'a':all_rows[j]['id'],'b':all_rows[i]['id'],'kind':kind,'jaccard':score})
    contradictory = {key for key, labels in exact_labels.items() if len(labels) > 1}
    components = collections.defaultdict(list)
    for i, row in enumerate(all_rows):
        components[union.find(i)].append((i, row))
    eligible = {'validation': [], 'test': []}
    exclusions, mixed = [], []
    for members in components.values():
        current = [row for i, row in members if i >= offset]
        if not current:
            continue
        gid = 'promptshield-group:' + min(digest(norm(row['prompt']).encode()) for _, row in members)
        splits = {row['split'] for row in current}
        labels = {row['upstream_label'] for row in current}
        reasons = []
        if any(i < offset for i, _ in members):
            reasons.append('historical_component')
        if any(norm(row['prompt']) in contradictory for row in current):
            reasons.append('exact_contradictory_labels')
        # Entire cross-split components are quarantined, making validation/test disjoint.
        if len(splits) > 1:
            reasons.append('cross_split_component')
        if len(labels) > 1:
            mixed.append({'group_id': gid, 'ids': sorted(row['id'] for row in current),
                          'labels': sorted(labels), 'quarantined': bool(reasons)})
        if reasons:
            exclusions.append({'group_id': gid, 'ids': sorted(row['id'] for row in current),
                               'reasons': reasons})
            continue
        representative = min(current, key=lambda row: rank('promptshield', 'representative', row['id']))
        eligible[representative['split']].append({**representative, 'group_id': gid,
                                                 'component_size': len(current)})
    return eligible, edges, exclusions, mixed


def select(eligible, test_per_label=2000, validation_per_label=50):
    selected, used = [], set()
    for split, count in (('validation', validation_per_label), ('test', test_per_label)):
        for label in (0, 1):
            pool = sorted((row for row in eligible[split] if row['upstream_label'] == label),
                          key=lambda row: rank('promptshield', split + ':label:' + str(label), row['id']))
            chosen = [row for row in pool if row['group_id'] not in used][:count]
            if len(chosen) != count:
                raise ValueError(f'Insufficient {split} label {label} components: {len(chosen)} / {count}')
            for row in chosen:
                if row['group_id'] in used:
                    raise AssertionError('Mixed-label component reused')
                used.add(row['group_id'])
                selected.append({
                    'id': row['id'], 'group_id': row['group_id'], 'group': row['group_id'],
                    'candidate': row['prompt'], 'source': 'promptshield',
                    'upstream_label': row['upstream_label'],
                    'partition': 'development' if split == 'validation' else 'confirmation',
                    'general_subset': split == 'validation' or chosen.index(row) < min(500, count),
                    'input_sha256': digest(row['prompt'].encode()),
                    'provenance': {'repository': REPO, 'revision': REV, 'file': split + '.json',
                                   'source_index': row['source_index'], 'component_size': row['component_size']},
                })
    return selected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--historical-root', type=Path, default=CANONICAL)
    args = parser.parse_args()
    rows, receipts = [], []
    for split in ('validation', 'test'):
        path = RAW / 'promptshield-source' / (split + '.json')
        if not path.exists():
            with urlopen(f'https://huggingface.co/datasets/{REPO}/resolve/{REV}/{split}.json', timeout=120) as handle:
                save(path, handle.read())
        body = path.read_bytes()
        if split == 'test' and digest(body) != TEST_SHA:
            raise ValueError('Pinned PromptShield test SHA256 differs')
        parsed = validate(json.loads(body), split)
        if split == 'test' and (len(parsed) != 23516 or collections.Counter(r['upstream_label'] for r in parsed) != {0:17030, 1:6486}):
            raise ValueError('Pinned test counts differ')
        rows.extend(parsed)
        receipts.append({'file': split + '.json', 'sha256': digest(body), 'bytes': len(body),
                         'rows': len(parsed), 'labels': dict(collections.Counter(r['upstream_label'] for r in parsed))})
    history, historical_receipts = historical(args.historical_root)
    print(f'Closing {len(rows)} released inputs against {len(history)} unique historical inputs.', flush=True)
    eligible, edges, exclusions, mixed = close(rows, history)
    selected = select(eligible)
    write_rows(RAW / 'external-selected-v3.jsonl', selected)
    write_rows(RAW / 'external-edges-v3.jsonl', edges)
    write_rows(RAW / 'external-exclusions-v3.jsonl', exclusions)
    write_rows(RAW / 'external-semantic-concerns-v3.jsonl', mixed)
    record = {'version': 'study-v7-external-selection-3', 'seed': SEED, 'repository': REPO, 'revision': REV,
              'supersedes': 'external-selection-v2.json; adds every individual prior AIB candidate message, including constituents of multi-message historical candidates; earlier receipts retained',
              'source_receipts': receipts, 'historical_receipts': historical_receipts,
              'historical_unique_inputs': len(history), 'near_jaccard': .8, 'historical_near_jaccard': .5,
              'minimum_distinct_trigrams': 5, 'edge_count': len(edges), 'excluded_components': len(exclusions),
              'mixed_label_components': len(mixed), 'eligible_components': {key:dict(collections.Counter(r['upstream_label'] for r in val)) for key,val in eligible.items()},
              'selected_counts': {part:dict(collections.Counter(r['upstream_label'] for r in selected if r['partition']==part)) for part in ('development','confirmation')},
              'general_confirmation_rows': sum(r['general_subset'] and r['partition']=='confirmation' for r in selected),
              'selected': [{key: row[key] for key in ('id','group_id','partition','upstream_label','general_subset','input_sha256','provenance')} for row in selected],
              'artifacts': {name:digest((RAW/name).read_bytes()) for name in ('external-selected-v3.jsonl','external-edges-v3.jsonl','external-exclusions-v3.jsonl','external-semantic-concerns-v3.jsonl')},
              'inference_calls': 0, 'labels': 'Original published labels; semantic concerns do not change them.',
              'limitations': ['Lexical closure does not prove semantic independence or absence of model training overlap.',
                             'No authentic separate task field; external requests are a separate descriptive endpoint.']}
    save(OUT / 'external-selection-v3.json', json.dumps(record, indent=2, sort_keys=True).encode()+b'\n')
    print(json.dumps({key:record[key] for key in ('selected_counts','general_confirmation_rows','edge_count','excluded_components','mixed_label_components')}))


if __name__ == '__main__':
    main()
