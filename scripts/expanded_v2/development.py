"""Explicitly bounded existing-subscription development checks, never evaluation or paid fallback."""
import argparse,json,sys,time
from datetime import datetime,timezone
from common import ROOT,DATA,OUT,sha,jsonl,dump
from panel import PANEL
from adapters import request,parse,LocalDetector
sys.path.insert(0,str(ROOT/'scripts'))
from provider_access import subscription_credentials
from smoke_access import post


def dev_rows():
    rows=[r for r in jsonl(DATA/'collection.jsonl') if r['split']=='dev']
    selected=[]
    for domain in ['bipia-email','bipia-table','bipia-code']:
        for gold in [0,1]:
            candidates=[r for r in rows if r['dataset']==domain and r['gold']==gold]
            if candidates:selected.append(candidates[0])
    return selected


def run_local():
    start=time.perf_counter();model=LocalDetector();records=[]
    for row in dev_rows():
        records.append({'id':row['id'],'split':'dev','gold':row['gold'],'candidate_sha256':row['candidate_sha256'],
                        'result':model.classify(row['candidate'])})
    dump(OUT/'local-development.json',{'purpose':'development access/window validation; no evaluation',
        'collection_sha256':sha((DATA/'collection.jsonl').read_bytes()),'records':records,
        'logical_scans':len(records),'model_windows':sum(x['result']['windows'] for x in records),
        'elapsed_seconds':round(time.perf_counter()-start,3)})
    print(json.dumps({'local_dev_scans':len(records),'windows':sum(x['result']['windows'] for x in records)}))


def run_subscription():
    records=OUT/'development';records.mkdir(exist_ok=True)
    chosen=dev_rows()
    jobs=[]
    for config in ['luna_chat','astra_chat']:
        for row in (chosen[:4] if config=='luna_chat' else chosen[-2:]):
            for condition in ['candidate','task']:jobs.append((config,row,condition))
    # At most 12 calls for this preparation. No retries, no API-key credentials, no other endpoint.
    for config,row,condition in jobs:
        key=sha(config+row['id']+condition)[:24];path=records/(key+'.json')
        if path.exists():continue
        if len(list(records.glob('*.json')))>=12:raise ValueError('Development call cap reached')
        payload=request(config,row,condition)
        credential=subscription_credentials()['access_token']
        observation,body=post('https://api.openai.com/v1/responses',payload,{'Authorization':'Bearer '+credential})
        body=(body or '').replace(credential,'[redacted]')
        result={'config':config,'id':row['id'],'split':'dev','gold':row['gold'],'condition':condition,
                'started_at':datetime.now(timezone.utc).isoformat(),'request':payload,'request_sha256':sha(json.dumps(payload,sort_keys=True)),
                'candidate_sha256':row['candidate_sha256'],'access_route':'existing authorized subscription; no API-key fallback',
                'paid_requests':0,'observation':observation,'raw_body':body,
                'parsed':{'status':'http_error','valid':False,'prediction':None}}
        if observation['http_status']==200:
            try:result['parsed']=parse(config,body)
            except (ValueError,KeyError,TypeError):result['parsed']={'status':'parse_error','valid':False,'prediction':None}
        dump(path,result)
        print(json.dumps({'config':config,'condition':condition,'status':result['parsed']['status']}),flush=True)
        if not result['parsed']['valid']:
            print('Development stopped; preserve diagnostic and revise only in a new settings revision.',flush=True);return


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['local','subscription']);a=p.parse_args()
    run_local() if a.mode=='local' else run_subscription()
