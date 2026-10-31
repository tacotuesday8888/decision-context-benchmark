"""Predeclared v6 source-conditional estimators; no inference or fitted thresholds.

The unit resampled or sign-flipped is the final review component, including every
retained member.  Class means give equal weight to components containing that
class; the two class estimates then receive equal weight.  These are conditional
estimates for the selected source material, not prevalence or deployment claims.
"""
from __future__ import annotations

import math
from collections import Counter, defaultdict

import numpy as np

SEED = 20261031
PRIMARY_TESTS = 6
BOOTSTRAP_DRAWS = 20_000
RANDOMIZATION_DRAWS = 100_000


def binary(value):
    return type(value) in (int, bool) and value in (0, 1)


def probability(value):
    return type(value) in (int, float) and math.isfinite(value) and 0 <= value <= 1


def valid(row):
    return row.get('valid') is True and row.get('status') == 'ok' and binary(row.get('prediction'))


def group_class_means(values, groups, labels):
    """One mean per (final component, gold class), leaving absent classes NaN."""
    if not (len(values) == len(groups) == len(labels)):
        raise ValueError('Values, groups and labels must align')
    cells = defaultdict(list)
    for value, group, label in zip(values, groups, labels):
        if not binary(label) or not isinstance(group, str) or not group:
            raise ValueError('Binary gold and nonempty final component required')
        if not math.isfinite(value):
            raise ValueError('Nonfinite group value')
        cells[(group, int(label))].append(float(value))
    names = sorted(set(groups))
    result = np.full((len(names), 2), np.nan)
    for index, group in enumerate(names):
        for label in (0, 1):
            part = cells.get((group, label))
            if part:
                result[index, label] = math.fsum(part) / len(part)
    return names, result


def _class_estimates(array):
    counts = np.sum(np.isfinite(array), axis=0)
    sums = np.nansum(array, axis=0)
    means = np.divide(sums, counts, out=np.full(2, np.nan), where=counts > 0)
    return means, counts


def group_balanced(values, groups, labels):
    names, array = group_class_means(values, groups, labels)
    means, counts = _class_estimates(array)
    return {'estimate': float(np.mean(means)) if np.all(counts > 0) else None,
            'groups': len(names), 'class_groups': {str(c): int(counts[c]) for c in (0, 1)},
            'class_estimates': {str(c): float(means[c]) if counts[c] else None for c in (0, 1)},
            'rows': len(values)}


