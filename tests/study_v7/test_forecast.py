from decimal import Decimal
import unittest
from scripts.study_v7.token_audit import cost, build_forecast, full_tokenizer
from scripts.study_v7.requests import PANEL, canonical, digest


class ForecastTests(unittest.TestCase):
    def test_saved_tokenizer_truncation_cannot_clip_window_estimates(self):
        from tokenizers import Tokenizer,models,pre_tokenizers
        tokenizer=Tokenizer(models.WordLevel({'[UNK]':0,'word':1},unk_token='[UNK]'))
        tokenizer.pre_tokenizer=pre_tokenizers.Whitespace()
        tokenizer.enable_truncation(max_length=512)
        tokenizer.enable_padding(length=512)
        text=' '.join(['word']*1500)
        self.assertEqual(len(tokenizer.encode(text,add_special_tokens=False).ids),512)
        self.assertEqual(len(full_tokenizer(tokenizer).encode(text,add_special_tokens=False).ids),1500)
        self.assertIsNone(tokenizer.truncation)
        self.assertIsNone(tokenizer.padding)

    def test_request_specific_tiers_output_ceiling_and_cache(self):
        self.assertEqual(cost('jev_firstparty',1000),Decimal('.000042'))
        self.assertEqual(cost('luna_decisions',1000,native_write=True),Decimal('.00025'))
        self.assertEqual(cost('sol_responses',1000,2048),Decimal('.02248'))
        self.assertEqual(cost('sol_responses',300000,2048),Decimal('1.23072'))
        self.assertEqual(cost('luna_decisions',300000,native_write=True),Decimal('.15'))

    def test_aggregate_prices_per_request_and_exact_plan_file_hash(self):
        rows=[]
        for config in PANEL:
            row={'config':config,'source':'browsesafe','condition':'task'}
            row.update({'windows':2} if config=='protectai_local' else {'serialization_proxy_tokens':200000})
            rows.extend([row.copy(),row.copy()])
        plan={'immutable':'test'}
        report=build_forecast(rows,plan,{'openai':'1','typesafe':'2'})
        # Aggregate400k must not trigger a long tier on two200k calls.
        self.assertEqual(Decimal(report['cost_scenarios_usd']['ordinary_proxy']['luna_decisions']),Decimal('.04'))
        self.assertEqual(report['plan_sha256'],digest(canonical(plan)+b'\n'))
        self.assertEqual(report['local_windows'],4)
        self.assertEqual(report['proxy_requests_above_272k']['sol_responses'],0)
        self.assertEqual(report['doubled_proxy_requests_above_272k']['sol_responses'],2)


if __name__=='__main__':
    unittest.main()
