"""Source-specific error contrasts, descriptive subgroups and route accounting."""
from collections import Counter
import csv
import json
import numpy as np
from execute import OUT, DATA, PANEL, jsonl, save, sha, verify_preparation
from analyze import metrics
from forecast_analysis import native_score, interval, axes
from spending import totals, caps


def error_contrast(rows, base, context, gold):
    selected=[r for r in rows if r['gold']==gold]
    common=[r for r in selected if base.get(r['id'],{}).get('valid') and context.get(r['id'],{}).get('valid')]
    strict=[]; valid=[]
    for r in selected:
        a=base.get(r['id']); b=context.get(r['id'])
        strict.append(None if a is None or b is None else int(not b['valid'] or b['prediction']!=gold)-int(not a['valid'] or a['prediction']!=gold))
        valid.append(None if r not in common else int(b['prediction']!=gold)-int(a['prediction']!=gold))
    def delta(values):
        xs=[v for v in values if v is not None]
        return float(np.mean(xs)) if xs else None
    return {'class':gold,'eligible_n':len(selected),'common_valid_n':len(common),
        'strict_failure_delta':delta(strict),'valid_error_delta':delta(valid),
        'strict_intervals':[interval(selected,strict,a) for a in axes(selected)] if selected else [],
        'valid_intervals':[interval(selected,valid,a) for a in axes(selected)] if selected else [],
        'definition':'Context minus candidate. Strict failure includes invalid/tie; valid error compares common valid decisions only.'}


def main():
    verify_preparation()
    rows=sorted([r for r in jsonl(DATA/'collection.jsonl') if r['split']=='eval'],key=lambda r:r['id'])
    actual={}; attempts=[]; hashes={}
    for config in PANEL:
        for path in sorted((OUT/'evaluation'/config).glob('*-*.json')):
            r=json.loads(path.read_text())
            if 'parsed' not in r:continue
            hashes[str(path.relative_to(OUT))]=sha(path.read_bytes());attempts.append(r)
            key=(config,r['id'],r['condition'])
            if key not in actual or r['attempt']>actual[key]['attempt']:actual[key]=r
    errors=[];subgroups=[];tradeoffs=[];operations=[]
    for config in PANEL:
        records=[r for r in attempts if r['config']==config]
        times=[r['elapsed_seconds'] for r in records if isinstance(r.get('elapsed_seconds'),(int,float))]
        operations.append({'config':config,'route':dict(Counter(r['access_route'] for r in records)),
            'saved_attempt_records':len(records),'logical_cells':sum(k[0]==config for k in actual),
            'status_counts':dict(Counter(r['parsed']['status'] for k,r in actual.items() if k[0]==config)),
            'measured_attempt_times_n':len(times),'elapsed_median_seconds':float(np.median(times)) if times else None,
            'elapsed_p90_seconds':float(np.quantile(times,.9)) if times else None,
            'elapsed_sum_seconds':sum(times),'known_input_tokens':sum((r['parsed'].get('usage') or {}).get('input_tokens',0) for r in records),
            'usage_records_n':sum(isinstance((r['parsed'].get('usage') or {}).get('input_tokens'),int) for r in records),
            'known_output_tokens':sum((r['parsed'].get('usage') or {}).get('output_tokens',0) for r in records),
            'note':'Observed route duration includes overhead; concurrently running local jobs may contend. Not intrinsic speed or wall-clock run duration.'})
        for dataset in sorted({r['dataset'] for r in rows}):
            source=[r for r in rows if r['dataset']==dataset]
            conditions=['candidate'] if config=='protectai_local' else sorted({c for r in source for c in r['conditions']})
            cells={c:{r['id']:actual[(config,r['id'],c)]['parsed'] for r in source if (config,r['id'],c) in actual} for c in conditions}
            if 'task' in cells:
                eligible=[r for r in source if 'task' in r['conditions']]
                complete=all((config,r['id'],c) in actual for r in eligible for c in ('candidate','task'))
                for g in (0,1):
                    errors.append({'config':config,'dataset':dataset,'execution_complete':complete,**error_contrast(eligible,cells['candidate'],cells['task'],g)})
            for c in conditions:
                for label,predicate in [('<=1000 chars',lambda r:len(r['candidate'])<=1000),('1001-4000 chars',lambda r:1000<len(r['candidate'])<=4000),('>4000 chars',lambda r:len(r['candidate'])>4000)]:
                    subset=[r for r in source if predicate(r) and c in r['conditions']]
                    data=[dict(gold=r['gold'],**cells[c].get(r['id'],{'status':'not_run','valid':False,'prediction':None})) for r in subset]
                    subgroups.append({'config':config,'dataset':dataset,'condition':c,'axis':'candidate_length','group':label,**metrics(data)})
                if dataset.startswith('bipia-'):
                    for family in sorted({r['groups']['attack_family'] for r in source}):
                        subset=[r for r in source if r['groups']['attack_family']==family]
                        data=[dict(gold=r['gold'],**cells[c].get(r['id'],{'status':'not_run','valid':False,'prediction':None})) for r in subset]
                        subgroups.append({'config':config,'dataset':dataset,'condition':c,'axis':'attack_family','group':family,**metrics(data)})
                if PANEL[config]['kind']=='chat':continue
                scored=[(r,native_score(cells[c].get(r['id']))) for r in source]
                scored=[(r,p) for r,p in scored if p is not None]
                for step in range(11):
                    cut=step/10
                    n0=sum(r['gold']==0 for r,p in scored);n1=sum(r['gold']==1 for r,p in scored)
                    fp=sum(r['gold']==0 and p>cut for r,p in scored);fn=sum(r['gold']==1 and p<cut for r,p in scored)
                    tradeoffs.append({'config':config,'dataset':dataset,'condition':c,'threshold':float(cut),
                        'scored_n':len(scored),'negative_n':n0,'positive_n':n1,'false_positives':fp,'false_negatives':fn,
                        'abstentions':sum(p==cut for r,p in scored),'fpr_all_scored_negatives':fp/n0 if n0 else None,'fnr_all_scored_positives':fn/n1 if n1 else None})
    save(OUT/'research-summary.json',{'version':'research-summaries-v1.1','record_hashes':hashes,
        'error_contrasts':errors,'descriptive_subgroups':subgroups,'threshold_tradeoffs':tradeoffs,
        'threshold_note':'Fixed descriptive grid; ties abstain. No selected threshold, fitting, or deployment policy. Error rates exclude abstentions from numerator but retain scored class denominators; inspect abstention counts.',
        'operations':operations,'all_in_accounted_usd':totals(OUT),'provider_caps_usd':caps()})
    print(json.dumps({'errors':len(errors),'subgroups':len(subgroups),'tradeoffs':len(tradeoffs),'observed_cells':len(actual)}))

if __name__=='__main__':main()
