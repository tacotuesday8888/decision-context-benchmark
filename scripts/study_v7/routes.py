"""Authorized-only v7 transport; no fallback, retry or truncation; subscription is an explicit profile.

Importing or inspecting this module never creates a client or loads model weights.
Every attempt must have a current owner-bound permit and a durable ledger intent.
"""
from __future__ import annotations
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import time
from scripts.study_v7.requests import PANEL, canonical, digest, AUDIT_SCHEMA
from scripts.study_v6.routes import (_exclusive, probability, _failure, _truncated,
    _valid_count, _stream_events, requires_stop, parse_response as parse_native)

PARSER_VERSION = 'study-v7-routes-2'


def parse_response(config, body, *, audit=False):
    if config in ('jev_firstparty', 'luna_decisions'):
        return parse_native(config, body)
    p = PANEL[config]
    metadata = {}
    try:
        events = list(_stream_events(body))
        if config == 'sol_subscription':
            failure = _subscription_failure(events)
            if failure:
                return _failure(failure)
        terminals = [e['response'] for e in events if e.get('type') in
                     ('response.completed', 'response.incomplete', 'response.failed')]
        if len(terminals) != 1:
            return _failure('interrupted_stream' if not terminals else 'invalid_terminal_events')
        raw = terminals[0]
        metadata = {'usage': raw.get('usage') or {}, 'returned_model': raw.get('model'),
            'provider_request_id': raw.get('id'), 'termination': raw.get('status'),
            'returned_settings': {k: raw.get(k) for k in ('reasoning', 'max_output_tokens',
                'service_tier', 'prompt_cache_options', 'store', 'truncation')}}
        if raw.get('model') != p['model']:
            return _failure('model_mismatch', **metadata)
        expected = {'reasoning': {'effort': p['reasoning']},
            'service_tier': 'default', 'prompt_cache_options': {'mode': 'explicit'}, 'store': False}
        if p.get('output_cap') is not None:
            expected['max_output_tokens'] = p['output_cap']
        else:
            metadata['output_limit_status'] = p['output_limit_status']
            metadata['fixed_max_output_supported'] = False
        mismatches = []
        for name, value in expected.items():
            if raw.get(name) is not None:
                if name == 'reasoning':
                    if raw[name].get('effort') != value['effort']:
                        mismatches.append('reasoning.effort')
                elif name == 'prompt_cache_options':
                    # v7.0.1 technical parser amendment: the provider echoes its
                    # documented 30m default even without cache breakpoints. The
                    # requested mode/bytes remain unchanged; other metadata is
                    # not silently ignored or treated as an equivalent setting.
                    returned = raw[name]
                    if (not isinstance(returned, dict) or set(returned) - {'mode', 'ttl'} or
                            returned.get('mode') != 'explicit' or
                            ('ttl' in returned and returned['ttl'] != '30m')):
                        mismatches.append(name)
                elif raw[name] != value:
                    mismatches.append(name)
        if mismatches:
            return _failure('settings_mismatch', settings_mismatch_fields=mismatches, **metadata)
        usage = metadata['usage']
        if _truncated(raw) or _truncated(usage) or raw.get('truncation') not in (None, 'disabled'):
            return _failure('truncated', truncation_scope='input', **metadata)
        if not _valid_count(usage.get('input_tokens'), 1) or not _valid_count(usage.get('output_tokens')):
            return _failure('missing_usage', **metadata)
        if usage['input_tokens'] + usage['output_tokens'] > p['context_tokens'] or (p.get('output_cap') is not None and usage['output_tokens'] > p['output_cap']):
            return _failure('context_limit_mismatch', **metadata)
        details = usage.get('input_tokens_details') or {}
        if config != 'sol_subscription' and any(details.get(k, 0) != 0 for k in ('cached_tokens', 'cache_write_tokens')):
            return _failure('unexpected_cache_usage', **metadata)
        if raw.get('status') == 'incomplete':
            scope = (raw.get('incomplete_details') or {}).get('reason')
            return _failure('truncated' if scope == 'max_output_tokens' else 'provider_incomplete',
                            truncation_scope='output', **metadata)
        if raw.get('status') != 'completed' or any(e.get('type') == 'error' for e in events):
            return _failure('provider_failed', **metadata)
        content = [c for item in raw.get('output', []) for c in item.get('content', [])]
        if any(c.get('type') == 'refusal' for c in content):
            return _failure('refusal', **metadata)
        text = ''.join(c['text'] for c in content if c.get('type') == 'output_text')
        if not text:
            # Some retained streaming terminal objects omit final content.
            text = ''.join(e['delta'] for e in events if e.get('type') == 'response.output_text.delta')
        try:
            answer = json.loads(text)
        except (ValueError, TypeError):
            return _failure('invalid_format', **metadata)
        if audit:
            valid = isinstance(answer, dict) and set(answer) == set(AUDIT_SCHEMA['required'])
            valid = valid and all(type(answer[k]) is bool for k in ('task_fidelity', 'attack_visible', 'ambiguous'))
            valid = valid and all(isinstance(answer[k], list) and all(isinstance(s, str) for s in answer[k])
                                  for k in ('concerns', 'evidence_spans'))
            return dict(metadata, status='ok', valid=True, prediction=None, audit=answer) if valid else _failure('invalid_format', **metadata)
        if not isinstance(answer, dict) or set(answer) != {'injection'} or type(answer['injection']) is not bool:
            return _failure('invalid_format', **metadata)
        return dict(metadata, status='ok', valid=True, prediction=int(answer['injection']))
    except (ValueError, TypeError, KeyError, AttributeError):
        return _failure('parse_error', **metadata)


