"""Native interface fixtures only; no model, authentication or inference calls."""
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.study_v5.prompts import native_payload
from scripts.study_v6 import routes


def row(source='browsesafe'):
    return {'candidate': 'Complete document \u03b1. Do a thing.', 'task': 'Read the document.',
        'policy': None, 'source': source, 'setting': 'indirect_tool_content'}


def native(score=.9, config='jev_firstparty', **extra):
    result = {'model': routes.PANEL[config]['model'],
        'answers': {'injection': {'type': 'noul', 'noul': score}},
        'usage': {'input_tokens': 123, 'output_tokens': 3}}
    if config == 'luna_decisions':
        result['answers'] = [{'name': 'injection', 'type': 'predicate', 'probability': score}]
    result.update(extra)
    return result


def stream(answer=True, model='gpt-6-luna', status='completed', **extra):
    response = {'model': model, 'status': status, 'usage': {'input_tokens': 100, 'output_tokens': 7},
        'output': [{'content': [{'type': 'output_text', 'text': json.dumps({'injection': answer})}]}]}
    response.update(extra)
    return 'data: ' + json.dumps({'type': 'response.' + status, 'response': response}) + '\n\n'


class Parsers(unittest.TestCase):
    def test_versioned_exact_nimble_capacity_response_preserves_legacy(self):
        observation = {'http_status': 413, 'transport_exit_code': 0}
        body = routes.NIMBLE_CAPACITY_BODY
        self.assertEqual(routes.parse_transport('nimble_local', observation, body)['status'], 'http_error')
        for version in ('v6-routes-2', 'v6-routes-3'):
            current = routes.parse_transport('nimble_local', observation, body, version)
            self.assertEqual(current, {'status': 'unsupported_over_limit', 'valid': False, 'prediction': None})
        for config, obs, raw, expected in (
                ('nimble_local', observation, body + '\n', 'http_error'),
                ('nimble_local', observation, '{"error":"another limit"}', 'http_error'),
                ('jev_firstparty', observation, body, 'http_error'),
                ('nimble_local', observation | {'transport_exit_code': 28}, body, 'transport_error')):
            self.assertEqual(routes.parse_transport(config, obs, raw, routes.PARSER_VERSION)['status'], expected)
        with self.assertRaises(ValueError):
            routes.parse_transport('nimble_local', observation, body, 'unknown')

    def test_strict_native_context_capacity_error_counts_and_json(self):
        error = 'request (12677 tokens) exceeds the available context size (8448 tokens), try increasing it'
        body = json.dumps({'error': error})
        expected = {'requested_tokens': 12677, 'available_tokens': 8448}
        self.assertEqual(routes.native_context_capacity_error(body), expected)
        self.assertEqual(routes.native_context_capacity_error(body.encode()), expected)
        for invalid in (
                error, '{}', '[]', 'null', '{"error":true}', body[:-1],
                json.dumps({'error': error, 'other': 1}),
                '{"error":"other","error":' + json.dumps(error) + '}',
                json.dumps({'error': error + '.'}), json.dumps({'error': error + '\n'}),
                json.dumps({'error': error.replace('request (', 'request  (')}),
                json.dumps({'error': error.replace('12677', '8448')}),
                json.dumps({'error': error.replace('12677', '8447')}),
                json.dumps({'error': error.replace('12677', '0')}),
                json.dumps({'error': error.replace('8448', '0')}),
                json.dumps({'error': error.replace('12677', '-12677')}),
                json.dumps({'error': error.replace('12677', '012677')}),
                json.dumps({'error': error.replace('12677', '12677.0')}),
                json.dumps({'error': error.replace('8448', 'NaN')}), b'\xff', {'error': error}):
            self.assertIsNone(routes.native_context_capacity_error(invalid))

    def test_only_parser3_nimble_http400_successful_transport_recognizes_context_error(self):
        body = '{"error":"request (12677 tokens) exceeds the available context size (8448 tokens), try increasing it"}'
        observation = {'http_status': 400, 'transport_exit_code': 0}
        for version in (None, 'v6-routes-2'):
            self.assertEqual(routes.parse_transport('nimble_local', observation, body, version)['status'], 'http_error')
        parsed = routes.parse_transport('nimble_local', observation, body, 'v6-routes-3')
        self.assertEqual(parsed, {'status': 'unsupported_over_limit', 'valid': False, 'prediction': None})
        self.assertFalse(routes.requires_stop(parsed))
        for config, obs, raw, expected in (
                ('jev_firstparty', observation, body, 'http_error'),
                ('nimble_local', observation | {'http_status': 500}, body, 'http_error'),
                ('nimble_local', observation | {'transport_exit_code': 28}, body, 'transport_error'),
                ('nimble_local', observation, '{"error":"Context size has been exceeded."}', 'http_error'),
                ('nimble_local', observation, body.replace('12677', '8448'), 'http_error')):
            parsed = routes.parse_transport(config, obs, raw, 'v6-routes-3')
            self.assertEqual(parsed['status'], expected)
            self.assertTrue(routes.requires_stop(parsed))

    def test_second_statically_proved_native_context_form_is_strict_and_versioned(self):
        error = 'input (12677 tokens) is larger than the max context size (8448 tokens). skipping'
        body = json.dumps({'error': error})
        observation = {'http_status': 400, 'transport_exit_code': 0}
        self.assertEqual(routes.native_context_capacity_error(body),
            {'requested_tokens': 12677, 'available_tokens': 8448})
        for version in (None, 'v6-routes-2'):
            self.assertEqual(routes.parse_transport('nimble_local', observation, body, version)['status'], 'http_error')
        self.assertEqual(routes.parse_transport('nimble_local', observation, body, 'v6-routes-3'),
            {'status': 'unsupported_over_limit', 'valid': False, 'prediction': None})
        for invalid in (error.replace('12677', '8448'), error.replace('8448', '0'),
                error.replace('12677', '012677'), error + '.', error.replace('. skipping', ' skipping')):
            raw = json.dumps({'error': invalid})
            self.assertIsNone(routes.native_context_capacity_error(raw))
            self.assertEqual(routes.parse_transport('nimble_local', observation, raw, 'v6-routes-3')['status'], 'http_error')
        self.assertEqual(routes.parse_transport('nimble_local', observation | {'transport_exit_code': 28},
            body, 'v6-routes-3')['status'], 'transport_error')
        self.assertEqual(routes.parse_transport('jev_firstparty', observation, body, 'v6-routes-3')['status'], 'http_error')

    def test_fixed_boolean_orientation_and_ties(self):
        for config in ('jev_firstparty', 'luna_decisions', 'nimble_local'):
            for score, prediction, status in ((.1, 0, 'ok'), (.9, 1, 'ok'), (.5, None, 'tie')):
                result = routes.parse_response(config, json.dumps(native(score, config)))
                self.assertEqual((result['prediction'], result['status']), (prediction, status))
                self.assertEqual(result['valid'], score != .5)

    def test_invalid_native_numbers_and_duplicate_answers(self):
        for value in (True, False, '0.9', None, -1, 2, float('nan')):
            self.assertEqual(routes.parse_response('jev_firstparty', json.dumps(native(value)))['status'], 'parse_error')
        raw = native(config='luna_decisions')
        raw['answers'].append(dict(raw['answers'][0]))
        self.assertEqual(routes.parse_response('luna_decisions', json.dumps(raw))['status'], 'parse_error')
        raw = native()
        raw['answers']['other'] = raw['answers']['injection']
        self.assertEqual(routes.parse_response('jev_firstparty', json.dumps(raw))['status'], 'parse_error')

    def test_model_truncation_and_usage_fail_closed(self):
        self.assertEqual(routes.parse_response('jev_firstparty', json.dumps(native(model='jev-latest')))['status'], 'model_mismatch')
        for usage, expected in (({'input_tokens': True}, 'missing_usage'),
                ({'input_tokens': 0}, 'missing_usage'), ({'input_tokens': 32001}, 'context_limit_mismatch'),
                ({'input_tokens': 100, 'truncated': True}, 'truncated'),
                ({'input_tokens': 100, 'state_tokens_dropped': 1}, 'truncated')):
            result = routes.parse_response('jev_firstparty', json.dumps(native(usage=usage)))
            self.assertEqual(result['status'], expected)
            self.assertEqual(result['usage'], usage)

    def test_native_confidence_is_distinct_from_decision_score(self):
        raw = native(.7)
        raw['answers']['injection']['confidence'] = .2
        result = routes.parse_response('jev_firstparty', json.dumps(raw))
        self.assertEqual((result['score'], result['native_confidence']), (.7, .2))
        raw['answers']['injection']['confidence'] = True
        result = routes.parse_response('jev_firstparty', json.dumps(raw))
        self.assertEqual(result['status'], 'ok')
        self.assertNotIn('native_confidence', result)
        self.assertEqual(result['native_confidence_status'], 'invalid_optional_field')

    def test_chat_boolean_only_no_invented_confidence(self):
        for answer in (True, False):
            parsed = routes.parse_response('luna_chat', stream(answer))
            self.assertEqual(parsed['prediction'], int(answer))
            self.assertEqual(parsed['status'], 'ok')
            self.assertNotIn('score', parsed)
        self.assertEqual(routes.parse_response('luna_chat', stream('true'))['status'], 'invalid_format')
        self.assertEqual(routes.parse_response('luna_chat', stream(True, model='gpt-6-astra'))['status'], 'model_mismatch')

    def test_chat_failure_dispositions(self):
        self.assertEqual(routes.parse_response('luna_chat', 'data: [DONE]\n\n')['status'], 'interrupted_stream')
        self.assertEqual(routes.parse_response('luna_chat', stream(status='incomplete',
            incomplete_details={'reason': 'max_output_tokens'}))['status'], 'truncated')
        self.assertEqual(routes.parse_response('luna_chat', stream(output=[{'content': [{'type': 'refusal'}]}]))['status'], 'refusal')
        self.assertEqual(routes.parse_response('luna_chat', stream(truncation='auto'))['status'], 'truncated')
        self.assertEqual(routes.parse_response('luna_chat', stream() + stream())['status'], 'invalid_terminal_events')
        self.assertEqual(routes.parse_response('luna_chat', 'data: {"type":"error"}\n\n')['status'], 'provider_failed')

    def test_input_and_output_truncation_have_distinct_stop_policy(self):
        output = routes.parse_response('luna_chat', stream(status='incomplete',
            incomplete_details={'reason': 'max_output_tokens'}))
        self.assertEqual((output['status'], output['truncation_scope']), ('truncated', 'output'))
        self.assertFalse(output['valid'])
        self.assertIsNone(output['prediction'])
        self.assertFalse(routes.requires_stop(output))
        for body in (stream(truncation='auto'), stream(status='incomplete',
                incomplete_details={'reason': 'max_output_tokens'},
                usage={'input_tokens': 100, 'input_truncated': True})):
            parsed = routes.parse_response('luna_chat', body)
            self.assertEqual(parsed['truncation_scope'], 'input')
            self.assertTrue(routes.requires_stop(parsed))
        native_input = routes.parse_response('jev_firstparty', json.dumps(native(
            usage={'input_tokens': 100, 'state_tokens_dropped': 1})))
        self.assertEqual(native_input['truncation_scope'], 'input')
        self.assertTrue(routes.requires_stop(native_input))

    def test_case_failures_abstain_without_stopping_and_missing_usage_still_stops(self):
        cases = [stream(output=[{'content': [{'type': 'refusal'}]}]),
            stream('invalid Boolean'), stream(output=[{'content': [{'type': 'output_text', 'text': 'Not JSON'}]}]),
            stream(status='incomplete', incomplete_details={'reason': 'content_filter'})]
        self.assertEqual([routes.parse_response('luna_chat', b)['status'] for b in cases],
            ['refusal', 'invalid_format', 'invalid_format', 'provider_incomplete'])
        for body in cases:
            parsed = routes.parse_response('luna_chat', body)
            self.assertFalse(parsed['valid'])
            self.assertIsNone(parsed['prediction'])
            self.assertFalse(routes.requires_stop(parsed))
            self.assertTrue(routes.requires_stop(dict(parsed, usage={})))
        for status in ('parse_error', 'transport_error', 'http_error', 'authentication_error',
                'model_mismatch', 'settings_mismatch', 'missing_usage', 'runtime_error',
                'context_limit_mismatch', 'provider_failed'):
            self.assertTrue(routes.requires_stop({'status': status, 'usage': {'input_tokens': 100}}))

    def test_chat_returned_settings_mismatches_stop(self):
        for extra, field in (({'reasoning': {'effort': 'high'}}, 'reasoning.effort'),
                ({'max_output_tokens': 123}, 'max_output_tokens'), ({'service_tier': 'priority'}, 'service_tier')):
            result = routes.parse_response('luna_chat', stream(**extra))
            self.assertEqual(result['status'], 'settings_mismatch')
            self.assertIn(field, result['settings_mismatch_fields'])
            self.assertEqual(result['usage']['input_tokens'], 100)


