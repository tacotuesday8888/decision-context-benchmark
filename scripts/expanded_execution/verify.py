"""Offline verification of saved execution; never loads a credential for inference."""
from collections import Counter
import json
from pathlib import Path
import sys
from execute import OUT, ROOT, DATA, PANEL, canonical, sha, jsonl, verify_preparation, safe_parse, reserve_usd
from adapters import request, probability
from verify_pilot import check_secrets


def verify():
    verify_preparation()
    rows={r['id']:r for r in jsonl(DATA/'collection.jsonl')}
    seen=set();counts=Counter();files=[]
    for phase in ('checks','evaluation'):
        for config in PANEL:
            for path in (OUT/phase/config).glob('*-*.json'):
                if path.name=='stop-resolution.json':continue
                record=json.loads(path.read_text());files.append(path)
                row=rows[record['id']]
                assert row['split']==record['split']==('dev' if phase=='checks' else 'eval')
                assert row['candidate_sha256']==record['candidate_sha256']
                assert record['request']==request(config,row,record['condition'])
                assert record['request_sha256']==sha(canonical(record['request']))
                key=(phase,config,row['id'],record['condition'],record['attempt'])
                assert key not in seen;seen.add(key)
                if config=='protectai_local':
                    parsed=record['parsed'];scores=parsed['window_scores']
                    assert parsed['windows']==len(scores)
                    assert parsed['revision']==PANEL[config]['revision']
                    expected=probability(max(scores))
                    assert all(parsed[k]==v for k,v in expected.items())
                elif record['observation']['http_status']==200:
                    assert record['parsed']==safe_parse(config,record['raw_body'])
                assert record['reserved_usd']==reserve_usd(config,record['request'],record['access_route'])
                if record['access_route']=='api_key':
                    assert record['paid_request'] is True
                else:assert record['paid_request'] is False
                counts[phase+':'+config]+=1
    total=0
    for path in OUT.glob('*ledger*.json'):
        d=json.loads(path.read_text());assert all(e['accounted_usd']>=0 for e in d['entries'])
        n=sum(e['accounted_usd'] for e in d['entries'])
        assert n<=d['cap_usd']+1e-12
        if path.name.startswith('execution-ledger'):total+=n
    assert total<=14.01+1e-12
    check=json.loads((OUT/'check-ledger.json').read_text())
    assert sum(e['accounted_usd'] for e in check['entries'])<=.99+1e-12
    source_files=[p for base in ('scripts/expanded_execution','tests/expanded_execution','docs/expanded-execution','results/expanded-execution') for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in str(p) and p.suffix!='.lock']
    check_secrets(source_files)
    print(json.dumps({'records':dict(counts),'evaluation_accounted_usd':total,'pilot_and_preparation_intact':True,'credential_matches':0},sort_keys=True))

if __name__=='__main__':verify()
