import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/controls_v4'))
try:
 import metrics
 from verify_bootstrap import reference
except ModuleNotFoundError:
 metrics=None
@unittest.skipIf(metrics is None,'Requires numerical runtime')
class BootstrapTests(unittest.TestCase):
    def test_independent_multiplicity_reference_matches(self):
        values=[-1,0,1,1,0,-1,1,0,0,1]
        primary=['a','a','b','b','c','c','d','d','e','e']
        secondary=['u','v','v','w','w','x','x','y','y','u']
        actual=metrics.crossed_interval(values,primary,secondary,draws=100)
        expected,skipped=reference(values,primary,secondary,draws=100)
        self.assertEqual(actual['degenerate_draws'],skipped)
        for a,b in zip(actual['interval'],expected):self.assertAlmostEqual(a,b,places=12)
    def test_too_few_secondary_groups_omits_interval(self):
        actual=metrics.crossed_interval([0]*5,list('abcde'),['same']*5,draws=10)
        self.assertIsNone(actual['interval'])
