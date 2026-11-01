"""Offline provenance inventory. Does not infer gold labels or run upstream code."""
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REVISION = '5353cf7615b135cace8d07c8f12dac53a16b6db3'
PIPELINE = 'gpt-4o-mini-2024-07-18'


def sha(value):
    return hashlib.sha256(value.encode() if isinstance(value, str) else value).hexdigest()


def content(message):
    blocks = message.get('content')
    if isinstance(blocks, str):
        return blocks
    if not isinstance(blocks, list) or any(b.get('type') != 'text' for b in blocks):
        return None
    return '\n'.join(b['content'] for b in blocks)


def normalize(text):
    # Matching only: preserved candidate text is NEVER normalized or reconstructed.
    return re.sub(r'\s+', ' ', text).strip()


def inspect_trace(record, relative_path, file_sha):
    task = record.get('user_task_id', '')
    if not re.fullmatch(r'user_task_\d+', task):
        return [], 'attacker_goal_or_unknown_task'
    messages = record.get('messages', [])
    users = [content(m) for m in messages if m.get('role') == 'user']
    if len(users) != 1 or not users[0]:
        return [], 'ambiguous_user_context'
    injections = record.get('injections', {})
    attack = record.get('attack_type')
    if attack not in (None, 'important_instructions'):
        return [], 'unreviewed_attack_family'
    if bool(attack) != bool(injections):
        return [], 'inconsistent_attack_metadata'
    payloads = [normalize(v) for v in injections.values() if isinstance(v, str) and v.strip()]
    rows = []
    for index, message in enumerate(messages):
        if message.get('role') != 'tool' or message.get('error'):
            continue
        candidate = content(message)
        if not candidate:
            continue
        matched = [sha(p) for p in payloads if p in normalize(candidate)]
        # Nonmatching responses on attacked trajectories may be downstream effects;
        # never relabel them benign. Baseline responses are candidates, not gold yet.
        if attack and not matched:
            continue
        rows.append({
            'source': 'AgentDyn', 'revision': REVISION, 'pipeline': PIPELINE,
            'path': relative_path, 'file_sha256': file_sha, 'message_index': index,
            'suite': record['suite_name'], 'task_id': task,
            'task_group': record['suite_name'] + ':' + task,
            'task_sha256': sha(users[0]), 'candidate_sha256': sha(candidate),
            'normalized_sha256': sha(normalize(candidate)),
            'candidate_characters': len(candidate),
            'tool_function': (message.get('tool_call') or {}).get('function'),
            'attack_family': attack, 'injection_task_id': record.get('injection_task_id'),
            'matched_payload_hashes': matched,
            'label_evidence': 'published_injection_present' if matched else 'published_no_attack_trace',
            'gold': None, 'eligibility': 'pending_semantic_and_license_review',
            'benchmark_version': record.get('benchmark_version'),
        })
    return rows, None if rows else 'no_eligible_tool_message'


def audit(source):
    revision = subprocess.check_output(['git', '-C', str(source), 'rev-parse', 'HEAD'], text=True).strip()
    if revision != REVISION:
        raise ValueError('Upstream revision differs from reviewed source')
    rows, exclusions, traces = [], Counter(), Counter()
    for path in sorted((source / 'runs' / PIPELINE).rglob('*.json')):
        raw = path.read_bytes()
        record = json.loads(raw)
        extracted, reason = inspect_trace(record, str(path.relative_to(source)), sha(raw))
        traces[record.get('suite_name', 'unknown')] += 1
        rows.extend(extracted)
        if reason:
            exclusions[reason] += 1
    tasks = {r['task_group'] for r in rows}
    task_texts = {}
    for r in rows:
        task_texts.setdefault(r['task_group'], set()).add(r['task_sha256'])
    parent = {task: task for task in tasks}

    def find(task):
        while parent[task] != task:
            parent[task] = parent[parent[task]]
            task = parent[task]
        return task

    seen = {}
    for row in rows:
        digest, task = row['normalized_sha256'], row['task_group']
        if digest in seen:
            parent[find(task)] = find(seen[digest])
        else:
            seen[digest] = task
    summary = {
        'source_url': 'https://github.com/leolee99/AgentDyn', 'revision': revision,
        'pipeline': PIPELINE, 'license_sha256': sha((source / 'LICENSE').read_bytes()),
        'trace_files_by_domain': dict(traces), 'excluded_traces': dict(exclusions),
        'tool_message_occurrences': len(rows),
        'distinct_candidate_bytes': len({r['candidate_sha256'] for r in rows}),
        'distinct_task_candidate_pairs': len({(r['task_sha256'], r['candidate_sha256']) for r in rows}),
        'distinct_task_ids': len(tasks),
        'task_components_linked_by_identical_candidates': sorted(Counter(find(t) for t in tasks).values(), reverse=True),
        'tasks_with_multiple_recorded_wordings': sum(len(v) > 1 for v in task_texts.values()),
        'evidence_counts': dict(Counter(r['label_evidence'] for r in rows)),
        'approved_evaluation_examples': 0,
        'model_requests': 0,
        'limitations': [
            'Published benchmark fixtures, not naturally occurring production traffic.',
            'One attack template; repeated goals/tasks/traces are correlated.',
            'Task IDs are not statistically independent: shared documents link tasks.',
            'No-attack does not by itself establish a semantic negative label.',
            'Actual trace user wording is authoritative; task IDs alone do not align wording.',
            'Attacked messages match payload after whitespace normalization only.',
            'No train/evaluation split or gold labels assigned by this inventory.',
        ],
    }
    return rows, summary


if __name__ == '__main__':
    rows, summary = audit(ROOT / 'data/raw/extension-v3/AgentDyn')
    out = ROOT / 'results/extension-v3'
    out.mkdir(parents=True, exist_ok=True)
    (out / 'agentdyn-inventory.jsonl').write_text(''.join(json.dumps(r, sort_keys=True) + '\n' for r in rows))
    (out / 'agentdyn-audit.json').write_text(json.dumps(summary, indent=2, sort_keys=True) + '\n')
    print(json.dumps(summary, indent=2))
