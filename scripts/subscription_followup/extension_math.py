"""Fixture-friendly frozen source estimators. No file, auth or inference reads."""
from collections import defaultdict,Counter
from scripts.subscription_followup import analyze_core as core

SEED='subscription-followup-extension-analysis-v1-20261101'
MODELS=('sol_subscription','jev_firstparty')
CONDITIONS=core.CONDITIONS
CONTROLS=core.CONTROLS
DRAWS=20000


def index_source(rows):
    groups=defaultdict(dict);members=defaultdict(dict);identities={}
    for original in rows:
        row=dict(original);model=row['config'];label=row.get('gold',row.get('upstream_label'))
        core.require(model in MODELS and row['condition'] in CONDITIONS,'Unexpected source model/condition')
        core.require(type(label) is int and label in (0,1),'Original source condition label required')
        core.require(row.get('replicate','first')=='first' and row.get('stage','secondary')=='secondary','Only source first outcomes are admissible')
        core._valid(row);gid=row['group_id'];identity=(model,row['condition'],label)
        core.require(identity not in groups[gid],'Duplicate source cell')
        core.require(identities.setdefault(row['id'],(gid,label))==(gid,label),'Source identity/group/label changed')
        core.require(label not in members[gid] or members[gid][label]==row['id'],'Source must retain one intact clean/attack pair')
        members[gid][label]=row['id'];groups[gid][identity]=dict(row,gold=label)
    expected={(m,c,a) for m in MODELS for c in CONDITIONS for a in (0,1)}
    core.require(all(set(group)==expected and set(members[g])=={0,1} for g,group in groups.items()),'Require all planned16 cells per component, with missing outcomes explicit')
    return dict(groups)


def _estimate(values,ids,*,purpose,limit=1,draws=DRAWS):
    return {'cohort':core.cohort(ids),**core.bootstrap_mean(values,purpose=purpose,seed=SEED,limit=limit,draws=draws)}


def analyze_source(rows,*,draws=DRAWS):
    """Six D contrasts and three paired Sol−Jev interactions on shared16.

    Namespace is retained, not rewritten to a core run namespace. A native0.5
    score remains available while its classification abstains. Unknown errors
    retain every planned component in signed finite missing-error bounds.
    """
    groups=index_source(rows);ids=sorted(groups)
    common=[g for g in ids if all(core._valid(r) for r in groups[g].values())]
    model8={m:[g for g in ids if all(core._valid(r) for (config,_,_),r in groups[g].items() if config==m)] for m in MODELS}
    contrasts=[];interactions=[]
    for control in CONTROLS:
        errors={m:{g:core._contrast(groups[g],m,control) for g in ids} for m in MODELS}
        for model in MODELS:
            complete4=[g for g in ids if all(e is not None for e in errors[model][g])]
            contrasts.append({'config':model,'control':control,'task':'task',
                'primary_shared16':_estimate([core._difference(errors[model][g]) for g in common],common,
                    purpose=f'{model}/{control}/shared16',draws=draws),
                'model_complete8_sensitivity':_estimate([core._difference(errors[model][g]) for g in model8[model]],model8[model],
                    purpose=f'{model}/{control}/model8',draws=draws),
                'contrast_complete4_sensitivity':_estimate([core._difference(errors[model][g]) for g in complete4],complete4,
                    purpose=f'{model}/{control}/contrast4',draws=draws),
                'all_planned_missing_error_bounds':{'cohort':core.cohort(ids),
                    'range':core._mean_bounds([core.signed_bounds(errors[model][g],(.5,.5,-.5,-.5)) for g in ids])}})
        pair8=[g for g in ids if all(e is not None for e in errors[MODELS[0]][g]+errors[MODELS[1]][g])]
        value=lambda g:core._difference(errors[MODELS[0]][g])-core._difference(errors[MODELS[1]][g])
        interactions.append({'config':MODELS[0],'native':MODELS[1],'control':control,'task':'task',
            'primary_shared16':_estimate([value(g) for g in common],common,purpose=f'interaction/{control}/shared16',limit=2,draws=draws),
            'pair_contrast_complete8_sensitivity':_estimate([value(g) for g in pair8],pair8,purpose=f'interaction/{control}/paircontrast8',limit=2,draws=draws),
            'all_planned_missing_error_bounds':{'cohort':core.cohort(ids),'range':core._mean_bounds([
                core.signed_bounds(errors[MODELS[0]][g]+errors[MODELS[1]][g],(.5,.5,-.5,-.5,-.5,-.5,.5,.5)) for g in ids])}})
    scores=[]
    for gid,group in groups.items():
        for (model,condition,label),row in group.items():
            if model=='jev_firstparty' and row.get('score') is not None:
                scores.append({'group_id':gid,'id':row['id'],'condition':condition,'gold':label,'score':row['score'],
                    'status':row['status'],'valid':core._valid(row),'namespace':row.get('namespace')})
    return {'version':'subscription-followup-extension-source-analysis-1','planned':core.cohort(ids),
        'shared_complete16':core.cohort(common),'model_complete8':{m:core.cohort(v) for m,v in model8.items()},
        'contrasts':contrasts,'direct_interactions':interactions,
        'shared16_metrics':{m:core._metrics(groups,common,m,draws=draws,seed=SEED,purpose='shared16') for m in MODELS},
        'model8_metrics':{m:core._metrics(groups,model8[m],m,draws=draws,seed=SEED,purpose='model_complete8') for m in MODELS},
        'all_planned_available_output_metrics':{m:core._metrics(groups,ids,m,draws=draws,seed=SEED,purpose='all_planned_available') for m in MODELS},
        'native_score_diagnostics':{'actual_score_records':sorted(scores,key=lambda r:(r['group_id'],r['condition'],r['id'])),
            'scored_cells':len(scores),'exact_ties':sum(r['score']==.5 for r in scores),
            'planned_native_cells':8*len(ids),'missing_scores':8*len(ids)-len(scores),
            'status_counts':dict(Counter(r['status'] for r in scores)),'invented_boolean_scores':False},
        'bootstrap_draws':draws,'seed':SEED,'descriptive_only':True,'source_labels_are_semantic_gold':False,
        'direction':'D positive favors task; interaction positive means greater task benefit in Sol'}
