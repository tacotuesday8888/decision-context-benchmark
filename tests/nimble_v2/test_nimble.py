import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/nimble_v2'))
import local as n
import run as r


def native(value=.99):
    return {'model':n.MODEL,'answers':{'injection':{'type':'noul','noul':value}},'usage':{'input_tokens':123,'output_tokens':1}}


class NimbleTests(unittest.TestCase):
    def test_probability_and_tie_semantics(self):
        self.assertEqual(n.parse(native(.99))['score'],.99)
        self.assertEqual(n.parse(native(.5))['status'],'tie')
        for value in [True,-.1,1.1,float('nan')]:
            with self.assertRaises(ValueError):n.parse(native(value))

    def test_invalid_model_usage_and_truncation_rejected(self):
        x=native();x['model']='nimble:cloud'
        self.assertEqual(n.parse(x)['status'],'model_mismatch')
        for value in [True,0,None]:
            x=native();x['usage']['input_tokens']=value
            self.assertEqual(n.parse(x)['status'],'missing_usage')
        x=native();x['usage']['truncated']=True
        self.assertEqual(n.parse(x)['status'],'truncated')

    def test_development_selection_and_long_input(self):
        jobs=r.selected_dev();self.assertEqual(len(jobs),14)
        self.assertTrue(all(row['split']=='dev' for row,_ in jobs))
        longest=max((row for row in r.jsonl(r.DATA/'collection.jsonl') if row['split']=='dev'),key=lambda row:len(row['candidate']))
        self.assertIn(longest['id'],{row['id'] for row,_ in jobs})

    def test_evaluation_never_starts_without_freeze(self):
        with patch.object(r,'verify_freeze',side_effect=PermissionError('not frozen')),patch.object(r,'verify_model') as verify:
            with self.assertRaises(PermissionError):r.run('eval')
            verify.assert_not_called()

    def test_only_loopback_and_no_redirects(self):
        self.assertEqual(n.BASE,'http://127.0.0.1:11434')
        with self.assertRaises(ValueError):n.call('https://example.com')
        with self.assertRaises(ValueError):n.NoRedirect().redirect_request(None,None,None,None,None,None)

    def test_runtime_failure_saved_even_when_metadata_server_is_down(self):
        row,condition=r.selected_dev()[0]
        with tempfile.TemporaryDirectory() as directory:
            temp=Path(directory);out=temp/'setup';out.mkdir()
            (out/'execution-config.json').write_text(json.dumps({'configuration':n.CONFIG}))
            with patch.object(r,'OUT',out),patch.object(r,'RECORDS',temp/'records'),patch.object(r,'verify_preparation'),patch.object(r,'verify_model',return_value={}),patch.object(r,'selected_dev',return_value=[(row,condition)]),patch.object(r,'call',side_effect=ConnectionError):
                with self.assertRaises(RuntimeError):r.run('dev')
            records=list((temp/'records/checks/nimble_local').glob('*-0.json'))
            self.assertEqual(len(records),1)
            saved=json.loads(records[0].read_text())
            self.assertEqual(saved['parsed']['status'],'local_runtime_error')
            self.assertTrue(saved['observation']['loaded_models']['metadata_unavailable'])
            self.assertTrue((temp/'records/checks/nimble_local/STOP.json').exists())

    def test_saved_real_development_evidence(self):
        rows={row['id']:row for row,_ in r.selected_dev()}
        paths=list((r.RECORDS/'checks/nimble_local').glob('*-0.json'))
        self.assertEqual(len(paths),14)
        for path in paths:
            record=json.loads(path.read_text())
            self.assertEqual(record['request'],n.request(rows[record['id']],record['condition']))
            self.assertEqual(record['parsed'],n.parse(record['raw_response']))
            self.assertEqual(record['split'],'dev')
            self.assertEqual(record['conservative_usage_cost_usd'],0)
            self.assertFalse(record['paid_request'])
            loaded=record['observation']['loaded_models']['models']
            self.assertTrue(any(m.get('digest')==n.DIGEST for m in loaded))

if __name__=='__main__':unittest.main()
