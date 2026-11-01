"""Assemble and check an inert future-run manifest from locked acquired inputs.

This command makes no network calls, loads no model weights and cannot authorize
inference. Historical accounting is replayed read-only without creating its lock.
"""
from __future__ import annotations
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.study_v7.external_data import ROOT, RAW, OUT, CANONICAL, save
from scripts.study_v7.requests import build_plan, canonical, digest, PANEL
from scripts.study_v6.accounting import BudgetLedger, amount, money, PROVIDERS, verify_history

EXPECTED = {'jev_firstparty':29300,'luna_decisions':29300,'luna_responses':5900,
            'sol_subscription':6000,'protectai_local':5200}


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines() if line]


def historical_accounting(root=CANONICAL):
    path=root/'data/raw/study-v6/execution-v1/budget.jsonl'
    # __init__/snapshot open a write-capable historical lock, so use the pure
    # validated journal replay and totals directly. No canonical file is opened
    # for writing and no response/accuracy artifact is read.
    ledger=object.__new__(BudgetLedger)
    ledger.path=path
    ledger._cache=None
    state=ledger._read()
    if state is None:
        raise ValueError('Historical spending journal absent')
    prior_receipt=state['policy']['prior_receipt']
    verify_history(prior_receipt,root)
    incremental,_=BudgetLedger._totals(state)
    prior={p:amount(money(state['policy']['prior_accounted_usd'][p])+incremental[p]) for p in PROVIDERS}
    expected={'openai':'7.0275592','typesafe':'1.827584934'}
    if any(abs(Decimal(prior[p])-Decimal(expected[p]))>Decimal('1e-12') for p in PROVIDERS):
        raise ValueError('Historical spending changed; independently reconcile before a new run')
    return {'prior_accounted_usd':prior,
        'evidence_sha256':{**prior_receipt['evidence_sha256'],str(path.relative_to(root)):digest(path.read_bytes())},
        'unknown_charge_entries_held':sum(e['status']=='unknown_usage' for e in state['entries'].values()),
        'pending_entries_held':sum(e['status'] in ('reserved','dispatched') for e in state['entries'].values()),
        'historical_journal_head_sha256':state['head_sha256'],
        'is_invoice_balance':False,'no_canonical_writes':True,
        'precision_note':'Preserves inherited conservative decimal literals, including the historical 0.00000000000000006 TypeSafe float artifact; planning rounded only that immaterial tail.'}


def assemble():
    main=json.loads((OUT/'main-selection.json').read_text())
    external=json.loads((OUT/'external-selection-v3.json').read_text())
    if not main['target_met'] or (main['development_groups'],main['confirmation_groups'])!=(200,3000):
        raise ValueError('Main target not attained; issue incomplete readiness instead of changing target')
    main_rows=read_rows(RAW/'main-selected.jsonl')
    external_rows=read_rows(RAW/'external-selected-v3.jsonl')
    for name,sha in external['artifacts'].items():
        if digest((RAW/name).read_bytes())!=sha:
            raise ValueError('External source/selection evidence changed')
    for item in main['outputs'].values():
        if digest((ROOT/item['path']).read_bytes())!=item['sha256']:
            raise ValueError('Main source/selection evidence changed')
    if Counter((r['partition'],r['upstream_label']) for r in external_rows)!={
        ('development',0):50,('development',1):50,('confirmation',0):2000,('confirmation',1):2000}:
        raise ValueError('External balanced quotas differ')
    if len({r['group_id'] for r in external_rows})!=4100:
        raise ValueError('External components were reused')
    subsets=main['subsets']
    selection={'general_groups':subsets['general'],'native_repeat_groups':subsets['repeat_native'],
        'general_repeat_groups':subsets['repeat_general'],'audit_groups':subsets['audit'],
        'development_execution_groups':subsets['development_execute'],
        'external_general_ids':[r['id'] for r in external_rows if r['general_subset'] and r['partition']=='confirmation']}
    plan=build_plan(main_rows,external_rows,selection,sol_config='sol_subscription')
    if plan['subsets']['development_execution_groups']!=subsets['development_execute']:
        raise ValueError('Main development execution subset changed between selection and requests')
    if plan['counts']!=EXPECTED:
        raise ValueError('Protocol request counts differ: '+str(plan['counts']))
    plan_body=canonical(plan)+b'\n'
    save(RAW/'request-plan.json',plan_body)
    manifest={'version':'study-v7-run-1','status':'offline_prepared_inference_paused',
        'experimental_inference_authorized':False,
        'plan_path':'data/raw/study-v7/request-plan.json','plan_sha256':digest(plan_body),
        'source_files':[{'path':str((RAW/name).relative_to(ROOT)),'sha256':digest((RAW/name).read_bytes())}
                        for name in ('main-selected.jsonl','external-selected-v3.jsonl')],
        'source_selection_receipts':{str((OUT/name).relative_to(ROOT)):digest((OUT/name).read_bytes())
                                    for name in ('main-selection.json','external-selection-v3.json','main-external-v3-equivalence.json')},
        'historical_accounting':historical_accounting(),
        'authorization_path':'results/study-v7/run-authorization.json',
        'route_validation':{'completed':False,'plan_sha256':digest(plan_body),'validated_configurations':[],
            'limitation':'Requires later explicitly authorized development; no inference was performed in preparation.'},
        'counts':plan['counts'],'paid_calls':64500,'subscription_calls':6000,'local_records':5200,
        'execution_profile':plan['execution_profile'],'active_configurations':plan['active_configurations'],
        'model_configurations':plan['model_configurations'],
        'execution_code_sha256':{str(path.relative_to(ROOT)):digest(path.read_bytes())
                                for path in sorted((ROOT/'scripts').rglob('*.py'))},
        'current_cumulative_caps_usd':{'openai':'357.0275592','typesafe':'21.82758493400000006'},
        'owner_bounded_execution_authorized':True,'allow_paid_sol_api':False,
        'authorization_reference':'docs/study-v7/RUN-AUTHORIZATION.md',
        'route_amendment_reference':'docs/study-v7/ROUTE-AMENDMENT.md'}
    body=json.dumps(manifest,indent=2,sort_keys=True).encode()+b'\n'
    path=OUT/'run-manifest.json'
    if path.exists() and path.read_bytes()!=body:
        # Pre-inference code fixes may refresh the offline lock; preserve each old
        # lock as ignored metadata. Cohort/request bytes above remain immutable.
        save(RAW/'preparation-lock-history'/(digest(path.read_bytes())+'.json'),path.read_bytes())
        if (RAW/'execution-v1').exists():
            raise ValueError('Cannot refresh a manifest once execution evidence exists')
        path.write_bytes(body)
    else:
        save(path,body)
    summary={'version':'study-v7-request-summary-1','inference_authorized':False,
        'counts':plan['counts'],'paid_calls':64500,'subscription_calls':6000,'local_records':5200,
        'plan_sha256':digest(plan_body),'run_manifest_sha256':digest(body),
        'allocation_counts':{name:dict(Counter(plan['requests'][key]['config'] for group in groups for key in group['request_keys']))
                             for name,groups in plan['schedules'].items()},
        'subset_sizes':{key:len(value) for key,value in plan['subsets'].items()}}
    # Summary is derived metadata; keep it in sync with the final pre-inference lock.
    (OUT/'request-summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    return summary


def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    print(json.dumps(assemble(),indent=2))


if __name__=='__main__':
    main()
