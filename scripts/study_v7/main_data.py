"""Pinned BrowseSafe++ v7 preparation. Downloads columns; never invokes a model.

The full English reserve pool is closed under metadata/task/document relatives
before partitions are selected. Raw text and edge evidence remain Git ignored.
No v6 file is changed and no prediction/accuracy file is read.
"""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import Union, index_browse, norm, references
from scripts.source_discovery.prepare_review import canonical_bytes, preserve_write, sha256

ROOT = Path(__file__).resolve().parents[2]
HISTORY = ROOT.with_name('Decision Context Benchmark')
RAW = ROOT / 'data/raw/study-v7'
OUT = ROOT / 'results/study-v7'
REPO = 'perplexity-ai/browsesafe-plus-plus'
REVISION = '3e9f4b3cef9295a1928ddfb33675eafd8bb68259'
SEED = 'study-v7-plan-20261101'
HISTORICAL_INPUTS = (
    'data/raw/pilot.jsonl',
    'data/expanded-v2/collection.jsonl',
    'data/raw/expanded-v2/pre-query-audit-collection.jsonl',
    'data/raw/extension-v3/prepared-collection-v1.jsonl',
    'data/raw/controls-v4/prepared-collection-v1.jsonl',
    'data/raw/study-v5/grouped-review-v2.jsonl',
    'data/raw/study-v5/prepared-review.jsonl',
    'data/raw/study-v5/scope-pairs.jsonl',
    'data/raw/study-v6/prepared.jsonl',
)


def rank(source, purpose, canonical_id):
    """Frozen v7 rank: SHA256(seed NUL source NUL purpose NUL canonical ID)."""
    return sha256('\0'.join((SEED, source, purpose, str(canonical_id))).encode())


def read_rows(path):
    with Path(path).open() as stream:
        return [json.loads(line) for line in stream if line.strip()]


def rows_bytes(rows):
    return b''.join(canonical_bytes(row) + b'\n' for row in rows)


def write_rows(path, rows):
    preserve_write(path, rows_bytes(rows))


def receipt(path, base=ROOT):
    return {'path': str(path.relative_to(base)), 'sha256': sha256(path.read_bytes()),
            'bytes': path.stat().st_size}


def progress(stage, **values):
    print(json.dumps({'stage': stage, **values}), flush=True)


def compact_shingles(texts):
    """Collision-free compact three-word sets, identical to common.shingles.

    Token IDs use 21 bits each (fail closed at 2**21 words), so three IDs pack
    without collisions into uint64. No LSH/probabilistic candidate selection.
    """
    import numpy as np
    vocabulary, result = {}, []
    for text in texts:
        words = norm(text).split()
        codes = []
        for word in words:
            if word not in vocabulary:
                vocabulary[word] = len(vocabulary) + 1
            code = vocabulary[word]
            if code >= 2 ** 21:
                raise ValueError('Vocabulary exceeds exact compact shingle capacity')
            codes.append(code)
        values = np.asarray(codes, dtype=np.uint64)
        result.append(np.unique((values[:-2] << np.uint64(42)) |
                                (values[1:-1] << np.uint64(21)) | values[2:]))
    return result


def compact_near_links(texts, threshold, *, historical_count=None):
    """Exact Jaccard prefix join, minimum five distinct three-word shingles.

    With historical_count only historical/new cross links are generated. All
    comparison sets share one frequency order, as required by prefix filtering.
    Flat numpy posting arrays avoid retaining millions of Python tuples.
    """
    import numpy as np
    sets = compact_shingles(texts)
    nonempty = [s for s in sets if len(s) >= 5]
    if not nonempty:
        return []
    keys, counts = np.unique(np.concatenate(nonempty), return_counts=True)
    prefixes = []
    for group in sets:
        if len(group) < 5:
            prefixes.append(group[:0])
            continue
        frequencies = counts[np.searchsorted(keys, group)]
        order = np.lexsort((group, frequencies))
        prefixes.append(group[order[:len(group) - math.ceil(threshold * len(group)) + 1]])
    del keys, counts, nonempty
    index_ids = range(len(sets)) if historical_count is None else range(historical_count)
    indexed = [i for i in index_ids if len(prefixes[i])]
    if not indexed:
        return []
    pkeys = np.concatenate([prefixes[i] for i in indexed])
    prows = np.concatenate([np.full(len(prefixes[i]), i, dtype=np.int32) for i in indexed])
    order = np.argsort(pkeys, kind='stable')
    pkeys, prows = pkeys[order], prows[order]
    del order
    links = []
    queries = range(len(sets)) if historical_count is None else range(historical_count, len(sets))
    sizes = np.asarray([len(s) for s in sets])
    for i in queries:
        group, prefix = sets[i], prefixes[i]
        if not len(prefix):
            continue
        starts = np.searchsorted(pkeys, prefix, side='left')
        ends = np.searchsorted(pkeys, prefix, side='right')
        candidates = np.unique(np.concatenate([prows[a:b] for a, b in zip(starts, ends)]))
        if historical_count is None:
            candidates = candidates[candidates < i]
        candidates = candidates[(np.minimum(sizes[candidates], sizes[i]) >=
                                 threshold * np.maximum(sizes[candidates], sizes[i]))]
        for j in candidates:
            intersection = len(np.intersect1d(group, sets[j], assume_unique=True))
            score = intersection / (len(group) + len(sets[j]) - intersection)
            if score >= threshold:
                links.append((int(j), i, score))
    return links


