"""Completed-route source-specific control contrasts and absolute error rates."""
import hashlib,json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/controls-v4'
ORDER=['jev_firstparty','luna_decisions','laya_local','nimble_local','luna_chat','astra_chat']
LABELS=['Jev 1.14','Luna Decisions','Laya multilingual','Nimble Q4_K_M','Luna chat','Astra chat']
SOURCES=['tasktracker-qa-advbench','aib-static-stress']
TITLES=['TaskTracker QA: 27 article clusters','AIB static fixtures: 17 tasks, only 3 benign']
COLORS={'reminder':'#007991','format':'#b15b00','candidate':'#5d61a6','scrambled':'#768237'}

def main():
    reports={};hashes={}
    for config in ORDER+['protectai_local']:
        p=OUT/'analysis'/(config+'.json')
        if not p.exists():continue
        digest=hashlib.sha256(p.read_bytes()).hexdigest()
        receipt=json.loads((OUT/'analysis'/(config+'-verification.json')).read_text())
        assert receipt['analysis_sha256']==digest
        reports[config]=json.loads(p.read_text());hashes[config]=digest
    contextual=[c for c in ORDER if c in reports]
    assert contextual,'Need a completed contextual arm'
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':'decision-context-controls-v4'})
    target=OUT/'figures';target.mkdir(exist_ok=True)
    for metric in ['error','brier']:
        fig,axes=plt.subplots(1,2,figsize=(14,7),squeeze=False)
        for source,title,ax in zip(SOURCES,TITLES,axes[0]):
            ax.axvline(0,color='#aaa',lw=1)
            for i,config in enumerate(contextual):
                stratum=next(s for s in reports[config]['strata'] if s['dataset']==source)
                for j,control in enumerate(COLORS):
                    effect=next((e for e in stratum['paired_effects'] if e['scope']=='all_confirmation' and e['left']==control and e['metric']==metric),None)
                    if not effect or not effect['primary_cluster_weighted']:continue
                    point=effect['primary_cluster_weighted'];y=i+(j-1.5)*.17;scale=100 if metric=='error' else 1
                    ci=point['interval']
                    if ci:ax.plot([v*scale for v in ci],[y,y],color=COLORS[control],lw=1.7)
                    ax.plot(point['estimate']*scale,y,'o' if ci else 'D',color=COLORS[control],ms=5,label=control if i==0 else None)
            ax.set_yticks(range(len(contextual)),[LABELS[ORDER.index(c)] for c in contextual]);ax.invert_yaxis();ax.set_title(title,loc='left');ax.grid(axis='x',alpha=.15)
            ax.set_xlabel('Control error − task error (percentage points)' if metric=='error' else 'Control Brier loss − task Brier loss')
        handles,labels=axes[0,0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='upper center',ncol=4,bbox_to_anchor=(.5,.94))
        fig.suptitle('Does the authentic task outperform the controls?\nPositive values favor the authentic task',fontsize=16,y=.995)
        fig.text(.025,.015,'QA: equal article weights. AIB: equal task weights. Pointwise conditional 95% crossed-bootstrap intervals; diamonds omit insufficient-group intervals.\nPublished construction labels; fixed broad attack family. Completed routes only. Boolean chat outputs have no Brier scores.',fontsize=9)
        fig.tight_layout(rect=(0,.075,1,.88));save(fig,target/('controls-'+metric))
    configs=[c for c in ORDER+['protectai_local'] if c in reports]
    names={**dict(zip(ORDER,LABELS)),'protectai_local':'ProtectAI (candidate only)'}
    conditions=['candidate','task','format','reminder','scrambled']
    fig,axes=plt.subplots(2,2,figsize=(13,10))
    for j,source in enumerate(SOURCES):
        for i,metric in enumerate(['fpr','fnr']):
            matrix=[]
            for config in configs:
                s=next(s for s in reports[config]['strata'] if s['dataset']==source)
                by={c['condition']:c for c in s['conditions']}
                matrix.append([float('nan') if c not in by or by[c][metric] is None else by[c][metric]*100 for c in conditions])
            ax=axes[i,j];im=ax.imshow(matrix,vmin=0,vmax=100,cmap='YlOrRd',aspect='auto')
            for r,row in enumerate(matrix):
                for c,value in enumerate(row):
                    if value==value:ax.text(c,r,f'{value:.1f}',ha='center',va='center',fontsize=9,color='white' if value>65 else '#222')
            ax.set_xticks(range(5),conditions,rotation=25,ha='right');ax.set_yticks(range(len(configs)),[names[c] for c in configs]);ax.set_title(TITLES[j]+'\n'+('False positives (%)' if metric=='fpr' else 'False negatives (%)'),fontsize=11)
    fig.suptitle('Absolute errors against published construction labels',fontsize=16)
    fig.text(.02,.01,'Valid predictions only; missing and abstention denominators are in the accompanying tables. These rates are unweighted per text.\nAIB false positives have only three benign fixtures. Blank cells are unsupported conditions, not zero error.',fontsize=9)
    fig.tight_layout(rect=(0,.065,1,.95));save(fig,target/'absolute-errors')
    (target/'figure-inputs.json').write_text(json.dumps({'analysis_sha256':hashes,'script_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'scope':'Completed verified routes; no pooled scores.'},indent=2,sort_keys=True)+'\n')

def save(fig,path):
    fig.savefig(str(path)+'.png',dpi=170)
    fig.savefig(str(path)+'.svg',metadata={'Date':None})
    p=Path(str(path)+'.svg');p.write_text('\n'.join(line.rstrip() for line in p.read_text().splitlines())+'\n');plt.close(fig)
if __name__=='__main__':main()
