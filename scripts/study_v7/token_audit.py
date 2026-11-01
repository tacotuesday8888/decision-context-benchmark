"""Measure frozen payloads with local tokenizers only, without loading weights.

Run using the already installed tiktoken/tokenizers environment. o200k_base is a
serialization proxy: neither GPT-6 nor Jev is certified to use that tokenizer.
ProtectAI candidate token/window counts use its actual pinned tokenizer.
"""
from __future__ import annotations
import argparse
from collections import defaultdict
from decimal import Decimal
import importlib.metadata
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v7.requests import canonical, digest, materialize, PANEL
from scripts.study_v7.budget import maximum_cost, RATES
from scripts.study_v7.external_data import RAW, OUT, CANONICAL, save, write_rows


def summary(values):
    ordered = sorted(values)
    return {'n':len(values), 'sum':sum(values), 'mean':sum(values)/len(values),
            'min':ordered[0], 'median':ordered[len(ordered)//2], 'max':ordered[-1]}


def full_tokenizer(tokenizer):
    """Override serialized preprocessing limits before measuring full documents."""
    tokenizer.no_truncation()
    tokenizer.no_padding()
    if tokenizer.truncation is not None or tokenizer.padding is not None:
        raise ValueError('Tokenizer would clip or pad the complete candidate')
    return tokenizer


def cost(config, inputs, output=0, native_write=False):
    if PANEL[config]['provider'] is None:
        return Decimal(0)
    million=Decimal(1000000)
    tokens=Decimal(str(inputs))
    if config=='jev_firstparty':
        return tokens*Decimal(RATES['jev_input'])/million
    input_multiplier=Decimal(2) if tokens>272000 else Decimal(1)
    if config=='luna_decisions':
        return tokens*Decimal('.25' if native_write else '.10')*input_multiplier/million
    prefix='sol' if config=='sol_responses' else 'luna'
    output_multiplier=Decimal('1.5') if tokens>272000 else Decimal(1)
    return (tokens*Decimal(RATES[prefix+'_input'])*input_multiplier+Decimal(output)*Decimal(RATES[prefix+'_output'])*output_multiplier)/million


def build_forecast(records, plan, historical=None):
    grouped=defaultdict(list)
    for row in records:
        grouped[row['config']].append(row)
    counts={key:len(value) for key,value in grouped.items()}
    cases={name:{} for name in ('ordinary_proxy','native_write_proxy','stress_2x_proxy_max_output','accepted_context_maximum')}
    for config, rows in grouped.items():
        if PANEL[config]['provider'] is None:
            continue
        # Price tiers apply to each request, never to an aggregate token sum.
        def mean_output(row):
            return (512 if row['condition']=='audit' else 128) if config=='sol_responses' else 16 if config=='luna_responses' else 0
        cases['ordinary_proxy'][config]=str(sum((cost(config,r['serialization_proxy_tokens'],mean_output(r)) for r in rows),Decimal(0)))
        cases['native_write_proxy'][config]=str(sum((cost(config,r['serialization_proxy_tokens'],mean_output(r),True) for r in rows),Decimal(0)))
        cases['stress_2x_proxy_max_output'][config]=str(sum((cost(config,2*r['serialization_proxy_tokens'],PANEL[config].get('output_cap',0),True) for r in rows),Decimal(0)))
        cases['accepted_context_maximum'][config]=str(Decimal(maximum_cost(config))*len(rows))
    for values in cases.values():
        values['openai_total']=str(sum((Decimal(v) for k,v in values.items() if k!='jev_firstparty'),Decimal(0)))
        values['typesafe_total']=values['jev_firstparty']
        values['all_tests_total']=str(Decimal(values['openai_total'])+Decimal(values['typesafe_total']))
    sources={source:{config:{'requests':len(part), 'proxy_tokens':sum(r.get('serialization_proxy_tokens',0) for r in part),
        'protectai_windows':sum(r.get('windows',0) for r in part)}
        for config in grouped for part in [[r for r in grouped[config] if r['source']==source]]}
        for source in ('browsesafe','promptshield')}
    # Usage-only historical request timing. No correctness or predictions are read.
    historic_hours=Decimal('49.6')/60
    runtime={source:{'native_requests':sum(v['requests'] for k,v in configs.items() if k in ('jev_firstparty','luna_decisions')),
        'historical_request_rate_extrapolation_hours':str(historic_hours*sum(v['requests'] for k,v in configs.items() if k in ('jev_firstparty','luna_decisions'))/7904),
        'basis':'49.6 minutes for 7904 historical native calls; unchanged request rate assumption, not measured v7 throughput'}
        for source,configs in sources.items()}
    if historical is None:
        from scripts.study_v7.prepare import historical_accounting
        historical=historical_accounting()['prior_accounted_usd']
    caps={p:str(Decimal(extra)+Decimal(historical[p])) for p,extra in {'openai':'350','typesafe':'20'}.items()}
    return {'version':'study-v7-measured-forecast-2','inference_calls_made':0,'paid_execution_authorized':True,
        'supersedes':'forecast-v1.json: same paid proxy arithmetic; corrects ProtectAI counts by disabling the serialized tokenizer 512-token truncation before full-document window measurement',
        'authorization_reference':'docs/study-v7/RUN-AUTHORIZATION.md',
        'counts':counts, 'paid_calls':sum(v for k,v in counts.items() if PANEL[k]['provider'] is not None),
        'subscription_calls':sum(v for k,v in counts.items() if PANEL[k]['route']=='subscription'),
        'model_configurations':plan.get('model_configurations',{k:PANEL[k] for k in counts}),'rates_usd_per_million':RATES,'cost_scenarios_usd':cases,
        'sources':sources, 'runtime_by_source':runtime,
        'native_projected_hours':str(sum(Decimal(x['historical_request_rate_extrapolation_hours']) for x in runtime.values())),
        'general_required_requests_per_second_each_for_8h':{k:str(Decimal(counts[k])/28800) for k in counts if PANEL[k]['kind']=='responses'},
        'local_windows':sum(r.get('windows',0) for r in records),
        'local_required_windows_per_second_for_8h':str(Decimal(sum(r.get('windows',0) for r in records))/28800),
        'input_basis':{'encoding':'o200k_base','measured':'Exact tokenization of each complete canonical serialized JSON payload under this local encoding.',
            'not_native':'No GPT-6 Luna/Sol or Jev tokenizer mapping is available in installed tiktoken0.13.0. These are proxy counts, not exact billed/native input counts.',
            'framing':'Canonical JSON includes explicit request/schema metadata; hidden server framing is not measured.',
            'conservative_bound':'accepted_context_maximum reserves the full accepted route context per request, output caps and worst documented cache/long-input rates; does not use proxy as certified upper.',
            'protectai':'Actual pinned candidate tokenizer, 510-token windows /64 overlap; no weights loaded or forward passes.',
            'output_assumptions':'Paid Luna mean16;stress uses fixed256 maximum. Sol subscription has an unsupported requested cap/provider-default ceiling and zero API-dollar cost; quota/time are not guaranteed. No empirical output usage exists.'},
        'current_cumulative_caps_usd':caps,
        'historical_conservative_accounted_usd':historical,
        'current_headroom_usd':{p:str(Decimal(caps[p])-Decimal(historical[p])) for p in caps},
        'authorized_incremental_caps_usd':{'openai_tests_audit':'350','openai_optional_authoring':'0','typesafe':'20','total':'370'},
        'optional_authoring_calls_made':0,
        'paid_sol_api_and_paid_authoring_permitted':False,
        'limitations':['Proxy scenarios are forecasts, not certified billing maxima. Full-context maximum is a deliberately loose bound, not an expected bill.',
            'Jev tokenization may differ substantially. Reforecast with authenticated native development usage after authorization without inspecting accuracy.',
            'Provider rate limits, credit, paid Responses field support and all v7 inference throughput remain unverified.',
            'Native and general requests may overlap; serial sums are not a source-specific wall-clock guarantee. ProtectAI hardware throughput remains unmeasured.'],
        'official_sources':['https://developers.openai.com/api/docs/pricing','https://developers.openai.com/api/docs/guides/decisions',
            'https://developers.openai.com/api/docs/models/gpt-6.1-sol','https://docs.typesafe.ai/models',
            'https://github.com/openai/tiktoken/blob/main/tiktoken/model.py'],
        'proxy_requests_above_272k':{config:sum(r.get('serialization_proxy_tokens',0)>272000 for r in records if r['config']==config) for config in counts},
        'doubled_proxy_requests_above_272k':{config:sum(2*r.get('serialization_proxy_tokens',0)>272000 for r in records if r['config']==config) for config in counts},
        'plan_sha256':digest(canonical(plan)+b'\n')}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--plan',type=Path,default=RAW/'request-plan.json')
    ap.add_argument('--output-version',choices=('v2','v3'),default='v2')
    ap.add_argument('--reuse-audit',type=Path,help='Reuse unchanged exact payload measurements from the verified full-token v2 audit')
    ap.add_argument('--tokenizer',type=Path,default=Path.home()/'.cache/huggingface/hub/models--protectai--deberta-v3-base-prompt-injection-v2/snapshots/90c9989b1a342275dd0d1a95aad283c04e075671/tokenizer.json')
    args=ap.parse_args()
    import tiktoken
    from tokenizers import Tokenizer
    enc=tiktoken.get_encoding('o200k_base')
    tok=full_tokenizer(Tokenizer.from_file(str(args.tokenizer)))
    plan=json.loads(args.plan.read_text())
    rows={r['id']:r for name in ('main-selected.jsonl','external-selected-v3.jsonl')
          for r in map(json.loads,(RAW/name).read_text().splitlines())}
    records, cache, local_cache=[],{},{}
    prior={}
    if args.reuse_audit is not None:
        prior_forecast=json.loads((OUT/'forecast-v2.json').read_text())
        if (digest(args.reuse_audit.read_bytes())!=prior_forecast['token_audit_sha256'] or
            prior_forecast.get('protectai_tokenizer_preprocessing')!={'truncation':None,'padding':None,'special_tokens':False}):
            raise ValueError('Only the verified complete-document v2 measurement audit can be reused')
        prior={r['key']:r for r in map(json.loads,args.reuse_audit.read_text().splitlines())}
    reused=0
    for i,request in enumerate(plan['requests'].values()):
        config=request['config']
        body=materialize(request,rows)
        entry={key:request[key] for key in ('key','id','config','source','condition','namespace','split','payload_sha256')}
        old=prior.get(request['key'])
        if old is not None and old['payload_sha256']==request['payload_sha256']:
            entry.update({key:old[key] for key in ('serialization_proxy_tokens','serialized_utf8_bytes','candidate_tokens','windows') if key in old})
            reused+=1
        elif config=='protectai_local':
            sha=digest(body['candidate'].encode())
            if sha not in local_cache:
                n=len(tok.encode(body['candidate'],add_special_tokens=False).ids)
                local_cache[sha]={'candidate_tokens':n,'windows':max(1,1+math.ceil(max(0,n-510)/446))}
            entry.update(local_cache[sha])
        else:
            sha=request['payload_sha256']
            if sha not in cache:
                raw=canonical(body)
                cache[sha]={'serialization_proxy_tokens':len(enc.encode(raw.decode(),disallowed_special=())),
                            'serialized_utf8_bytes':len(raw)}
            entry.update(cache[sha])
        records.append(entry)
        if i and i%10000==0:
            print(f'Tokenized {i} frozen requests; no model forward passes.',flush=True)
    audit_path=RAW/('token-audit-'+args.output_version+'.jsonl')
    write_rows(audit_path,records)
    forecast=build_forecast(records,plan)
    if args.output_version=='v3':
        forecast.update(version='study-v7-measured-forecast-3',supersedes='forecast-v2.json: unchanged paid/local payloads and measurements; separately versioned subscription Sol omits its unsupported cache-control parameter',subscription_revision='v7.0.2')
    forecast['measurements_reused_from_verified_v2']=reused
    forecast['tokenizer_software']={key:importlib.metadata.version(key) for key in ('tiktoken','tokenizers')}
    forecast['protectai_tokenizer_sha256']=digest(args.tokenizer.read_bytes())
    forecast['protectai_tokenizer_preprocessing']={'truncation':tok.truncation,'padding':tok.padding,'special_tokens':False}
    forecast['token_audit_sha256']=digest(audit_path.read_bytes())
    forecast['summary_by_config']={config:summary([r.get('serialization_proxy_tokens',r.get('candidate_tokens')) for r in records if r['config']==config]) for config in forecast['counts']}
    first_main=[r for r in records if r['source']=='browsesafe' and r['namespace']=='first' and r['split']=='confirmation' and r['config']!='protectai_local']
    forecast['main_confirmation_proxy_tokens_by_condition']={config:{condition:summary([
        r['serialization_proxy_tokens'] for r in first_main if r['config']==config and r['condition']==condition])
        for condition in ('format','task','reminder','length')} for config in forecast['counts'] if config!='protectai_local'}
    paired=defaultdict(dict)
    for row in first_main:
        paired[(row['config'],row['id'])][row['condition']]=row['serialization_proxy_tokens']
    forecast['character_matched_task_minus_length_proxy_tokens']={config:summary([
        values['task']-values['length'] for (cfg,_),values in paired.items() if cfg==config])
        for config in forecast['counts'] if config!='protectai_local'}
    forecast['coverage_preflight']={config:{'native_tokenizer_count_verified':config=='protectai_local',
        'model_forward_passes':0,'coverage': 'complete_sliding_windows' if config=='protectai_local' else 'unchanged_full_input_server_gate_pending_development',
        'proxy_count_above_native_limit_not_certified':sum(r.get('serialization_proxy_tokens',0)>forecast['model_configurations'][config]['context_tokens'] for r in records if r['config']==config)}
        for config in forecast['counts']}
    save(OUT/('forecast-'+args.output_version+'.json'),json.dumps(forecast,indent=2,sort_keys=True).encode()+b'\n')
    print(json.dumps({'paid_calls':forecast['paid_calls'],'cost_scenarios_usd':forecast['cost_scenarios_usd'],'local_windows':forecast['local_windows']}))


if __name__=='__main__':
    main()
