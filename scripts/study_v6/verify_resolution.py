"""Verify tracked resolution receipts, and optionally ignored reviewed rows, read-only."""
import argparse
import collections
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import ROOT, RAW, read, rank, sha256
from scripts.study_v6.resolve_review import RESULTS, DEST, pair_key, source_label


def verify(require_cache=False, with_adjudication=False):
    dest = RAW / 'review-resolution-v3' if with_adjudication else DEST
    resolution_path = RESULTS / ('resolution-final.json' if with_adjudication else 'resolution.json')
    resolution = json.loads(resolution_path.read_text())
    plan = json.loads((RESULTS / 'planning-final.json').read_text()) if with_adjudication else None
    verification = json.loads((RESULTS / 'verification.json').read_text())
    for name, expected in verification['tracked_sha256'].items():
        if sha256((ROOT / name).read_bytes()) != expected:
            raise ValueError('Tracked file changed: ' + name)
    assert resolution['input_rows'] == resolution['review_eligible_rows'] + resolution['quarantined_rows']
    assert sum(s['review_eligible'] for s in resolution['source_counts'].values()) == resolution['review_eligible_rows']
    assert resolution['review_resolution_complete'] == (resolution['unresolved_review_actions'] == 0)
    assert not resolution['inference_ready'] and resolution['new_model_calls'] == 0
    if with_adjudication:
        assert resolution['review_resolution_complete'] and resolution['adjudication_completed']
        assert not plan['inference_ready'] and plan['new_model_calls'] == 0
        assert plan['resolution_receipt_sha256'] == sha256(resolution_path.read_bytes())
    if require_cache:
        receipts = list(resolution['inputs'].values()) + list(resolution['outputs'].values())
        if plan: receipts += list(plan['manifests'].values())
        for receipt in receipts:
            assert sha256((ROOT / receipt['path']).read_bytes()) == receipt['sha256'], receipt['path']
        originals = {r['id']: r for r in read(RAW / 'prepared.jsonl')}
        mapping = {r['id']: r for r in read(RAW / 'review-mapping.jsonl')}
        rows = read(dest / 'resolved.jsonl')
        by_id = {r['id']: r for r in rows}
        assert len(by_id) == len(rows) and set(by_id) == set(originals)
        groups, old_groups, pairs = collections.defaultdict(list), collections.defaultdict(set), collections.defaultdict(list)
        for row in rows:
            original = originals[row['id']]
            assert all(row[k] == original[k] for k in ('candidate', 'task', 'policy', 'setting', 'source', 'upstream_label', 'provenance'))
            assert row['review_id'] == mapping[row['id']]['review_id']
            assert not row['inference_eligible']
            if row['review_eligible']:
                assert not row['exclusion_reasons']
                assert row['semantic_gold'] == source_label(row['upstream_label'])
                assert row['reviewed_verdict'] == ('violation' if row['semantic_gold'] else 'allowed')
                if row['reviewer_ambiguity'].strip().lower() != 'none':
                    assert row['adjudication'] is not None
                    assert row['adjudication']['verdict'] == row['reviewed_verdict']
                    assert row['adjudication']['ambiguity'].strip().lower() == 'none'
                    assert not row['adjudication'].get('group_merge_ids', '').strip()
            else:
                assert row['exclusion_reasons'] and row['semantic_gold'] is None
            groups[row['group']].append(row)
            old_groups[original['group']].add(row['group'])
            if pair_key(row): pairs[pair_key(row)].append(row)
        assert all(len(values) == 1 for values in old_groups.values())
        for pair in pairs.values():
            assert len(pair) == 2
            assert len({r['group'] for r in pair}) == len({r['review_eligible'] for r in pair}) == 1
        for gid, members in groups.items():
            assert gid == 'v6:' + min(rank(r['id']) for r in members)
            split = 'development' if int(rank('split:' + gid)[:8], 16) % 5 == 0 else 'confirmation'
            assert all(r['split_proposal'] == split for r in members)
        for decision in read(dest / 'group-resolutions.jsonl'):
            members = [by_id[i] for i in decision['source_ids']]
            if decision['action'] == 'merge': assert len({r['group'] for r in members}) == 1
            if decision['action'] == 'quarantine_component': assert all(not r['review_eligible'] for r in members)
        for entry in read(dest / 'link-resolutions.jsonl'):
            a, b = [by_id[i] for i in entry['source_ids']]
            if entry['disposition'] == 'same_final_component': assert a['group'] == b['group']
            elif entry['disposition'] == 'endpoint_component_quarantined':
                assert any(any(s.startswith('grouping:') for s in r['exclusion_reasons']) for r in (a, b))
            else: assert entry['disposition'] == 'rejected_broad_or_unsupported_relation'
        if plan:
            target = read(dest / 'primary-target.jsonl')
            ids = [i for g in target for i in g['ids']]
            assert len(set(ids)) == len(ids)
            assert set(ids) == {r['id'] for r in rows if r['review_eligible'] and r['source'] == 'browsesafe' and r['split_proposal'] == 'confirmation'}
            assert [g['group'] for g in target] == sorted((g['group'] for g in target), key=lambda g: rank('budget-order:' + g))
            prefix = read(dest / 'primary-reservation-prefix.jsonl')
            assert [g['group'] for g in prefix] == [g['group'] for g in target[:len(prefix)]]
    return {'verified': True, 'require_cache': require_cache, 'review_resolution_complete': resolution['review_resolution_complete'],
            'review_eligible_rows': resolution['review_eligible_rows'], 'inference_ready': False}


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--require-cache', action='store_true')
    parser.add_argument('--with-adjudication', action='store_true')
    args = parser.parse_args()
    print(json.dumps(verify(args.require_cache, args.with_adjudication)))
