"""Narrow pre-confirmation capacity lineage; synthetic files only, no inference."""
import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.study_v5.prompts import native_payload
from scripts.study_v6 import development_amendment as a, routes, plan
from scripts.study_v6.accounting import BudgetLedger, NIMBLE_LEGACY_CAPACITY_BODY
from scripts.study_v6.common import canonical_bytes, sha256
from scripts.study_v6.evidence import exclusive, immutable, load


class DevelopmentAmendmentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'data/raw/study-v6/execution-v1'
        self.results = self.root / 'results/study-v6-execution'
        self.directory.mkdir(parents=True)
        self.results.mkdir(parents=True)
        for name, value in (('EXPECTED_REQUESTS', 3), ('EXPECTED_PRESERVED_ATTEMPTS', 2), ('EXPECTED_REMAINING_REQUESTS', 1)):
            p = patch.object(a, name, value);p.start();self.addCleanup(p.stop)
        subprocess.run(['git', 'init', '-q'], cwd=self.root, check=True, capture_output=True)
        self.old = {}
        for relative in ('scripts/study_v5/prompts.py', 'scripts/study_v6/routes.py', 'scripts/study_v6/run.py'):
            path = self.root / relative;path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('original:' + relative)
            self.old[relative] = sha256(path.read_bytes())
        self.commit('Original scientific source')
        old_head = self.head()
        self.ledger = BudgetLedger(self.directory / 'budget.jsonl', {
            'prior_accounted_usd': {'openai': '0', 'typesafe': '0'},
            'provider_caps_usd': {'openai': '15', 'typesafe': '20'}, 'evidence_sha256': {}})
        self.requests = []
        for index, candidate in enumerate(('ordinary content', 'x' * 70_000, 'remaining content')):
            row = {'candidate': candidate, 'task': 'Summarize.', 'policy': None,
                   'source': 'browsesafe', 'setting': 'indirect_tool_content'}
            payload = native_payload(row, 'task', 'nimble_local')
            digest = sha256(canonical_bytes(payload))
            key = sha256(canonical_bytes([plan.VERSION, 'development', 'nimble_local', digest]))
            self.requests.append({'key': key, 'config': 'nimble_local', 'provider': None,
                'split': 'development', 'allocation': 'development', 'batch': 'development:fixture',
                'payload': payload, 'request_sha256': digest, 'reserved_usd': '0',
                'inference_eligible': True, 'coverage_supported': True, 'refs': []})
        self.frozen = {'split': 'development', 'requests': self.requests, 'cells': [], 'schedules': {}}
        immutable(self.directory / 'development-frozen-plan.json', self.frozen)
        immutable(self.directory / 'intended-plan.json', {'requests': self.requests, 'cells': [], 'schedules': {}})
        self.base = {'split': 'development', 'code_commit': old_head,
            'scientific_hashes': self.old, 'raw_plan': self.relative(self.directory / 'development-frozen-plan.json'),
            'evidence': {self.relative(p): sha256(p.read_bytes()) for p in
                (self.directory / 'development-frozen-plan.json', self.directory / 'intended-plan.json')}}
        immutable(self.results / 'development-freeze-v1.json', self.base)
        self.retain(self.requests[0], failed=False)
        self.retain(self.requests[1], failed=True)
        self.failed, self.remaining = self.requests[1], self.requests[2]
        exclusive(self.directory / 'STOP.json', {'reason': 'Preserved first-attempt route failure',
                                               'request_key': self.failed['key']})
        self.current = dict(self.old)
        for relative in ('scripts/study_v6/routes.py', *sorted(a.ADDITIONS)):
            path = self.root / relative;path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text('operational revision:' + relative)
            self.current[relative] = sha256(path.read_bytes())
        doc = self.root / 'docs/study-v6-execution/AMENDMENT-v6.0.1.md'
        doc.parent.mkdir(parents=True, exist_ok=True);doc.write_text('Fixture explicit capacity amendment.')
        self.binary = self.root / 'fixture-pinned-native-binary'
        self.binary.write_bytes(b'fixture pinned native binary')
        self.static = self.directory / 'amendment-byte-limit-evidence-v1'
        self.static.mkdir()
        (self.static / 'static-disassembly.txt').write_text('Fixture static inspection only.')
        immutable(self.static / 'static-reconstruction.json', {'schema': 'nimble-native-byte-limit-static-v1',
            'binary': {'real_path': str(self.binary), 'sha256': sha256(self.binary.read_bytes()),
                       'bytes': self.binary.stat().st_size}})
        immutable(self.static / 'plan-capacity-counts.json', {'fixture_only': True})
        for name, value in (('TRUSTED_BINARY', self.binary), ('TRUSTED_BINARY_SHA256', sha256(self.binary.read_bytes())),
                            ('TRUSTED_BINARY_BYTES', self.binary.stat().st_size),
                            ('STATIC_FILES', {p.name: sha256(p.read_bytes()) for p in self.static.iterdir()})):
            p = patch.object(a, name, value);p.start();self.addCleanup(p.stop)
        p = patch.object(a, '_hashes', lambda root: self.current);p.start();self.addCleanup(p.stop)
        self.gates()
        self.commit('Commit exact operational code and independent gate fixtures')

    def relative(self, path):
        return str(path.relative_to(self.root))

    def head(self):
        return subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=self.root, text=True).strip()

    def commit(self, message):
        subprocess.run(['git', 'add', '.'], cwd=self.root, check=True, capture_output=True)
        subprocess.run(['git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-qm', message], cwd=self.root, check=True, capture_output=True)

    def gates(self):
        (self.results / 'offline-verification-v4.json').write_bytes(canonical_bytes({
            'checks_passed': True, 'scientific_hashes': self.current}) + b'\n')
        (self.results / 'prefreeze-audit-v3.json').write_bytes(canonical_bytes({
            'checks_passed': True, 'new_model_calls': 0, 'model_outputs_inspected': False,
            'checks': {'exact_payloads': True}, 'inputs': {'intended_plan': {
                'path': self.relative(self.directory / 'intended-plan.json'),
                'sha256': sha256((self.directory / 'intended-plan.json').read_bytes())}}}) + b'\n')

    def retain(self, request, *, failed):
        spec = {k: request[k] for k in ('key', 'provider', 'reserved_usd', 'request_sha256', 'config', 'split')}
        self.ledger.reserve_batch('development:request:' + request['key'], 'development', [spec])
        self.ledger.mark_dispatched(request['key'])
        folder = self.directory / 'attempts' / request['key']
        exclusive(folder / 'request.json', canonical_bytes(request['payload']))
        exclusive(folder / 'started.json', {'config': 'nimble_local', 'attempt_key': request['key'],
            'payload_sha256': request['request_sha256'], 'route': 'local'})
        native = {'model': 'nimble:9b-q4_K_M', 'answers': {'injection': {'type': 'noul', 'noul': .8}},
                  'usage': {'input_tokens': 100}}
        body = NIMBLE_LEGACY_CAPACITY_BODY if failed else canonical_bytes(native)
        exclusive(folder / 'response.raw', body)
        exclusive(folder / 'response.partial', body)
        http = 413 if failed else 200
        exclusive(folder / 'response-headers.partial', f'HTTP/1.1 {http}\r\n\r\n'.encode())
        parsed = {'status': 'http_error', 'valid': False, 'prediction': None} if failed else routes.parse_response('nimble_local', native)
        result = {'request_sha256': request['request_sha256'], 'parsed': parsed, 'stop_required': failed,
            'attempt_key': request['key'], 'access_route': 'local', 'paid_request': False,
            'observation': {'http_status': http, 'transport_exit_code': 0},
            'raw_hashes': {p.name: sha256(p.read_bytes()) for p in folder.iterdir()}}
        exclusive(folder / 'completed.json', result)
        costs = {'accounted_usd': '0', 'actual_billed_usd': None,
                 'basis': 'Existing subscription/local route; zero incremental metered API charge'}
        record = {'version': plan.VERSION, 'attempt': 0, 'first_attempt_primary': True,
            **{k: request[k] for k in ('key', 'config', 'split', 'allocation', 'batch', 'request_sha256', 'reserved_usd')},
            'charged_allocation': 'development', 'result': result, 'costs': costs}
        exclusive(folder / 'execution-record.json', record)
        self.ledger.settle(request['key'], '0', evidence_sha256=sha256((folder / 'execution-record.json').read_bytes()))

    def prepare(self):
        return a.prepare(project_root=self.root, directory=self.directory, current_hashes=self.current, now_epoch=1000)

    def verify(self, **kwargs):
        return a.verify(project_root=self.root, directory=self.directory, current_hashes=self.current, **kwargs)

    def activate(self, **kwargs):
        return a.activate(directory=self.directory, project_root=self.root, now_epoch=1000, **kwargs)

    def test_prepare_is_inert_exact_scope_and_tracked_receipt_is_sanitized(self):
        before = (self.directory / 'budget.jsonl').read_bytes()
        prepared = self.prepare()
        self.assertEqual((self.directory / 'budget.jsonl').read_bytes(), before)
        self.assertTrue((self.directory / 'STOP.json').exists())
        manifest = load(prepared['manifest_path'])
        self.assertEqual(manifest['remaining_request_keys'], [self.remaining['key']])
        self.assertNotIn(self.failed['key'], manifest['remaining_request_keys'])
        self.assertEqual(len(manifest['preserved_attempts']), 2)
        receipt = load(prepared['receipt_path'])
        self.assertNotIn(self.failed['key'], json.dumps(receipt))
        self.assertNotIn('remaining_request_keys', receipt)
        self.assertTrue(receipt['original_http_error_preserved'])
        self.assertFalse(receipt['failed_key_retried'])
        with self.assertRaisesRegex(a.AmendmentError, 'committed'):
            self.verify()
        self.assertEqual(self.verify(require_committed=False)['version'], a.VERSION)

    def test_activation_requires_commit_journals_then_archives_and_is_idempotent(self):
        self.prepare()
        with self.assertRaisesRegex(a.AmendmentError, 'committed'):
            self.activate()
        self.commit('Approve exact sanitized operational amendment')
        before = self.ledger.snapshot()
        result = self.activate()
        after = self.ledger.snapshot()
        self.assertTrue(result['activated'])
        self.assertFalse((self.directory / 'STOP.json').exists())
        self.assertEqual(before['entries'], after['entries'])
        self.assertEqual(before['all_in_accounted_usd'], after['all_in_accounted_usd'])
        self.assertEqual(before['policy'], after['policy'])
        self.assertTrue(a.approved_failure(self.failed['key'], self.ledger, self.directory, self.root))
        self.assertFalse(a.approved_failure(self.remaining['key'], self.ledger, self.directory, self.root))
        journal = (self.directory / 'budget.jsonl').read_bytes()
        self.activate()
        self.assertEqual((self.directory / 'budget.jsonl').read_bytes(), journal)
        self.assertEqual(load(self.directory / 'attempts' / self.failed['key'] / 'execution-record.json')['result']['parsed']['status'], 'http_error')

    def test_crash_after_journaling_retains_stop_and_finishes_without_second_event(self):
        self.prepare();self.commit('Approve exact amendment')
        with self.assertRaisesRegex(RuntimeError, 'fixture crash'):
            self.activate(after_journal=lambda: (_ for _ in ()).throw(RuntimeError('fixture crash')))
        self.assertTrue((self.directory / 'STOP.json').exists())
        journal = (self.directory / 'budget.jsonl').read_bytes()
        self.activate()
        self.assertEqual((self.directory / 'budget.jsonl').read_bytes(), journal)
        self.assertFalse((self.directory / 'STOP.json').exists())

    def test_unauthorized_scientific_change_and_postconfirmation_prepare_fail(self):
        changed = dict(self.current)
        changed['scripts/study_v5/prompts.py'] = 'f' * 64
        with self.assertRaisesRegex(a.AmendmentError, 'allowlist'):
            a.prepare(project_root=self.root, directory=self.directory, current_hashes=changed)
        immutable(self.results / 'confirmation-freeze-v1.json', {'fixture': True})
        with self.assertRaisesRegex(a.AmendmentError, 'precede'):
            self.prepare()

    def test_original_body_raw_inventory_prefix_and_binary_mutation_are_rejected(self):
        prepared = self.prepare();self.commit('Approve exact amendment')
        response = self.directory / 'attempts' / self.failed['key'] / 'response.raw'
        original = response.read_bytes();response.write_bytes(original + b' ')
        with self.assertRaises(a.AmendmentError):
            self.verify()
        response.write_bytes(original)
        extra = response.parent / 'second-response.raw';extra.write_bytes(b'unplanned')
        with self.assertRaises(Exception):
            self.verify()
        extra.unlink()
        old_binary = self.binary.read_bytes();self.binary.write_bytes(b'changed')
        with self.assertRaisesRegex(a.AmendmentError, 'binary changed'):
            self.verify()
        self.binary.write_bytes(old_binary)
        manifest = load(prepared['manifest_path'])
        manifest['remaining_request_keys'] = [self.failed['key']]
        Path(prepared['manifest_path']).write_bytes(canonical_bytes(manifest) + b'\n')
        with self.assertRaisesRegex(a.AmendmentError, 'receipt differs'):
            self.verify()

    def test_none_when_absent_and_incomplete_pair_fails_closed(self):
        self.assertIsNone(self.verify())
        exclusive(self.directory / a.BASENAME, {'version': a.VERSION})
        with self.assertRaisesRegex(a.AmendmentError, 'Incomplete'):
            self.verify()


