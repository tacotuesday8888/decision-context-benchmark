"""Single-attempt transport for the separately frozen subscription follow-up.

No client, credentials, model weights or network request are created on import.
Only an owner-bound executor permit with a durable dispatch intent can invoke it.
"""
from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import time

from scripts.study_v7.requests import canonical, digest
from scripts.study_v7.routes import _credential, _post, parse_transport as parse_classification
from scripts.study_v6.routes import _stream_events, _truncated
from scripts.subscription_followup.budget import route_for, validate_route

VERSION = 'subscription-followup-transport-1'
SOL_CONTEXT = 500000


def write_once(path, value):
    path = Path(path)
    data = value if isinstance(value, bytes) else canonical(value)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('xb') as stream:
        stream.write(data)
        stream.flush()
        __import__('os').fsync(stream.fileno())


def validate_payload(config, payload):
    route = route_for(config)
    validate_route(config, route=route['route'], credential_source=route['credential_source'],
                   endpoint=route['endpoint'])
    if payload.get('model') != route['model']:
        raise PermissionError('Frozen model differs')
    if config == 'sol_subscription':
        required = {'model', 'instructions', 'input', 'store', 'stream', 'service_tier', 'reasoning', 'text'}
        if set(payload) != required or payload['store'] is not False or payload['stream'] is not True:
            raise PermissionError('Only complete stateless structured subscription requests are allowed')
        if payload['service_tier'] != 'default' or payload['reasoning'] != {'effort': 'low'}:
            raise PermissionError('The classifier/actor uses frozen low reasoning and default tier')
        if not isinstance(payload['input'], list) or not payload['input']:
            raise PermissionError('Complete input array required')
        fmt = payload.get('text', {}).get('format', {})
        if fmt.get('type') != 'json_schema' or fmt.get('strict') is not True:
            raise PermissionError('Strict predeclared schema required')
        if any(i.get('role') not in ('user', 'developer') for i in payload['input']):
            raise PermissionError('Unsupported subscription input role')
    elif config == 'jev_firstparty':
        if set(payload) != {'model', 'state', 'questions'} or len(payload['questions']) != 1:
            raise PermissionError('One default-context native Jev question required')
    else:
        raise PermissionError('No other route or billing fallback exists')
    return route


def _validate_schema(value, schema):
    """Small strict output validator for this frozen Boolean/string/action subset."""
    kind = schema.get('type')
    if kind == 'object':
        if not isinstance(value, dict) or set(value) != set(schema.get('required', [])):
            return False
        return all(k in schema.get('properties', {}) and _validate_schema(v, schema['properties'][k])
                   for k, v in value.items())
    if kind == 'boolean':
        return type(value) is bool
    if kind == 'string':
        return isinstance(value, str) and ('enum' not in schema or value in schema['enum'])
    if kind == 'array':
        return isinstance(value, list) and all(_validate_schema(v, schema['items']) for v in value)
    if kind == 'integer':
        return type(value) is int
    return False


