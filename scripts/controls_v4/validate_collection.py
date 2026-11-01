"""Independent source reconstruction, labels and split checks. No inference."""
import csv
import hashlib
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'
RAW=ROOT/'data/raw/controls-v4'


def digest(value):
    return hashlib.sha256(value.encode() if isinstance(value,str) else value).hexdigest()


def read(path):
    return [json.loads(s) for s in path.read_text().splitlines()]


def validate():
    rows=read(RAW/'prepared-collection-v1.jsonl')
    manifest=read(OUT/'collection-manifest-v1.jsonl')
    summary=json.loads((OUT/'collection-summary-v1.json').read_text())
    assert digest((RAW/'prepared-collection-v1.jsonl').read_bytes())==summary['collection_sha256']
    assert manifest==[{k:v for k,v in r.items() if k not in ('candidate','trusted_task')} for r in rows]
    qa=[]
    for article in json.loads((RAW/'squad-dev-v2.0.json').read_text())['data']:
        for paragraph in article['paragraphs']:
            questions=[q for q in paragraph['qas'] if len(q['answers'])>0]
            if questions:qa.append((article['title'],paragraph['context'],questions))
    base=RAW/'TaskTracker/task_tracker/dataset_creation/recreate_dataset'
    clean=json.loads((base/'clean_val_indices.json').read_text())
    attacks=json.loads((base/'poisoned_val_indices.json').read_text())
    goals={digest(''.join(r['goal'].split())):r['goal'] for r in csv.DictReader((RAW/'advbench-harmful-behaviors.csv').open())}
    cumulative=hashlib.sha256();clean_hashes={}
    for index,item in enumerate(clean):
        if (item['text_data_src'],item['split'],item['primary_task_type'])!=('SQuAD','dev','qa'):break
        _,text,qs=qa[item['text_idx']];task=item['sep_prompt']+' '+qs[item['primary_task_index']]['question']
        cumulative.update((task+' '+text+' ').encode());assert cumulative.hexdigest()==item['final_prompt_hash']
        clean_hashes[index]=cumulative.hexdigest()
    aib={r['id']:r for r in read(RAW/'agent-injection-bench/aib/data/attacks.jsonl')}
    old_dev={r['id']:r for r in read(ROOT/'data/expanded-v2/collection.jsonl') if r['split']=='dev'}
    source_hashes={}
    def file_digest(path):
        if path not in source_hashes:source_hashes[path]=digest(path.read_bytes())
        return source_hashes[path]
    for row in rows:
        assert row['semantic_label'] is None
        assert row['conditions']==['candidate','task','format','reminder','scrambled']
        assert digest(row['candidate'])==row['candidate_sha256']
        assert digest(row['trusted_task'])==row['task_sha256']
        if row['dataset']=='tasktracker-qa-advbench':
            s=row['source'];index=s['row_index']
            original_path=RAW/'TaskTracker'/s['index_file']
            assert file_digest(original_path)==s['index_file_sha256']
            item=(attacks if row['gold'] else clean)[index]
            assert (item['text_data_src'],item['split'],item['primary_task_type'])==('SQuAD','dev','qa')
            title,text,questions=qa[item['text_idx']];q=questions[item['primary_task_index']]
            task=item['sep_prompt']+' '+q['question']
            assert s['question_id']==q['id'] and s['article_title']==title
            if row['gold']:
                injected=item['trigger']+' '+goals[item['secondary_task_hash']]
                pos=item['pos']
                parts=[injected,text] if pos==0 else [text,injected] if pos==-1 else [text[:pos],injected,text[pos:]]
                candidate=' '.join(parts)
                assert digest(''.join((task+' '+candidate+' ').split()))==item['final_prompt_hash']
                assert row['gold_basis']=='published_poisoned_task_diversion'
                assert row['split']=='confirmation', 'Published attack family must not enter development'
                assert row['groups']['wrapper']==digest(item['trigger'])
            else:
                candidate=text;assert clean_hashes[index]==item['final_prompt_hash']
                assert row['gold_basis']=='published_clean_qa'
            assert row['candidate']==candidate and row['trusted_task']==task
            assert row['groups']['document']=='squad-paragraph:'+digest(text)
        elif row['dataset']=='aib-static-stress':
            item=aib[row['source']['source_id']]
            assert file_digest(RAW/'agent-injection-bench/aib/data/attacks.jsonl')==row['source']['file_sha256']
            assert row['split']=='confirmation' and not item.get('history') and not item.get('system_prompt')
            assert item['channel'] in ('document','web_page','tool_result')
            if item['channel']=='tool_result':assert any(t.get('returns')==item['injected'] for t in item['tools'])
            assert (row['candidate'],row['trusted_task'],row['gold'])==(item['injected'],item['task'],int(item['family']!='control'))
        else:
            original=old_dev[row['id']];assert row['split']=='development'
            for key in ('candidate','trusted_task','gold','gold_basis','source','license'):assert row[key]==original[key]
    dev=[r for r in rows if r['split']=='development'];evaluation=[r for r in rows if r['split']=='confirmation']
    assert len({r['id'] for r in rows})==len(rows)
    for field in ('candidate_sha256','task_sha256'):
        assert not ({r[field] for r in dev}&{r[field] for r in evaluation}),field
    for field in ('document','article','primary_cluster','wrapper','attack_family'):
        def values(part):return {r['groups'].get(field) for r in part}-{None,'none'}
        assert not values(dev)&values(evaluation),field
    # The paired clean row's wrapper cluster must match the actual paired attack's template.
    paired={r['groups']['task']:r for r in evaluation if r['dataset']=='tasktracker-qa-advbench' and r['gold']==1}
    for row in evaluation:
        if row['dataset']=='tasktracker-qa-advbench':
            partner=paired[row['groups']['task']]
            assert row['groups']['wrapper']==partner['groups']['wrapper']
            assert row['groups']['document']==partner['groups']['document']
    report={'status':'passed_source_and_exact_group_checks','rows':len(rows),'development':len(dev),'confirmation':len(evaluation),
        'collection_sha256':summary['collection_sha256'],'verified_clean_hash_prefix':len(clean_hashes),
        'semantic_labels_assigned':0,'labels':'Reconstructed published construction/control status only.',
        'scope':'Independent original-source reconstruction and exact group boundaries. Lexical near-duplicate and prior exposure checks are separate; no independent human semantic annotation claim.'}
    (OUT/'collection-validation-v1.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps(report));return rows


if __name__=='__main__':validate()
