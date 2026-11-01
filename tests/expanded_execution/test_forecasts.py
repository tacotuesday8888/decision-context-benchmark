import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/expanded_execution'))
from forecast_analysis import native_score, paired_forecasts, reliability, draw_weights, design

class ForecastTests(unittest.TestCase):
    def rows(self):
        return [{'id':str(i),'dataset':'bipia-test','gold':i%2,'groups':{'document':str(i//2),'attack_family':str(i//2)}} for i in range(4)]
    def test_tie_is_score_boolean_is_not(self):
        self.assertEqual(native_score({'status':'tie','score':.5}),.5)
        self.assertIsNone(native_score({'status':'ok','prediction':True}))
        self.assertIsNone(native_score({'status':'ok','score':True}))
        self.assertIsNone(native_score({'status':'http_error','score':.9}))
    def test_paired_missing_no_imputation(self):
        rows=self.rows();base={r['id']:{'status':'tie','score':.5} for r in rows}
        other={r['id']:{'status':'ok','score':r['gold']} for r in rows[:3]}
        got=paired_forecasts(rows,base,other)
        self.assertEqual(got['common_score_n'],3)
        self.assertEqual(got['missing_context_n'],1)
        self.assertEqual(got['brier_delta'],-.25)
        self.assertEqual(got['base']['brier'],.25)
        self.assertEqual(got['intervals'][0]['interval'],[-.25,-.25])
    def test_same_cluster_draws_and_no_independent_pair_members(self):
        rows=self.rows();sig=design(rows,'document')
        w,_=draw_weights(sig)
        self.assertTrue((w[:,0]==w[:,1]).all())
        self.assertIs(w,draw_weights(sig)[0])
    def test_one_negative_fixture_no_population_interval(self):
        rows=self.rows()
        for r in rows:r.update(dataset='llmail-test',groups={'fixture':'one','team':r['id']})
        cells={r['id']:{'status':'tie','score':.5} for r in rows}
        got=paired_forecasts(rows,cells,cells)
        self.assertIsNone(got['intervals'][0]['interval'])
    def test_reliability_fixed_bins_and_counts(self):
        rows=self.rows();cells={r['id']:{'status':'ok','score':p} for r,p in zip(rows,[0,.2,.5,1])}
        got=reliability(rows,cells)
        self.assertEqual([x['n'] for x in got['calibration']],[1,1,1,0,1])
        self.assertEqual(got['n'],4)
        self.assertEqual(got['exact_zero_or_one_scores'],2)

    def test_error_contrasts_keep_invalids_separate(self):
        from research_summaries import error_contrast
        rows=self.rows();base={r['id']:{'valid':True,'prediction':r['gold']} for r in rows}
        other={r['id']:{'valid':True,'prediction':r['gold']} for r in rows}
        other['1']={'valid':False,'prediction':None}
        got=error_contrast(rows,base,other,1)
        self.assertEqual(got['eligible_n'],2)
        self.assertEqual(got['common_valid_n'],1)
        self.assertEqual(got['strict_failure_delta'],.5)
        self.assertEqual(got['valid_error_delta'],0)

if __name__=='__main__':unittest.main()
