"""Verify released clean QA records, preserving construction and semantic labels separately."""
import json
import hashlib
from audit_sources import ROOT, OUT, sha
from audit_tasktracker import paragraphs, REVISION


def main():
    raw = ROOT / 'data/raw/controls-v4'
    path = raw / 'TaskTracker/task_tracker/dataset_creation/recreate_dataset/clean_val_indices.json'
    pars = paragraphs(json.loads((raw/'squad-dev-v2.0.json').read_text()))
    file_hash = sha(path.read_bytes())
    rows, prepared = [], []
    cumulative = hashlib.sha256()
    for i,r in enumerate(json.loads(path.read_text())):
        if (r['text_data_src'],r['split'],r['primary_task_type']) != ('SQuAD','dev','qa'):
            break  # Only the initial contiguous QA prefix can be verified without later components.
        title, candidate, questions = pars[r['text_idx']]
        q = questions[r['primary_task_index']]
        prompt = r['sep_prompt']+' '+q['question']+' '+candidate+' '
        cumulative.update(prompt.encode())
        assert cumulative.hexdigest() == r['final_prompt_hash']
        row = {'source':'TaskTracker', 'revision':REVISION, 'index_file':str(path.relative_to(raw/'TaskTracker')),
               'index_file_sha256':file_hash, 'row_index':i,'candidate_sha256':sha(candidate),
               'task_sha256':sha(q['question']), 'question_id':q['id'], 'article_title':title,
               'published_prompt_hash':r['final_prompt_hash'], 'hash_semantics':'cumulative raw UTF-8 prompt prefix per published clean reconstruction code', 'construction_label':'published_clean_qa',
               'semantic_label':None,'eligibility':'pending_content_license_and_group_review'}
        rows.append(row);prepared.append(dict(row,candidate=candidate,trusted_task=q['question']))
    (OUT/'tasktracker-clean-inventory-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in rows))
    (raw/'tasktracker-clean-reconstructed-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in prepared))
    receipt={'published_clean_rows_verified':len(rows),'distinct_candidates':len({r['candidate_sha256'] for r in rows}),
             'distinct_questions':len({r['question_id'] for r in rows}), 'distinct_articles':len({r['article_title'] for r in rows}),
             'index_file_sha256':file_hash,'approved_examples':0,'model_requests':0,
             'scope':'Published clean validation QA subset; prior source split is not our experiment split. No semantic label newly assigned.'}
    (OUT/'tasktracker-clean-audit-v1.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps(receipt))


if __name__=='__main__':
    main()
