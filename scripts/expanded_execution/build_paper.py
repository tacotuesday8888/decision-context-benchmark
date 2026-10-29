"""Render a traceable Markdown and PDF draft from saved numerical artifacts.

Run with the bundled Python runtime (reportlab), or a Python with reportlab installed.
No credentials, network access, models, or inference dependencies are required.
"""
from pathlib import Path
import hashlib
import json
import re
from xml.sax.saxutils import escape
from reportlab import rl_config
rl_config.invariant = 1
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, KeepTogether
from reportlab.lib.pagesizes import A4

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/expanded-execution'
PAPER=ROOT/'paper'
NAMES={'jev_firstparty':'Jev 1.14','luna_decisions':'Luna Decisions','luna_chat':'Luna Responses','astra_chat':'Astra Responses','nimble_local':'Nimble Q4','laya_local':'Laya','protectai_local':'Protect AI'}
SOURCES={'bipia-code':'BIPIA code','bipia-email':'BIPIA email','bipia-table':'BIPIA table','llmail-task2':'LLMail task 2','llmail-task3':'LLMail task 3','llmail-task4':'LLMail task 4','llmail-benign-stress':'LLMail stress'}


def read(path):return json.loads(path.read_text())
def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def pct(v):return '--' if v is None else f'{100*v:.2f}'
def num(v):return '--' if v is None else f'{v:.4f}'
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','| '+' | '.join(['---']*len(headers))+' |']+['| '+' | '.join(map(str,r))+' |' for r in rows])
def ci(bounds,scale=1):return '--' if bounds is None else f'[{bounds[0]*scale:.3f}, {bounds[1]*scale:.3f}]'


