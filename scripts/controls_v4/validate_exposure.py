"""Check selected fresh confirmation against all prior texts and new development."""
import json
import re
from audit_sources import ROOT, OUT, sha
from overlap_audit import read, overlaps


def main():
    raw=ROOT/'data/raw/controls-v4'
    rows=read(raw/'prepared-collection-v1.jsonl')
    confirmation=[r for r in rows if r['split']=='confirmation']
    development=[r for r in rows if r['split']=='development']
    previous=read(ROOT/'data/pilot.jsonl')+read(ROOT/'data/expanded-v2/collection.jsonl')+read(ROOT/'data/raw/extension-v3/prepared-collection-v1.jsonl')
    prior_text={r['id']:r['candidate'] for r in previous}
    new_text={r['id']:r['candidate'] for r in confirmation}
    prior_near=overlaps(new_text,prior_text)
    split_near=overlaps(new_text,{r['id']:r['candidate'] for r in development})
    prior_tasks={sha(r['trusted_task']) for r in previous if r.get('trusted_task')}
    task_overlap=[r['id'] for r in confirmation if r['task_sha256'] in prior_tasks or r['source'].get('question_sha256') in prior_tasks]
    normalize=lambda text:re.sub(r'\s+',' ',text).strip().casefold()
    indices=json.loads((raw/'TaskTracker/task_tracker/dataset_creation/recreate_dataset/poisoned_val_indices.json').read_text())
    trigger_matches=[]
    templates={indices[r['source']['row_index']]['trigger'] for r in confirmation if r['dataset']=='tasktracker-qa-advbench' and r['gold']==1}
    old_normalized={r['id']:normalize(r['candidate']) for r in previous}
    for template in templates:
        if not template.strip():continue
        for old_id,text in old_normalized.items():
            if normalize(template) in text:trigger_matches.append({'template_sha256':sha(template),'previous':old_id})
    assert not prior_near and not split_near and not task_overlap and not trigger_matches, 'Exposure/split overlap requires review before freeze'
    report={'status':'passed','prior_rows':len(previous),'confirmation_rows':len(confirmation),'new_development_rows':len(development),
        'prior_candidate_near_overlaps':prior_near,'development_confirmation_near_overlaps':split_near,
        'prior_exact_task_or_question_overlaps':task_overlap,'full_selected_wrapper_matches_in_previous_text':trigger_matches,
        'selected_wrapper_templates':len(templates),'threshold':.8,'definition':'5-word casefolded shingle Jaccard; complete normalized wrapper substring separately checked',
        'collection_sha256':sha((raw/'prepared-collection-v1.jsonl').read_bytes()),
        'limits':'Lexical checks do not prove semantic novelty or freedom from model pretraining exposure. Prior attack-goal lexical audit and named source-family split remain separate evidence.'}
    (OUT/'exposure-validation-v1.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n');print(json.dumps(report))


if __name__=='__main__':main()
