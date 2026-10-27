"""Offline analysis and scientific figures from frozen requests and raw responses."""
import csv
from collections import Counter, defaultdict
import json
from pathlib import Path
import statistics

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from prepare_pilot import ROOT, sha
from run_pilot import CONDITIONS, MODELS, parse_response
from response_metadata import terminal_metadata

OUT=ROOT/'results/pilot'
LABELS={'candidate':'Candidate only','task':'+ Trusted task','source':'+ Source neighbor','both':'+ Both'}
COLORS={'jevmodel':'#285A8E','openai':'#B56A19','gemini':'#66783A'}
NAMES={'jevmodel':'Jev 1.13.0 (reseller)','openai':'GPT-6 Luna (subscription)','gemini':'Gemini 3.8 Flash (free API)'}


def wilson(k,n):
    if not n:return [None,None]
    z=1.959963984540054
    p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [max(0,float(mid-half)),min(1,float(mid+half))]


def metrics(rows):
    pos=[r for r in rows if r['gold']==1];neg=[r for r in rows if r['gold']==0]
    if not pos or not neg:raise ValueError('Both classes required')
    validpos=[r for r in pos if r['valid']];validneg=[r for r in neg if r['valid']]
    tp=sum(r['prediction']==1 and r['valid'] for r in pos)
    tn=sum(r['prediction']==0 and r['valid'] for r in neg)
    fp=sum(r['prediction']==1 for r in validneg);fn=sum(r['prediction']==0 for r in validpos)
    return {'n':len(rows),'positive_n':len(pos),'negative_n':len(neg),'valid_n':len(validpos)+len(validneg),
            'tp':tp,'tn':tn,'fp':fp,'fn':fn,'invalid_positive':len(pos)-len(validpos),'invalid_negative':len(neg)-len(validneg),
            'balanced_accuracy':.5*(tp/len(pos)+tn/len(neg)),
            'fpr':fp/len(validneg) if validneg else None,'fnr':fn/len(validpos) if validpos else None,
            'fpr_wilson95':wilson(fp,len(validneg)),'fnr_wilson95':wilson(fn,len(validpos))}


def resample_indices(rows,draws=10000,seed=20261026):
    # Class stratification, shared indices across all paired conditions/providers.
    rng=np.random.default_rng(seed)
    strata=[]
    for gold in [0,1]:
        groups=defaultdict(list)
        for i,row in enumerate(rows):
            if row['gold']==gold:groups[row['group']].append(i)
        group_values=[np.array(groups[k],dtype=int) for k in sorted(groups)]
        if not group_values:raise ValueError('Missing class')
        strata.append((group_values,rng.integers(0,len(group_values),size=(draws,len(group_values)))))
    for draw in range(draws):
        yield [np.concatenate([groups[k] for k in sampled[draw]]) for groups,sampled in strata]


def interval(values):
    return [float(x) for x in np.quantile(values,[.025,.975])]


def paired_summary(rows_by_condition):
    ids=sorted({r['id'] for r in rows_by_condition['candidate']})
    lookup={c:{r['id']:r for r in rows} for c,rows in rows_by_condition.items()}
    if any(set(lookup[c])!=set(ids) for c in CONDITIONS):raise ValueError('Unpaired conditions')
    reference=[lookup['candidate'][i] for i in ids]
    correct={c:np.array([float(lookup[c][i]['valid'] and lookup[c][i]['prediction']==lookup[c][i]['gold']) for i in ids]) for c in CONDITIONS}
    ba_draws={c:[] for c in CONDITIONS};fpr_draws={c:[] for c in CONDITIONS};fnr_draws={c:[] for c in CONDITIONS}
    for neg,pos in resample_indices(reference):
        for c in CONDITIONS:
            ba_draws[c].append(.5*(correct[c][neg].mean()+correct[c][pos].mean()))
            # Only complete valid outputs contribute to FPR/FNR; invalids remain in BA.
            validneg=[lookup[c][ids[i]] for i in neg if lookup[c][ids[i]]['valid']]
            validpos=[lookup[c][ids[i]] for i in pos if lookup[c][ids[i]]['valid']]
            fpr_draws[c].append(np.mean([r['prediction']==1 for r in validneg]) if validneg else np.nan)
            fnr_draws[c].append(np.mean([r['prediction']==0 for r in validpos]) if validpos else np.nan)
    result={}
    for c in CONDITIONS:
        result[c]=metrics(list(lookup[c].values()))
        result[c]['ba_cluster95']=interval(ba_draws[c])
        result[c]['fpr_cluster95']=interval(fpr_draws[c])
        result[c]['fnr_cluster95']=interval(fnr_draws[c])
        if c!='candidate':
            result[c]['delta_ba']=result[c]['balanced_accuracy']-result['candidate']['balanced_accuracy']
            result[c]['delta_cluster95']=interval(np.array(ba_draws[c])-np.array(ba_draws['candidate']))
            delta=correct[c]-correct['candidate']
            result[c]['improved_n']=int(sum(delta>0));result[c]['worsened_n']=int(sum(delta<0))
    return result,ba_draws


