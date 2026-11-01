"""Exact reviewed nonterminal stream exception; never retries the missing cell."""
from datetime import datetime
import json
from pathlib import Path
import time
from preserved_adapters import sha
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'

def nonterminal_timeout(record, expected_model):
    """No answer, refusal, terminal event, usage or provider error may be bypassed."""
    if (record.get('access_route') != 'subscription' or record.get('paid_request') is not False
            or record.get('accounting_error')
            or record.get('observation', {}).get('http_status') != 200
            or record.get('observation', {}).get('transport_exit_code') != 28
            or record.get('parsed') != {'prediction': None, 'status': 'interrupted_stream',
                'termination': 'missing_terminal_event', 'valid': False}):
        return False
    events = []
    for line in record.get('raw_body', '').splitlines():
        if line.startswith('event:'):
            if line.split(':', 1)[1].strip() not in ('response.created', 'response.in_progress', 'keepalive'):
                return False
        elif line.startswith('data:'):
            try:
                event = json.loads(line.split(':', 1)[1])
            except ValueError:
                return False
            if event == {'type': 'keepalive', 'sequence_number': 2}:
                events.append('keepalive')
                continue
            response = event.get('response', {})
            if (event.get('type') not in ('response.created', 'response.in_progress')
                    or response.get('model') != expected_model
                    or response.get('status') != 'in_progress'
                    or response.get('output') != []
                    or response.get('error') is not None
                    or response.get('incomplete_details') is not None
                    or response.get('usage') is not None):
                return False
            events.append(event['type'])
        elif line.strip():
            return False
    return events == ['response.created', 'response.in_progress', 'keepalive']


def resolve():
    policy_path=OUT/'stream-continuation-v1.json'
    policy=json.loads(policy_path.read_text())
    assert policy['tool_sha256']==sha(Path(__file__).read_bytes())
    assert policy['confirmation_freeze_sha256']==sha((OUT/'confirmation-freeze-v1.json').read_bytes())
    path=ROOT/policy['stop_path'];record_path=ROOT/policy['record_path']
    assert sha(path.read_bytes())==policy['stop_sha256'] and sha(record_path.read_bytes())==policy['record_sha256']
    record=json.loads(record_path.read_text());config=record['job']['config']
    assert record['status']=='failed' and not record.get('error_type')
    assert nonterminal_timeout(record,policy['model'])
    assert len(list(path.parent.glob('STOP*.json')))<=10
    ledger=json.loads((OUT/'inference-ledger-v1.json').read_text())['entries']
    entry=next(e for e in ledger if e['key']=='confirmation:'+config+':'+record_path.stem)
    assert entry['status']=='settled' and entry['accounted_usd']==entry['reserved_usd']==0
    receipt={'config':config,'stop_sha256':sha(path.read_bytes()),'failure_sha256':sha(record_path.read_bytes()),
        'not_before_epoch':datetime.fromisoformat(record['started_at']).timestamp()+record['elapsed_seconds']+60,
        'policy':'Exact reviewed nonterminal empty-output timeout; preserve failed cell, continue only untouched jobs.',
        'policy_sha256':sha(policy_path.read_bytes())}
    target=OUT/'continuations'/(sha(path.read_bytes())+'.json')
    if target.exists():assert json.loads(target.read_text())==receipt
    else:target.write_text(json.dumps(receipt,indent=2,sort_keys=True)+'\n')
    print(json.dumps({'preserved_failure':str(record_path.relative_to(ROOT)),'cooldown_remaining_seconds':max(0,receipt['not_before_epoch']-time.time())}))
if __name__=='__main__':resolve()