def paired_inference(values, groups, labels, *, bootstrap_draws=BOOTSTRAP_DRAWS,
                     randomization_draws=RANDOMIZATION_DRAWS, seed=SEED, exact_max_groups=20):
    """Two-sided component sign test and paired component percentile intervals.

    A sign is shared by both classes within a component.  Bootstrap draws sample
    components with replacement and recompute both class denominators.  Draws
    missing either class are counted and omitted explicitly.  Randomization relies
    on exchangeability of condition labels under the null; bootstrap intervals rely
    on treating selected final components as exchangeable within this source.
    """
    result = group_balanced(values, groups, labels)
    names, array = group_class_means(values, groups, labels)
    means, counts = _class_estimates(array)
    result.update(seed=seed, bootstrap_draws=bootstrap_draws,
                  bootstrap_degenerate_draws=0, bootstrap_valid_draws=0,
                  interval_95=None, interval_99_1667=None,
                  interval_method='paired whole-component percentile bootstrap',
                  randomization_p_two_sided=None, randomization_draws=0,
                  randomization_method=None, descriptive_only=len(names) < 20,
                  assumptions=['Condition exchangeability under the sign-randomization null.',
                               'Source-conditional exchangeability of final components for bootstrap.'])
    result['individual_group_class_effects'] = [
        {'group': name, 'class_0': None if np.isnan(row[0]) else float(row[0]),
         'class_1': None if np.isnan(row[1]) else float(row[1])}
        for name, row in zip(names, array)]
    if result['estimate'] is None:
        result['inference_status'] = 'missing_gold_class'
        return result
    if bootstrap_draws <= 0 or randomization_draws <= 0:
        raise ValueError('Positive draw counts required')
    n = len(names)
    # Each component contribution retains the class-specific group denominator.
    contributions = np.nansum(array / counts, axis=1) / 2
    nonzero = contributions[np.abs(contributions) > 0]
    result['randomization_nonzero_component_contributions'] = len(nonzero)
    observed = abs(float(np.sum(contributions)))
    tolerance = 1e-12
    if len(nonzero) <= exact_max_groups:
        total = 1 << len(nonzero)
        extreme = 0
        for start in range(0, total, 4096):
            ids = np.arange(start, min(total, start + 4096), dtype=np.uint64)
            bits = (ids[:, None] >> np.arange(len(nonzero), dtype=np.uint64)) & 1
            statistics = (bits.astype(float) * 2 - 1) @ nonzero
            extreme += int(np.count_nonzero(np.abs(statistics) >= observed - tolerance))
        p = extreme / total
        result.update(randomization_method='exact whole-component sign enumeration',
                      randomization_draws=total, randomization_p_two_sided=p)
    else:
        rng = np.random.default_rng(seed)
        extreme = 0
        for start in range(0, randomization_draws, 512):
            count = min(512, randomization_draws - start)
            signs = rng.integers(0, 2, size=(count, len(nonzero)), dtype=np.int8) * 2 - 1
            extreme += int(np.count_nonzero(np.abs(signs @ nonzero) >= observed - tolerance))
        result.update(randomization_method='Monte Carlo whole-component signs, +1 correction',
                      randomization_draws=randomization_draws,
                      randomization_p_two_sided=(extreme + 1) / (randomization_draws + 1))
    rng = np.random.default_rng(seed + 1)
    bootstrapped = []
    for start in range(0, bootstrap_draws, 256):
        count = min(256, bootstrap_draws - start)
        chosen = array[rng.integers(0, n, size=(count, n))]
        denominators = np.sum(np.isfinite(chosen), axis=1)
        good = np.all(denominators > 0, axis=1)
        result['bootstrap_degenerate_draws'] += int(np.count_nonzero(~good))
        estimates = np.nansum(chosen[good], axis=1) / denominators[good]
        bootstrapped.extend(np.mean(estimates, axis=1).tolist())
    result['bootstrap_valid_draws'] = len(bootstrapped)
    if bootstrapped:
        result['interval_95'] = np.quantile(bootstrapped, [.025, .975]).tolist()
        tail = .05 / (2 * PRIMARY_TESTS)
        result['interval_99_1667'] = np.quantile(bootstrapped, [tail, 1 - tail]).tolist()
    result['inference_status'] = 'descriptive_fewer_than_20_groups' if n < 20 else 'source_conditional'
    return result


def holm(p_values, alpha=.05):
    """Fixed family Holm adjustment; absent tests retain their family positions.

    None is conservatively treated as 1 for multiplicity but remains unavailable
    in the output.  This prevents a partially run family shrinking after outcomes.
    """
    if not 0 < alpha < 1:
        raise ValueError('Invalid alpha')
    for value in p_values:
        if value is not None and not probability(value):
            raise ValueError('Invalid p value')
    m = len(p_values)
    order = sorted(range(m), key=lambda i: (1 if p_values[i] is None else p_values[i], i))
    adjusted = [None] * m
    running = 0.0
    for rank, index in enumerate(order):
        value = 1 if p_values[index] is None else p_values[index]
        running = max(running, min(1.0, value * (m - rank)))
        if p_values[index] is not None:
            adjusted[index] = running
    return [{'p': p, 'p_holm': a, 'reject_holm_05': a is not None and a <= alpha}
            for p, a in zip(p_values, adjusted)]