def recover_external_alias(raw=RAW, out=OUT):
    """Recover the historical v2 filename only from byte-identical locked v3 data."""
    target = raw / 'external-selected-v2.jsonl'
    if target.exists():
        return target
    source = raw / 'external-selected-v3.jsonl'
    old_lock = json.loads((out / 'external-selection-v2.json').read_text())
    new_lock = json.loads((out / 'external-selection-v3.json').read_text())
    expected = old_lock['artifacts'][target.name]
    body = source.read_bytes()
    if sha256(body) != expected or new_lock['artifacts'][source.name] != expected:
        raise ValueError('Cannot recover an external alias from different source bytes')
    preserve_write(target, body)
    return target


def metadata_and_history(history=HISTORY):
    """Read only source/preparation records, never attempts or model outputs."""
    acquisition = json.loads((ROOT / 'results/study-v6/browse-acquisition.json').read_text())
    if acquisition['revision'] != REVISION or acquisition['repository'] != REPO:
        raise ValueError('Historical metadata revision does not match v7')
    receipts, metadata = [], []
    for item in acquisition['receipts']:
        if not item['path'].startswith('data/raw/study-v6/browse-metadata/'):
            continue
        path = history / item['path']
        if sha256(path.read_bytes()) != item['sha256']:
            raise ValueError('Historical pinned metadata receipt mismatch')
        metadata.extend(read_rows(path))
        receipts.append({**receipt(path, history), 'base': 'canonical_historical_checkout'})
    if len(metadata) != 59000 or len(receipts) != 21:
        raise ValueError('Expected complete pinned metadata from 21 training shards')
    prior_path = history / 'data/raw/study-v6/browse-train-selected.jsonl'
    if sha256(prior_path.read_bytes()) != acquisition['output_sha256']:
        raise ValueError('Historical selected source rows changed')
    prior_rows = read_rows(prior_path)
    selected_ids = {r['entry_id'].rsplit('_', 1)[0] for r in prior_rows}
    if len(prior_rows) != 2000 or len(selected_ids) != 1000:
        raise ValueError('Expected all 1,000 selected v6 pairs, including rejected pairs')
    receipts.append({**receipt(prior_path, history), 'base': 'canonical_historical_checkout'})
    old = []
    for name in HISTORICAL_INPUTS:
        path = history / name
        if not path.exists():
            raise FileNotFoundError('Historical source/preparation input missing: ' + name)
        for n, row in enumerate(read_rows(path)):
            old.append({'id': f'{name}:{row.get("id", n)}', 'candidate': row['candidate'],
                        'task': row.get('task') or row.get('trusted_task') or '',
                        'pair_id': row.get('pair_id') if row.get('source') == 'browsesafe' else None})
        receipts.append({**receipt(path, history), 'base': 'canonical_historical_checkout'})
    # Source-discovery review packets were prepared before the smaller locked
    # collections. Conservatively count all submitted prompts/candidate messages
    # as historical exposure, even if no later classifier evaluated them.
    for source, name in (
            ('spml', 'data/raw/source-discovery/spml-review-v1.jsonl'),
            ('aib', 'data/raw/source-discovery/aib-review-v1.jsonl')):
        path = history / name
        source_rows = read_rows(path)
        for n, row in enumerate(source_rows):
            payload = row['detector_payload']
            task = payload.get('actual_user_task') or ''
            if source == 'spml':
                candidates = [payload['submitted_user_prompt']]
            else:
                indexes = set(payload['candidate_message_indexes'])
                candidates = [m['content'] for m in payload['source_conversation_inputs']
                              if m['original_index'] in indexes]
                if len(candidates) != len(indexes):
                    raise ValueError('Historical AIB candidate-message indexes differ')
            for number, candidate in enumerate(candidates):
                if not isinstance(candidate, str) or not isinstance(task, str):
                    raise ValueError('Malformed historical source-discovery input')
                old.append({'id': f'{name}:{n}:{number}', 'candidate': candidate,
                            'task': task, 'pair_id': None})
        receipts.append({**receipt(path, history), 'base': 'canonical_historical_checkout',
                         'source_rows': len(source_rows)})
    # The rejected pre-review selected rows are included even if later preparation
    # omitted them for technical reasons. Labels are never replaced by review labels.
    for row in prior_rows:
        old.append({'id': 'all_v6_selected:' + row['entry_id'],
                    'candidate': row['content_markdown'], 'task': row['benign_task'],
                    'pair_id': row['entry_id'].rsplit('_', 1)[0]})
    # External v2 is locked first. Treat all its validation/confirmation inputs
    # conservatively as exclusion inputs for the main corpus, so current-study
    # development/confirmation relatives cannot cross the two sources either.
    external_path = recover_external_alias()
    external_lock_path = OUT / 'external-selection-v2.json'
    external_lock = json.loads(external_lock_path.read_text())
    if sha256(external_path.read_bytes()) != external_lock['artifacts'][external_path.name]:
        raise ValueError('Current-study external locked source inputs changed')
    external_rows = read_rows(external_path)
    if len(external_rows) != 4100 or len({r['id'] for r in external_rows}) != 4100:
        raise ValueError('Expected all 4,100 locked v7 external source inputs')
    for row in external_rows:
        old.append({'id': 'v7-external:' + row['id'], 'candidate': row['candidate'],
                    'task': '', 'pair_id': None})  # External source has no task field.
    receipts.append({**receipt(external_path), 'base': 'prepared_checkout',
                     'role': 'locked_current_study_cross_source_exclusion_inputs', 'source_rows': len(external_rows)})
    receipts.append({**receipt(external_lock_path), 'base': 'prepared_checkout',
                     'role': 'current_study_external_selection_lock'})
    selected_ids |= {r['pair_id'] for r in old if r['pair_id']}
    return metadata, old, selected_ids, receipts


