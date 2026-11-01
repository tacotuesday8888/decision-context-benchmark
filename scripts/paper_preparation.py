"""Presentation-only tables and figures from frozen results; no inference or fitting."""
import csv
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'results/paper-preparation'
INPUTS = [
    'results/study-v7-execution/shared-primary-confusion.csv',
    'results/study-v7-execution/tables/primary-contrasts.csv',
    'results/subscription-followup-execution/core-analysis-v1.json',
    'results/subscription-followup-execution/core-contrasts-v1.csv',
    'results/subscription-followup-extensions-execution/source.json',
]
NAMES = {'jev_firstparty': 'Jev', 'luna_decisions': 'GPT-6 Luna (Decisions)', 'sol_subscription': 'GPT-6.1 Sol'}
CONDITIONS = {'format': 'Empty task', 'task': 'User task', 'reminder': 'Generic reminder', 'length': 'Character filler'}


def read_csv(path):
    return list(csv.DictReader((ROOT / path).open()))


def write_csv(name, rows):
    with (OUT / name).open('w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def save(fig, name):
    for fmt in ('png', 'pdf', 'svg'):
        fig.savefig(OUT / f'{name}.{fmt}', dpi=200, facecolor='white', bbox_inches='tight')
        if fmt == 'svg':
            path = OUT / f'{name}.{fmt}'
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines()) + '\n')
    plt.close(fig)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'svg.fonttype': 'none', 'pdf.fonttype': 42})
    rates = []
    for row in read_csv(INPUTS[0]):
        n = int(row['shared_complete_groups'])
        fp, fn, tp, tn = (int(row[k]) for k in ('fp', 'fn', 'tp', 'tn'))
        assert n == 2850 and fp + tn == fn + tp == n
        assert abs(fp/n - float(row['fpr'])) < 1e-12
        assert abs(fn/n - float(row['fnr'])) < 1e-12
        assert abs((fp+fn)/(2*n) - float(row['balanced_error'])) < 1e-12
        rates.append(dict(model=NAMES[row['config']], condition=row['condition'], groups=n,
                          false_alarms=fp, missed_attacks=fn, clean_pages=n, attacked_pages=n,
                          false_alarm_percent=100*fp/n, missed_attack_percent=100*fn/n,
                          balanced_error_percent=50*(fp+fn)/n))
    core = json.loads((ROOT / INPUTS[2]).read_text())['main']
    for condition, row in core['sol_complete8_metrics'].items():
        n = row['valid_clean']
        assert n == row['valid_attack'] == 498
        fp, fn = round(row['fpr']*n), round(row['fnr']*n)
        assert abs((fp+fn)/(2*n) - row['balanced_error']) < 1e-12
        rates.append(dict(model='GPT-6.1 Sol', condition=condition, groups=n,
                          false_alarms=fp, missed_attacks=fn, clean_pages=n, attacked_pages=n,
                          false_alarm_percent=100*fp/n, missed_attack_percent=100*fn/n,
                          balanced_error_percent=50*(fp+fn)/n))
    write_csv('error-rates.csv', rates)
    effects = []
    for row in read_csv(INPUTS[1]):
        effects.append(dict(source='BrowseSafe++', model=NAMES[row['config']], control=row['control'],
                            groups=int(row['primary_complete_groups']),
                            reduction_pp=float(row['estimate_pp']),
                            lower95_pp=float(row['pointwise_95_lower_pp']),
                            upper95_pp=float(row['pointwise_95_upper_pp']),
                            holm_p=row['holm6_adjusted_p']))
    for row in read_csv(INPUTS[3]):
        if row['type'] == 'Sol contrast' and row['cohort'] == 'primary_complete8':
            effects.append(dict(source='BrowseSafe++', model='GPT-6.1 Sol', control=row['control'],
                                groups=int(row['n']), reduction_pp=100*float(row['mean']),
                                lower95_pp=100*float(row['lower95']), upper95_pp=100*float(row['upper95']), holm_p=''))
    for e in effects:
        r = {r['condition']: r for r in rates if r['model'] == e['model']}
        assert abs(r[e['control']]['balanced_error_percent']-r['task']['balanced_error_percent']-e['reduction_pp']) < 1e-10
    source = json.loads((ROOT / INPUTS[4]).read_text())
    for row in source['contrasts']:
        x = row['primary_shared16']
        effects.append(dict(source='DTap (secondary)', model=NAMES[row['config']], control=row['control'],
                            groups=x['cohort']['n'], reduction_pp=100*x['mean'],
                            lower95_pp=100*x['pointwise_95'][0], upper95_pp=100*x['pointwise_95'][1], holm_p=''))
    assert len(effects) == 15 and len(rates) == 12
    write_csv('context-effects.csv', effects)

    fig, axes = plt.subplots(1, 3, figsize=(11, 4.4), sharex=True, sharey=True)
    for ax, model in zip(axes, ('Jev', 'GPT-6 Luna (Decisions)', 'GPT-6.1 Sol')):
        rows = {r['condition']: r for r in rates if r['model'] == model}
        for y, key in enumerate(('false_alarm_percent', 'missed_attack_percent')):
            a, b = rows['format'][key], rows['task'][key]
            ax.plot([a,b], [y,y], color='#999999', lw=2)
            ax.plot(a,y,'o',mfc='white',mec='#333333',ms=8)
            ax.plot(b,y,'s',color='#28658A',ms=7)
            ax.annotate(f'{a:.2f}%',(a,y),xytext=(0,12),textcoords='offset points',ha='center',fontsize=9)
            ax.annotate(f'{b:.2f}%',(b,y),xytext=(0,-20),textcoords='offset points',ha='center',fontsize=9)
        ax.set_title(f'{model}\nn = {rows["task"]["groups"]:,} groups', fontsize=11)
        ax.set_xlim(0,26); ax.set_ylim(1.5,-.5)
        ax.set_xticks([0,5,10,15,20,25]); ax.grid(axis='x',alpha=.2)
        ax.set_xlabel('Error within each class (%)')
    axes[0].set_yticks([0,1], ['Clean-labeled pages\nflagged as attacks', 'Attack-labeled pages\nmissed'])
    fig.legend(handles=[plt.Line2D([],[],marker='o',mfc='white',mec='#333333',ls='',label='Empty task'),
                        plt.Line2D([],[],marker='s',color='#28658A',ls='',label='User task')],loc='upper center',ncol=2,frameon=False)
    fig.subplots_adjust(top=.75,bottom=.25,left=.16,wspace=.15)
    fig.text(.16,.04,'Publisher labels. Each group has one clean and one attacked page. Descriptive rates only.\n'
             'Native models share 2,850 groups; Sol uses 498 groups from a 500-group subset. Not a matched model ranking.',fontsize=8)
    save(fig,'figure-2-error-tradeoff')

    for source_name, filename, models, limits in [
        ('BrowseSafe++','figure-3-context-effects',('Jev','GPT-6 Luna (Decisions)','GPT-6.1 Sol'),(-3.5,3.5)),
        ('DTap (secondary)','supplement-second-source',('Jev','GPT-6.1 Sol'),(-10,18))]:
        fig, axes = plt.subplots(1,len(models),figsize=(11,4.2),sharex=True,sharey=True)
        for ax, model in zip(axes,models):
            rows={e['control']:e for e in effects if e['source']==source_name and e['model']==model}
            for y,c in enumerate(('format','reminder','length')):
                e=rows[c]; m=e['reduction_pp']; lo=e['lower95_pp']; hi=e['upper95_pp']
                ax.errorbar(m,y,xerr=[[m-lo],[hi-m]],fmt='o',color='#28658A',capsize=4)
                ax.annotate(f'{m:+.2f}',(m,y),xytext=(0,9),textcoords='offset points',ha='center',fontsize=9)
            ax.axvline(0,color='#555555',lw=1);ax.set_xlim(*limits);ax.set_ylim(2.6,-.6)
            ax.set_title(f'{model}\nn = {e["groups"]:,} groups',fontsize=11)
            ax.grid(axis='x',alpha=.2);ax.set_xlabel('Balanced-error reduction\n(percentage points)')
        axes[0].set_yticks(range(3),['Against empty task','Against reminder','Against filler'])
        fig.suptitle(source_name+': effect of adding the user task',x=.16,ha='left',fontsize=14)
        fig.subplots_adjust(top=.75,bottom=.27,left=.16,wspace=.17)
        note=('Native panels share 2,850 groups; Sol has a separate 498-group cohort. Not a model ranking. '
              'Only native tests have Holm adjustment.' if source_name=='BrowseSafe++' else
              '62 shared complete groups of 66 planned; 64/66 planned groups are legal-domain cases. Descriptive, not pooled with main results.')
        fig.text(.16,.015,'Balanced error = (false-alarm rate + missed-attack rate) / 2. Positive = task lowers this average.\nLines: saved pointwise 95% group-bootstrap intervals.\n'
                 +note+'\nMissing-outcome bounds use a different, all-planned cohort; see source tables. No new statistical fitting.',fontsize=8)
        save(fig,filename)

    fig, ax = plt.subplots(figsize=(10,3.2)); ax.set_xlim(0,10);ax.set_ylim(0,3.2);ax.axis('off')
    boxes=[(.1,1.1,2.0,1.1,'Same saved page\n(clean or attacked)'),
           (2.7,.4,3.1,2.5,'Four input versions\n\nEmpty task field\nOriginal user task\nGeneric reminder\nCharacter-matched filler'),
           (6.4,1.1,1.5,1.1,'Fixed model\nand settings'),
           (8.5,1.1,1.4,1.1,'Record\njudgment')]
    for x,y,w,h,label in boxes:
        ax.add_patch(FancyBboxPatch((x,y),w,h,boxstyle='round,pad=.04',fc='#f4f6f8',ec='#28658A'))
        ax.text(x+w/2,y+h/2,label,ha='center',va='center',fontsize=10)
    for a,b in [(2.1,2.7),(5.8,6.4),(7.9,8.5)]:
        ax.annotate('',xy=(b-.06,1.65),xytext=(a+.06,1.65),arrowprops=dict(arrowstyle='->',color='#333333'))
    ax.text(5,0,'Main study design: candidate text stays identical across conditions. Existing models; no new model training.',ha='center',fontsize=9)
    save(fig,'figure-1-design')
    manifest={'purpose':'Pre-paper figures and tables only; no manuscript, inference, relabeling or statistical refit',
              'inputs':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in INPUTS},
              'outputs':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.suffix in ('.png','.pdf','.svg','.csv')},
              'matplotlib':matplotlib.__version__, 'effect_direction':'control minus task; positive favors task',
              'rates_checked_against_counts':12,'effects_checked_against_rate_tables':9,
              'secondary_effects_copied_without_refit':6}
    (OUT/'render-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Prepared 12 rate rows, 15 effect rows, three main figures and one secondary figure.')


if __name__ == '__main__':
    main()
