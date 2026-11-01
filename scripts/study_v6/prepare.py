"""Build source-faithful v6 review packets with provenance kept separately.

No source annotation is semantic gold; all rows remain inference-ineligible.
"""
from __future__ import annotations
import argparse
import collections
import csv
import io
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import (
    ROOT, RAW, OUT, SEED, BROWSE_REPO, BROWSE_REV, NVIDIA_REV, NVIDIA_SHA,
    Union, read, write_rows, report, rank, norm, near_links, references,
    index_browse, canonical_bytes, preserve_write, sha256,
)

def leaves(value, path=()):
    if isinstance(value, str):
        yield path, value
    elif isinstance(value, dict):
        for key, child in value.items():
            yield from leaves(child, path + (key,))
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from leaves(child, path + (i,))

def base(source, key, task, policy, candidate, label, pair, provenance):
    return {'id': source + ':' + str(key), 'source': source,
            'setting': 'indirect_tool_content', 'task': task, 'policy': policy,
            'candidate': candidate, 'upstream_label': label, 'pair_id': pair,
            'group': source + ':' + pair, 'provenance': provenance,
            'semantic_gold': None, 'inference_eligible': False,
            'review_status': 'pending_agent_review', 'group_review': 'pending'}

def nvidia_pair(row):
    messages = row['responses_create_params']['input']
    if [m['role'] for m in messages] != ['system', 'user']:
        raise ValueError('Unexpected task/policy roles')
    if any(not isinstance(m['content'], str) or not m['content'].strip() for m in messages):
        raise ValueError('Missing task/policy text')
    injection = row['injection']['injection_text']
    if not isinstance(injection, str) or not injection.strip():
        raise ValueError('Missing injection text')
    matches = [(path, text) for path, text in leaves(row['environment']) if injection in text]
    if len(matches) != 1 or matches[0][1].count(injection) != 1:
        raise ValueError('Injection does not occur exactly once in exactly one environment leaf')
    path, attacked = matches[0]
    clean = attacked.replace(injection, '', 1)
    if not clean.strip():
        raise ValueError('Deletion leaves no substantive candidate')
    pair = str(row['id'])
    provenance = {'repository': 'nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1',
                  'revision': NVIDIA_REV, 'source_file_sha256': NVIDIA_SHA,
                  'source_row_sha256': sha256(canonical_bytes(row)),
                  'environment_leaf_path': list(path), 'domain': row['domain'],
                  'attack_category': row['attack_category'],
                  'injection_sha256': sha256(injection.encode()),
                  'construction': 'Fully synthetic upstream attack; local clean is exact deletion counterfactual',
                  'candidate_boundary': 'Single environment string, not an observed complete tool response',
                  'selection_bias': 'Upstream successful attacks against Nemotron Nano 3; susceptibility-resampled',
                  'tools_omitted': True}
    return [base('nvidia', pair + ':' + arm, messages[1]['content'], messages[0]['content'],
                 text, label, pair, {**provenance, 'arm': arm})
            for arm, text, label in [('attack', attacked, 1), ('deletion_control', clean, 0)]]

def nvidia():
    path = ROOT / 'data/raw/source-discovery/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1-train.jsonl'
    if sha256(path.read_bytes()) != NVIDIA_SHA:
        raise ValueError('NVIDIA source bytes changed')
    source = read(path)
    pool, excluded, injections = [], [], []
    for row in source:
        try:
            pair = nvidia_pair(row)
        except ValueError as exc:
            excluded.append({'id': row['id'], 'reason': str(exc)})
            continue
        pool.append(pair)
        injections.append(row['injection']['injection_text'])
    u = Union(len(pool))
    edges = []
    for axis, values in [('task', [p[0]['task'] for p in pool]), ('injection', injections)]:
        seen = {}
        for i, value in enumerate(values):
            key = norm(value)
            if key in seen:
                u.join(i, seen[key])
            seen[key] = i
        for j, i, score in near_links(values, .5):
            u.join(i, j)
            edges.append({'a': pool[j][0]['pair_id'], 'b': pool[i][0]['pair_id'], 'axis': axis, 'jaccard': score})
    by_group = collections.defaultdict(list)
    for i, pair in enumerate(pool):
        by_group[u.find(i)].append(pair)
    # 200 pairs maximum, round-robin across source domains, at most one per component.
    representatives = [min(group, key=lambda p: rank('nv:' + p[0]['pair_id'])) for group in by_group.values()]
    buckets = collections.defaultdict(list)
    for pair in sorted(representatives, key=lambda p: rank('nv-select:' + p[0]['pair_id'])):
        buckets[pair[0]['provenance']['domain']].append(pair)
    selected = []
    while len(selected) < 200 and any(buckets.values()):
        for domain in sorted(buckets):
            if buckets[domain] and len(selected) < 200:
                selected.append(buckets[domain].pop(0))
    items = [r for p in selected for r in p]
    write_rows(RAW / 'nvidia-pool-group-edges.jsonl', edges)
    write_rows(RAW / 'nvidia-prepared.jsonl', items)
    record = {'source_rows': len(source), 'adaptable_pairs': len(pool),
              'provisional_pool_components': len(by_group), 'selected_pairs': len(selected),
              'selected_rows': len(items), 'quarantine': excluded,
              'selected_domain_counts': dict(collections.Counter(p[0]['provenance']['domain'] for p in selected)),
              'selection': 'One pair per connected task/injection 3-word Jaccard >= .5 component; domain round-robin hash ranking',
              'source_sha256': NVIDIA_SHA, 'new_semantic_gold': 0}
    report(OUT / 'nvidia-preparation.json', record)
    return items, record

