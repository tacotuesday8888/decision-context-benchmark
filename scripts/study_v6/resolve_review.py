"""Resolve reviewed v6 data without relabeling, inference or overwriting preparation.

All scientific decisions are explicit in POLICY.json. Derived raw files stay local;
the aggregate receipt pins every input and output. A verify mode recomputes in memory.
"""
from __future__ import annotations
import argparse
import collections
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import (ROOT, RAW, OUT, Union, read, rank, sha256,
                                     canonical_bytes, preserve_write)
from scripts.study_v6.reviews import validate_complete

VERSION = 'v6-review-resolution-2'
DEST = RAW / 'review-resolution-v2'
RESULTS = ROOT / 'results/study-v6-review-resolution'
POLICY = ROOT / 'docs/study-v6-review-resolution/POLICY.json'


def unique(rows, field):
    result = {r[field]: r for r in rows}
    if len(result) != len(rows):
        raise ValueError('Duplicate ' + field)
    return result


def source_label(value):
    if value == 'safe' or type(value) is int and value == 0:
        return 0
    if value == 'unsafe' or type(value) is int and value == 1:
        return 1
    raise ValueError('Unrecognized upstream label')


def pair_key(row):
    pair = row.get('pair_id') or row.get('provenance', {}).get('pair_id')
    return (row['source'], str(pair)) if pair is not None else None


