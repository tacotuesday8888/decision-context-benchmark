"""Credential-free offline verification and immutable preparation snapshot."""
import argparse,json,sys
from collections import Counter
from common import ROOT,DATA,OUT,VERSION,sha,jsonl,dump
from prepare import validate
from panel import PANEL
from adapters import request,parse
sys.path.insert(0,str(ROOT/'scripts'))
from verify_pilot import check_secrets


def verify(freeze=False):
    pilot=json.loads((OUT/'pilot-integrity.json').read_text())
    for name,digest in pilot.items():
        if sha((ROOT/name).read_bytes())!=digest:raise ValueError('Original pilot changed: '+name)
    rows=jsonl(DATA/'collection.jsonl');by_id={r['id']:r for r in rows};summary=validate(rows)
    assert json.loads((DATA/'model-panel.json').read_text())['configurations']==PANEL
    manifest=json.loads((DATA/'manifest.json').read_text())
    assert manifest['collection_sha256']==sha((DATA/'collection.jsonl').read_bytes())
    assert manifest['sources_sha256']==sha((DATA/'sources.json').read_bytes())
    assert manifest['summary']==summary
    records=[]
    for path in sorted((OUT/'development').glob('*.json')):
        r=json.loads(path.read_text());row=by_id[r['id']]
        assert row['split']==r['split']=='dev' and row['gold']==r['gold']
        assert row['candidate_sha256']==r['candidate_sha256']
        assert r['request']==request(r['config'],row,r['condition'])
        # Historical dev traces hash the serialized request with ASCII escaping;
        # the offline plan uses Unicode-preserving canonical JSON. Verify both by their stated encodings.
        assert r['request_sha256']==sha(json.dumps(r['request'],sort_keys=True))
        assert r['parsed']==parse(r['config'],r['raw_body'])
        assert r['paid_requests']==0 and r['parsed']['valid']
        returned=r['parsed'].get('returned_settings',{})
        assert returned.get('max_output_tokens')==r['request']['max_output_tokens']
        assert returned.get('reasoning',{}).get('effort')==r['request']['reasoning']['effort']
        records.append(r)
    assert Counter(r['config'] for r in records)=={'luna_chat':8,'astra_chat':4}
    scans=windows=0
    for name in ['local-development.json','local-window-development.json']:
        d=json.loads((OUT/name).read_text())
        for r in d['records']:
            row=by_id[r['id']]
            assert row['split']=='dev' and row['candidate_sha256']==r['candidate_sha256']
            assert r['result']['revision']==PANEL['protectai_local']['revision']
            assert r['result']['windows']==len(r['result']['window_scores'])
            scans+=1;windows+=r['result']['windows']
    assert not any((OUT/'evaluation').glob('*')) if (OUT/'evaluation').exists() else True
    files=[p for base in ['scripts/expanded_v2','tests/expanded_v2','docs/expanded-v2','data/expanded-v2','results/expanded-v2'] for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    check_secrets(files)
    snapshot_files=[p for base in ['scripts/expanded_v2','docs/expanded-v2','data/expanded-v2'] for p in (ROOT/base).rglob('*') if p.is_file() and '__pycache__' not in str(p)]
    snapshot_files += [OUT/'request-plan.json',OUT/'budget.json',ROOT/'requirements-expanded-v2.lock',ROOT/'requirements-expanded-v2-data.txt']
    hashes={str(p.relative_to(ROOT)):sha(p.read_bytes()) for p in sorted(snapshot_files)}
    frozen={'version':VERSION,'status':'prepared; evaluation not cleared; paid execution disabled',
            'hashes':hashes,'paid_enabled':False}
    destination=OUT/'preparation-freeze.json'
    if destination.exists():assert json.loads(destination.read_text())==frozen,'Preparation snapshot changed'
    elif freeze:dump(destination,frozen)
    else:raise ValueError('Preparation snapshot missing')
    result={'pilot_files_unchanged':len(pilot),'development_remote_calls':len(records),
            'local_development_scans':scans,'local_development_forward_windows':windows,
            'evaluation_requests_made':0,'paid_requests_made':0,'credential_matches':0,
            'distinct_evaluation_candidates':summary['distinct_candidates']['eval'],
            'distinct_development_candidates':summary['distinct_candidates']['dev'],
            'planned_evaluation_remote_requests':4*summary['available_condition_cells']['eval'],
            'planned_local_evaluation_scans':summary['distinct_candidates']['eval']}
    dump(OUT/'verification.json',result)
    print(json.dumps(result,sort_keys=True))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--freeze',action='store_true');a=p.parse_args();verify(a.freeze)