def load_records():
    frozen=json.loads((OUT/'frozen-plan.json').read_text())
    assert frozen['protocol_sha256']==sha((ROOT/'docs/protocol.md').read_bytes())
    assert frozen['manifest_sha256']==sha((ROOT/'data/manifest.json').read_bytes())
    expected={(r['provider'],r['id'],r['condition']):r for r in frozen['requests']}
    rows=[];seen=set()
    for path in sorted((OUT/'records').glob('*.json')):
        r=json.loads(path.read_text());key=(r['provider'],r['id'],r['condition'])
        if key in seen or key not in expected:raise ValueError('Duplicate/unplanned record')
        seen.add(key)
        if sha(json.dumps(r['request'],sort_keys=True,ensure_ascii=False))!=expected[key]['request_sha256']:
            raise ValueError('Request changed')
        if r['attempts'][-1]['http_status']==200 and r['status'] not in ['parse_or_version_error']:
            parsed=parse_response(r['provider'],r['attempts'][-1]['raw_body'])
            if any(parsed.get(k)!=r.get(k) for k in ['prediction','valid','returned_model']):
                raise ValueError('Saved prediction differs from raw response')
        r.update(terminal_metadata(r['provider'],r['attempts'][-1]['raw_body']))
        r['record']=str(path.relative_to(ROOT));rows.append(r)
    return rows,expected,seen


def usage_tokens(r):
    u=r.get('usage',{})
    if r['provider'].startswith('gemini'):return u.get('promptTokenCount'),u.get('candidatesTokenCount'),u.get('thoughtsTokenCount')
    return u.get('input_tokens'),u.get('output_tokens'),None


