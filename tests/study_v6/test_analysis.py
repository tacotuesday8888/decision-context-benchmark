"""Hand-computable scientific fixtures; no corpora, models or network access."""
import json
import unittest

from scripts.study_v6 import analyze
from scripts.study_v6 import metrics as stats


def cell(identity, group, gold, condition, prediction, *, config='jev_firstparty', source='browsesafe', **extra):
    return {'id': identity, 'source': source, 'config': config, 'group': group,
            'gold': gold, 'upstream_label': gold, 'condition': condition,
            'status': 'ok' if prediction is not None else 'timeout',
            'valid': prediction is not None, 'prediction': prediction, 'score': None,
            'split': 'confirmation', 'inference_eligible': True, **extra}


class GroupEstimators(unittest.TestCase):
    def test_equal_class_and_equal_group_weight_not_row_weight(self):
        # Group A has three negatives; replicating them changes raw error, not
        # its within-class group mean.  Positive effects are -1 in A and +1 B.
        values = [1, 1, 1, -1, 0, 1]
        groups = ['A', 'A', 'A', 'A', 'B', 'B']
        labels = [0, 0, 0, 1, 0, 1]
        result = stats.group_balanced(values, groups, labels)
        self.assertEqual(result['estimate'], .25)
        self.assertEqual(sum(values) / len(values), .5)
        self.assertEqual(result['class_estimates'], {'0': .5, '1': 0.0})

    def test_largest_component_does_not_become_thousands_of_independent_units(self):
        values = [1] * 10_000 + [-1, 0, 0]
        groups = ['large'] * 10_001 + ['small', 'small']
        labels = [0] * 10_000 + [1, 0, 1]
        result = stats.paired_inference(values, groups, labels, bootstrap_draws=100, randomization_draws=100)
        self.assertEqual(result['groups'], 2)
        self.assertEqual(result['estimate'], 0)
        self.assertEqual(result['randomization_p_two_sided'], 1)
        self.assertEqual(result['interval_95'], [0, 0])
        self.assertEqual(result['bootstrap_degenerate_draws'], 0)

    def test_classes_have_separate_group_denominators(self):
        result = stats.group_balanced([1, 1, -1], ['A', 'B', 'C'], [0, 0, 1])
        self.assertEqual(result['estimate'], 0)
        self.assertEqual(result['class_groups'], {'0': 2, '1': 1})
        self.assertNotEqual(result['estimate'], (1 + 1 - 1) / 3)

    def test_one_missing_class_is_not_balanced_accuracy(self):
        self.assertIsNone(stats.group_balanced([1, 0], ['A', 'B'], [0, 0])['estimate'])

    def test_exact_sign_test_flips_whole_group_with_shared_classes(self):
        groups = [f'g{index}' for index in range(4) for _ in (0, 1)]
        result = stats.paired_inference([1] * 8, groups, [0, 1] * 4,
            bootstrap_draws=128, randomization_draws=100)
        # Four independent groups => 2/16, not the 2/256 from eight rows.
        self.assertEqual(result['randomization_p_two_sided'], .125)
        self.assertEqual(result['randomization_draws'], 16)
        self.assertEqual(result['interval_95'], [1, 1])
        self.assertEqual(result['interval_99_1667'], [1, 1])
        self.assertTrue(result['descriptive_only'])

    def test_bootstrap_recomputes_class_denominators_and_counts_degeneracy(self):
        result = stats.paired_inference([1, -1], ['negative_only', 'positive_only'], [0, 1],
            bootstrap_draws=400, randomization_draws=100)
        self.assertEqual(result['estimate'], 0)
        self.assertEqual(result['interval_95'], [0, 0])
        self.assertGreater(result['bootstrap_degenerate_draws'], 0)
        self.assertEqual(result['bootstrap_valid_draws'] + result['bootstrap_degenerate_draws'], 400)

    def test_seeded_monte_carlo_plus_one(self):
        args = ([1] * 6, ['A', 'A', 'B', 'B', 'C', 'C'], [0, 1] * 3)
        options = dict(bootstrap_draws=50, randomization_draws=99, exact_max_groups=0)
        first = stats.paired_inference(*args, **options)
        second = stats.paired_inference(*args, **options)
        self.assertEqual(first, second)
        self.assertEqual(first['randomization_draws'], 99)
        # A +1-corrected probability has denominator draws+1, and cannot be 0.
        p = first['randomization_p_two_sided']
        self.assertGreaterEqual(p, .01)
        self.assertAlmostEqual(p * 100, round(p * 100))

    def test_holm_keeps_six_tests_and_monotonic_adjustment(self):
        result = stats.holm([.001, .011, .012, .04, .9, None])
        for actual, expected in zip([r['p_holm'] for r in result], [.006, .055, .055, .12, 1, None]):
            if expected is None:
                self.assertIsNone(actual)
            else:
                self.assertAlmostEqual(actual, expected)
        self.assertEqual([r['reject_holm_05'] for r in result], [True, False, False, False, False, False])


