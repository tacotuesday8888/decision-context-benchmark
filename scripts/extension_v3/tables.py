"""Readable source-specific tables from verified complete-arm analyses."""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / 'results/extension-v3/analysis'
CONFIGS = ('jev_firstparty', 'luna_decisions', 'laya_local', 'nimble_local', 'luna_chat', 'astra_chat', 'protectai_local')


def write(name, rows, fields):
    with (DIRECTORY / name).open('w') as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator='\n')
        writer.writeheader()
        writer.writerows(rows)


def main():
    primary, controls, conditions, inputs = [], [], [], {}
    for config in CONFIGS:
        path = DIRECTORY / (config + '.json')
        if not path.exists():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        receipt = json.loads((DIRECTORY / (config + '-verification.json')).read_text())
        assert receipt['status'] == 'passed' and receipt['analysis_sha256'] == digest
        report = json.loads(path.read_text())
        inputs[config] = digest
        for stratum in report['strata']:
            for condition in stratum['conditions']:
                row = dict(config=config, dataset=stratum['dataset'])
                row.update({k: condition[k] for k in ['condition', 'planned', 'valid', 'abstentions', 'operational_or_missing', 'negative_valid', 'positive_valid', 'false_positives', 'false_negatives', 'fpr', 'fnr', 'balanced_accuracy']})
                row.update({k: condition['forecast'][k] for k in ['n_forecasts', 'brier', 'log_loss']})
                row.update(accuracy_lower=condition['accuracy_bounds_all_planned'][0], accuracy_upper=condition['accuracy_bounds_all_planned'][1])
                conditions.append(row)
            for effect in stratum['paired_effects']:
                weighted = effect['task_weighted'] or {}
                interval = weighted.get('interval') or [None, None]
                bounds = effect['all_planned_task_weighted_bounds'] or [None, None]
                row = dict(config=config, dataset=stratum['dataset'], metric=effect['metric'], left=effect['left'], right=effect['right'],
                    complete_pairs=effect['complete_pairs'], planned_pairs=effect['planned_pairs'],
                    task_weighted=weighted.get('estimate'), text_weighted=effect['text_weighted_estimate'],
                    interval_lower=interval[0], interval_upper=interval[1], interval_status=weighted.get('interval_status'),
                    task_groups=weighted.get('task_groups'), secondary_groups=weighted.get('second_axis_groups'),
                    missing_bound_lower=bounds[0], missing_bound_upper=bounds[1])
                (primary if effect['scope'] == 'full_collection' else controls).append(row)
    effect_fields = ['config', 'dataset', 'metric', 'left', 'right', 'complete_pairs', 'planned_pairs',
        'task_weighted', 'text_weighted', 'interval_lower', 'interval_upper', 'interval_status',
        'task_groups', 'secondary_groups', 'missing_bound_lower', 'missing_bound_upper']
    write('primary-effects.csv', primary, effect_fields)
    write('control-effects.csv', controls, effect_fields)
    write('source-metrics.csv', conditions, list(conditions[0]))
    (DIRECTORY / 'table-inputs.json').write_text(json.dumps({'scope': 'Completed arms only; error effects are fractions, not percentage points. Negative task-minus-comparator effects favor task.',
        'analysis_sha256': inputs, 'script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'primary_rows': len(primary), 'control_rows': len(controls), 'condition_rows': len(conditions)}, indent=2, sort_keys=True) + '\n')
    print(json.dumps({'primary_rows': len(primary), 'control_rows': len(controls), 'condition_rows': len(conditions)}))


if __name__ == '__main__':
    main()