class Coverage(unittest.TestCase):
    def test_native_byte_gate_normalization_unicode_and_schema(self):
        request = routes.payload('nimble_local', row(), 'task')
        proof = routes.native_byte_coverage(request)
        self.assertEqual(proof['measured_bytes'], len(routes.canonical(request)) + 2)
        self.assertEqual(proof['limit_bytes'], 65536)
        self.assertTrue(proof['supported'])
        self.assertFalse(proof['preflight_native_token_count'])
        request['state'] = 'é<&>\u2028\u2029'
        baseline = routes.native_byte_coverage(request)
        # State RawMessage retains these exact UTF-8 bytes. Schema's inner
        # default json.Marshal escapes HTML (5 extra each) and separators
        # (6 escape bytes replacing each 3-byte UTF-8 sequence).
        self.assertEqual(baseline['measured_bytes'], len(routes.canonical(request)) + 2)
        request['questions']['injection']['instructions'] = 'é<&>\u2028\u2029'
        escaped = routes.native_byte_coverage(request)
        self.assertEqual(escaped['measured_bytes'], len(routes.canonical(request)) + 2 + 15 + 6)
        self.assertEqual(escaped['payload_sha256'], routes.digest(routes.canonical(request)))
        self.assertEqual(request['keep_alive'], '2m')

    def test_native_byte_gate_inclusive_utf8_and_schema_boundaries(self):
        for schema in (False, True):
            request = routes.payload('nimble_local', row(), 'task')
            if schema:
                request['questions']['injection']['instructions'] = 'é'
            else:
                request['state'] = 'é'
            missing = 65536 - routes.native_byte_coverage(request)['measured_bytes']
            if schema:
                request['questions']['injection']['instructions'] += 'x' * missing
            else:
                request['state'] += 'x' * missing
            at = routes.native_byte_coverage(request)
            self.assertEqual((at['measured_bytes'], at['supported']), (65536, True))
            request['state'] += 'x'
            over = routes.native_byte_coverage(request)
            self.assertEqual((over['measured_bytes'], over['supported']), (65537, False))
            self.assertEqual(over['coverage_status'], 'unsupported_native_byte_limit')
        for change in ({'keep_alive': '3m'}, {'images': []}, {'model': 'other'}):
            with self.assertRaises(ValueError):
                routes.native_byte_coverage(request | change)

    def test_exact_v5_contract_and_source_fields(self):
        for config in routes.PANEL:
            if config == 'protectai_local':
                continue
            for condition in ('candidate', 'format', 'task', 'reminder', 'length', 'scrambled'):
                self.assertEqual(routes.payload(config, row(), condition), native_payload(row(), condition, config))
        request = routes.payload('protectai_local', row(), 'candidate')
        self.assertEqual(request['candidate'], row()['candidate'])
        self.assertNotIn('task', request)
        for source in ('spml', 'scope', 'unknown'):
            with self.assertRaises(ValueError):
                routes.payload('protectai_local', row(source), 'candidate')
        with self.assertRaises(ValueError):
            routes.payload('protectai_local', row(), 'task')

    def test_no_tokenizer_certification_from_bytes(self):
        request = routes.payload('jev_firstparty', row(), 'task')
        pending = routes.coverage('jev_firstparty', request)
        self.assertFalse(pending['supported'])
        self.assertFalse(pending['preflight_native_token_count'])
        gate = routes.coverage('jev_firstparty', request, allow_server_gate=True)
        self.assertEqual(gate['coverage_status'], 'full_input_server_gate')
        self.assertTrue(gate['supported'])
        self.assertFalse(gate['capacity_verified_before_dispatch'])
        self.assertNotIn('input_tokens', gate)

    def test_native_token_binding_and_budget(self):
        request = routes.payload('nimble_local', row(), 'task')
        evidence = {'payload_sha256': routes.digest(routes.canonical(request)),
            'model': request['model'], 'framing_included': True, 'provenance': 'test-only exact native fixture', 'input_tokens': 8194}
        self.assertTrue(routes.coverage('nimble_local', request, native_count=evidence)['supported'])
        self.assertFalse(routes.coverage('nimble_local', request,
            native_count=evidence | {'input_tokens': 8195})['supported'])
        with self.assertRaises(ValueError):
            routes.coverage('nimble_local', request, native_count=evidence | {'payload_sha256': 'wrong'})
        with self.assertRaises(ValueError):
            routes.coverage('nimble_local', request, native_count=evidence | {'framing_included': False})

    def test_laya_audit_binding_and_no_truncation(self):
        request = routes.payload('laya_local', row(), 'task')
        audit = {'payload_sha256': routes.digest(routes.canonical(request)), 'truncated': False,
            'state_tokens': 8190, 'head_tokens': 100}
        self.assertTrue(routes.coverage('laya_local', request, laya_audit=audit)['supported'])
        self.assertFalse(routes.coverage('laya_local', request, laya_audit=audit | {'truncated': True})['supported'])
        with self.assertRaises(ValueError):
            routes.coverage('laya_local', request, laya_audit=audit | {'payload_sha256': 'wrong'})

    def test_specialist_complete_overlapping_windows(self):
        class Tokenizer:
            def encode(self, text, add_special_tokens):
                assert add_special_tokens is False
                return list(range(1000))
        request = routes.payload('protectai_local', row(), 'candidate')
        coverage = routes.coverage('protectai_local', request, tokenizer=Tokenizer())
        self.assertEqual((coverage['candidate_tokens'], coverage['windows']), (1000, 3))
        self.assertEqual(coverage['coverage_status'], 'complete_windowed')


