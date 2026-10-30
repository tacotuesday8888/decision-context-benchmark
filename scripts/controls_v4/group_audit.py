"""Quantify why occurrence/text counts cannot be used as independent task counts."""
from collections import defaultdict
import json
from pathlib import Path
from audit_sources import ROOT, OUT


def components(rows):
    parent = {r['task_group']: r['task_group'] for r in rows}
    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x
    by_text = defaultdict(set)
    for r in rows:
        by_text[r['candidate_sha256']].add(r['task_group'])
    for tasks in by_text.values():
        tasks = sorted(tasks)
        for task in tasks[1:]:
            parent[find(task)] = find(tasks[0])
    groups = defaultdict(list)
    for task in parent:
        groups[find(task)].append(task)
    return {'task_count': len(parent), 'text_count': len(by_text),
            'texts_shared_across_tasks': sum(len(v) > 1 for v in by_text.values()),
            'connected_component_sizes': sorted([len(v) for v in groups.values()], reverse=True),
            'groups': sorted([sorted(v) for v in groups.values()])}


def main():
    rows = [json.loads(s) for s in (OUT / 'tau-trajectory-inventory-v1.jsonl').read_text().splitlines()]
    summaries = {}
    for domain in ('airline', 'retail'):
        subset = [r for r in rows if r['domain'] == domain]
        summaries[domain + ':all_linked_tools'] = components(subset)
        reads = {'get_product_details', 'search_direct_flight', 'search_onestop_flight'}
        summaries[domain + ':catalog_or_flight_search_only'] = components([r for r in subset if r['function'] in reads])
    report = {'summary': summaries, 'scope': 'Exact candidate sharing only; not a complete semantic/template/entity overlap test. Components are diagnostics, not an approved split.',
              'model_requests': 0}
    (OUT / 'tau-group-audit-v1.json').write_text(json.dumps(report, indent=2, sort_keys=True) + '\n')
    print(json.dumps({k: {n: v[n] for n in ('task_count','text_count','texts_shared_across_tasks','connected_component_sizes')} for k,v in summaries.items()}))


if __name__ == '__main__':
    main()
