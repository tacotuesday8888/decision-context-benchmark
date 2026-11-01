"""Lock complete blinded reviews without opening source mappings or labels."""
import argparse
import csv
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import read, preserve_write, canonical_bytes, sha256
from scripts.study_v5.reviews import validate

ENUMS = {'context_needed': {'yes', 'no', 'unclear'},
         'task_relation': {'related', 'unrelated', 'mixed', 'unclear', 'not_applicable'},
         'instruction_type': {'ordinary_data', 'legitimate_procedure', 'quoted_instruction',
             'authority_forgery', 'unauthorized_side_effect', 'answer_corruption',
             'task_replacement', 'policy_conflict', 'unclear'}}

def validate_complete(packet, reviews, session):
    ids = [r['review_id'] for r in packet]
    if len(set(ids)) != len(ids):
        raise ValueError('Duplicate packet IDs')
    index = {r['review_id']: r for r in packet}
    seen = set()
    for review in reviews:
        rid = review.get('review_id')
        if rid not in index or rid in seen:
            raise ValueError('Unknown or repeated review ID')
        seen.add(rid)
        validate(review, index[rid])
        for field, allowed in ENUMS.items():
            if review[field] not in allowed:
                raise ValueError('Invalid review category: ' + field)
        if review['reviewer_id'] != session['reviewer_id']:
            raise ValueError('Review/session identity mismatch')
        if review['reviewer_kind'] != 'agent':
            raise ValueError('This packet uses the owner-selected agent review workflow')
        merges = [s.strip() for s in review.get('group_merge_ids', '').split(';') if s.strip()]
        if any(s not in index for s in merges):
            raise ValueError('Unknown grouping reference')
    if seen != set(index):
        raise ValueError('Incomplete review: preserve a checkpoint, not a final lock')
    required = ['reviewer_id', 'model_version', 'session_identifier', 'blinding_declaration', 'limitations']
    if any(not isinstance(session.get(k), str) or not session[k].strip() for k in required):
        raise ValueError('Incomplete session provenance')
    if any(r['reviewer_model_version'] != session['model_version'] for r in reviews):
        raise ValueError('Model provenance mismatch')
    return True

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--packet', type=Path, required=True)
    p.add_argument('--reviews', type=Path, required=True)
    p.add_argument('--session', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    packet = read(a.packet)
    with a.reviews.open(newline='') as handle:
        reviews = list(csv.DictReader(handle))
    session = json.loads(a.session.read_text())
    validate_complete(packet, reviews, session)
    lock = {'kind': 'blinded-agent-review-lock-v1', 'rows': len(reviews),
            'packet_sha256': sha256(a.packet.read_bytes()), 'reviews_sha256': sha256(a.reviews.read_bytes()),
            'session_sha256': sha256(a.session.read_bytes()), 'reviewer_id': session['reviewer_id'],
            'model_version': session['model_version'],
            'label_admission': False, 'note': 'Lock integrity only; grouping/adjudication/exposure/freeze remain required'}
    preserve_write(a.out, canonical_bytes(lock) + b'\n')
    print(json.dumps(lock))

if __name__ == '__main__':
    main()