class ProspectiveCoverageTests(unittest.TestCase):
    def test_only_nimble_confirmation_coverage_changes_and_pair_closure_is_complete(self):
        from scripts.study_v6.development_amendment import apply_confirmation_coverage
        requests, cells, schedules = [], [], {'comparators': [], 'development': []}
        for split in ('development', 'confirmation'):
            for config in ('nimble_local', 'luna_chat'):
                batch = split + ':' + config
                keys = []
                for identity, gold, candidate in (('negative', 0, 'ordinary'), ('positive', 1, 'x' * 70_000)):
                    row = {'candidate': candidate, 'task': 'Summarize.', 'policy': None,
                           'source': 'browsesafe', 'setting': 'indirect_tool_content'}
                    payload = native_payload(row, 'task', config)
                    key = sha256(canonical_bytes([split, config, identity]))
                    keys.append(key)
                    requests.append({'key': key, 'config': config, 'split': split,
                        'payload': payload, 'coverage_supported': True, 'refs': []})
                    cells.append({'id': identity, 'source': 'browsesafe', 'pair_id': 'paired', 'group': 'g',
                        'gold': gold, 'split': split, 'config': config, 'condition': 'task',
                        'allocation': 'comparators' if split == 'confirmation' else 'development',
                        'batch': batch, 'request_key': key, 'coverage_supported': True,
                        'coverage_status': 'full_input_server_gate'})
                schedules['comparators' if split == 'confirmation' else 'development'].append({
                    'batch': batch, 'request_keys': keys, 'all_requests_supported': True})
        intended = {'requests': requests, 'cells': cells, 'schedules': schedules}
        before = copy.deepcopy(intended)
        updated = apply_confirmation_coverage(intended)
        self.assertEqual(intended, before)
        self.assertEqual(len(updated['requests']), len(before['requests']))
        for old, new in zip(before['requests'], updated['requests']):
            self.assertEqual({k: v for k, v in old.items() if k != 'coverage_supported'},
                             {k: v for k, v in new.items() if k != 'coverage_supported'})
        for old, new in zip(before['cells'], updated['cells']):
            if old['split'] == 'confirmation' and old['config'] == 'nimble_local':
                self.assertFalse(new['coverage_supported'])
                self.assertFalse(new['native_byte_coverage']['preflight_native_token_count'])
            else:
                self.assertEqual(old, new)
        self.assertEqual(updated['cells'][4]['coverage_status'], 'unsupported_paired_native_byte_limit')
        self.assertEqual(updated['cells'][5]['coverage_status'], 'unsupported_native_byte_limit')
        self.assertEqual([g['request_keys'] for g in before['schedules']['comparators']],
                         [g['request_keys'] for g in updated['schedules']['comparators']])


if __name__ == '__main__':
    unittest.main()
