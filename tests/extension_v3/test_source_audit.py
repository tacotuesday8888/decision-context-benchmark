"""Parser/integrity regression tests; fixtures below are not benchmark examples."""
import copy
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('audit', ROOT / 'scripts/extension_v3/source_audit.py')
audit = importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class ProvenanceTests(unittest.TestCase):
    def fixture(self):
        return {'user_task_id': 'user_task_0', 'suite_name': 'test', 'attack_type': None,
                'injections': {}, 'messages': [
                    {'role': 'user', 'content': 'task'},
                    {'role': 'tool', 'content': [{'type': 'text', 'content': 'payload'}]}]}

    def inspect(self, fixture):
        return audit.inspect_trace(fixture, 'fixture.json', 'hash')

    def test_attacker_goal_baseline_is_not_benign(self):
        fixture = self.fixture()
        fixture['user_task_id'] = 'injection_task_0'
        rows, reason = self.inspect(fixture)
        self.assertEqual(rows, [])
        self.assertEqual(reason, 'attacker_goal_or_unknown_task')

    def test_baseline_does_not_invent_gold(self):
        rows, reason = self.inspect(self.fixture())
        self.assertIsNone(reason)
        self.assertIsNone(rows[0]['gold'])
        self.assertEqual(rows[0]['task_sha256'], audit.sha('task'))

    def test_nonmatching_attacked_message_not_negative(self):
        fixture = self.fixture()
        fixture.update(attack_type='important_instructions', injections={'slot': 'different'})
        rows, reason = self.inspect(fixture)
        self.assertEqual(rows, [])
        self.assertEqual(reason, 'no_eligible_tool_message')

    def test_whitespace_matching_preserves_bytes(self):
        fixture = self.fixture()
        fixture.update(attack_type='important_instructions', injections={'slot': 'pay\n\nload'})
        fixture['messages'][1]['content'][0]['content'] = 'prefix pay\nload suffix'
        rows, _ = self.inspect(fixture)
        self.assertEqual(rows[0]['candidate_sha256'], audit.sha('prefix pay\nload suffix'))
        self.assertEqual(rows[0]['label_evidence'], 'published_injection_present')

    def test_multiple_user_messages_rejected(self):
        fixture = self.fixture()
        fixture['messages'].append(copy.deepcopy(fixture['messages'][0]))
        self.assertEqual(self.inspect(fixture)[1], 'ambiguous_user_context')

    def test_nontext_content_not_silently_dropped(self):
        self.assertIsNone(audit.content({'content': [{'type': 'image', 'url': 'unused'}]}))


if __name__ == '__main__':
    unittest.main()
