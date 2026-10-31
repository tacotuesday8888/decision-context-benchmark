"""Frozen paid-route accounting, separate from outcomes and tokenizer coverage."""
from decimal import Decimal
import json

BASE_RATES = {'openai': Decimal('0.10'), 'typesafe': Decimal('0.042')}
# Decisions can charge 12h cache writes at 2.5x the base input rate. No discount,
# regional endpoint, long-context tier or faster processing tier is assumed.
RESERVATION_RATES = {'openai': Decimal('0.25'), 'typesafe': Decimal('0.084')}


def reserve(payload, provider):
    """Preserved byte+4096 planning proxy, NOT a certified tokenizer upper bound."""
    size = len(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode())
    return format((Decimal(size + 4096) * RESERVATION_RATES[provider] / Decimal(1000000)), 'f')


def usage_cost(provider, usage):
    """Conservative usage upper and invoice-independent lower; unknown stays held."""
    if not isinstance(usage, dict):
        return {'accounted_usd': None, 'actual_billed_usd': None}
    n = usage.get('input_tokens')
    if type(n) is not int or n < 0:
        return {'accounted_usd': None, 'actual_billed_usd': None}
    if provider == 'typesafe':
        cost = Decimal(n) * BASE_RATES[provider] / Decimal(1000000)
        return {'accounted_usd': format(cost, 'f'), 'metered_price_estimate_usd': format(cost, 'f'),
                'actual_billed_usd': None, 'basis': 'returned input usage at frozen base rate; output free'}
    if provider != 'openai':
        raise ValueError('Unknown paid provider')
    details = usage.get('input_tokens_details') or {}
    reads, writes = details.get('cached_tokens', 0), details.get('cache_write_tokens', 0)
    if any(type(x) is not int or x < 0 for x in (reads, writes)) or reads + writes > n:
        return {'accounted_usd': None, 'actual_billed_usd': None, 'basis': 'invalid cache usage'}
    # Missing cache detail cannot be treated as proof that no writes occurred.
    if 'cached_tokens' in details and 'cache_write_tokens' in details:
        uncached = n - reads - writes
        lower = (Decimal(uncached) * Decimal('.10') + Decimal(reads) * Decimal('.01')
                 + Decimal(writes) * Decimal('.125')) / Decimal(1000000)
        upper = (Decimal(uncached) * Decimal('.10') + Decimal(reads) * Decimal('.01')
                 + Decimal(writes) * Decimal('.25')) / Decimal(1000000)
    else:
        lower, upper = Decimal(n) * Decimal('.01') / Decimal(1000000), Decimal(n) * Decimal('.25') / Decimal(1000000)
    return {'accounted_usd': format(upper, 'f'), 'metered_price_estimate_range_usd': [format(lower, 'f'), format(upper, 'f')],
            'actual_billed_usd': None, 'basis': 'cache counts inclusive in input; conservative 12h write upper; output free'}
