"""Offline validation against native raw values, without importing the adapter/parser."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/laya-empty-field-reproduction'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
plan=json.loads((OUT/'plan.json').read_text())
assert sha(ROOT/'scripts/reproduction/laya_empty_field.py')==plan['script_sha256']
for name,digest in plan['source_hashes'].items():assert sha(ROOT/name)==digest
original={k:json.loads((ROOT/'results/extension-v3/confirmation/laya_local'/f'{v}.json').read_text()) for k,v in {'A':'614aac425fd608ee16de97c0','B':'55c5090952021e24b1635f6d'}.items()}
records=[];pids=set();by_condition={'A':[],'B':[]}
for method in ['adapter','sdk']:
 for order in ['AB','BA']:
  for restart in [1,2]:
   p=OUT/f'{method}-{order}-{restart}.json';session=json.loads(p.read_text())
   assert session['method']==method and session['order']==order and session['restart']==restart
   assert session['pid'] not in pids;pids.add(session['pid'])
   assert session['training'] is False and session['parameter_dtypes']==['torch.float32']
   assert len(session['results'])==4
   for expected,r in zip(order*2,session['results']):
    assert r['condition']==expected and r['request']==original[expected]['request']
    raw=r['raw_response'];value=raw['answers']['injection']['noul'];usage=raw['usage']
    assert raw['model']=='laya-rl-agent' and type(value) in (int,float) and 0<=value<=1
    assert not usage['truncated'] and usage['state_tokens_dropped']==0
    assert usage['input_tokens']==original[expected]['raw_response']['usage']['input_tokens']
    assert r['parsed']['score']==value and r['parsed']['prediction']==int(value>.5)
    by_condition[expected].append(value)
   records.append(p)
assert len(pids)==8 and all(len(x)==16 for x in by_condition.values())
result={'status':'passed','sessions':8,'forward_calls':32,'original_results_unchanged':True,'source_hashes':plan['source_hashes'],'session_hashes':{p.name:sha(p) for p in records},'native_scores':{k:sorted(set(v)) for k,v in by_condition.items()},'matches_original_at_reported_precision':all(v==original[k]['raw_response']['answers']['injection']['noul'] for k,values in by_condition.items() for v in values),'scope':'Post-hoc reproducibility of one selected pair on pinned CPU/eager SDK; does not independently validate SDK implementation or establish population error/bias.'}
(OUT/'verification.json').write_text(json.dumps(result,indent=2,sort_keys=True)+'\n')
print(json.dumps({k:v for k,v in result.items() if k not in ['source_hashes','session_hashes']}))
