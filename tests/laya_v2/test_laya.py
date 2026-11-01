import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/laya_v2'))
import adapter as a
import runner as r


def native(score=.7,**usage):
    return {'model':'laya-rl-agent','answers':{'injection':{'type':'noul','noul':score}},
            'usage':{'input_tokens':120,'state_tokens_dropped':0,'truncated':False,**usage}}


class LayaTests(unittest.TestCase):
    def test_native_output_tie_and_invalid_probabilities(self):
        self.assertEqual(a.parse(native())['prediction'],1)
        self.assertEqual(a.parse(native(.5))['status'],'tie')
        for score in [True,-1,1.01,float('nan')]:
            with self.assertRaises(ValueError):a.parse(native(score))

    def test_truncation_and_missing_usage_are_never_valid(self):
        self.assertEqual(a.parse(native(truncated=True,state_tokens_dropped=10))['status'],'truncated')
        self.assertEqual(a.parse(native(input_tokens=0))['status'],'missing_usage')
        raw=native();raw['model']='different'
        self.assertEqual(a.parse(raw)['status'],'model_mismatch')

    def test_frozen_question_and_trust_boundaries(self):
        rows=r.jsonl(r.DATA/'collection.jsonl')
        row=next(x for x in rows if x['split']=='dev')
        payload=a.request(row,'task');state=json.loads(payload['state'])
        self.assertEqual(set(state),{'CANDIDATE','TRUSTED_USER_TASK'})
        self.assertEqual(payload['questions']['injection']['instructions'],a.QUESTION)
        self.assertNotIn('gold',payload)
        with self.assertRaises(ValueError):a.request(row,'both')

    def test_development_jobs_never_include_evaluation(self):
        self.assertEqual(len(r.jobs('dev')),120)
        self.assertEqual(len({row['id'] for row,_ in r.jobs('dev')}),60)
        self.assertTrue(all(row['split']=='dev' for row,_ in r.jobs('dev')))
        self.assertEqual(len(r.jobs('eval')),812)

    def test_evaluation_requires_a_freeze_before_loading_weights(self):
        with patch.object(r,'verify_freeze',side_effect=PermissionError('not frozen')), \
             patch.object(r,'LocalDecision') as loader:
            with self.assertRaises(PermissionError):r.run('eval')
            loader.assert_not_called()

    def test_saved_development_requests_and_parsing(self):
        rows={row['id']:row for row,_ in r.jobs('dev')}
        paths=list((r.RECORDS/'checks/laya_local').glob('*-0.json'))
        self.assertEqual(len(paths),120)
        for p in paths:
            record=json.loads(p.read_text())
            self.assertEqual(record['split'],'dev')
            self.assertEqual(record['request'],a.request(rows[record['id']],record['condition']))
            self.assertEqual(record['parsed'],a.parse(record['raw_response']))
            self.assertFalse(record['token_audit']['truncated'])
            self.assertEqual(record['token_audit']['input_tokens'],record['parsed']['usage']['input_tokens'])
            self.assertEqual(record['conservative_usage_cost_usd'],0)

    def test_registered_without_mutating_frozen_panel(self):
        import execute
        self.assertIn('laya_local',execute.PANEL)
        self.assertNotIn('laya_local',execute.PREPARED_PANEL)
        row=r.jobs('dev')[0][0]
        self.assertEqual(execute.request('laya_local',row,'candidate'),a.request(row,'candidate'))

if __name__=='__main__':unittest.main()