def resolve(rows, mapping, packet, reviews, group_records, links, edges, policy,
            exposure_ids=(), adjudications=None):
    """Pure coordinator decisions. No model outputs or filesystem access."""
    by_id = unique(rows, 'id')
    by_map = unique(mapping, 'id')
    by_review = unique(reviews, 'review_id')
    by_packet = unique(packet, 'review_id')
    if set(by_id) != set(by_map):
        raise ValueError('Prepared/mapping ID mismatch')
    if {r['review_id'] for r in mapping} != set(by_review) or set(by_review) != set(by_packet):
        raise ValueError('Packet/review/mapping mismatch')
    fixes = []
    for row in rows:
        mapped = by_map[row['id']]
        # Only the known inherited review-ID discrepancy is permitted.
        if {k: v for k, v in row.items() if k != 'review_id'} != {
                k: v for k, v in mapped.items() if k != 'review_id'}:
            raise ValueError('Changed source fields in mapping: ' + row['id'])
        rid = mapped['review_id']
        for field in ('candidate', 'task', 'policy', 'setting'):
            if mapped[field] != by_packet[rid][field]:
                raise ValueError('Packet content differs: ' + field)
        if row.get('review_id') and row['review_id'] != rid:
            fixes.append({'id': row['id'], 'old_review_id': row['review_id'], 'review_id': rid})

    index = {r['id']: i for i, r in enumerate(rows)}
    source_for_review = {r['review_id']: r['id'] for r in mapping}
    locked_links = set()
    for review in reviews:
        for rid in review.get('group_merge_ids', '').split(';'):
            if rid.strip():
                a, b = source_for_review[review['review_id']], source_for_review[rid.strip()]
                # The locked review contains one self-reference. Retain its
                # audit record (a no-op), rather than silently dropping it.
                locked_links.add(tuple(sorted((a, b))))
    if locked_links != {tuple(sorted(link['source_ids'])) for link in links}:
        raise ValueError('Blinded link ledger does not match locked review CSV')
    u = Union(len(rows))
    old_groups, pairs = collections.defaultdict(list), collections.defaultdict(list)
    for row in rows:
        old_groups[row['group']].append(row['id'])
        if pair_key(row):
            pairs[pair_key(row)].append(row['id'])

    def join(ids):
        if not ids or any(i not in index for i in ids):
            raise ValueError('Empty or unknown group member')
        for other in ids[1:]:
            u.join(index[ids[0]], index[other])

    for members in list(old_groups.values()) + list(pairs.values()):
        join(members)
    for edge in edges:
        if edge['a'] not in index or edge['b'] not in index:
            raise ValueError('Unknown original edge endpoint')
        if by_id[edge['a']]['group'] != by_id[edge['b']]['group']:
            raise ValueError('Original grouping omitted an edge')

    proposals = {r['proposal_id']: r for r in group_records if 'proposal_id' in r}
    if len(proposals) != sum('proposal_id' in r for r in group_records):
        raise ValueError('Duplicate proposal ID')
    if set(proposals) != set(policy['proposals']):
        raise ValueError('Every proposal needs an explicit coordinator decision')
    resolutions, quarantine_seeds = [], collections.defaultdict(set)
    for pid, decision in policy['proposals'].items():
        prop = proposals[pid]
        ids = prop['source_ids']
        if len(set(ids)) != len(ids) or any(i not in index for i in ids):
            raise ValueError('Invalid proposal membership')
        if set(prop['review_ids']) != {by_map[i]['review_id'] for i in ids}:
            raise ValueError('Proposal ID join mismatch')
        action = decision['action']
        if action == 'merge':
            join(ids)
        elif action == 'quarantine_component':
            for i in ids:
                quarantine_seeds[i].add('grouping:' + pid)
        elif action != 'reject_weak_cross_source':
            raise ValueError('Unknown proposal decision')
        resolutions.append({'proposal_id': pid, **decision, 'source_ids': ids,
                            'reviewer_proposal': prop['proposal'],
                            'reviewer_evidence_sha256': sha256(canonical_bytes(prop))})

    # Explicit cross-source dispositions supplement component-level decisions.
    bridge_decisions = {}
    for record in group_records:
        if record['kind'] != 'cross_source_bridge_review':
            continue
        key = tuple(sorted(record['source_ids']))
        action = policy['cross_source_links'][record['post_lock_disposition']]
        if len(key) != 2 or any(i not in index for i in key) or key in bridge_decisions:
            raise ValueError('Invalid bridge identity')
        bridge_decisions[key] = action
        if action == 'quarantine_component':
            for i in key:
                quarantine_seeds[i].add('grouping:cross_source_compliance_bridge')
        elif action != 'reject':
            raise ValueError('Unknown bridge action')

    used_extra = set()
    for link in links:
        key = tuple(sorted(link['source_ids']))
        link_id = sha256(canonical_bytes(list(key)))
        if link_id not in policy.get('additional_links', {}):
            continue
        decision = policy['additional_links'][link_id]
        if decision['action'] != 'quarantine_component':
            raise ValueError('Unknown additional-link disposition')
        used_extra.add(link_id)
        for i in key:
            quarantine_seeds[i].add('grouping:additional_link:' + link_id)
    if used_extra != set(policy.get('additional_links', {})):
        raise ValueError('Additional link decision has no matching review link')

    components = collections.defaultdict(list)
    for row in rows:
        components[u.find(index[row['id']])].append(row['id'])
    final_group, splits, group_exclusions, groups = {}, {}, {}, []
    for ids in components.values():
        gid = 'v6:' + min(rank(i) for i in ids)
        split = 'development' if int(rank('split:' + gid)[:8], 16) % 5 == 0 else 'confirmation'
        reasons = sorted({reason for i in ids for reason in quarantine_seeds[i]})
        for i in ids:
            final_group[i], splits[i], group_exclusions[i] = gid, split, reasons
        groups.append({'group': gid, 'split': split, 'source_ids': sorted(ids),
                       'original_groups': sorted({by_id[i]['group'] for i in ids}),
                       'original_splits': sorted({by_id[i]['split_proposal'] for i in ids}),
                       'group_quarantine_reasons': reasons})

    # No recorded link can silently disappear between review and final cohort.
    link_records, seen_links = [], set()
    for link in links:
        key = tuple(sorted(link['source_ids']))
        if len(key) != 2 or any(i not in index for i in key) or key in seen_links:
            raise ValueError('Invalid/duplicate blinded link')
        seen_links.add(key)
        if key in bridge_decisions and bridge_decisions[key] == 'reject':
            disposition = 'rejected_broad_or_unsupported_relation'
        elif final_group[key[0]] == final_group[key[1]]:
            disposition = 'same_final_component'
        elif any(group_exclusions[i] for i in key):
            disposition = 'endpoint_component_quarantined'
        else:
            raise ValueError('Unresolved blinded grouping link: ' + str(key))
        link_records.append({'source_ids': list(key), 'disposition': disposition})
    if not set(bridge_decisions) <= seen_links:
        raise ValueError('Bridge absent from blinded link ledger')

    reasons, direct = collections.defaultdict(set), collections.defaultdict(set)
    for row in rows:
        i = row['id']
        review = by_review[by_map[i]['review_id']]
        verdict = review['verdict']
        if verdict not in ('allowed', 'violation'):
            direct[i].add('label:' + verdict)
        elif int(verdict == 'violation') != source_label(row['upstream_label']):
            direct[i].add('label:source_disagreement')
        if i in exposure_ids or row.get('prior_exposure_flags'):
            direct[i].add('historical_exposure')
        reasons[i].update(direct[i])
        reasons[i].update(group_exclusions[i])
    for ids in pairs.values():
        if any(reasons[i] for i in ids):
            for i in ids:
                if not reasons[i]:
                    reasons[i].add('paired_member_excluded')

    # A binary verdict does not erase the reviewer's explicit ambiguity. Only
    # the distinct adjudicator can distinguish label-relevant uncertainty from
    # incidental caveats; no lexical rules or coordinator defaults do so.
    candidates = {i for i in by_id if not reasons[i]}
    caveats = {by_map[i]['review_id']: i for i in candidates
               if by_review[by_map[i]['review_id']].get('ambiguity', 'none').strip().lower() != 'none'}
    adjudicated = unique(adjudications, 'review_id') if adjudications is not None else {}
    if adjudications is not None and set(adjudicated) != set(caveats):
        raise ValueError('Adjudication must cover exactly the complete caveat packet')
    new_group_holds = set()
    for rid, i in caveats.items():
        if adjudications is None:
            direct[i].add('label:caveat_adjudication_pending')
        else:
            judgment = adjudicated[rid]
            if (judgment['verdict'] != by_review[rid]['verdict'] or
                    judgment['ambiguity'].strip().lower() != 'none' or
                    judgment.get('group_merge_ids', '').strip()):
                direct[i].add('label:adjudication_unresolved_or_disagreed')
            if judgment.get('group_merge_ids', '').strip():
                linked = [i] + [source_for_review[r.strip()] for r in judgment['group_merge_ids'].split(';') if r.strip()]
                new_group_holds.update(final_group[j] for j in linked)
        reasons[i].update(direct[i])
    for i in by_id:
        if final_group[i] in new_group_holds:
            reasons[i].add('grouping:adjudicator_unresolved_link')
    for ids in pairs.values():
        if any(reasons[i] for i in ids):
            for i in ids:
                if not reasons[i]: reasons[i].add('paired_member_excluded')

    resolved, dispositions = [], []
    for original in rows:
        i = original['id']
        review = by_review[by_map[i]['review_id']]
        eligible = not reasons[i]
        row = dict(original)
        row.update(review_id=by_map[i]['review_id'], original_review_id=original.get('review_id'),
                   original_group=original['group'], original_split_proposal=original['split_proposal'],
                   group=final_group[i], split_proposal=splits[i],
                   review_status='agent_reviewed_source_agreement' if eligible else 'quarantined',
                   group_review='resolved_with_documented_exclusions',
                   reviewed_verdict=review['verdict'],
                   reviewer_ambiguity=review.get('ambiguity', 'none'),
                   adjudication=adjudicated.get(by_map[i]['review_id']),
                   semantic_gold=int(review['verdict'] == 'violation') if eligible else None,
                   label_basis=('distinct_agent_caveat_adjudication_source_agreement'
                                if by_map[i]['review_id'] in adjudicated else 'single_agent_source_agreement')
                                if eligible else None,
                   candidate_eligible=i in candidates, review_eligible=eligible, inference_eligible=False,
                   exclusion_reasons=sorted(reasons[i]), resolution_version=VERSION)
        resolved.append(row)
        dispositions.append({'id': i, 'review_id': row['review_id'],
                             'review_verdict': review['verdict'], 'upstream_label': original['upstream_label'],
                             'review_eligible': eligible, 'semantic_gold': row['semantic_gold'],
                             'direct_exclusion_reasons': sorted(direct[i]),
                             'exclusion_reasons': row['exclusion_reasons']})
    summary = {'version': VERSION, 'input_rows': len(rows),
               'candidate_eligible_rows_before_caveat_gate': len(candidates),
               'caveat_adjudication_rows': len(caveats),
               'adjudication_completed': adjudications is not None,
               'review_eligible_rows': sum(r['review_eligible'] for r in resolved),
               'quarantined_rows': sum(not r['review_eligible'] for r in resolved),
               'id_corrections': len(fixes), 'original_groups': len(old_groups),
               'final_groups_all_rows': len(groups), 'explicit_pairs': len(pairs),
               'proposal_decisions': dict(collections.Counter(r['action'] for r in resolutions)),
               'blinded_link_dispositions': dict(collections.Counter(r['disposition'] for r in link_records)),
               'direct_exclusions': dict(collections.Counter(s for v in direct.values() for s in v)),
               'all_exclusion_reasons_nonexclusive': dict(collections.Counter(s for v in reasons.values() for s in v)),
               'source_counts': {}, 'new_model_calls': 0, 'new_inference_spend_usd': 0,
               'unresolved_review_actions': len(caveats) if adjudications is None else 0,
               'review_resolution_complete': adjudications is not None or not caveats,
               'inference_ready': False,
               'remaining_execution_gates': ['native route access and full-input coverage',
                   'tested runner/accounting/statistics', 'current prices and shared ledger reconciliation',
                   'exact request/cohort/code freeze before inference'],
               'limitations': policy['limitations']}
    for source in sorted({r['source'] for r in rows}):
        part = [r for r in resolved if r['source'] == source]
        eligible = [r for r in part if r['review_eligible']]
        summary['source_counts'][source] = {'prepared': len(part),
            'candidate_eligible_before_caveat_gate': sum(r['candidate_eligible'] for r in part),
            'review_eligible': len(eligible),
            'quarantined': len(part)-len(eligible), 'labels': dict(collections.Counter(r['reviewed_verdict'] for r in eligible)),
            'splits': {s: {'rows': sum(r['split_proposal'] == s for r in eligible),
                'groups': len({r['group'] for r in eligible if r['split_proposal'] == s})}
                for s in ('development', 'confirmation')}}
    return {'resolved': resolved, 'dispositions': dispositions, 'id-corrections': fixes,
            'groups': sorted(groups, key=lambda r: r['group']), 'group-resolutions': resolutions,
            'link-resolutions': link_records}, summary