def write_table(rows, destination=None):
    fields=['id','gold','group','split','condition','provider','requested_model','returned_model','status','valid',
            'prediction','score','candidate_sha256','request_sha256','record','started_at','attempt_count',
            'http_status','route_seconds_total','input_tokens','output_tokens','thought_tokens','termination','failure_reason','paid_spend_usd']
    with (destination or OUT/'per-example.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for r in rows:
            row={k:r.get(k,'') for k in fields}
            row.update({'attempt_count':len(r['attempts']),'http_status':r['attempts'][-1]['http_status'],
                        'route_seconds_total':round(sum(a['elapsed_seconds'] for a in r['attempts']),3)})
            row['input_tokens'],row['output_tokens'],row['thought_tokens']=usage_tokens(r)
            row['failure_reason']=(r.get('incomplete_details') or {}).get('reason','')
            writer.writerow(row)


def plot_results(summary):
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,
                         'axes.spines.right':False,'pdf.fonttype':42,'svg.fonttype':'none','svg.hashsalt':'decision-context-pilot-v1'})
    figures=OUT/'figures';figures.mkdir(exist_ok=True)
    fig,(a,b)=plt.subplots(1,2,figsize=(12,4.8),gridspec_kw={'width_ratios':[1,1.1]})
    for i,p in enumerate(['jevmodel','openai']):
        vals=summary['primary'][p]; y=np.arange(4)+(i-.5)*.16
        mid=np.array([vals[c]['balanced_accuracy'] for c in CONDITIONS]);lo=np.array([vals[c]['ba_cluster95'][0] for c in CONDITIONS]);hi=np.array([vals[c]['ba_cluster95'][1] for c in CONDITIONS])
        a.errorbar(mid,y,xerr=[mid-lo,hi-mid],fmt=['o','s'][i],capsize=3,color=COLORS[p],label=NAMES[p],markersize=6)
        cs=CONDITIONS[1:]; yy=np.arange(3)+(i-.5)*.16
        mid=np.array([vals[c]['delta_ba'] for c in cs]);lo=np.array([vals[c]['delta_cluster95'][0] for c in cs]);hi=np.array([vals[c]['delta_cluster95'][1] for c in cs])
        b.errorbar(mid,yy,xerr=[mid-lo,hi-mid],fmt=['o','s'][i],capsize=3,color=COLORS[p],markersize=6)
    a.set(yticks=np.arange(4),yticklabels=[LABELS[c] for c in CONDITIONS],xlim=(-.03,1.03),xlabel='Balanced accuracy',title='Detection on 18 held-out emails');a.invert_yaxis()
    b.set(yticks=np.arange(3),yticklabels=[LABELS[c] for c in CONDITIONS[1:]],xlim=(-.55,.55),xlabel='Change from candidate only (percentage points)',title='Paired effect of revealing context');b.invert_yaxis();b.axvline(0,color='#444444',lw=1)
    a.xaxis.set_major_formatter(PercentFormatter(1));b.xaxis.set_major_formatter(PercentFormatter(1,decimals=0,symbol=' pp'))
    for axis in [a,b]:axis.grid(axis='x',color='#e5e5e5',lw=.7);axis.set_axisbelow(True)
    fig.legend(*a.get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.095),ncol=2,frameon=False)
    fig.text(.5,.035,'Bars: 95% paired cluster bootstrap; 9 attack teams + 1 related benign fixture.\nZero-error intervals collapse; one benign cluster and one task limit uncertainty estimation.',ha='center',fontsize=9,color='#444444')
    fig.subplots_adjust(left=.14,right=.98,top=.88,bottom=.30,wspace=.52)
    for ext in ['png','pdf','svg']:
        path=figures/('context-effects.'+ext)
        metadata={'Date':None} if ext=='svg' else ({'CreationDate':None,'ModDate':None} if ext=='pdf' else {})
        fig.savefig(path,dpi=180,facecolor='white',metadata=metadata)
        if ext=='svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)
    fig,axes=plt.subplots(1,2,figsize=(11,4.8),sharex=True,sharey=True)
    for axis,p in zip(axes,['jevmodel','openai']):
        vals=summary['primary'][p]
        for metric,offset,marker,color,label in [('fpr',-.10,'o',COLORS[p],'False positive'),('fnr',.10,'s','#555555','False negative')]:
            mid=np.array([vals[c][metric] for c in CONDITIONS]);bounds=np.array([vals[c][metric+'_wilson95'] for c in CONDITIONS])
            axis.errorbar(mid,np.arange(4)+offset,xerr=[mid-bounds[:,0],bounds[:,1]-mid],fmt=marker,color=color,capsize=3,label=label)
        axis.set(title=NAMES[p],xlim=(-.03,1.03),xlabel='Error rate among valid outputs',yticks=np.arange(4),yticklabels=[LABELS[c] for c in CONDITIONS]);axis.grid(axis='x',color='#e5e5e5');axis.xaxis.set_major_formatter(PercentFormatter(1))
    axes[0].invert_yaxis()
    fig.legend(*axes[0].get_legend_handles_labels(),loc='lower center',bbox_to_anchor=(.5,.09),ncol=2,frameon=False)
    fig.text(.5,.035,'Bars: descriptive Wilson 95% intervals; related fixtures violate the independence assumption. Gold N=9/class.\nGPT candidate-only FNR uses 8 valid attacks; 1 truncated response is excluded here and counted incorrect in accuracy.',ha='center',fontsize=9,color='#444444')
    fig.subplots_adjust(left=.15,right=.98,top=.88,bottom=.29,wspace=.15)
    for ext in ['png','pdf','svg']:
        path=figures/('error-rates.'+ext)
        metadata={'Date':None} if ext=='svg' else ({'CreationDate':None,'ModDate':None} if ext=='pdf' else {})
        fig.savefig(path,dpi=180,facecolor='white',metadata=metadata)
        if ext=='svg':path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)


