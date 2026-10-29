"""Development-first local Laya execution. Never calls a hosted model or reads API keys."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
import fcntl
import json
from pathlib import Path
import sys
import time

from adapter import ROOT, CONFIG, MODEL, REVISION, SDK, LocalDecision, request, parse, digest
sys.path.insert(0,str(ROOT/'scripts/expanded_execution'))
from execute import save, canonical, verify_preparation
from analyze import metrics
from common import DATA, jsonl, sha

OUT = ROOT/'results/laya-v2'
RECORDS = ROOT/'results/expanded-execution'
CONFIG_PATH = OUT/'execution-config.json'


def jobs(split):
    return [(row,condition) for row in jsonl(DATA/'collection.jsonl') if row['split']==split
            for condition in row['conditions']]


def provenance_files():
    files=[Path(__file__),Path(__file__).with_name('adapter.py'),ROOT/'requirements-laya.lock',
           CONFIG_PATH,OUT/'model-artifacts.json',DATA/'collection.jsonl',DATA/'prompts.json',
           ROOT/'scripts/laya_v2/download.py', ROOT/'scripts/expanded_execution/execute.py']
    return {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in files}


def freeze():
    verify_preparation()
    dev=list((RECORDS/'checks/laya_local').glob('*-0.json'))
    if len(dev)!=len(jobs('dev')):
        raise ValueError('Full development completion required before evaluation freeze')
    for path in dev:
        r=json.loads(path.read_text())
        if r['parsed']['status'] not in ('ok','tie') or r['token_audit']['truncated']:
            raise ValueError('Unresolved operational development failure')
    frozen={'version':'expanded-laya-v2.3','prior_freeze_sha256':sha((OUT/'execution-freeze.json').read_bytes()),'integration_amendment':'New provider caps and Nimble registration; Laya checkpoint/prompts/settings and dev responses unchanged','hashes':provenance_files(),
            'development_sha256':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(dev)},
            'evaluation_permitted_by_runner':True,'evaluation_cells':len(jobs('eval')),
            'note':'Local supplementary arm added after original evaluation began; not a blind original model selection. No Laya eval outcomes used.'}
    path=OUT/'execution-freeze-v2.3.json'
    if path.exists() and json.loads(path.read_text())!=frozen:
        raise ValueError('Frozen Laya settings changed; new version required')
    save(path,frozen)
    print(json.dumps({'frozen':True,'dev_cells':len(dev),'eval_cells':len(jobs('eval'))}))


def verify_freeze():
    frozen=json.loads((OUT/'execution-freeze-v2.3.json').read_text())
    if frozen['hashes']!=provenance_files():raise ValueError('Frozen code/config/data changed')
    for path,value in frozen['development_sha256'].items():
        if sha((ROOT/path).read_bytes())!=value:raise ValueError('Frozen development evidence changed')


def summarize(split):
    directory=RECORDS/('checks' if split=='dev' else 'evaluation')/'laya_local'
    records=[json.loads(p.read_text()) for p in directory.glob('*-0.json')]
    lookup={r['id']:r for r in jsonl(DATA/'collection.jsonl')}
    groups=defaultdict(list)
    for r in records:
        row=lookup[r['id']]
        groups[(row['dataset'],r['condition'])].append({'gold':row['gold'],**r['parsed']})
    summary={'split':split,'completed_cells':len(records),'planned_cells':len(jobs(split)),
             'distinct_candidates':len({r['id'] for r in records}),
             'status_counts':dict(Counter(r['parsed']['status'] for r in records)),
             'api_cost_usd':0,'elapsed_inference_seconds':sum(x['elapsed_seconds'] for x in records),'max_input_tokens':max((r.get('token_audit',{}).get('input_tokens',0) for r in records),default=0),
             'by_source_condition':[{'dataset':d,'condition':c,**metrics(rs)} for (d,c),rs in sorted(groups.items())]}
    save(OUT/(split+'-summary.json'),summary)
    print(json.dumps({k:v for k,v in summary.items() if k!='by_source_condition'}),flush=True)


def run(split):
    verify_preparation()
    config=json.loads(CONFIG_PATH.read_text())
    if config['configuration']!=CONFIG:raise ValueError('Configuration differs from adapter')
    if split=='eval':verify_freeze()
    OUT.mkdir(exist_ok=True)
    with (OUT/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        model=LocalDecision()
        # Token/format audit uses all planned inputs, never labels or predictions, and
        # is recorded separately from inference. No evaluation model forwards here.
        audits=[]
        for phase in ('dev','eval'):
            for row,condition in jobs(phase):
                audits.append({'id':row['id'],'split':phase,'condition':condition,
                               **model.audit(request(row,condition))})
        save(OUT/'token-audit.json',{'model':MODEL,'revision':REVISION,'records':audits,
             'parameter_count_loaded':model.parameter_count,'evaluation_inference_in_this_audit':False})
        directory=RECORDS/('checks' if split=='dev' else 'evaluation')/'laya_local'
        directory.mkdir(parents=True,exist_ok=True)
        if (directory/'STOP.json').exists():raise PermissionError('Preserved Laya failure requires review')
        for index,(row,condition) in enumerate(jobs(split)):
            payload=request(row,condition);key=sha('laya_local'+row['id']+condition)[:24]
            path=directory/(key+'-0.json')
            if path.exists():
                if json.loads(path.read_text())['request_sha256']!=sha(canonical(payload)):
                    raise ValueError('Saved request changed')
                continue
            started=datetime.now(timezone.utc).isoformat();start=time.perf_counter()
            try:
                raw,parsed,audit=model.predict(payload)
            except Exception as error:
                raw=None;parsed={'status':'local_runtime_error','valid':False,'prediction':None,
                                 'error_type':type(error).__name__};audit={}
            record={'version':'expanded-laya-v2.2','config':'laya_local',
                    'execution_config_sha256':sha(canonical(config)),'id':row['id'],'split':split,
                    'condition':condition,'attempt':0,'candidate_sha256':row['candidate_sha256'],
                    'request':payload,'request_sha256':sha(canonical(payload)),
                    'access_route':'local','paid_request':False,'reserved_usd':0,
                    'conservative_usage_cost_usd':0,'started_at':started,
                    'elapsed_seconds':round(time.perf_counter()-start,3),
                    'observation':{'http_status':None,'device':'cpu','backend':'eager'},
                    'raw_response':raw,'raw_body':None,'parsed':parsed,'token_audit':audit}
            save(path,record)
            if parsed['status'] not in ('ok','tie'):
                save(directory/'STOP.json',{'id':row['id'],'condition':condition,'status':parsed['status']})
                summarize(split);raise RuntimeError('Laya operational failure saved; no retries')
            if (index+1)%20==0:print(json.dumps({'split':split,'completed':index+1}),flush=True)
        summarize(split)


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['dev','eval','freeze','summary']);a=p.parse_args()
    if a.mode=='freeze':freeze()
    elif a.mode=='summary':summarize('dev')
    else:run(a.mode)

if __name__=='__main__':main()
