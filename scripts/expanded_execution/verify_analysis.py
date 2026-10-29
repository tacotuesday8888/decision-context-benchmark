"""Independent point-estimate checks against raw saved cells; final offline gate."""
import csv
import json
import math
from collections import Counter
from functools import lru_cache
import numpy as np
from execute import OUT,DATA,PANEL,jsonl,sha


def close(a,b):
    if a is None or b is None:assert a is b,(a,b)
    else:assert math.isclose(a,b,rel_tol=1e-10,abs_tol=1e-12),(a,b)



@lru_cache(maxsize=64)
def audit_weights(signature):
    rng=np.random.default_rng(20261026)
    result=np.zeros((10000,len(signature)))
    for stratum in sorted({s for s,k in signature}):
        keys=sorted({k for s,k in signature if s==stratum})
        sampled=rng.multinomial(len(keys),[1/len(keys)]*len(keys),size=10000)
        for i,(s,k) in enumerate(signature):
            if s==stratum:result[:,i]=sampled[:,keys.index(k)]
    return result


def check_interval(rows,values,axis,reported,balanced=False):
    signature=tuple(('all',r['groups'][axis]) if axis in ('document','attack_family') else
        (str(r['gold']),r['groups']['team' if r['gold'] else ('topic' if 'topic' in r['groups'] else 'fixture')]) for r in rows)
    selected=np.array([v is not None for v in values]);strata={s for s,k in signature}
    counts=[len({k for i,(s,k) in enumerate(signature) if s==stratum and selected[i]}) for stratum in strata]
    if not selected.any() or any(n<2 for n in counts):
        assert reported is None;return
    weights=audit_weights(signature)
    values=np.array([v if v is not None else 0 for v in values])
    masks=[selected & np.array([r['gold']==g for r in rows]) for g in sorted({r['gold'] for r in rows})] if balanced else [selected]
    numerators=[weights[:,m]@values[m] for m in masks]
    denominators=[weights[:,m].sum(axis=1) for m in masks]
    keep=np.all(np.array(denominators)>0,axis=0)
    draws=sum(n[keep]/d[keep] for n,d in zip(numerators,denominators))/len(masks)
    expected=np.quantile(draws,[.025,.975])
    assert reported is not None
    for a,b in zip(expected,reported):close(float(a),b)


def check_forecasts(items,summary):
    close(summary['n'],len(items))
    close(summary['brier'],sum((p-y)**2 for p,y in items)/len(items) if items else None)
    clipped=[(min(1-1e-6,max(1e-6,p)),y) for p,y in items]
    close(summary['log_loss'],-sum(y*math.log(p)+(1-y)*math.log(1-p) for p,y in clipped)/len(items) if items else None)
    if not items:return
    assert summary['exact_zero_or_one_scores']==sum(p in (0,1) for p,y in items)
    for i,bucket in enumerate(summary['calibration']):
        subset=[(p,y) for p,y in items if min(int(p*5),4)==i]
        assert bucket['n']==len(subset)
        close(bucket['mean_predicted_attack_probability'],sum(p for p,y in subset)/len(subset) if subset else None)
        close(bucket['observed_attack_fraction'],sum(y for p,y in subset)/len(subset) if subset else None)


