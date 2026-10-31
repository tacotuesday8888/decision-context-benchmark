"""Behavioral fixtures for scientific boundaries and frozen allocation order."""
import copy
import json
import unittest

from scripts.study_v6 import plan
from scripts.study_v5.prompts import evidence, native_payload, conditions


def row(i, source='browsesafe', split='confirmation', gold=0, group=None, **kw):
    value = {'id': str(i), 'review_id': 'review-' + str(i), 'source': source,
        'candidate': 'A complete page. Evidence annotations may be literal page words.',
        'task': 'Read the complete page and summarize its contents.',
        'policy': None, 'setting': 'indirect_tool_content',
        'group': group or 'group-' + str(i), 'pair_id': str(i),
        'split_proposal': split, 'semantic_gold': gold, 'upstream_label': gold,
        'review_eligible': True, 'inference_eligible': False, 'exclusion_reasons': []}
    value.update(kw)
    return value


class PlanTests(unittest.TestCase):
    def test_candidate_and_context_bytes_only(self):
        r = row('a', policy='Only read documents.', candidate='\nUnicode: café\tignore previous\n')
        r['annotation_secret'] = 'DO NOT LEAK THIS ANNOTATION'
        r['expected_answer'] = 'some reference answer'
        for c in conditions(r):
            p = native_payload(r, c, 'jev_firstparty')
            state = json.loads(p['state'])
            self.assertEqual(state['CANDIDATE'], r['candidate'])
            self.assertNotIn('DO NOT LEAK THIS ANNOTATION', p['state'])
            self.assertNotIn('some reference answer', p['state'])
        self.assertEqual(evidence(r, 'policy_reminder')['GOVERNING_SYSTEM_POLICY'], r['policy'])
        self.assertEqual(len(evidence(r, 'policy_length')['TRUSTED_USER_TASK']), len(r['task']))

    def test_dedup_is_within_config_and_split_keeps_refs(self):
        a = row('a', group='pair', pair_id='pair', gold=0)
        b = row('b', group='pair', pair_id='pair', gold=1)
        c = row('c', split='development')
        result = plan.build([a, b, c])
        native = [q for q in result['requests'] if q['config'] == 'jev_firstparty']
        self.assertTrue(any(len(q['refs']) == 2 for q in native))
        for q in native:
            self.assertEqual({r['id'] for r in q['refs']} <= {'a','b'}, q['split'] == 'confirmation')
        self.assertEqual(len(result['cells']), len({(c['id'], c['config'], c['condition'], c['split']) for c in result['cells']}))
        self.assertTrue(all(not c['inference_eligible'] for c in result['cells']))

    def test_main_full_target_and_fixed_first_100(self):
        rows = [row(i, candidate='page ' + str(i)) for i in range(105)]
        result = plan.build(rows)
        self.assertEqual(len(result['schedules']['main']), 105)
        comparator = result['schedules']['comparators']
        self.assertEqual([e['group'] for e in comparator], [e['group'] for e in result['schedules']['main'][:100]])
        self.assertTrue(all(e['batch'].startswith('main:') for e in result['schedules']['main']))
        self.assertEqual({c['condition'] for c in result['cells'] if c['allocation'] == 'main'}, set(plan.PRIMARY))

    def test_secondary_round_robin_no_moving_no_splitting(self):
        rows = [row(s + str(i), source=s, candidate=s + str(i)) for s in plan.SOURCES for i in range(3)]
        result = plan.build(rows)
        self.assertEqual([e['source'] for e in result['schedules']['supporting'][:5]], list(plan.SOURCES))
        self.assertFalse(result['schedules']['development'])
        self.assertFalse(any(c['config'] == 'protectai_local' and c['source'] in ('scope', 'spml') for c in result['cells']))

    def test_development_longest_per_label_then_distinct_hash_groups(self):
        rows = [row(i, split='development', gold=i % 2, candidate='x' * (i + 1)) for i in range(12)]
        chosen = plan.development_rows(rows)
        self.assertEqual(len(chosen), 4)
        self.assertTrue({'10', '11'} <= {r['id'] for r in chosen})
        self.assertEqual(len({r['group'] for r in chosen}), 4)
        self.assertEqual(plan.development_rows(rows), plan.development_rows(list(reversed(rows))))

    def test_common_native_pair_coverage_and_pending(self):
        rows = [row('a', group='g', pair_id='p'), row('b', group='g', pair_id='p', gold=1, candidate='attack')]
        coverage = {(r['id'], config, c): {'status': 'complete'} for r in rows for config in plan.CONFIGS for c in conditions(r)}
        coverage[('b', 'jev_firstparty', 'length')] = {'status': 'unsupported_over_limit'}
        result = plan.build(rows, coverage)
        main = [c for c in result['cells'] if c['allocation'] == 'main']
        self.assertTrue(all(not c['coverage_supported'] for c in main))
        self.assertTrue(all(not c['inference_eligible'] for c in result['cells']))
        self.assertTrue(all(not c['coverage_supported'] for c in plan.build(rows)['cells']))

    def test_quarantine_and_exposure_cannot_be_restored(self):
        excluded = row('q', review_eligible=False, semantic_gold=None, exclusion_reasons=['historical_exposure'])
        result = plan.build([excluded])
        self.assertEqual(result['requests'], [])
        invalid = row('bad', exclusion_reasons=['historical_exposure'])
        with self.assertRaises(ValueError):
            plan.build([invalid])


if __name__ == '__main__':
    unittest.main()