def load_inputs():
    review_dir = RAW / 'reviews'
    prep = json.loads((OUT / 'preparation.json').read_text())
    paths = {'prepared': RAW / 'prepared.jsonl', 'mapping': RAW / 'review-mapping.jsonl',
             'packet': RAW / 'review-packet.jsonl', 'reviews': review_dir / 'reviewer-A.csv',
             'session': review_dir / 'reviewer-A-session.json', 'lock': review_dir / 'reviewer-A-lock.json',
             'group_records': review_dir / 'group-review.jsonl',
             'links': review_dir / 'group-review-blinded-links.jsonl',
             'discrepancies': review_dir / 'reviewer-A-discrepancies.jsonl',
             'edges': RAW / 'group-edges.jsonl', 'policy': POLICY,
             'exposure': RAW / 'historical-exposure-hits.jsonl',
             'exposure_receipt': OUT / 'exposure.json', 'token_audit': RAW / 'laya-token-audit.jsonl',
             'token_receipt': OUT / 'token-audit.json', 'prompts': ROOT / 'scripts/study_v5/prompts.py'}
    hashes = {k: sha256(p.read_bytes()) for k, p in paths.items()}
    for key, receipt_key in [('prepared', 'prepared_sha256'), ('mapping', 'mapping_sha256'),
                             ('packet', 'review_packet_sha256')]:
        if hashes[key] != prep[receipt_key]:
            raise ValueError('Historical preparation changed: ' + key)
    lock = json.loads(paths['lock'].read_text())
    for key, receipt_key in [('packet', 'packet_sha256'), ('reviews', 'reviews_sha256'), ('session', 'session_sha256')]:
        if hashes[key] != lock[receipt_key]:
            raise ValueError('Review lock mismatch: ' + key)
    packet = read(paths['packet'])
    with paths['reviews'].open(newline='') as handle:
        reviews = list(csv.DictReader(handle))
    session = json.loads(paths['session'].read_text())
    validate_complete(packet, reviews, session)
    for key, raw_key, hash_key in [('exposure_receipt', 'exposure', 'hits_sha256'),
                                  ('token_receipt', 'token_audit', 'audit_sha256')]:
        receipt = json.loads(paths[key].read_text())
        if hashes[raw_key] != receipt[hash_key]:
            raise ValueError('Cached audit changed')
    exposure = json.loads(paths['exposure_receipt'].read_text())
    for receipt in exposure['historical_receipts']:
        if sha256((ROOT / receipt['path']).read_bytes()) != receipt['sha256']:
            raise ValueError('Historical exposure collection changed')
    args = dict(rows=read(paths['prepared']), mapping=read(paths['mapping']), packet=packet,
                reviews=reviews, group_records=read(paths['group_records']), links=read(paths['links']),
                edges=read(paths['edges']), policy=json.loads(POLICY.read_text()),
                exposure_ids={r['id'] for r in read(paths['exposure'])})
    receipts = {k: {'path': str(p.relative_to(ROOT)), 'sha256': hashes[k]} for k, p in paths.items()}
    return args, receipts, session


