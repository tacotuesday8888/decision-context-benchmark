"""Tokenize every native Laya payload without a model forward pass."""
import json
from pathlib import Path
from plan import jobs, read, request, preserved

ROOT = Path(__file__).resolve().parents[2]


def main():
    rows = read(ROOT / 'data/raw/controls-v4/prepared-collection-v1.jsonl')
    lookup = {r['id']: r for r in rows}
    runtime = preserved.LocalDecision()
    records = []
    for job in jobs(rows):
        if job['config'] != 'laya_local':
            continue
        payload = request(job['config'], lookup[job['id']], job['condition'])
        audit = runtime.audit(payload)
        records.append(dict(job, request_sha256=preserved.sha(preserved.canonical(payload)), **audit))
    out = ROOT / 'results/controls-v4'
    (out / 'token-audit-v1.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in records))
    summary = {'audited_payloads': len(records), 'model_forward_passes': 0,
        'max_input_tokens': max(r['input_tokens'] for r in records),
        'max_head_tokens': max(r['head_tokens'] for r in records),
        'truncated_payloads': sum(bool(r['truncated']) for r in records),
        'state_tokens_dropped': sum(r['state_tokens_dropped'] for r in records),
        'checkpoint': preserved.PANEL['laya_local'],
        'scope': 'All prepared Laya payloads (development and confirmation); other routes retain runtime coverage checks.'}
    (out / 'token-audit-summary-v1.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
