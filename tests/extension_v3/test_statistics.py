import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('extension_statistics', ROOT / 'scripts/extension_v3/statistics.py')
stats = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(stats)
    HAS_NUMPY = True
except ModuleNotFoundError as error:
    if error.name != 'numpy':
        raise
    HAS_NUMPY = False


@unittest.skipUnless(HAS_NUMPY, 'Analysis environment requires numpy')
class EstimatorTests(unittest.TestCase):
    def test_repeated_task_does_not_dominate(self):
        self.assertEqual(stats.task_mean([0, 0, 0, 1], ['a', 'a', 'a', 'b']), .5)

    def test_native_tie_in_forecasts_not_classification(self):
        rows = [{'gold': 1, 'score': .5, 'prediction': None, 'status': 'tie', 'valid': False}]
        self.assertEqual(stats.classification(rows)['valid'], 0)
        self.assertEqual(stats.forecast(rows)['brier'], .25)
        self.assertEqual(stats.classification(rows)['accuracy_bounds_all_planned'], [0, 1])

    def test_missing_boolean_score_not_fabricated(self):
        rows = [{'gold': 1, 'prediction': 1, 'valid': True, 'status': 'ok'}]
        self.assertEqual(stats.forecast(rows)['n_forecasts'], 0)
        self.assertIsNone(stats.classification(rows)['fpr'])
        self.assertIsNone(stats.classification(rows)['balanced_accuracy'])

    def test_conflicting_forecasts_are_penalized(self):
        self.assertEqual(stats.losses(0, 1)['brier'], 1)
        self.assertGreater(stats.losses(0, 1)['log_loss'], 13)
        with self.assertRaises(ValueError):
            stats.losses(0, float('nan'))

    def test_constant_effect_and_insufficient_groups(self):
        result = stats.crossed_interval([.25] * 6, list('abcdef'), list('ghijkl'), draws=100)
        self.assertEqual(result['interval'], [.25, .25])
        self.assertTrue(result['degenerate_interval'])
        self.assertIsNone(stats.crossed_interval([0, 1], ['a', 'b'], ['x', 'y'])['interval'])

    def test_interval_reproducible(self):
        args = ([0, 1, 0, 1, -1, 0], list('abcdef'), list('ghijkl'))
        self.assertEqual(stats.crossed_interval(*args, draws=100), stats.crossed_interval(*args, draws=100))


if __name__ == '__main__':
    unittest.main()
