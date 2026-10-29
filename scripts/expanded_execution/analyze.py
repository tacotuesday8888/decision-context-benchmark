"""Offline source-stratified analysis. Missing cells never count as observed predictions."""
import csv
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
import sys
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from execute import OUT, DATA, PANEL, jsonl, save, verify_preparation, sha


def wilson(errors, n):
    if not n:return None
    z=1.959963984540054;phat=errors/n;denom=1+z*z/n
    center=(phat+z*z/(2*n))/denom
    half=z*math.sqrt(phat*(1-phat)/n+z*z/(4*n*n))/denom
    return [max(0,center-half),min(1,center+half)]


def metrics(rows):
    n={g:sum(r['gold']==g for r in rows) for g in (0,1)}
    valid={g:sum(r['gold']==g and r['valid'] for r in rows) for g in (0,1)}
    wrong={g:sum(r['gold']==g and r['valid'] and r['prediction']!=g for r in rows) for g in (0,1)}
    correct={g:sum(r['gold']==g and r['valid'] and r['prediction']==g for r in rows) for g in (0,1)}
    return {'n':len(rows),'negative_n':n[0],'positive_n':n[1],
            'valid_negative_n':valid[0],'valid_positive_n':valid[1],
            'invalid_n':sum(not r['valid'] and r['status']!='not_run' for r in rows),
            'not_run_n':sum(r['status']=='not_run' for r in rows),
            'valid_coverage':sum(valid.values())/len(rows) if rows else None,
            'false_positives':wrong[0],'false_negatives':wrong[1],
            'valid_fpr':wrong[0]/valid[0] if valid[0] else None,
            'valid_fnr':wrong[1]/valid[1] if valid[1] else None,
            'fpr_descriptive_wilson95':wilson(wrong[0],valid[0]),
            'fnr_descriptive_wilson95':wilson(wrong[1],valid[1]),
            'strict_balanced_accuracy':sum(correct[g]/n[g] for g in (0,1))/2 if all(n.values()) else None}


def clustered_delta(rows, base, other, axis):
    """Same sampled cluster weights apply to both conditions, labels and pair members."""
    clusters=sorted({r['groups'][axis] for r in rows})
    if len(clusters)<2:return {'clusters':len(clusters),'interval':None}
    values=np.zeros((len(clusters),4));index={c:i for i,c in enumerate(clusters)}
    for r in rows:
        g=r['gold'];v=values[index[r['groups'][axis]]]
        v[g]+=1
        v[g+2]+=int(other[r['id']]['valid'] and other[r['id']]['prediction']==g)-int(base[r['id']]['valid'] and base[r['id']]['prediction']==g)
    rng=np.random.default_rng(20261026)
    weights=rng.multinomial(len(clusters), np.full(len(clusters),1/len(clusters)),size=10000)
    sampled=weights@values
    classes=sorted({r['gold'] for r in rows})
    keep=np.all(sampled[:,classes]>0,axis=1)
    delta=np.mean(sampled[keep][:,[g+2 for g in classes]]/sampled[keep][:,classes],axis=1)
    return {'clusters':len(clusters),'draws':10000,'valid_draws':int(keep.sum()),
            'interval':np.quantile(delta,[.025,.975]).tolist(),
            'interval_kind':'95% percentile paired cluster bootstrap; correctness delta'}


def paired(rows,base,other):
    pairs=[r for r in rows if r['id'] in base and r['id'] in other]
    if not pairs or any(base[r['id']]['status']=='not_run' or other[r['id']]['status']=='not_run' for r in pairs):
        return {'status':'incomplete; no paired inference until stratum execution completes'}
    a=metrics([base[r['id']] for r in pairs]);b=metrics([other[r['id']] for r in pairs])
    classes=sorted({r['gold'] for r in pairs})
    delta=np.mean([np.mean([int(other[r['id']]['valid'] and other[r['id']]['prediction']==g)-int(base[r['id']]['valid'] and base[r['id']]['prediction']==g) for r in pairs if r['gold']==g]) for g in classes])
    result={'status':'complete','pairs':len(pairs),'strict_correctness_delta':float(delta),
            'metric':'balanced accuracy' if len(classes)==2 else 'class-specific correctness',
            'base':a,'context':b,'intervals':{}}
    if pairs[0]['dataset'].startswith('bipia-'):
        for axis in ('document','attack_family'):
            result['intervals'][axis]=clustered_delta(pairs,base,other,axis)
    else:
        # LLMail gold classes have distinct grouping units. Sample each class separately;
        # task/fixture support is fixed, not a claim of independent tasks.
        draws=[];units={};rng=np.random.default_rng(20261026)
        for g in classes:
            subset=[r for r in pairs if r['gold']==g]
            axis='team' if g else ('topic' if 'topic' in subset[0]['groups'] else 'fixture')
            keys=sorted({r['groups'][axis] for r in subset});units[str(g)]={'axis':axis,'clusters':len(keys)}
            if len(keys)<2:
                draws=[];break
            counts=np.array([sum(r['groups'][axis]==k for r in subset) for k in keys])
            diffs=np.array([sum(int(other[r['id']]['valid'] and other[r['id']]['prediction']==g)-int(base[r['id']]['valid'] and base[r['id']]['prediction']==g) for r in subset if r['groups'][axis]==k) for k in keys])
            w=rng.multinomial(len(keys),np.full(len(keys),1/len(keys)),size=10000)
            draws.append((w@diffs)/(w@counts))
        result['intervals']['class_clusters']={'units':units,'interval':np.quantile(np.mean(draws,axis=0),[.025,.975]).tolist() if draws else None,
            'caveat':'Conditional on observed tasks. No population interval when a class has fewer than two clusters.'}
    return result