def write_report(summary,rows):
    lines=['# Decision Context Benchmark — pilot results','',
           'This report is generated from saved provider responses. The primary sample has 18 emails (9 recorded successful attacks, 9 published benign fixtures), 9 attack-team groups, one benign-fixture group and one trusted task. Development data is excluded.','',
           '| Model / condition | Valid / N | Balanced accuracy (cluster 95% CI) | FP / benign | FN / attacks |',
           '| --- | --- | --- | --- | --- |']
    for p,conds in summary['primary'].items():
        for c,m in conds.items():
            lo,hi=m['ba_cluster95']
            lines.append(f"| {NAMES[p]} / {LABELS[c]} | {m['valid_n']}/{m['n']} | {m['balanced_accuracy']:.1%} ({lo:.1%}–{hi:.1%}) | {m['fp']}/{m['negative_n']} | {m['fn']}/{m['positive_n']} |")
    lines+=['','Observed change: both models score 94.4% strict balanced accuracy with the candidate alone and 100% in each context condition on this fixture. For Jev, one false negative changes to YES (score 0.48 alone, 0.54–0.56 with context). For GPT, the difference is one candidate-only response truncated after spending all 128 output tokens on reasoning; all 17 valid candidate-only answers were correct. These are different failure modes, not evidence that context improves semantic classification equally for both models.','',
            'All three within-model gains are +5.6 percentage points with a paired cluster 95% interval of 0.0 to +16.7 points. There were no observed false positives. Zero-error bootstrap intervals collapse and do not establish certainty; the Wilson upper bound for 0/9 observed errors is about 29.9% under its independence assumption.','',
            'The GPT candidate-only valid-output FNR denominator is 8, with one additional invalid attack response. All other class denominators are 9. The strict primary metric includes that invalid as incorrect.']
    lines+=['','## Paired changes','','Each interval uses the same cluster resamples for the context and candidate-only conditions. These are exploratory comparisons.','',
            '| Model | Context | BA change | Cluster 95% CI | Improved / worsened emails |','| --- | --- | --- | --- | --- |']
    for p,conds in summary['primary'].items():
        for c in CONDITIONS[1:]:
            m=conds[c];lo,hi=m['delta_cluster95']
            lines.append(f"| {NAMES[p]} | {LABELS[c]} | {m['delta_ba']*100:+.1f} pp | {lo*100:+.1f} to {hi*100:+.1f} pp | {m['improved_n']} / {m['worsened_n']} |")
    lines+=['','## Gemini subpanel','','Only four held-out candidates were planned for Gemini, with all four conditions. Compare every provider on identical candidates, not against its full-panel score. If this table has no rows, the original route did not reach evaluation; see the substitution section below.','',
            '| Provider | Condition | Valid / N | Balanced accuracy |','| --- | --- | --- | --- |']
    for p,conds in summary['shared_subpanel'].items():
        for c,m in conds.items():lines.append(f"| {NAMES[p]} | {LABELS[c]} | {m['valid_n']}/{m['n']} | {m['balanced_accuracy']:.1%} |")
    lines+=['','## Access, usage and completion','',
            'Credentials were reused locally; current catalog authentication succeeded for both chat routes. Actual development/evaluation responses establish inference access. Jev identity is the independent reseller’s reported version; the upstream weights are not attested. Exact returned IDs and settings are preserved in records.','',
            '```json',json.dumps(summary['operations'],indent=2),'```','',
            f"Missing planned records: {len(summary['missing'])}. All HTTP attempts, including any retries, are retained in the raw records. Route timings include network/reseller/provider overhead and are not intrinsic model speeds.",'',
            '## Representative errors and transitions','']
    errors=[r for r in rows if r['split']=='eval' and (not r['valid'] or r['prediction']!=r['gold'])]
    selected=[];seen=set()
    # Include each distinct erroneous candidate/model; inspect its exact linked raw request.
    for r in sorted(errors,key=lambda r:(r['provider'],r['id'],r['condition'])):
        key=(r['provider'],r['id'])
        if key not in seen:seen.add(key);selected.append(r)
    if not selected:lines+=['No classification errors were observed in the saved evaluation records. This is a small selected fixture, so that does not establish robust detection.']
    for r in selected[:8]:
        request=r['request']
        state=request['state'] if r['provider']=='jevmodel' else (request['input'][0]['content'] if r['provider']=='openai' else request['contents'][0]['parts'][0]['text'])
        candidate=json.loads(state)['CANDIDATE_EMAIL']
        # Excerpts are source text, not generated replacement examples or relabels.
        lines+=[f"- **{r['provider']} / {r['id']} / {r['condition']}**: gold={r['gold']}, prediction={r['prediction']}, status={r['status']}. [Raw request/response](../../{r['record']}).",f"  Source excerpt: {candidate[:420].replace(chr(10),' ')}"]
    lines+=['','## Interpretation limits and next experiment','',
            'The intervals are conditional on a single task and a small selected sample. All benign examples share a source theme; its cluster bootstrap can be degenerate. Wilson intervals describe a stronger independence assumption and are included only as a small-sample warning. No interval estimates generalization to new benign domains. Public-data contamination and historical-success selection remain possible. Model probabilities are uncalibrated, and interface/provider differences prevent attributing differences to specialization alone.','',
            'Revealing context does not alter the original gold label: the target is the same whole email in the same original scenario. These results cannot establish sentence-level labels, task-dependent relabeling, end-to-end agent safety or full-document context effects.','',
            'The next useful experiment is to obtain multiple independent published task/source fixtures with human-validated candidate labels, keep teams and source families grouped, and expand paired evaluation across genuinely varied tasks and ambiguous benign instructions. Check an adequate chat output/reasoning budget using development data before the next evaluation, to distinguish semantic errors from truncation. Recheck Gemini availability on a later date and expand its common panel rather than treating four cases as a reliable model ranking.','',
            '## Figures','','![Balanced accuracy and paired changes](figures/context-effects.png)','','![False-positive and false-negative rates](figures/error-rates.png)','','Offline reproduction and live-run commands are in the root README.']
    (OUT/'report.md').write_text('\n'.join(lines)+'\n')


