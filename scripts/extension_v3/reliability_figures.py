"""Descriptive fixed-bin reliability panels; no fitted calibration or pooled curve."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
ANALYSIS = ROOT / 'results/extension-v3/analysis'
OUT = ROOT / 'results/extension-v3/figures'
MODELS = {'jev_firstparty': 'Jev 1.14.0', 'luna_decisions': 'Luna Decisions',
          'laya_local': 'Laya multilingual', 'nimble_local': 'Nimble Q4_K_M',
          'protectai_local': 'ProtectAI window maximum'}


def main():
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': 'extension-v3-reliability'})
    inputs = {}
    for config, title in MODELS.items():
        path = ANALYSIS / (config + '.json')
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        receipt = json.loads((ANALYSIS / (config + '-verification.json')).read_text())
        assert receipt['analysis_sha256'] == digest
        report = json.loads(path.read_text())
        inputs[config] = digest
        fig, axes = plt.subplots(3, 3, figsize=(12, 11), sharex=True, sharey=True)
        for ax, stratum in zip(axes.flat, report['strata']):
            ax.plot([0, 1], [0, 1], '--', color='#aaaaaa', linewidth=1)
            counts = []
            for condition, color, marker in [('candidate', '#297d99', 'o'), ('task', '#bd5f24', 'D')]:
                records = [r for r in stratum['conditions'] if r['condition'] == condition]
                if not records:
                    continue
                scores = records[0]['forecast']
                counts.append(f"{condition} n={scores['n_forecasts']}")
                points = [r for r in scores['reliability'] if r['n']]
                ax.scatter([r['mean_score'] for r in points], [r['observed_fraction'] for r in points],
                    s=[14 + 2 * r['n'] for r in points], color=color, marker=marker,
                    alpha=.65, edgecolors='white', linewidth=.5,
                    label=f"{condition}: {scores['n_forecasts']} forecasts")
            ax.set_xlim(-.04, 1.04)
            ax.set_ylim(-.04, 1.04)
            ax.set_xticks([0, .25, .5, .75, 1])
            ax.set_yticks([0, .25, .5, .75, 1])
            ax.grid(alpha=.15)
            ax.set_title(stratum['dataset'].replace('agentdojo-clean-', 'Dojo ').replace('agentdyn-', 'Dyn ').replace('injecagent-', 'Injec ') + '\n' + ' / '.join(counts), loc='left', fontsize=10)
        for ax in axes[-1]:
            ax.set_xlabel('Mean reported P(injection) / score')
        for ax in axes[:, 0]:
            ax.set_ylabel('Observed injection fraction')
        fig.suptitle(title + ' — source-specific reliability\nCompleted arm; ten fixed bins, no calibration fitting', fontsize=16)
        fig.text(.02, .012, 'Marker area = 14 + 2 × bin count; circles: candidate, diamonds: task. Exact 0.5 forecasts are included.\nDescriptive bin averages have no uncertainty bands. Single-class strata lie at 0 or 1 by construction.\nRepeated texts/tasks and public fixture labels limit interpretation; detector window maxima are not calibrated probabilities.', fontsize=10)
        fig.tight_layout(rect=(0, .085, 1, .94))
        fig.savefig(OUT / (config + '-reliability.png'), dpi=150)
        svg = OUT / (config + '-reliability.svg')
        fig.savefig(svg, metadata={'Date': None})
        svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
        plt.close(fig)
    (OUT / 'reliability-inputs.json').write_text(json.dumps({'analysis_sha256': inputs, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'completed_native_score_arms': list(inputs)}))


if __name__ == '__main__':
    main()
