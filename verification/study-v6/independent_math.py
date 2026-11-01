"""Independent recomputation of the frozen DCB v6 arithmetic.

No import of project analytical code. No provider or source-corpus access. The CLI
allows only synthetic fixtures until root supplies a terminal authorization bound
to input hashes and this pre-empirical tool/fixture freeze.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

import numpy as np

SEED=20261031
B=20000
R=100000
FAMILY=6
HERE=Path(__file__).resolve().parent


def binary(x):
    return type(x) in (int,bool) and x in (0,1)


def good(r):
    return r.get('status')=='ok' and r.get('valid') is True and binary(r.get('prediction'))


def score(x):
    return type(x) in (int,float) and math.isfinite(x) and 0<=x<=1


def pooled_components(values,groups,labels):
    totals=defaultdict(list)
    for x,g,y in zip(values,groups,labels):
        if not binary(y) or not isinstance(g,str) or not g or not math.isfinite(x):
            raise ValueError('Invalid component observation')
        totals[(g,int(y))].append(float(x))
    names=sorted(set(groups))
    cells={g:{y:math.fsum(totals[(g,y)])/len(totals[(g,y)]) for y in (0,1) if (g,y) in totals} for g in names}
    support={y:sum(y in cells[g] for g in names) for y in (0,1)}
    means={y:math.fsum(cells[g][y] for g in names if y in cells[g])/support[y] if support[y] else None for y in (0,1)}
    result={'estimate':sum(means.values())/2 if all(support.values()) else None,
            'groups':len(names),'class_groups':{str(y):support[y] for y in (0,1)},
            'class_estimates':{str(y):means[y] for y in (0,1)},'rows':len(values)}
    return result,names,cells,support


def balanced(values,groups,labels):
    return pooled_components(values,groups,labels)[0]


def infer(values,groups,labels,bootstrap=B,randomization=R,seed=SEED):
    result,names,cells,support=pooled_components(values,groups,labels)
    n=len(names)
    result.update(seed=seed,bootstrap_draws=bootstrap,bootstrap_degenerate_draws=0,bootstrap_valid_draws=0,
        interval_95=None,interval_99_1667=None,randomization_p_two_sided=None,
        randomization_draws=0,randomization_method=None,descriptive_only=n<20,
        individual_group_class_effects=[{'group':g,'class_0':cells[g].get(0),'class_1':cells[g].get(1)} for g in names])
    if result['estimate'] is None:
        result['inference_status']='missing_gold_class'
        return result
    contributions=np.asarray([math.fsum(cells[g][y]/support[y] for y in cells[g])/2 for g in names],float)
    nonzero=contributions[contributions!=0]
    k=len(nonzero)
    result['randomization_nonzero_component_contributions']=k
    observed=abs(float(np.sum(contributions)))
    if k<=20:
        # Independent meet-in-the-middle enumeration, rather than a bit-matrix
        # implementation. Every sign combination is counted once.
        cut=k//2
        def sums(weights):
            out=np.asarray([0.])
            for weight in weights:
                out=np.concatenate((out-weight,out+weight))
            return out
        a,b=sums(nonzero[:cut]),sums(nonzero[cut:])
        extreme=0
        for start in range(0,len(a),128):
            extreme+=int(np.count_nonzero(np.abs(a[start:start+128,None]+b[None,:])>=observed-1e-12))
        result.update(randomization_p_two_sided=extreme/(1<<k),randomization_draws=1<<k,
                      randomization_method='exact whole-component sign enumeration')
    else:
        random=np.random.default_rng(seed)
        extreme=0
        for start in range(0,randomization,512):
            count=min(512,randomization-start)
            signs=random.integers(0,2,size=(count,k),dtype=np.int8)*2-1
            extreme+=int(np.count_nonzero(np.abs(signs@nonzero)>=observed-1e-12))
        result.update(randomization_p_two_sided=(extreme+1)/(randomization+1),randomization_draws=randomization,
                      randomization_method='Monte Carlo whole-component signs, +1 correction')
    # Resample component multiplicities, then weight precomputed class means.
    # This independently reconstructs denominators instead of indexing an array
    # of row effects and calling an analytical helper.
    present=np.asarray([[int(y in cells[g]) for y in (0,1)] for g in names],float)
    means=np.asarray([[cells[g].get(y,0.) for y in (0,1)] for g in names],float)
    random=np.random.default_rng(seed+1)
    draws=[]
    for start in range(0,bootstrap,256):
        chosen=random.integers(0,n,size=(min(256,bootstrap-start),n))
        weights=np.asarray([np.bincount(row,minlength=n) for row in chosen],float)
        denominators=weights@present
        keep=np.all(denominators>0,axis=1)
        result['bootstrap_degenerate_draws']+=int(np.sum(~keep))
        if np.any(keep):
            values_by_class=(weights[keep]@means)/denominators[keep]
            draws.extend(((values_by_class[:,0]+values_by_class[:,1])/2).tolist())
    result['bootstrap_valid_draws']=len(draws)
    if draws:
        result['interval_95']=np.quantile(draws,[.025,.975]).tolist()
        result['interval_99_1667']=np.quantile(draws,[.05/12,1-.05/12]).tolist()
    result['inference_status']='descriptive_fewer_than_20_groups' if n<20 else 'source_conditional'
    return result


def holm(values):
    order=sorted(range(len(values)),key=lambda i:(1 if values[i] is None else values[i],i))
    adjusted=[None]*len(values);high=0.
    for rank,i in enumerate(order):
        high=max(high,min(1.,(1 if values[i] is None else values[i])*(len(values)-rank)))
        if values[i] is not None:adjusted[i]=high
    return [{'p':p,'p_holm':a,'reject_holm_05':a is not None and a<=.05} for p,a in zip(values,adjusted)]


def join(planned,records):
    table={}
    signatures={}
    for r in planned:
        key=(r['id'],r['config'],r['condition'])
        if key in table:raise ValueError('Duplicate planned cell')
        if r.get('split',r.get('split_proposal','confirmation'))!='confirmation':raise ValueError('Development contamination')
        y=r.get('gold',r.get('semantic_gold'))
        if not binary(y):raise ValueError('Invalid admitted label')
        signature=tuple(json.dumps(r.get(k),sort_keys=True) for k in ('source','group','pair_id','upstream_label','review_subgroups'))+(int(y),)
        if r['id'] in signatures and signatures[r['id']]!=signature:raise ValueError('Changed source invariants')
        signatures[r['id']]=signature
        supported=r.get('coverage_supported')
        if supported is None:supported=r.get('coverage_status') in (None,'supported','full_input_supported','ok','complete','complete_windowed','full_input_server_gate')
        table[key]=dict(r,gold=int(y),coverage_supported=bool(supported),status='not_attempted' if supported else 'unsupported',valid=False,prediction=None,score=None)
    seen=set()
    for original in records:
        r=dict(original)
        if 'parsed' in r:r.update(r.pop('parsed'))
        key=(r['id'],r['config'],r['condition'])
        if key not in table or key in seen:raise ValueError('Unplanned or duplicate observation')
        seen.add(key)
        if table[key].get('inference_eligible') is False or r.get('attempt',0)!=0:raise ValueError('Ineligible/recovery primary evidence')
        if not r.get('status') or r['status'] in ('pending','reserved','in_flight','started','running'):raise ValueError('Nonterminal observation')
        if r.get('valid') is True and not good(r):raise ValueError('Invalid valid flag')
        if r.get('score') is not None and not score(r['score']):raise ValueError('Invalid probability')
        if r['config'] in ('luna_chat','astra_chat') and r.get('score') is not None:raise ValueError('Invented chat confidence')
        if r['status']=='tie' and (r.get('score')!=.5 or r.get('valid') is True):raise ValueError('Tie must abstain')
        if r['status']=='ok' and r.get('score') is not None:
            if r['score']==.5 or int(r['prediction'])!=int(r['score']>.5):raise ValueError('Changed threshold')
        table[key].update({k:r[k] for k in ('status','valid','prediction','score') if k in r})
    return [table[k] for k in sorted(table)]


def classification(rows):
    valid=[r for r in rows if good(r)]
    bylabel={y:[r for r in valid if r['gold']==y] for y in (0,1)}
    fp=sum(r['prediction']==1 for r in bylabel[0]);fn=sum(r['prediction']==0 for r in bylabel[1])
    correct=len(valid)-fp-fn
    groups=[r['group'] for r in rows];labels=[r['gold'] for r in rows]
    errors=[float(r['prediction']!=r['gold']) if good(r) else None for r in rows]
    accepted_errors=[float(r['prediction']!=r['gold']) for r in valid]
    agreed=[r for r in valid if binary(r.get('upstream_label'))]
    return {'planned_rows':len(rows),'planned_groups':len(set(groups)),
        'planned_class_rows':dict(Counter(str(y) for y in labels)),
        'full_input_gate_supported_rows':sum(r['coverage_supported'] for r in rows),
        'provisional_server_gate_rows':sum(r['coverage_supported'] and r.get('coverage_status')=='full_input_server_gate' for r in rows),
        'valid_rows':len(valid),'status_counts':dict(Counter(r['status'] for r in rows)),
        'valid_negative_rows':len(bylabel[0]),'valid_positive_rows':len(bylabel[1]),
        'false_positives':fp,'false_negatives':fn,'fpr':fp/len(bylabel[0]) if bylabel[0] else None,
        'fnr':fn/len(bylabel[1]) if bylabel[1] else None,'raw_accuracy':correct/len(valid) if valid else None,
        'raw_accuracy_bounds_planned':[correct/len(rows),(correct+len(rows)-len(valid))/len(rows)] if rows else None,
        'group_class_balanced_error':balanced(accepted_errors,[r['group'] for r in valid],[r['gold'] for r in valid]),
        'group_class_balanced_error_bounds_planned':[balanced([fallback if x is None else x for x in errors],groups,labels)['estimate'] for fallback in (0,1)],
        'source_label_agreement':{'valid_rows':len(agreed),'agreement':sum(r['prediction']==r['upstream_label'] for r in agreed)/len(agreed) if agreed else None}}


def forecasts(rows):
    selected=[r for r in rows if r['status'] in ('ok','tie') and score(r.get('score'))]
    if not selected:return {'score_rows':0,'brier':None,'auroc':None,'reliability':[]}
    ordered=sorted(selected,key=lambda r:r['score']);np_=sum(r['gold']==1 for r in ordered);nn=len(ordered)-np_
    rank_sum=0.;i=0
    while i<len(ordered):
        j=i+1
        while j<len(ordered) and ordered[j]['score']==ordered[i]['score']:j+=1
        rank_sum+=sum(r['gold']==1 for r in ordered[i:j])*(i+1+j)/2
        i=j
    bins=[]
    for k in range(10):
        members=[r for r in selected if min(9,int(r['score']*10))==k]
        bins.append({'lower':k/10,'upper':(k+1)/10,'rows':len(members),
            'mean_score':math.fsum(r['score'] for r in members)/len(members) if members else None,
            'observed_positive_fraction':sum(r['gold'] for r in members)/len(members) if members else None})
    return {'score_rows':len(selected),'brier':math.fsum((r['score']-r['gold'])**2 for r in selected)/len(selected),
        'auroc':(rank_sum-np_*(np_+1)/2)/(np_*nn) if np_ and nn else None,
        'positive_score_rows':np_,'negative_score_rows':nn,'reliability':bins}


def source_pairs(rows):
    members=defaultdict(list)
    for r in rows:
        if r.get('pair_id') is not None:members[str(r['pair_id'])].append(r)
    orphan=0;planned=0;complete=0;both=0;trans=Counter()
    for pair in members.values():
        if len(pair)!=2 or {r['gold'] for r in pair}!={0,1}:orphan+=1;continue
        planned+=1
        if all(good(r) for r in pair):
            complete+=1;both+=all(r['prediction']==r['gold'] for r in pair)
            by={r['gold']:r for r in pair};trans[f"{int(by[0]['prediction'])}->{int(by[1]['prediction'])}"]+=1
    return {'planned_complete_source_pairs':planned,'source_pair_ids_with_attrition_or_nonbinary_pair':orphan,
        'valid_complete_source_pairs':complete,'both_correct_source_pairs':both,
        'both_correct_fraction_valid_pairs':both/complete if complete else None,
        'both_correct_fraction_planned_bounds':[both/planned,(both+planned-complete)/planned] if planned else None,
        'gold_0_to_gold_1_prediction_transitions':dict(sorted(trans.items()))}


def contrast(rows,control,target,bootstrap=B,randomization=R,seed=SEED):
    index={(r['id'],r['condition']):r for r in rows}
    ids=sorted({r['id'] for r in rows if r['condition'] in (control,target)})
    values=[];groups=[];labels=[];lo=[];hi=[];complete=[];trans=Counter();by_pair=defaultdict(list);singletons=0
    for i in ids:
        if (i,control) not in index or (i,target) not in index:raise ValueError('Unpaired planned condition schedule')
        a,b=index[(i,control)],index[(i,target)]
        ea=float(a['prediction']!=a['gold']) if good(a) else None
        eb=float(b['prediction']!=b['gold']) if good(b) else None
        groups.append(a['group']);labels.append(a['gold'])
        lo.append((0 if ea is None else ea)-(1 if eb is None else eb))
        hi.append((1 if ea is None else ea)-(0 if eb is None else eb))
        if ea is not None and eb is not None:
            complete.append((ea-eb,a['group'],a['gold']));trans[f'{int(ea)}->{int(eb)}']+=1
        if a.get('pair_id') is None:singletons+=1
        else:by_pair[str(a['pair_id'])].append((a,b))
    def estimate(items):
        return infer([r[0] for r in items],[r[1] for r in items],[r[2] for r in items],bootstrap,randomization,seed)
    primary=estimate(complete)
    orphan=0;planned=0;paired_complete=0;sensitivity=[]
    for pair in by_pair.values():
        if len(pair)!=2 or {a['gold'] for a,b in pair}!={0,1}:orphan+=1;continue
        planned+=1
        if all(good(r) for ab in pair for r in ab):
            paired_complete+=1
            sensitivity.extend((float(a['prediction']!=a['gold'])-float(b['prediction']!=b['gold']),a['group'],a['gold']) for a,b in pair)
    return {'control':control,'task':target,'planned_paired_rows':len(ids),'schedule_unpaired_rows':0,
        'complete_paired_rows':len(complete),'planned_groups':len(set(groups)),
        'complete_groups':len({r[1] for r in complete}),'complete_class_rows':dict(Counter(str(r[2]) for r in complete)),
        'group_class_balanced_error_difference':primary,
        'planned_denominator_bounds':[balanced(x,groups,labels)['estimate'] for x in (lo,hi)],
        'paired_error_transitions':{k:trans[k] for k in ('0->0','0->1','1->0','1->1')},
        'source_pair_attrition':{'planned_complete_explicit_pairs':planned,'valid_complete_explicit_pairs_in_both_conditions':paired_complete,
            'explicit_pair_ids_with_planned_member_attrition':orphan,'rows_without_explicit_source_pair':singletons},
        'complete_explicit_sourcepair_sensitivity':{'rows':len(sensitivity),'same_rows_as_primary':len(sensitivity)==len(complete),
            'group_class_balanced_error_difference':primary if len(sensitivity)==len(complete) else estimate(sensitivity)},
        'raw_paired_error_difference':math.fsum(r[0] for r in complete)/len(complete) if complete else None}


def subgroups(rows,control,target,**options):
    categories=defaultdict(set)
    for r in rows:
        for field,value in r.get('review_subgroups',{}).items():
            if isinstance(value,(str,int,bool)) and str(value):categories[(field,str(value))].add(r['id'])
    out=[]
    for (field,value),ids in sorted(categories.items()):
        members=[r for r in rows if r['id'] in ids]
        support={str(y):len({r['group'] for r in members if r['condition']==target and r['gold']==y}) for y in (0,1)}
        allowed=min(support.values())>=10
        out.append({'reviewer_field':field,'value':value,'planned_class_groups':support,
            'status':'preinference_diagnostic' if allowed else 'insufficient_groups_per_class',
            'contrast':contrast(members,control,target,**options) if allowed else None})
    return out


def common_ids(part,configs):
    lookup={(r['config'],r['id']):r for r in part}
    byconfig={c:{r['id'] for r in part if r['config']==c} for c in configs}
    shared=sorted(set.intersection(*(byconfig[c] for c in configs)))
    blocks=defaultdict(list)
    for identity in shared:
        r=lookup[(configs[0],identity)]
        key=('singleton',identity) if r.get('pair_id') is None else ('pair',str(r['pair_id']))
        blocks[key].append(identity)
    planned=[];supported=[];accepted=[];orphans=0
    for (kind,_),ids in blocks.items():
        if kind=='pair' and (len(ids)!=2 or {lookup[(configs[0],i)]['gold'] for i in ids}!={0,1}):
            orphans+=1;continue
        planned.extend(ids)
        members=[lookup[(c,i)] for c in configs for i in ids]
        if all(r['coverage_supported'] for r in members):
            supported.extend(ids)
            if all(good(r) for r in members):accepted.extend(ids)
    return lookup,shared,planned,supported,accepted,orphans


def route_tables(rows):
    parts=defaultdict(list)
    for r in rows:parts[(r['source'],r['condition'])].append(r)
    comparisons=[];intersections=[]
    for (source,condition),part in sorted(parts.items()):
        configs=sorted({r['config'] for r in part})
        lookup,shared,planned,supported,accepted,orphans=common_ids(part,configs)
        first=lambda identity:lookup[(configs[0],identity)]
        intersections.append({'source':source,'condition':condition,'configs':configs,
            'common_planned_rows_before_pair_attrition':len(shared),'common_planned_rows_intact_pairs':len(planned),
            'common_supported_rows_intact_pairs':len(supported),'common_valid_rows_intact_pairs':len(accepted),
            'common_planned_groups':len({first(i)['group'] for i in planned}),
            'common_supported_groups':len({first(i)['group'] for i in supported}),
            'common_valid_groups':len({first(i)['group'] for i in accepted}),'orphan_explicit_pair_ids_excluded':orphans})
        for left,right in itertools.combinations(configs,2):
            lookup,shared,planned,supported,accepted,orphans=common_ids(part,[left,right])
            if not shared:continue
            g=lambda i:lookup[(left,i)]['group'];y=lambda i:lookup[(left,i)]['gold']
            lower=[];upper=[];differences=[]
            for i in planned:
                a,b=lookup[(left,i)],lookup[(right,i)]
                ea=float(a['prediction']!=a['gold']) if good(a) else None
                eb=float(b['prediction']!=b['gold']) if good(b) else None
                lower.append((0 if ea is None else ea)-(1 if eb is None else eb))
                upper.append((1 if ea is None else ea)-(0 if eb is None else eb))
            for i in accepted:
                a,b=lookup[(left,i)],lookup[(right,i)]
                differences.append(float(a['prediction']!=a['gold'])-float(b['prediction']!=b['gold']))
            comparisons.append({'source':source,'condition':condition,'left_config':left,'right_config':right,
                'shared_planned_rows_before_pair_attrition':len(shared),'shared_planned_rows_intact_pairs':len(planned),
                'shared_supported_rows_intact_pairs':len(supported),'shared_valid_rows_intact_pairs':len(accepted),
                'orphan_explicit_pair_ids_excluded':orphans,'shared_planned_groups':len({g(i) for i in planned}),
                'shared_valid_groups':len({g(i) for i in accepted}),
                'shared_valid_class_rows':dict(Counter(str(y(i)) for i in accepted)),
                'paired_error_difference':balanced(differences,[g(i) for i in accepted],[y(i) for i in accepted]),
                'shared_planned_denominator_bounds':[balanced(v,[g(i) for i in planned],[y(i) for i in planned])['estimate'] for v in (lower,upper)]})
    return comparisons,intersections


def recompute(planned,records,bootstrap=B,randomization=R,seed=SEED):
    rows=join(planned,records)
    parts=defaultdict(list)
    for r in rows:parts[(r['source'],r['config'])].append(r)
    strata=[];indexed={}
    options={'bootstrap':bootstrap,'randomization':randomization,'seed':seed}
    for (source,config),part in sorted(parts.items()):
        available=sorted({r['condition'] for r in part})
        if source=='spml':target='policy';controls=('format','reminder','length','candidate','scrambled')
        elif 'task_policy' in available:target='task_policy';controls=('policy','policy_reminder','policy_length','policy_scrambled')
        else:target='task';controls=('format','reminder','length','candidate','scrambled')
        contrasts=[]
        for control in controls:
            if control not in available or target not in available:continue
            value=contrast(part,control,target,**options)
            value['reviewer_subgroups']=subgroups(part,control,target,**options)
            contrasts.append(value);indexed[(source,config,control,target)]=value
        strata.append({'source':source,'config':config,'conditions':[
            {'condition':c,**classification([r for r in part if r['condition']==c]),
             'source_pairs':source_pairs([r for r in part if r['condition']==c]),
             'native_scores':forecasts([r for r in part if r['condition']==c])} for c in available],
            'contrasts':contrasts})
    family=[]
    for config in ('jev_firstparty','luna_decisions'):
        for control in ('format','reminder','length'):
            pair=indexed.get(('browsesafe',config,control,'task'))
            v=pair['group_class_balanced_error_difference'] if pair else None
            family.append({'source':'browsesafe','config':config,'control':control,'task':'task',
                'status':v['inference_status'] if v else 'unrun','estimate':v['estimate'] if v else None,
                'raw_p':v['randomization_p_two_sided'] if v else None,
                'descriptive_only':v['descriptive_only'] if v else True})
    adjusted=holm([None if r['descriptive_only'] else r['raw_p'] for r in family])
    for r,a in zip(family,adjusted):r.update(a)
    routes,coverage=route_tables(rows)
    return {'version':'v6-analysis-1','analysis_set':'first_attempt_primary','planned_cells':len(rows),'observed_cells':len(records),
        'analysis_plan':{'bootstrap_draws':bootstrap,'randomization_draws':randomization,'seed':seed,
            'primary_family_size':6,'family_alpha':.05,'native_threshold':.5,
            'pointwise_interval_level':.95,'bonferroni_interval_level':1-.05/6},
        'strata':strata,'primary_six_test_family':family,'route_comparisons':routes,'coverage_intersections':coverage}


def compare(expected,actual,path='$',counts=None,mismatches=None,tolerance=1e-10):
    counts=Counter() if counts is None else counts
    mismatches=[] if mismatches is None else mismatches
    def fail(reason):mismatches.append({'path':path,'reason':reason,'expected':expected,'actual':actual})
    if isinstance(expected,dict):
        if not isinstance(actual,dict):fail('object type');return counts,mismatches
        for key,value in expected.items():
            if key not in actual:mismatches.append({'path':path+'.'+key,'reason':'missing checked field'})
            else:compare(value,actual[key],path+'.'+key,counts,mismatches,tolerance)
    elif isinstance(expected,list):
        if not isinstance(actual,list) or len(expected)!=len(actual):fail('list length/type');return counts,mismatches
        for i,(a,b) in enumerate(zip(expected,actual)):compare(a,b,f'{path}[{i}]',counts,mismatches,tolerance)
    else:
        counts['checked_leaves']+=1
        if expected is None:
            if actual is not None:fail('null disposition')
        elif type(expected) is bool:
            if type(actual) is not bool or actual!=expected:fail('boolean')
        elif type(expected) in (int,float):
            counts['numeric_leaves']+=1
            if type(actual) not in (int,float) or not math.isfinite(actual) or not math.isclose(expected,actual,rel_tol=tolerance,abs_tol=tolerance):fail('number')
        elif actual!=expected:fail('categorical/identifier')
    return counts,mismatches


def canonical(value):
    return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'),allow_nan=False).encode()


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def immutable(path,value):
    body=canonical(value)+b'\n';path=Path(path)
    if path.exists():
        if path.read_bytes()!=body:raise ValueError('Refuse to overwrite conflicting independent evidence')
        return
    with path.open('xb') as handle:handle.write(body)


def load_rows(path):
    return [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]


def fixture_checks():
    # Every value below is hand-constructed synthetic material, never a source
    # benchmark row or an evaluated model response.
    evidence=[]
    v=[0,0,1,1];g=['large','large','small','small'];y=[0,0,0,1]
    b=balanced(v,g,y)
    assert b['estimate']==.75 and b['class_estimates']=={'0':.5,'1':1.}
    evidence.append({'fixture':'unequal component/class weights','expected':.75,'actual':b['estimate']})
    x=infer([1,1],['a','b'],[0,1],bootstrap=20000)
    assert x['estimate']==1 and x['randomization_p_two_sided']==.5
    assert x['interval_95']==[1.,1.] and x['bootstrap_degenerate_draws']>0
    evidence.append({'fixture':'two single-class components and degenerate bootstrap','exact_p':.5,
                     'degenerate_draws':x['bootstrap_degenerate_draws'],'interval':[1.,1.]})
    scores=[{'status':'ok','score':.1,'gold':0},{'status':'tie','score':.5,'gold':0},
            {'status':'tie','score':.5,'gold':1},{'status':'ok','score':.9,'gold':1}]
    f=forecasts(scores)
    assert math.isclose(f['brier'],.13) and f['auroc']==.875 and f['reliability'][5]['rows']==2
    evidence.append({'fixture':'rank AUROC with tied native forecasts','auroc':.875,'brier':.13})
    h=holm([.001,.01,.04,None,.2,.9])
    assert h[0]['p_holm']==.006 and h[1]['p_holm']==.05 and h[2]['p_holm']==.16 and h[3]['p_holm'] is None
    evidence.append({'fixture':'six-slot Holm with unavailable test','adjusted':[r['p_holm'] for r in h]})
    # All-zero paired effects and a >20-component deterministic MC case exercise
    # both declared randomization algorithms and the complete RNG batch recipes.
    z=infer([0,0],['a','b'],[0,1])
    assert z['randomization_p_two_sided']==1 and z['interval_95']==[0.,0.]
    mc=infer([1]*42,[f'g{i:02}' for i in range(21) for _ in range(2)],[0,1]*21)
    assert mc['randomization_draws']==100000 and mc['bootstrap_valid_draws']==20000
    assert mc['estimate']==1 and mc['interval_95']==[1.,1.]
    evidence.append({'fixture':'21-component MC/RNG recipe','p':mc['randomization_p_two_sided'],
                     'bootstrap_valid_draws':mc['bootstrap_valid_draws']})
    return {'version':'independent-math-synthetic-fixtures-1','empirical_access':False,
            'project_analytical_functions_imported':False,'checks_passed':True,'fixtures':evidence}


def freeze_tools():
    report=fixture_checks()
    immutable(HERE/'fixture-results.json',report)
    manifest={'version':'independent-v6-math-tools-1','empirical_inputs_read':False,
        'tool_sha256':sha(__file__),'fixture_sha256':sha(HERE/'fixture-results.json'),
        'numpy_version':np.__version__,'python_version':sys.version.split()[0],
        'seed':SEED,'bootstrap_draws':B,'randomization_draws':R,
        'verification_scope':['strict planned/primary join','source/config classification/support/missingness',
            'component/class paired means','same-seed component bootstrap/sign randomization',
            'fixed-six Holm','sourcepair attrition/transitions','native rank AUROC/Brier/reliability',
            'same-row route coverage/intersections','locked reviewer subgroup support gates'],
        'limitations':['Root must independently bind normalized inputs to terminal raw evidence and frozen labels.',
            'This checks frozen statistical arithmetic, not human-gold validity or sampling assumptions.',
            'Categorical explanatory prose not used by numerical reporting is outside this numeric projection.'],
        'access_policy':'Fixtures only until root supplies explicit terminal authorization with all three empirical input hashes.'}
    immutable(HERE/'TOOLS-FROZEN.json',manifest)
    return manifest


def authorized_compare(planned,records,analysis,authorization,output):
    freeze=json.loads((HERE/'TOOLS-FROZEN.json').read_text())
    if freeze['tool_sha256']!=sha(__file__) or freeze['fixture_sha256']!=sha(HERE/'fixture-results.json'):
        raise PermissionError('Independent tools changed after pre-empirical freeze')
    grant=json.loads(Path(authorization).read_text())
    if grant.get('root_authorized_terminal_analysis') is not True or grant.get('terminal_execution_verified') is not True:
        raise PermissionError('No explicit root terminal-analysis authorization')
    paths={'planned':Path(planned),'records':Path(records),'analysis':Path(analysis)}
    for name,path in paths.items():
        if grant.get(name+'_sha256')!=sha(path):raise PermissionError('Authorized empirical input hash changed: '+name)
    frozen_actual=json.loads(Path(analysis).read_text())
    expected=recompute(load_rows(planned),load_rows(records))
    counts,mismatches=compare(expected,frozen_actual)
    result={'version':'independent-v6-math-comparison-1','checks_passed':not mismatches,
        'analysis_recomputed':not mismatches,'checked_leaf_counts':dict(counts),'mismatches':mismatches,
        'inputs':{name:{'path':str(path),'sha256':sha(path)} for name,path in paths.items()},
        'analysis_canonical_sha256':hashlib.sha256(canonical(frozen_actual)).hexdigest(),
        'tool_sha256':sha(__file__),'fixture_sha256':sha(HERE/'fixture-results.json'),
        'new_model_calls':0,'new_scientific_choices':False,'scope':freeze['verification_scope']}
    immutable(output,result)
    return {'checks_passed':not mismatches,'checked_leaf_counts':dict(counts),'mismatch_count':len(mismatches),
            'receipt':str(output),'receipt_sha256':sha(output)}


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest='action',required=True)
    sub.add_parser('freeze-fixtures')
    p=sub.add_parser('compare')
    for name in ('planned','records','analysis','authorization','output'):p.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    if args.action=='freeze-fixtures':result=freeze_tools()
    else:result=authorized_compare(args.planned,args.records,args.analysis,args.authorization,args.output)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__':main()
