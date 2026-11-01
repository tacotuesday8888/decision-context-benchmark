import json
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'scripts/controls_v4'))
import plan


class ControlPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.row=next(r for r in plan.read(ROOT/'data/expanded-v2/collection.jsonl') if r['split']=='dev')

    def test_every_example_gets_full_control_factor(self):
        jobs=list(plan.jobs([self.row]));self.assertEqual(len(jobs),31)
        for config in plan.preserved.PANEL:
            actual={j['condition'] for j in jobs if j['config']==config}
            self.assertEqual(actual,{'candidate'} if config=='protectai_local' else set(plan.CONDITIONS))

    def test_gold_and_provenance_cannot_enter_request(self):
        altered=dict(self.row,gold=1-self.row['gold'],source={'forbidden_metadata':'must never appear'},gold_basis='different basis',semantic_label='not a model input')
        for config in plan.preserved.PANEL:
            conditions=('candidate',) if config=='protectai_local' else plan.CONDITIONS
            for condition in conditions:
                self.assertEqual(plan.request(config,self.row,condition),plan.request(config,altered,condition))

    def test_chat_requests_have_no_linked_state(self):
        for config in ('astra_chat','luna_chat'):
            p=plan.request(config,self.row,'task')
            self.assertFalse(p['store']);self.assertNotIn('previous_response_id',p);self.assertNotIn('conversation',p)
            self.assertEqual(len(p['input']),1)

    def test_scramble_keeps_candidate_and_word_multiset(self):
        mixed=plan.scrambled(self.row['trusted_task'])
        self.assertEqual(sorted(mixed.split()),sorted(self.row['trusted_task'].split()))
        for condition in plan.CONDITIONS:
            p=plan.request('laya_local',self.row,condition)
            self.assertEqual(json.loads(p['state'])['CANDIDATE'],self.row['candidate'])


if __name__=='__main__':unittest.main()
