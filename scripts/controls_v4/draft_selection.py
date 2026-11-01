"""Outcome-blind feasibility selection. Not a protocol freeze or inference approval."""
import json
from collections import defaultdict, Counter
from audit_sources import ROOT, OUT, sha
from overlap_audit import read, shingles

SEED='controls-v4-feasibility-20261030'


def rank(value):
    return sha(SEED+':'+value)


def main():
    raw=ROOT/'data/raw/controls-v4'
    attacks=read(raw/'tasktracker-advbench-reconstructed-v1.jsonl')
    clean=read(raw/'tasktracker-clean-reconstructed-v1.jsonl')
    clean_by_question={r['question_id']:r for r in clean}
    assert len(clean_by_question)==len(clean)
    # Match only already-published identical original QA/document pairs; do not generate clean counterparts.
    matched=[]
    for r in attacks:
        c=clean_by_question.get(r['question_id'])
        if c and c['candidate_sha256']==r['original_document_sha256'] and c['trusted_task']==r['trusted_task']:
            if 80 <= len(r['candidate']) <= 16000 and 80 <= len(c['candidate']) <= 16000:
                matched.append(r)
    import csv
    texts={sha(r['goal']):r['goal'] for r in csv.DictReader((raw/'advbench-harmful-behaviors.csv').open())}
    parent={h:h for h in texts}
    def find(h):
        while parent[h]!=h:
            parent[h]=parent[parent[h]];h=parent[h]
        return h
    hashes=sorted(texts)
    grams={h:shingles(texts[h]) for h in hashes}
    for i,h in enumerate(hashes):
        for k in hashes[:i]:
            a,b=grams[h],grams[k]
            if a and b and len(a&b)/len(a|b)>=.8:
                parent[find(h)]=find(k)
    members=defaultdict(list)
    for h in hashes: members[find(h)].append(h)
    components={h:min(v) for v in members.values() for h in v}
    articles=sorted({r['article_title'] for r in matched},key=rank)
    dev_articles=set(articles[:8])
    selected=[];used_goals=set();used_questions=set()
    for split in ('development','confirmation'):
        for article in articles:
            if (article in dev_articles)!=(split=='development'):continue
            quota=6 if split=='development' else 8
            count=0
            pool=sorted([r for r in matched if r['article_title']==article],key=lambda r:rank(r['published_prompt_hash']))
            for r in pool:
                component=components[r['attack_prompt_sha256']]
                if r['question_id'] in used_questions or component in used_goals: continue
                used_questions.add(r['question_id']);used_goals.add(component)
                c=clean_by_question[r['question_id']]
                for label,row in [(0,c),(1,r)]:
                    selected.append(dict(row,split=split,source_construction_target=label,
                        attack_group=component if label else None,
                        selection_status='feasibility_only_not_frozen'))
                count+=1
                if count==quota:break
    metadata=[{k:v for k,v in r.items() if k not in ('candidate','trusted_task','original_document')} for r in selected]
    (OUT/'draft-selection-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in metadata))
    (raw/'draft-selection-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in selected))
    summaries={}
    for split in ('development','confirmation'):
        rows=[r for r in selected if r['split']==split]
        summaries[split]={'task_content_pairs':len(rows),'distinct_texts':len({r['candidate_sha256'] for r in rows}),
                         'questions':len({r['question_id'] for r in rows}),'articles':len({r['article_title'] for r in rows}),
                         'documents':len({r.get('original_document_sha256',r['candidate_sha256']) for r in rows}),
                         'attack_goal_groups':len({r['attack_group'] for r in rows if r['attack_group']}),
                         'class_counts':dict(Counter(r['source_construction_target'] for r in rows))}
    triggers={split:{r['trigger_sha256'] for r in selected if r['split']==split and 'trigger_sha256' in r} for split in ('development','confirmation')}
    trigger_overlap=triggers['development'] & triggers['confirmation']
    report={'validation_status':'rejected_trigger_template_overlap_before_inference' if trigger_overlap else 'pending_full_validation',
            'cross_split_trigger_templates':len(trigger_overlap),'seed':SEED,'available_matched_attack_rows':len(matched),'available_matched_questions':len({r['question_id'] for r in matched}),
            'available_articles':len(articles),'counts':summaries,'model_requests':0,'status':'draft_feasibility_not_frozen',
            'limits':'Task counts are not independent article counts. Attack grouping uses exact/near lexical goals; broad harm-category or semantic-family separation is not established. One QA source; multi-domain coverage remains to resolve. No semantic judgments assigned.'}
    (OUT/'draft-selection-summary-v1.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report))


if __name__=='__main__':
    main()
