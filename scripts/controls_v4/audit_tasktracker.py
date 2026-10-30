"""Reconstruct an existing published subset and verify hashes; never generate examples."""
import json
from collections import Counter
from pathlib import Path
import subprocess
from audit_sources import ROOT, OUT, sha

REVISION = 'b4fabe25504dc1d3f7c6fdf5e50d4bb209a152b0'


def paragraphs(data):
    result = []
    for article in data['data']:
        for paragraph in article['paragraphs']:
            questions = [q for q in paragraph['qas'] if q['answers']]
            if questions:
                result.append((article['title'], paragraph['context'], questions))
    return result


def reconstruct(record, source_paragraphs, secondary_prompts):
    title, text, questions = source_paragraphs[record['text_idx']]
    question = questions[record['primary_task_index']]
    attack = secondary_prompts[record['secondary_task_index']]
    embedded = record['trigger'] + ' ' + attack
    pos = record['pos']
    if pos == 0:
        candidate = embedded + ' ' + text
    elif pos == -1:
        candidate = text + ' ' + embedded
    else:
        assert 0 <= pos <= len(text)
        candidate = ' '.join((text[:pos], embedded, text[pos:]))
    prompt = record['sep_prompt'] + ' ' + question['question'] + ' ' + candidate + ' '
    assert sha(''.join(prompt.split())) == record['final_prompt_hash'], 'Published prompt hash mismatch'
    return title, text, question, candidate, attack


def main():
    raw = ROOT / 'data/raw/controls-v4'
    source = raw / 'TaskTracker'
    assert subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip() == REVISION
    indices_path = source / 'task_tracker/dataset_creation/recreate_dataset/poisoned_test_indices.json'
    squad_path, code_path = raw/'squad-dev-v2.0.json', raw/'code-alpaca-20k.json'
    pars = paragraphs(json.loads(squad_path.read_text()))
    secondary = [r['instruction'] + '.' for r in json.loads(code_path.read_text()) if r['input'] == '']
    index_file_hash = sha(indices_path.read_bytes())
    records, prepared = [], []
    for i, r in enumerate(json.loads(indices_path.read_text())):
        if (r['text_data_src'],r['secondary_task_type'],r['primary_task_type']) != ('SQuAD','code_alpaca','qa'):
            continue
        assert r['split'] == 'dev'
        title, original, question, candidate, attack = reconstruct(r, pars, secondary)
        item = {'source':'TaskTracker', 'revision':REVISION, 'index_file':str(indices_path.relative_to(source)),
                'index_file_sha256':index_file_hash, 'row_index':i,
                'published_prompt_hash':r['final_prompt_hash'],
                'candidate_sha256':sha(candidate), 'task_sha256':sha(question['question']),
                'original_document_sha256':sha(original), 'article_title':title,
                'question_id':question['id'], 'trigger_sha256':sha(r['trigger']),
                'secondary_prompt_sha256':sha(attack), 'position':r['pos_label'],
                'construction_label':'published_poisoned_task_diversion', 'semantic_label':None,
                'eligibility':'pending_component_license_semantics_and_split_review',
                'hash_semantics':'Publisher SHA256 removes all whitespace; not a byte-identical source-text guarantee',
                'source_data_provenance':'Published synthetic attack using generated trigger/code instruction and original crowdworker QA context'}
        records.append(item)
        prepared.append(dict(item,candidate=candidate,trusted_task=question['question'],original_document=original))
    (OUT/'tasktracker-inventory-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in records))
    (raw/'tasktracker-reconstructed-v1.jsonl').write_text(''.join(json.dumps(r,sort_keys=True)+'\n' for r in prepared))
    receipt = {'source_revision':REVISION,'published_rows_verified':len(records),
               'distinct_candidates':len({r['candidate_sha256'] for r in records}),
               'distinct_questions':len({r['question_id'] for r in records}),
               'distinct_original_paragraphs':len({r['original_document_sha256'] for r in records}),
               'distinct_articles':len({r['article_title'] for r in records}),
               'distinct_triggers':len({r['trigger_sha256'] for r in records}),
               'distinct_secondary_prompts':len({r['secondary_prompt_sha256'] for r in records}),
               'positions':dict(Counter(r['position'] for r in records)),
               'source_files_sha256':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in [indices_path,squad_path,code_path]},
               'component_licenses':{'TaskTracker':'MIT','SQuAD':'CC-BY-SA-4.0','CodeAlpaca-data':'CC-BY-NC-4.0'},
               'redistribution_status':'Component review pending; reconstructed text kept ignored, no hosted inference',
               'model_requests':0,'approved_examples':0}
    (OUT/'tasktracker-audit-v1.json').write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in receipt.items() if k.startswith('distinct') or k=='published_rows_verified'}))


if __name__ == '__main__':
    main()