def metadata_components(metadata):
    pairs, technical = index_browse(metadata)
    ids = sorted(pairs)
    positions = {key: i for i, key in enumerate(ids)}
    union, edges = Union(len(ids)), []
    for axis in ('task', 'reference'):
        seen = {}
        for key in ids:
            values = ([norm(pairs[key]['benign']['benign_task'])] if axis == 'task'
                      else [norm(s) for s in references(pairs[key]['malicious'])
                            if len(norm(s).split()) >= 5])
            for value in values:
                if value in seen:
                    union.join(positions[key], positions[seen[value]])
                    edges.append({'a': seen[value], 'b': key, 'axis': axis,
                                  'match': 'normalized_exact', 'key_sha256': sha256(value.encode())})
                else:
                    seen[value] = key
    return pairs, ids, positions, union, edges, technical


def english(arms):
    return (all(arms[a].get('language_page') == ['en'] for a in ('benign', 'malicious'))
            and arms['malicious'].get('language_payload') == ['en']
            and arms['benign'].get('language_payload') is None)


def acquire(metadata, wanted, *, namespace='browse-reserve'):
    """Read only entry_id/content_markdown from pinned labeled train shards."""
    import huggingface_hub
    import pyarrow.parquet as pq
    from huggingface_hub import HfApi, HfFileSystem, get_token
    if not get_token():
        raise PermissionError('Approved existing Hugging Face login required')
    info = HfApi().dataset_info(REPO, revision=REVISION, files_metadata=True)
    paths = sorted(s.rfilename for s in info.siblings
                   if re.fullmatch(r'data/members-train-\d{4}\.parquet', s.rfilename))
    if info.sha != REVISION or len(paths) != 21:
        raise ValueError('Pinned training revision/shard inventory mismatch')
    locations = collections.defaultdict(set)
    for row in metadata:
        if row['entry_id'].rsplit('_', 1)[0] in wanted:
            locations[row['_file']].add(row['_row_group'])
    def fetch(location):
        path, row_groups = location
        if path not in paths:
            raise ValueError('Refuse any file outside the pinned labeled train inventory')
        if namespace not in ('browse-reserve', 'browse-historical-relatives'):
            raise ValueError('Unknown versioned column-cache namespace')
        output = RAW / namespace / (Path(path).stem + '.jsonl')
        if not output.exists():
            fs = HfFileSystem(token=True, block_size=65536)
            rows = []
            with fs.open(f'datasets/{REPO}@{REVISION}/{path}', 'rb') as stream:
                parquet = pq.ParquetFile(stream)
                for group in sorted(row_groups):
                    for row in parquet.read_row_group(group, columns=['entry_id', 'content_markdown']).to_pylist():
                        if row['entry_id'].rsplit('_', 1)[0] in wanted:
                            rows.append(row)
            write_rows(output, sorted(rows, key=lambda r: r['entry_id']))
        result = read_rows(output)
        expected = {r['entry_id'] for r in metadata if r['_file'] == path
                    and r['entry_id'].rsplit('_', 1)[0] in wanted}
        if len(result) != len(expected) or {r['entry_id'] for r in result} != expected:
            raise ValueError('Incomplete/stale reserve column cache')
        progress('train_markdown_shard', shard=Path(path).name, pages=len(result))
        return result, {**receipt(output), 'source_file': path,
                        'source_revision': REVISION, 'row_groups': sorted(row_groups),
                        'columns': ['entry_id', 'content_markdown']}
    rows, receipts = [], []
    with ThreadPoolExecutor(max_workers=3) as executor:
        for part, part_receipt in executor.map(fetch, sorted(locations.items())):
            rows.extend(part)
            receipts.append(part_receipt)
    if len(rows) != 2 * len(wanted) or len({r['entry_id'] for r in rows}) != len(rows):
        raise ValueError('Reserve pool must contain two unique complete source rows per pair')
    return rows, receipts, huggingface_hub.__version__


