import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/controls_v4'))
import run

class AccountingTests(unittest.TestCase):
    def test_prior_all_in_cost_blocks_new_reservation(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder);out=base/'out';raw=base/'raw';out.mkdir();raw.mkdir()
            (out/'request-plan-v1.json').write_text(json.dumps({'prior_accounted_usd':{'openai':14.99},'provider_caps_usd':{'openai':15}}))
            with patch.object(run,'OUT',out),patch.object(run,'RAW',raw):
                with self.assertRaises(PermissionError):run.transact('a','luna_decisions',amount=.02)
                run.transact('a','luna_decisions',amount=.01)
                run.transact('a','luna_decisions',settled=None)
                with self.assertRaises(PermissionError):run.transact('b','luna_decisions',amount=.001)
                ledger=json.loads((out/'inference-ledger-v1.json').read_text())
                self.assertEqual(ledger['entries'][0]['status'],'unknown_usage')
                self.assertEqual(ledger['entries'][0]['accounted_usd'],.01)

    def test_duplicate_attempt_cannot_reserve_twice(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder)
            with patch.object(run,'OUT',base),patch.object(run,'RAW',base):
                run.transact('local','laya_local',amount=0)
                with self.assertRaises(ValueError):run.transact('local','laya_local',amount=0)

if __name__=='__main__':unittest.main()
