"""Prepare source-construction evaluation rows; never assign independent semantic gold."""
import json
from collections import Counter
from audit_sources import ROOT, OUT, sha
from overlap_audit import read

RAW=ROOT/'data/raw/controls-v4'


def main():
    draft=read(RAW/'draft-selection-v2.jsonl')
    attack_by_question={r['question_id']:r for r in draft if r['source_construction_target']==1}
    rows=[]
    for r in draft:
        positive=attack_by_question.get(r['question_id'])
        wrapper=positive['trigger_sha256'] if positive else 'none'
        source={k:v for k,v in r.items() if k not in ('candidate','trusted_task','original_document','split','selection_status')}
        rows.append({'id':'tasktracker:'+sha(r['index_file']+':'+str(r['row_index']))[:24],
            'dataset':'tasktracker-qa-advbench','split':r['split'],'candidate':r['candidate'],'trusted_task':r['trusted_task'],
            'gold':r['source_construction_target'],'gold_basis':r['construction_label'],'semantic_label':None,
            'source':source,'license':'CC-BY-SA-4.0 with MIT source components; see THIRD-PARTY-NOTICES.md',
            'groups':{'task':'tasktracker-question:'+r['question_id'],
                'document':'squad-paragraph:'+r.get('original_document_sha256',r['candidate_sha256']),
                'article':'squad-article:'+r['article_title'],
                'attack_family':r['attack_family'], 'wrapper':wrapper,
                'attack_goal':r.get('attack_prompt_sha256','none'),
                'primary_cluster':'squad-article:'+r['article_title'],
                'secondary_cluster':'matched-wrapper:'+wrapper if positive else 'clean-dev:'+r['candidate_sha256']},
            'sampling_note':'Clean/attack matched by original published question and paragraph; clean gets its matched design wrapper cluster for uncertainty, not an injected-content label.'})
    for r in read(RAW/'aib-prepared-v1.jsonl'):
        rows.append({'id':'aib:'+r['source_id'],'dataset':'aib-static-stress','split':'confirmation',
            'candidate':r['candidate'],'trusted_task':r['trusted_task'],'gold':r['source_construction_target'],
            'gold_basis':r['construction_label'],'semantic_label':None,
            'source':{k:v for k,v in r.items() if k not in ('candidate','trusted_task')},'license':'MIT',
            'groups':{'task':'aib-task:'+r['task_sha256'],'document':'aib-content:'+r['candidate_sha256'],
                'attack_family':'aib:'+r['family'],'primary_cluster':'aib-task:'+r['task_sha256'],
                'secondary_cluster':'aib-family:'+r['family']},
            'sampling_note':'Complete eligible static fixture subset; no custom system context/history or direct-user baseline.'})
    for r in read(ROOT/'data/expanded-v2/collection.jsonl'):
        if r['split']!='dev':continue
        row=dict(r,split='development',semantic_label=None,source_exposure='previous_designated_development')
        row['groups']=dict(r['groups'],primary_cluster=r['groups']['document'],secondary_cluster=r['groups']['document'])
        rows.append(row)
    for r in rows:
        r['conditions']=['candidate','task','format','reminder','scrambled']
        r['candidate_sha256']=sha(r['candidate']);r['task_sha256']=sha(r['trusted_task'])
        r['surrounding_before']=r['surrounding_after']=None
    rows.sort(key=lambda r:r['id'])
    assert len({r['id'] for r in rows})==len(rows)
    full=''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in rows)
    (RAW/'prepared-collection-v1.jsonl').write_text(full)
    manifest=[{k:v for k,v in r.items() if k not in ('candidate','trusted_task')} for r in rows]
    (OUT/'collection-manifest-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True,ensure_ascii=False)+'\n' for r in manifest))
    summary={'version':'controls-v4-preparation-draft','status':'pending_independent_validation_and_protocol',
             'collection_sha256':sha(full),'rows':len(rows),'counts':{},'model_requests':0,
             'label_scope':'Published intended injection vs source clean/control construction, not new semantic annotations or attack success.'}
    for split in ('development','confirmation'):
        part=[r for r in rows if r['split']==split]
        summary['counts'][split]={'task_content_pairs':len(part),'distinct_texts':len({r['candidate_sha256'] for r in part}),
            'task_groups':len({r['groups'].get('task',r['task_sha256']) for r in part}),
            'primary_clusters':len({r['groups']['primary_cluster'] for r in part}),
            'by_source':dict(Counter(r['dataset'] for r in part)), 'classes':dict(Counter(r['gold'] for r in part))}
    (OUT/'collection-summary-v1.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print(json.dumps(summary))


if __name__=='__main__':main()
