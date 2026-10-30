"""Accounting/terminal-state fixtures only; no benchmark text or gold labels."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'scripts/extension_v3'))
spec = importlib.util.spec_from_file_location('closure_gate', ROOT / 'scripts/extension_v3/closure.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.old = module.ROOT, module.OUT, module.RAW
        module.ROOT = Path(self.temp.name)
        module.OUT = module.ROOT / 'results/extension-v3'
        module.RAW = module.ROOT / 'data/raw/extension-v3'
        module.RAW.mkdir(parents=True)
        (module.OUT / 'confirmation/jev_firstparty').mkdir(parents=True)
        self.job = {'id': 'operational_fixture', 'config': 'jev_firstparty', 'condition': 'candidate'}
        self.key = module.sha(json.dumps(self.job, sort_keys=True))[:24]
        self.identity = 'confirmation:jev_firstparty:' + self.key
        self.write(module.OUT / 'development-freeze-v1.json', {'jobs': []})
        self.write(module.OUT / 'confirmation-freeze-v1.json', {'jobs': [self.job]})
        self.write(module.OUT / 'request-plan-v1.json', {'prior_accounted_usd': {'openai': 0., 'typesafe': .005}, 'provider_caps_usd': {'openai': .1, 'typesafe': .1}})
        self.entry = {'key': self.identity, 'config': 'jev_firstparty', 'provider': 'typesafe', 'status': 'settled', 'reserved_usd': .01, 'accounted_usd': .002}
        self.record = {'job': self.job, 'split': 'confirmation', 'attempt': 0, 'status': 'completed', 'reserved_usd': .01, 'conservative_usage_cost_usd': .002}
        self.path = module.OUT / 'confirmation/jev_firstparty' / (self.key + '.json')
        self.save()

    def tearDown(self):
        module.ROOT, module.OUT, module.RAW = self.old
        self.temp.cleanup()

    @staticmethod
    def write(path, value):
        path.write_text(json.dumps(value))

    def save(self):
        self.write(module.OUT / 'inference-ledger-v1.json', {'entries': [self.entry]})
        self.write(self.path, self.record)

    def check(self):
        with contextlib.redirect_stdout(io.StringIO()):
            return module.closure(True)

    def test_clean_export_without_ignored_directory(self):
        module.RAW.rmdir()
        result = self.check()
        self.assertEqual(result["status"], "terminal")
        self.assertTrue((module.RAW / "inference-budget.lock").exists())

    def test_terminal_requires_every_frozen_cell(self):
        self.path.unlink()
        self.entry.update(status='pending', accounted_usd=.01)
        self.write(module.OUT / 'inference-ledger-v1.json', {'entries': [self.entry]})
        with self.assertRaisesRegex(AssertionError, 'Incomplete:'):
            self.check()
        self.assertFalse((module.OUT / 'execution-closure-v1.json').exists())

    def test_prior_spend_and_unknown_reservation_remain_counted(self):
        self.entry.update(status='unknown_usage', accounted_usd=.01)
        self.record.update(status='failed', conservative_usage_cost_usd=None)
        self.save()
        result = self.check()
        self.assertEqual(result['unknown_usage_reservations_retained'], [self.identity])
        self.assertAlmostEqual(result['all_in_conservative_accounted_usd']['typesafe'], .015)

    def test_extra_unplanned_raw_record_fails(self):
        self.write(self.path.parent / 'unexpected.json', self.record)
        with self.assertRaisesRegex(AssertionError, 'Unplanned/unreserved'):
            self.check()

    def test_settled_amount_must_match_raw_evidence(self):
        self.entry['accounted_usd'] = .003
        self.save()
        with self.assertRaises(AssertionError):
            self.check()

    def test_caps_include_prior_cost(self):
        self.write(module.OUT / 'request-plan-v1.json', {'prior_accounted_usd': {'openai': 0., 'typesafe': .099}, 'provider_caps_usd': {'openai': .1, 'typesafe': .1}})
        with self.assertRaises(AssertionError):
            self.check()


if __name__ == '__main__':
    unittest.main()
