"""Supplemental execution quarantine for every locked reviewer-B grouping concern.

The original v3 review resolution remains immutable. This gate neither adjudicates
labels nor merges/splits groups: every complete final component touched by a B
proposal is excluded from execution, including proposals preserved only in logs.
"""
from __future__ import annotations

import argparse
import collections
import csv
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import ROOT, RAW, read, canonical_bytes, sha256
from scripts.study_v6.evidence import immutable, load, file_receipt

VERSION = 'v6-execution-grouping-admission-1'
DEST = RAW / 'execution-v1'
RESULTS = ROOT / 'results/study-v6-execution'
EXPECTED_SIDECAR_SHA256 = 'ec198eed973c061517533d5aaf8c11692a5c89a681328fb1836e7c4299adc0e9'
EXPECTED_PAIRS = 54
EXPECTED_OBSERVATIONS = 88
EXPECTED_B_ROWS = 1749
REASON = 'adjudicator_grouping_component_quarantine'


def _ids(value, known, *, delimiter=False):
    if delimiter:
        if not isinstance(value, str):
            raise ValueError('CSV grouping field must be a string')
        value = [] if not value.strip() else [v.strip() for v in value.split(';')]
    if not isinstance(value, list) or any(not isinstance(v, str) or not v or v != v.strip() for v in value):
        raise ValueError('Grouping IDs must be a list of nonempty exact strings')
    if len(value) != len(set(value)):
        raise ValueError('Duplicate grouping target')
    if not set(value) <= known:
        raise ValueError('Unknown grouping review ID')
    return value


def _pair(a, b, known):
    _ids([a, b], known)
    return tuple(sorted((a, b)))


