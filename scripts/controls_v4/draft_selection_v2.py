"""Keep the published override-wrapper family entirely in fresh confirmation."""
import json
from collections import Counter
from audit_sources import ROOT, OUT, sha
from overlap_audit import read
from draft_selection import rank, SEED


def main():
    raw=ROOT/'data/raw/controls-v4'
    attacks=read(raw/'tasktracker-advbench-reconstructed-v1.jsonl')
    clean=read(raw/'tasktracker-clean-reconstructed-v1.jsonl')
    by_question={r['question_id']:r for r in clean}
    articles=sorted({r['article_title'] for r in clean},key=rank)
    dev_articles=set(articles[:8])
    selected=[]
    for article in articles[:8]:
        pool=sorted([r for r in clean if r['article_title']==article and 80<=len(r['candidate'])<=16000],key=lambda r:rank(r['published_prompt_hash']))
        for r in pool[:6]:
            selected.append(dict(r,split='development',source_construction_target=0,attack_family='none',selection_status='draft_not_frozen'))
    used_questions=set();used_goals=set()
    for article in articles[8:]:
        count=0
        pool=sorted([r for r in attacks if r['article_title']==article],key=lambda r:rank(r['published_prompt_hash']))
        for r in pool:
            c=by_question.get(r['question_id'])
            if not c or c['candidate_sha256']!=r['original_document_sha256'] or c['trusted_task']!=r['trusted_task']:continue
            if r['question_id'] in used_questions or r['attack_prompt_sha256'] in used_goals:continue
            if not all(80<=len(x['candidate'])<=16000 for x in [r,c]):continue
            used_questions.add(r['question_id']);used_goals.add(r['attack_prompt_sha256'])
            for label,row in [(0,c),(1,r)]:
                selected.append(dict(row,split='confirmation',source_construction_target=label,
                    attack_family='TaskTracker-published-override-wrappers' if label else 'none',selection_status='draft_not_frozen'))
            count+=1
            if count==8:break
    # Reuse only the previous designated development partition; never prior evaluation outcomes as fresh confirmation.
    reused=[]
    for r in read(ROOT/'data/expanded-v2/collection.jsonl'):
        if r['split']=='dev':
            reused.append({'id':r['id'],'source_collection':'data/expanded-v2/collection.jsonl','candidate_sha256':r['candidate_sha256'],
                           'groups':r['groups'],'split':'development','exposure_status':'previous_development_reused','construction_target':r['gold']})
    assert len(reused)==60
    assert not ({r['article_title'] for r in selected if r['split']=='development'} & {r['article_title'] for r in selected if r['split']=='confirmation'})
    (OUT/'draft-selection-v2.jsonl').write_text(''.join(json.dumps({k:v for k,v in r.items() if k not in ('candidate','trusted_task','original_document')},sort_keys=True)+'\n' for r in selected))
    (OUT/'reused-development-v2.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in reused))
    (raw/'draft-selection-v2.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in selected))
    counts={}
    for split in ('development','confirmation'):
        rows=[r for r in selected if r['split']==split]
        counts[split]={'new_task_content_pairs':len(rows),'new_questions':len({r['question_id'] for r in rows}),
                       'new_articles':len({r['article_title'] for r in rows}),'class_counts':dict(Counter(r['source_construction_target'] for r in rows))}
    report={'status':'draft_not_frozen_or_approved','seed':SEED,'counts':counts,'reused_development_pairs':len(reused),
            'wrapper_family_split':'Entire new published override-wrapper family kept in confirmation; new QA development is clean only, with old designated BIPIA development retained separately.',
            'remaining':'Near-duplicate grouping/independent validation, source-label eligibility, multi-domain benign pathway, precision, exact requests and cost freeze. No inference.',
            'model_requests':0}
    (OUT/'draft-selection-summary-v2.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report))


if __name__=='__main__':main()
