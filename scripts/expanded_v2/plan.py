"""Offline request/token/cost plan. Estimates are not charges or evaluation outcomes."""
import json,math
from collections import Counter
from common import ROOT,DATA,OUT,sha,dump,jsonl
from panel import PANEL,QUESTION
from adapters import request


def build_plan():
    rows=jsonl(DATA/'collection.jsonl');jobs=[];totals={}
    for config,p in PANEL.items():
        totals[config]={}
        for split in ['dev','eval']:
            selected=[r for r in rows if r['split']==split];items=[]
            for row in selected:
                conditions=['candidate'] if p['kind']=='local_detector' else row['conditions']
                for condition in conditions:
                    payload=request(config,row,condition)
                    serialized=json.dumps(payload,ensure_ascii=False,sort_keys=True)
                    count=math.ceil(len(serialized)/4)
                    upper=len(serialized.encode())+512
                    if p['kind']!='local_detector' and upper>p['context_tokens']:
                        raise ValueError('Conservative context limit exceeded')
                    item={'config':config,'id':row['id'],'split':split,'condition':condition,
                          'endpoint':p.get('endpoint'),'request_sha256':sha(serialized),
                          'input_tokens_char_estimate':count,'input_tokens_byte_upper':upper,
                          'max_output_tokens':p.get('output_cap')}
                    jobs.append(item);items.append(item)
            n=len(items);tokens=sum(i['input_tokens_char_estimate'] for i in items)
            upper=sum(i['input_tokens_byte_upper'] for i in items)
            # Planning assumptions; replace by a separately versioned dev-based estimate, never gold tuning.
            output_mean=16 if config=='luna_chat' else (256 if config=='astra_chat' else 0)
            estimated=(tokens*p['input_usd_per_million']+n*output_mean*p['output_usd_per_million'])/1e6
            ceiling=(upper*p['input_usd_per_million']+n*(p.get('output_cap') or 0)*p['output_usd_per_million'])/1e6
            totals[config][split]={'logical_requests_or_scans':n,'input_tokens_char_estimate':tokens,
                'input_tokens_byte_upper':upper,'assumed_mean_output_tokens':output_mean,
                'api_equivalent_estimated_usd':round(estimated,4),'conservative_input_and_output_cap_usd':round(ceiling,4),
                'api_billable_now':False}
        # 5% max transient retries; no retries for quota/auth/funding/schema/refusal/truncation.
        base=totals[config]['eval'];retry=math.ceil(base['logical_requests_or_scans']*.05) if p['kind']!='local_detector' else 0
        totals[config]['retry_reserve']={'max_requests':retry,
             'estimated_usd':round(base['api_equivalent_estimated_usd']*.05,4),
             'worst_case_top_5pct_requests_usd':round(sum(sorted([
                 (i['input_tokens_byte_upper']*p['input_usd_per_million']+(p.get('output_cap') or 0)*p['output_usd_per_million'])/1e6
                 for i in jobs if i['config']==config and i['split']=='eval'],reverse=True)[:retry]),4)}
    manifest={'status':'prepared; evaluation disabled pending billing and all-model development checks',
              'collection_sha256':sha((DATA/'collection.jsonl').read_bytes()),
              'model_panel_sha256':sha((DATA/'model-panel.json').read_bytes()),'prompts_sha256':sha((DATA/'prompts.json').read_bytes()),
              'configurations':len(PANEL),'distinct_model_ids':len({p['model'] for p in PANEL.values()}),
              'totals':totals,'requests':jobs,'paid_enabled':False}
    dump(OUT/'request-plan.json',manifest)
    return manifest


def main():
    p=build_plan();t=p['totals'];estimated=sum(x[s]['api_equivalent_estimated_usd'] for x in t.values() for s in ['dev','eval'])+sum(x['retry_reserve']['estimated_usd'] for x in t.values())
    ceiling=sum(x[s]['conservative_input_and_output_cap_usd'] for x in t.values() for s in ['dev','eval'])+sum(x['retry_reserve']['worst_case_top_5pct_requests_usd'] for x in t.values())
    budget={'estimate_method':'ceil(serialized request characters/4), no cache discounts; planning means 16 Luna and 256 Astra output tokens; not tokenizer quotes',
            'api_equivalent_total_estimated_usd':round(estimated,2),'conservative_total_cap_based_usd':round(ceiling,2),
            'paid_requests_made':0,'funding_is_not_spending_authorization':True,'totals':t}
    dump(OUT/'budget.json',budget)
    print(json.dumps({k:v for k,v in budget.items() if k!='totals'}))

if __name__=='__main__':main()
