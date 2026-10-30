"""Read-only source/exposure inventory. Does not generate examples or assign gold."""
import hashlib
import json
from collections import Counter
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / 'results/controls-v4'
TAU_REV = '59a200c6d575d595120f1cb70fea53cef0632f6b'


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, indent=2, sort_keys=True) + '\n')


def exposure():
    rows = []
    files = ['data/pilot.jsonl', 'data/expanded-v2/collection.jsonl',
             'results/extension-v3/collection-manifest-v1.jsonl']
    for name in files:
        for r in map(json.loads, (ROOT / name).read_text().splitlines()):
            task_hash = r.get('task_sha256')
            if not task_hash and r.get('trusted_task'):
                task_hash = sha(r['trusted_task'])
            rows.append({'collection': name, 'id': r['id'], 'split': r['split'],
                         'candidate_sha256': r['candidate_sha256'], 'task_sha256': task_hash,
                         'groups': r.get('groups', {'legacy_group': str(r.get('group'))}),
                         'source': r.get('source', {'scenario': r.get('source_scenario'),
                                                   'team': r.get('source_team')})})
    # Includes all earlier dev/evaluation membership, not merely successful predictions.
    (OUT / 'exposure-register-v1.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))
    return {'files_sha256': {n: sha((ROOT / n).read_bytes()) for n in files},
            'rows': len(rows), 'distinct_text_hashes': len({r['candidate_sha256'] for r in rows}),
            'distinct_task_hashes': len({r['task_sha256'] for r in rows if r['task_sha256']}),
            'scope': 'All prior prepared dev/evaluation rows; conservative exposure, not only successful calls. Group IDs are source-specific and require cross-source reconciliation. Inspection-only source inventory does not itself mean model exposure.'}, rows


def audit_tau(previous):
    base = ROOT / 'data/raw/controls-v4/tau-bench'
    revision = subprocess.check_output(['git', '-C', str(base), 'rev-parse', 'HEAD'], text=True).strip()
    assert revision == TAU_REV
    old_texts = {r['candidate_sha256'] for r in previous}
    inventory, reasons = [], Counter()
    source_hashes = {}
    for path in sorted((base / 'historical_trajectories').glob('*.json')):
        source_hashes[str(path.relative_to(base))] = sha(path.read_bytes())
        domain = 'airline' if 'airline' in path.name else 'retail'
        for record_index, trace in enumerate(json.loads(path.read_text())):
            users, calls = [], {}
            for mi, message in enumerate(trace['traj']):
                if message.get('role') == 'user':
                    if isinstance(message.get('content'), str):
                        users.append({'message_index': mi, 'text_sha256': sha(message['content'])})
                if message.get('role') == 'assistant':
                    for call in message.get('tool_calls') or []:
                        if call.get('id'):
                            calls[call['id']] = call
                if message.get('role') != 'tool':
                    continue
                candidate = message.get('content')
                if not isinstance(candidate, str) or not candidate.strip():
                    reasons['nontext_or_empty_tool_response'] += 1
                    continue
                call = calls.get(message.get('tool_call_id'))
                if not call or not users:
                    reasons['missing_call_or_prior_user_message'] += 1
                    continue
                function = call.get('function') or {}
                row = {'source': 'tau-bench', 'revision': revision,
                       'path': str(path.relative_to(base)), 'file_sha256': source_hashes[str(path.relative_to(base))],
                       'record_index': record_index, 'message_index': mi,
                       'task_group': f"tau-bench:{domain}:{trace['task_id']}", 'domain': domain,
                       'trial': trace['trial'], 'candidate_sha256': sha(candidate),
                       'candidate_characters': len(candidate), 'user_messages': list(users),
                       'tool_call_id': message['tool_call_id'], 'function': function.get('name'),
                       'arguments_sha256': sha(json.dumps(function.get('arguments'), sort_keys=True)),
                       'prior_exact_candidate_overlap': sha(candidate) in old_texts,
                       'construction_label': 'published_unattacked_trajectory',
                       'semantic_label': None, 'eligibility': 'pending_policy_content_group_review',
                       'task_context_basis': 'actual_preceding_user_messages_not_private_task_instruction'}
                inventory.append(row)
    (OUT / 'tau-trajectory-inventory-v1.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in inventory))
    return {'revision': revision, 'license': 'MIT', 'license_sha256': sha((base / 'LICENSE').read_bytes()),
            'source_files_sha256': source_hashes, 'candidate_occurrences': len(inventory),
            'distinct_texts': len({r['candidate_sha256'] for r in inventory}),
            'distinct_task_groups': len({r['task_group'] for r in inventory}),
            'domains': dict(Counter(r['domain'] for r in inventory)),
            'excluded_occurrences': dict(reasons), 'approved_examples': 0, 'model_requests': 0,
            'limitations': ['Repeated trials/backends are grouped by original task.',
                'Actual user-message history is available; private simulator instruction excluded.',
                'No-attack trajectory is construction provenance, not independently reviewed semantic gold.',
                'Multi-turn history needs an explicit task-context policy; no synthetic summary generated.',
                'Exact hashes alone do not establish document/template independence.']}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    summary, previous = exposure()
    write('exposure-summary-v1.json', summary)
    tau = audit_tau(previous)
    write('tau-trajectory-audit-v1.json', tau)
    print(json.dumps({'prior_exposure_rows': summary['rows'], 'tau_occurrences': tau['candidate_occurrences'],
                      'tau_texts': tau['distinct_texts'], 'tau_tasks': tau['distinct_task_groups'],
                      'approved_examples': 0, 'model_requests': 0}))


if __name__ == '__main__':
    main()
