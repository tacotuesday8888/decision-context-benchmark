"""Synthetic hand-calculable integration checks; no project analysis imports."""
import math
from pathlib import Path
import json
import independent_math as m


def row(identity,group,label,prediction=None,config='X',condition='task',pair=None,supported=True):
    return {'id':identity,'source':'synthetic','group':group,'gold':label,'upstream_label':label,
        'config':config,'condition':condition,'split':'confirmation','pair_id':pair,
        'coverage_supported':supported,'status':'ok' if prediction is not None else 'unsupported',
        'valid':prediction is not None,'prediction':prediction,'score':None,
        'review_subgroups':{'instruction_type':'fixture'}}


def run():
    passed=[]
    rows=[row('a','A',0,1),row('b','A',0,0),row('c','B',0,supported=False),row('d','B',1,1)]
    c=m.classification(rows)
    assert c['group_class_balanced_error']['estimate']==.25
    assert c['group_class_balanced_error_bounds_planned']==[.125,.375]
    assert c['raw_accuracy_bounds_planned']==[.5,.75] and c['fpr']==.5 and c['fnr']==0
    passed.append({'fixture':'classification with unequal groups and missing denominator','balanced_error':.25,'bounds':[.125,.375]})
    pairrows=[row('n','p',0,0,pair='p'),row('p','p',1,1,pair='p'),row('orphan','orphan',0,1,pair='orphan')]
    pairs=m.source_pairs(pairrows)
    assert pairs['planned_complete_source_pairs']==1 and pairs['source_pair_ids_with_attrition_or_nonbinary_pair']==1
    assert pairs['both_correct_fraction_valid_pairs']==1 and pairs['gold_0_to_gold_1_prediction_transitions']=={'0->1':1}
    passed.append({'fixture':'explicit sourcepairs plus orphan','both_correct':1,'orphan':1})
    route=[]
    for config in ('X','Y'):
        for identity,label,pair in (('a',0,'p1'),('b',1,'p1'),('c',0,'p2'),('d',1,'p2'),('e',0,'orphan')):
            supported=not(config=='Y' and identity=='c')
            prediction=label if supported else None
            route.append(row(identity,pair,label,prediction,config=config,pair=pair,supported=supported))
    comparisons,intersection=m.route_tables(route)
    assert len(comparisons)==1 and comparisons[0]['shared_planned_rows_before_pair_attrition']==5
    assert comparisons[0]['shared_planned_rows_intact_pairs']==4 and comparisons[0]['shared_supported_rows_intact_pairs']==2
    assert comparisons[0]['shared_valid_rows_intact_pairs']==2 and comparisons[0]['orphan_explicit_pair_ids_excluded']==1
    assert intersection[0]['common_valid_rows_intact_pairs']==2
    passed.append({'fixture':'common route coverage preserves pairs','shared':5,'intact_planned':4,'supported':2,'valid':2})
    for n in (9,10):
        subgroup=[]
        for g in range(n):
            for y in (0,1):
                for condition in ('format','task'):
                    subgroup.append(row(f'{g}:{y}',str(g),y,y,condition=condition))
        check=m.subgroups(subgroup,'format','task',bootstrap=20000,randomization=100000,seed=m.SEED)[0]
        assert (check['contrast'] is not None)==(n==10)
        if n==10:assert check['contrast']['group_class_balanced_error_difference']['estimate']==0
    passed.append({'fixture':'locked reviewer support gate','nine_groups':'no contrast','ten_groups':'numerical descriptive contrast'})
    planned=[];records=[]
    for config in ('jev_firstparty','luna_decisions'):
        for group in range(20):
            for label in (0,1):
                for condition in ('format','task','reminder','length'):
                    identity=f'fixture:{group}:{label}'
                    prediction=(1-label if condition=='format' else 1 if condition=='reminder' else label)
                    p=row(identity,f'g{group:02}',label,config=config,condition=condition,pair=f'pair:{group}')
                    p['source']='browsesafe';p['inference_eligible']=True
                    planned.append(p)
                    records.append({'id':identity,'config':config,'condition':condition,'status':'ok','valid':True,
                        'prediction':prediction,'score':.9 if prediction else .1,'attempt':0})
    analysis=m.recompute(planned,records)
    exact=2/(2**20)
    assert analysis['planned_cells']==320 and analysis['observed_cells']==320
    assert len(analysis['primary_six_test_family'])==6
    for contrast in analysis['primary_six_test_family']:
        target={'format':1.,'reminder':.5,'length':0.}[contrast['control']]
        assert contrast['estimate']==target
        assert contrast['raw_p']==(1. if target==0 else exact)
        assert contrast['p_holm']==(1. if target==0 else 6*exact)
    for stratum in analysis['strata']:
        conditions={r['condition']:r for r in stratum['conditions']}
        assert conditions['task']['raw_accuracy']==1 and conditions['format']['raw_accuracy']==0
        assert conditions['reminder']['raw_accuracy']==.5
        assert conditions['task']['source_pairs']['both_correct_source_pairs']==20
        assert math.isclose(conditions['task']['native_scores']['brier'],.01)
        assert conditions['task']['native_scores']['auroc']==1
        assert conditions['format']['native_scores']['auroc']==0
        for c in stratum['contrasts']:
            point={'format':1.,'reminder':.5,'length':0.}[c['control']]
            assert c['group_class_balanced_error_difference']['interval_95']==[point,point]
            assert c['complete_explicit_sourcepair_sensitivity']['same_rows_as_primary']
    passed.append({'fixture':'full 20-component/2-route/4-condition integration','planned_cells':320,
        'effects':[1.,.5,0.],'nonzero_exact_p':exact,'nonzero_holm_p':6*exact,'bootstrap_draws':20000})
    # Join must retain an unsupported planned cell and reject missing-denominator
    # tricks such as duplicate or nonconfirmation observations.
    p=row('missing','M',0,supported=False);p['inference_eligible']=False
    joined=m.join([p],[])
    assert len(joined)==1 and joined[0]['status']=='unsupported'
    try:m.join([p,p],[])
    except ValueError:pass
    else:raise AssertionError('duplicate plan accepted')
    passed.append({'fixture':'strict join retains unsupported denominator and rejects duplicates','planned':1,'valid':0})
    return {'version':'independent-math-extended-synthetic-fixtures-1','checks_passed':True,
        'empirical_inputs_read':False,'project_analytical_functions_imported':False,'fixtures':passed}


if __name__=='__main__':
    report=run()
    m.immutable(Path(__file__).parent/'extended-fixture-results.json',report)
    print(json.dumps({'checks_passed':report['checks_passed'],'fixture_count':len(report['fixtures'])}))
