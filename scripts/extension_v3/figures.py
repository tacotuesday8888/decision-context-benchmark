"""Source-specific effect plots from verified completed arms; no pooled score."""
import hashlib
import json
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'results/extension-v3/analysis'
ORDER = ['jev_firstparty', 'luna_decisions', 'laya_local', 'nimble_local', 'luna_chat', 'astra_chat']
LABELS = {'jev_firstparty': 'Jev 1.14.0', 'luna_decisions': 'Luna Decisions', 'laya_local': 'Laya multilingual', 'nimble_local': 'Nimble Q4_K_M', 'luna_chat': 'Luna Responses', 'astra_chat': 'Astra Responses'}


def main():
    reports = []
    for config in ORDER:
        path = DIRECTORY / (config + '.json')
        if not path.exists():
            continue
        receipt = json.loads((DIRECTORY / (config + '-verification.json')).read_text())
        assert receipt['analysis_sha256'] == hashlib.sha256(path.read_bytes()).hexdigest()
        reports.append(json.loads(path.read_text()))
    assert reports
    plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(len(reports), 2, figsize=(15, 4.2 * len(reports)), squeeze=False)
    evidence = {}
    for i, report in enumerate(reports):
        evidence[report['config']] = hashlib.sha256((DIRECTORY / (report['config'] + '.json')).read_bytes()).hexdigest()
        for j, metric in enumerate(['error', 'brier']):
            ax = axes[i, j]
            ax.axvline(0, color='#9aa3ad', linewidth=1)
            labels = []
            for y, stratum in enumerate(report['strata']):
                label = stratum['dataset'].replace('agentdojo-clean-', 'Dojo ').replace('agentdyn-', 'Dyn ').replace('injecagent-', 'Injec ')
                effects = [x for x in stratum['paired_effects'] if x['scope'] == 'full_collection' and x['metric'] == metric]
                labels.append(label)
                if not effects or not effects[0]['task_weighted']:
                    ax.text(.5, y, 'No native probabilities' if metric == 'brier' else 'No complete pairs', transform=ax.get_yaxis_transform(), ha='center', color='#777777')
                    continue
                effect = effects[0]
                point = effect['task_weighted']
                value = 100 * point['estimate'] if metric == 'error' else point['estimate']
                scale = 100 if metric == 'error' else 1
                interval = point['interval']
                if interval:
                    ax.plot([interval[0] * scale, interval[1] * scale], [y, y], color='#347488', linewidth=2)
                ax.plot(value, y, 'o' if interval else 'D', color='#163c4a', markersize=5)
                labels[-1] += f" ({effect['complete_pairs']}/{effect['planned_pairs']})"
            ax.set_yticks(range(len(labels)), labels)
            ax.invert_yaxis()
            ax.grid(axis='x', alpha=.2)
            ax.set_title(LABELS[report['config']] + (' — decision error' if metric == 'error' else ' — Brier loss'), loc='left', weight='bold')
            ax.set_xlabel('Task − candidate (percentage points)' if metric == 'error' else 'Task − candidate (Brier units)')
    for j in range(2):
        limits = [ax.get_xlim() for ax in axes[:, j]]
        for ax in axes[:, j]:
            ax.set_xlim(min(v[0] for v in limits), max(v[1] for v in limits))
    fig.suptitle('Authentic task context: source-specific paired effects\nCompleted contextual arms only; negative values favor task context', fontsize=16, y=.995)
    fig.text(.01, .006, 'Each task receives equal weight. Lines: conditional 95% crossed bootstrap intervals (5,000 draws). Diamonds: too few groups for an interval.\nLabels show complete/planned pairs. Intervals condition on the released fixtures/templates; no pooled winner or unseen-environment claim.', fontsize=10)
    fig.tight_layout(rect=(0, .055, 1, .955))
    target = ROOT / 'results/extension-v3/figures'
    target.mkdir(exist_ok=True)
    fig.savefig(target / 'completed-arm-effects.png', dpi=170)
    fig.savefig(target / 'completed-arm-effects.svg')
    svg = target / 'completed-arm-effects.svg'
    svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines()) + '\n')
    plt.close(fig)
    (target / 'figure-inputs.json').write_text(json.dumps({'analysis_sha256': evidence, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), 'scope': 'Completed verified contextual arms only; specialist has no context contrast.'}, indent=2, sort_keys=True) + '\n')


if __name__ == '__main__':
    main()