class PairedAndCoverage(unittest.TestCase):
    def test_missing_one_condition_uses_known_error_in_planned_bounds(self):
        rows = [cell('negative', 'A', 0, 'format', 1),
                cell('negative', 'A', 0, 'task', None),
                cell('positive', 'A', 1, 'format', 0),
                cell('positive', 'A', 1, 'task', 1)]
        result = analyze.paired(rows, 'format', 'task', bootstrap_draws=20, randomization_draws=20)
        # Negative effect [0,1], positive +1 -> balanced [0.5,1].
        self.assertEqual(result['planned_denominator_bounds'], [.5, 1])
        self.assertEqual(result['complete_paired_rows'], 1)
        self.assertIsNone(result['group_class_balanced_error_difference']['estimate'])

    def test_single_class_source_keeps_fpr_and_support_but_no_balanced_effect(self):
        planned = []
        for index in range(20):
            for condition in ('format', 'task', 'reminder', 'length'):
                planned.append(cell(str(index), f'g{index}', 0, condition, 0))
        result = analyze.analyze(planned, planned, bootstrap_draws=20, randomization_draws=20)
        conditions = result['strata'][0]['conditions']
        self.assertTrue(all(row['fpr'] == 0 and row['fnr'] is None for row in conditions))
        for contrast in result['strata'][0]['contrasts']:
            self.assertIsNone(contrast['group_class_balanced_error_difference']['estimate'])
            self.assertEqual(contrast['planned_denominator_bounds'], [None, None])
        self.assertEqual(len(result['primary_six_test_family']), 6)
        self.assertTrue(all(row['p_holm'] is None and not row['reject_holm_05'] for row in result['primary_six_test_family']))

    def test_transitions_and_direction(self):
        rows = [cell('negative', 'A', 0, 'format', 1), cell('negative', 'A', 0, 'task', 0),
                cell('positive', 'A', 1, 'format', 1), cell('positive', 'A', 1, 'task', 0)]
        result = analyze.paired(rows, 'format', 'task', bootstrap_draws=20, randomization_draws=20)
        self.assertEqual(result['group_class_balanced_error_difference']['estimate'], 0)
        self.assertEqual(result['paired_error_transitions']['1->0'], 1)
        self.assertEqual(result['paired_error_transitions']['0->1'], 1)

    def test_source_pair_runtime_attrition_keeps_primary_and_separate_sensitivity(self):
        rows = []
        for identity, label, group, pair, control, task in (
            ('a0', 0, 'A', 'PA', 1, None), ('a1', 1, 'A', 'PA', 0, 1),
            ('b0', 0, 'B', 'PB', 0, 0), ('b1', 1, 'B', 'PB', 1, 1)):
            rows.extend([cell(identity, group, label, 'format', control, pair_id=pair),
                         cell(identity, group, label, 'task', task, pair_id=pair)])
        result = analyze.paired(rows, 'format', 'task', bootstrap_draws=20, randomization_draws=20)
        self.assertEqual(result['complete_paired_rows'], 3)
        self.assertEqual(result['group_class_balanced_error_difference']['estimate'], .25)
        self.assertEqual(result['source_pair_attrition']['planned_complete_explicit_pairs'], 2)
        self.assertEqual(result['source_pair_attrition']['valid_complete_explicit_pairs_in_both_conditions'], 1)
        sensitivity = result['complete_explicit_sourcepair_sensitivity']
        self.assertEqual(sensitivity['rows'], 2)
        self.assertEqual(sensitivity['group_class_balanced_error_difference']['estimate'], 0)
        self.assertFalse(sensitivity['same_rows_as_primary'])

    def test_route_comparisons_use_same_supported_intact_pairs(self):
        rows = []
        for config in ('jev_firstparty', 'luna_decisions'):
            for identity, label, group, pair in (
                ('a0', 0, 'A', 'PA'), ('a1', 1, 'A', 'PA'),
                ('b0', 0, 'B', 'PB'), ('b1', 1, 'B', 'PB')):
                row = cell(identity, group, label, 'task', label, config=config, pair_id=pair, coverage_supported=True)
                if config == 'luna_decisions' and identity == 'a0':
                    row.update(coverage_supported=False, valid=False, prediction=None, status='unsupported')
                rows.append(row)
        result = analyze.route_comparisons(rows, bootstrap_draws=20, randomization_draws=20)[0]
        self.assertEqual(result['shared_planned_rows_intact_pairs'], 4)
        self.assertEqual(result['shared_supported_rows_intact_pairs'], 2)
        self.assertEqual(result['shared_valid_rows_intact_pairs'], 2)
        self.assertEqual(result['paired_error_difference']['estimate'], 0)
        self.assertEqual(result['shared_valid_class_rows'], {'0': 1, '1': 1})
        common = analyze.coverage_intersections(rows)[0]
        self.assertEqual(common['configs'], ['jev_firstparty', 'luna_decisions'])
        self.assertEqual(common['common_planned_rows_intact_pairs'], 4)
        self.assertEqual(common['common_supported_rows_intact_pairs'], 2)
        self.assertEqual(common['common_valid_rows_intact_pairs'], 2)

    def test_classification_separates_failure_tie_and_planned_support(self):
        rows = [cell('a', 'A', 0, 'task', 1), cell('b', 'B', 0, 'task', None),
                cell('c', 'C', 1, 'task', None, status='tie', score=.5),
                cell('d', 'D', 1, 'task', 1)]
        result = stats.classification(rows)
        self.assertEqual(result['status_counts'], {'ok': 2, 'timeout': 1, 'tie': 1})
        self.assertEqual(result['fpr'], 1)
        self.assertEqual(result['fnr'], 0)
        self.assertEqual(result['raw_accuracy_bounds_planned'], [.25, .75])
        self.assertEqual(result['group_class_balanced_error_bounds_planned'], [.25, .75])

    def test_join_preserves_full_target_and_unsupported_denominator(self):
        planned = [cell('a', 'A', 0, 'task', None),
                   cell('b', 'B', 1, 'task', None, coverage_status='too_long', inference_eligible=False)]
        record = {k: v for k, v in cell('a', 'A', 0, 'task', 0).items()
                  if k in ('id', 'config', 'condition', 'valid', 'prediction', 'score', 'status')}
        joined = analyze.collect(planned, [record])
        self.assertEqual([r['status'] for r in joined], ['ok', 'unsupported'])
        result = stats.classification(joined)
        self.assertEqual(result['planned_rows'], 2)
        self.assertEqual(result['raw_accuracy_bounds_planned'], [.5, 1])

    def test_join_rejects_duplicates_unplanned_development_and_recovery(self):
        planned = [cell('a', 'A', 0, 'task', 0)]
        with self.assertRaisesRegex(ValueError, 'Duplicate planned'):
            analyze.collect(planned * 2, [])
        with self.assertRaisesRegex(ValueError, 'Duplicate record'):
            analyze.collect(planned, planned * 2)
        with self.assertRaisesRegex(ValueError, 'Unplanned record'):
            analyze.collect(planned, [cell('other', 'B', 1, 'task', 1)])
        with self.assertRaisesRegex(ValueError, 'Development'):
            analyze.collect([dict(planned[0], split='development')], [])
        with self.assertRaisesRegex(ValueError, 'Recovery'):
            analyze.collect(planned, [dict(planned[0], attempt=1)])
        with self.assertRaisesRegex(ValueError, 'ineligible'):
            analyze.collect([dict(planned[0], inference_eligible=False)], planned)
        with self.assertRaisesRegex(ValueError, 'nonterminal'):
            analyze.collect(planned, [dict(planned[0], valid=False, status='in_flight')])
        with self.assertRaisesRegex(ValueError, 'changed across'):
            analyze.collect(planned + [dict(planned[0], condition='format', group='changed')], [])
        with self.assertRaisesRegex(ValueError, 'identical planned row coverage'):
            analyze.paired(planned, 'format', 'task', bootstrap_draws=20, randomization_draws=20)

    def test_exact_ties_abstain_and_chat_has_no_scores(self):
        planned = [cell('a', 'A', 0, 'task', 0)]
        with self.assertRaisesRegex(ValueError, 'Valid flag'):
            analyze.collect(planned, [dict(planned[0], status='tie', score=.5)])
        chat = [dict(planned[0], config='luna_chat')]
        with self.assertRaisesRegex(ValueError, 'invent confidence'):
            analyze.collect(chat, [dict(chat[0], score=.2)])
        with self.assertRaisesRegex(ValueError, '0.5 threshold'):
            analyze.collect(planned, [dict(planned[0], score=.8)])

    def test_source_pairs_are_not_condition_pairs_and_scope_changes_label(self):
        rows = [cell('allowed', 'A', 0, 'task_policy', 0, source='scope', pair_id='P'),
                cell('conflict', 'A', 1, 'task_policy', 1, source='scope', pair_id='P'),
                cell('attrited', 'A', 0, 'task_policy', 0, source='scope', pair_id='Q')]
        result = analyze.explicit_pairs(rows)
        self.assertEqual(result['planned_complete_source_pairs'], 1)
        self.assertEqual(result['source_pair_ids_with_attrition_or_nonbinary_pair'], 1)
        self.assertEqual(result['both_correct_fraction_valid_pairs'], 1)
        self.assertEqual(result['gold_0_to_gold_1_prediction_transitions'], {'0->1': 1})

    def test_subgroups_require_ten_groups_in_each_class(self):
        rows = []
        for index in range(9):
            for label in (0, 1):
                for condition in ('format', 'task'):
                    rows.append(cell(f'{index}-{label}', f'g{index}', label, condition, label,
                        review_subgroups={'task_relation': 'related'}))
        result = analyze.subgroup_effects(rows, 'format', 'task', bootstrap_draws=20, randomization_draws=20)
        self.assertEqual(result[0]['status'], 'insufficient_groups_per_class')
        self.assertIsNone(result[0]['contrast'])