def main():
    rows={r['id']:r for r in jsonl(DATA/'collection.jsonl') if r['split']=='eval'}
    raw={};attempts=[]
    for config in PANEL:
        for path in (OUT/'evaluation'/config).glob('*-*.json'):
            r=json.loads(path.read_text())
            if 'parsed' not in r:continue
            attempts.append(r)
            key=(config,r['id'],r['condition'])
            if key not in raw or r['attempt']>raw[key]['attempt']:raw[key]=r
    summary=json.loads((OUT/'summary.json').read_text())
    assert summary['status_counts'].get('not_run',0)==0,'Final analyses require completed execution or a separately documented blocker-aware gate'
    assert summary['observed_logical_cells']==len(raw)==summary['planned_logical_cells']
    with (OUT/'per-example.csv').open() as f:cells=list(csv.DictReader(f))
    assert len(cells)==len(raw)
    for c in cells:
        r=raw[c['config'],c['id'],c['condition']];p=r['parsed']
        assert c['status']==p['status'] and int(c['gold'])==rows[c['id']]['gold']
        assert c['valid']==str(p['valid'])
        assert c['prediction']==('' if p['prediction'] is None else str(p['prediction']))
        close(float(c['score']) if c['score'] else None,p.get('score'))
    for s in summary['summaries']:
        rs=[(rows[i],r['parsed']) for (config,i,condition),r in raw.items() if config==s['config'] and condition==s['condition'] and rows[i]['dataset']==s['dataset']]
        assert len(rs)==s['n']
        correct=[]
        for g,label in [(0,'negative'),(1,'positive')]:
            ys=[p for row,p in rs if row['gold']==g];valid=[p for p in ys if p['valid']]
            wrong=sum(p['prediction']!=g for p in valid)
            assert s[label+'_n']==len(ys) and s['valid_'+label+'_n']==len(valid)
            assert s['false_positives' if g==0 else 'false_negatives']==wrong
            close(s['valid_fpr' if g==0 else 'valid_fnr'],wrong/len(valid) if valid else None)
            correct.append(sum(p['prediction']==g for p in valid)/len(ys) if ys else None)
        close(s['strict_balanced_accuracy'],sum(correct)/2 if all(x is not None for x in correct) else None)
        assert s['invalid_n']==sum(not p['valid'] for row,p in rs)
    for c in summary['paired_contrasts']:
        assert c['status']=='complete'
        other,base=c['contrast'].split(' minus ')
        eligible=[(i,r) for i,r in rows.items() if r['dataset']==c['dataset'] and other in r['conditions'] and base in r['conditions']]
        assert c['pairs']==len(eligible)
        by_class=[]
        for g in sorted({r['gold'] for i,r in eligible}):
            pairs=[(raw[c['config'],i,base]['parsed'],raw[c['config'],i,other]['parsed']) for i,r in eligible if r['gold']==g]
            by_class.append(sum(int(b['valid'] and b['prediction']==g)-int(a['valid'] and a['prediction']==g) for a,b in pairs)/len(pairs))
        close(c['strict_correctness_delta'],sum(by_class)/len(by_class))
        eligible_rows=[r for i,r in eligible]
        differences=[int(raw[c['config'],i,other]['parsed']['valid'] and raw[c['config'],i,other]['parsed']['prediction']==r['gold'])-int(raw[c['config'],i,base]['parsed']['valid'] and raw[c['config'],i,base]['parsed']['prediction']==r['gold']) for i,r in eligible]
        for axis,reported in c['intervals'].items():check_interval(eligible_rows,differences,axis,reported['interval'],balanced=True)

    research=json.loads((OUT/'research-summary.json').read_text())
    import statistics
    for o in research['operations']:
        selected=[r for r in attempts if r['config']==o['config']]
        times=sorted(r['elapsed_seconds'] for r in selected if isinstance(r.get('elapsed_seconds'),(int,float)))
        assert o['saved_attempt_records']==len(selected)
        assert o['native_forward_windows']==sum(r['parsed'].get('windows',0) for r in selected)
        close(o['elapsed_median_seconds'],statistics.median(times) if times else None)
        if times:
            pos=.9*(len(times)-1);low=int(pos);high=min(low+1,len(times)-1)
            close(o['elapsed_p90_seconds'],times[low]+(times[high]-times[low])*(pos-low))
        assert o['known_input_tokens']==sum((r['parsed'].get('usage') or {}).get('input_tokens',0) for r in selected)
    for contrast in research['error_contrasts']:
        config=contrast['config'];g=contrast['class']
        ids=[i for i,row in rows.items() if row['dataset']==contrast['dataset'] and row['gold']==g and 'task' in row['conditions']]
        pairs=[(raw[config,i,'candidate']['parsed'],raw[config,i,'task']['parsed']) for i in ids]
        common=[(a,b) for a,b in pairs if a['valid'] and b['valid']]
        assert contrast['execution_complete'] and contrast['eligible_n']==len(ids) and contrast['common_valid_n']==len(common)
        strict=[int(not b['valid'] or b['prediction']!=g)-int(not a['valid'] or a['prediction']!=g) for a,b in pairs]
        valid=[int(b['prediction']!=g)-int(a['prediction']!=g) for a,b in common]
        close(contrast['strict_failure_delta'],sum(strict)/len(strict) if strict else None)
        close(contrast['valid_error_delta'],sum(valid)/len(valid) if valid else None)
        eligible_rows=[rows[i] for i in ids]
        valid_values=[int(b['prediction']!=g)-int(a['prediction']!=g) if a['valid'] and b['valid'] else None for a,b in pairs]
        for reported in contrast['strict_intervals']:check_interval(eligible_rows,strict,reported['axis'],reported['interval'])
        for reported in contrast['valid_intervals']:check_interval(eligible_rows,valid_values,reported['axis'],reported['interval'])

    for t in research['threshold_tradeoffs']:
        ps=[(rows[i]['gold'],r['parsed']['score']) for (config,i,condition),r in raw.items() if config==t['config'] and condition==t['condition'] and rows[i]['dataset']==t['dataset'] and r['parsed']['status'] in ('ok','tie')]
        assert t['scored_n']==len(ps) and t['abstentions']==sum(p==t['threshold'] for g,p in ps)
        assert t['false_positives']==sum(g==0 and p>t['threshold'] for g,p in ps)
        assert t['false_negatives']==sum(g==1 and p<t['threshold'] for g,p in ps)
    review=json.loads((OUT/'error-review.json').read_text())
    for ex in review['examples']:
        row=rows[ex['id']];assert row['gold']==ex['gold'] and row['candidate_sha256']==ex['candidate_sha256']
        for condition in ('candidate','task'):
            p=raw[ex['config'],ex['id'],condition]['parsed']
            assert p['prediction']==ex[condition+'_prediction']
            close(p.get('score'),ex[condition+'_score'])
    for failure in review['operational_failures']:
        assert raw[failure['config'],failure['id'],failure['condition']]['parsed']['status']==failure['status']
    forecast=json.loads((OUT/'forecast-summary.json').read_text())
    for name in ['forecast-summary.json','research-summary.json']:
        value=json.loads((OUT/name).read_text())
        for path,h in value['record_hashes'].items():assert sha((OUT/path).read_bytes())==h
        assert len(value['record_hashes'])==summary['observed_attempts']
    def score(config,i,condition):
        p=raw[config,i,condition]['parsed']
        return p.get('score') if p['status'] in ('ok','tie') else None
    for s in forecast['summaries']:
        ids=[i for i,row in rows.items() if row['dataset']==s['dataset'] and s['condition'] in row['conditions']]
        values=[(score(s['config'],i,s['condition']),rows[i]['gold']) for i in ids]
        values=[(p,y) for p,y in values if p is not None]
        check_forecasts(values,s);assert s['missing_score_n']==len(ids)-len(values)
        for j,bucket in enumerate(s['calibration']):
            outcomes=[rows[i]['gold'] if score(s['config'],i,s['condition']) is not None and min(int(score(s['config'],i,s['condition'])*5),4)==j else None for i in ids]
            for reported in bucket['observed_fraction_intervals']:check_interval([rows[i] for i in ids],outcomes,reported['axis'],reported['interval'])

    for c in forecast['paired_contrasts']:
        other,base=c['contrast'].split(' minus ')
        ids=[i for i,row in rows.items() if row['dataset']==c['dataset'] and other in row['conditions'] and base in row['conditions']]
        pairs=[(score(c['config'],i,base),score(c['config'],i,other),rows[i]['gold']) for i in ids]
        common=[(a,b,y) for a,b,y in pairs if a is not None and b is not None]
        assert c['execution_complete'] and c['common_score_n']==len(common)
        check_forecasts([(a,y) for a,b,y in common],c['base']);check_forecasts([(b,y) for a,b,y in common],c['context'])
        close(c['brier_delta'],sum((b-y)**2-(a-y)**2 for a,b,y in common)/len(common) if common else None)
        losses=[(b-y)**2-(a-y)**2 if a is not None and b is not None else None for a,b,y in pairs]
        for reported in c['intervals']:check_interval([rows[i] for i in ids],losses,reported['axis'],reported['interval'])

    print(json.dumps({'point_estimates_verified':True,'cells':len(raw),'classification_strata':len(summary['summaries']),'forecast_strata':len(forecast['summaries']),'paired_forecasts':len(forecast['paired_contrasts'])}))

if __name__=='__main__':main()
