"""Sanitize checked v6 aggregates and export standalone scientific figures.

Raw case/group IDs, text, labels, review records, paths and mappings never enter the
allowlisted table schema.  Empirical figure export requires a separate verification
receipt pinning the analysis.  An unrun scaffold can show only unrun dispositions.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from scripts.study_v6.analyze import PRIMARY_CONFIGS, PRIMARY_CONTROLS

SOURCES = ('browsesafe', 'aib', 'nvidia', 'spml', 'infuse', 'scope')
CONFIGS = PRIMARY_CONFIGS + ('luna_chat', 'astra_chat', 'laya_local', 'nimble_local',
                            'protectai_local', 'constant_allow', 'constant_block', 'lexical_shortcut')
CONDITIONS = ('candidate', 'format', 'task', 'reminder', 'length', 'scrambled', 'policy',
              'task_policy', 'policy_reminder', 'policy_length', 'policy_scrambled')
VERIFY_FIELDS = ('analysis_recomputed', 'terminal_execution_verified', 'accounting_verified',
                 'label_provenance_verified', 'freeze_verified')
DISPLAY = {'browsesafe': 'BrowseSafe++', 'aib': 'AIB', 'nvidia': 'NVIDIA', 'spml': 'SPML',
           'infuse': 'INFUSE', 'scope': 'Authored scope', 'jev_firstparty': 'Jev native',
           'luna_decisions': 'Luna Decisions'}
COLORS = {'jev_firstparty': '#245B83', 'luna_decisions': '#A44B16'}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def count(value):
    if type(value) is not int or value < 0:
        raise ValueError('Aggregate count must be a nonnegative integer')
    return value


def numeric(value, lower=None, upper=None):
    if value is None:
        return None
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Aggregate metric must be finite numeric or null')
    if lower is not None and value < lower or upper is not None and value > upper:
        raise ValueError('Aggregate metric outside its declared range')
    return float(value)


def interval(value, lower=-1, upper=1):
    if value is None:
        return None
    if not isinstance(value, list) or len(value) != 2:
        raise ValueError('Expected two interval endpoints')
    if value == [None, None]:
        return None
    result = [numeric(v, lower, upper) for v in value]
    if None in result or result[0] > result[1]:
        raise ValueError('Unordered or null interval endpoint')
    return result


def percent(value):
    return None if value is None else value * 100


def percent_interval(value):
    value = interval(value)
    return None if value is None else [percent(v) for v in value]


def _identity(source, config, condition=None):
    if source not in SOURCES or config not in CONFIGS or condition is not None and condition not in CONDITIONS:
        raise ValueError('Unknown source/configuration/condition in aggregate evidence')


def _status_counts(value):
    # Parser dispositions are categorical codes, never raw exception/error text.
    allowed = {'ok', 'tie', 'timeout', 'http_error', 'runtime_error', 'parser_error',
               'parse_error', 'invalid_output', 'malformed_output', 'refused', 'refusal',
               'truncated', 'unsupported', 'not_attempted', 'empty_output', 'auth_error',
               'model_mismatch', 'transport_error', 'coverage_error', 'schema_error'}
    result = {}
    for status, n in value.items():
        label = status if status in allowed else 'other_parser_failure'
        result[label] = result.get(label, 0) + count(n)
    return result


def build_tables(analysis, *, resolution=None, verification=None):
    """Strict allowlist from full local analysis to safe machine-readable tables."""
    if analysis.get('version') != 'v6-analysis-1':
        raise ValueError('Unsupported analysis schema')
    planned, observed = count(analysis['planned_cells']), count(analysis['observed_cells'])
    if observed > planned:
        raise ValueError('Observed count exceeds the frozen denominator')
    analysis_hash = digest(analysis)
    verification = verification or {}
    ready = verification.get('analysis_sha256') == analysis_hash and all(
        verification.get(field) is True for field in VERIFY_FIELDS)
    if observed and not ready:
        raise ValueError('Empirical tables require separate complete verification pinning this analysis')
    if analysis.get('analysis_set') not in ('first_attempt_primary', 'recovery_first_valid_sensitivity'):
        raise ValueError('Unknown analysis set')
    strata = {}
    condition_rows, reliability = [], []
    for stratum in analysis['strata']:
        source, config = stratum['source'], stratum['config']
        _identity(source, config)
        if (source, config) in strata:
            raise ValueError('Duplicate aggregate source/configuration')
        strata[(source, config)] = stratum
        seen = set()
        for cell in stratum['conditions']:
            condition = cell['condition']
            _identity(source, config, condition)
            if condition in seen:
                raise ValueError('Duplicate condition aggregate')
            seen.add(condition)
            n, valid = count(cell['planned_rows']), count(cell['valid_rows'])
            statuses = _status_counts(cell['status_counts'])
            if valid > n or sum(statuses.values()) != n:
                raise ValueError('Condition disposition counts do not reconcile')
            negative = count(cell['planned_class_rows'].get('0', 0))
            positive = count(cell['planned_class_rows'].get('1', 0))
            if negative + positive != n:
                raise ValueError('Class support does not reconcile with planned rows')
            row = {'source': source, 'config': config, 'condition': condition,
                   'planned_rows': n, 'valid_rows': valid, 'planned_groups': count(cell['planned_groups']),
                   'full_input_gate_supported_rows': count(cell['full_input_gate_supported_rows']),
                   'provisional_server_gate_rows': count(cell['provisional_server_gate_rows']),
                   'negative_planned_rows': negative, 'positive_planned_rows': positive,
                   'negative_valid_rows': count(cell['valid_negative_rows']),
                   'positive_valid_rows': count(cell['valid_positive_rows']),
                   'status_counts': statuses, 'fpr': numeric(cell['fpr'], 0, 1),
                   'fnr': numeric(cell['fnr'], 0, 1), 'raw_accuracy': numeric(cell['raw_accuracy'], 0, 1),
                   'balanced_error': numeric(cell['group_class_balanced_error']['estimate'], 0, 1),
                   'balanced_error_planned_bounds': interval(cell['group_class_balanced_error_bounds_planned'], 0, 1),
                   'raw_accuracy_planned_bounds': interval(cell['raw_accuracy_bounds_planned'], 0, 1),
                   'source_label_agreement': numeric(cell['source_label_agreement']['agreement'], 0, 1)}
            if row['negative_valid_rows'] + row['positive_valid_rows'] != valid:
                raise ValueError('Valid class support does not reconcile')
            if not 0 <= row['provisional_server_gate_rows'] <= row['full_input_gate_supported_rows'] <= n:
                raise ValueError('Full-input gate counts exceed planned support')
            scores = cell['native_scores']
            row.update(native_score_rows=count(scores['score_rows']), brier=numeric(scores['brier'], 0, 1),
                       auroc=numeric(scores['auroc'], 0, 1))
            condition_rows.append(row)
            for bucket in scores['reliability']:
                reliability.append({'source': source, 'config': config, 'condition': condition,
                    'lower': numeric(bucket['lower'], 0, 1), 'upper': numeric(bucket['upper'], 0, 1),
                    'rows': count(bucket['rows']), 'mean_score': numeric(bucket['mean_score'], 0, 1),
                    'observed_positive_fraction': numeric(bucket['observed_positive_fraction'], 0, 1)})
    if sum(row['planned_rows'] for row in condition_rows) != planned:
        raise ValueError('Stratum denominators do not reconcile with all planned cells')
    family = {(r['config'], r['control']): r for r in analysis['primary_six_test_family']}
    if len(family) != 6 or set(family) != {(config, control) for config in PRIMARY_CONFIGS for control in PRIMARY_CONTROLS}:
        raise ValueError('The fixed six-test family must be complete')
    primary = []
    for config in PRIMARY_CONFIGS:
        stratum = strata.get(('browsesafe', config), {})
        for control in PRIMARY_CONTROLS:
            family_row = family[(config, control)]
            matches = [r for r in stratum.get('contrasts', []) if r['control'] == control and r['task'] == 'task']
            if len(matches) > 1:
                raise ValueError('Duplicate primary contrast')
            contrast = matches[0] if matches else None
            infer = contrast['group_class_balanced_error_difference'] if contrast else {}
            point = numeric(infer.get('estimate'), -1, 1)
            if point != numeric(family_row['estimate'], -1, 1):
                raise ValueError('Primary table and family estimates disagree')
            complete = count(contrast['complete_paired_rows']) if contrast else 0
            pair_attrition = contrast.get('source_pair_attrition', {}) if contrast else {}
            pair_sensitivity = contrast.get('complete_explicit_sourcepair_sensitivity', {}) if contrast else {}
            pair_effect = pair_sensitivity.get('group_class_balanced_error_difference', {})
            primary.append({'source': 'browsesafe', 'config': config, 'control': control, 'task': 'task',
                'estimate_pp': percent(point), 'interval_95_pp': percent_interval(infer.get('interval_95')),
                'interval_99_1667_pp': percent_interval(infer.get('interval_99_1667')),
                'planned_bounds_pp': percent_interval(contrast['planned_denominator_bounds']) if contrast else None,
                'planned_groups': count(contrast['planned_groups']) if contrast else 0,
                'complete_groups': count(contrast['complete_groups']) if contrast else 0,
                'planned_paired_rows': count(contrast['planned_paired_rows']) if contrast else 0,
                'complete_paired_rows': complete,
                'complete_negative_rows': count(contrast['complete_class_rows'].get('0', 0)) if contrast else 0,
                'complete_positive_rows': count(contrast['complete_class_rows'].get('1', 0)) if contrast else 0,
                'planned_complete_explicit_sourcepairs': count(pair_attrition.get('planned_complete_explicit_pairs', 0)),
                'valid_complete_explicit_sourcepairs': count(pair_attrition.get('valid_complete_explicit_pairs_in_both_conditions', 0)),
                'planned_orphan_explicit_sourcepair_ids': count(pair_attrition.get('explicit_pair_ids_with_planned_member_attrition', 0)),
                'complete_sourcepair_sensitivity_rows': count(pair_sensitivity.get('rows', 0)),
                'complete_sourcepair_sensitivity_estimate_pp': percent(numeric(pair_effect.get('estimate'), -1, 1)),
                'complete_sourcepair_sensitivity_interval_95_pp': percent_interval(pair_effect.get('interval_95')),
                'raw_p_two_sided': numeric(family_row['raw_p'], 0, 1),
                'p_holm': numeric(family_row['p_holm'], 0, 1),
                'reject_holm_05': family_row['reject_holm_05'] is True,
                'descriptive_only': family_row['descriptive_only'] is True,
                'status': 'unrun' if complete == 0 else 'incomplete_class_support' if point is None else
                          'descriptive' if family_row['descriptive_only'] else 'source_conditional'})
    attrition = []
    resolution_complete = False
    if resolution is not None:
        resolution_complete = resolution.get('review_resolution_complete') is True
        for source, entry in sorted(resolution['source_counts'].items()):
            if source not in SOURCES:
                raise ValueError('Unknown attrition source')
            prepared, admitted, quarantined = [count(entry[k]) for k in ('prepared', 'review_eligible', 'quarantined')]
            if admitted + quarantined != prepared:
                raise ValueError('Source attrition does not reconcile')
            splits = entry['splits']
            attrition.append({'source': source, 'prepared_rows': prepared, 'admitted_rows': admitted,
                'quarantined_rows': quarantined,
                'allowed_admitted_rows': count(entry['labels'].get('allowed', 0)),
                'violation_admitted_rows': count(entry['labels'].get('violation', 0)),
                'confirmation_rows': count(splits.get('confirmation', {}).get('rows', 0)),
                'confirmation_groups': count(splits.get('confirmation', {}).get('groups', 0)),
                'development_rows': count(splits.get('development', {}).get('rows', 0)),
                'development_groups': count(splits.get('development', {}).get('groups', 0))})
    routes = []
    for row in analysis.get('route_comparisons', []):
        for config in (row['left_config'], row['right_config']):
            _identity(row['source'], config, row['condition'])
        planned_intact = count(row['shared_planned_rows_intact_pairs'])
        supported_intact = count(row['shared_supported_rows_intact_pairs'])
        valid_intact = count(row['shared_valid_rows_intact_pairs'])
        if not 0 <= valid_intact <= supported_intact <= planned_intact:
            raise ValueError('Route comparison coverage does not reconcile')
        routes.append({'source': row['source'], 'condition': row['condition'],
            'left_config': row['left_config'], 'right_config': row['right_config'],
            'shared_planned_rows_intact_pairs': planned_intact,
            'shared_supported_rows_intact_pairs': supported_intact,
            'shared_valid_rows_intact_pairs': valid_intact,
            'shared_planned_groups': count(row['shared_planned_groups']),
            'shared_valid_groups': count(row['shared_valid_groups']),
            'orphan_explicit_pair_ids_excluded': count(row['orphan_explicit_pair_ids_excluded']),
            'error_difference_pp': percent(numeric(row['paired_error_difference']['estimate'], -1, 1)),
            'planned_bounds_pp': percent_interval(row['shared_planned_denominator_bounds']),
            'descriptive_only': True})
    intersections = []
    for row in analysis.get('coverage_intersections', []):
        for config in row['configs']:
            _identity(row['source'], config, row['condition'])
        safe = {'source': row['source'], 'condition': row['condition'], 'configs': list(row['configs'])}
        for field in ('common_planned_rows_before_pair_attrition', 'common_planned_rows_intact_pairs',
                      'common_supported_rows_intact_pairs', 'common_valid_rows_intact_pairs',
                      'common_planned_groups', 'common_supported_groups', 'common_valid_groups',
                      'orphan_explicit_pair_ids_excluded'):
            safe[field] = count(row[field])
        if not (0 <= safe['common_valid_rows_intact_pairs'] <= safe['common_supported_rows_intact_pairs']
                <= safe['common_planned_rows_intact_pairs'] <= safe['common_planned_rows_before_pair_attrition']):
            raise ValueError('All-route common coverage does not reconcile')
        intersections.append(safe)
    return {'version': 'v6-aggregate-tables-1', 'analysis_sha256': analysis_hash,
            'analysis_set': analysis['analysis_set'], 'empirical_checks_complete': ready,
            'planned_cells': planned, 'observed_cells': observed,
            'review_resolution_complete': resolution_complete,
            'primary_contrasts': primary, 'condition_support': condition_rows,
            'source_attrition': attrition, 'reliability': reliability, 'route_comparisons': routes,
            'coverage_intersections': intersections,
            'units': {'primary_effect': 'percentage points, control minus task group/class-balanced error',
                      'intervals': 'paired whole-group percentile 95% and Bonferroni 99.1667%',
                      'rates': 'fractions in tables; percentages in figures'}}


def _mpl():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10,
                         'axes.spines.top': False, 'axes.spines.right': False,
                         'axes.titleweight': 'semibold', 'savefig.facecolor': 'white',
                         'pdf.fonttype': 42, 'ps.fonttype': 42})
    return plt


def contrast_figure(tables):
    plt = _mpl()
    rows = tables['primary_contrasts']
    fig, ax = plt.subplots(figsize=(10, 5.1))
    fig.subplots_adjust(left=.25, right=.72, bottom=.18, top=.80)
    ax.axvline(0, color='#4A4A4A', linewidth=1, linestyle='--')
    extents = [0.0]
    for index, row in enumerate(rows):
        y = len(rows) - index - 1
        color = COLORS[row['config']]
        if row['estimate_pp'] is None:
            ax.text(.02, y, 'Unrun' if row['status'] == 'unrun' else 'No balanced estimate',
                    transform=ax.get_yaxis_transform(), va='center', color='#5A5A5A')
        else:
            for key, width, alpha in (('interval_99_1667_pp', 1, .6), ('interval_95_pp', 3, 1)):
                bounds = row[key]
                if bounds is not None:
                    ax.hlines(y, bounds[0], bounds[1], color=color, linewidth=width, alpha=alpha)
                    extents.extend(bounds)
            point = row['estimate_pp']
            ax.plot(point, y, marker='o' if row['config'] == 'jev_firstparty' else 'D', color=color, markersize=6)
            extents.append(point)
        denominator = (f"{row['complete_groups']}/{row['planned_groups']} groups\n"
                       f"{row['complete_paired_rows']}/{row['planned_paired_rows']} rows")
        if row['estimate_pp'] is not None:
            denominator = f"{row['estimate_pp']:+.2f} pp · " + denominator
        if row['descriptive_only'] and row['estimate_pp'] is not None:
            denominator += ' · descriptive'
        ax.text(1.03, y, denominator, transform=ax.get_yaxis_transform(), va='center', fontsize=9)
    low, high = min(extents), max(extents)
    pad = max(2, (high - low) * .10)
    ax.set_xlim(max(-100, low - pad), min(100, high + pad))
    ax.set_ylim(-.7, len(rows) - .3)
    ax.set_yticks(list(reversed(range(len(rows)))),
                  [f"{DISPLAY[row['config']]}\nvs {row['control']}" for row in rows])
    ax.set_xlabel('Control − task error (percentage points; positive favors task)')
    ax.grid(axis='x', color='#E1E4E6', linewidth=.7)
    ax.set_axisbelow(True)
    fig.suptitle('Task context versus three controls', x=.25, ha='left', fontsize=14, y=.96)
    fig.text(.25, .88, 'BrowseSafe++ · first attempts · same frozen target · six-test Holm family', fontsize=10)
    fig.text(.25, .045, 'Thick: 95% interval. Thin: Bonferroni 99.1667% interval. Counts: complete/planned.\n'
             'Effects are conditional on valid pairs; full-target bounds remain in the checked tables.', fontsize=9)
    return fig


def attrition_figure(tables):
    plt = _mpl()
    rows = tables['source_attrition']
    fig, axes = plt.subplots(1, 2, figsize=(10, 4.5), gridspec_kw={'width_ratios': [1.2, 1]})
    fig.subplots_adjust(left=.16, right=.96, bottom=.17, top=.79, wspace=.44)
    if not rows:
        for ax in axes:
            ax.text(.5, .5, 'Final admission not supplied', transform=ax.transAxes, ha='center')
            ax.set_axis_off()
    else:
        y = list(reversed(range(len(rows))))
        axes[0].barh(y, [r['admitted_rows'] for r in rows], color='#245B83', label='Admitted')
        axes[0].barh(y, [r['quarantined_rows'] for r in rows], left=[r['admitted_rows'] for r in rows],
                     color='#DEE4E8', edgecolor='#9AA3AA', linewidth=.5, label='Quarantined')
        axes[0].set_yticks(y, [DISPLAY[r['source']] for r in rows])
        axes[0].set_xlabel('Prepared rows')
        axes[0].legend(loc='upper left', bbox_to_anchor=(0, 1.16), frameon=False, ncols=2, fontsize=9)
        axes[1].barh(y, [r['confirmation_groups'] for r in rows], color='#245B83')
        axes[1].set_yticks(y, [str(r['confirmation_groups']) for r in rows])
        axes[1].set_xlabel('Admitted confirmation groups')
        for ax in axes:
            ax.set_xlim(left=0)
            ax.grid(axis='x', color='#E1E4E6', linewidth=.7)
            ax.set_axisbelow(True)
    fig.suptitle('Source attrition and independent group support', x=.16, ha='left', fontsize=14, y=.96)
    fig.text(.16, .87, 'Final agent-reviewed admission' if tables['review_resolution_complete'] else
             'Admission pending · counts are provisional and cannot authorize inference', fontsize=10)
    fig.text(.16, .035, 'Rows and final components are different units. Small secondary arms remain descriptive.', fontsize=9)
    return fig


def coverage_figure(tables):
    plt = _mpl()
    # One common reference condition per source/route, never sum repeated pages
    # across intervention conditions into an inflated sample count.
    selected = {}
    preference = {'task': 0, 'task_policy': 1, 'policy': 2, 'candidate': 3, 'format': 4}
    for row in tables['condition_support']:
        identity = (row['source'], row['config'])
        rank = preference.get(row['condition'], 5)
        if identity not in selected or rank < selected[identity][0]:
            selected[identity] = (rank, row)
    rows = [value[1] for _, value in sorted(selected.items())]
    height = max(3.8, .39 * len(rows) + 1.8)
    fig, ax = plt.subplots(figsize=(10, height))
    fig.subplots_adjust(left=.36, right=.83, bottom=1.20 / height, top=1 - .85 / height)
    if not rows:
        ax.text(.5, .5, 'No execution cells supplied', transform=ax.transAxes, ha='center')
        ax.set_axis_off()
    else:
        y = list(reversed(range(len(rows))))
        gate_fractions = [r['full_input_gate_supported_rows'] / r['planned_rows'] if r['planned_rows'] else 0 for r in rows]
        valid_fractions = [r['valid_rows'] / r['planned_rows'] if r['planned_rows'] else 0 for r in rows]
        ax.barh(y, [f * 100 for f in gate_fractions], color='#DEE4E8', edgecolor='#9AA3AA', linewidth=.5,
                label='Dispatch coverage gate')
        ax.barh(y, [f * 100 for f in valid_fractions], color='#245B83', height=.45,
                label='Valid first attempt')
        ax.set_xlim(0, 100)
        ax.set_yticks(y, [f"{DISPLAY[r['source']]} · {DISPLAY.get(r['config'], r['config'])}\n{r['condition']}" for r in rows])
        for pos, row in zip(y, rows):
            ax.text(1.03, pos, f"{row['valid_rows']}/{row['planned_rows']}",
                    transform=ax.get_yaxis_transform(), va='center', fontsize=9)
        ax.set_xlabel('Rows (% of the planned condition)')
        handles, labels = ax.get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower left', bbox_to_anchor=(.36, .35 / height),
                   frameon=False, fontsize=9, ncols=2)
        ax.grid(axis='x', color='#E1E4E6', linewidth=.7)
        ax.set_axisbelow(True)
    fig.suptitle('Coverage gates and valid outputs', x=.36, ha='left', fontsize=14, y=1 - .12 / height)
    fig.text(.36, 1 - .55 / height, 'Reference condition per source/route · counts show valid/planned rows', fontsize=9)
    fig.text(.36, .10 / height, 'Server gates are provisional full-input checks; they are not tokenizer certificates.', fontsize=9)
    return fig


def reliability_figure(tables):
    plt = _mpl()
    panels = [(config, [row for row in tables['reliability'] if row['source'] == 'browsesafe'
                       and row['config'] == config and row['condition'] == 'task' and row['rows'] > 0])
              for config in PRIMARY_CONFIGS]
    if not any(rows for _, rows in panels):
        return None
    fig, axes = plt.subplots(1, 2, figsize=(8, 4), sharex=True, sharey=True)
    fig.subplots_adjust(left=.10, right=.97, bottom=.22, top=.77, wspace=.18)
    for ax, (config, rows) in zip(axes, panels):
        ax.plot([0, 100], [0, 100], color='#555555', linestyle='--', linewidth=1)
        if rows:
            ax.scatter([r['mean_score'] * 100 for r in rows],
                       [r['observed_positive_fraction'] * 100 for r in rows],
                       color=COLORS[config], marker='o' if config == 'jev_firstparty' else 'D')
            for row in rows:
                ax.annotate(str(row['rows']), (row['mean_score'] * 100, row['observed_positive_fraction'] * 100),
                            xytext=(4, 4), textcoords='offset points', fontsize=8)
        else:
            ax.text(.5, .5, 'No valid native scores', transform=ax.transAxes, ha='center')
        ax.set_title(DISPLAY[config], fontsize=11)
        ax.set_xlim(-3, 103)
        ax.set_ylim(-3, 103)
        ax.set_xlabel('Mean native score (%)')
    axes[0].set_ylabel('Observed positive fraction (%)')
    fig.suptitle('Native-score reliability diagnostics', x=.10, ha='left', fontsize=14, y=.97)
    fig.text(.10, .85, 'BrowseSafe++ task condition · fixed deciles · numbers show rows in bin', fontsize=9)
    fig.text(.10, .04, 'Selected balanced material; native scores are not assumed calibrated. No calibration fitted.', fontsize=9)
    return fig


def _safe_write(path, data):
    if path.exists() and path.read_bytes() != data:
        raise ValueError('Refuse to overwrite changed figure/table artifact: ' + path.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


def export(tables, directory):
    """Export from sanitized checked tables only; never synthesize result points."""
    if tables.get('version') != 'v6-aggregate-tables-1':
        raise ValueError('Unsupported aggregate table schema')
    if tables.get('observed_cells') and not tables.get('empirical_checks_complete'):
        raise ValueError('Empirical figures require verified aggregate tables')
    directory = Path(directory)
    _safe_write(directory / 'tables.json', (json.dumps(tables, indent=2, sort_keys=True, allow_nan=False) + '\n').encode())
    csv_rows = tables['primary_contrasts']
    stream = io.StringIO(newline='')
    fields = ['config', 'control', 'status', 'estimate_pp', 'interval_95_pp', 'interval_99_1667_pp',
              'planned_bounds_pp', 'complete_groups', 'planned_groups', 'complete_paired_rows',
              'planned_paired_rows', 'p_holm', 'descriptive_only']
    writer = csv.DictWriter(stream, fields, extrasaction='ignore', lineterminator='\n')
    writer.writeheader()
    writer.writerows(csv_rows)
    _safe_write(directory / 'primary-contrasts.csv', stream.getvalue().encode())
    plt = _mpl()
    paths = []
    for name, factory in (('primary-contrasts', contrast_figure), ('source-attrition', attrition_figure),
                          ('coverage', coverage_figure), ('native-reliability', reliability_figure)):
        fig = factory(tables)
        if fig is None:
            continue
        for extension in ('pdf', 'png'):
            data = io.BytesIO()
            metadata = {'CreationDate': None, 'ModDate': None} if extension == 'pdf' else {}
            fig.savefig(data, format=extension, dpi=180, metadata=metadata)
            path = directory / f'{name}.{extension}'
            _safe_write(path, data.getvalue())
            paths.append(path)
        plt.close(fig)
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--analysis', required=True, type=Path)
    parser.add_argument('--resolution', type=Path)
    parser.add_argument('--verification', type=Path)
    parser.add_argument('--output-dir', required=True, type=Path)
    args = parser.parse_args()
    analysis = json.loads(args.analysis.read_text())
    tables = build_tables(analysis,
        resolution=json.loads(args.resolution.read_text()) if args.resolution else None,
        verification=json.loads(args.verification.read_text()) if args.verification else None)
    paths = export(tables, args.output_dir)
    print(json.dumps({'tables_sha256': digest(tables), 'figure_exports': len(paths),
                      'output_dir': str(args.output_dir), 'empirical_checks_complete': tables['empirical_checks_complete']}))


if __name__ == '__main__':
    main()
