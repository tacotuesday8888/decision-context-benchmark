"""Frozen-protocol estimators; numerical arrays are not additional benchmark data."""
import math
import numpy as np


def valid_probability(value):
    return type(value) in (float, int) and math.isfinite(value) and 0 <= value <= 1


def losses(gold, score):
    if not valid_probability(score) or gold not in (0, 1):
        raise ValueError('Invalid forecast')
    p = min(1 - 1e-6, max(1e-6, score))
    return {'brier': (score - gold) ** 2,
            'log_loss': -math.log(p if gold else 1 - p)}


def task_mean(values, tasks):
    values = np.asarray(values, dtype=float)
    unique = sorted(set(tasks))
    if not len(values) or len(values) != len(tasks):
        raise ValueError('Nonempty paired values/groups required')
    return float(np.mean([np.mean(values[np.asarray(tasks) == task]) for task in unique]))


def text_mean(values, texts):
    return task_mean(values, texts)


def crossed_interval(values, tasks, second_groups, draws=5000, seed=20261029):
    """Task-weighted mean with crossed group multiplicities, fixed source/template.

    Reweight observations within each task by the second sampled grouping axis,
    then average those task means under the sampled task multiplicities.
    """
    values = np.asarray(values, dtype=float)
    if len(values) != len(tasks) or len(values) != len(second_groups) or not len(values):
        raise ValueError('Aligned nonempty inputs required')
    task_names, ti = np.unique(tasks, return_inverse=True)
    second_names, si = np.unique(second_groups, return_inverse=True)
    estimate = task_mean(values, tasks)
    leave_one_out = [task_mean(values[ti != index], np.asarray(tasks)[ti != index])
                     for index in range(len(task_names))] if len(task_names) > 1 else []
    result = {'estimate': estimate, 'n_pairs': len(values), 'task_groups': len(task_names),
              'second_axis_groups': len(second_names),
              'leave_one_task_out_range': [min(leave_one_out), max(leave_one_out)] if leave_one_out else None,
              'interval': None, 'draws': draws, 'degenerate_draws': 0,
              'scope': 'Conditional on released source fixtures, fixed templates and model version.'}
    if min(len(task_names), len(second_names)) < 5:
        result['interval_status'] = 'insufficient_groups_descriptive_only'
        return result
    rng = np.random.default_rng(seed)
    samples = []
    for _ in range(draws):
        tw = rng.multinomial(len(task_names), np.full(len(task_names), 1 / len(task_names)))
        sw = rng.multinomial(len(second_names), np.full(len(second_names), 1 / len(second_names)))
        weights = sw[si]
        denominator = np.bincount(ti, weights=weights, minlength=len(task_names))
        numerator = np.bincount(ti, weights=weights * values, minlength=len(task_names))
        usable = denominator > 0
        if not np.sum(tw[usable]):
            result['degenerate_draws'] += 1
            continue
        samples.append(float(np.average(numerator[usable] / denominator[usable], weights=tw[usable])))
    result['interval_status'] = 'conditional_crossed_percentile' if samples else 'all_draws_degenerate'
    result['interval'] = [float(x) for x in np.quantile(samples, [.025, .975])] if samples else None
    result['degenerate_interval'] = bool(samples and min(samples) == max(samples))
    return result


def classification(rows):
    n = len(rows)
    valid = [r for r in rows if r.get('valid') and r.get('prediction') in (0, 1)]
    negatives = [r for r in valid if r['gold'] == 0]
    positives = [r for r in valid if r['gold'] == 1]
    fp = sum(r['prediction'] == 1 for r in negatives)
    fn = sum(r['prediction'] == 0 for r in positives)
    correct = len(valid) - fp - fn
    fpr = fp / len(negatives) if negatives else None
    fnr = fn / len(positives) if positives else None
    return {'planned': n, 'valid': len(valid), 'abstentions': sum(r.get('status') == 'tie' for r in rows),
        'operational_or_missing': sum(r.get('status') not in ('ok', 'tie') for r in rows),
        'negative_valid': len(negatives), 'positive_valid': len(positives),
        'false_positives': fp, 'false_negatives': fn, 'fpr': fpr, 'fnr': fnr,
        'balanced_accuracy': 1 - (fpr + fnr) / 2 if fpr is not None and fnr is not None else None,
        'accuracy_bounds_all_planned': [correct / n, (correct + n - len(valid)) / n] if n else None}


def forecast(rows):
    eligible = [r for r in rows if valid_probability(r.get('score')) and r.get('status') in ('ok', 'tie')]
    if not eligible:
        return {'n_forecasts': 0, 'brier': None, 'log_loss': None, 'reliability': []}
    values = [losses(r['gold'], r['score']) for r in eligible]
    bins = []
    for index in range(10):
        part = [r for r in eligible if min(9, int(r['score'] * 10)) == index]
        bins.append({'lower': index / 10, 'upper': (index + 1) / 10, 'n': len(part),
            'mean_score': sum(r['score'] for r in part) / len(part) if part else None,
            'observed_fraction': sum(r['gold'] for r in part) / len(part) if part else None})
    return {'n_forecasts': len(eligible),
            'brier': sum(v['brier'] for v in values) / len(values),
            'log_loss': sum(v['log_loss'] for v in values) / len(values), 'reliability': bins}