def _subscription_failure(value):
    """Recognize subscription quota/access failures without treating them as labels."""
    text = json.dumps(value).lower()
    if 'subscription_sharing_usage_limit_exceeded' in text:
        return 'subscription_quota_exceeded'
    if 'subscription_sharing_usage_unavailable' in text or 'subscription_sharing_unavailable' in text:
        return 'subscription_unavailable'
    return None


def parse_transport(config, observation, body, *, audit=False):
    status, code = observation['http_status'], observation['transport_exit_code']
    if status == 200:
        parsed = parse_response(config, body, audit=audit)
        return _failure('transport_error', usage=parsed.get('usage') or {},
            returned_model=parsed.get('returned_model')) if code else parsed
    if config == 'sol_subscription':
        failure = _subscription_failure(body)
        if failure:
            return _failure(failure)
    if status in (401, 403):
        return _failure('authentication_error')
    if status == 400 and any(s in body.lower() for s in
            ('max_tokens_exceeded', 'context_length_exceeded', 'context length', 'too long', 'context window')):
        return _failure('unsupported_over_limit')
    if config == 'sol_subscription' and status == 400:
        return _failure('subscription_route_unsupported')
    return _failure('transport_error' if code else 'http_error')


def _credential(config, credential_root):
    """Read existing credentials in place; never duplicate them into this checkout."""
    if config == 'sol_subscription':
        return _subscription_credential(credential_root)
    p = Path(credential_root) / '.env.local'
    if p.is_symlink():
        raise ValueError('Credential file cannot be a symlink')
    name = PANEL[config]['credential']
    values = [line.split('=', 1)[1] for line in p.read_text().splitlines() if line.startswith(name + '=')]
    if len(values) != 1 or not values[0] or any(c.isspace() for c in values[0]):
        raise ValueError('Missing or ambiguous credential')
    return values[0]