def parse_structured(body, payload, observation):
    """Preserve terminal failures separately; never turn a partial answer into success."""
    status = observation.get('http_status', 0)
    transport_exit = observation.get('transport_exit_code', 0)
    try:
        error_body = json.loads(body)
    except (ValueError, TypeError):
        error_body = {}
    error = error_body.get('error', {}) if isinstance(error_body, dict) else {}
    base = {'valid': False, 'status': 'http_error', 'prediction': None,
            'http_status': status, 'error_code': error.get('code'), 'error_type': error.get('type'),
            'error_param': error.get('param'), 'usage': {}}
    if status != 200:
        if transport_exit:
            base['status'] = 'transport_error'
        return base
    try:
        events = list(_stream_events(body))
        terminal = [e for e in events if e.get('type') in
                    ('response.completed', 'response.incomplete', 'response.failed')]
        if len(terminal) != 1:
            return dict(base, status='interrupted_stream' if not terminal else 'invalid_terminal_events')
        final = terminal[0].get('response', {})
        err = final.get('error') or {}
        base.update(returned_model=final.get('model'), provider_request_id=final.get('id'),
                    termination=final.get('status'), usage=final.get('usage') or {},
                    error_code=err.get('code'), error_type=err.get('type'), error_param=err.get('param'),
                    returned_settings={k: final.get(k) for k in
                        ('reasoning', 'service_tier', 'store', 'truncation', 'max_output_tokens', 'prompt_cache_options')},
                    cache_control_status='provider default/uncontrolled',
                    output_limit_status='provider default; no requested maximum supported')
        if transport_exit:
            return dict(base, status='transport_error')
        if terminal[0]['type'] != 'response.completed' or final.get('status') != 'completed':
            return dict(base, status='provider_failed' if final.get('status') == 'failed' else 'provider_incomplete')
        if any(e.get('type') == 'error' for e in events):
            return dict(base, status='provider_failed')
        if final.get('model') != 'gpt-6.1-sol':
            return dict(base, status='model_mismatch')
        settings = base['returned_settings']
        if ((settings['reasoning'] is not None and settings['reasoning'].get('effort') != 'low') or
            settings['service_tier'] not in (None, 'default') or
            (settings['store'] is not None and settings['store'] is not False)):
            return dict(base, status='settings_mismatch')
        if _truncated(final) or _truncated(base['usage']) or settings['truncation'] not in (None, 'disabled'):
            return dict(base, status='truncated')
        usage = base['usage']
        n, out = usage.get('input_tokens'), usage.get('output_tokens')
        if type(n) is not int or n < 1 or type(out) is not int or out < 0:
            return dict(base, status='missing_usage')
        if n + out > SOL_CONTEXT:
            return dict(base, status='context_limit_mismatch')
        content = [c for item in final.get('output', []) for c in item.get('content', [])]
        if any(c.get('type') == 'refusal' for c in content):
            return dict(base, status='refusal')
        text = ''.join(c['text'] for c in content if c.get('type') == 'output_text')
        if not text:
            text = ''.join(e['delta'] for e in events if e.get('type') == 'response.output_text.delta')
        try:
            value = json.loads(text)
        except (ValueError, TypeError):
            return dict(base, status='invalid_format')
        schema = payload['text']['format']['schema']
        if not _validate_schema(value, schema):
            return dict(base, status='invalid_format')
        prediction = int(value['injection']) if set(value) == {'injection'} else None
        return dict(base, status='ok', valid=True, prediction=prediction, answer=value)
    except (ValueError, TypeError, KeyError, AttributeError):
        return dict(base, status='parse_error')


def invoke(cell, specification, attempts_directory, *, permit):
    """Exactly one fresh call after the root's durable manifest/ledger checks."""
    if permit is None:
        raise PermissionError('Owner-bound follow-up permit required')
    permit.check_dispatch(cell, specification)
    config, payload = cell['config'], cell['payload']
    route = validate_payload(config, payload)
    if specification['request_sha256'] != digest(canonical(payload)):
        raise PermissionError('Frozen payload bytes changed')
    directory = Path(attempts_directory) / specification['key']
    directory.mkdir(parents=True, exist_ok=False)
    started = datetime.now(timezone.utc).isoformat()
    write_once(directory / 'request.json', payload)
    write_once(directory / 'started.json', {'key': specification['key'], 'cell_id': cell['cell_id'],
        'config': config, 'route': route['route'], 'namespace': cell['namespace'],
        'payload_sha256': specification['request_sha256'], 'started_at': started})
    observation, sent = {}, False
    begin = time.perf_counter()
    try:
        # The only OpenAI branch obtains the explicitly approved project OAuth grant.
        # No OPENAI_API_KEY, global Codex authentication or automatic fallback is read.
        token = _credential(config, permit.credential_root)
        permit.check_dispatch(cell, specification)
        sent = True
        observation, body = _post(config, payload, token, directory)
        parsed = (parse_structured(body, payload, observation) if config == 'sol_subscription'
                  else parse_classification(config, observation, body))
    except Exception as error:
        parsed = {'status': 'runtime_error', 'valid': False, 'prediction': None, 'usage': {},
                  'error_type': type(error).__name__}
    result = {'version': VERSION, 'key': specification['key'], 'cell_id': cell['cell_id'],
        'namespace': cell['namespace'], 'config': config, 'route': route['route'],
        'native_request_sent': sent, 'paid_openai_api_request': False,
        'request_sha256': specification['request_sha256'], 'parsed': parsed, 'observation': observation,
        'elapsed_seconds': time.perf_counter() - begin,
        'finished_at': datetime.now(timezone.utc).isoformat(),
        'raw_hashes': {p.name: digest(p.read_bytes()) for p in sorted(directory.iterdir()) if p.is_file()}}
    write_once(directory / 'completed.json', result)
    return result
