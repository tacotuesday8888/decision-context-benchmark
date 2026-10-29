import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'scripts/expanded_execution'))
import execute as e


class ExecutionTests(unittest.TestCase):
    def test_cap_blocks_before_call_and_pending_survives_restart(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'ledger.json'
            ledger=e.Ledger(p, .01)
            ledger.begin('attempt1', .008)
            with self.assertRaises(PermissionError):
                e.Ledger(p,.01).begin('attempt2', .003)
            with self.assertRaises(ValueError):
                ledger.begin('attempt1', .001)
            self.assertEqual(len(json.loads(p.read_text())['entries']),1)

    def test_unknown_usage_keeps_reservation_and_known_usage_releases(self):
        with tempfile.TemporaryDirectory() as d:
            ledger=e.Ledger(Path(d)/'ledger.json', .1)
            ledger.begin('a', .05); ledger.finish('a', None)
            ledger.begin('b', .05); ledger.finish('b', .001)
            self.assertAlmostEqual(sum(x['accounted_usd'] for x in ledger.data['entries']), .051)
            with self.assertRaises(ValueError): e.Ledger(ledger.path,1)

    def test_invalid_caps_and_provider_overrun_stop(self):
        with tempfile.TemporaryDirectory() as d:
            for cap in [-1, float('nan'),float('inf')]:
                with self.assertRaises(ValueError): e.Ledger(Path(d)/'l.json',cap)
            ledger=e.Ledger(Path(d)/'l.json',.1);ledger.begin('a',.001)
            with self.assertRaises(RuntimeError): ledger.finish('a',.002)
            self.assertEqual(json.loads(ledger.path.read_text())['entries'][0]['accounted_usd'],.002)

    def test_full_output_reserve_and_no_subscription_charges(self):
        payload={'input':'hello'}
        self.assertGreater(e.reserve_usd('astra_chat',payload,'api_key'),.1024)
        self.assertEqual(e.reserve_usd('astra_chat',payload,'subscription'),0)
        self.assertIsNone(e.metered_cost('luna_decisions',{},'api_key'))
        self.assertIsNone(e.metered_cost('luna_decisions',{'usage':{'input_tokens':True}},'api_key'))

    def test_eval_refuses_without_successful_dev(self):
        with tempfile.TemporaryDirectory() as d, patch.object(e,'OUT',Path(d)):
            with self.assertRaises(PermissionError):
                e.run('jev_firstparty','eval',{'jev_firstparty':'api_key'},None,'hash')

    def test_http_billing_failure_saved_then_never_retried(self):
        with tempfile.TemporaryDirectory() as d, patch.object(e,'OUT',Path(d)), \
             patch.object(e,'env_secret',return_value='secret-test-value'), \
             patch.object(e,'post',return_value=({'http_status':402},'billing failure secret-test-value')) as post:
            ledger=e.Ledger(Path(d)/'ledger.json',.99)
            e.run('jev_firstparty','dev',{'jev_firstparty':'api_key'},ledger,'hash')
            self.assertEqual(post.call_count,1)
            with self.assertRaises(PermissionError):
                e.run('jev_firstparty','dev',{'jev_firstparty':'api_key'},ledger,'hash')
            self.assertNotIn('secret-test-value',''.join(p.read_text() for p in Path(d).rglob('*.json')))
            self.assertEqual(post.call_count,1)

    def test_standalone_stream_quota_error_is_provider_failure(self):
        body='data: '+json.dumps({'type':'error','code':'subscription_sharing_usage_limit_exceeded'})+'\n\n'
        result=e.safe_parse('luna_chat',body)
        self.assertEqual(result['status'],'provider_failed')
        self.assertFalse(result['valid'])

    def test_frozen_artifacts_still_match(self):
        e.verify_preparation()


class AnalysisTests(unittest.TestCase):
    def test_invalids_and_one_class_denominators(self):
        import analyze
        rows=[{'gold':0,'valid':True,'prediction':1,'status':'ok'},
              {'gold':0,'valid':False,'prediction':None,'status':'invalid_format'},
              {'gold':1,'valid':True,'prediction':1,'status':'ok'}]
        m=analyze.metrics(rows)
        self.assertEqual(m['strict_balanced_accuracy'],.5)
        self.assertEqual(m['valid_fpr'],1)
        self.assertEqual(m['valid_negative_n'],1)
        self.assertEqual(m['invalid_n'],1)
        self.assertIsNone(analyze.metrics(rows[:2])['strict_balanced_accuracy'])

    def test_paired_bootstrap_preserves_both_labels_and_conditions(self):
        import analyze
        rows=[{'id':f'{i}:{g}','gold':g,'dataset':'bipia-email','groups':{'document':str(i),'attack_family':str(i)}} for i in range(3) for g in [0,1]]
        base={r['id']:{**r,'valid':True,'prediction':1-r['gold'],'status':'ok'} for r in rows}
        other={r['id']:{**r,'valid':True,'prediction':r['gold'],'status':'ok'} for r in rows}
        p=analyze.paired(rows,base,other)
        self.assertEqual(p['strict_correctness_delta'],1)
        self.assertEqual(p['intervals']['document']['interval'],[1,1])
        self.assertEqual(p['intervals']['document']['clusters'],3)

class CredentialTests(unittest.TestCase):
    def test_atomic_private_save_preserves_other_entries(self):
        import credential_entry
        with tempfile.TemporaryDirectory() as d, patch.object(credential_entry,'ROOT',Path(d)):
            import subprocess
            subprocess.run(['git','init','-q',d],check=True)
            (Path(d)/'.gitignore').write_text('.env.*\n')
            p=Path(d)/'.env.local';p.write_text('OTHER=value\n# preserved\n')
            credential_entry.write_secret('TYPESAFE_API_KEY','apikey_'+'fake_test_only_'*3)
            self.assertEqual(p.stat().st_mode & 0o777,0o600)
            self.assertTrue(p.read_text().startswith('OTHER=value\n# preserved\n'))
            p.unlink();p.symlink_to(Path(d)/'other')
            with self.assertRaises(ValueError):credential_entry.write_secret('TYPESAFE_API_KEY','apikey_'+'fake_test_only_'*3)

class SharedBudgetTests(unittest.TestCase):
    def test_independent_ledgers_share_one_cap(self):
        with tempfile.TemporaryDirectory() as d:
            a=e.Ledger(Path(d)/'execution-ledger-a.json',.1)
            b=e.Ledger(Path(d)/'execution-ledger-b.json',.1)
            a.begin('a',.06)
            with self.assertRaises(PermissionError):b.begin('b',.05)
            a.finish('a',.01)
            b.begin('b',.05)
            self.assertEqual(len(b.data['entries']),1)

    def test_two_handles_reload_same_ledger_without_lost_reservations(self):
        with tempfile.TemporaryDirectory() as d:
            a=e.Ledger(Path(d)/'ledger.json',.1)
            b=e.Ledger(Path(d)/'ledger.json',.1)
            a.begin('a',.04);b.begin('b',.04);a.finish('a',.01)
            data=json.loads(a.path.read_text())
            self.assertEqual(len(data['entries']),2)
            self.assertAlmostEqual(sum(x['accounted_usd'] for x in data['entries']),.05)

if __name__=='__main__':unittest.main()