def apply(rows, sidecar, bcsv):
    """Return derived rows, safe aggregate counts, and ignored raw dispositions.

    Production counts/hashes are enforced by the file wrapper; this pure function
    supports small complete fixtures. Repeated *observations* of one pair are
    legitimate; duplicate pair declarations or identical observation records fail.
    """
    by_review, source_ids = {}, set()
    for row in rows:
        rid, sid = row['review_id'], row['id']
        if not isinstance(rid, str) or not rid or rid in by_review or sid in source_ids:
            raise ValueError('Missing or duplicate source/review identity')
        if not isinstance(row['group'], str) or not row['group'] or type(row['review_eligible']) is not bool:
            raise ValueError('Invalid original group or review admission')
        if row.get('inference_eligible') is not False:
            raise ValueError('Original prepared inference flags must remain false')
        if row['review_eligible'] and (type(row['semantic_gold']) is not int or row['semantic_gold'] not in (0, 1)):
            raise ValueError('Original review admission lacks a binary label')
        if any(k in row for k in ('execution_group_eligible', 'execution_exclusion_reasons')):
            raise ValueError('Apply only to preserved v3 rows, not already derived rows')
        by_review[rid] = row
        source_ids.add(sid)
    known = set(by_review)
    if not isinstance(sidecar, dict) or sidecar.get('certified') is not False:
        raise ValueError('Expected uncertified packet-only grouping sidecar')
    raw_pairs = sidecar.get('pairs')
    if not isinstance(raw_pairs, list):
        raise ValueError('Missing sidecar pairs')
    pairs = set()
    for pair in raw_pairs:
        if not isinstance(pair, list) or len(pair) != 2:
            raise ValueError('Grouping proposal must be exactly a pair')
        canonical = _pair(pair[0], pair[1], known)
        if canonical in pairs:
            raise ValueError('Duplicate sidecar pair')
        pairs.add(canonical)
    if type(sidecar.get('unique_pair_count')) is not int or sidecar['unique_pair_count'] != len(pairs):
        raise ValueError('Sidecar declared pair count differs')

    csv_directed, csv_pairs, csv_rows = set(), set(), set()
    for row in bcsv:
        rid = row['review_id']
        _ids([rid], known)
        if rid in csv_rows:
            raise ValueError('Duplicate reviewer-B CSV row')
        csv_rows.add(rid)
        for target in _ids(row['group_merge_ids'], known, delimiter=True):
            pair = _pair(rid, target, known)
            csv_directed.add((rid, target))
            csv_pairs.add(pair)
    if not csv_pairs <= pairs:
        raise ValueError('CSV grouping link missing from sidecar')

    observations = sidecar.get('observations')
    if not isinstance(observations, list):
        raise ValueError('Missing complete sidecar observations')
    observed_pairs, observed_csv, seen_observations = collections.Counter(), set(), set()
    for observation in observations:
        if not isinstance(observation, dict) or not isinstance(observation.get('source'), str) or not observation['source']:
            raise ValueError('Observation source missing')
        fingerprint = sha256(canonical_bytes(observation))
        if fingerprint in seen_observations:
            raise ValueError('Duplicate exact grouping observation')
        seen_observations.add(fingerprint)
        if 'record' in observation:
            if 'review_id' in observation or 'group_merge_ids' in observation:
                raise ValueError('Ambiguous grouping observation schema')
            record = observation['record']
            if not isinstance(record, dict) or sum(k in record for k in ('review_ids', 'ids')) != 1:
                raise ValueError('Log grouping record must identify its pair')
            ids = _ids(record.get('review_ids', record.get('ids')), known)
            if len(ids) != 2:
                raise ValueError('Log observation must contain exactly two distinct IDs')
            observed_pairs[_pair(*ids, known)] += 1
        else:
            if observation['source'] != 'reviewer-B.csv':
                raise ValueError('CSV observation source differs')
            rid = observation['review_id']
            _ids([rid], known)
            targets = _ids(observation['group_merge_ids'], known)
            if not targets:
                raise ValueError('Empty CSV grouping observation')
            for target in targets:
                directed = (rid, target)
                if directed in observed_csv:
                    raise ValueError('Duplicate directed CSV observation')
                observed_csv.add(directed)
                observed_pairs[_pair(rid, target, known)] += 1
    if observed_csv != csv_directed:
        raise ValueError('Sidecar CSV observations differ from locked reviewer CSV')
    if set(observed_pairs) != pairs:
        raise ValueError('Sidecar pair list differs from observation union')

    held_groups = {by_review[rid]['group'] for pair in pairs for rid in pair}
    derived, dispositions = [], []
    for original in rows:
        held = original['group'] in held_groups
        reasons = [REASON] if held else []
        derived.append(dict(original, execution_group_eligible=not held, execution_exclusion_reasons=reasons))
        dispositions.append({'id': original['id'], 'review_id': original['review_id'],
            'group': original['group'], 'review_eligible': original['review_eligible'],
            'execution_group_eligible': not held, 'execution_exclusion_reasons': reasons})
    admitted = lambda r: r['review_eligible'] and r['execution_group_eligible']
    aggregate = {'version': VERSION, 'input_rows': len(rows),
        'unique_proposal_pairs': len(pairs), 'observation_records': len(observations),
        'csv_unique_pairs': len(csv_pairs), 'sidecar_only_pairs': len(pairs - csv_pairs),
        'held_final_components': len(held_groups),
        'rows_in_held_final_components': sum(not r['execution_group_eligible'] for r in derived),
        'review_eligible_rows_before_execution_grouping': sum(r['review_eligible'] for r in rows),
        'review_quarantined_rows_preserved': sum(not r['review_eligible'] for r in rows),
        'newly_execution_excluded_review_eligible_rows': sum(r['review_eligible'] and not r['execution_group_eligible'] for r in derived),
        'execution_admitted_rows': sum(admitted(r) for r in derived), 'source_counts': {},
        'policy': 'Quarantine complete final v3 components touched by any B sidecar proposal; preserve original labels, review eligibility, source fields, groups and splits.',
        'inference_ready': False, 'new_model_calls': 0}
    for source in sorted({r['source'] for r in rows}):
        part = [r for r in derived if r['source'] == source]
        before = [r for r in part if r['review_eligible']]
        after = [r for r in part if admitted(r)]
        aggregate['source_counts'][source] = {'prepared_rows': len(part),
            'review_quarantined_rows_preserved': len(part)-len(before),
            'review_eligible_rows_before_execution_grouping': len(before),
            'newly_execution_excluded_review_eligible_rows': len(before)-len(after),
            'execution_admitted_rows': len(after),
            'admitted_label_support': dict(sorted(collections.Counter(str(r['semantic_gold']) for r in after).items())),
            'by_split': {split: {'rows': sum(r['split_proposal'] == split for r in after),
                'groups': len({r['group'] for r in after if r['split_proposal'] == split})}
                for split in ('development', 'confirmation')}}
    raw = {'version': VERSION, 'pairs': [{'review_ids': list(pair),
        'final_components': sorted({by_review[rid]['group'] for rid in pair}),
        'present_in_csv': pair in csv_pairs, 'observation_count': observed_pairs[pair],
        'disposition': 'quarantine_every_endpoint_final_component'} for pair in sorted(pairs)],
        'rows': dispositions}
    return derived, aggregate, raw


