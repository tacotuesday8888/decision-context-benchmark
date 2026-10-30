"""Extract unchanged published candidates; labels inherit source construction only."""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from source_audit import content, normalize, sha

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / 'data/raw/extension-v3'
OUT = ROOT / 'results/extension-v3'
CONTENT_TOOLS = {
    'browse_webpage', 'get_webpage', 'read_file', 'get_received_emails',
    'get_unread_emails', 'get_shopping_linked_unread_emails',
    'get_shopping_linked_received_emails', 'get_github_linked_unread_emails',
    'get_day_calendar_events',
}


def jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def make_row(source, domain, candidate, task, gold, groups, provenance):
    identity = sha(json.dumps([source, candidate, task], ensure_ascii=False))
    return {'id': source + ':' + identity[:24], 'dataset': source + '-' + domain,
        'candidate': candidate, 'trusted_task': task, 'gold': gold,
        'gold_basis': 'published intended injection construction' if gold else 'published clean/default fixture with no injected payload',
        'candidate_sha256': sha(candidate), 'task_sha256': sha(task),
        'normalized_sha256': sha(normalize(candidate)), 'groups': groups,
        'source': provenance, 'license': 'MIT', 'split': 'confirmation',
        'conditions': ['candidate', 'task'], 'surrounding_before': None, 'surrounding_after': None}


def candidates():
    # Sample 16 published base attacks per original task, cycling all 62 instructions.
    # The selection is independent of model scores and attack success.
    inventory = jsonl(OUT / 'injecagent-inventory.jsonl')
    by_task = defaultdict(list)
    for record in inventory:
        by_task[record['task_sha256']].append(record)
    for task_index, (_, items) in enumerate(sorted(by_task.items())):
        items.sort(key=lambda r: r['attack_instruction_sha256'])
        chosen = [items[(task_index * 16 + i) % len(items)] for i in range(16)]
        for record in chosen:
            path = RAW / 'InjecAgent' / record['path']
            if sha(path.read_bytes()) != record['file_sha256']:
                raise ValueError('InjecAgent source changed')
            item = json.loads(path.read_text())[record['row_index']]
            yield make_row('injecagent', record['stratum'], item['Tool Response'], item['User Instruction'], 1,
                {'task': 'injecagent:' + record['task_sha256'],
                 'document': 'injecagent:' + record['document_template_sha256'],
                 'attack_family': 'injecagent:' + record['attack_instruction_sha256']}, record)

    # First *verified matching* injected response in each historical trace, not a
    # claim of first encounter or a counterfactual agent execution experiment.
    seen_attacked_traces = set()
    for record in jsonl(OUT / 'agentdyn-inventory.jsonl'):
        if record['tool_function'] not in CONTENT_TOOLS:
            continue
        if record['attack_family']:
            if record['path'] in seen_attacked_traces:
                continue
            seen_attacked_traces.add(record['path'])
        path = RAW / 'AgentDyn' / record['path']
        if sha(path.read_bytes()) != record['file_sha256']:
            raise ValueError('AgentDyn source changed')
        trace = json.loads(path.read_text())
        candidate = content(trace['messages'][record['message_index']])
        task = next(content(m) for m in trace['messages'] if m['role'] == 'user')
        yield make_row('agentdyn', record['suite'], candidate, task, int(bool(record['attack_family'])),
            {'task': 'agentdyn:' + record['task_group'], 'document': 'candidate:' + record['normalized_sha256'],
             'attack_family': 'agentdyn:important_instructions' if record['attack_family'] else 'none',
             'attack_goal': 'agentdyn:' + record['suite'] + ':' + str(record['injection_task_id'])}, record)

    replay_path = RAW / 'agentdojo-clean-replay.jsonl'
    receipt = json.loads((OUT / 'agentdojo-clean-replay.json').read_text())
    if sha(replay_path.read_bytes()) != receipt['raw_output_sha256']:
        raise ValueError('Clean replay differs from preserved receipt')
    for index, record in enumerate(jsonl(replay_path)):
        if not record['function'].startswith(('get_', 'search_', 'read_', 'list_')):
            continue
        provenance = {k: v for k, v in record.items() if k not in ('candidate', 'trusted_task', 'arguments')}
        provenance.update(path='agentdojo-clean-replay.jsonl', file_sha256=receipt['raw_output_sha256'], row_index=index)
        yield make_row('agentdojo-clean', record['task'].split(':')[0], record['candidate'], record['trusted_task'], 0,
            {'task': 'agentdojo:' + record['task'], 'document': 'candidate:' + sha(normalize(record['candidate'])),
             'attack_family': 'none'}, provenance)


