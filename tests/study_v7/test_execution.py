"""Offline regression fixtures only: fake transports and synthetic source text."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts.study_v5 import prompts
from scripts.study_v7 import requests, budget, capacity, routes, run


def main_rows(n=4, partition='confirmation'):
    return [{'id': f'{partition}-{i}-{label}', 'group_id': f'{partition}-group-{i}',
        'pair_id': str(i), 'source': 'browsesafe', 'task': f'Find the relevant destination {i}',
        'candidate': f'Complete synthetic page {partition} {i} label {label}',
        'upstream_label': label, 'partition': partition,
        'input_sha256': requests.digest(f'{partition}-{i}-{label}'.encode())}
        for i in range(n) for label in (0, 1)]


def external_rows(n=4, partition='confirmation'):
    return [{'id': f'external-{partition}-{label}-{i}', 'group_id': f'ext-{partition}-{label}-{i}',
        'source': 'promptshield', 'candidate': f'Complete original request {partition} {label} {i}',
        'upstream_label': label, 'partition': partition, 'general_subset': partition == 'confirmation' and i < 2}
        for label in (0, 1) for i in range(n)]


def stream(answer=None, config='sol_responses', **extra):
    p = requests.PANEL[config]
    raw = {'id': 'synthetic-response', 'model': p['model'], 'status': 'completed',
        'usage': {'input_tokens': 10, 'output_tokens': 2,
                  'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}},
        'reasoning': {'effort': p['reasoning']}, 'max_output_tokens': p['output_cap'],
        'service_tier': 'default', 'prompt_cache_options': {'mode': 'explicit'}, 'store': False,
        'output': [{'content': [{'type': 'output_text', 'text': json.dumps(answer or {'injection': True})}]}]}
    raw.update(extra)
    return 'data: ' + json.dumps({'type': 'response.' + raw['status'], 'response': raw}) + '\n\n'


class Requests(unittest.TestCase):
    def test_main_native_exact_v5_contract_and_no_annotation_fields(self):
        row = main_rows(1)[0]
        old = row | {'setting': 'indirect_tool_content', 'policy': None}
        for condition in requests.CONDITIONS:
            for config in requests.NATIVE:
                payload = requests.payload(config, row, condition)
                self.assertEqual(payload, prompts.native_payload(old, condition, config))
                state = json.loads(payload.get('state') or payload['input'])
                self.assertEqual(state['CANDIDATE'], row['candidate'])
                self.assertEqual(set(state), {'CANDIDATE', 'CANDIDATE_ROLE', 'TRUSTED_USER_TASK'})
        self.assertEqual(len(prompts.placebo(row['task'])), len(row['task']))

    def test_external_original_complete_request_and_exact_paid_settings(self):
        row = external_rows(1)[0]
        for config in requests.NATIVE + requests.GENERAL:
            payload = requests.payload(config, row, 'external')
            state = payload.get('state') or payload['input']
            if config in requests.GENERAL:
                state = state[0]['content']
                self.assertEqual(payload['prompt_cache_options'], {'mode': 'explicit'})
                self.assertFalse(payload['store'])
                self.assertEqual(payload['service_tier'], 'default')
                self.assertTrue(payload['text']['format']['strict'])
                self.assertNotIn('previous_response_id', payload)
            self.assertEqual(json.loads(state), {'FULL_REQUEST': row['candidate']})
            self.assertNotIn('task', json.loads(state))
        self.assertEqual(requests.payload('sol_responses', row)['reasoning']['effort'], 'low')
        self.assertEqual(requests.payload('luna_responses', row)['max_output_tokens'], 256)

    def test_repeat_distinct_attempt_identity_identical_bytes_nested_subsets(self):
        rows = main_rows(4) + main_rows(1, 'development')
        external = external_rows(4) + external_rows(1, 'development')
        plan = requests.build_plan(rows, external)
        by_hash = {}
        for record in plan['requests'].values():
            identity = record['config'], record['payload_sha256']
            if record['namespace'] == 'first':
                by_hash[identity] = record
            elif record['namespace'] == 'repeat-1':
                original = by_hash.get(identity) or next(r for r in plan['requests'].values()
                    if r['config'] == record['config'] and r['payload_sha256'] == record['payload_sha256'] and r['namespace'] == 'first')
                self.assertNotEqual(original['key'], record['key'])
                lookup = {r['id']: r for r in rows + external}
                self.assertEqual(requests.canonical(requests.materialize(original, lookup)),
                                 requests.canonical(requests.materialize(record, lookup)))
        selected = plan['subsets']['external_general_ids']
        self.assertEqual(set(selected), {r['id'] for r in external if r.get('general_subset')})
        self.assertEqual(sum(len(g['request_keys']) for g in plan['schedules']['external_general']), 8)
        for group in plan['schedules']['main_native']:
            self.assertEqual(len(group['request_keys']), 16)
        self.assertFalse(plan['experimental_inference_authorized'])

    def test_audit_original_labels_do_not_enter_classifier(self):
        pair = main_rows(1)
        audit = requests.audit_payload(pair)
        state = json.loads(audit['input'][0]['content'])
        self.assertEqual(state['SOURCE_LABELS'], {'CLEAN_PAGE': 0, 'ATTACK_PAGE': 1})
        self.assertEqual(state['CLEAN_PAGE'], pair[0]['candidate'])
        self.assertNotIn('SOURCE_LABELS', requests.payload('sol_responses', pair[0], 'task')['input'][0]['content'])


class Capacity(unittest.TestCase):
    def test_native_preflight_remains_unverified_and_local_windows_complete(self):
        row = main_rows(1)[0]
        payload = requests.payload('jev_firstparty', row, 'task')
        self.assertFalse(capacity.check('jev_firstparty', payload)['supported'])
        gate = capacity.check('jev_firstparty', payload, allow_server_gate=True)
        self.assertTrue(gate['supported'])
        self.assertFalse(gate['preflight_native_token_count'])
        self.assertFalse(gate['capacity_verified_before_dispatch'])
        evidence = {'payload_sha256': gate['payload_sha256'], 'model': payload['model'],
                    'framing_included': True, 'provenance': 'synthetic native fixture', 'input_tokens': 32001}
        self.assertEqual(capacity.check('jev_firstparty', payload, native_count=evidence)['coverage_status'], 'unsupported_over_limit')
        with self.assertRaises(ValueError):
            capacity.check('jev_firstparty', payload, native_count=evidence | {'framing_included': False})
        class Tokenizer:
            def encode(self, text, add_special_tokens=False):
                return list(range(1000))
        cov = capacity.check('protectai_local', requests.payload('protectai_local', row), tokenizer=Tokenizer())
        self.assertEqual((cov['candidate_tokens'], cov['windows']), (1000, 3))
        self.assertEqual(cov['tokenizer_revision'], requests.PANEL['protectai_local']['revision'])


class Accounting(unittest.TestCase):
    def test_cost_exact_response_ceiling_cache_and_long_tier(self):
        self.assertEqual(Decimal(budget.maximum_cost('jev_firstparty')), Decimal('.001344'))
        self.assertEqual(Decimal(budget.maximum_cost('luna_decisions')), Decimal('.525'))
        self.assertEqual(Decimal(budget.maximum_cost('sol_responses', 1000)), Decimal('.02248'))
        self.assertEqual(Decimal(budget.maximum_cost('luna_responses', 1000)), Decimal('.000228'))
        self.assertEqual(Decimal(budget.maximum_cost('sol_responses', 300000)), Decimal('1.23072'))
        self.assertIsNone(budget.usage_cost('sol_responses', {'input_tokens': 5, 'output_tokens': 1}))
        self.assertIsNone(budget.usage_cost('sol_responses', {'input_tokens': 5, 'output_tokens': 1,
            'input_tokens_details': {'cached_tokens': 1}}))
        self.assertEqual(Decimal(budget.usage_cost('sol_responses', {'input_tokens': 1000, 'output_tokens': 10,
            'input_tokens_details': {'cached_tokens': 0, 'cache_write_tokens': 0}})), Decimal('.0021'))

    def test_atomic_group_cap_unknown_hold_no_duplicate_dispatch_or_replay(self):
        specs = [{'key': str(i), 'provider': provider, 'reserved_usd': '.5', 'request_sha256': 'a'*64,
                  'config': 'test', 'split': 'confirmation'} for i, provider in enumerate(('openai', 'typesafe'))]
        p = budget.policy({'openai': '7', 'typesafe': '1'}, {'openai': '8', 'typesafe': '2'},
                          {'openai': '1', 'typesafe': '1'}, {'main_native': {'openai': '1', 'typesafe': '1'}})
        with tempfile.TemporaryDirectory() as temp:
            ledger = budget.BudgetLedger(Path(temp)/'journal', p)
            groups = [{'group': 'g0', 'requests': specs}, {'group': 'g1', 'requests': [dict(s, key=s['key']+'b', reserved_usd='.6') for s in specs]}]
            ledger.register_schedule('main_native', groups)
            self.assertEqual(ledger.reserve_next_group('main_native')['status'], 'admitted')
            with self.assertRaises(ValueError):
                ledger.reserve_next_group('main_native')
            for s in specs:
                ledger.mark_dispatched(s['key'])
                with self.assertRaises(PermissionError):
                    ledger.mark_dispatched(s['key'])
                ledger.settle(s['key'], None, evidence_sha256='b'*64)
            self.assertEqual(ledger.reserve_next_group('main_native')['status'], 'stopped')
            snapshot = ledger.snapshot()
            self.assertEqual(snapshot['incremental_accounted_usd'], {'openai': '0.5', 'typesafe': '0.5'})
            self.assertEqual(set(snapshot['entries']), {'0', '1'})
            self.assertTrue(all(e['status'] == 'unknown_usage' for e in snapshot['entries'].values()))
            self.assertEqual(budget.BudgetLedger(Path(temp)/'journal').snapshot()['all_in_accounted_usd'],
                             {'openai': '7.5', 'typesafe': '1.5'})

    def test_two_process_objects_cannot_overreserve(self):
        p = budget.policy({'openai': '0', 'typesafe': '0'}, {'openai': '1', 'typesafe': '1'},
            {'openai': '1', 'typesafe': '1'}, {'external_general': {'openai': '1', 'typesafe': '1'}})
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'journal'
            first, second = budget.BudgetLedger(path, p), budget.BudgetLedger(path)
            spec = {'key': 'one', 'provider': 'openai', 'reserved_usd': '.9', 'request_sha256': 'a'*64}
            first.register_schedule('external_general', [{'group': 'one', 'requests': [spec]}])
            def reserve(ledger):
                try:
                    return ledger.reserve_next_group('external_general')['status']
                except ValueError:
                    return 'held'
            with ThreadPoolExecutor(max_workers=2) as pool:
                values = list(pool.map(reserve, [first, second]))
            self.assertEqual(values.count('admitted'), 1)
            self.assertEqual(first.snapshot()['incremental_accounted_usd']['openai'], '0.9')


class CrashRecovery(unittest.TestCase):
    def _fixture(self, *, namespace='first', saved_namespace=None, status='ok', primary_override=None):
        temp = tempfile.TemporaryDirectory(); self.addCleanup(temp.cleanup)
        directory = Path(temp.name)/'attempt'; directory.mkdir()
        request = {'key': 'synthetic-'+namespace, 'config': 'luna_responses', 'split': 'confirmation',
            'namespace': namespace, 'payload_sha256': 'a'*64}
        p = budget.policy({'openai': '0', 'typesafe': '0'}, {'openai': '1', 'typesafe': '1'},
            {'openai': '1', 'typesafe': '1'}, {'main_general': {'openai': '1', 'typesafe': '1'}})
        ledger = budget.BudgetLedger(Path(temp.name)/'journal', p)
        ledger.register_schedule('main_general', [{'group': 'synthetic-group',
            'requests': [budget.reservation(request)]}])
        ledger.reserve_next_group('main_general'); ledger.mark_dispatched(request['key'])
        saved_namespace = namespace if saved_namespace is None else saved_namespace
        parsed = {'status': status, 'valid': status == 'ok', 'prediction': 1 if status == 'ok' else None,
            'usage': {'input_tokens': 10, 'output_tokens': 2} if status == 'ok' else {}}
        # Missing cache accounting is intentional: the parser can complete before
        # the executor notices the unknown paid charge and crashes before settle.
        result = {'request_sha256': 'a'*64, 'namespace': saved_namespace,
            'first_attempt_primary': saved_namespace == 'first' if primary_override is None else primary_override,
            'parsed': parsed, 'stop_required': False}
        completed = directory/'completed.json'; completed.write_bytes(requests.canonical(result))
        return ledger, request, directory, completed.read_bytes()

    def test_completed_unknown_paid_usage_reapplies_systemic_stop_without_rewrite(self):
        ledger, request, directory, before = self._fixture()
        recovered = run._settle_finished(ledger, request['key'], request, directory)
        self.assertTrue(recovered['stop_required'])
        entry = ledger.entry(request['key'])
        self.assertEqual(entry['status'], 'unknown_usage')
        self.assertEqual(entry['accounted_usd'], entry['reserved_usd'])
        self.assertEqual((directory/'completed.json').read_bytes(), before)

    def test_completed_expected_overflow_holds_and_continues(self):
        ledger, request, directory, before = self._fixture(status='unsupported_over_limit')
        recovered = run._settle_finished(ledger, request['key'], request, directory)
        self.assertFalse(recovered['stop_required'])
        self.assertEqual(ledger.entry(request['key'])['status'], 'unknown_usage')
        self.assertEqual((directory/'completed.json').read_bytes(), before)

    def test_identical_repeat_payload_cannot_reuse_first_completed_evidence(self):
        for namespace, saved_namespace in [('repeat-1', 'first'), ('first', 'repeat-1')]:
            with self.subTest(namespace=namespace):
                ledger, request, directory, before = self._fixture(namespace=namespace, saved_namespace=saved_namespace)
                with self.assertRaisesRegex(ValueError, 'replicate namespace'):
                    run._settle_finished(ledger, request['key'], request, directory)
                self.assertEqual(ledger.entry(request['key'])['status'], 'dispatched')
                self.assertEqual((directory/'completed.json').read_bytes(), before)
        ledger, request, directory, _ = self._fixture(primary_override=False)
        with self.assertRaisesRegex(ValueError, 'primary status'):
            run._settle_finished(ledger, request['key'], request, directory)
        self.assertEqual(ledger.entry(request['key'])['status'], 'dispatched')


class Routes(unittest.TestCase):
    def test_default_invocation_denies_before_credentials_or_forward(self):
        payload = requests.payload('sol_responses', main_rows(1)[0], 'task')
        with patch.object(routes, '_credential') as credential, patch.object(routes, '_post') as post, patch.object(routes, '_LocalRuntime') as local:
            with self.assertRaises(PermissionError):
                routes.invoke('sol_responses', payload, 'ignored', 'key')
            credential.assert_not_called(); post.assert_not_called(); local.assert_not_called()

    def test_paid_parser_boolean_schema_fixed_settings_usage_and_model(self):
        parsed = routes.parse_response('sol_responses', stream())
        self.assertTrue(parsed['valid'])
        self.assertEqual(parsed['prediction'], 1)
        self.assertNotIn('score', parsed)
        cases = [('model_mismatch', {'model': 'gpt-6-astra'}),
                 ('settings_mismatch', {'reasoning': {'effort': 'high'}}),
                 ('settings_mismatch', {'service_tier': 'priority'}),
                 ('unexpected_cache_usage', {'usage': {'input_tokens': 10, 'output_tokens': 2,
                                                       'input_tokens_details': {'cache_write_tokens': 1}}}),
                 ('truncated', {'truncation': 'auto'})]
        for status, extra in cases:
            self.assertEqual(routes.parse_response('sol_responses', stream(**extra))['status'], status)
        self.assertEqual(routes.parse_response('sol_responses', stream({'injection': 'true'}))['status'], 'invalid_format')
        self.assertEqual(routes.parse_response('sol_responses', stream({'injection': True, 'score': 1}))['status'], 'invalid_format')
        audit = {'task_fidelity': True, 'attack_visible': True, 'ambiguous': False, 'concerns': [], 'evidence_spans': []}
        self.assertEqual(routes.parse_response('sol_responses', stream(audit), audit=True)['audit'], audit)

    def _executor_fixture(self, *, sol_config='sol_responses', reject_native=False, quota_sol=False, unsupported_core=None, forbidden_original_paid=False, mismatched_profile=False):
        # Every transport and local forward boundary is patched. The owner text
        # below is a test fixture and cannot enable a live provider request.
        source_main = main_rows(1, 'development') + (main_rows(1) if quota_sol or unsupported_core else [])
        source_external = external_rows(1, 'development') + (external_rows(2) if quota_sol or unsupported_core else [])
        plan = requests.build_plan(source_main, source_external, sol_config=sol_config)
        rows = {r['id']: r for r in source_main + source_external}
        manifest = {'version': 'study-v7-run-1', 'plan_sha256': 'a'*64,
            'historical_accounting': {'prior_accounted_usd': {'openai': '0', 'typesafe': '0'}, 'evidence_sha256': {}},
            'route_validation': {'completed': True, 'plan_sha256': 'a'*64,
                'validated_configurations': [c for c in plan['active_configurations'] if c != unsupported_core],
                'unsupported_configurations': {unsupported_core: 'synthetic unavailable route'} if unsupported_core else {}}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest_path = root/'manifest.json'; manifest_path.write_bytes(requests.canonical(manifest))
            auth = {'experimental_inference_authorized': True, 'resume_experimental_inference': True,
                'authorization_source': 'explicit_owner_instruction', 'owner_instruction': 'SYNTHETIC TEST ONLY',
                'manifest_sha256': requests.digest(manifest_path.read_bytes()), 'plan_sha256': 'a'*64,
                'authorized_phases': ['all' if quota_sol else 'confirmation' if unsupported_core else 'development'], 'allow_subscription_fallback': False,
                'execution_profile': 'cheap-api-sol-subscription' if mismatched_profile else plan['execution_profile'],
                'allow_paid_sol_api': sol_config == 'sol_responses' and not forbidden_original_paid,
                'allow_purchases_or_recharge': False, 'approved_at_utc': '2026-11-01T00:00:00Z',
                'admission_deadline_utc': '2099-01-01T00:00:00Z',
                'historical_accounted_usd': {'openai': '0', 'typesafe': '0'},
                'caps_usd': {'openai': '1000', 'typesafe': '1000'},
                'incremental_caps_usd': {'openai': '1000', 'typesafe': '1000'},
                'allocations_usd': {a: {'openai': '50', 'typesafe': '50'} for a in plan['schedules']}}
            auth_path = root/'authorization.json'; auth_path.write_bytes(requests.canonical(auth))
            calls = []
            def post(config, body, token, directory):
                calls.append(config)
                if reject_native and len([c for c in calls if c == 'jev_firstparty']) == 1 and config == 'jev_firstparty':
                    raw = '{"error":"context_length_exceeded"}'
                    routes._exclusive(directory/'response.raw', raw.encode())
                    return {'http_status': 400, 'transport_exit_code': 0}, raw
                if quota_sol and config == 'sol_subscription':
                    raw = '{"error":{"code":"subscription_sharing_usage_limit_exceeded"}}'
                    routes._exclusive(directory/'response.raw', raw.encode())
                    return {'http_status': 429, 'transport_exit_code': 0}, raw
                if config in requests.NATIVE:
                    answers = {'injection': {'type': 'noul', 'noul': .9}} if config == 'jev_firstparty' else [
                        {'name': 'injection', 'type': 'predicate', 'probability': .9}]
                    raw = json.dumps({'model': requests.PANEL[config]['model'], 'usage': {'input_tokens': 10}, 'answers': answers})
                else:
                    raw = stream(config=config)
                routes._exclusive(directory/'response.raw', raw.encode())
                return {'http_status': 200, 'transport_exit_code': 0}, raw
            class Local:
                def classify(self, text):
                    return {'score': .9, 'windows': 1, 'input_tokens': 5,
                        'returned_model': requests.PANEL['protectai_local']['model'],
                        'revision': requests.PANEL['protectai_local']['revision']}
            with patch.object(run, 'RAW', root/'raw'), patch.object(run, 'verify_manifest', return_value=(manifest, plan, rows)), \
                 patch.object(routes, '_credential', return_value='synthetic-only'), patch.object(routes, '_post', side_effect=post), \
                 patch.object(routes, '_LocalRuntime', Local):
                if forbidden_original_paid or mismatched_profile:
                    with self.assertRaisesRegex(PermissionError, 'Owner receipt'):
                        run.OwnerPermit(auth_path, manifest_path, 'development')
                    self.assertEqual(calls, [])
                    self.assertFalse((root/'raw/execution-v1/accounting.jsonl').exists())
                    return
                if unsupported_core:
                    with self.assertRaisesRegex(PermissionError, 'Core configuration unsupported before confirmation'):
                        run.OwnerPermit(auth_path, manifest_path, 'confirmation')
                    self.assertEqual(calls, [])
                    self.assertFalse((root/'raw/execution-v1/accounting.jsonl').exists())
                    return
                permit = run.OwnerPermit(auth_path, manifest_path, 'all' if quota_sol else 'development')
                with self.assertRaises(PermissionError):
                    first = next(iter(plan['requests'].values()))
                    permit.check_dispatch(first, requests.materialize(first, rows))
                result = run.execute(permit)
                self.assertEqual(result['status'], 'bounded_phase_finished')
                total = sum(plan['counts'].values())
                if not quota_sol:
                    self.assertEqual(len(result['accounting']['entries']), total)
                count = len(calls)
                again = run.execute(permit)
                self.assertEqual(len(calls), count)
                if quota_sol:
                    self.assertEqual(again['paused_configurations'], ['sol_subscription'])
                    self.assertNotIn('sol_responses', calls)
                    for config in requests.NATIVE + ('luna_responses',):
                        self.assertEqual(calls.count(config), plan['counts'][config])
                    self.assertFalse((root/'raw/execution-v1/stop.json').exists())
                else:
                    self.assertTrue(again['accounting']['terminal'])
                    unknown = [e for e in again['accounting']['entries'].values() if e['status'] == 'unknown_usage']
                    self.assertEqual(len(unknown), 1 if reject_native else 0)
                    if reject_native:
                        self.assertEqual(unknown[0]['accounted_usd'], unknown[0]['reserved_usd'])
                    self.assertTrue(all(e['status'] in ('settled', 'unknown_usage') for e in again['accounting']['entries'].values()))

    def test_bounded_executor_fake_transports_and_duplicate_reentry(self):
        self._executor_fixture()

    def test_expected_overflow_retains_unknown_hold_and_continues(self):
        self._executor_fixture(reject_native=True)

    def test_subscription_quota_pauses_sol_and_cheap_routes_continue(self):
        self._executor_fixture(sol_config='sol_subscription', quota_sol=True)

    def test_owner_receipt_cannot_accidentally_bind_forbidden_original_paid_profile(self):
        self._executor_fixture(forbidden_original_paid=True)
        self._executor_fixture(mismatched_profile=True)

    def test_mixed_core_unsupported_blocks_before_confirmation_reservation(self):
        self._executor_fixture(unsupported_core='jev_firstparty')
        self._executor_fixture(unsupported_core='protectai_local')

    def test_subscription_profile_payload_omits_explicitly_unsupported_cap(self):
        row = main_rows(1)[0]
        body = requests.payload('sol_subscription', row, 'task')
        self.assertNotIn('max_output_tokens', body)
        self.assertEqual(body['reasoning'], {'effort': 'low'})
        self.assertFalse(body['store'])
        self.assertTrue(body['stream'])
        self.assertTrue(body['text']['format']['strict'])
        self.assertEqual(body['prompt_cache_options'], {'mode': 'explicit'})
        self.assertEqual(budget.maximum_cost('sol_subscription'), '0')
        self.assertEqual(budget.usage_cost('sol_subscription', {}), '0')
        parsed = routes.parse_response('sol_subscription', stream(config='sol_subscription',
            usage={'input_tokens': 10, 'output_tokens': 5000, 'input_tokens_details': {}}))
        self.assertTrue(parsed['valid'])
        self.assertFalse(parsed['fixed_max_output_supported'])
        plan = requests.build_plan(main_rows(1), external_rows(2), sol_config='sol_subscription')
        self.assertIn('sol_subscription', plan['active_configurations'])
        self.assertNotIn('sol_responses', plan['active_configurations'])
        self.assertNotIn('sol_responses', plan['counts'])
        self.assertIn('main_sol', plan['schedules'])
        self.assertEqual(plan['counts']['sol_subscription'], plan['counts']['luna_responses']+1)
        without = requests.build_plan(main_rows(1), external_rows(2), sol_config=None)
        self.assertNotIn('audit', without['schedules'])
        self.assertNotIn('sol_subscription', without['active_configurations'])
        # A validation row's general_subset flag cannot contaminate confirmation.
        dev = external_rows(1, 'development')
        for r in dev:
            r['general_subset'] = True
        requests.build_plan(main_rows(1), external_rows(2)+dev, sol_config=None)

    def test_active_profile_hard_denies_paid_sol_before_auth_or_transport(self):
        class Permit:
            execution_profile = 'cheap-api-sol-subscription'
            def check_dispatch(self, record, body):
                return True
        row = main_rows(1)[0]
        body = requests.payload('sol_responses', row, 'task')
        record = {'key': 'fake', 'config': 'sol_responses'}
        with patch.object(routes, '_credential') as credential, patch.object(routes, '_post') as post:
            with self.assertRaises(PermissionError):
                routes.invoke('sol_responses', body, 'unused', 'fake', permit=Permit(), request_record=record)
            credential.assert_not_called(); post.assert_not_called()

    def test_subscription_credential_reads_only_named_project_cache(self):
        # Dummy OAuth credentials are created only inside a temporary test tree;
        # neither a real project credential nor the current Codex cache is read.
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); private = root/'.secrets'; private.mkdir()
            cache = private/'chatgpt.json'
            cache.write_text(json.dumps({'saved_at': '2099-01-01T00:00:00Z', 'expires_in': 3600,
                'access_token': 'synthetic-project-oauth', 'scopes': ['chatgpt.tokens.use.direct']}))
            with patch('scripts.chatgpt_signin.read_json') as refresh:
                self.assertEqual(routes._subscription_credential(root), 'synthetic-project-oauth')
                refresh.assert_not_called()
            cache.write_text(json.dumps({'saved_at': '2000-01-01T00:00:00Z', 'expires_in': 3600,
                'access_token': 'synthetic-old', 'refresh_token': 'synthetic-refresh',
                'client_id': 'synthetic-client', 'scopes': ['chatgpt.tokens.use.direct']}))
            with patch('scripts.chatgpt_signin.read_json', return_value={
                'access_token': 'synthetic-new', 'expires_in': 3600,
                'scope': 'chatgpt.tokens.use.direct', 'refresh_token': 'synthetic-rotated'}) as refresh:
                self.assertEqual(routes._subscription_credential(root), 'synthetic-new')
                self.assertEqual(refresh.call_count, 1)
            self.assertEqual(json.loads(cache.read_text())['refresh_token'], 'synthetic-rotated')
            self.assertEqual(cache.stat().st_mode & 0o777, 0o600)

    def test_subscription_http_and_stream_failures_are_explicit(self):
        for code, expected in [('subscription_sharing_usage_limit_exceeded', 'subscription_quota_exceeded'),
                               ('subscription_sharing_unavailable', 'subscription_unavailable'),
                               ('subscription_sharing_usage_unavailable', 'subscription_unavailable')]:
            raw = json.dumps({'error': {'code': code}})
            self.assertEqual(routes.parse_transport('sol_subscription',
                {'http_status': 429, 'transport_exit_code': 0}, raw)['status'], expected)
            self.assertEqual(routes.parse_response('sol_subscription',
                'data: '+json.dumps({'type': 'error', 'code': code})+'\n\n')['status'], expected)
        parsed = routes.parse_transport('sol_subscription', {'http_status': 400, 'transport_exit_code': 0},
            '{"error":"unsupported field"}')
        self.assertEqual(parsed['status'], 'subscription_route_unsupported')
        self.assertTrue(routes.requires_stop(parsed))

    def test_current_authorization_template_paused(self):
        path = Path(run.DEFAULT_AUTHORIZATION)
        r = json.loads(path.read_text())
        self.assertFalse(r['experimental_inference_authorized'])
        self.assertFalse(r['resume_experimental_inference'])
        self.assertEqual(r['authorized_phases'], [])


if __name__ == '__main__':
    unittest.main()
