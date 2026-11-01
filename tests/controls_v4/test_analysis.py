import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/controls_v4'))
try:
 import analyze
except ModuleNotFoundError:
 analyze=None
@unittest.skipIf(analyze is None,'Analysis runtime requires numpy')
class AnalysisTests(unittest.TestCase):
    def row(self,identity,condition,prediction,article,task):
        return {'id':identity,'condition':condition,'prediction':prediction,'gold':1,'valid':prediction is not None,
            'status':'ok' if prediction is not None else 'http_error','score':None,'dataset':'tasktracker-qa-advbench',
            'candidate_sha256':identity,'groups':{'primary_cluster':article,'task':task,'secondary_cluster':identity}}
    def test_direction_and_article_weight_not_task_weight(self):
        rows=[]
        for identity,article,pred in [('a','article1',1),('b','article1',1),('c','article2',0)]:
            rows.extend([self.row(identity,'reminder',0,article,identity),self.row(identity,'task',pred,article,identity)])
        result=analyze.paired(rows,'reminder','task','error')
        self.assertEqual(result['primary_cluster_weighted']['estimate'],.5)
        self.assertAlmostEqual(result['equal_task_estimate'],2/3)
        self.assertIsNone(result['primary_cluster_weighted']['interval'])
    def test_missing_contrast_bounds(self):
        rows=[self.row('a','format',None,'x','a'),self.row('a','task',1,'x','a')]
        result=analyze.paired(rows,'format','task','error')
        self.assertEqual(result['all_planned_primary_cluster_weighted_bounds'],[0,1])
        self.assertEqual(result['complete_pairs'],0)