def classification(rows):
    accepted = [r for r in rows if valid(r)]
    negatives = [r for r in accepted if r['gold'] == 0]
    positives = [r for r in accepted if r['gold'] == 1]
    fp = sum(r['prediction'] == 1 for r in negatives)
    fn = sum(r['prediction'] == 0 for r in positives)
    correct = len(accepted) - fp - fn
    source_agree = [r for r in accepted if binary(r.get('upstream_label'))]
    balanced = group_balanced([float(r['prediction'] != r['gold']) for r in accepted],
                             [r['group'] for r in accepted], [r['gold'] for r in accepted])
    lower = [float(r['prediction'] != r['gold']) if valid(r) else 0 for r in rows]
    upper = [float(r['prediction'] != r['gold']) if valid(r) else 1 for r in rows]
    groups, labels = [r['group'] for r in rows], [r['gold'] for r in rows]
    return {'planned_rows': len(rows), 'planned_groups': len(set(groups)),
            'planned_class_rows': dict(Counter(str(r['gold']) for r in rows)),
            'full_input_gate_supported_rows': sum(r.get('coverage_supported') is True for r in rows),
            'provisional_server_gate_rows': sum(r.get('coverage_supported') is True and r.get('coverage_status') == 'full_input_server_gate' for r in rows),
            'valid_rows': len(accepted), 'status_counts': dict(Counter(r['status'] for r in rows)),
            'valid_negative_rows': len(negatives), 'valid_positive_rows': len(positives),
            'false_positives': fp, 'false_negatives': fn,
            'fpr': fp / len(negatives) if negatives else None,
            'fnr': fn / len(positives) if positives else None,
            'raw_accuracy': correct / len(accepted) if accepted else None,
            'raw_accuracy_bounds_planned': [correct / len(rows), (correct + len(rows) - len(accepted)) / len(rows)] if rows else None,
            'group_class_balanced_error': balanced,
            'group_class_balanced_error_bounds_planned': [group_balanced(v, groups, labels)['estimate'] for v in (lower, upper)],
            'source_label_agreement': {'valid_rows': len(source_agree),
                'agreement': sum(r['prediction'] == r['upstream_label'] for r in source_agree) / len(source_agree) if source_agree else None,
                'meaning': 'Agreement with upstream construction labels; not human gold or an independent validity endpoint.'}}


def forecast(rows):
    selected = [r for r in rows if r.get('status') in ('ok', 'tie') and probability(r.get('score'))]
    if not selected:
        return {'score_rows': 0, 'brier': None, 'auroc': None, 'reliability': []}
    brier = math.fsum((r['score'] - r['gold']) ** 2 for r in selected) / len(selected)
    ordered = sorted(selected, key=lambda r: r['score'])
    positives = sum(r['gold'] == 1 for r in ordered)
    negatives = len(ordered) - positives
    favorable = 0.0
    negative_before = 0
    index = 0
    while index < len(ordered):
        end = index + 1
        while end < len(ordered) and ordered[end]['score'] == ordered[index]['score']:
            end += 1
        tied = ordered[index:end]
        tied_positive = sum(r['gold'] == 1 for r in tied)
        tied_negative = len(tied) - tied_positive
        favorable += tied_positive * (negative_before + tied_negative / 2)
        negative_before += tied_negative
        index = end
    bins = []
    for index in range(10):
        part = [r for r in selected if min(9, int(r['score'] * 10)) == index]
        bins.append({'lower': index / 10, 'upper': (index + 1) / 10, 'rows': len(part),
                     'mean_score': math.fsum(r['score'] for r in part) / len(part) if part else None,
                     'observed_positive_fraction': sum(r['gold'] for r in part) / len(part) if part else None})
    return {'score_rows': len(selected), 'brier': brier,
            'auroc': favorable / (positives * negatives) if positives and negatives else None,
            'positive_score_rows': positives, 'negative_score_rows': negatives,
            'reliability': bins, 'interpretation': 'Native score diagnostics only; no calibration fitted or assumed.'}
