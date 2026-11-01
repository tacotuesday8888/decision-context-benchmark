"""Render technical comparison figures from closed, saved analysis only."""
from __future__ import annotations

import argparse
import io
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

from scripts.study_v7.requests import canonical, digest
from scripts.subscription_followup.prepare import write_once


BLUE = '#265d91'
GOLD = '#b88928'
LABELS = {'format': 'Format', 'reminder': 'Reminder', 'length': 'Length'}
MODELS = {'sol_subscription': 'Sol', 'jev_firstparty': 'Jev', 'luna_decisions': 'Luna Decisions'}


def panel(ax, entries, cohort_key, *, interaction=False):
    """Keep confidence intervals and finite error bounds visually distinct."""
    labels = []
    for y, entry in enumerate(entries):
        value = entry[cohort_key]
        bounds = entry['all_planned_missing_error_bounds']['range']
        prefix = (MODELS[entry['native']] + ': ') if interaction else (
            MODELS[entry['config']] + ': ' if len(entries) > 3 else '')
        labels.append(prefix + LABELS[entry['control']] + f" − task (n={value['n']})")
        if bounds is not None:
            ax.plot([100*x for x in bounds], [y+.10]*2, color=GOLD, lw=5, alpha=.45,
                    solid_capstyle='butt')
        if value['pointwise_95'] is not None:
            ax.plot([100*x for x in value['pointwise_95']], [y-.08]*2, color=BLUE, lw=1.7)
        if value['mean'] is not None:
            ax.scatter([100*value['mean']], [y-.08], color=BLUE, marker='o', s=30, zorder=3)
    ax.axvline(0, color='#4c4c4c', lw=.8, ls='--')
    ax.set_yticks(range(len(labels)), labels)
    ax.invert_yaxis()
    ax.set_xlabel('Difference in balanced error (percentage points)')
    ax.grid(axis='x', color='#dddddd', lw=.6)
    ax.set_axisbelow(True)
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['left', 'bottom']].set_color('#aaaaaa')
    ax.tick_params(axis='both', labelsize=9)
    ax.margins(x=.15, y=.18)


def render(data, *, kind):
    fig, axes = plt.subplots(1, 2, figsize=(13, 5.6), gridspec_kw={'width_ratios': [1, 1.15]})
    if kind == 'core':
        main = data['main']
        panel(axes[0], main['sol_contrasts'], 'primary_complete8')
        panel(axes[1], main['direct_interactions'], 'primary_shared24', interaction=True)
        fig.suptitle('Locked 500-group subscription follow-up', fontsize=14, x=.04, ha='left')
        axes[0].set_title('Sol context effects', loc='left', fontsize=11)
        axes[1].set_title('Sol effect minus archived native effect', loc='left', fontsize=11)
        note = ('Positive context effects favor task context. Positive interactions mean greater task benefit in Sol.\n'
                'Archived native comparisons are nonconcurrent; model, route and time differ. Bounds retain all 500 groups.')
    else:
        source = data.get('source', data)
        panel(axes[0], source['contrasts'], 'primary_shared16')
        panel(axes[1], source['direct_interactions'], 'primary_shared16', interaction=True)
        fig.suptitle('Released simulated-service source: 66 groups', fontsize=14, x=.04, ha='left')
        axes[0].set_title('Source-condition context effects', loc='left', fontsize=11)
        axes[1].set_title('Sol effect minus Jev effect', loc='left', fontsize=11)
        note = ('Positive context effects favor task context. Labels describe released source conditions, not human semantic gold.\n'
                'Groups are mostly legal tasks; this selected source is descriptive. Bounds retain all 66 groups.')
    handles = [Line2D([0], [0], color=BLUE, marker='o', lw=1.7, label='Point estimate and pointwise 95% bootstrap interval'),
               Line2D([0], [0], color=GOLD, lw=5, alpha=.45, label='All-planned missing-error bounds (not a confidence interval)')]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(.035, .13), frameon=False, fontsize=9)
    fig.text(.04, .04, note, fontsize=8.5, linespacing=1.5, color='#444444')
    fig.subplots_adjust(left=.22, right=.98, bottom=.31, top=.84, wspace=1.0)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=180, facecolor='white', metadata={'Software': 'Decision Context Benchmark'})
    plt.close(fig)
    return buf.getvalue()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--core', type=Path)
    parser.add_argument('--extensions', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if not args.core and not args.extensions:
        parser.error('A saved closed analysis is required')
    proof = {'version': 'subscription-followup-figures-1', 'inputs': {}, 'outputs': {},
             'matplotlib': matplotlib.__version__, 'no_new_estimation': True}
    for kind, path in [('core', args.core), ('source', args.extensions)]:
        if path is None:
            continue
        body = path.read_bytes()
        data = json.loads(body)
        if data.get('bootstrap_draws') != 20000:
            raise ValueError('Production closed analysis with 20,000 draws required')
        if kind == 'core' and data.get('evidence', {}).get('core_completed') != 4510:
            raise ValueError('Full core evidence required')
        if kind == 'source' and not all(data.get('proof', {}).get(k) for k in
                ('stop_sha256', 'snapshot_sha256', 'journal_sha256', 'core_lineage_sha256')):
            raise ValueError('Closed extension evidence required')
        image = render(data, kind=kind)
        target = args.output / (kind + '-context-effects.png')
        if target.exists() and target.read_bytes() != image:
            raise ValueError('Refuse changed figure overwrite')
        write_once(target, image)
        proof['inputs'][kind] = {'path': str(path.resolve()), 'sha256': digest(body)}
        proof['outputs'][target.name] = digest(image)
    write_once(args.output / 'figure-provenance.json', canonical(proof) + b'\n')
    print(json.dumps(proof, indent=2))


if __name__ == '__main__':
    main()
