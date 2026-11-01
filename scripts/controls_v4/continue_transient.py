"""Reviewed bounded continuation of untouched jobs; never resend a failed cell."""
import argparse
from datetime import datetime
import json
from pathlib import Path
import time
from preserved_adapters import sha
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'

def eligible(record):
    observation=record.get('observation',{})
    if record.get('status')!='failed' or record.get('error_type'):return False
    if record.get('accounting_error') not in (None,'missing_usage'):return False
    body=record.get('raw_body','')
    if any(s in body.lower() for s in ('insufficient_quota','billing','unauthorized','invalid_api_key','usage_limit_reached')):return False
    return record.get('parsed',{}).get('status')=='http_error' and observation.get('http_status') in (0,429,500,502,503,504)

def resolve(config):
    directory=OUT/'confirmation'/config
    stops=list(directory.glob('STOP*.json'))
    if len(stops)>10:raise PermissionError('Ten continuation limit reached')
    ledger={e['key']:e for e in json.loads((OUT/'inference-ledger-v1.json').read_text())['entries']}
    for path in stops:
        stop=json.loads(path.read_text());record_path=ROOT/stop['record'];record=json.loads(record_path.read_text())
        target=OUT/'continuations'/(sha(path.read_bytes())+'.json')
        if target.exists():
            receipt=json.loads(target.read_text())
            assert receipt['stop_sha256']==sha(path.read_bytes()) and receipt['failure_sha256']==sha(record_path.read_bytes())
            continue
        if not eligible(record):raise PermissionError('Stop needs specific inspection/versioned correction')
        entry=ledger['confirmation:'+config+':'+record_path.stem]
        if entry['status']=='pending':raise PermissionError('Accounting still pending')
        if entry['status']=='unknown_usage' and entry['accounted_usd']!=entry['reserved_usd']:raise PermissionError('Unknown usage must retain full reservation')
        delay=max(60,float(record['observation'].get('response_headers',{}).get('retry-after','60')))
        receipt={'config':config,'stop_sha256':sha(path.read_bytes()),'failure_sha256':sha(record_path.read_bytes()),
            'not_before_epoch':datetime.fromisoformat(record['started_at']).timestamp()+record['elapsed_seconds']+delay,
            'policy':'HTTP transient only; unknown usage retains full reservation; no replacement or retry; ten continuations per route maximum.',
            'tool_sha256':sha(Path(__file__).read_bytes()),'confirmation_freeze_sha256':sha((OUT/'confirmation-freeze-v1.json').read_bytes())}
        target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
        print(json.dumps({'preserved':stop['record'],'cooldown_remaining_seconds':max(0,receipt['not_before_epoch']-time.time())}))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);resolve(p.parse_args().config)
