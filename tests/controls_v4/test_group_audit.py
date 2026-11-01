import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts/controls_v4'))
from group_audit import components


class GroupAuditTests(unittest.TestCase):
    def test_transitive_shared_documents_cannot_cross_splits(self):
        # Identifier-only operational fixture, not benchmark examples or labels.
        rows = [{'task_group': t, 'candidate_sha256': d} for t,d in
                [('a','x'), ('b','x'), ('b','y'), ('c','y'), ('d','z')]]
        result = components(rows)
        self.assertEqual(result['connected_component_sizes'], [3,1])
        self.assertEqual(result['texts_shared_across_tasks'], 2)

    def test_repeated_calls_do_not_increase_sample_size(self):
        row = {'task_group': 'a', 'candidate_sha256': 'x'}
        self.assertEqual(components([row]), components([row]*5))


if __name__ == '__main__':
    unittest.main()