class ScoreDiagnostics(unittest.TestCase):
    def test_auroc_average_ties_brier_and_fixed_reliability_bins(self):
        rows = [cell('n0', 'A', 0, 'task', 0, score=0),
                cell('n1', 'B', 0, 'task', 1, score=.5),
                cell('p0', 'C', 1, 'task', None, score=.5, status='tie'),
                cell('p1', 'D', 1, 'task', 1, score=1)]
        result = stats.forecast(rows)
        self.assertEqual(result['auroc'], .875)
        self.assertEqual(result['brier'], .125)
        self.assertEqual(result['score_rows'], 4)
        self.assertEqual(len(result['reliability']), 10)
        self.assertEqual(result['reliability'][5]['rows'], 2)
        self.assertEqual(result['reliability'][9]['mean_score'], 1)

    def test_small_arm_keeps_fixed_family_without_confirmatory_rejection(self):
        planned = []
        for label in (0, 1):
            for condition in ('format', 'task'):
                planned.append(cell(str(label), 'A', label, condition, label))
        result = analyze.analyze(planned, planned, bootstrap_draws=20, randomization_draws=20)
        family = result['primary_six_test_family']
        self.assertEqual(len(family), 6)
        self.assertTrue(all(not r['reject_holm_05'] for r in family))
        self.assertIsNone(family[0]['p'])
        self.assertEqual(result['planned_cells'], 4)
        json.dumps(result, allow_nan=False)


if __name__ == '__main__':
    unittest.main()
