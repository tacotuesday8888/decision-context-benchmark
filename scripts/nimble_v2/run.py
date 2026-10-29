"""Bounded dev checks now; explicit frozen local evaluation available for continuation."""
import argparse
from datetime import datetime,timezone
import fcntl
import json
from pathlib import Path
import sys
import time
from local import ROOT,CONFIG,MODEL,DIGEST,request,parse,call,verify_model
sys.path.insert(0,str(ROOT/'scripts/expanded_execution'))
from execute import save,canonical,verify_preparation
from common import DATA,sha,jsonl
from development import dev_rows

OUT=ROOT/'results/nimble-setup'
RECORDS=ROOT/'results/expanded-execution'


def selected_dev():
    rows=dev_rows()
    longest=max((r for r in jsonl(DATA/'collection.jsonl') if r['split']=='dev'),key=lambda r:len(r['candidate']))
    if longest['id'] not in {r['id'] for r in rows}:rows.append(longest)
    return [(r,c) for r in rows for c in r['conditions']]


def hashes():
    paths=[Path(__file__),Path(__file__).with_name('local.py'),OUT/'execution-config.json',DATA/'collection.jsonl',DATA/'prompts.json']
    return {str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in paths}


def freeze():
    paths=list((RECORDS/'checks/nimble_local').glob('*-0.json'))
    if len(paths)!=len(selected_dev()):raise ValueError('Development incomplete')
    records=[json.loads(p.read_text()) for p in paths]
    if any(r['parsed']['status'] not in ('ok','tie') for r in records):raise ValueError('Unresolved development failure')
    value={'version':'nimble-local-v2.3.1','prior_freeze_sha256':sha((OUT/'execution-freeze.json').read_bytes()),'amendment':'Preserve inference evidence even when post-request runtime metadata is unavailable; model, data and prompts unchanged','hashes':hashes(),'development_hashes':{str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(paths)},'evaluation_cells':812,'note':'Supplementary addition after original model evaluation; no Nimble evaluation outcomes used.'}
    p=OUT/'execution-freeze-v2.3.1.json'
    if p.exists() and json.loads(p.read_text())!=value:raise ValueError('Freeze changed; new version required')
    save(p,value)


def verify_freeze():
    d=json.loads((OUT/'execution-freeze-v2.3.1.json').read_text())
    if d['hashes']!=hashes():raise ValueError('Frozen Nimble settings changed')
    for path,digest in d['development_hashes'].items():
        if sha((ROOT/path).read_bytes())!=digest:raise ValueError('Nimble development evidence changed')


def run(split):
    verify_preparation()
    if split=='eval':verify_freeze()
    config=json.loads((OUT/'execution-config.json').read_text())
    if config['configuration']!=CONFIG:raise ValueError('Configuration mismatch')
    jobs=selected_dev() if split=='dev' else [(r,c) for r in jsonl(DATA/'collection.jsonl') if r['split']=='eval' for c in r['conditions']]
    OUT.mkdir(exist_ok=True)
    with (OUT/'.run.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        metadata=verify_model();save(OUT/'local-metadata.json',metadata)
        directory=RECORDS/('checks' if split=='dev' else 'evaluation')/'nimble_local'
        directory.mkdir(parents=True,exist_ok=True)
        if (directory/'STOP.json').exists():raise PermissionError('Review saved local failure before continuation')
        for i,(row,condition) in enumerate(jobs):
            payload=request(row,condition);key=sha('nimble_local'+row['id']+condition)[:24];path=directory/(key+'-0.json')
            if path.exists():
                if json.loads(path.read_text())['request_sha256']!=sha(canonical(payload)):raise ValueError('Saved request differs')
                continue
            if len(json.dumps(payload,ensure_ascii=False).encode())>65536:raise ValueError('Local API input byte limit exceeded')
            started=datetime.now(timezone.utc).isoformat();t=time.perf_counter()
            status=0;body='';raw=None
            try:
                status,body=call('/v1/systemone',payload)
                raw=json.loads(body) if body else None
                parsed=parse(raw) if status==200 else {'status':'http_error','valid':False,'prediction':None}
            except Exception as error:
                parsed={'status':'local_runtime_error','valid':False,'prediction':None,'error_type':type(error).__name__}
            try:
                metadata_status,running=call('/api/ps');loaded=json.loads(running)
                if metadata_status!=200:loaded={'metadata_unavailable':True,'http_status':metadata_status}
            except Exception as error:
                loaded={'metadata_unavailable':True,'error_type':type(error).__name__}
            record={'version':'nimble-local-v2.3','config':'nimble_local','execution_config_sha256':sha(canonical(config)),
                    'id':row['id'],'split':split,'condition':condition,'attempt':0,
                    'candidate_sha256':row['candidate_sha256'],'request':payload,'request_sha256':sha(canonical(payload)),
                    'access_route':'local','paid_request':False,'reserved_usd':0,'conservative_usage_cost_usd':0,
                    'started_at':started,'elapsed_seconds':round(time.perf_counter()-t,3),
                    'observation':{'http_status':status,'loaded_models':loaded},'raw_body':body,'raw_response':raw,'parsed':parsed,
                    'input_coverage_contract':'Official native local System One rejects oversized input rather than truncating; no generation fallback.'}
            save(path,record)
            print(json.dumps({'split':split,'completed':i+1,'planned':len(jobs),'status':parsed['status']}),flush=True)
            if parsed['status'] not in ('ok','tie'):
                save(directory/'STOP.json',{'id':row['id'],'condition':condition,'status':parsed['status']})
                raise RuntimeError('Local failure saved; no retries or model fallback')
        records=[json.loads(p.read_text()) for p in directory.glob('*-0.json')]
        save(OUT/(split+'-status.json'),{'split':split,'completed_cells':len(records),'distinct_candidates':len({r['id'] for r in records}),'valid_cells':sum(r['parsed']['valid'] for r in records),'api_cost_usd':0,'inference_elapsed_seconds':sum(r['elapsed_seconds'] for r in records),'purpose':'Development operational checks, not a representative accuracy estimate' if split=='dev' else 'frozen held-out evaluation'})


def main():
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['dev','eval','freeze']);a=p.parse_args()
    if a.mode=='freeze':freeze()
    else:run(a.mode)

if __name__=='__main__':main()
