import unittest
from decimal import Decimal
from scripts.study_v6.pricing import usage_cost, reserve


class PricingTests(unittest.TestCase):
    def test_cache_counts_are_not_added_twice(self):
        c = usage_cost('openai', {'input_tokens': 1000, 'input_tokens_details':
                                {'cached_tokens': 200, 'cache_write_tokens': 300}})
        self.assertEqual(Decimal(c['accounted_usd']), Decimal('.000127'))
        self.assertEqual(Decimal(c['metered_price_estimate_range_usd'][0]), Decimal('.0000895'))
        self.assertIsNone(c['actual_billed_usd'])

    def test_missing_usage_cannot_release_reservation(self):
        for u in (None, {}, {'input_tokens': True}, {'input_tokens': -1},
                  {'input_tokens': 1, 'input_tokens_details': {'cached_tokens': 2}}):
            self.assertIsNone(usage_cost('openai', u)['accounted_usd'])

    def test_reservation_and_exact_typesafe_rate(self):
        self.assertGreater(Decimal(reserve({'input': 'complete'}, 'openai')), Decimal('.001024'))
        self.assertEqual(usage_cost('typesafe', {'input_tokens': 1000})['accounted_usd'], '0.000042')

    def test_unexpected_long_input_multiplier_is_accounted_and_flagged(self):
        short = usage_cost('openai', {'input_tokens': 272000})
        long = usage_cost('openai', {'input_tokens': 272001})
        self.assertEqual(short['long_input_multiplier'], 1)
        self.assertFalse(short['unexpected_pricing_tier'])
        self.assertEqual(long['long_input_multiplier'], 2)
        self.assertTrue(long['unexpected_pricing_tier'])
        self.assertEqual(Decimal(long['accounted_usd']), Decimal('272001') * Decimal('.50') / 1000000)


if __name__ == '__main__':
    unittest.main()
