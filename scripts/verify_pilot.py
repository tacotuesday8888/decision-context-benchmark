"""Offline integrity checks. Never performs inference or prints secret values."""
import csv
import json
from pathlib import Path
import sys
from collections import Counter
from prepare_pilot import ROOT, load_data, sha
from run_pilot import CONDITIONS, MODELS, plan, state_for
from analyze_pilot import load_records, metrics


def check_secrets(paths):
    secrets=[]
    env=ROOT/'.env.local'
    if env.exists():
        secrets += [s.split('=',1)[1].strip() for s in env.read_text().splitlines() if '=' in s and not s.startswith('#')]
    path=ROOT/'.secrets/chatgpt.json'
    if path.exists():
        d=json.loads(path.read_text())
        secrets += [d.get(k,'') for k in ['access_token','refresh_token','id_token']]
    secrets=[x.encode() for x in secrets if isinstance(x,str) and len(x)>12]
    for path in paths:
        content=path.read_bytes()
        if any(value in content for value in secrets):
            raise ValueError('Credential match in '+str(path.relative_to(ROOT)))


def main():
    manifest=json.loads((ROOT/'data/manifest.json').read_text())
    assert sha((ROOT/'data/pilot.jsonl').read_bytes())==manifest['selection_sha256']
    examples=load_data();by_id={e['id']:e for e in examples}
    assert len(by_id)==20
    assert not ({e['group'] for e in examples if e['split']=='dev'} & {e['group'] for e in examples if e['split']=='eval'})
    rows,expected,seen=load_records()
    for r in rows:
        e=by_id[r['id']]
        assert r['gold']==e['gold'] and r['group']==e['group'] and r['split']==e['split']
        assert r['candidate_sha256']==e['candidate_sha256']
        request=r['request']
        state=request['state'] if r['provider']=='jevmodel' else (request['input'][0]['content'] if r['provider']=='openai' else request['contents'][0]['parts'][0]['text'])
        assert state==state_for(e,r['condition'])
        assert len(r['attempts'])<=2
        assert r['paid_spend_usd']==0
    for p in ['jevmodel','openai']:
        for c in CONDITIONS:
            subset=[r for r in rows if r['provider']==p and r['condition']==c and r['split']=='eval']
            assert len(subset)==18, (p,c,'Incomplete primary panel')
    for p,cap in [('jevmodel',88),('openai',88),('gemini',20)]:
        assert sum(len(r['attempts']) for r in rows if r['provider']==p)<=cap
    table=list(csv.DictReader((ROOT/'results/pilot/per-example.csv').open()))
    supplement=[json.loads(p.read_text()) for p in (ROOT/'results/pilot/gemini-3.7-records').glob('*.json')]
    assert len(table)==len(rows)+len(supplement)
    for r in supplement:
        e=by_id[r['id']]
        assert r['gold']==e['gold'] and r['group']==e['group']
        assert r['requested_model']=='gemini-3.7-flash'
        assert r['endpoint'].endswith('models/gemini-3.7-flash:generateContent')
        assert r['request_sha256']==sha(json.dumps(r['request'],sort_keys=True,ensure_ascii=False))
        assert r['paid_spend_usd']==0
    assert len(supplement)<=20
    summary=json.loads((ROOT/'results/pilot/summary.json').read_text())
    for p in ['jevmodel','openai']:
        for c in CONDITIONS:
            m=metrics([r for r in rows if r['provider']==p and r['condition']==c and r['split']=='eval'])
            for k in ['balanced_accuracy','fp','fn','n','valid_n']:
                assert summary['primary'][p][c][k]==m[k]
    paths=[p for directory in ['scripts','tests','docs','data','results/pilot','.github']
           for p in (ROOT/directory).rglob('*') if p.is_file() and '__pycache__' not in str(p) and '/data/raw/' not in str(p)]
    paths += [ROOT/'README.md',ROOT/'AGENTS.md',ROOT/'.env.example']
    check_secrets(paths)
    print(json.dumps({'primary_eval_requests_verified':144,'records_verified':len(rows)+len(supplement),
                      'missing_planned_records':len(expected)-len(seen),'secret_scan_files':len(paths),
                      'secret_matches':0,'network_requests':0}))


if __name__=='__main__':main()
