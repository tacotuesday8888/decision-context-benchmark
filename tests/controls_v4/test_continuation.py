import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'scripts/controls_v4'))
from continue_transient import eligible
class ContinuationTests(unittest.TestCase):
    def test_unknown_usage_503_can_continue_without_resending(self):
        r={'status':'failed','accounting_error':'missing_usage','parsed':{'status':'http_error'},'observation':{'http_status':503},'raw_body':'server unavailable'}
        self.assertTrue(eligible(r))
        for body in ('billing','invalid_api_key','insufficient_quota'):
            self.assertFalse(eligible(dict(r,raw_body=body)))
        for status in ('truncated','refusal','invalid_format','model_mismatch'):
            self.assertFalse(eligible(dict(r,parsed={'status':status})))
    def test_accounting_or_identity_failure_not_bypassed(self):
        r={'status':'failed','parsed':{'status':'http_error'},'observation':{'http_status':503}}
        self.assertFalse(eligible(dict(r,accounting_error='cost_exceeds_bound')))
        self.assertFalse(eligible(dict(r,error_type='ValueError')))