def content():
    summary=read(OUT/'summary.json'); forecasts=read(OUT/'forecast-summary.json'); research=read(OUT/'research-summary.json')
    rows=[json.loads(x) for x in (ROOT/'data/expanded-v2/collection.jsonl').read_text().splitlines()]
    evalrows=[r for r in rows if r['split']=='eval'];devrows=[r for r in rows if r['split']=='dev']
    assert len(evalrows)==402 and len(devrows)==60
    missing=summary['status_counts'].get('not_run',0)
    status=f"INTERIM DRAFT: {summary['observed_logical_cells']} / {summary['planned_logical_cells']} logical cells are represented in the classification snapshot; {missing} remain unrun. Analyses may have different interim capture times. Do not treat this as a completed experiment." if missing else f"RESEARCH DRAFT: all {summary['planned_logical_cells']} planned logical cells are represented, including preserved failures. This is not a claim that every cell returned a valid prediction."
    data=[]
    for source in SOURCES:
        rs=[r for r in evalrows if r['dataset']==source];n0=sum(r['gold']==0 for r in rs)
        data.append([SOURCES[source],n0,len(rs)-n0,len(rs),' / '.join(sorted({c for r in rs for c in r['conditions']}))])
    panels=read(ROOT/'data/expanded-v2/model-panel.json')['configurations']
    local={c:read(ROOT/path)['configuration'] for c,path in [('nimble_local','results/nimble-setup/execution-config.json'),('laya_local','results/laya-v2/execution-config.json')]}
    models=[]
    for c in NAMES:
        p=local[c] if c in local else panels[c]
        route='Local' if c.endswith('_local') else ('Subscription Responses' if c.endswith('_chat') else 'First-party API')
        models.append([NAMES[c],p['model'],route,'Boolean' if c.endswith('_chat') else 'Native score'])
    cover=[]
    for c in NAMES:
        ss=[s for s in summary['summaries'] if s['config']==c]
        planned=sum(s['n'] for s in ss);notrun=sum(s['not_run_n'] for s in ss);invalid=sum(s['invalid_n'] for s in ss)
        cover.append([NAMES[c],planned,planned-notrun,planned-notrun-invalid,invalid,notrun])
    complete=[c for c in summary['paired_contrasts'] if c['status']=='complete' and c['contrast']=='task minus candidate' and c['metric']=='balanced accuracy']
    effectrows=[]
    for c in complete:
        interval=c['intervals'].get('document',c['intervals'].get('class_clusters',{})).get('interval')
        effectrows.append([NAMES[c['config']],SOURCES[c['dataset']],pct(c['base']['strict_balanced_accuracy']),pct(c['context']['strict_balanced_accuracy']),f"{100*c['strict_correctness_delta']:+.2f}",ci(interval,100)])
    fs=[c for c in forecasts['paired_contrasts'] if c['execution_complete'] and c['contrast']=='task minus candidate']
    briers=[[NAMES[c['config']],SOURCES[c['dataset']],f"{c['common_score_n']}/{c['eligible_n']}",num(c['base']['brier']),num(c['context']['brier']),num(c['brier_delta']),ci(c['intervals'][0]['interval'])] for c in fs]
    op=[]
    for r in research['operations']:
        op.append([NAMES[r['config']],r['saved_attempt_records'],num(r['elapsed_median_seconds']),num(r['elapsed_p90_seconds']),r['known_input_tokens'] if r['usage_records_n'] else '--',f"{r['usage_records_n']}/{r['saved_attempt_records']}"])
    review=read(OUT/'error-review.json')
    wanted={('jev_firstparty','corrected'),('luna_decisions','regressed'),('laya_local','persistent_false_alarm'),('nimble_local','regressed')}
    example_rows=[[NAMES[e['config']],e['category'].replace('_',' '),e['id'],e['gold'],num(e['candidate_score']),num(e['task_score'])] for e in review['examples'] if (e['config'],e['category']) in wanted]
    windows=next(o['native_forward_windows'] for o in research['operations'] if o['config']=='protectai_local')
    # Restrict prose examples to the already complete first-party arms; expose source.
    ex={(c['config'],c['dataset']):c for c in complete}
    j=ex[('jev_firstparty','bipia-code')];l=ex[('luna_decisions','bipia-email')]
    abstract=f"In the completed first-party arms, task context changes Jev's BIPIA code balanced accuracy by {100*j['strict_correctness_delta']:+.2f} percentage points and Luna Decisions' BIPIA email balanced accuracy by {100*l['strict_correctness_delta']:+.2f} points, illustrating source-dependent effects."
    resulttext=f"The table includes {len(complete)} completed two-class comparisons; incomplete strata are excluded from effect claims, not removed from coverage accounting. Numerical direction and uncertainty must be read by source. The first-party arms each retain 812 cells; Jev's exact-0.5 forecasts are classification abstentions rather than false probability records."
    source_order=('bipia-code','bipia-email','bipia-table')
    per_model=[]
    for config in NAMES:
        available=[ex[config,source] for source in source_order if (config,source) in ex]
        if available:
            values=', '.join(f"{SOURCES[c['dataset']]} {100*c['strict_correctness_delta']:+.2f} pp" for c in available)
            per_model.append(f"{NAMES[config]}: {values}.")
    resulttext+=' Across completed BIPIA strata, task-context changes are '+ ' '.join(per_model)
    forecast_lines=[]
    for config in NAMES:
        available=[c for c in fs if c['config']==config and c['dataset'] in source_order]
        if available:
            forecast_lines.append(NAMES[config]+': '+', '.join(f"{SOURCES[c['dataset']]} {c['brier_delta']:+.4f}" for c in available)+'.')
    forecast_text='Task-minus-candidate Brier changes in completed BIPIA strata are '+ ' '.join(forecast_lines)+' Negative values indicate smaller probability error. These changes describe forecast quality; reliability bins must still be inspected because Brier score combines calibration and discrimination. All source-specific values, common-subset counts and uncertainty are retained below.'
    for config in ('laya_local','nimble_local'):
        strata=[s for s in forecasts['summaries'] if s['config']==config and s['dataset']=='bipia-code' and s['condition']=='candidate' and s['missing_score_n']==0]
        if strata:
            bucket=max(strata[0]['calibration'],key=lambda b:b['n'])
            forecast_text+=f" For {NAMES[config]} on BIPIA code, the largest candidate-only probability bin contains {bucket['n']} examples: mean predicted attack probability {bucket['mean_predicted_attack_probability']:.3f}, observed attack fraction {bucket['observed_attack_fraction']:.3f}. This is an empirical bin comparison, not a population calibration guarantee."
    cost=research['all_in_accounted_usd']
    discussion=f"Task context is not uniformly beneficial across the completed comparisons. The BIPIA code improvement for Jev and email decrease for Luna Decisions exemplify why a global winner would be misleading. The study's conservative all-in accounted metered usage is ${cost['openai']:.6f} for OpenAI and ${cost['typesafe']:.6f} for TypeSafe, including earlier checks and retained reservations; these are ledger estimates, not reconciled invoices. Provider limits remain $15 and $20 respectively."
    reproduction='Offline regeneration sequence: `analyze.py`, `forecast_analysis.py`, `research_summaries.py`, `error_review.py`, `verify_analysis.py`, `paper_figures.py`, and `build_paper.py` in `scripts/expanded_execution/`. The analysis and figure scripts use the project environment; the PDF build additionally requires ReportLab. Run the execution, local-arm, preparation and pilot tests/verifiers before delivery. No regeneration command calls a model.'
    mapping={'forecast_text':forecast_text,'local_window_note':f'The specialist baseline contains 402 logical candidate scans and {windows} actual forward windows; scans, forward windows, candidate counts and remote attempt records are different units.','example_table':table(['Configuration','Category','Candidate ID','Gold','p candidate','p task'],example_rows),'status':status,'abstract_results':abstract,'data_table':table(['Source','Benign','Attack','Total','Conditions'],data),'model_table':table(['Configuration','Exact model ID','Route','Output'],models),'coverage_table':table(['Configuration','Planned','Recorded','Valid','Invalid / tie','Not run'],cover),'results_text':resulttext,'effect_table':table(['Configuration','Source','BA candidate %','BA task %','Delta pp','95% CI pp'],effectrows),'brier_table':table(['Configuration','Source','Common / eligible','Brier candidate','Brier task','Delta','95% CI'],briers),'operations_table':table(['Configuration','Attempt records','Median s','P90 s','Known input tokens','Usage records'],op),'discussion_text':discussion,'reproduction':reproduction}
    text=(PAPER/'manuscript-template.md').read_text()
    for k,v in mapping.items():text=text.replace('{{'+k+'}}',v)
    assert '{{' not in text
    return text


