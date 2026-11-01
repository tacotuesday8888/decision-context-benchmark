"""Tokenization-only coverage checks. Never load a model or run a forward pass."""
from __future__ import annotations
import math
from scripts.study_v7.requests import PANEL, canonical, digest

SOURCES = {
    'jev_firstparty': ['https://docs.typesafe.ai/models'],
    'luna_decisions': ['https://developers.openai.com/api/docs/models/gpt-6-luna'],
    'luna_responses': ['https://developers.openai.com/api/docs/models/gpt-6-luna'],
    'sol_subscription': ['https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations'],
    'sol_responses': ['https://developers.openai.com/api/docs/models/gpt-6.1-sol'],
}


def check(config, request, *, tokenizer=None, native_count=None, allow_server_gate=False):
    p = PANEL[config]
    if request.get('model') != p['model']:
        raise ValueError('Pinned model differs')
    result = {'payload_sha256': digest(canonical(request)), 'request_bytes': len(canonical(request)),
        'context_limit_tokens': p['context_tokens'], 'full_input': True,
        'preflight_native_token_count': False, 'capacity_verified_before_dispatch': False,
        'supported': False, 'coverage_status': 'pending_native_coverage'}
    if config == 'sol_subscription':
        result['output_limit_status'] = p['output_limit_status']
        result['fixed_max_output_supported'] = False
    if config == 'protectai_local':
        if request.get('revision') != p['revision']:
            raise ValueError('Pinned local revision differs')
        if tokenizer is None:
            return result
        ids = tokenizer.encode(request['candidate'], add_special_tokens=False)
        windows = max(1, 1 + math.ceil(max(0, len(ids) - 510) / 446))
        return result | {'preflight_native_token_count': True, 'capacity_verified_before_dispatch': True,
            'supported': True, 'coverage_status': 'complete_windowed', 'candidate_tokens': len(ids),
            'windows': windows, 'window_tokens': 510, 'overlap_tokens': 64,
            'aggregation': p['aggregation'], 'tokenizer_revision': p['revision']}
    if native_count is not None:
        n = native_count.get('input_tokens')
        if (native_count.get('payload_sha256') != result['payload_sha256'] or
            native_count.get('model') != p['model'] or native_count.get('framing_included') is not True or
            not native_count.get('provenance') or type(n) is not int or n <= 0):
            raise ValueError('Native count lacks exact payload/model/framing evidence')
        supported = n + (p.get('output_cap') or 0) <= p['context_tokens'] and not native_count.get('truncated')
        return result | {'preflight_native_token_count': True, 'capacity_verified_before_dispatch': True,
            'supported': supported, 'coverage_status': 'complete' if supported else 'unsupported_over_limit',
            'input_tokens': n, 'token_count_provenance': native_count['provenance']}
    if allow_server_gate:
        return result | {'supported': True, 'coverage_status': 'full_input_server_gate', 'sources': SOURCES[config],
            'limitation': 'No exact native preflight count. Send unchanged full input only after authorization; '
                'native overflow is an unsupported first attempt. No crop, substitution or refill.'}
    return result
