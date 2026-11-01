"""Publication figures from saved analytical artifacts; no model calls."""
import json
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from execute import OUT,DATA,jsonl,save,sha

DEST=OUT/'paper-figures'
NAMES={'jev_firstparty':'Jev 1.14','luna_decisions':'Luna Decisions','luna_chat':'Luna Responses','astra_chat':'Astra Responses','nimble_local':'Nimble Q4','laya_local':'Laya','protectai_local':'Protect AI'}
SOURCES={'bipia-code':'BIPIA code','bipia-email':'BIPIA email','bipia-table':'BIPIA table','llmail-task2':'LLMail task 2','llmail-task3':'LLMail task 3','llmail-task4':'LLMail task 4','llmail-benign-stress':'LLMail benign stress'}
COLORS={'candidate':'#276A92','task':'#C06725','source':'#38856A','both':'#87579B'}
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none','svg.hashsalt':'decision-context-benchmark-paper-v1','savefig.facecolor':'white'})


def export(fig,name):
    DEST.mkdir(exist_ok=True)
    for ext in ('png','svg'):fig.savefig(DEST/(name+'.'+ext),dpi=180,bbox_inches='tight',metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)


def coverage(rows):
    fig,ax=plt.subplots(figsize=(9,4.3),layout='constrained')
    sources=list(SOURCES)
    for i,d in enumerate(sources):
        s=[r for r in rows if r['dataset']==d];n0=sum(r['gold']==0 for r in s);n1=len(s)-n0
        ax.barh(i,n0,color='#276A92',label='Benign' if i==0 else None)
        ax.barh(i,n1,left=n0,color='#C06725',label='Attack' if i==0 else None)
        ax.text(len(s)+2,i,f'{n0} / {n1}',va='center',fontsize=8)
    ax.set_yticks(range(len(sources)),[SOURCES[x] for x in sources]);ax.invert_yaxis()
    ax.set_xlim(0,148);ax.set_xlabel('Distinct evaluation candidates (labels at right: benign / attack)')
    ax.legend(loc='lower right',frameon=False);ax.set_title('402 candidates across seven source strata')
    counts={axis:len({r['groups'][axis] for r in rows if axis in r['groups']}) for axis in ('document','attack_family','team','fixture','topic')}
    fig.text(.25,-.06,f"Related units: {counts['document']} BIPIA documents / {counts['attack_family']} attack families;"
             f" {counts['team']} LLMail teams / {counts['fixture']} fixtures / {counts['topic']} topics.\nThese overlapping grouping axes are not additive independent samples.",fontsize=8)
    export(fig,'coverage')


def trust_boundary():
    fig,ax=plt.subplots(figsize=(10,4.2));ax.axis('off');ax.set_xlim(0,10);ax.set_ylim(0,4.2)
    boxes=[(.1,2.65,2.6,1.05,'Trusted original task\nRevealed only in task / both','#E7F1F5'),(.1,.65,2.6,1.35,'Untrusted source material\nSame candidate across conditions\nNeighbor only when available','#FFF0E3'),(3.6,1.25,2.65,1.75,'Frozen detector input\nExplicitly labeled trust roles\nNo gold label or outcome\nNo task execution','#EDF0F2'),(7.2,1.25,2.65,1.75,'Saved decision\nBoolean or native probability\nIdentity, usage and failures\nPaired source-specific analysis','#EAF2EC')]
    for x,y,w,h,t,c in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=0.04',facecolor=c,edgecolor='#7D8790'))
        ax.text(x+w/2,y+h/2,t,ha='center',va='center',fontsize=8)
    for a,b in [((2.75,3.15),(3.55,2.6)),((2.75,1.3),(3.55,1.7)),((6.3,2.1),(7.15,2.1))]:ax.annotate('',xy=b,xytext=a,arrowprops={'arrowstyle':'->','color':'#44515B','lw':1.5})
    ax.text(5,.15,'Detection experiment: no protected assistant, tool execution, or measured attack prevention',ha='center',fontsize=10)
    export(fig,'trust-boundary')


def document_interval(contrast):
    intervals=contrast['intervals']
    return intervals['document']['interval'] if isinstance(intervals,dict) else next(x['interval'] for x in intervals if x['axis']=='document')


def effects(summary,forecast):
    fig,axs=plt.subplots(1,2,figsize=(12,7.2),layout='constrained')
    for ax,items,value,key,title,scale in [
        (axs[0],summary['paired_contrasts'],'strict_correctness_delta','status','Task-context effect on detection',100),
        (axs[1],forecast['paired_contrasts'],'brier_delta','execution_complete','Task-context effect on Brier score',1)]:
        xs=[c for c in items if c['contrast']=='task minus candidate' and c['dataset'].startswith('bipia-') and (c.get(key)=='complete' if key=='status' else c.get(key))]
        for i,c in enumerate(xs):
            v=c[value]*scale;ax.plot(v,i,'o',color='#276A92',markersize=5)
            ci=document_interval(c)
            if ci:ax.plot(np.array(ci)*scale,[i,i],color='#276A92',lw=1.5)
        ax.set_yticks(range(len(xs)),[NAMES[c['config']]+' / '+SOURCES[c['dataset']].replace('BIPIA ','') for c in xs],fontsize=8)
        ax.invert_yaxis();ax.axvline(0,color='#777777',lw=.8);ax.set_title(title)
        ax.set_xlabel('Balanced accuracy change (percentage points)\nPositive is better' if scale==100 else 'Mean squared probability error change\nNegative is better')
    fig.suptitle('Completed BIPIA contrasts; 95% paired document-bootstrap intervals',fontsize=12)
    export(fig,'paired-effects')