def browse():
    path = RAW / 'browse-train-selected.jsonl'
    receipt = json.loads((OUT / 'browse-acquisition.json').read_text())
    if sha256(path.read_bytes()) != receipt['output_sha256']:
        raise ValueError('BrowseSafe export differs from receipt')
    pairs, excluded = index_browse(read(path))
    items, audit = [], []
    for key, arms in sorted(pairs.items()):
        values = [arms[a].get('content_markdown') for a in ['malicious', 'benign']]
        if any(not isinstance(v, str) or not v.strip() for v in values):
            excluded.append({'pair': key, 'reason': 'missing_complete_markdown'})
            continue
        if values[0] == values[1]:
            excluded.append({'pair': key, 'reason': 'identical_pair_in_markdown'})
            continue
        refs = references(arms['malicious'])
        bound = [s for s in refs if s in values[0]]
        audit.append({'pair_id': key, 'reference_count': len(refs), 'bound_in_attack': len(bound),
                      'also_in_control': sum(s in values[1] for s in bound)})
        for arm, label in [('malicious', 1), ('benign', 0)]:
            r = arms[arm]
            items.append(base('browsesafe', r['entry_id'], r['benign_task'], None,
                              r['content_markdown'], label, key,
                              {'repository': BROWSE_REPO, 'revision': BROWSE_REV, 'split': 'train',
                               'file': r['_file'], 'row_group': r['_row_group'], 'offset': r['_group_offset'],
                               'entry_id': r['entry_id'], 'view': 'content_markdown',
                               'domain': r.get('domain'), 'page_type': r.get('page_type'),
                               'language_page': r.get('language_page'), 'language_payload': r.get('language_payload'),
                               'task_origin': 'Source-provided benchmark task; original production user request not established',
                               'construction': 'Privacy-rewritten benchmark pair, not untouched production capture',
                               'reference_binding': audit[-1], 'source_row_sha256': sha256(canonical_bytes(r))}))
    write_rows(RAW / 'browse-view-audit.jsonl', audit)
    return items, {'adapted_pairs': len(items) // 2, 'excluded': excluded,
                   'pairs_with_no_exact_bound_reference': sum(r['bound_in_attack'] == 0 for r in audit),
                   'note': 'Reference binding is a diagnostic, not semantic label verification; no cropping or editing'}

def group_rows(items):
    u = Union(len(items))
    seen = {}
    edges = []
    for i, row in enumerate(items):
        # V5's split_group is its conservative task/template/domain closure;
        # the older group field alone would incorrectly split those families.
        keys = [('old_group', row.get('split_group') or row['group']), ('candidate', norm(row['candidate']))]
        if row.get('task'):
            keys.append(('task', norm(row['task'])))
        for key in keys:
            if key[1] and key in seen:
                j = seen[key]
                u.join(i, j)
                edges.append({'a': items[j]['id'], 'b': row['id'], 'axis': key[0], 'match': 'exact'})
            seen[key] = i
    for axis, threshold in [('task', .5), ('candidate', .8)]:
        for j, i, score in near_links([r.get(axis) or '' for r in items], threshold):
            u.join(i, j)
            edges.append({'a': items[j]['id'], 'b': items[i]['id'], 'axis': axis, 'jaccard': score})
    members = collections.defaultdict(list)
    for i, row in enumerate(items):
        members[u.find(i)].append(row)
    for group in members.values():
        gid = 'v6:' + min(rank(r['id']) for r in group)
        # Preserve any historical proposal for diagnostics, but all v6 assignment
        # uses merged components and happens before development inference.
        split = 'development' if int(rank('split:' + gid)[:8], 16) % 5 == 0 else 'confirmation'
        for row in group:
            row['v5_split_proposal'] = row.get('split_proposal')
            row['group'] = gid
            row['split_proposal'] = split
    write_rows(RAW / 'group-edges.jsonl', edges)
    return {'components': len(members), 'largest_component_rows': max(map(len, members.values())),
            'edges': len(edges), 'status': 'Lexical proposal; independent semantic grouping review required'}

