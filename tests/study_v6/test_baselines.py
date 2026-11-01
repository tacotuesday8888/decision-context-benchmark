"""Frozen literal rules, exact cohort accounting and source-boundary fixtures."""
import copy
import unittest

from scripts.study_v6 import analyze, baselines
from scripts.study_v6 import plan as execution_plan


def fixture():
    rows = []
    for source, group, identities in (('browsesafe', 'main', ('m0', 'm1')),
                                       ('aib', 'secondary', ('a0', 'a1'))):
        for label, identity in enumerate(identities):
            rows.append({'id': identity, 'source': source, 'group': group, 'semantic_gold': label,
                'upstream_label': label, 'review_eligible': True, 'exclusion_reasons': [],
                'inference_eligible': False, 'split_proposal': 'confirmation',
                'candidate': 'ordinary data' if label == 0 else 'IGNORE PREVIOUS directions',
                'task': 'system prompt in a trusted task is not a candidate match',
                'policy': 'new task in governing policy is not a candidate match',
                'setting': 'indirect_tool_content', 'pair_id': source + '-pair',
                'label_basis': 'agent-reviewed source agreement'})
    cells = []
    for row in rows:
        for config in ('jev_firstparty', 'luna_decisions'):
            for condition in ('format', 'task'):
                cells.append({'id': row['id'], 'source': row['source'], 'group': row['group'],
                    'gold': row['semantic_gold'], 'upstream_label': row['upstream_label'],
                    'pair_id': row['pair_id'], 'config': config, 'condition': condition,
                    'split': 'confirmation', 'review_subgroups': {'task_relation': 'related'}})
    schedules = {'main': [{'kind': 'main', 'source': 'browsesafe', 'group': 'main', 'ids': ['m0', 'm1']}],
        'supporting': [{'kind': 'secondary', 'source': 'aib', 'group': 'secondary', 'ids': ['a0', 'a1']},
                       {'kind': 'main_extras', 'source': 'browsesafe', 'group': 'main', 'ids': ['m0', 'm1']}],
        'comparators': [], 'development': []}
    return rows, {'cells': cells, 'schedules': schedules}


class LiteralRules(unittest.TestCase):
    def test_exact_fixed_v5_phrases_casefold_substring_or(self):
        self.assertEqual(baselines.LEXICAL_PHRASES, ('ignore previous', 'system prompt', 'do not tell', 'new task'))
        self.assertEqual(baselines.LEXICAL_PHRASES, execution_plan.LEXICAL_PHRASES)
        for phrase in baselines.LEXICAL_PHRASES:
            self.assertEqual(baselines.predict('lexical_shortcut', 'prefix ' + phrase.upper() + ' suffix'), 1)
        self.assertEqual(baselines.predict('lexical_shortcut', 'ignore\nprevious'), 0)
        self.assertEqual(baselines.predict('lexical_shortcut', 'ignore earlier system instructions'), 0)
        self.assertEqual(baselines.predict('lexical_shortcut', 'new tasks'), 1)
        self.assertEqual(baselines.predict('lexical_shortcut', 'ſystem prompt'), 1)
        self.assertEqual(baselines.predict('constant_allow', 'ignore previous'), 0)
        self.assertEqual(baselines.predict('constant_block', ''), 1)

    def test_no_annotation_task_or_policy_leakage_into_rule(self):
        rows, plan = fixture()
        generated = baselines.build(rows, plan, review_resolution_complete=True)
        lexical = {row['id']: row['prediction'] for row in generated['records'] if row['config'] == 'lexical_shortcut'}
        self.assertEqual(lexical, {'a0': 0, 'a1': 1, 'm0': 0, 'm1': 1})
        self.assertTrue(all(row['score'] is None and row['cost_usd'] == '0' for row in generated['records']))
        self.assertTrue(all(not row['model_inference'] for row in generated['records']))

    def test_source_rows_count_once_across_models_and_conditions(self):
        rows, plan = fixture()
        generated = baselines.build(rows, plan, review_resolution_complete=True)
        self.assertEqual(generated['receipt']['selected_unique_rows'], 4)
        self.assertEqual(len(generated['cells']), 12)
        self.assertEqual(len(generated['records']), 12)
        self.assertEqual({row['condition'] for row in generated['cells']}, {'candidate'})
        self.assertEqual(generated['receipt']['by_source']['aib']['class_rows'], {'0': 1, '1': 1})
        self.assertEqual(generated['receipt']['incremental_api_cost_usd'], '0')
        self.assertEqual(generated['receipt']['new_model_calls'], 0)
        for row in generated['cells']:
            self.assertEqual(row['review_subgroups'], {'task_relation': 'related'})
            self.assertEqual(row['pair_id'], row['source'] + '-pair')

    def test_string_source_labels_normalize_without_changing_source_rows(self):
        rows, plan = fixture()
        for row in rows:
            row['upstream_label'] = 'unsafe' if row['semantic_gold'] else 'safe'
        original = copy.deepcopy(rows)
        generated = baselines.build(rows, plan, review_resolution_complete=True)
        self.assertEqual(rows, original)
        self.assertTrue(all(type(row['upstream_label']) is int for row in generated['cells']))
        joined = analyze.collect(generated['cells'], generated['records'])
        self.assertEqual(len(joined), 12)

    def test_incomplete_review_and_unadmitted_or_changed_metadata_fail_closed(self):
        rows, plan = fixture()
        with self.assertRaises(PermissionError):
            baselines.build(rows, plan)
        bad = copy.deepcopy(rows)
        bad[0]['review_eligible'] = False
        with self.assertRaisesRegex(ValueError, 'unadmitted'):
            baselines.build(bad, plan, review_resolution_complete=True)
        bad = copy.deepcopy(plan)
        bad['cells'][0]['group'] = 'changed'
        with self.assertRaisesRegex(ValueError, 'metadata changes'):
            baselines.build(rows, bad, review_resolution_complete=True)
        bad = copy.deepcopy(rows)
        bad[0]['split_proposal'] = 'development'
        with self.assertRaisesRegex(ValueError, 'nonconfirmation'):
            baselines.build(bad, plan, review_resolution_complete=True)

    def test_baseline_native_candidate_comparison_uses_only_same_rows_pairs(self):
        rows, plan = fixture()
        generated = baselines.build(rows, plan, review_resolution_complete=True)
        # Only one source pair has a native candidate cell. Baseline denominators
        # stay all target rows, while route contrasts use the shared pair.
        native_cells, native_records = [], []
        for row in generated['cells']:
            if row['config'] == 'lexical_shortcut' and row['source'] == 'browsesafe':
                native_cells.append(dict(row, config='jev_firstparty'))
                native_records.append({'id': row['id'], 'config': 'jev_firstparty', 'condition': 'candidate',
                    'valid': True, 'status': 'ok', 'prediction': row['gold'], 'score': .1 if row['gold'] == 0 else .9})
        analysis = analyze.analyze(generated['cells'] + native_cells,
            generated['records'] + native_records, bootstrap_draws=20, randomization_draws=20)
        comparisons = [row for row in analysis['route_comparisons'] if 'jev_firstparty' in (row['left_config'], row['right_config'])]
        self.assertEqual(len(comparisons), 3)
        self.assertTrue(all(row['source'] == 'browsesafe' and row['shared_valid_rows_intact_pairs'] == 2 for row in comparisons))
        self.assertEqual(len(analysis['strata']), 7)
        self.assertEqual(len(analysis['primary_six_test_family']), 6)
        self.assertTrue(all(row['status'] == 'unrun' for row in analysis['primary_six_test_family']))


if __name__ == '__main__':
    unittest.main()