class Accounting(unittest.TestCase):
    def test_usage_upper_is_separate_from_base_and_invoice(self):
        parsed = {'usage': {'input_tokens': 1000000, 'input_tokens_details': {'cache_write_tokens': 200000}}}
        result = routes.metered_cost('luna_decisions', parsed)
        self.assertEqual(result['conservative_usage_cost_usd'], .50)
        self.assertEqual(result['uncached_base_usage_cost_usd'], .1)
        self.assertIsNone(result['exact_usage_cost_usd'])
        self.assertEqual(result['usage'], parsed['usage'])
        self.assertEqual(routes.metered_cost('jev_firstparty', parsed)['exact_usage_cost_usd'], .042)
        self.assertIsNone(routes.metered_cost('jev_firstparty', {})['conservative_usage_cost_usd'])
        self.assertEqual(routes.metered_cost('astra_chat', {})['exact_usage_cost_usd'], 0)


class DurableAttempts(unittest.TestCase):
    def test_future_context_rejection_retains_raw_without_usage_or_retry(self):
        request = routes.payload('nimble_local', row(), 'task')
        body = '{"error":"request (12677 tokens) exceeds the available context size (8448 tokens), try increasing it"}'
        def fake_post(config, payload, token, directory):
            routes._exclusive(directory / 'response.raw', body.encode())
            return {'http_status': 400, 'transport_exit_code': 0}, body
        with tempfile.TemporaryDirectory() as temp, patch.object(routes, '_post', side_effect=fake_post) as post:
            result = routes.invoke('nimble_local', request, temp, 'context-rejection', runtime=object())
            post.assert_called_once()
            self.assertEqual(result['parser_version'], 'v6-routes-3')
            self.assertTrue(result['native_request_sent'])
            self.assertFalse(result['local_preflight'])
            self.assertFalse(result['stop_required'])
            self.assertEqual(result['parsed'], {'status': 'unsupported_over_limit', 'valid': False, 'prediction': None})
            self.assertNotIn('usage', result['parsed'])
            self.assertEqual((Path(temp) / 'context-rejection' / 'response.raw').read_bytes(), body.encode())

    def test_credential_failure_has_no_dispatch_intent(self):
        request = routes.payload('jev_firstparty', row(), 'task')
        with tempfile.TemporaryDirectory() as temp, patch.object(routes, '_credential',
                side_effect=ValueError('fixture-only missing credential')), patch.object(routes, '_post') as post:
            result = routes.invoke('jev_firstparty', request, temp, 'no-credential')
            post.assert_not_called()
            self.assertFalse(result['native_request_sent'])
            self.assertFalse(result['local_preflight'])
            self.assertTrue(result['stop_required'])
            self.assertEqual(result['parsed']['status'], 'runtime_error')

    def test_known_native_overflow_has_only_local_evidence_without_dispatch(self):
        request = routes.payload('nimble_local', row(), 'task')
        request['state'] = 'é' * 40000
        unchanged = routes.canonical(request)
        with tempfile.TemporaryDirectory() as temp, patch.object(routes, '_post') as post, patch.object(routes, '_credential') as credential:
            result = routes.invoke('nimble_local', request, temp, 'preflight')
            post.assert_not_called()
            credential.assert_not_called()
            self.assertEqual(result['parser_version'], 'v6-routes-3')
            self.assertFalse(result['native_request_sent'])
            self.assertTrue(result['local_preflight'])
            self.assertFalse(result['stop_required'])
            self.assertEqual(result['parsed'], {'status': 'unsupported_over_limit', 'valid': False, 'prediction': None})
            self.assertEqual(result['observation'], {})
            self.assertNotIn('usage', result['parsed'])
            directory = Path(temp) / 'preflight'
            self.assertEqual({p.name for p in directory.iterdir()},
                {'request.json', 'started.json', 'local-preflight.json', 'completed.json'})
            self.assertEqual(json.loads((directory / 'local-preflight.json').read_text()), result['native_byte_coverage'])
            self.assertEqual((directory / 'request.json').read_bytes(), unchanged)
            self.assertEqual(routes.canonical(request), unchanged)

    def test_native_byte_fit_still_dispatches_unchanged_request_once(self):
        request = routes.payload('nimble_local', row(), 'task')
        body = json.dumps(native(config='nimble_local'))
        with tempfile.TemporaryDirectory() as temp, patch.object(routes, '_post',
                return_value=({'http_status': 200, 'transport_exit_code': 0}, body)) as post:
            result = routes.invoke('nimble_local', request, temp, 'fit', runtime=object())
            post.assert_called_once()
            self.assertIs(post.call_args.args[1], request)
            self.assertTrue(result['native_request_sent'])
            self.assertFalse(result['local_preflight'])
            self.assertTrue(result['native_byte_coverage']['supported'])
            self.assertEqual(result['parsed']['status'], 'ok')

    def test_case_behavior_does_not_stop_invoke_or_trigger_retry(self):
        request = routes.payload('luna_chat', row(), 'task')
        bodies = [stream(output=[{'content': [{'type': 'refusal'}]}]), stream('not a Boolean'),
            stream(status='incomplete', incomplete_details={'reason': 'max_output_tokens'}),
            stream(status='incomplete', incomplete_details={'reason': 'content_filter'})]
        with tempfile.TemporaryDirectory() as temp, patch.object(routes, '_credential', return_value='test-only'):
            for i, body in enumerate(bodies):
                with patch.object(routes, '_post', return_value=({'http_status': 200, 'transport_exit_code': 0}, body)) as post:
                    result = routes.invoke('luna_chat', request, temp, str(i))
                    self.assertFalse(result['stop_required'])
                    self.assertFalse(result['parsed']['valid'])
                    self.assertIsNone(result['parsed']['prediction'])
                    post.assert_called_once()

    def test_first_attempt_exclusive_and_no_automatic_retry(self):
        request = routes.payload('jev_firstparty', row(), 'task')
        calls = []
        def fake_post(config, payload, token, directory):
            calls.append(config)
            routes._exclusive(directory / 'response.raw', b'partial malformed body')
            return {'http_status': 200, 'transport_exit_code': 0}, 'partial malformed body'
        with tempfile.TemporaryDirectory() as temp, patch.object(routes, '_post', fake_post), patch.object(routes, '_credential', return_value='test-only'):
            result = routes.invoke('jev_firstparty', request, temp, 'first')
            self.assertEqual(result['parsed']['status'], 'parse_error')
            self.assertTrue(result['stop_required'])
            self.assertTrue((Path(temp) / 'first' / 'request.json').exists())
            self.assertEqual((Path(temp) / 'first' / 'response.raw').read_bytes(), b'partial malformed body')
            with self.assertRaises(FileExistsError):
                routes.invoke('jev_firstparty', request, temp, 'first')
            self.assertEqual(calls, ['jev_firstparty'])

    def test_transport_timeout_retains_usage_but_abstains(self):
        def fake_post(config, payload, token, directory):
            body = json.dumps(native())
            routes._exclusive(directory / 'response.raw', body.encode())
            return {'http_status': 200, 'transport_exit_code': 28}, body
        with tempfile.TemporaryDirectory() as temp, patch.object(routes, '_post', fake_post), patch.object(routes, '_credential', return_value='test-only'):
            result = routes.invoke('jev_firstparty', routes.payload('jev_firstparty', row(), 'task'), temp, 'timeout')
            self.assertEqual(result['parsed']['status'], 'transport_error')
            self.assertEqual(result['parsed']['usage']['input_tokens'], 123)
            self.assertIsNone(result['parsed']['prediction'])

    def test_http_auth_and_context_errors_distinct(self):
        request = routes.payload('jev_firstparty', row(), 'task')
        with tempfile.TemporaryDirectory() as temp, patch.object(routes, '_credential', return_value='test-only'):
            for status, body, expected, stop in ((401, '{}', 'authentication_error', True),
                    (400, '{"error":"max_tokens_exceeded"}', 'unsupported_over_limit', False)):
                with patch.object(routes, '_post', return_value=({'http_status': status, 'transport_exit_code': 0}, body)):
                    result = routes.invoke('jev_firstparty', request, temp, str(status))
                self.assertEqual(result['parsed']['status'], expected)
                self.assertEqual(result['stop_required'], stop)

    def test_durable_curl_partial_and_credential_redaction(self):
        token = 'fixture-secret-not-real'
        def fake_run(command, **kwargs):
            self.assertEqual(command, ['/usr/bin/curl', '--disable', '--config', '-'])
            self.assertIn(token, kwargs['input'])
            self.assertNotIn('retry', kwargs['input'])
            self.assertNotIn('location', kwargs['input'])
            (directory / 'response.partial').write_text('partial ' + token)
            (directory / 'response-headers.partial').write_text('x-request-id: fixture\nAuthorization: ' + token)
            return subprocess.CompletedProcess(command, 28, stdout='200', stderr='safe error')
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / 'request.json').write_bytes(b'{}')
            with patch.object(subprocess, 'run', fake_run):
                observation, body = routes._post('jev_firstparty', {}, token, directory)
            self.assertEqual(body, 'partial [redacted]')
            self.assertEqual(observation['transport_exit_code'], 28)
            for path in directory.iterdir():
                self.assertNotIn(token.encode(), path.read_bytes())


if __name__ == '__main__':
    unittest.main()
