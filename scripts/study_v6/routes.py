"""V6 native routes: fixed contracts, full input, durable first attempts, no retries.

This module does not dispatch on import. The coordinator owns admission, freezing,
reservations and resumption. ``invoke`` must only be called after those gates.
Server-gated coverage is explicitly different from a tokenizer preflight: accepted
responses and input accounting must still be checked, and overflow is unsupported.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import importlib
import json
import math
import os
from decimal import Decimal
from pathlib import Path
import re
import subprocess
import sys
import time

from scripts.study_v5.prompts import native_payload
from scripts.response_metadata import terminal_metadata

ROOT = Path(__file__).resolve().parents[2]
PANEL = {
    'jev_firstparty': {'model': 'jev-1.14.0', 'kind': 'noul', 'context_tokens': 32000,
        'endpoint': 'https://api.typesafe.ai/v1/systemone', 'credential': 'TYPESAFE_API_KEY'},
    'luna_decisions': {'model': 'gpt-6-luna', 'kind': 'predicate', 'context_tokens': 1050000,
        'endpoint': 'https://api.openai.com/v1/decisions', 'credential': 'OPENAI_API_KEY'},
    'luna_chat': {'model': 'gpt-6-luna', 'kind': 'chat', 'context_tokens': 1050000,
        'endpoint': 'https://api.openai.com/v1/responses', 'output_cap': 256},
    'astra_chat': {'model': 'gpt-6-astra', 'kind': 'chat', 'context_tokens': 1050000,
        'endpoint': 'https://api.openai.com/v1/responses', 'output_cap': 2048},
    'laya_local': {'model': 'convaiinnovations/laya-multilingual', 'kind': 'local_decision',
        'revision': '1720e3e3357cfe1e281542e223f8273b0890ca34', 'context_tokens': 8192,
        'sdk': '0.4.17', 'head_max_len': 256},
    'nimble_local': {'model': 'nimble:9b-q4_K_M', 'kind': 'local_decision',
        'revision': 'd99f22c363cea449151cc473887de081b98ca98e8a29b1a8710e09da916f2c79',
        'runtime': '0.40.13', 'context_tokens': 8194,
        'endpoint': 'http://127.0.0.1:11434/v1/systemone'},
    'protectai_local': {'model': 'protectai/deberta-v3-base-prompt-injection-v2',
        'revision': '90c9989b1a342275dd0d1a95aad283c04e075671', 'kind': 'local_detector',
        'context_tokens': 512, 'window_tokens': 510, 'overlap_tokens': 64,
        'aggregation': 'maximum P(INJECTION) over candidate-only windows'},
}
ROUTES = {config: ('local' if config.endswith('_local') else
    'subscription' if config.endswith('_chat') else 'api_key') for config in PANEL}
SERVER_COVERAGE_SOURCES = {
    'jev_firstparty': ['https://docs.typesafe.ai/models', 'https://docs.typesafe.ai/api/errors'],
    'luna_decisions': ['https://developers.openai.com/api/reference/resources/decisions/methods/create',
        'https://developers.openai.com/api/docs/models/gpt-6-luna'],
    'luna_chat': ['https://developers.openai.com/api/reference/resources/responses/methods/create'],
    'astra_chat': ['https://developers.openai.com/api/reference/resources/responses/methods/create'],
    'nimble_local': ['https://huggingface.co/bespokelabs/Bespoke-Nimble-9B',
        'docs/controls-v4/MODEL-ROUTES.md', 'scripts/controls_v4/nimble_runtime.py'],
}


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def payload(config, row, condition):
    if config != 'protectai_local':
        return native_payload(row, condition, config)
    if (condition != 'candidate' or row['setting'] != 'indirect_tool_content' or
            row['source'] not in ('browsesafe', 'nvidia', 'aib', 'infuse')):
        raise ValueError('ProtectAI is candidate-only and restricted to indirect injection')
    p = PANEL[config]
    return {k: p[k] for k in ('model', 'revision', 'window_tokens', 'overlap_tokens', 'aggregation')} | {
        'candidate': row['candidate']}


def _valid_count(value, minimum=0):
    return isinstance(value, int) and not isinstance(value, bool) and value >= minimum


def _failure(status, **metadata):
    return dict(metadata, status=status, valid=False, prediction=None)


def probability(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError('Invalid native score')
    return {'status': 'tie' if value == .5 else 'ok', 'valid': value != .5,
        'prediction': None if value == .5 else int(value > .5), 'score': value}


def _truncated(value):
    return bool(value.get('truncated') or value.get('input_truncated') or
        value.get('state_tokens_dropped', 0))


def requires_stop(parsed):
    """Separate retained case behavior from violations of the execution contract.

    A refusal, unusable answer or exhausted output allowance is missing outcome
    evidence, not a reason to select a different cohort. Missing native usage is
    still systemic: preserve the case disposition and retain its reservation.
    """
    status = parsed.get('status')
    if status in ('ok', 'tie', 'unsupported_over_limit'):
        return False
    case_failure = status in ('refusal', 'invalid_format', 'provider_incomplete') or (
        status == 'truncated' and parsed.get('truncation_scope') == 'output')
    if case_failure:
        usage = parsed.get('usage') or {}
        return not isinstance(usage, dict) or not _valid_count(usage.get('input_tokens'), minimum=1)
    return True


def _stream_events(body):
    for event in body.replace('\r\n', '\n').split('\n\n'):
        data = '\n'.join(line[5:].lstrip(' ') for line in event.splitlines() if line.startswith('data:'))
        if data and data != '[DONE]':
            value = json.loads(data)
            if not isinstance(value, dict):
                raise ValueError('Malformed SSE event')
            yield value


def parse_response(config, body):
    """Retain usage on format/refusal failures; never invent chat probabilities."""
    p = PANEL[config]
    metadata = {}
    try:
        if p['kind'] == 'chat':
            metadata = terminal_metadata('openai', body)
            events = list(_stream_events(body))
            if any(event.get('type') == 'error' for event in events):
                return _failure('provider_failed', **metadata)
            terminals = [e['response'] for e in events if e.get('type') in
                ('response.completed', 'response.incomplete', 'response.failed')]
            if len(terminals) != 1:
                return _failure('interrupted_stream' if not terminals else 'invalid_terminal_events', **metadata)
            response = terminals[0]
            if response.get('model') != p['model']:
                return _failure('model_mismatch', **metadata)
            settings_mismatches = []
            expected_effort = 'none' if config == 'luna_chat' else 'low'
            returned_effort = (response.get('reasoning') or {}).get('effort')
            if returned_effort is not None and returned_effort != expected_effort:
                settings_mismatches.append('reasoning.effort')
            if response.get('max_output_tokens') is not None and response['max_output_tokens'] != p['output_cap']:
                settings_mismatches.append('max_output_tokens')
            if response.get('service_tier') not in (None, 'default'):
                settings_mismatches.append('service_tier')
            if settings_mismatches:
                return _failure('settings_mismatch', settings_mismatch_fields=settings_mismatches, **metadata)
            # Input integrity takes precedence even if the output also exhausted
            # its allowance: a full-input gate violation must stop the route.
            if response.get('truncation') not in (None, 'disabled') or _truncated(response.get('usage') or {}):
                return _failure('truncated', truncation_scope='input', **metadata)
            if metadata.get('termination') == 'incomplete':
                reason = (metadata.get('incomplete_details') or {}).get('reason')
                if reason == 'max_output_tokens':
                    return _failure('truncated', truncation_scope='output', **metadata)
                return _failure('provider_incomplete', **metadata)
            if metadata.get('termination') != 'completed':
                return _failure('provider_failed', **metadata)
            if any(c.get('type') == 'refusal' for item in response.get('output', []) for c in item.get('content', [])):
                return _failure('refusal', **metadata)
            # Reuse the established SSE assembly, including terminal output fallback.
            sys.path.insert(0, str(ROOT / 'scripts'))
            from smoke_access import parse_openai_stream
            text = parse_openai_stream(body)['stream_output_text']
            try:
                answer = json.loads(text)
            except (ValueError, TypeError):
                return _failure('invalid_format', **metadata)
            if not isinstance(answer, dict) or set(answer) != {'injection'} or not isinstance(answer['injection'], bool):
                return _failure('invalid_format', **metadata)
            result = dict(metadata, status='ok', valid=True, prediction=int(answer['injection']))
        else:
            raw = json.loads(body) if isinstance(body, str) else body
            if not isinstance(raw, dict):
                raise ValueError('Response object required')
            metadata = {'usage': raw.get('usage') or {}, 'returned_model': raw.get('model')}
            expected = 'laya-rl-agent' if config == 'laya_local' else p['model']
            if raw.get('model') != expected:
                return _failure('model_mismatch', **metadata)
            if _truncated(raw) or _truncated(metadata['usage']):
                return _failure('truncated', truncation_scope='input', **metadata)
            answers = raw['answers']
            if p['kind'] == 'predicate':
                if not isinstance(answers, list) or len(answers) != 1 or answers[0].get('name') != 'injection':
                    raise ValueError('Exact single decision required')
                answer = answers[0]
                if answer.get('type') == 'refusal':
                    return _failure('refusal', **metadata)
                if answer.get('type') != 'predicate':
                    raise ValueError('Predicate required')
                score = answer['probability']
            else:
                if not isinstance(answers, dict) or set(answers) != {'injection'} or answers['injection'].get('type') != 'noul':
                    raise ValueError('Exact single noul required')
                answer = answers['injection']
                score = answer['noul']
            result = dict(metadata, **probability(score))
            if 'confidence' in answer:
                confidence = answer['confidence']
                if (isinstance(confidence, (float, int)) and not isinstance(confidence, bool)
                        and math.isfinite(confidence) and 0 <= confidence <= 1):
                    result['native_confidence'] = confidence
                else:
                    result['native_confidence_status'] = 'invalid_optional_field'
        usage = result.get('usage') or {}
        if not _valid_count(usage.get('input_tokens'), minimum=1):
            return _failure('missing_usage', **metadata)
        if usage['input_tokens'] > p['context_tokens']:
            return _failure('context_limit_mismatch', **metadata)
        return result
    except (ValueError, TypeError, KeyError, IndexError, AttributeError):
        return _failure('parse_error', **metadata)


def coverage(config, request, *, laya_audit=None, native_count=None, tokenizer=None, allow_server_gate=False):
    """No cropping. Token evidence must bind the exact payload and include framing.

    Server-gated admission requires an explicit caller choice frozen in the plan.
    It permits an intact first attempt, not a claim of verified native token count.
    Overflow/errors remain unsupported and never become classifier predictions.
    """
    p = PANEL[config]
    if request.get('model') != p['model']:
        raise ValueError('Pinned request model changed')
    result = {'payload_sha256': digest(canonical(request)), 'request_bytes': len(canonical(request)),
        'context_limit_tokens': p['context_tokens'], 'preflight_native_token_count': False,
        'supported': False, 'coverage_status': 'pending_native_coverage', 'full_input': True}
    if config == 'laya_local':
        if laya_audit is None:
            return result
        if laya_audit['payload_sha256'] != result['payload_sha256']:
            raise ValueError('Cached Laya audit belongs to another payload')
        result.update({k: laya_audit[k] for k in ('state_tokens', 'head_tokens', 'truncated') if k in laya_audit})
        result.update(preflight_native_token_count=True, supported=not laya_audit['truncated'],
            coverage_status='unsupported_over_limit' if laya_audit['truncated'] else 'complete')
        return result
    if config == 'protectai_local':
        if request.get('revision') != p['revision']:
            raise ValueError('Specialist revision changed')
        if tokenizer is None:
            return result
        ids = tokenizer.encode(request['candidate'], add_special_tokens=False)
        windows = max(1, 1 + math.ceil(max(0, len(ids)-p['window_tokens']) /
            (p['window_tokens']-p['overlap_tokens'])))
        result.update(preflight_native_token_count=True, supported=True, coverage_status='complete_windowed',
            candidate_tokens=len(ids), windows=windows, native_window_tokens=512,
            interpretation='Every candidate token is covered; maximum score over native windows')
        return result
    if native_count is not None:
        if (native_count.get('payload_sha256') != result['payload_sha256'] or
            native_count.get('model') != p['model'] or native_count.get('framing_included') is not True or
            not native_count.get('provenance') or not _valid_count(native_count.get('input_tokens'), 1)):
            raise ValueError('Native token count lacks exact request/provenance binding')
        count = native_count['input_tokens']
        supported = count + p.get('output_cap', 0) <= p['context_tokens'] and not _truncated(native_count)
        result.update(preflight_native_token_count=True, supported=supported,
            coverage_status='complete' if supported else 'unsupported_over_limit', input_tokens=count,
            token_count_provenance=native_count['provenance'])
    elif allow_server_gate and config in SERVER_COVERAGE_SOURCES:
        result.update(supported=True, coverage_status='full_input_server_gate',
            capacity_verified_before_dispatch=False, sources=SERVER_COVERAGE_SOURCES[config],
            limitation='No native preflight count. Full unchanged request; require native acceptance, '
                'valid usage, no truncation and matching model. Capacity failures are unsupported first attempts.')
    return result


def metered_cost(config, parsed):
    """Price retained native usage; keep conservative accounting separate from bills.

    The shared pricing module owns rates and cache-count-aware bounds. These are
    usage-derived estimates, not a provider balance or an asserted invoice.
    Frozen prices and premiums must be verified by the coordinator before use.
    """
    usage = parsed.get('usage') or {}
    result = {'usage': usage, 'conservative_usage_cost_usd': None,
        'exact_usage_cost_usd': None, 'uncached_base_usage_cost_usd': None}
    if ROUTES[config] in ('local', 'subscription'):
        return result | {'conservative_usage_cost_usd': 0.0, 'exact_usage_cost_usd': 0.0,
            'accounting_basis': 'zero incremental metered API charge on frozen route'}
    if not _valid_count(usage.get('input_tokens'), minimum=1):
        return result | {'accounting_basis': 'unknown usage; retain full reservation'}
    from scripts.study_v6.pricing import usage_cost
    provider = 'typesafe' if config == 'jev_firstparty' else 'openai'
    cost = usage_cost(provider, usage)
    upper = cost.get('accounted_usd')
    result.update(conservative_usage_cost_usd=float(upper) if upper is not None else None,
        actual_billed_usd=cost.get('actual_billed_usd'), accounting_basis=cost.get('basis'),
        metered_price_estimate_range_usd=cost.get('metered_price_estimate_range_usd'))
    n = Decimal(usage['input_tokens']) / Decimal(1000000)
    if config == 'jev_firstparty':
        exact = float(cost['metered_price_estimate_usd']) if cost.get('metered_price_estimate_usd') is not None else None
        return result | {'exact_usage_cost_usd': exact, 'uncached_base_usage_cost_usd': exact}
    return result | {'uncached_base_usage_cost_usd': float(n * Decimal('0.10')),
        'base_rate_interpretation': 'Nominal comparison, not an invoice or lower bound'}


def _exclusive(path, value):
    data = value if isinstance(value, bytes) else canonical(value) + b'\n'
    with Path(path).open('xb') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())
    # Sync the directory entry as well as file contents before dispatch/resumption.
    descriptor = os.open(str(Path(path).parent), os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _credential(config):
    sys.path.insert(0, str(ROOT / 'scripts'))
    if ROUTES[config] == 'api_key':
        from smoke_access import env_secret
        return env_secret(PANEL[config]['credential'])
    if ROUTES[config] == 'subscription':
        from provider_access import subscription_credentials
        return subscription_credentials()['access_token']
    return None


def _post(config, request, token, directory):
    """Established curl transport with a durable output path instead of tempfile.

    Authorization is supplied via stdin. Curl makes exactly one request, does not
    follow redirects, and writes each received byte immediately into ignored raw
    evidence, so interruption cannot erase an already received partial stream.
    """
    url = PANEL[config]['endpoint']
    if url not in {p.get('endpoint') for p in PANEL.values()}:
        raise ValueError('Unapproved endpoint')
    if token and any(c in token for c in '\r\n'):
        raise ValueError('Invalid credential')
    partial, headers = directory / 'response.partial', directory / 'response-headers.partial'
    max_time = 300 if config == 'nimble_local' else 60
    settings = ['url = ' + json.dumps(url), 'request = "POST"', 'header = "Content-Type: application/json"',
        'data-binary = ' + json.dumps('@' + str(directory / 'request.json')),
        'output = ' + json.dumps(str(partial)), 'dump-header = ' + json.dumps(str(headers)),
        'write-out = "%{http_code}"', 'silent', 'show-error', 'no-buffer',
        'connect-timeout = 10', 'max-time = ' + str(max_time)]
    if token:
        settings.append('header = ' + json.dumps('Authorization: Bearer ' + token))
    if config == 'nimble_local':
        settings.append('noproxy = "*"')
    start = time.perf_counter()
    try:
        # Disable ~/.curlrc first: a user default must not introduce redirects,
        # retries, an extra header, or a changed inference route into this freeze.
        completed = subprocess.run(['/usr/bin/curl', '--disable', '--config', '-'], input='\n'.join(settings)+'\n',
            text=True, capture_output=True, timeout=max_time+5, check=False)
        status = int(completed.stdout) if completed.stdout.isdigit() else 0
        code = completed.returncode
    except subprocess.TimeoutExpired:
        status, code = 0, 124
    safe_headers = {}
    if headers.exists():
        for line in headers.read_text(errors='replace').splitlines():
            if ':' in line:
                name, value = line.split(':', 1)
                if name.lower() in ('retry-after', 'x-request-id', 'request-id', 'x-tokens-remaining'):
                    safe_headers[name.lower()] = value.strip()
    body = partial.read_text(errors='replace') if partial.exists() else ''
    # Credentials never enter normalized records. A provider unexpectedly echoing
    # its bearer value is recorded as redacted evidence rather than a secret.
    if token:
        body = body.replace(token, '[redacted]')
        safe_headers = {k: v.replace(token, '[redacted]') for k, v in safe_headers.items()}
        for path in (partial, headers):
            if path.exists() and token.encode() in path.read_bytes():
                path.write_bytes(path.read_bytes().replace(token.encode(), b'[redacted]'))
    _exclusive(directory / 'response.raw', body.encode())
    return {'http_status': status, 'transport_exit_code': code,
        'elapsed_seconds': round(time.perf_counter()-start, 4), 'response_headers': safe_headers}, body


def make_runtime(config):
    """Root executor only: loading a local model is explicit, never an import effect."""
    if config == 'laya_local':
        return importlib.import_module('scripts.laya_v2.adapter').LocalDecision()
    if config == 'protectai_local':
        sys.path.insert(0, str(ROOT / 'scripts/expanded_v2'))
        return importlib.import_module('scripts.expanded_v2.adapters').LocalDetector()
    if config == 'nimble_local':
        runtime = importlib.import_module('scripts.controls_v4.nimble_runtime')
        runtime.verify_model()
        return runtime
    return None


def invoke(config, request, raw_directory, attempt_key, *, runtime=None):
    """One first attempt, with exclusive artifacts. Reusing a key always refuses.

    Returned ``stop_required`` is operational only; no reference labels are read.
    Usage is retained separately for the frozen accounting policy to price. There
    is no paid Responses route, automatic retry, model substitution or fallback.
    """
    if not re.fullmatch(r'[A-Za-z0-9_.:-]+', attempt_key):
        raise ValueError('Invalid attempt key')
    if request.get('model') != PANEL[config]['model']:
        raise ValueError('Pinned request model changed')
    directory = Path(raw_directory) / attempt_key
    directory.mkdir(parents=True, exist_ok=False)
    _exclusive(directory / 'request.json', canonical(request))
    _exclusive(directory / 'started.json', {'config': config, 'attempt_key': attempt_key,
        'payload_sha256': digest(canonical(request)), 'route': ROUTES[config],
        'started_at': datetime.now(timezone.utc).isoformat()})
    observation, parsed, audit = {}, None, None
    start = time.perf_counter()
    try:
        if config == 'laya_local':
            if runtime is None:
                raise ValueError('Explicit initialized local runtime required')
            raw, parsed, audit = runtime.predict(request)
            _exclusive(directory / 'response.raw', canonical(raw))
            parsed = parse_response(config, raw)
        elif config == 'protectai_local':
            if runtime is None or request.get('revision') != PANEL[config]['revision']:
                raise ValueError('Explicit pinned specialist runtime required')
            raw = runtime.classify(request['candidate'])
            _exclusive(directory / 'response.raw', canonical(raw))
            if raw.get('returned_model') != PANEL[config]['model'] or raw.get('revision') != PANEL[config]['revision']:
                parsed = _failure('model_mismatch')
            else:
                parsed = dict(raw, **probability(raw['score']))
        else:
            if config == 'nimble_local' and runtime is None:
                raise ValueError('Verified native Nimble runtime required')
            observation, body = _post(config, request, _credential(config), directory)
            if observation['http_status'] == 200:
                parsed = parse_response(config, body)
                if observation['transport_exit_code'] and parsed['status'] != 'model_mismatch':
                    parsed = _failure('transport_error', usage=parsed.get('usage') or {},
                        returned_model=parsed.get('returned_model'))
            elif observation['http_status'] in (401, 403):
                parsed = _failure('authentication_error')
            elif observation['http_status'] == 400 and any(s in body.lower() for s in
                    ('max_tokens_exceeded', 'context_length_exceeded', 'context length', 'too long', 'context window')):
                parsed = _failure('unsupported_over_limit')
            else:
                parsed = _failure('transport_error' if observation['transport_exit_code'] else 'http_error')
        result = {'parsed': parsed, 'observation': observation, 'token_audit': audit,
            'elapsed_seconds': round(time.perf_counter()-start, 4), 'access_route': ROUTES[config],
            'paid_request': ROUTES[config] == 'api_key', 'attempt_key': attempt_key,
            'request_sha256': digest(canonical(request)),
            'stop_required': requires_stop(parsed),
            'raw_directory': str(directory)}
    except Exception as error:
        result = {'parsed': _failure('runtime_error'), 'error_type': type(error).__name__,
            'observation': observation, 'attempt_key': attempt_key, 'stop_required': True,
            'access_route': ROUTES[config], 'paid_request': ROUTES[config] == 'api_key',
            'request_sha256': digest(canonical(request)), 'raw_directory': str(directory),
            'elapsed_seconds': round(time.perf_counter()-start, 4)}
    result['raw_hashes'] = {path.name: digest(path.read_bytes()) for path in sorted(directory.iterdir()) if path.is_file()}
    _exclusive(directory / 'completed.json', result)
    return result
