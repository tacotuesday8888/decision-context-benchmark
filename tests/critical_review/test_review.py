import itertools
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

from scripts.critical_review import verify, human_packet


class ReviewChecks(unittest.TestCase):
    def test_signed_missing_bounds_exhaustive(self):
        values = [1, None, None, 0]
        keys = [("m", c, l) for c in ('format', 'task') for l in (0, 1)]
        group = dict(zip(keys, values))
        possible = [verify.difference([1, a, b, 0]) for a, b in itertools.product((0, 1), repeat=2)]
        self.assertEqual(verify.bounds({'g': group}, 'm', 'format'), [min(possible), max(possible)])

    def test_stream_done_with_empty_terminal_output(self):
        events = [{'type': 'response.output_text.done', 'text': '{"injection":false}'},
                  {'type': 'response.completed', 'response': {'output': []}}]
        body = '\n'.join('data: ' + json.dumps(e) for e in events)
        self.assertEqual(verify.stream_answer(body), {'injection': False})
        with self.assertRaises(AssertionError):
            verify.stream_answer(body.splitlines()[0])

    def test_frozen_metrics_forwards_custom_seed(self):
        # This test rejects the mistaken initial review finding F2.
        groups = {'g': {('sol_subscription', c, label):
                       {'config': 'sol_subscription', 'gold': label, 'status': 'ok',
                        'valid': True, 'prediction': label, 'score': None}
                       for c in verify.CONDITIONS for label in (0, 1)}}
        original = verify.analyze_core._seed
        with patch.object(verify.analyze_core, '_seed', wraps=original) as derive:
            verify.analyze_core._metrics(groups, ['g'], 'sol_subscription', draws=10, seed='test-custom-seed')
        self.assertEqual(len(derive.call_args_list), 4)
        self.assertTrue(all(call.args[0] == 'test-custom-seed' for call in derive.call_args_list))

    def test_blinded_packet_omits_mapping_and_preserves_pages(self):
        plan = {'groups': [{'stage': 'audit', 'source_group_id': 'source:private', 'cells': [
            {'payload': {'input': [{'content': json.dumps({'TASK': 'Find X', 'PAGE_A': 'alpha', 'PAGE_B': 'beta'})}]},
             'private_page_mapping': {'A': {'upstream_label': 1}}}]}]}
        selected = {'pairs': [{'packet_id': 'R01', 'group_id': 'source:private', 'selection_reasons': ['flag']}]}
        packet = human_packet.build_packet(plan, selected)
        self.assertEqual(set(packet[0]), {'packet_id', 'task', 'page_A', 'page_B'})
        self.assertEqual({packet[0]['page_A'], packet[0]['page_B']}, {'alpha', 'beta'})
        self.assertNotIn('source:private', json.dumps(packet))

    def test_roster_includes_nonambiguous_disagreement(self):
        selected = human_packet.roster()
        self.assertEqual(selected['required_flagged_groups'], 24)
        self.assertEqual(selected['total_pairs'], 32)
        row = next(r for r in selected['pairs'] if r['group_id'] == 'browsesafe-v7:24123')
        self.assertEqual(row['selection_reasons'], ['AI/source disagreement'])

    def test_receipt_never_replaces_different_output(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'receipt.json'
            verify.write_new(path, {'a': 1})
            verify.write_new(path, {'a': 1})
            with self.assertRaises(ValueError):
                verify.write_new(path, {'a': 2})
            self.assertEqual(verify.read(path), {'a': 1})

    def test_archived_sampling_reproduces_original_intervals(self):
        from scripts.critical_review.sampling_replay import replay
        actual, diagnostics = replay()
        saved = verify.read(verify.ROOT / 'results/subscription-followup-execution/core-analysis-v1.json')
        expected = saved['main']['all_planned_available_output_metrics']['jev_firstparty']['task']['rate_intervals']
        for metric, value in actual.items():
            self.assertEqual(value, expected[metric]['pointwise_95'])
        self.assertTrue(diagnostics['identical_support_counts_and_probability_bits'])

    def test_replay_diff_rejects_real_value_and_structural_changes(self):
        with self.assertRaises(AssertionError):
            verify.check_replay({'n': 5}, {'n': 6})
        with self.assertRaises(AssertionError):
            verify.check_replay({'mean': .1}, {'mean': .2})


if __name__ == '__main__':
    unittest.main()