def main():
    rows,expected,seen=load_records();write_table(rows)
    evaluation=[r for r in rows if r['split']=='eval']
    summary={'primary':{},'shared_subpanel':{},'cross_model':{},'operations':{},'substitution':{},
             'missing':[{'provider':k[0],'id':k[1],'condition':k[2]} for k in sorted(set(expected)-seen)],
             'bootstrap':{'draws':10000,'seed':20261026,'method':'paired, stratified by label, resample team/source-fixture clusters'}}
    draws={}
    for p in ['jevmodel','openai']:
        conds={c:[r for r in evaluation if r['provider']==p and r['condition']==c] for c in CONDITIONS}
        summary['primary'][p],draws[p]=paired_summary(conds)
    for c in CONDITIONS:
        summary['cross_model'][c]={'gpt_minus_jev':summary['primary']['openai'][c]['balanced_accuracy']-summary['primary']['jevmodel'][c]['balanced_accuracy'],
                                 'cluster95':interval(np.array(draws['openai'][c])-np.array(draws['jevmodel'][c]))}
    gemini_ids={r['id'] for r in evaluation if r['provider']=='gemini'}
    if gemini_ids:
        # Only complete condition pairs enter the common descriptive subpanel.
        shared={i for i in gemini_ids if all(any(r['provider']==p and r['id']==i and r['condition']==c for r in evaluation) for p in MODELS for c in CONDITIONS)}
        if shared and {r['gold'] for r in evaluation if r['id'] in shared}=={0,1}:
            for p in MODELS:
                conds={c:[r for r in evaluation if r['provider']==p and r['condition']==c and r['id'] in shared] for c in CONDITIONS}
                summary['shared_subpanel'][p]=paired_summary(conds)[0]
    for p in MODELS:
        selected=[r for r in rows if r['provider']==p]
        attempts=[a for r in selected for a in r['attempts']]
        balances=[int(a['response_headers']['x-tokens-remaining']) for a in attempts if 'x-tokens-remaining' in a.get('response_headers',{})]
        usage=[usage_tokens(r) for r in selected]
        summary['operations'][p]={'records':len(selected),'attempts':len(attempts),'status_counts':dict(Counter(r['status'] for r in selected)),
             'returned_models':sorted({r['returned_model'] for r in selected if r.get('returned_model')}),
             'reported_input_tokens':sum(u[0] or 0 for u in usage),'reported_output_tokens':sum(u[1] or 0 for u in usage),
             'median_route_seconds':statistics.median([sum(a['elapsed_seconds'] for a in r['attempts']) for r in selected]) if selected else None,
             'free_jev_balance_min':min(balances) if balances else None,'paid_api_spend_usd':sum(r['paid_spend_usd'] for r in selected)}
    supplement_rows=summarize_substitution(summary,rows)
    write_table(rows+supplement_rows)
    # Reject NaN/Infinity rather than serializing invalid JSON.
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True,allow_nan=False)+'\n')
    plot_results(summary);write_report(summary,rows)
    supplement_report(summary)
    print(json.dumps({'primary_plan_records':len(rows),'total_records':len(rows)+len(supplement_rows),'missing_original_plan':len(summary['missing']),'summary':'results/pilot/summary.json'}))



