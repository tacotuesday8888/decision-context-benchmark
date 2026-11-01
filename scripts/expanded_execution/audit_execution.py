"""Complete-cell and per-response identity/usage/ledger audit, without inference."""
import argparse
from collections import Counter
import json
import math
from execute import OUT,ROOT,DATA,PANEL,jsonl,request,canonical,sha,save
import importlib.util
_spec=importlib.util.spec_from_file_location('execution_verifier',ROOT/'scripts/expanded_execution/verify.py')
_verifier=importlib.util.module_from_spec(_spec);_spec.loader.exec_module(_verifier)
verify=_verifier.verify
from spending import totals,caps


def audit_native(record):
    if record['config']!='nimble_local' or record['parsed']['status'] not in ('ok','tie'):return
    models=record['observation']['loaded_models'].get('models',[])
    selected=[m for m in models if m.get('name')==PANEL['nimble_local']['model']]
    assert len(selected)==1,'Native loaded model missing or ambiguous'
    m=selected[0]
    assert m['digest']==PANEL['nimble_local']['revision'],'Loaded model digest mismatch'
    assert m['details']['quantization_level']=='Q4_K_M'
    assert record['parsed']['usage']['input_tokens']<=m['context_length'],'Native input exceeds loaded context'


def audit(require_terminal=False):
    verify()
    policy=json.loads((OUT/'hosted-amendment-v2.3.3.json').read_text())
    for name,expected_hash in policy['hashes'].items():
        assert sha((ROOT/name).read_bytes())==expected_hash,('Changed continuation policy/evidence',name)
    candidates=[r for r in jsonl(DATA/'collection.jsonl') if r['split']=='eval']
    expected={(config,r['id'],condition):sha(canonical(request(config,r,condition))) for config in PANEL for r in candidates for condition in (['candidate'] if config=='protectai_local' else r['conditions'])}
    actual={};hashes={};statuses=Counter();usage={};attempt_keys=set()
    for config in PANEL:
        used=[]
        for path in sorted((OUT/'evaluation'/config).glob('*-*.json')):
            r=json.loads(path.read_text())
            if 'parsed' not in r:continue
            key=(config,r['id'],r['condition']);assert key in expected
            assert r['request_sha256']==expected[key]
            expected_name=sha(config+r['id']+r['condition'])[:24]+'-'+str(r['attempt'])+'.json'
            assert path.name==expected_name
            audit_native(r)
            if key not in actual or r['attempt']>actual[key]['attempt']:actual[key]=r
            hashes[str(path.relative_to(ROOT))]=sha(path.read_bytes())
            u=r['parsed'].get('usage') or {}
            if r['parsed']['status'] in ('ok','tie') and config!='protectai_local':
                assert isinstance(u.get('input_tokens'),int) and not isinstance(u['input_tokens'],bool) and u['input_tokens']>0
                assert not u.get('truncated') and not u.get('state_tokens_dropped',0)
                used.append(u['input_tokens'])
            if r['access_route']!='local':attempt_keys.add('eval:'+config+':'+path.name[:-7]+':'+str(r['attempt']))
        usage[config]={'valid_native_or_chat_usage_records':len(used),'min_input_tokens':min(used) if used else None,'max_input_tokens':max(used) if used else None,'sum_input_tokens':sum(used)}
    ledgers=[]
    for p in sorted(OUT.glob('*ledger*.json')):
        for e in json.loads(p.read_text()).get('entries',[]):ledgers.append((p.name,e))
    ledgerkeys=[e['key'] for _,e in ledgers]
    assert len(ledgerkeys)==len(set(ledgerkeys)),'Duplicate attempt budget reservations'
    assert attempt_keys<=set(ledgerkeys),'Remote attempt lacks reservation'
    pending=[]
    for name,e in ledgers:
        if e['state']=='pending':pending.append({'ledger':name,'key':e['key'],'accounted_usd':e['accounted_usd'],'has_saved_record':e['key'] in attempt_keys})
    missing=[{'config':k[0],'id':k[1],'condition':k[2]} for k in expected if k not in actual]
    if require_terminal:
        assert not missing,'Intended evaluation cells remain unrun'
        assert all(e['has_saved_record'] for e in pending),'Unresolved pending attempt without record'
    for (config,_,_),r in actual.items():statuses[config+':'+r['parsed']['status']]+=1
    result={'version':'execution-audit-v1','terminal_required':require_terminal,'planned_cells':len(expected),'saved_cells':len(actual),'missing_cells':missing,'status_counts':dict(statuses),'usage':usage,'pending_reservations':pending,'accounted_usd':totals(OUT),'caps_usd':caps(),'record_hashes':hashes,'native_loaded_digest_verified':True,'raw_parsing_and_frozen_preparation_verified':True}
    save(OUT/'execution-audit.json',result)
    print(json.dumps({k:result[k] for k in ['planned_cells','saved_cells','status_counts','pending_reservations']}))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--require-terminal',action='store_true');args=parser.parse_args();audit(args.require_terminal)
