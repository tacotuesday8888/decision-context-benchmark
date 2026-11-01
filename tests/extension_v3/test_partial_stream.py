"""Transport-only fixtures; no generated benchmark examples or labels."""
import copy
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/extension_v3'))
from continue_reviewed_v4 import nonterminal_timeout


class PartialStreamTests(unittest.TestCase):
    def fixture(self):
        response = {'model': 'gpt-6-astra', 'status': 'in_progress', 'output': [],
            'error': None, 'incomplete_details': None, 'usage': None}
        body = ''.join('event: ' + t + '\ndata: ' + json.dumps({'type': t, 'response': response})
            + '\n\n' for t in ('response.created', 'response.in_progress'))
        return {'access_route': 'subscription', 'paid_request': False,
            'observation': {'http_status': 200, 'transport_exit_code': 28},
            'parsed': {'prediction': None, 'status': 'interrupted_stream',
                'termination': 'missing_terminal_event', 'valid': False}, 'raw_body': body}

    def test_only_nonterminal_empty_output_is_eligible(self):
        self.assertTrue(nonterminal_timeout(self.fixture()))

    def test_answer_terminal_or_error_events_are_ineligible(self):
        for event in ('response.output_text.delta', 'response.completed', 'response.failed', 'error'):
            record = self.fixture()
            record['raw_body'] += 'event: ' + event + '\ndata: {}\n\n'
            self.assertFalse(nonterminal_timeout(record))
        record = self.fixture()
        record['raw_body'] = record['raw_body'].replace('"output": []', '"output": [{"refusal": "refused"}]')
        self.assertFalse(nonterminal_timeout(record))

    def test_paid_accounting_or_non_timeout_ineligible(self):
        changes = [{'paid_request': True}, {'accounting_error': 'missing usage'},
            {'observation': {'http_status': 200, 'transport_exit_code': 0}}]
        for change in changes:
            record = self.fixture(); record.update(change)
            self.assertFalse(nonterminal_timeout(record))

    def test_usage_provider_error_malformed_or_wrong_model_ineligible(self):
        for old, new in [('"usage": null', '"usage": {}'), ('"error": null', '"error": {}'),
                ('gpt-6-astra', 'another-model'), ('data: {', 'data: invalid{')]:
            record = self.fixture(); record['raw_body'] = record['raw_body'].replace(old, new)
            self.assertFalse(nonterminal_timeout(record))


if __name__ == '__main__':
    unittest.main()
