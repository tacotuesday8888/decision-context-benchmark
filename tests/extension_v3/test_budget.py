import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/extension_v3'))
spec = importlib.util.spec_from_file_location('extension_runner', ROOT / 'scripts/extension_v3/run.py')
runner = importlib.util.module_from_spec(spec)
spec.loader.exec_module(runner)


class BudgetTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.patchers = [patch.object(runner, 'OUT', self.root), patch.object(runner, 'RAW', self.root),
            patch.object(runner.plan.preserved, 'provider_totals', return_value={'openai': .2, 'typesafe': .1}),
            patch.object(runner.plan.preserved, 'provider_caps', return_value={'openai': 1, 'typesafe': 1})]
        for p in self.patchers:
            p.start()

    def tearDown(self):
        for p in reversed(self.patchers):
            p.stop()
        self.temp.cleanup()

    def entries(self):
        return json.loads((self.root / 'inference-ledger-v1.json').read_text())['entries']

    def test_prior_spend_and_pending_count_against_cap(self):
        runner.transact('a', 'luna_decisions', amount=.7)
        with self.assertRaises(PermissionError):
            runner.transact('b', 'luna_decisions', amount=.2)
        self.assertEqual(len(self.entries()), 1)

    def test_provider_caps_are_independent(self):
        runner.transact('a', 'luna_decisions', amount=.7)
        runner.transact('b', 'jev_firstparty', amount=.8)
        self.assertEqual(len(self.entries()), 2)

    def test_unknown_keeps_reservation_and_duplicate_rejected(self):
        runner.transact('a', 'luna_decisions', amount=.4)
        runner.transact('a', 'luna_decisions', settled=None)
        self.assertEqual(self.entries()[0]['accounted_usd'], .4)
        with self.assertRaises(ValueError):
            runner.transact('a', 'luna_decisions', amount=.4)

    def test_settlement_cannot_exceed_bound(self):
        runner.transact('a', 'luna_decisions', amount=.4)
        with self.assertRaises(ValueError):
            runner.transact('a', 'luna_decisions', settled=.5)
        self.assertEqual(self.entries()[0]['status'], 'pending')
        runner.transact('a', 'luna_decisions', settled=.1)
        self.assertEqual(self.entries()[0]['accounted_usd'], .1)


if __name__ == '__main__':
    unittest.main()