def exact_text_edges(texts, keys, axis, union, positions, edges, *, old_count=0):
    seen = {}
    held = set()
    for i, text in enumerate(texts):
        value = norm(text)
        if not value:
            continue
        if value in seen:
            j = seen[value]
            if i >= old_count and j >= old_count:
                union.join(positions[keys[i]], positions[keys[j]])
            elif i >= old_count:
                held.add(keys[i])
            edges.append({'a': keys[j], 'b': keys[i], 'axis': axis,
                          'match': 'normalized_exact', 'key_sha256': sha256(value.encode())})
        else:
            seen[value] = i
    return held


def component_map(ids, positions, union):
    groups = collections.defaultdict(list)
    for key in ids:
        groups[union.find(positions[key])].append(key)
    canonical = {root: min(members, key=lambda k: rank('browsesafe', 'component-id', k))
                 for root, members in groups.items()}
    return {key: 'browsesafe-v7:' + canonical[union.find(positions[key])] for key in ids}


def prepare(history=HISTORY):
    start = time.monotonic()
    metadata, old, prior_ids, history_receipts = metadata_and_history(history)
    pairs, ids, positions, union, edges, technical = metadata_components(metadata)
    if not prior_ids <= set(ids):
        raise ValueError('Historical BrowseSafe identifier missing from pinned pool')
    initial = component_map(ids, positions, union)
    held_initial = {initial[k] for k in prior_ids}
    eligible_ids = [k for k in ids if initial[k] not in held_initial and english(pairs[k])]
    eligible_set = set(eligible_ids)
    progress('reserve_pool', metadata_pairs=len(ids), metadata_components=len(set(initial.values())),
             prior_components=len(held_initial), fresh_english_pairs=len(eligible_ids),
             fresh_english_components=len({initial[k] for k in eligible_ids}))
    # Full eligible reserve is fixed before reading Markdown. No output-driven refill.
    reserve_rows, download_receipts, hf_version = acquire(metadata, eligible_set)
    text_index = {r['entry_id']: r['content_markdown'] for r in reserve_rows}
    technical_by_pair = {}
    intact = []
    semantic_concerns = []
    for key in eligible_ids:
        clean, attack = [text_index[pairs[key][arm]['entry_id']] for arm in ('benign', 'malicious')]
        if any(not isinstance(v, str) or not v.strip() for v in (clean, attack)):
            technical_by_pair[key] = 'missing_complete_markdown'
            continue
        if clean == attack:
            technical_by_pair[key] = 'identical_clean_attack_markdown'
            continue
        intact.append(key)
        refs = references(pairs[key]['malicious'])
        bound = [s for s in refs if s in attack]
        if not bound or any(s in clean for s in bound):
            semantic_concerns.append({'pair_id': key, 'reference_count': len(refs),
                'literal_references_bound_in_attack': len(bound),
                'literal_bound_references_also_in_clean': sum(s in clean for s in bound),
                'disposition': 'source_labels_preserved_no_semantic_exclusion'})
    progress('technical_eligibility', intact_pairs=len(intact), technical_exclusions=len(technical_by_pair))
    # Tasks are available for the entire metadata pool, so closure also propagates
    # all prior selected components and language-ineligible relatives.
    task_texts = [pairs[k]['benign']['benign_task'] for k in ids]
    task_links = compact_near_links(task_texts, .5)
    for j, i, score in task_links:
        union.join(i, j)
        edges.append({'a': ids[j], 'b': ids[i], 'axis': 'task', 'match': 'jaccard_ge_0.5', 'jaccard': score})
    progress('task_closure', near_edges=len(task_links), components=len(set(component_map(ids, positions, union).values())))
    del task_links
    # Historical task exact/near closure. Historical candidate screen retains v6's
    # stricter Jaccard >= .5 rule; within v7 documents use the frozen >= .8 rule.
    historical_tasks = list({norm(r['task']): r['task'] for r in old if norm(r['task'])}.values())
    old_task_ids = ['historical-task:' + sha256(norm(t).encode()) for t in historical_tasks]
    task_held = exact_text_edges(historical_tasks + task_texts, old_task_ids + ids,
                                'historical_task', union, positions, edges, old_count=len(historical_tasks))
    for j, i, score in compact_near_links(historical_tasks + task_texts, .5, historical_count=len(historical_tasks)):
        key = ids[i-len(historical_tasks)]
        task_held.add(key)
        edges.append({'a': old_task_ids[j], 'b': key, 'axis': 'historical_task',
                      'match': 'jaccard_ge_0.5', 'jaccard': score})
    progress('historical_task_screen', touched_pairs=len(task_held))
    # A previously selected metadata component includes unselected relatives.
    # Their complete documents must also be historical exclusion inputs: merely
    # excluding their IDs does not prevent a fresh page from matching a relative.
    task_closed_groups = component_map(ids, positions, union)
    historical_component_ids = {task_closed_groups[k] for k in prior_ids | task_held}
    historical_relative_ids = {k for k in ids if task_closed_groups[k] in historical_component_ids}
    known_texts = {r['id'].removeprefix('all_v6_selected:'): r['candidate']
                   for r in old if r['id'].startswith('all_v6_selected:')}
    known_texts.update(text_index)
    missing_relative_ids = {k for k in historical_relative_ids
                            if any(pairs[k][a]['entry_id'] not in known_texts for a in ('benign', 'malicious'))}
    relative_receipts = []
    if missing_relative_ids:
        relative_rows, relative_receipts, _ = acquire(metadata, missing_relative_ids,
                                                      namespace='browse-historical-relatives')
        known_texts.update({r['entry_id']: r['content_markdown'] for r in relative_rows})
    for key in sorted(historical_relative_ids):
        for arm in ('benign', 'malicious'):
            source = pairs[key][arm]
            text = known_texts[source['entry_id']]
            if not isinstance(text, str):
                raise ValueError('Historical component relative lacks a complete Markdown string')
            old.append({'id': 'historical-component-relative:' + source['entry_id'],
                        'candidate': text, 'task': source['benign_task'], 'pair_id': key})
    progress('historical_component_documents', complete_pairs=len(historical_relative_ids),
             additional_downloaded_pairs=len(missing_relative_ids))
    # Candidate closure includes technically unusable rows when their text exists;
    # malformed-arm exclusion never hides an intact relative's dependence.
    document_keys, document_texts = [], []
    for key in eligible_ids:
        for arm in ('benign', 'malicious'):
            text = text_index[pairs[key][arm]['entry_id']]
            if isinstance(text, str) and text.strip():
                document_keys.append(key)
                document_texts.append(text)
    exact_text_edges(document_texts, document_keys, 'candidate', union, positions, edges)
    for j, i, score in compact_near_links(document_texts, .8):
        if document_keys[j] == document_keys[i]:
            continue
        union.join(positions[document_keys[j]], positions[document_keys[i]])
        edges.append({'a': document_keys[j], 'b': document_keys[i], 'axis': 'candidate',
                      'match': 'jaccard_ge_0.8', 'jaccard': score})
    progress('candidate_closure', document_rows=len(document_texts),
             components=len(set(component_map(ids, positions, union).values())))
    old_candidates_by_norm = {}
    for row in old:
        if norm(row['candidate']):
            old_candidates_by_norm.setdefault(norm(row['candidate']), row)
    old_candidates = list(old_candidates_by_norm.values())
    old_keys = [r['id'] for r in old_candidates]
    old_texts = [r['candidate'] for r in old_candidates]
    document_held = exact_text_edges(old_texts + document_texts, old_keys + document_keys,
                                    'historical_candidate', union, positions, edges,
                                    old_count=len(old_candidates))
    for j, i, score in compact_near_links(old_texts + document_texts, .5, historical_count=len(old_candidates)):
        key = document_keys[i-len(old_candidates)]
        document_held.add(key)
        edges.append({'a': old_keys[j], 'b': key, 'axis': 'historical_candidate',
                      'match': 'jaccard_ge_0.5', 'jaccard': score})
    cross_source_held = set()
    for edge in edges:
        if edge['axis'] == 'historical_candidate' and edge['a'].startswith('v7-external:'):
            edge['axis'] = 'cross_source_candidate'
            cross_source_held.add(edge['b'])
    groups = component_map(ids, positions, union)
    excluded_groups = {groups[k] for k in prior_ids | task_held | document_held}
    usable = collections.defaultdict(list)
    exclusions = list(technical)
    for key in ids:
        if groups[key] in excluded_groups:
            reason = 'component_touches_historical_selection_or_exact_near_overlap'
        elif not english(pairs[key]):
            reason = 'source_page_or_payload_not_exclusively_english'
        elif key in technical_by_pair:
            reason = technical_by_pair[key]
        elif key not in eligible_set:
            reason = 'prior_metadata_component'
        else:
            usable[groups[key]].append(key)
            continue
        exclusions.append({'pair_id': key, 'group_id': groups[key], 'reason': reason})
    representatives = {g: min(members, key=lambda k: rank('browsesafe', 'pair-representative', k))
                       for g, members in usable.items()}
    ordered_groups = sorted(representatives, key=lambda g: rank('browsesafe', 'partition', g))
    development = ordered_groups[:200]
    confirmation = ordered_groups[200:3200]
    selected_groups = development + confirmation
    partitions = {g: 'development' if g in development else 'confirmation' for g in selected_groups}
    selected_rows, provenance, safe_selected = [], [], []
    for group in selected_groups:
        key = representatives[group]
        for arm, label in (('benign', 0), ('malicious', 1)):
            source = pairs[key][arm]
            text = text_index[source['entry_id']]
            source_provenance = {'repository': REPO, 'revision': REVISION, 'split': 'train',
                'file': source['_file'], 'row_group': source['_row_group'], 'offset': source['_group_offset'],
                'entry_id': source['entry_id'], 'view': 'content_markdown',
                'upstream_arm': source['arm'], 'upstream_label': source['label'],
                'language_page': source['language_page'], 'language_payload': source['language_payload'],
                'task_provenance': 'publisher_privacy_rewritten_benign_task'}
            row = {'id': 'browsesafe:' + source['entry_id'], 'source': 'browsesafe',
                'group_id': group, 'group': group, 'pair_id': key, 'task': source['benign_task'],
                'candidate': text, 'upstream_label': label, 'partition': partitions[group],
                'provenance': source_provenance,
                'input_sha256': sha256(canonical_bytes({'task': source['benign_task'], 'candidate': text})),
                'inference_authorized': False}
            selected_rows.append(row)
            provenance.append({'id': row['id'], 'group_id': group, **source_provenance,
                               'candidate_sha256': sha256(text.encode()),
                               'task_sha256': sha256(source['benign_task'].encode())})
            safe_selected.append({k: row[k] for k in ('id', 'group_id', 'pair_id', 'upstream_label',
                                                     'partition', 'input_sha256')})
    general = sorted(confirmation, key=lambda g: rank('browsesafe', 'general-subset', g))[:500]
    audit = sorted(confirmation, key=lambda g: rank('browsesafe', 'audit', g))[:100]
    repeat_native = sorted(confirmation, key=lambda g: rank('browsesafe', 'native-repeat', g))[:100]
    repeat_general = sorted(general, key=lambda g: rank('browsesafe', 'general-repeat', g))[:50]
    development_execute = sorted(development, key=lambda g: rank('browsesafe', 'development-execute', g))[:50]
    selected_by_group = collections.defaultdict(dict)
    for row in selected_rows:
        selected_by_group[row['group_id']][row['upstream_label']] = row
    audit_rows = [{'group_id': g, 'pair_id': representatives[g],
        'task': selected_by_group[g][0]['task'],
        'clean': {'candidate': selected_by_group[g][0]['candidate'], 'source_label': 0},
        'attack': {'candidate': selected_by_group[g][1]['candidate'], 'source_label': 1},
        'audit_status': 'locked_pending_authorized_sol_review',
        'allowed_fields': ['task_fidelity', 'attack_visibility', 'ambiguity', 'evidence_spans'],
        'source_labels_remain_primary': True, 'inference_authorized': False} for g in audit]
    paths = {'selected': RAW / 'main-selected.jsonl', 'audit_packet': RAW / 'main-audit-packet.jsonl',
        'edges': RAW / 'main-group-edges.jsonl', 'exclusions': RAW / 'main-technical-exclusions.jsonl',
        'semantic_concerns': RAW / 'main-semantic-concerns.jsonl', 'source_provenance': RAW / 'main-source-provenance.jsonl',
        'pool_components': RAW / 'main-pool-components.jsonl'}
    for name, rows in [('selected', selected_rows), ('audit_packet', audit_rows), ('edges', edges),
                       ('exclusions', exclusions), ('semantic_concerns', semantic_concerns),
                       ('source_provenance', provenance),
                       ('pool_components', [{'pair_id': k, 'metadata_group_id': initial[k], 'group_id': groups[k]} for k in ids])]:
        write_rows(paths[name], rows)
    result = {'version': 'study-v7-main-preparation-1', 'seed': SEED, 'repository': REPO,
        'revision': REVISION, 'source_license': 'CC-BY-4.0',
        'source_training_pages': len(metadata), 'source_pairs': len(pairs),
        'initial_metadata_components': len(set(initial.values())), 'prior_selected_pairs': len(prior_ids),
        'prior_selected_metadata_components': len(held_initial), 'fresh_english_reserve_pairs': len(eligible_ids),
        'fresh_english_reserve_components': len({initial[k] for k in eligible_ids}),
        'acquired_reserve_pages': len(reserve_rows), 'technically_intact_reserve_pairs': len(intact),
        'final_pool_components': len(set(groups.values())), 'eligible_fresh_components': len(usable),
        'development_groups': len(development), 'confirmation_groups': len(confirmation),
        'selected_pages': len(selected_rows), 'audit_groups': len(audit), 'general_groups': len(general),
        'target_met': len(development) == 200 and len(confirmation) == 3000,
        'exclusion_reason_counts': dict(collections.Counter(r['reason'] for r in exclusions)),
        'relation_edge_counts': dict(collections.Counter(r['axis'] + ':' + r['match'] for r in edges)),
        'semantic_concerns_logged_without_relabeling': len(semantic_concerns),
        'historical_source_rows_read': len(old), 'historical_source_receipts': history_receipts,
        'cross_source_locked_external_inputs': 4100,
        'cross_source_touched_reserve_pairs': len(cross_source_held),
        'historical_component_relative_pairs': len(historical_relative_ids),
        'additional_downloaded_historical_relative_pairs': len(missing_relative_ids),
        'download_receipts': download_receipts + relative_receipts, 'outputs': {k: receipt(v) for k, v in paths.items()},
        'selected': safe_selected, 'subsets': {'development_execute': development_execute,
            'general': general, 'audit': audit, 'repeat_native': repeat_native, 'repeat_general': repeat_general},
        'grouping': {'task_jaccard': .5, 'candidate_jaccard': .8, 'historical_candidate_jaccard': .5,
            'historical_task_jaccard': .5, 'minimum_distinct_trigrams': 5,
            'exact_near_algorithm': 'Collision-free packed word trigrams; exact shared-order prefix join',
            'document_closure_scope': 'Full English reserve plus historical source/preparation candidates and complete documents of all metadata/task components touching prior selected pairs or historical tasks',
            'task_closure_scope': 'Entire labeled training metadata plus historical source/preparation tasks',
            'cross_source_policy': 'Lock external v2 first; exclude entire main components touching any of its 4,100 inputs by normalized exact or candidate Jaccard >=0.5',
            'limitation': 'Lexical/document/task closure reduces dependence; semantic template identity and model training overlap are not certified.'},
        'partition_rule': 'One frozen hash representative per final component; hash order first200development then3000confirmation',
        'new_model_calls': 0, 'test_partition_read': False, 'screenshot_or_html_read': False,
        'source_labels_preserved': True, 'inference_authorized': False,
        'huggingface_hub_version': hf_version,
        'selection_lock_sha256': sha256(canonical_bytes({'selected': safe_selected, 'subsets': {
            'development_execute': development_execute, 'general': general, 'audit': audit,
            'repeat_native': repeat_native, 'repeat_general': repeat_general}}))}
    preserve_write(OUT / 'main-selection.json', json.dumps(result, indent=2, sort_keys=True).encode() + b'\n', raw=False)
    progress('main_preparation_complete', development_groups=len(development), confirmation_groups=len(confirmation),
             elapsed_seconds=round(time.monotonic()-start, 1), target_met=result['target_met'])
    return result


