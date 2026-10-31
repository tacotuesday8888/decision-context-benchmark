"""Audit lexical overlap with all four frozen project collections, without inference."""
import collections
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.common import (
    ROOT, RAW, OUT, read, write_rows, report, norm, near_links, sha256,
)

HISTORICAL = ['data/raw/pilot.jsonl', 'data/expanded-v2/collection.jsonl',
              'data/raw/extension-v3/prepared-collection-v1.jsonl',
              'data/raw/controls-v4/prepared-collection-v1.jsonl']

def main():
    old, receipts = [], []
    for name in HISTORICAL:
        path = ROOT / name
        for row in read(path):
            old.append({'id': name + ':' + row['id'], 'candidate': row['candidate'],
                        'task': row.get('trusted_task') or ''})
        receipts.append({'path': name, 'sha256': sha256(path.read_bytes())})
    new = read(RAW / 'prepared.jsonl')
    hits = collections.defaultdict(list)
    for axis in ['candidate', 'task']:
        seen = collections.defaultdict(list)
        for row in old:
            if norm(row[axis]):
                seen[norm(row[axis])].append(row['id'])
        for row in new:
            if norm(row.get(axis)) in seen:
                hits[row['id']].append({'axis': axis, 'match': 'normalized_exact',
                                        'historical_ids': seen[norm(row.get(axis))]})
    combined = old + new
    for j, i, score in near_links([r['candidate'] for r in combined], .5):
        if j < len(old) <= i:
            hits[combined[i]['id']].append({'axis': 'candidate', 'match': 'jaccard_ge_0.5',
                                           'jaccard': score, 'historical_ids': [combined[j]['id']]})
    write_rows(RAW / 'historical-exposure-hits.jsonl', [{'id': key, 'hits': value} for key, value in sorted(hits.items())])
    result = {'historical_receipts': receipts, 'historical_rows_including_repeats': len(old),
              'new_rows': len(new), 'flagged_rows': len(hits),
              'flagged_by_source': dict(collections.Counter(r['source'] for r in new if r['id'] in hits)),
              'hits_sha256': sha256((RAW / 'historical-exposure-hits.jsonl').read_bytes()),
              'limitations': 'Project lexical exposure only; semantic overlap and closed-model pretraining remain unresolved'}
    report(OUT / 'exposure.json', result)
    print(json.dumps(result))

if __name__ == '__main__':
    main()
