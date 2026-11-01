"""Verify every planned development attempt without treating correctness as a gate."""
from collections import Counter
import json
from pathlib import Path
import plan
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'

def main():
    rows={r['id']:r for r in plan.read(ROOT/'data/raw/controls-v4/prepared-collection-v1.jsonl')}
    amendment=json.loads((OUT/'development-amendment-v4.0.1.json').read_text())
    accepted=amendment['reviewed_development_transport_failure']['record_sha256']
    ledger={e['key']:e for e in json.loads((OUT/'inference-ledger-v1.json').read_text())['entries']}
    summaries={};hashes={}
    for config in plan.preserved.PANEL:
        records=[];entries=[]
        for job in plan.read(OUT/'development-jobs-v1.jsonl'):
            if job['config']!=config:continue
            key=plan.preserved.sha(json.dumps(job,sort_keys=True))[:24]
            p=OUT/'development'/config/(key+'.json');r=json.loads(p.read_text())
            payload=plan.request(config,rows[job['id']],job['condition'])
            assert r['job']==job and r['request']==payload
            assert r['request_sha256']==plan.preserved.sha(plan.preserved.canonical(payload))
            digest=plan.preserved.sha(p.read_bytes());hashes[str(p.relative_to(ROOT))]=digest
            assert r['status']=='completed' or digest==accepted
            entry=ledger['development:'+config+':'+key];assert entry['status'] in ('settled','unknown_usage')
            if entry['status']=='unknown_usage':assert entry['accounted_usd']==entry['reserved_usd'] and digest==accepted
            if r['status']=='completed':
                assert r['parsed']['status'] in ('ok','tie')
                assert not r['parsed'].get('usage',{}).get('truncated',False)
            records.append(r);entries.append(entry)
        parsed=[r['parsed'] for r in records if r['status']=='completed']
        usages=[r.get('usage',{}) for r in parsed]
        summaries[config]={'attempts':len(records),'status_counts':dict(Counter(r['status'] for r in records)),
            'parsed_status_counts':dict(Counter(r.get('parsed',{}).get('status','runtime_error') for r in records)),
            'max_reported_input_tokens':max((u.get('input_tokens',0) for u in usages),default=0),
            'max_reported_output_tokens':max((u.get('output_tokens',0) for u in usages),default=0),
            'conservative_cost_usd':sum(e['accounted_usd'] for e in entries),
            'predictions':dict(Counter(str(r.get('prediction')) for r in parsed)),
            'note':'Prediction distribution descriptive only; no prompt/threshold fitting.'}
    report={'status':'development_operational_gate_passed_with_one_reviewed_503',
        'by_configuration':summaries,'records_sha256':hashes,'amendment_sha256':plan.preserved.sha((OUT/'development-amendment-v4.0.1.json').read_bytes()),
        'output_budget_changes':0,'truncated_responses':0,'semantic_gold_created':0,
        'scope':'All 372 planned attempts retained; one HTTP503 remains missing with full reservation. No confirmation inference or outcome analysis here.'}
    (OUT/'development-report-v1.json').write_text(json.dumps(report,indent=2,sort_keys=True)+'\n')
    print(json.dumps({k:v for k,v in report.items() if k!='records_sha256'},indent=2))
if __name__=='__main__':main()