def summarize_substitution(summary,main_rows):
    path=OUT/'gemini-3.7-plan.json'
    if not path.exists():return []
    frozen=json.loads(path.read_text())
    assert frozen['protocol_sha256']==sha((ROOT/'docs/gemini-substitution.md').read_bytes())
    assert frozen['original_plan_sha256']==sha((OUT/'frozen-plan.json').read_bytes())
    expected={(r['id'],r['condition']):r for r in frozen['requests']}
    rows=[]
    for file in sorted((OUT/'gemini-3.7-records').glob('*.json')):
        r=json.loads(file.read_text());key=(r['id'],r['condition'])
        assert key in expected and expected[key]['request_sha256']==sha(json.dumps(r['request'],sort_keys=True,ensure_ascii=False))
        if r['attempts'][-1]['http_status']==200 and r['status']!='parse_or_version_error':
            parsed=parse_response('gemini',r['attempts'][-1]['raw_body'],expected_model='gemini-3.7-flash')
            assert parsed['prediction']==r['prediction'] and parsed['valid']==r['valid']
        r['record']=str(file.relative_to(ROOT));rows.append(r)
    assert len(rows)<=20
    ids={r['id'] for r in rows if r['split']=='eval'}
    complete={i for i in ids if all(any(r['id']==i and r['condition']==c for r in rows if r['split']=='eval') for c in CONDITIONS)}
    result={'model':'gemini-3.7-flash','records':len(rows),'missing_records':len(expected)-len(rows),
            'status_counts':dict(Counter(r['status'] for r in rows)),'shared_subpanel':{},
            'paid_api_spend_usd':sum(r['paid_spend_usd'] for r in rows),
            'reported_input_tokens':sum(usage_tokens(r)[0] or 0 for r in rows),
            'reported_output_tokens':sum(usage_tokens(r)[1] or 0 for r in rows),
            'returned_models':sorted({r['returned_model'] for r in rows if r.get('returned_model')})}
    if complete and {r['gold'] for r in rows if r['id'] in complete}=={0,1}:
        for p in ['jevmodel','openai','gemini-3.7']:
            data=rows if p=='gemini-3.7' else main_rows
            conds={c:[r for r in data if r['provider']==p and r['split']=='eval' and r['condition']==c and r['id'] in complete] for c in CONDITIONS}
            result['shared_subpanel'][p]=paired_summary(conds)[0]
    summary['substitution']=result
    if rows:
        write_table(rows,OUT/'gemini-3.7-per-example.csv')
    return rows


def supplement_report(summary):
    result=summary['substitution']
    if not result:return
    lines=['','## Explicit Gemini substitution','',
           'Gemini 3.8 Flash produced capacity errors/timeouts during development. A separately saved protocol tried catalog-listed Gemini 3.7 Flash through the same free project. The prompts and four selected evaluation cases were unchanged. The original failed route and substitution are retained separately; no model was silently replaced.','',
           '```json',json.dumps({k:v for k,v in result.items() if k!='shared_subpanel'},indent=2),'```','']
    if not result['shared_subpanel']:
        lines+=['The substitute did not complete the common evaluation panel. There is no three-model accuracy comparison. The completed primary experiment is Jev versus GPT-6 Luna.']
    else:
        lines+=['All providers below are evaluated on the same four held-out emails; N=4 is too small for a model ranking.','',
                '| Model | Condition | Valid / N | Balanced accuracy (cluster 95% CI) |','| --- | --- | --- | --- |']
        for p,conds in result['shared_subpanel'].items():
            for c,m in conds.items():
                lo,hi=m['ba_cluster95'];name=NAMES.get(p,'Gemini 3.7 Flash (free API)')
                lines.append(f"| {name} | {LABELS[c]} | {m['valid_n']}/{m['n']} | {m['balanced_accuracy']:.1%} ({lo:.1%}–{hi:.1%}) |")
    with (OUT/'report.md').open('a') as f:f.write('\n'.join(lines)+'\n')


if __name__=='__main__':main()
