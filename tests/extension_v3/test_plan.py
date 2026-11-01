import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/extension_v3'))
import plan


class PlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = [r for r in plan.read(ROOT / 'data/expanded-v2/collection.jsonl') if r['split'] == 'dev']

    def test_original_conditions_unchanged(self):
        for config in plan.preserved.PANEL:
            for condition in (['candidate'] if config == 'protectai_local' else ['candidate', 'task']):
                self.assertEqual(plan.request(config, self.rows[0], condition),
                                 plan.preserved.request(config, self.rows[0], condition))

    def test_controls_leave_candidate_and_question_unchanged(self):
        row = self.rows[0]
        for condition in ('format', 'reminder', 'scrambled'):
            original = plan.request('laya_local', row, 'task')
            payload = plan.request('laya_local', row, condition)
            self.assertEqual(original['questions'], payload['questions'])
            self.assertEqual(json.loads(payload['state'])['CANDIDATE'], row['candidate'])

    def test_scramble_preserves_words_and_characters(self):
        for row in self.rows:
            task = row['trusted_task']
            mixed = plan.scrambled(task)
            self.assertEqual(len(task), len(mixed))
            self.assertEqual(sorted(task.split()), sorted(mixed.split()))
            self.assertEqual(mixed, plan.scrambled(task))

    def test_no_specialist_control_or_unknown_condition(self):
        with self.assertRaises(ValueError):
            plan.request('protectai_local', self.rows[0], 'task')
        with self.assertRaises(ValueError):
            plan.request('laya_local', self.rows[0], 'unknown')

    def test_paid_reserve_not_zero_and_subscription_no_fallback(self):
        for config in ('jev_firstparty', 'luna_decisions'):
            payload = plan.request(config, self.rows[0], 'task')
            self.assertGreater(plan.preserved.reserve_usd(config, payload, 'api_key'), 0)
            self.assertEqual(plan.preserved.reserve_usd(config, payload, 'subscription'), 0)


if __name__ == '__main__':
    unittest.main()
