"""Read public metadata/data as inert bytes; no inference or third-party code execution."""
import hashlib,json,urllib.request
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RAW=ROOT/'data/raw/source-discovery'
OUT=ROOT/'results/source-discovery'

def sha(b):return hashlib.sha256(b).hexdigest()
def fetch(url,name):
    request=urllib.request.Request(url,headers={'User-Agent':'DecisionContextBenchmark-source-audit'})
    with urllib.request.urlopen(request,timeout=45) as response:body=response.read()
    (RAW/name).write_bytes(body)
    return body,{'url':url,'bytes':len(body),'sha256':sha(body),'local_cache':str((RAW/name).relative_to(ROOT))}
def lines(b):return [json.loads(x) for x in b.decode().splitlines() if x.strip()]
def main():
    RAW.mkdir(parents=True,exist_ok=True);OUT.mkdir(parents=True,exist_ok=True)
    rows=[];receipts=[]
    for repo,filename in [('nvidia/Nemotron-RL-Agentic-Indirect-Prompt-Injection-v1','train.jsonl'),('ScaleAI/aspi',None)]:
        slug=repo.split('/')[1]
        body,receipt=fetch('https://huggingface.co/api/datasets/'+repo,slug+'-metadata.json');receipts.append(receipt);meta=json.loads(body);revision=meta['sha']
        body,receipt=fetch('https://huggingface.co/datasets/'+repo+'/resolve/'+revision+'/README.md',slug+'-README.md');receipts.append(receipt)
        paths=[filename] if filename else ['data/banking.jsonl','data/slack.jsonl','data/travel.jsonl','data/workspace.jsonl']
        records=[]
        for path in paths:
            b,r=fetch('https://huggingface.co/datasets/'+repo+'/resolve/'+revision+'/'+path,slug+'-'+path.replace('/','-'));receipts.append(r);records.extend(lines(b))
        row={'id':repo,'revision':revision,'rows_counted':len(records),'schema_keys':sorted(records[0]),'license_declared':meta.get('cardData',{}).get('license'),'inspected':'Pinned README and all released JSONL rows parsed as data','source_url':'https://huggingface.co/datasets/'+repo}
        if filename:
            row.update(domains=dict(Counter(x['domain'] for x in records)),attack_categories=dict(Counter(x['attack_category'] for x in records)),distinct_injection_texts=len({sha(x['injection']['injection_text'].encode()) for x in records}),has_explicit_task_and_attack=all(x['responses_create_params']['input'] and x['injection']['injection_text'] for x in records),limitation='Synthetic successful-attack-selected training data; full policy/tool context must be preserved. Not a balanced clean/attack semantic-label set.')
        else:
            row.update(distinct_agentdojo_tasks=len({(x['suite'],x['user_task_id']) for x in records}),injection_variants=sum(len(x['injections']) for x in records),suites=dict(Counter(x['suite'] for x in records)),limitation='Clarification-channel task/attack pairs reuse exposed AgentDojo tasks. Not fresh independent task count; published generator/human-validation claims need validation details.')
        rows.append(row)
    repo='ppradyoth/AgentInjectionBench'
    b,r=fetch('https://api.github.com/repos/'+repo+'/commits/HEAD','aib-commit.json');receipts.append(r);revision=json.loads(b)['sha']
    b,r=fetch('https://raw.githubusercontent.com/'+repo+'/'+revision+'/data/agent_injection_bench.jsonl','aib-cases.jsonl');receipts.append(r);records=lines(b)
    b,r=fetch('https://raw.githubusercontent.com/'+repo+'/'+revision+'/LICENSE','aib-LICENSE');receipts.append(r)
    rows.append({'id':repo,'revision':revision,'source_url':'https://github.com/'+repo,'rows_counted':len(records),'schema_keys':sorted(records[0]),'inspected':'Pinned GitHub JSONL actual rows and license bytes','category_counts':dict(Counter(x['attack_category'] for x in records)),'label_counts':dict(Counter(x['ground_truth'] for x in records)),'limitation':'Public synthetic fixtures; reference assistant messages and gold labels must not leak into detector inputs. System policy belongs in trusted context. Separate repository from Sentinel Den 24-case source already used in v4.','license_file_sha256':sha(b)})
    repo='EliasHossain/nexus-ipi'
    b,r=fetch('https://huggingface.co/api/datasets/'+repo,'nexus-metadata.json');receipts.append(r);revision=json.loads(b)['sha']
    b,r=fetch('https://huggingface.co/datasets/'+repo+'/resolve/'+revision+'/README.md','nexus-README.md');receipts.append(r)
    versions={}
    for version in ['v1','v2']:
        b,r=fetch('https://huggingface.co/datasets/'+repo+'/resolve/'+revision+'/ipi_'+version+'.jsonl','nexus-'+version+'.jsonl');receipts.append(r);records=lines(b)
        pairs={}
        for record in records:pairs.setdefault(record['control_pair_id'],[]).append(record)
        complete=[pair for pair in pairs.values() if len(pair)==2]
        versions[version]={'rows_counted':len(records),'pairs_counted':len(pairs),'two_record_pairs':len(complete),'label_counts':dict(Counter(str(x['safety_label']) for x in records)),'identical_request_pairs':sum(p[0]['request']==p[1]['request'] for p in complete),'identical_full_plan_steps_pairs':sum(p[0]['structured_plan']['steps']==p[1]['structured_plan']['steps'] for p in complete),'identical_first_plan_step_pairs':sum(p[0]['structured_plan']['steps'][:1]==p[1]['structured_plan']['steps'][:1] for p in complete),'distinct_requests':len({x['request'] for x in records}),'schema_keys':sorted(records[0])}
    rows.append({'id':repo,'revision':revision,'source_url':'https://huggingface.co/datasets/'+repo,'license_declared':'cc-by-4.0','inspected':'Pinned README and both full JSONL versions parsed; pair invariants checked','versions':versions,'limitation':'Deterministic synthetic templates, not observed agent behavior or independent human gold. Check actual full-plan differences before accepting the card claim that only history differs. Versions may reuse tasks; do not add versions as independent scenarios.'})
    repo='judydnguyen/infuse'
    b,r=fetch('https://api.github.com/repos/'+repo+'/commits/HEAD','infuse-commit.json');receipts.append(r);revision=json.loads(b)['sha']
    b,r=fetch('https://api.github.com/repos/'+repo+'/git/trees/'+revision+'?recursive=1','infuse-tree.json');receipts.append(r);tree=json.loads(b)
    if tree.get('truncated'):raise ValueError('Incomplete INFUSE tree')
    paths=[x['path'] for x in tree['tree'] if x['type']=='blob']
    for path in ['README.md','LICENSE','benchmark/tasks/task_1/instruction.md','benchmark/tasks/task_1/environment/overlays/benign.toml','benchmark/tasks/task_1/tests/test.sh','benchmark/attacks/attack_1/config.toml']:
        b,r=fetch('https://raw.githubusercontent.com/'+repo+'/'+revision+'/'+path,'infuse-'+path.replace('/','-'));receipts.append(r)
    rows.append({'id':repo,'revision':revision,'source_url':'https://github.com/'+repo,'inspected':'Complete pinned repository tree plus README/license and task-1 instruction, benign surface config, hidden-test script, attack-1 config read as inert bytes; no code or Docker executed','task_instruction_files_counted':sum(p.startswith('benchmark/tasks/task_') and p.endswith('/instruction.md') for p in paths),'attack_config_files_counted':sum(p.startswith('benchmark/attacks/attack_') and p.endswith('/config.toml') for p in paths),'limitation':'Full trace availability and replay validity not established; indexed HF public-subset card was readable through search, but live HF connector returned dataset not found. Paper headline trajectories are not an independently verified downloadable row count. Needs isolated sandbox and task/attack verifier audit before prevention runs.'})
    result={'as_of':'2026-10-30','no_model_requests':True,'no_generated_examples':True,'records':rows,'receipts':receipts}
    (OUT/'priority-source-inspection.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'sources':[{k:v for k,v in r.items() if k not in ['schema_keys']} for r in rows],'receipt_count':len(receipts)}))
if __name__=='__main__':main()
