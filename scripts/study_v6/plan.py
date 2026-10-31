"""Pure v6 scheduling and exact, split-isolated request deduplication.

This module never imports credentials or dispatches requests. Source text and labels
are written only below the ignored raw directory by the execution preparation CLI.
"""
from __future__ import annotations

import collections
import csv
import json
from pathlib import Path

from scripts.study_v6.common import ROOT, RAW, rank, sha256, canonical_bytes, read
from scripts.study_v5.prompts import conditions, native_payload, evidence
from scripts.study_v6.pricing import reserve
from scripts.study_v6.resolve_review import source_label

VERSION = 'study-v6-execution-1'
DEST = RAW / 'execution-v1'
RESULTS = ROOT / 'results/study-v6-execution'
PRIMARY = ('format', 'task', 'reminder', 'length')
PAID = ('jev_firstparty', 'luna_decisions')
COMPARATORS = ('luna_chat', 'astra_chat', 'laya_local', 'nimble_local')
CONFIGS = PAID + COMPARATORS + ('protectai_local',)
PROVIDERS = {'jev_firstparty': 'typesafe', 'luna_decisions': 'openai'}
RATES = {'openai': .10, 'typesafe': .042}
SOURCES = ('aib', 'spml', 'infuse', 'nvidia', 'scope')
LEXICAL_PHRASES = ('ignore previous', 'system prompt', 'do not tell', 'new task')


def request(config, row, condition):
    if config == 'protectai_local':
        from scripts.study_v6.routes import payload
        return payload(config, row, condition)
    return native_payload(row, condition, config)


def development_rows(rows):
    """Longest per label, then hash-first new groups; at most four per source."""
    selected = []
    for source in sorted({r['source'] for r in rows}):
        part = [r for r in rows if r['source'] == source and r['review_eligible']
                and r['split_proposal'] == 'development']
        chosen = []
        for label in (0, 1):
            candidates = [r for r in part if r['semantic_gold'] == label]
            if candidates:
                chosen.append(min(candidates, key=lambda r: (
                    -len(r['candidate'].encode()), rank('development:' + r['id']))))
        groups = {r['group'] for r in chosen}
        for row in sorted(part, key=lambda r: rank('development:' + r['id'])):
            if len(chosen) >= 4:
                break
            if row['group'] not in groups:
                chosen.append(row)
                groups.add(row['group'])
        selected.extend(chosen)
    return selected


def group_order(rows):
    return sorted({r['group'] for r in rows}, key=lambda g: rank('budget-order:' + g))


def fixed_schedules(rows):
    admitted = [r for r in rows if r['review_eligible']]
    confirmation = [r for r in admitted if r['split_proposal'] == 'confirmation']
    main = [r for r in confirmation if r['source'] == 'browsesafe']
    primary = [{'group': g, 'source': 'browsesafe', 'kind': 'main',
                'ids': sorted(r['id'] for r in main if r['group'] == g)}
               for g in group_order(main)]
    by_source = {s: [{'group': g, 'source': s, 'kind': 'secondary',
                     'ids': sorted(r['id'] for r in confirmation if r['source'] == s and r['group'] == g)}
                    for g in group_order([r for r in confirmation if r['source'] == s])[:12]]
                 for s in SOURCES}
    supporting = [by_source[s][i] for i in range(12) for s in SOURCES if i < len(by_source[s])]
    extras = [dict(g, kind='main_extras') for g in primary[:100]]
    dev = collections.defaultdict(list)
    for row in development_rows(admitted):
        dev[(row['source'], row['group'])].append(row['id'])
    return {'main': primary, 'supporting': supporting + extras,
            'comparators': [dict(g) for g in primary[:100] + supporting],
            'development': [{'group': g, 'source': s, 'kind': 'development', 'ids': sorted(ids)}
                            for (s, g), ids in dev.items()]}


