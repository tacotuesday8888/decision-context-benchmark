"""Distinguish texts, source documents, tasks, wrappers and clusters from calls."""
import json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'
def main():
    rows=[json.loads(s) for s in (OUT/'collection-manifest-v1.jsonl').read_text().splitlines()]
    report={}
    for split in ['development','confirmation']:
        part=[r for r in rows if r['split']==split];sources={}
        for source in sorted({r['dataset'] for r in part}):
            selected=[r for r in part if r['dataset']==source]
            counts={'task_content_pairs':len(selected),'distinct_candidate_texts':len({r['candidate_sha256'] for r in selected}),
                'label_counts':dict(Counter(r['gold'] for r in selected)),'label_basis_counts':dict(Counter(r['gold_basis'] for r in selected)),
                'independently_reviewed_semantic_labels':sum(r.get('semantic_label') is not None for r in selected)}
            for key in ['task','document','article','wrapper','attack_goal','attack_family','primary_cluster','secondary_cluster']:
                counts['distinct_'+key]=len({r['groups'].get(key) for r in selected}-{None,'none'})
            primary=Counter(r['groups']['primary_cluster'] for r in selected)
            counts['rows_per_primary_cluster']={'min':min(primary.values()),'max':max(primary.values())}
            sources[source]=counts
        report[split]=sources
    result={'by_split_and_source':report,'planned_calls':{'development':372,'confirmation':13175},
        'limits':'Group counts are descriptive, not an effective sample-size or independence proof. QA broad attack family is fixed; AIB families are community fixture categories, not independent real-world sources.'}
    (OUT/'coverage-v1.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