def prepare():
    old = jsonl(ROOT / 'data/expanded-v2/collection.jsonl') + jsonl(ROOT / 'data/pilot.jsonl')
    old_text = {sha(normalize(r.get('candidate', r.get('text', '')))) for r in old}
    rows, excluded, seen = [], [], {}
    for row in candidates():
        reason = None
        if not isinstance(row['trusted_task'], str) or not row['trusted_task'].strip():
            reason = 'missing_original_task'
        elif not 80 <= len(row['candidate']) <= 16000:
            reason = 'content_length_outside_80_16000_characters'
        elif row['normalized_sha256'] in old_text:
            reason = 'previous_study_candidate_overlap'
        elif re.search(r'(?i)(?:password|OTP|api_key)\s*[:=]\s*\S+|ssh-(?:rsa|ed25519)\s+[A-Za-z0-9+/]+', row['candidate']):
            reason = 'published_credential_like_fixture_omitted'
        pair = (row['normalized_sha256'], row['task_sha256'])
        if pair in seen:
            if seen[pair]['gold'] != row['gold']:
                raise ValueError('Contradictory inherited labels for same task/text')
            reason = 'duplicate_task_candidate_pair'
        if reason:
            excluded.append({'id': row['id'], 'source': row['source'], 'reason': reason})
        else:
            seen[pair] = row
            rows.append(row)
    rows.sort(key=lambda r: r['id'])
    strata = []
    for name in sorted({r['dataset'] for r in rows}):
        part = [r for r in rows if r['dataset'] == name]
        strata.append({'dataset': name, 'task_candidate_pairs': len(part),
            'distinct_candidates': len({r['normalized_sha256'] for r in part}),
            'task_groups': len({r['groups']['task'] for r in part}),
            'label_counts': dict(Counter(r['gold'] for r in part))})
    metadata = [{k: v for k, v in row.items() if k not in ('candidate', 'trusted_task')} for row in rows]
    raw = ''.join(json.dumps(row, sort_keys=True, ensure_ascii=False) + '\n' for row in rows)
    (RAW / 'prepared-collection-v1.jsonl').write_text(raw)
    (OUT / 'collection-manifest-v1.jsonl').write_text(''.join(json.dumps(row, sort_keys=True) + '\n' for row in metadata))
    (OUT / 'collection-exclusions-v1.json').write_text(json.dumps(excluded, sort_keys=True, indent=2) + '\n')
    summary = {'version': 'extension-collection-v1', 'status': 'prepared_pending_final_validation',
        'task_candidate_pairs': len(rows), 'distinct_candidate_bytes': len({r['candidate_sha256'] for r in rows}),
        'distinct_normalized_candidates': len({r['normalized_sha256'] for r in rows}),
        'distinct_task_groups': len({r['groups']['task'] for r in rows}),
        'strata': strata, 'exclusions': dict(Counter(r['reason'] for r in excluded)),
        'collection_sha256': sha(raw), 'model_requests': 0,
        'partition': 'All newly sourced rows are confirmation-only; prior dev is retained separately.',
        'label_contract': 'Source construction labels inherited deterministically, not new AI semantic labels or attack-success labels.'}
    (OUT / 'collection-summary-v1.json').write_text(json.dumps(summary, sort_keys=True, indent=2) + '\n')
    return summary


if __name__ == '__main__':
    print(json.dumps(prepare(), indent=2))