def build(rows, coverage=None, review_subgroups=None):
    """Return immutable intended cells, unique requests and whole-group schedules.

    Missing coverage is pending, never permission to dispatch. Exact duplicates
    share a request within config/split; every source row/condition retains a ref.
    """
    coverage = coverage or {}
    review_subgroups = review_subgroups or {}
    lookup = {r['id']: r for r in rows}
    if len(lookup) != len(rows):
        raise ValueError('Duplicate source row')
    if any(r.get('inference_eligible') for r in rows):
        raise ValueError('Prepared rows must remain ineligible; gates belong to frozen requests')
    for row in rows:
        if row['review_eligible'] and (row.get('exclusion_reasons') or type(row.get('semantic_gold')) is not int
                or row['semantic_gold'] not in (0, 1)):
            raise ValueError('Invalid reviewed admission')
    schedules = fixed_schedules(rows)
    cells, requests, batches, seen = [], {}, collections.defaultdict(list), set()
    request_cells = collections.defaultdict(list)
    batch_cells = collections.defaultdict(list)

    def add(row, config, condition, allocation, batch):
        split = 'development' if allocation == 'development' else 'confirmation'
        identity = (row['id'], config, condition, split)
        if identity in seen:
            raise ValueError('Duplicate planned cell')
        seen.add(identity)
        payload = request(config, row, condition)
        # Verify only explicitly permitted fields, without a dangerous annotation
        # substring blacklist (source text can legitimately contain those words).
        if config != 'protectai_local':
            ev = evidence(row, condition)
            key = 'USER_MESSAGE' if row['setting'] == 'system_policy_boundary' else 'CANDIDATE'
            if ev[key] != row['candidate']:
                raise ValueError('Candidate changed across intervention')
        digest = sha256(canonical_bytes(payload))
        request_key = sha256(canonical_bytes([VERSION, split, config, digest]))
        cov = coverage.get((row['id'], config, condition), {'status': 'pending'})
        if cov.get('payload_sha256', digest) != digest:
            raise ValueError('Coverage request hash mismatch')
        supported = cov.get('supported') is True or cov.get('status') == 'complete'
        cell = {'id': row['id'], 'source': row['source'], 'group': row['group'],
                'gold': row['semantic_gold'], 'upstream_label': source_label(row['upstream_label']),
                'label_basis': row.get('label_basis'), 'setting': row['setting'],
                'pair_id': row.get('pair_id') or row.get('provenance', {}).get('pair_id'),
                'review_subgroups': review_subgroups.get(row['review_id'], {}),
                'config': config, 'condition': condition, 'split': split,
                'allocation': allocation, 'batch': batch, 'request_key': request_key,
                'payload_sha256': digest, 'coverage_status': cov.get('status', 'pending'),
                'coverage_supported': supported, 'inference_eligible': False}
        cells.append(cell)
        request_cells[request_key].append(cell)
        batch_cells[(allocation, batch)].append(cell)
        ref = {'id': row['id'], 'condition': condition, 'source': row['source'], 'group': row['group']}
        if request_key in requests:
            previous = requests[request_key]
            previous['refs'].append(ref)
            previous['coverage_supported'] &= supported
            if request_key not in batches[(allocation, batch)]:
                batches[(allocation, batch)].append(request_key)
        else:
            provider = PROVIDERS.get(config)
            requests[request_key] = {'key': request_key, 'config': config, 'split': split,
                'allocation': allocation, 'batch': batch, 'provider': provider,
                'payload': payload, 'request_sha256': digest, 'refs': [ref],
                'reserved_usd': reserve(payload, provider) if provider else '0',
                'coverage_supported': supported, 'inference_eligible': False}
            batches[(allocation, batch)].append(request_key)

    for allocation in ('main', 'supporting', 'development'):
        for i, entry in enumerate(schedules[allocation]):
            batch = f'{allocation}:{i:04d}:{entry["source"]}:{entry["group"]}'
            entry['batch'] = batch
            for rid in entry['ids']:
                row = lookup[rid]
                configs = CONFIGS if allocation == 'development' else PAID
                for config in configs:
                    if config == 'protectai_local' and row['source'] in ('spml', 'scope'):
                        continue
                    conds = (('candidate',) if config == 'protectai_local' else
                             PRIMARY if allocation == 'main' else
                             ('candidate', 'scrambled') if entry['kind'] == 'main_extras' else conditions(row))
                    for condition in conds:
                        add(row, config, condition, allocation, batch)
    for i, entry in enumerate(schedules['comparators']):
        batch = f'comparators:{i:04d}:{entry["source"]}:{entry["group"]}'
        entry['batch'] = batch
        for rid in entry['ids']:
            row = lookup[rid]
            for config in COMPARATORS + ('protectai_local',):
                if config == 'protectai_local' and row['source'] in ('spml', 'scope'):
                    continue
                for condition in (('candidate',) if config == 'protectai_local' else conditions(row)):
                    add(row, config, condition, 'comparators', batch)

    # Route full-input coverage preserves explicit pairs and the same four native
    # conditions/provider cohort. Never admit a short pair member on its own.
    blocks = collections.defaultdict(list)
    for cell in cells:
        row = lookup[cell['id']]
        pair = cell['pair_id'] if cell['pair_id'] is not None else cell['id']
        family = 'native_main' if cell['allocation'] == 'main' else cell['config']
        blocks[(cell['split'], cell['allocation'], cell['source'], str(pair), family)].append(cell)
    for block in blocks.values():
        if not all(c['coverage_supported'] for c in block):
            for cell in block:
                cell['coverage_supported'] = False
                if cell['coverage_status'] == 'complete':
                    cell['coverage_status'] = 'unsupported_paired_common_coverage'
    for req in requests.values():
        refs = request_cells[req['key']]
        # A shared request can serve a covered pair while another reference is
        # excluded because its *partner* is too long. Retain that excluded ref;
        # it must not be expanded into an admitted prediction by the runner.
        req['coverage_supported'] = any(c['coverage_supported'] for c in refs)
    for allocation, entries in schedules.items():
        for entry in entries:
            keys = batches[(allocation, entry['batch'])]
            entry['request_keys'] = keys
            entry['all_requests_supported'] = all(c['coverage_supported'] for c in batch_cells[(allocation, entry['batch'])])
    return {'version': VERSION, 'schedules': schedules, 'cells': cells,
            'requests': list(requests.values()), 'lexical_phrases': list(LEXICAL_PHRASES)}


def load_review_subgroups():
    with (RAW / 'reviews/reviewer-A.csv').open(newline='') as handle:
        return {r['review_id']: {k: r[k] for k in ('task_relation', 'instruction_type')}
                for r in csv.DictReader(handle)}


def summary(plan):
    cells = plan['cells']
    return {'version': VERSION, 'planned_cells': len(cells), 'unique_requests': len(plan['requests']),
            'deduplicated_references': len(cells) - len(plan['requests']),
            'by_split_configuration': {':'.join(k): {'planned_cells': len(v),
                'supported_cells': sum(c['coverage_supported'] for c in v)}
                for k, v in _parts(cells, ('split', 'config')).items()},
            'schedules': {k: {'groups': len(v), 'rows': len({rid for g in v for rid in g['ids']})}
                          for k, v in plan['schedules'].items()},
            'inference_ready': False, 'new_model_calls': 0}


def _parts(rows, keys):
    parts = collections.defaultdict(list)
    for row in rows:
        parts[tuple(row[k] for k in keys)].append(row)
    return parts
