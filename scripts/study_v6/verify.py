"""Offline tracked-receipt checks, optionally with exact ignored source/cache verification."""
import argparse
import collections
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import (
    ROOT, RAW, OUT, BROWSE_REV, NVIDIA_SHA, read, sha256,
)
from scripts.study_v6.prepare import nvidia_pair
from scripts.study_v5.prompts import conditions, evidence

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--require-cache', action='store_true')
    a = p.parse_args()
    prep = json.loads((OUT / 'preparation.json').read_text())
    acquisition = json.loads((OUT / 'browse-acquisition.json').read_text())
    assert acquisition['revision'] == BROWSE_REV
    assert acquisition['source_training_pages'] == 59000
    assert not acquisition['test_data_read'] and not acquisition['screenshot_columns_read']
    assert prep['prepared_rows'] == sum(prep['source_counts'].values())
    assert prep['prepared_rows'] == sum(b['rows'] for b in prep['review_batches'])
    assert prep['semantic_gold'] == prep['inference_eligible'] == prep['new_model_calls'] == 0
    assert prep['nvidia']['selected_rows'] == 400
    for name in ['DESIGN.md', 'REVIEW.md', 'REVIEW-GOAL.md', 'SOL-GOAL.md', 'HANDOFF.md', 'SOURCES.md', 'METHODS-COMPARISON.md']:
        assert (ROOT / 'docs/study-v6' / name).is_file(), name
    if a.require_cache:
        source_receipt = json.loads((OUT / 'source-implementation-audit.json').read_text())
        tree = json.loads((RAW / 'browsesafe-tree.json').read_text())
        blobs = {r['path']: r['sha'] for r in tree['tree'] if r['type'] == 'blob'}
        for entry in source_receipt['files']:
            body = (RAW / 'browsesafe' / entry['path']).read_bytes()
            assert sha256(body) == entry['sha256']
            assert hashlib.sha1(b'blob ' + str(len(body)).encode() + b'\0' + body).hexdigest() == blobs[entry['path']]
        assert sha256((RAW / 'browsesafe-license.md').read_bytes()) == source_receipt['dataset_license_sha256']
        for receipt in acquisition['receipts']:
            assert sha256((ROOT / receipt['path']).read_bytes()) == receipt['sha256'], receipt['path']
        for name, key in [('prepared.jsonl', 'prepared_sha256'), ('review-mapping.jsonl', 'mapping_sha256'), ('review-packet.jsonl', 'review_packet_sha256')]:
            assert sha256((RAW / name).read_bytes()) == prep[key], name
        rows, blind, mapping = read(RAW / 'prepared.jsonl'), read(RAW / 'review-packet.jsonl'), read(RAW / 'review-mapping.jsonl')
        assert len({r['id'] for r in rows}) == len(rows)
        assert len({r['review_id'] for r in blind}) == len(blind)
        by_review = {r['review_id']: r for r in mapping}
        for r in blind:
            assert set(r) == {'review_id', 'setting', 'task', 'policy', 'candidate', 'review_target'}
            assert all(r[k] == by_review[r['review_id']][k] for k in ['setting', 'task', 'policy', 'candidate'])
        chunks = []
        for b in prep['review_batches']:
            path = RAW / 'review-batches' / (b['batch'] + '.jsonl')
            assert sha256(path.read_bytes()) == b['packet_sha256']
            assert sha256((path.parent / (b['batch'] + '-blank.csv')).read_bytes()) == b['template_sha256']
            chunks.extend(read(path))
        assert chunks == blind
        groups = collections.defaultdict(set)
        pairs = collections.defaultdict(set)
        for r in rows:
            groups[r['group']].add(r['split_proposal'])
            pair = r.get('pair_id') or r['provenance'].get('pair_id')
            if pair:
                pairs[(r['source'], pair)].add(r['group'])
            assert r['semantic_gold'] is None and r['inference_eligible'] is False
            for condition in conditions(r):
                e = evidence(r, condition)
                key = 'USER_MESSAGE' if r['setting'] == 'system_policy_boundary' else 'CANDIDATE'
                assert e[key] == r['candidate']
        assert all(len(s) == 1 for s in groups.values())
        assert all(len(s) == 1 for s in pairs.values())
        source_path = ROOT / 'data/raw/source-discovery/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1-train.jsonl'
        assert sha256(source_path.read_bytes()) == NVIDIA_SHA
        nv_source = {str(r['id']): r for r in read(source_path)}
        nv_rows = {r['id']: r for r in rows if r['source'] == 'nvidia'}
        for r in nv_rows.values():
            rebuilt = {x['id']: x for x in nvidia_pair(nv_source[r['pair_id']])}[r['id']]
            assert all(r[k] == rebuilt[k] for k in ['task', 'policy', 'candidate', 'upstream_label', 'provenance'])
        browse_source = {r['entry_id']: r for r in read(RAW / 'browse-train-selected.jsonl')}
        for r in rows:
            if r['source'] == 'browsesafe':
                source = browse_source[r['provenance']['entry_id']]
                assert r['task'] == source['benign_task'] and r['candidate'] == source['content_markdown']
                assert r['policy'] is None and source['split'] == 'train'
        for receipt_name, raw_name, field in [('token-audit.json', 'laya-token-audit.jsonl', 'audit_sha256'),
                                             ('exposure.json', 'historical-exposure-hits.jsonl', 'hits_sha256')]:
            receipt = json.loads((OUT / receipt_name).read_text())
            assert sha256((RAW / raw_name).read_bytes()) == receipt[field]
    print(json.dumps({'verified': True, 'require_cache': a.require_cache,
                      'prepared_rows': prep['prepared_rows'], 'inference_ready': False}))

if __name__ == '__main__':
    main()
