import json
from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from analyze_pilot import metrics,resample_indices,paired_summary,wilson


def example(i,gold,pred,group=None):
    return {'id':str(i),'gold':gold,'prediction':pred,'valid':pred is not None,'group':group or str(i)}


class AnalysisTests(unittest.TestCase):
    def test_invalid_does_not_disappear_from_primary_metric(self):
        rows=[example(0,0,0),example(1,0,None),example(2,1,0),example(3,1,1)]
        m=metrics(rows)
        self.assertEqual(m['balanced_accuracy'],.5)
        self.assertEqual(m['fpr'],0)
        self.assertEqual(m['fnr'],.5)
        self.assertEqual(m['valid_n'],3)
        self.assertEqual(m['invalid_negative'],1)
        self.assertGreater(m['fpr_wilson95'][1],0)

    def test_group_members_stay_together(self):
        rows=[example(0,0,0,'source'),example(1,0,0,'source'),example(2,1,1,'team1'),example(3,1,1,'team2')]
        draws=list(resample_indices(rows,draws=30))
        self.assertEqual(len(draws),30)
        for neg,pos in draws:
            self.assertEqual(neg.tolist(),[0,1]);self.assertEqual(len(pos),2)

    def test_paired_null_and_known_gain(self):
        base=[example(0,0,0),example(1,0,0),example(2,1,0),example(3,1,1)]
        changed=[dict(x) for x in base];changed[2]['prediction']=1
        data={'candidate':base,'task':base,'source':changed,'both':changed}
        summary,draws=paired_summary(data)
        self.assertEqual(summary['task']['delta_cluster95'],[0,0])
        self.assertEqual(summary['source']['delta_ba'],.25)
        self.assertEqual(summary['source']['improved_n'],1)
        self.assertEqual(summary['source']['worsened_n'],0)
        self.assertEqual(summary['both']['balanced_accuracy'],1)

    def test_unpaired_cases_rejected(self):
        a=[example(0,0,0),example(1,1,1)]
        with self.assertRaises(ValueError):paired_summary({'candidate':a,'task':a[:1],'source':a,'both':a})

    def test_wilson_zero_and_all_errors_are_not_zero_width(self):
        self.assertGreater(wilson(0,9)[1],.29)
        self.assertLess(wilson(9,9)[0],.71)
        self.assertEqual(wilson(0,0),[None,None])


if __name__=='__main__':unittest.main()

class TerminalMetadataTests(unittest.TestCase):
    def test_incomplete_response_keeps_usage_without_inventing_answer(self):
        from response_metadata import terminal_metadata
        body='data: '+json.dumps({'type':'response.incomplete','response':{'status':'incomplete','model':'gpt-6-luna',
             'usage':{'input_tokens':10,'output_tokens':128},'incomplete_details':{'reason':'max_output_tokens'}}})+'\n\n'
        result=terminal_metadata('openai',body)
        self.assertEqual(result['termination'],'incomplete')
        self.assertEqual(result['usage']['output_tokens'],128)
        self.assertNotIn('prediction',result)
