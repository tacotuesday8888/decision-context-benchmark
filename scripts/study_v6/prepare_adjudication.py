"""Prepare a bounded independent review of label-relevant reviewer-A caveats.

This does not decide whether an ambiguity is factual or label-relevant. A distinct
agent must inspect complete evidence. No upstream labels or source mappings exported.
"""
import csv
import io
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import RAW, ROOT, canonical_bytes, preserve_write, read, sha256


def main():
    dest = RAW / 'adjudication-v1'
    with (RAW / 'reviews/reviewer-A.csv').open(newline='') as handle:
        primary = {r['review_id']: r for r in csv.DictReader(handle)}
    resolved = read(RAW / 'review-resolution-v1/resolved.jsonl')
    packet = {r['review_id']: r for r in read(RAW / 'review-packet.jsonl')}
    selected = [r['review_id'] for r in resolved if r['review_eligible'] and primary[r['review_id']]['ambiguity'].strip().lower() != 'none']
    rows = [{**packet[rid], 'prior_agent_judgment': {k: primary[rid][k] for k in
        ('verdict', 'rationale', 'evidence_span', 'context_needed', 'task_relation', 'instruction_type', 'ambiguity')}} for rid in selected]
    body = b''.join(canonical_bytes(r)+b'\n' for r in rows)
    preserve_write(dest / 'packet.jsonl', body)
    fields = list(next(iter(primary.values()))) + ['limitations']
    chunks, chunk, size = [], [], 0
    for row in rows:
        n = len(canonical_bytes(row))+1
        if chunk and (len(chunk) >= 20 or size+n > 120000):
            chunks.append(chunk); chunk, size = [], 0
        chunk.append(row); size += n
    if chunk: chunks.append(chunk)
    batches = []
    for n, chunk in enumerate(chunks, 1):
        path = dest / 'batches' / f'batch-{n:03d}.jsonl'
        body = b''.join(canonical_bytes(r)+b'\n' for r in chunk)
        preserve_write(path, body)
        stream = io.StringIO(newline=''); writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader(); writer.writerows({'review_id': r['review_id']} for r in chunk)
        preserve_write(path.with_name(path.stem+'-blank.csv'), stream.getvalue().encode())
        batches.append({'batch': path.stem, 'rows': len(chunk), 'sha256': sha256(body)})
    manifest = {'kind': 'label_caveat_adjudication_packet_v1', 'rows': len(rows), 'batches': batches,
        'packet_sha256': sha256((dest/'packet.jsonl').read_bytes()),
        'reviewer_A_sha256': sha256((RAW/'reviews/reviewer-A.csv').read_bytes()),
        'candidate_resolution_sha256': sha256((RAW/'review-resolution-v1/resolved.jsonl').read_bytes()),
        'selection': 'Previously source-agreed, grouping-cleared rows with reviewer-A ambiguity != none. Other disputes and grouping exclusions remain excluded.',
        'not_blinded_to_reviewer_A': True, 'upstream_labels_exported': False,
        'status': 'Independent adjudication pending; previous resolution is a candidate pool, not final label admission.'}
    preserve_write(dest/'manifest.json', json.dumps(manifest,indent=2,sort_keys=True).encode()+b'\n')
    print(json.dumps({'rows': len(rows), 'batches': len(batches), 'packet_sha256': manifest['packet_sha256']}))


if __name__ == '__main__': main()
