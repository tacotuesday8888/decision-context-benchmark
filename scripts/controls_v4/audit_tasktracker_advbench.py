"""Verify the published QA/AdvBench subset, without CodeAlpaca's NC component."""
import csv
import json
import subprocess
from audit_sources import ROOT, OUT, sha
from audit_tasktracker import paragraphs, reconstruct, REVISION


def main():
    raw=ROOT/'data/raw/controls-v4'
    source=raw/'TaskTracker'
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()==REVISION
    index_path=source/'task_tracker/dataset_creation/recreate_dataset/poisoned_val_indices.json'
    attack_path=raw/'advbench-harmful-behaviors.csv'
    attacks={sha(''.join(r['goal'].split())):r['goal'] for r in csv.DictReader(attack_path.open())}
    pars=paragraphs(json.loads((raw/'squad-dev-v2.0.json').read_text()))
    index_hash=sha(index_path.read_bytes())
    inventory, prepared=[],[]
    for i,r in enumerate(json.loads(index_path.read_text())):
        if r['primary_task_type']!='qa' or r['secondary_task_hash'] not in attacks:
            continue
        assert r['text_data_src']=='SQuAD' and r['split']=='dev'
        attack=attacks[r['secondary_task_hash']]
        lookup=dict(r,secondary_task_index=0)
        title,original,q,candidate,_=reconstruct(lookup,pars,[attack])
        row={'source':'TaskTracker-AdvBench','revision':REVISION,
             'index_file':str(index_path.relative_to(source)), 'index_file_sha256':index_hash,'row_index':i,
             'published_prompt_hash':r['final_prompt_hash'],'candidate_sha256':sha(candidate),
             'task_sha256':sha(q['question']),'question_id':q['id'],'article_title':title,
             'original_document_sha256':sha(original),'attack_prompt_sha256':sha(attack),
             'attack_normalized_sha256':r['secondary_task_hash'],'trigger_sha256':sha(r['trigger']),
             'position':r['pos_label'], 'construction_label':'published_poisoned_task_diversion',
             'semantic_label':None,'eligibility':'pending_overlap_policy_and_split_review',
             'component_licenses':{'TaskTracker':'MIT','AdvBench':'MIT','SQuAD':'CC-BY-SA-4.0'}}
        inventory.append(row);prepared.append(dict(row,candidate=candidate,trusted_task=q['question'],original_document=original))
    (OUT/'tasktracker-advbench-inventory-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in inventory))
    (raw/'tasktracker-advbench-reconstructed-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in prepared))
    receipt={'published_rows_verified':len(inventory),'distinct_candidates':len({r['candidate_sha256'] for r in inventory}),
             'distinct_questions':len({r['question_id'] for r in inventory}),
             'distinct_documents':len({r['original_document_sha256'] for r in inventory}),
             'distinct_articles':len({r['article_title'] for r in inventory}),
             'distinct_attack_prompts':len({r['attack_prompt_sha256'] for r in inventory}),
             'source_files_sha256':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [index_path,attack_path,raw/'advbench-LICENSE',raw/'squad-dev-v2.0.json']},
             'approved_examples':0,'model_requests':0,
             'label_scope':'Published injected construction, not observed success or newly assigned semantic gold. Exact publisher normalized hashes verified.'}
    (OUT/'tasktracker-advbench-audit-v1.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k.startswith('distinct') or k=='published_rows_verified'}))


if __name__=='__main__':
    main()