def load_adjudication(inputs, primary_session):
    folder = RAW / 'adjudication-v1'
    paths = {k: folder / name for k, name in {
        'adjudication_packet': 'packet.jsonl', 'adjudication_manifest': 'manifest.json',
        'adjudication_reviews': 'reviewer-B.csv', 'adjudication_session': 'reviewer-B-session.json',
        'adjudication_lock': 'reviewer-B-lock.json'}.items()}
    hashes = {k: sha256(p.read_bytes()) for k, p in paths.items()}
    lock = json.loads(paths['adjudication_lock'].read_text())
    for key, field in [('adjudication_packet', 'packet_sha256'), ('adjudication_reviews', 'reviews_sha256'),
                       ('adjudication_session', 'session_sha256')]:
        if hashes[key] != lock[field]: raise ValueError('Adjudication lock mismatch')
    manifest = json.loads(paths['adjudication_manifest'].read_text())
    if hashes['adjudication_packet'] != manifest['packet_sha256']:
        raise ValueError('Adjudication packet differs from selection receipt')
    if sha256((RAW / 'reviews/reviewer-A.csv').read_bytes()) != manifest['reviewer_A_sha256']:
        raise ValueError('Adjudication selected from different primary review')
    if sha256((RAW / 'review-resolution-v1/resolved.jsonl').read_bytes()) != manifest['candidate_resolution_sha256']:
        raise ValueError('Preserved candidate selection snapshot changed')
    packet = read(paths['adjudication_packet'])
    with paths['adjudication_reviews'].open(newline='') as handle:
        reviews = list(csv.DictReader(handle))
    session = json.loads(paths['adjudication_session'].read_text())
    validate_complete(packet, reviews, session)
    if any(session[k] == primary_session[k] for k in ('reviewer_id', 'session_identifier')):
        raise ValueError('Adjudicator must be a distinct reviewer session')
    original = unique(inputs['packet'], 'review_id')
    primary = unique(inputs['reviews'], 'review_id')
    for row in packet:
        if any(row[k] != original[row['review_id']][k] for k in ('candidate', 'task', 'policy', 'setting', 'review_target')):
            raise ValueError('Adjudication evidence differs from original')
        if any(v != primary[row['review_id']][k] for k, v in row['prior_agent_judgment'].items()):
            raise ValueError('Adjudication prior judgment differs from locked A')
    receipts = {k: {'path': str(p.relative_to(ROOT)), 'sha256': hashes[k]} for k, p in paths.items()}
    return reviews, receipts, session