def main():
    verify_preparation()
    candidates=[r for r in jsonl(DATA/'collection.jsonl') if r['split']=='eval']
    actual={};attempts=[]
    for config in PANEL:
        for path in sorted((OUT/'evaluation'/config).glob('*.json')):
            if path.name=='STOP.json':continue
            r=json.loads(path.read_text())
            if 'parsed' not in r:continue
            attempts.append(r)
            k=(config,r['id'],r['condition'])
            if k not in actual or actual[k]['attempt']<r['attempt']:actual[k]=r
    cells=[]
    for config in PANEL:
        for row in candidates:
            for condition in (['candidate'] if config=='protectai_local' else row['conditions']):
                record=actual.get((config,row['id'],condition))
                parsed=record['parsed'] if record else {'status':'not_run','valid':False,'prediction':None}
                cells.append({'config':config,'id':row['id'],'dataset':row['dataset'],'condition':condition,
                    'gold':row['gold'],'candidate_chars':len(row['candidate']),**parsed,
                    'route':record['access_route'] if record else None})
    groups=defaultdict(list)
    for r in cells:groups[(r['config'],r['dataset'],r['condition'])].append(r)
    summaries=[{'config':c,'dataset':d,'condition':k,**metrics(rs)} for (c,d,k),rs in sorted(groups.items())]
    contrasts=[]
    for config in PANEL:
        if config=='protectai_local':continue
        for dataset in sorted({r['dataset'] for r in candidates}):
            rows=[r for r in candidates if r['dataset']==dataset]
            for baseline,condition in [('candidate','task'),('candidate','source'),('task','both'),('source','both')]:
                eligible=[r for r in rows if condition in r['conditions']]
                if not eligible:continue
                base={r['id']:r for r in groups[(config,dataset,baseline)]}
                other={r['id']:r for r in groups[(config,dataset,condition)]}
                contrasts.append({'config':config,'dataset':dataset,'contrast':condition+' minus '+baseline,
                                  **paired(eligible,base,other)})
    costs={}
    for p in sorted(OUT.glob('*ledger*.json')):
        name=p.stem
        if p.exists():
            d=json.loads(p.read_text());costs[name]={'cap_usd':d['cap_usd'],'accounted_usd':sum(e['accounted_usd'] for e in d['entries']),
                'pending_attempts':sum(e['state']=='pending' for e in d['entries'])}
    result={'collection_sha256':sha((DATA/'collection.jsonl').read_bytes()),'candidate_count':len(candidates),
            'observed_attempts':len(attempts),'observed_logical_cells':len(actual),
            'planned_logical_cells':len(cells),'summaries':summaries,'paired_contrasts':contrasts,'costs':costs,
            'status_counts':dict(Counter(r['status'] for r in cells)),
            'local_by_length':[{'length':label,**metrics([r for r in cells if r['config']=='protectai_local' and r['status']!='not_run' and predicate(r)])}
                for label,predicate in [('one window',lambda r:r.get('windows',0)==1),('multiple windows',lambda r:r.get('windows',0)>1)] ]}
    save(OUT/'summary.json',result)
    with (OUT/'per-example.csv').open('w') as f:
        keys=['config','id','dataset','condition','gold','status','valid','prediction','score','candidate_chars','route']
        writer=csv.DictWriter(f,fieldnames=keys,extrasaction='ignore',lineterminator='\n');writer.writeheader();writer.writerows(cells)
    figure_dir=OUT/'figures';figure_dir.mkdir(exist_ok=True)
    local=[s for s in summaries if s['config']=='protectai_local']
    fig,ax=plt.subplots(figsize=(9,5.2),layout='constrained')
    y=np.arange(len(local));width=.36
    for offset,key,label,color in [(-width/2,'valid_fpr','FPR (valid negatives)','#2864A0'),(width/2,'valid_fnr','FNR (valid positives)','#C58A22')]:
        values=[s[key] if s[key] is not None else np.nan for s in local]
        bars=ax.barh(y+offset,values,height=width,label=label,color=color)
        for bar,v in zip(bars,values):
            if np.isfinite(v):ax.text(v-.015 if v>.85 else v+.015,bar.get_y()+bar.get_height()/2,f'{v:.1%}',va='center',ha='right' if v>.85 else 'left',fontsize=9)
    ax.set_yticks(y,[f"{s['dataset']}  (n0={s['negative_n']}, n1={s['positive_n']})" for s in local]);ax.invert_yaxis()
    ax.set_xlim(0,1);ax.set_xlabel('Error rate');ax.set_title('Local detector: candidate-only evaluation by source',pad=38)
    ax.legend(loc='lower center',bbox_to_anchor=(.5,1.0),ncol=2,frameon=False);ax.spines[['top','right']].set_visible(False)
    fig.savefig(figure_dir/'local-errors.png',dpi=180);plt.close(fig)
    complete=[c for c in contrasts if c['status']=='complete' and c['metric']=='balanced accuracy']
    if complete:
        fig,ax=plt.subplots(figsize=(10,max(4,len(complete)*.35)),layout='constrained')
        for i,c in enumerate(complete):
            v=c['strict_correctness_delta'];ax.plot(v,i,'o',color='#2864A0')
            interval=c['intervals'].get('document',{}).get('interval')
            if interval:ax.plot(interval,[i,i],color='#2864A0')
            else:ax.annotate('CI unavailable',(v,i),xytext=(7,0),textcoords='offset points',va='center',fontsize=8)
        ax.set_yticks(range(len(complete)),[c['config']+' / '+c['dataset']+' / '+c['contrast'] for c in complete]);ax.invert_yaxis()
        ax.axvline(0,color='#666666',linewidth=.8);ax.set_xlabel('Strict balanced-accuracy change (proportion)')
        ax.set_title('Paired context effects in completed two-class strata')
        fig.savefig(figure_dir/'paired-effects.png',dpi=180);plt.close(fig)
    lines=['# Expanded experiment execution','',
        f"Observed {len(actual)} of {len(cells)} planned cells in {len(attempts)} attempts over 402 candidates. Missing cells are marked not_run, separate from observed invalid responses. This report is partial until all intended configurations complete.",'',
        'The primary question is the within-candidate effect of authentic trusted task context on injection detection. Neighboring-source context is secondary and available only for LLMail task2. No AI-generated examples or labels, invented context, evaluation tuning, or pilot changes are used.','',
        '## Completed source strata','',
        '| Configuration | Source | Condition | N− / N+ | Valid | Strict BA | FPR | FNR |',
        '| --- | --- | --- | --- | --- | --- | --- | --- |']
    def fmt(x):return '—' if x is None else f'{100*x:.1f}%'
    for s in summaries:
        if s['not_run_n']:continue
        lines.append(f"| {s['config']} | {s['dataset']} | {s['condition']} | {s['negative_n']} / {s['positive_n']} | {s['valid_coverage']:.1%} | {fmt(s['strict_balanced_accuracy'])} | {fmt(s['valid_fpr'])} | {fmt(s['valid_fnr'])} |")
    lines+=['','FPR and FNR use valid negative and positive denominators, respectively, saved in summary.json. Strict balanced accuracy counts observed invalid outputs as incorrect. It is undefined for one-class sources. No pooled ranking is reported. Descriptive Wilson bounds are in summary.json and assume independence that these correlated sources do not establish; task4 has only two negatives from one fixture.','',
            '![Local detector source errors](figures/local-errors.png)','','## Paired effects','']
    for c in complete:
        intervals=[]
        for axis,value in c['intervals'].items():
            bounds=value.get('interval')
            intervals.append(axis+': '+(f"[{bounds[0]*100:+.2f}, {bounds[1]*100:+.2f}] pp" if bounds else 'unavailable; too few independent clusters'))
        lines.append(f"- {c['config']}, {c['dataset']}, {c['contrast']}: {c['strict_correctness_delta']*100:+.2f} percentage points; {c['pairs']} paired candidates. 95% intervals: "+'; '.join(intervals)+'.')
    if not complete:lines.append('No complete two-class remote source comparison is available yet.')
    if complete:lines+=['','![Paired context effects](figures/paired-effects.png)']
    lines+=['','## Secondary neighboring-source effects','',
        *[f"- {c['config']}, {c['dataset']}, {c['contrast']}: {c['strict_correctness_delta']*100:+.2f} pp in class-specific correctness; {c['pairs']} pairs." for c in contrasts if c['status']=='complete' and c['metric']!='balanced accuracy'],
        '', '## Interpretation and limits','',
        'BIPIA labels inherit published clean/injected construction; LLMail attacks inherit recorded unauthorized tool-call outcomes. Public-data contamination and correlated candidates limit generalization. Native scores are not calibrated probabilities on this corpus. The local maximum over windows may increase false positives on long candidates and has no native task-context comparison.','',
        'Intervals use 10,000 paired cluster-bootstrap draws (seed 20261026). BIPIA document and attack-family intervals are separate sensitivity analyses. LLMail positive teams and negative fixtures/topics are sampled separately; one-fixture negative strata receive no population interval. No winner declaration or confirmatory p-values. Single model responses do not measure generation variance.','',
        '## Operations and cost','',json.dumps(costs,indent=2),'' ]
    (OUT/'report.md').write_text('\n'.join(lines)+'\n')
    print(json.dumps({'observed_cells':len(actual),'planned_cells':len(cells),'attempts':len(attempts),'costs':costs}))

if __name__=='__main__':main()