def reliability(forecast):
    for config in ['jev_firstparty','luna_decisions','nimble_local','laya_local','protectai_local']:
        fig,axs=plt.subplots(2,4,figsize=(12,6.2),layout='constrained')
        for ax,dataset in zip(axs.flat,list(SOURCES)):
            ax.plot([0,1],[0,1],color='#888888',ls='--',lw=.7)
            denominators=[]
            for condition in ('candidate','task'):
                ss=[s for s in forecast['summaries'] if s['config']==config and s['dataset']==dataset and s['condition']==condition]
                if not ss:continue
                s=ss[0];denominators.append(f'{condition}: {s["n"]}/{s["eligible_n"]}');bs=[b for b in s['calibration'] if b['n']]
                if not bs:continue
                x=[b['mean_predicted_attack_probability'] for b in bs];y=[b['observed_attack_fraction'] for b in bs]
                ax.plot(x,y,'o-',color=COLORS[condition],lw=1,ms=4,label=f'{condition}: {s["n"]}/{s["eligible_n"]}')
                for b,px,py in zip(bs,x,y):
                    ci=b['observed_fraction_intervals'][0].get('interval')
                    if ci:ax.vlines(px,*ci,color=COLORS[condition],alpha=.5,lw=2)
                    ax.annotate(str(b['n']),(px,py),xytext=(3,5 if condition=='candidate' else -10),textcoords='offset points',fontsize=6,color=COLORS[condition])
            ax.set_title(SOURCES[dataset]+'\n'+'; '.join(denominators),fontsize=8);ax.set_xlim(-.06,1.06);ax.set_ylim(-.14,1.13);ax.set_xticks([0,.5,1]);ax.set_yticks([0,.5,1])
        axs.flat[-1].axis('off');axs.flat[-1].text(0,.95,'Blue: candidate; orange: task\nFive fixed probability bins\nNumbers by points: bin counts\nTitles: scored / eligible\nBars: cluster-bootstrap intervals\nAbsent CI: too few clusters\nZero-height CI: no sampled variation\n\nOne-class strata cannot establish\nreliability over both labels.',va='top',fontsize=9)
        fig.supxlabel('Mean predicted attack probability');fig.supylabel('Observed attack fraction')
        fig.suptitle(NAMES[config]+' — probability reliability')
        export(fig,'reliability-'+config)


def errors(summary):
    fig,axs=plt.subplots(1,2,figsize=(12,6.2),layout='constrained')
    configs=list(NAMES);sources=list(SOURCES)
    for ax,key,title in zip(axs,['valid_fpr','valid_fnr'],['False alarms on benign candidates','Missed attacks']):
        grid=np.full((len(configs),len(sources)),np.nan)
        for i,c in enumerate(configs):
            for j,d in enumerate(sources):
                ss=[s for s in summary['summaries'] if s['config']==c and s['dataset']==d and s['condition']=='candidate']
                if not ss:continue
                s=ss[0]
                if not s['not_run_n'] and s[key] is not None:grid[i,j]=s[key]
        cmap=plt.get_cmap('YlOrRd').copy();cmap.set_bad('#EEEEEE')
        ax.imshow(grid,vmin=0,vmax=1,cmap=cmap,aspect='auto')
        for i in range(len(configs)):
            for j in range(len(sources)):
                v=grid[i,j];ax.text(j,i,'—' if np.isnan(v) else f'{100*v:.0f}%',ha='center',va='center',fontsize=8,color='white' if v>.65 else '#222222')
        ax.set_xticks(range(len(sources)),[SOURCES[s].replace('LLMail ','').replace('BIPIA ','') for s in sources],rotation=50,ha='right',fontsize=8)
        ax.set_yticks(range(len(configs)),[NAMES[c] for c in configs],fontsize=9);ax.set_title(title,fontsize=11)
    fig.suptitle('Candidate-only valid-decision error rates; gray = undefined or incomplete',fontsize=12)
    export(fig,'candidate-errors')


def main():
    rows=[r for r in jsonl(DATA/'collection.jsonl') if r['split']=='eval']
    summary=json.loads((OUT/'summary.json').read_text());forecast=json.loads((OUT/'forecast-summary.json').read_text())
    coverage(rows);trust_boundary();effects(summary,forecast);reliability(forecast);errors(summary)
    save(DEST/'inputs.json',{str(p.relative_to(OUT)):sha(p.read_bytes()) for p in [OUT/'summary.json',OUT/'forecast-summary.json']})
    print(json.dumps({'figures':len(list(DEST.glob('*.png'))),'directory':str(DEST)}))

if __name__=='__main__':main()
