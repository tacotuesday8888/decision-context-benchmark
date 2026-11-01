"""Offline checks of public-to-private delivery metadata; optional ignored data checks."""
from __future__ import annotations
import argparse
from collections import Counter
from decimal import Decimal
import json
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]))
from scripts.study_v7.requests import digest, PANEL
from scripts.study_v7.external_data import ROOT, OUT, RAW, REV, TEST_SHA


def require(value,message):
    if not value:
        raise ValueError(message)


def check_metadata():
    main=json.loads((OUT/'main-selection.json').read_text())
    external=json.loads((OUT/'external-selection-v3.json').read_text())
    manifest=json.loads((OUT/'run-manifest.json').read_text())
    summary=json.loads((OUT/'request-summary.json').read_text())
    forecast=json.loads((OUT/'forecast-v2.json').read_text())
    require(main['target_met'] and main['development_groups']==200 and main['confirmation_groups']==3000,'Main target differs')
    require(main['selected_pages']==6400 and main['source_labels_preserved'] is True,'Main source labels/pages differ')
    by_group={}
    for row in main['selected']:
        by_group.setdefault(row['group_id'],[]).append(row)
    require(len(by_group)==3200,'Main components reused')
    for rows in by_group.values():
        require(len(rows)==2 and {r['upstream_label'] for r in rows}=={0,1},'Main complete source pair differs')
        require(len({r['partition'] for r in rows})==1,'Main component crosses partition')
    confirmation={g for g,rs in by_group.items() if rs[0]['partition']=='confirmation'}
    subsets=main['subsets']
    require(len(subsets['audit'])==100 and set(subsets['audit'])<=confirmation,'Fixed audit differs')
    require(len(subsets['general'])==500 and set(subsets['general'])<=confirmation,'General subset differs')
    require(len(subsets['repeat_native'])==100 and set(subsets['repeat_native'])<=confirmation,'Native repeat subset differs')
    require(len(subsets['repeat_general'])==50 and set(subsets['repeat_general'])<=set(subsets['general']),'General repeat nesting differs')
    require(external['revision']==REV,'External revision differs')
    test_receipt=next(r for r in external['source_receipts'] if r['file']=='test.json')
    require(test_receipt['sha256']==TEST_SHA and test_receipt['rows']==23516,'Pinned released test differs')
    require(Counter((r['partition'],r['upstream_label']) for r in external['selected'])=={
        ('development',0):50,('development',1):50,('confirmation',0):2000,('confirmation',1):2000},'External quotas differ')
    require(len({r['group_id'] for r in external['selected']})==4100,'External component reused')
    require(Counter(r['upstream_label'] for r in external['selected'] if r['general_subset'] and r['partition']=='confirmation')=={0:500,1:500},'External general nesting differs')
    require(manifest['counts']==summary['counts']==forecast['counts'],'Request counts disagree')
    require(manifest['plan_sha256']==summary['plan_sha256']==forecast['plan_sha256'],'Exact plan byte hashes disagree')
    require(digest((OUT/'run-manifest.json').read_bytes())==summary['run_manifest_sha256'],'Run manifest lock differs')
    for name,sha in manifest['source_selection_receipts'].items():
        require(digest((ROOT/name).read_bytes())==sha,'Selection/equivalence receipt differs: '+name)
    for name,sha in manifest['execution_code_sha256'].items():
        require(digest((ROOT/name).read_bytes())==sha,'Execution code lock differs: '+name)
    for scenario, costs in forecast['cost_scenarios_usd'].items():
        by_config={k:Decimal(v) for k,v in costs.items() if k in PANEL}
        oa=sum((v for k,v in by_config.items() if PANEL[k]['provider']=='openai'),Decimal(0))
        ts=sum((v for k,v in by_config.items() if PANEL[k]['provider']=='typesafe'),Decimal(0))
        require(oa==Decimal(costs['openai_total']) and ts==Decimal(costs['typesafe_total']),'Forecast provider arithmetic differs: '+scenario)
        require(oa+ts==Decimal(costs['all_tests_total']),'Forecast total differs: '+scenario)
    simulation=json.loads((OUT/'statistical-simulation.json').read_text())
    require(simulation['model_calls']==0 and len(simulation['scenarios'])>=15,'Synthetic validation missing')
    template=json.loads((OUT/'run-authorization.json').read_text())
    require(template['experimental_inference_authorized'] is False,'Default authorization template must remain inert')
    return {'main_groups':3200,'main_pages':6400,'external_confirmation':4000,'external_development':100,
            'request_counts':manifest['counts'],'offline':True,'model_calls':0}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--with-raw',action='store_true')
    args=parser.parse_args()
    result=check_metadata()
    if args.with_raw:
        from scripts.study_v7.main_data import verify_locked
        from scripts.study_v7.run import verify_manifest
        verify_locked()
        verify_manifest(OUT/'run-manifest.json')
        external=json.loads((OUT/'external-selection-v3.json').read_text())
        for name,sha in external['artifacts'].items():
            require(digest((RAW/name).read_bytes())==sha,'Ignored external evidence differs')
        require(digest((RAW/'token-audit-v2.jsonl').read_bytes())==json.loads((OUT/'forecast-v2.json').read_text())['token_audit_sha256'],'Ignored token audit differs')
        result['ignored_artifacts_verified']=True
    print(json.dumps(result,indent=2))


if __name__=='__main__':
    main()
