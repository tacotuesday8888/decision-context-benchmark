"""Presentation-only error decomposition from frozen same-cohort counts."""
import argparse
import csv
import io
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from scripts.critical_review.verify import ROOT, read, sha, write_new


def render(output):
    native_path = ROOT / 'results/study-v7-execution/shared-primary-confusion.csv'
    sol_path = ROOT / 'results/subscription-followup-execution/core-analysis-v1.json'
    with native_path.open() as stream:
        native = list(csv.DictReader(stream))
    sol = read(sol_path)['main']['sol_complete8_metrics']
    conditions = ('format', 'reminder', 'length', 'task')
    data = []
    for model, title in [('jev_firstparty', 'Jev'), ('luna_decisions', 'Luna Decisions')]:
        rows = {r['condition']: r for r in native if r['config'] == model}
        assert len(rows) == 4 and all(int(r['shared_complete_groups']) == 2850 for r in rows.values())
        data.append((title, 2850, [(int(rows[c]['fp']), int(rows[c]['fn'])) for c in conditions]))
    data.append(('Sol subscription', 498, [(round(sol[c]['fpr'] * 498), round(sol[c]['fnr'] * 498)) for c in conditions]))
    assert all(sol[c]['valid_clean'] == sol[c]['valid_attack'] == 498 for c in conditions)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.9), sharex=True, sharey=True)
    for ax, (title, n, values) in zip(axes, data):
        for y, (fp, fn) in enumerate(values):
            ax.plot([100 * fp / n], [y - .12], 'o', color='#ac4934', markersize=7)
            ax.plot([100 * fn / n], [y + .12], 's', color='#265d91', markersize=6)
            ax.annotate(f'{fp}/{n}', (100 * fp / n, y - .12), xytext=(5, -3), textcoords='offset points', fontsize=8)
            ax.annotate(f'{fn}/{n}', (100 * fn / n, y + .12), xytext=(5, -3), textcoords='offset points', fontsize=8)
        ax.set_title(f'{title}\n{n:,} complete groups', fontsize=11, loc='left')
        ax.set_xlim(0, 31)
        ax.set_xticks([0, 10, 20, 30])
        ax.grid(axis='x', color='#dddddd')
        ax.set_axisbelow(True)
        ax.set_xlabel('Class-specific error (%)')
        ax.spines[['top', 'right']].set_visible(False)
    axes[0].set_yticks(range(4), ['Empty task', 'Generic reminder', 'Character filler', 'Published task'])
    axes[0].invert_yaxis()
    handles = [plt.Line2D([], [], marker='o', color='#ac4934', ls='', label='False alarms / clean pages'),
               plt.Line2D([], [], marker='s', color='#265d91', ls='', label='Missed attacks / attacked pages')]
    fig.legend(handles=handles, loc='lower left', bbox_to_anchor=(.12, .16), ncol=2, frameon=False)
    fig.suptitle('Task information changes both kinds of error', x=.12, ha='left', fontsize=15)
    fig.text(.12, .06, 'BrowseSafe++ publisher labels; counts are descriptive, with no new intervals. Each class has n pages.\n'
             'Native panels share 2,850 groups. Sol uses a separate 498-group subset; this is not a matched ranking.\n'
             'Paired effect intervals and all-planned missingness bounds remain in the original result records.', fontsize=9, color='#444444')
    fig.subplots_adjust(left=.13, right=.99, top=.80, bottom=.33, wspace=.18)
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=180, facecolor='white', metadata={'Software': 'Decision Context Benchmark'})
    plt.close(fig)
    output.mkdir(parents=True, exist_ok=True)
    path = output / 'error-tradeoffs.png'
    if path.exists():
        assert path.read_bytes() == buf.getvalue()
    else:
        with path.open('xb') as stream:
            stream.write(buf.getvalue())
    write_new(output / 'figure-provenance.json', {'version': 'critical-review-tradeoff-figure-1',
              'inputs': {str(p.relative_to(ROOT)): sha(p) for p in (native_path, sol_path)},
              'figure_sha256': sha(path), 'matplotlib': matplotlib.__version__,
              'new_estimation': False, 'source_counts': data})
    print(path)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    render(parser.parse_args().output)