def verify_locked(history=HISTORY):
    """Read-only local verification of the locked cohort and source receipts."""
    result = json.loads((OUT / 'main-selection.json').read_text())
    if result['revision'] != REVISION or result['seed'] != SEED:
        raise ValueError('Locked main revision/seed mismatch')
    equivalence_path = OUT / 'main-external-v3-equivalence.json'
    if equivalence_path.exists():
        equivalence = json.loads(equivalence_path.read_text())
        for key in ('main_closure_source_inputs', 'latest_external_source_inputs',
                    'main_closure_external_selection_lock', 'latest_external_selection_lock'):
            item = equivalence[key]
            path = ROOT / item['path']
            if sha256(path.read_bytes()) != item['sha256'] or path.stat().st_size != item['bytes']:
                raise ValueError('Cross-source v3 equivalence receipt changed: ' + item['path'])
        if ((ROOT / equivalence['main_closure_source_inputs']['path']).read_bytes() !=
                (ROOT / equivalence['latest_external_source_inputs']['path']).read_bytes()):
            raise ValueError('Cross-source v3 inputs no longer match main closure inputs')
    for item in result['historical_source_receipts']:
        base = ROOT if item['base'] == 'prepared_checkout' else history
        path = base / item['path']
        if sha256(path.read_bytes()) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Historical source/preparation input changed: ' + item['path'])
    for item in list(result['outputs'].values()) + result['download_receipts']:
        path = ROOT / item['path']
        if sha256(path.read_bytes()) != item['sha256'] or path.stat().st_size != item['bytes']:
            raise ValueError('Locked main artifact changed: ' + item['path'])
    rows = read_rows(ROOT / result['outputs']['selected']['path'])
    if len(rows) != result['selected_pages'] or len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Locked main page count/identifiers differ')
    by_group = collections.defaultdict(list)
    for row in rows:
        by_group[row['group_id']].append(row)
        if row['input_sha256'] != sha256(canonical_bytes({'task': row['task'], 'candidate': row['candidate']})):
            raise ValueError('Locked main input hash mismatch')
        if row['inference_authorized'] is not False:
            raise ValueError('Preparation rows must not authorize inference')
    pool = read_rows(ROOT / result['outputs']['pool_components']['path'])
    pool_groups = {r['pair_id']: r['group_id'] for r in pool}
    if len(pool_groups) != result['source_pairs']:
        raise ValueError('Full metadata pool component map is incomplete')
    prior_rows = read_rows(history / 'data/raw/study-v6/browse-train-selected.jsonl')
    prior_ids = {r['entry_id'].rsplit('_', 1)[0] for r in prior_rows}
    if any(pool_groups[key] in by_group for key in prior_ids):
        raise ValueError('Selected main cohort contains a prior selected component')
    for edge in read_rows(ROOT / result['outputs']['edges']['path']):
        a, b = edge['a'], edge['b']
        if a in pool_groups and b in pool_groups:
            if pool_groups[a] != pool_groups[b]:
                raise ValueError('Stored task/document relation was not closed into one component')
        elif a not in pool_groups and b in pool_groups:
            if pool_groups[b] in by_group:
                raise ValueError('Selected component touches a stored historical/cross-source overlap')
    for group in by_group.values():
        if len(group) != 2 or {r['upstream_label'] for r in group} != {0, 1}:
            raise ValueError('Expected one complete source-label pair per group')
        if any(len({r[field] for r in group}) != 1 for field in ('partition', 'task', 'pair_id')):
            raise ValueError('Pair task/partition/identity mismatch')
    counts = collections.Counter(group[0]['partition'] for group in by_group.values())
    if counts != {'development': result['development_groups'], 'confirmation': result['confirmation_groups']}:
        raise ValueError('Locked partition group count mismatch')
    safe_rows = [{k: row[k] for k in ('id', 'group_id', 'pair_id', 'upstream_label', 'partition', 'input_sha256')}
                 for row in rows]
    if safe_rows != result['selected']:
        raise ValueError('Tracked selection and ignored source rows disagree')
    if sha256(canonical_bytes({'selected': safe_rows, 'subsets': result['subsets']})) != result['selection_lock_sha256']:
        raise ValueError('Selection lock differs')
    confirmation = {g for g, rs in by_group.items() if rs[0]['partition'] == 'confirmation'}
    development = set(by_group) - confirmation
    subsets = result['subsets']
    if (not set(subsets['general']) <= confirmation or not set(subsets['audit']) <= confirmation
            or not set(subsets['repeat_native']) <= confirmation
            or not set(subsets['repeat_general']) <= set(subsets['general'])
            or not set(subsets['development_execute']) <= development):
        raise ValueError('Nested main subset boundary violated')
    audit = read_rows(ROOT / result['outputs']['audit_packet']['path'])
    if [r['group_id'] for r in audit] != subsets['audit']:
        raise ValueError('Audit packet differs from pre-prediction selection')
    for pair in audit:
        source = {r['upstream_label']: r for r in by_group[pair['group_id']]}
        if (pair['task'] != source[0]['task'] or pair['clean']['candidate'] != source[0]['candidate']
                or pair['attack']['candidate'] != source[1]['candidate']
                or pair['clean']['source_label'] != 0 or pair['attack']['source_label'] != 1):
            raise ValueError('Audit packet source labels/text differ')
    return {'selected_pages': len(rows), 'development_groups': len(development),
            'confirmation_groups': len(confirmation), 'target_met': result['target_met'],
            'new_model_calls': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--history-root', type=Path, default=HISTORY)
    parser.add_argument('--verify', action='store_true', help='Only verify existing local locks; no network')
    args = parser.parse_args()
    if args.verify:
        print(json.dumps(verify_locked(args.history_root), sort_keys=True))
    else:
        prepare(args.history_root)


if __name__ == '__main__':
    main()