def main():
    global VERSION
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true', help='Recompute and compare without writing')
    parser.add_argument('--with-adjudication', action='store_true', help='Require full distinct B lock; write separate v3 final resolution')
    args = parser.parse_args()
    inputs, receipts, session = load_inputs()
    dest, receipt_name = DEST, 'resolution.json'
    adjudicator = None
    if args.with_adjudication:
        judgments, extra_receipts, adjudicator = load_adjudication(inputs, session)
        inputs['adjudications'] = judgments
        receipts.update(extra_receipts)
        VERSION, dest, receipt_name = 'v6-review-resolution-3', RAW / 'review-resolution-v3', 'resolution-final.json'
    outputs, summary = resolve(**inputs)
    # Cross-check the coordinator's independently derived disputes against the locked handoff.
    disputed = {r['review_id'] for r in outputs['dispositions'] if any(
        reason in ('label:unclear', 'label:not_applicable', 'label:source_disagreement')
        for reason in r['direct_exclusion_reasons'])}
    supplied = read(RAW / 'reviews/reviewer-A-discrepancies.jsonl')
    if len(supplied) != len(disputed) or {r['review_id'] for r in supplied} != disputed:
        raise ValueError('Discrepancy ledger differs from independently recomputed exclusions')
    summary.update(inputs=receipts, reviewer={'reviewer_id': session['reviewer_id'],
        'model_version': session['model_version'], 'session_identifier': session['session_identifier']})
    if adjudicator:
        summary['adjudicator'] = {k: adjudicator[k] for k in ('reviewer_id', 'model_version', 'session_identifier')}
    summary['outputs'] = {}
    for name, rows in outputs.items():
        path = dest / (name + '.jsonl')
        body = b''.join(canonical_bytes(r) + b'\n' for r in rows)
        if args.verify:
            if path.read_bytes() != body:
                raise ValueError('Resolved output mismatch: ' + name)
        else:
            preserve_write(path, body)
        summary['outputs'][name] = {'path': str(path.relative_to(ROOT)), 'sha256': sha256(body), 'rows': len(rows)}
    body = json.dumps(summary, indent=2, sort_keys=True).encode() + b'\n'
    path = RESULTS / receipt_name
    if args.verify:
        if path.read_bytes() != body:
            raise ValueError('Aggregate resolution receipt mismatch')
    else:
        preserve_write(path, body, raw=False)
    print(json.dumps({k: summary[k] for k in ('review_eligible_rows', 'quarantined_rows', 'id_corrections',
        'source_counts', 'review_resolution_complete', 'inference_ready')}))


if __name__ == '__main__':
    main()
