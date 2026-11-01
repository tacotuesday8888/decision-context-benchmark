"""Preserve evidence for a lost subscription attempt without rerunning or releasing its reserve."""
import fcntl
import json
from pathlib import Path
from execute import OUT,ROOT,DATA,sha,canonical,request,jsonl,save,verify_preparation


def main():
    verify_preparation()
    with (OUT/'.run.lock').open('a') as serial, (OUT/'.eval-astra_chat.run.lock').open('a') as current:
        fcntl.flock(serial,fcntl.LOCK_EX|fcntl.LOCK_NB)
        fcntl.flock(current,fcntl.LOCK_EX|fcntl.LOCK_NB)
        path=OUT/'execution-ledger.json';ledger=json.loads(path.read_text())
        config=json.loads((OUT/'execution-config.json').read_text())
        for entry in ledger['entries']:
            if entry['state']!='pending':continue
            split,model,key,attempt=entry['key'].split(':')
            if model!='astra_chat' or split!='eval' or entry['accounted_usd']!=0:
                raise ValueError('Only the known zero-metered subscription interruption is handled')
            destination=OUT/'evaluation'/model/(key+'-'+attempt+'.json')
            if destination.exists():continue
            matches=[(r,c) for r in jsonl(DATA/'collection.jsonl') if r['split']==split for c in r['conditions'] if sha(model+r['id']+c)[:24]==key]
            if len(matches)!=1:raise ValueError('Cannot reconstruct unique frozen planned cell')
            row,condition=matches[0];payload=request(model,row,condition)
            record={'version':'expanded-execution-v2.1-interruption-record','config':model,
                    'execution_config_sha256':sha(canonical(config)),'id':row['id'],'split':split,
                    'condition':condition,'attempt':int(attempt),'candidate_sha256':row['candidate_sha256'],
                    'request':payload,'request_sha256':sha(canonical(payload)),
                    'access_route':'subscription','paid_request':False,'reserved_usd':0,'conservative_usage_cost_usd':0,
                    'started_at':None,'elapsed_seconds':None,'observation':{'http_status':0,'request_delivery':'unknown','raw_response_available':False},
                    'raw_body':'','parsed':{'status':'interrupted_attempt_unknown','valid':False,'prediction':None},
                    'recovery_evidence':{'ledger':str(path.relative_to(ROOT)),'pending_key':entry['key'],'request_reconstructed_from_frozen_plan':True,'response_reconstructed':False,'reservation_released':False,'prior_processes_absent_and_run_locks_acquired':True},
                    'note':'Pending attempt survived terminated process. Unknown whether request reached provider; no response exists. Preserve invalid cell and reserve; do not retry as a semantic error.'}
            save(destination,record)
            print('Preserved interrupted cell without retry or reservation release:',key)

if __name__=='__main__':main()
