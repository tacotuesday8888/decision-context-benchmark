"""Audit complete new requests using the existing local Laya tokenizer; no forward pass."""
import collections
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import (
    ROOT, RAW, OUT, read, write_rows, report, canonical_bytes, sha256,
)
from scripts.study_v5.prompts import conditions, native_payload
sys.path.insert(0, str(ROOT / 'scripts/laya_v2'))
from adapter import LocalDecision, CONFIG

def coverage(runtime, payload):
    # The execution adapter correctly raises on over-limit states. Preparation
    # records them instead, without ever passing the clipped sequence to inference.
    from laya.common import build_sequence, build_head
    internal = runtime.agent._to_internal(payload['questions']['injection'])
    head, _, _ = build_head(runtime.agent.tok, internal, CONFIG['head_max_len'])
    full_head, _, _ = build_head(runtime.agent.tok, internal, 4096)
    if head != full_head:
        raise ValueError('Question/options would be clipped')
    ids, markers, stats = build_sequence(runtime.agent.tok, payload['state'], internal,
        max_len=CONFIG['context_tokens'], head_max_len=CONFIG['head_max_len'], return_truncation_stats=True)
    if len(markers) != 2:
        raise ValueError('Native decision markers changed')
    return {**stats, 'input_tokens': len(ids), 'head_tokens': len(head),
            'input_ids_sha256': sha256(json.dumps(ids).encode()),
            'coverage_status': 'unsupported_over_limit' if stats['truncated'] else 'complete'}

def main():
    runtime = LocalDecision()
    rows = read(RAW / 'prepared.jsonl')
    records = []
    for row in rows:
        for condition in conditions(row):
            payload = native_payload(row, condition, 'laya_local')
            records.append({'id': row['id'], 'source': row['source'], 'condition': condition,
                            'payload_sha256': sha256(canonical_bytes(payload)), **coverage(runtime, payload)})
    write_rows(RAW / 'laya-token-audit.jsonl', records)
    output = {'audited_payloads': len(records), 'model_forward_passes': 0,
              'max_input_tokens': max(r['input_tokens'] for r in records),
              'max_head_tokens': max(r['head_tokens'] for r in records),
              'max_unclipped_state_tokens': max(r['state_tokens'] for r in records),
              'truncated_payloads': sum(bool(r['truncated']) for r in records),
              'affected_rows': len({r['id'] for r in records if r['truncated']}),
              'affected_rows_by_source': dict(collections.Counter(source for _, source in
                  {(r['id'], r['source']) for r in records if r['truncated']})),
              'audit_sha256': sha256((RAW / 'laya-token-audit.jsonl').read_bytes()),
              'scope': 'Pinned local Laya sequence only; no certification of other route coverage'}
    report(OUT / 'token-audit.json', output)
    print(json.dumps(output))

if __name__ == '__main__':
    main()