def _compute(rows_path=None, sidecar_path=None, bcsv_path=None):
    resolution_path = ROOT / 'results/study-v6-review-resolution/resolution-final.json'
    resolution = load(resolution_path)
    if not resolution['review_resolution_complete'] or not resolution['adjudication_completed']:
        raise PermissionError('Complete original final adjudication resolution is required')
    paths = {'resolved_rows': Path(rows_path or RAW / 'review-resolution-v3/resolved.jsonl'),
        'grouping_sidecar': Path(sidecar_path or RAW / 'adjudication-v1/reviewer-B-grouping-proposals.json'),
        'reviewer_b_csv': Path(bcsv_path or RAW / 'adjudication-v1/reviewer-B.csv')}
    if paths['resolved_rows'].resolve() != (ROOT / resolution['outputs']['resolved']['path']).resolve():
        raise ValueError('Use only the preserved final v3 resolved rows')
    if sha256(paths['resolved_rows'].read_bytes()) != resolution['outputs']['resolved']['sha256']:
        raise ValueError('Original v3 resolved rows changed')
    if sha256(paths['grouping_sidecar'].read_bytes()) != EXPECTED_SIDECAR_SHA256:
        raise ValueError('Grouping sidecar differs from complete reviewer-B handoff')
    for receipt in resolution['inputs'].values():
        if sha256((ROOT / receipt['path']).read_bytes()) != receipt['sha256']:
            raise ValueError('Original resolution input changed: ' + receipt['path'])
    inputs = resolution['inputs']
    if paths['reviewer_b_csv'].resolve() != (ROOT / inputs['adjudication_reviews']['path']).resolve():
        raise ValueError('Reviewer-B CSV differs from final resolution input')
    lock = load(ROOT / inputs['adjudication_lock']['path'])
    for key, field in (('adjudication_reviews', 'reviews_sha256'), ('adjudication_packet', 'packet_sha256'),
            ('adjudication_session', 'session_sha256')):
        if inputs[key]['sha256'] != lock[field]:
            raise ValueError('Complete adjudication lock hash mismatch')
    with paths['reviewer_b_csv'].open(newline='') as stream:
        bcsv = list(csv.DictReader(stream))
    packet = read(ROOT / inputs['adjudication_packet']['path'])
    if (lock['rows'] != EXPECTED_B_ROWS or len(bcsv) != EXPECTED_B_ROWS or len(packet) != EXPECTED_B_ROWS or
            len({r['review_id'] for r in packet}) != EXPECTED_B_ROWS or
            {r['review_id'] for r in packet} != {r['review_id'] for r in bcsv}):
        raise ValueError('Complete distinct adjudication packet/CSV lock required')
    sidecar = load(paths['grouping_sidecar'])
    if len(sidecar['pairs']) != EXPECTED_PAIRS or len(sidecar['observations']) != EXPECTED_OBSERVATIONS:
        raise ValueError('Complete grouping sidecar requires every pair and observation')
    derived, aggregate, dispositions = apply(read(paths['resolved_rows']), sidecar, bcsv)
    rows_body = b''.join(canonical_bytes(r) + b'\n' for r in derived)
    disposition_body = canonical_bytes(dispositions) + b'\n'
    aggregate.update(inputs={key: file_receipt(path, ROOT) for key, path in sorted(paths.items())},
        final_resolution=file_receipt(resolution_path, ROOT),
        original_resolution_inputs={key: {'path': value['path'], 'sha256': value['sha256']}
            for key, value in sorted(inputs.items())},
        outputs={'group_admitted_rows': {'path': str((DEST / 'group-admitted-rows.jsonl').relative_to(ROOT)),
            'sha256': sha256(rows_body), 'rows': len(derived)},
            'grouping_dispositions': {'path': str((DEST / 'grouping-dispositions.json').relative_to(ROOT)),
                'sha256': sha256(disposition_body)}})
    return derived, aggregate, rows_body, disposition_body


def finalize(rows_path=None, sidecar_path=None, bcsv_path=None):
    derived, aggregate, rows_body, dispositions = _compute(rows_path, sidecar_path, bcsv_path)
    immutable(DEST / 'group-admitted-rows.jsonl', rows_body)
    immutable(DEST / 'grouping-dispositions.json', dispositions)
    immutable(RESULTS / 'grouping-admission-v1.json', aggregate)
    return derived, aggregate


def verify(rows_path=None, sidecar_path=None, bcsv_path=None):
    """Recompute all admission and hash checks without writing any artifact."""
    derived, aggregate, rows_body, dispositions = _compute(rows_path, sidecar_path, bcsv_path)
    for path, expected in ((DEST / 'group-admitted-rows.jsonl', rows_body),
            (DEST / 'grouping-dispositions.json', dispositions),
            (RESULTS / 'grouping-admission-v1.json', canonical_bytes(aggregate) + b'\n')):
        if path.read_bytes() != expected:
            raise ValueError('Supplemental grouping admission artifact changed: ' + str(path))
    return derived, aggregate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    _, aggregate = verify() if args.verify else finalize()
    print(json.dumps({key: aggregate[key] for key in ('version', 'unique_proposal_pairs',
        'csv_unique_pairs', 'sidecar_only_pairs', 'held_final_components',
        'review_eligible_rows_before_execution_grouping', 'newly_execution_excluded_review_eligible_rows',
        'execution_admitted_rows', 'inference_ready')}))


if __name__ == '__main__':
    main()