def _subscription_credential(credential_root):
    """Refresh only the explicitly authorized project OAuth cache, at invocation."""
    import fcntl
    from urllib.parse import urlencode
    from scripts.chatgpt_signin import ISSUER, RESOURCE, private_json, read_json
    path = Path(credential_root) / '.secrets/chatgpt.json'
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('Project OAuth cache cannot be a symlink')
    with (path.parent / 'refresh.lock').open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        data = json.loads(path.read_text())
        saved = datetime.fromisoformat(data['saved_at'].replace('Z', '+00:00')).timestamp()
        scopes = data.get('scopes') or []
        if 'chatgpt.tokens.use.direct' not in scopes:
            raise ValueError('Project subscription direct-use scope missing')
        if datetime.now(timezone.utc).timestamp() > saved + data.get('expires_in', 0) - 120:
            if not data.get('refresh_token'):
                raise ValueError('Project OAuth sign-in requires owner attention')
            fresh = read_json(ISSUER + '/api/accounts/oauth/token', body=urlencode({
                'grant_type': 'refresh_token', 'client_id': data['client_id'],
                'refresh_token': data['refresh_token'], 'resource': RESOURCE}).encode())
            scopes = fresh.get('scope', ' '.join(scopes)).split()
            if 'chatgpt.tokens.use.direct' not in scopes:
                raise ValueError('Refreshed project subscription scope missing')
            for key in ('access_token', 'refresh_token', 'id_token', 'expires_in', 'token_type'):
                if key in fresh:
                    data[key] = fresh[key]
            data['scopes'] = scopes
            data['saved_at'] = datetime.now(timezone.utc).isoformat()
            private_json(path, data)
        token = data['access_token']
        if not isinstance(token, str) or not token or any(c.isspace() for c in token):
            raise ValueError('Invalid project OAuth token')
        return token


def _post(config, request, token, directory):
    """One curl call, durable partial bytes, no retry/redirect/long-context header."""
    p = PANEL[config]
    if p['route'] not in ('api_key', 'subscription') or any(c in token for c in '\r\n'):
        raise ValueError('Invalid API route or credential')
    partial, headers = directory / 'response.partial', directory / 'response-headers.partial'
    options = ['url = ' + json.dumps(p['endpoint']), 'request = "POST"',
        'header = "Content-Type: application/json"', 'header = ' + json.dumps('Authorization: Bearer ' + token),
        'data-binary = ' + json.dumps('@' + str(directory / 'request.json')),
        'output = ' + json.dumps(str(partial)), 'dump-header = ' + json.dumps(str(headers)),
        'write-out = "%{http_code}"', 'silent', 'show-error', 'no-buffer',
        'connect-timeout = 10', 'max-time = 60']
    start = time.perf_counter()
    try:
        completed = subprocess.run(['/usr/bin/curl', '--disable', '--config', '-'],
            input='\n'.join(options) + '\n', text=True, capture_output=True, timeout=65, check=False)
        status = int(completed.stdout) if completed.stdout.isdigit() else 0
        code = completed.returncode
    except subprocess.TimeoutExpired:
        status, code = 0, 124
    safe_headers = {}
    if headers.exists():
        for line in headers.read_text(errors='replace').splitlines():
            if ':' in line:
                key, value = line.split(':', 1)
                if key.lower() in ('x-request-id', 'request-id', 'retry-after', 'x-tokens-remaining',
                    'x-ratelimit-remaining-requests', 'x-ratelimit-remaining-tokens'):
                    safe_headers[key.lower()] = value.strip().replace(token, '[redacted]')
    body = partial.read_text(errors='replace') if partial.exists() else ''
    body = body.replace(token, '[redacted]')
    for path in (partial, headers):
        if path.exists() and token.encode() in path.read_bytes():
            path.write_bytes(path.read_bytes().replace(token.encode(), b'[redacted]'))
    _exclusive(directory / 'response.raw', body.encode())
    return {'http_status': status, 'transport_exit_code': code, 'response_headers': safe_headers,
            'elapsed_seconds': time.perf_counter()-start}, body


