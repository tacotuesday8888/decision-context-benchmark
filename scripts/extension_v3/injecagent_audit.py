"""Inventory published base attacks; never synthesize a clean tool response."""
import json
from collections import Counter
from pathlib import Path
import subprocess
from source_audit import sha

ROOT = Path(__file__).resolve().parents[2]
REVISION = 'f19c9f2c79a41046eb13c03c51a24c567a8ffa07'


def audit():
    source = ROOT / 'data/raw/extension-v3/InjecAgent'
    if subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip() != REVISION:
        raise ValueError('Source revision mismatch')
    user_cases = [json.loads(line) for line in (source / 'data/user_cases.jsonl').read_text().splitlines()]
    known_tasks = {r['User Instruction'] for r in user_cases}
    rows = []
    for kind in ('dh', 'ds'):
        path = source / f'data/test_cases_{kind}_base.json'
        raw = path.read_bytes()
        for index, item in enumerate(json.loads(raw)):
            candidate, task = item['Tool Response'], item['User Instruction']
            if not isinstance(candidate, str) or task not in known_tasks:
                raise ValueError('Missing text or unknown original task')
            # Source prompted-agent evaluation interpolates this string directly.
            # Decode only for checking payload presence, never for presentation.
            try:
                decoded = json.loads(candidate)
            except json.JSONDecodeError:
                decoded = candidate
            if not isinstance(decoded, str) or item['Attacker Instruction'] not in decoded:
                raise ValueError('Published payload not recoverable from candidate')
            rows.append({'source': 'InjecAgent', 'revision': REVISION,
                'path': str(path.relative_to(source)), 'file_sha256': sha(raw), 'row_index': index,
                'candidate_sha256': sha(candidate), 'candidate_characters': len(candidate),
                'task_sha256': sha(task), 'document_template_sha256': sha(item['Tool Response Template']),
                'attack_instruction_sha256': sha(item['Attacker Instruction']),
                'attack_category': item['Attack Type'], 'stratum': kind,
                'user_tool': item['User Tool'], 'label_evidence': 'published_attack_construction',
                'eligible_conditions': ['candidate', 'task'], 'gold': None,
                'eligibility': 'pending_final_context_and_duplicate_review'})
    summary = {'source_url': 'https://github.com/uiuc-kang-lab/InjecAgent', 'revision': REVISION,
        'license': 'MIT', 'license_sha256': sha((source / 'LICENCE').read_bytes()),
        'base_cases': len(rows), 'distinct_candidates': len({r['candidate_sha256'] for r in rows}),
        'distinct_tasks': len({r['task_sha256'] for r in rows}),
        'distinct_document_templates': len({r['document_template_sha256'] for r in rows}),
        'distinct_attacker_instructions': len({r['attack_instruction_sha256'] for r in rows}),
        'strata': dict(Counter(r['stratum'] for r in rows)), 'model_requests': 0,
        'approved_evaluation_examples': 0,
        'limitations': ['All candidates are published intended attacks; no benign labels inferred.',
            'Enhanced settings excluded as repeated wrapper variants.',
            'Task and attacker-instruction axes are crossed, not independent rows.',
            'Exact published Tool Response string retained, including serialization quotes.',
            'No generated missing context, attacker-side simulated response, or original reasoning included.']}
    return rows, summary


if __name__ == '__main__':
    rows, summary = audit()
    out = ROOT / 'results/extension-v3'
    (out / 'injecagent-inventory.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))
    (out / 'injecagent-audit.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2))