def render(text,path):
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='BodyAcademic',fontName='Times-Roman',fontSize=10.5,leading=14,spaceAfter=7))
    styles.add(ParagraphStyle(name='CaptionAcademic',fontName='Times-Italic',fontSize=9,leading=11.5,spaceAfter=9))
    styles.add(ParagraphStyle(name='CellAcademic',fontName='Helvetica',fontSize=7.2,leading=9))
    styles['Title'].fontName='Times-Bold';styles['Title'].fontSize=19;styles['Title'].leading=22
    styles['Heading2'].fontName='Times-Bold';styles['Heading2'].fontSize=13;styles['Heading2'].leading=16
    width=A4[0]-100;story=[];lines=text.splitlines();i=0
    def para(s,style='BodyAcademic'):
        s=escape(s.replace('—','-').replace('–','-')).replace('`','')
        return Paragraph(s,styles[style])
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line.startswith('# '):story.append(para(line[2:],'Title'));i+=1;continue
        if line.startswith('## '):story.append(para(line[3:],'Heading2'));i+=1;continue
        if line.startswith('| '):
            raw=[]
            while i<len(lines) and lines[i].startswith('| '):
                cols=[x.strip() for x in lines[i].strip('|').split('|')]
                if not all(x=='---' for x in cols):raw.append(cols)
                i+=1
            cells=[[para(c,'CellAcademic') for c in row] for row in raw]
            n=len(raw[0]);weights=[1]*n
            if n>=6:weights=[1.25,1.1]+[1]*(n-2)
            if n==4:weights=[1,2.3,1.1,.8]
            tw=Table(cells,colWidths=[width*w/sum(weights) for w in weights],repeatRows=1,hAlign='LEFT')
            tw.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#EDF1F4')),('VALIGN',(0,0),(-1,-1),'TOP'),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#607080')),('LINEBELOW',(0,-1),(-1,-1),.4,colors.HexColor('#607080')),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5)]))
            j=i
            while j<len(lines) and not lines[j].strip():j+=1
            caption=None
            if j<len(lines) and lines[j].startswith('Table '):
                caption=para(lines[j],'CaptionAcademic');i=j+1
            block=([caption] if caption else [])+[tw,Spacer(1,10)]
            story.append(KeepTogether(block)) if len(raw)<=10 else story.extend(block)
            continue
        if line.startswith('!['):
            m=re.match(r'!\[.*?\]\((.*?)\)',line);img=(PAPER/m.group(1)).resolve()
            iw,ih=ImageReader(str(img)).getSize();w=width;h=w*ih/iw
            if h>370:w*=370/h;h=370
            story.append(Image(str(img),width=w,height=h));i+=1;continue
        parts=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![')):
            parts.append(lines[i].strip());i+=1
        textblock=' '.join(parts)
        story.append(para(textblock,'CaptionAcademic' if textblock.startswith(('Figure ','Table ')) else 'BodyAcademic'))
    def footer(canvas,doc):
        canvas.saveState();canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#52606C'))
        canvas.drawString(50,28,'Decision Context Benchmark - private research draft')
        canvas.drawRightString(A4[0]-50,28,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=46,bottomMargin=45,title='Trusted task context and prompt-injection judgments',author='Decision Context Benchmark')
    doc.build(story,onFirstPage=footer,onLaterPages=footer)


def main():
    text=content();(PAPER/'manuscript.md').write_text(text)
    dest=ROOT/'output/pdf';dest.mkdir(parents=True,exist_ok=True)
    render(text,dest/'decision-context-benchmark-draft.pdf')
    inputs=[PAPER/'manuscript-template.md',OUT/'summary.json',OUT/'forecast-summary.json',OUT/'research-summary.json',OUT/'error-review.json',ROOT/'data/expanded-v2/collection.jsonl',Path(__file__)]
    inputs+=sorted((OUT/'paper-figures').glob('*.png'))
    (PAPER/'build-manifest.json').write_text(json.dumps({'input_sha256':{str(p.relative_to(ROOT)):digest(p) for p in inputs},'output_sha256':{str(p.relative_to(ROOT)):digest(p) for p in [PAPER/'manuscript.md',dest/'decision-context-benchmark-draft.pdf']},'numerical_tables_generated':True,'evaluation_complete':read(OUT/'summary.json')['status_counts'].get('not_run',0)==0},indent=2)+'\n')
    print(json.dumps({'markdown':str(PAPER/'manuscript.md'),'pdf':str(dest/'decision-context-benchmark-draft.pdf')}))

if __name__=='__main__':main()