class _LocalRuntime:
    def __init__(self):
        # Called only by invoke after a valid owner permit and durable intent.
        import torch
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        p = PANEL['protectai_local']
        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(p['model'], revision=p['revision'], trust_remote_code=False, local_files_only=True)
        self.model = AutoModelForSequenceClassification.from_pretrained(p['model'], revision=p['revision'],
            trust_remote_code=False, local_files_only=True, use_safetensors=True).cpu().eval()
        if self.model.config.id2label.get(1) != 'INJECTION':
            raise ValueError('Unexpected specialist label mapping')
        torch.set_num_threads(2)

    def classify(self, text):
        ids = self.tokenizer.encode(text, add_special_tokens=False, truncation=False, padding=False)
        scores = []
        for start in range(0, max(1, len(ids)), 446):
            chunk = ids[start:start+510]
            encoded = self.tokenizer.prepare_for_model(chunk, add_special_tokens=True,
                return_tensors='pt', return_token_type_ids=False)
            encoded = {k: v.unsqueeze(0) if v.ndim == 1 else v for k, v in encoded.items()}
            if encoded['input_ids'].shape[1] > 512:
                raise ValueError('Specialist window exceeds native capacity')
            with self.torch.inference_mode():
                scores.append(float(self.model(**encoded).logits.softmax(-1)[0, 1]))
            if start + 510 >= len(ids):
                break
        return {'score': max(scores), 'window_scores': scores, 'windows': len(scores), 'input_tokens': len(ids),
            'returned_model': PANEL['protectai_local']['model'], 'revision': PANEL['protectai_local']['revision']}


def invoke(config, request, raw_directory, attempt_key, *, permit=None, request_record=None, runtime_cache=None):
    """One exclusive transport attempt; default denies before credentials/weights."""
    if permit is None or request_record is None:
        raise PermissionError('Experimental inference remains paused: a bounded owner authorization is required')
    permit.check_dispatch(request_record, request)
    if config == 'sol_responses' and (permit.execution_profile == 'cheap-api-sol-subscription' or
            getattr(permit, 'receipt', {}).get('allow_paid_sol_api') is False):
        raise PermissionError('Paid Sol API is forbidden by the active owner profile')
    if attempt_key != request_record['key'] or config != request_record['config']:
        raise ValueError('Attempt identity differs from frozen manifest')
    directory = Path(raw_directory) / attempt_key
    directory.mkdir(parents=True, exist_ok=False)
    _exclusive(directory / 'request.json', canonical(request))
    _exclusive(directory / 'started.json', {'key': attempt_key, 'config': config,
        'namespace': request_record['namespace'], 'payload_sha256': digest(canonical(request)),
        'route': PANEL[config]['route'], 'started_at': datetime.now(timezone.utc).isoformat()})
    observation, sent = {}, False
    start = time.perf_counter()
    try:
        if config == 'protectai_local':
            cache = runtime_cache if runtime_cache is not None else {}
            if config not in cache:
                cache[config] = _LocalRuntime()
            sent = True
            raw = cache[config].classify(request['candidate'])
            _exclusive(directory / 'response.raw', canonical(raw))
            parsed = dict(raw, **probability(raw['score']))
        else:
            token = _credential(config, permit.credential_root)
            sent = True
            observation, body = _post(config, request, token, directory)
            parsed = parse_transport(config, observation, body, audit=request_record['condition'] == 'audit')
        result = {'parsed': parsed, 'observation': observation, 'stop_required': requires_stop(parsed)}
    except Exception as error:
        result = {'parsed': _failure('runtime_error'), 'observation': observation,
                  'stop_required': True, 'error_type': type(error).__name__}
    result.update(parser_version=PARSER_VERSION, access_route=PANEL[config]['route'],
        paid_request=PANEL[config]['route'] == 'api_key', native_request_sent=sent,
        request_sha256=digest(canonical(request)), namespace=request_record['namespace'],
        first_attempt_primary=request_record['namespace'] == 'first',
        elapsed_seconds=time.perf_counter()-start,
        finished_at=datetime.now(timezone.utc).isoformat(),
        raw_hashes={p.name: digest(p.read_bytes()) for p in sorted(directory.iterdir()) if p.is_file()})
    _exclusive(directory / 'completed.json', result)
    return result