def export(items):
    rows = sorted(items, key=lambda r: rank('review:' + r['id']))
    mapping, blind = [], []
    for row in rows:
        rid = rank('opaque-review:' + row['id'])[:24]
        mapping.append({**row, 'review_id': rid})
        blind.append({'review_id': rid, **{k: row[k] for k in ['setting', 'task', 'policy', 'candidate']},
                      'review_target': 'authorization_scope' if row['source'] == 'scope' else
                      ('direct_policy_conflict' if row['source'] == 'spml' else 'indirect_instruction_injection')})
    write_rows(RAW / 'prepared.jsonl', rows)
    write_rows(RAW / 'review-mapping.jsonl', mapping)
    write_rows(RAW / 'review-packet.jsonl', blind)
    fields = ['review_id', 'reviewer_id', 'reviewer_kind', 'reviewer_model_version', 'verdict',
              'rationale', 'evidence_span', 'context_needed', 'task_relation', 'instruction_type',
              'ambiguity', 'group_merge_ids']
    receipts = []
    chunks, chunk, size = [], [], 0
    for row in blind:
        row_size = len(canonical_bytes(row)) + 1
        if chunk and (len(chunk) >= 40 or size + row_size > 120000):
            chunks.append(chunk)
            chunk, size = [], 0
        chunk.append(row)
        size += row_size
    if chunk:
        chunks.append(chunk)
    for number, chunk in enumerate(chunks, 1):
        name = f'batch-{number:03d}'
        packet = RAW / 'review-batches' / (name + '.jsonl')
        write_rows(packet, chunk)
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({'review_id': r['review_id']} for r in chunk)
        template = RAW / 'review-batches' / (name + '-blank.csv')
        preserve_write(template, stream.getvalue().encode())
        receipts.append({'batch': name, 'rows': len(chunk), 'bytes': packet.stat().st_size, 'packet_sha256': sha256(packet.read_bytes()),
                         'template_sha256': sha256(template.read_bytes())})
    return receipts

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--nvidia-only', action='store_true')
    args = parser.parse_args()
    nn, ns = nvidia()
    if args.nvidia_only:
        print(json.dumps(ns))
        return
    bb, bs = browse()
    old = read(ROOT / 'data/raw/study-v5/grouped-review-v2.jsonl') + read(ROOT / 'data/raw/study-v5/scope-pairs.jsonl')
    items = old + nn + bb
    groups = group_rows(items)
    batches = export(items)
    result = {'version': 'v6-preparation-1', 'seed': SEED, 'prepared_rows': len(items),
              'source_counts': dict(collections.Counter(r['source'] for r in items)),
              'source_split_groups': {source: {split: len({r['group'] for r in items if r['source'] == source and r['split_proposal'] == split})
                  for split in ['development', 'confirmation']} for source in sorted({r['source'] for r in items})},
              'nvidia': ns, 'browsesafe': bs, 'groups': groups, 'review_batches': batches,
              'review_packet_sha256': sha256((RAW / 'review-packet.jsonl').read_bytes()),
              'mapping_sha256': sha256((RAW / 'review-mapping.jsonl').read_bytes()),
              'prepared_sha256': sha256((RAW / 'prepared.jsonl').read_bytes()),
              'semantic_gold': 0, 'independent_reviews_completed': 0, 'inference_eligible': 0,
              'new_model_calls': 0, 'review_status': 'External agent labels and grouping pending'}
    report(OUT / 'preparation.json', result)
    print(json.dumps({k: result[k] for k in ['prepared_rows', 'source_counts', 'source_split_groups', 'groups']}))

if __name__ == '__main__':
    main()
