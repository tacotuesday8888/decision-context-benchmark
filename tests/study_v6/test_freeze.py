"""Hermetic source/admission/freeze integration; no corpora, credentials or calls."""
from contextlib import ExitStack
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts.study_v6 import freeze, plan
from scripts.study_v6.common import canonical_bytes, sha256


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, bytes) else canonical_bytes(value) + b'\n'
    path.write_bytes(data)
    return data


def row(identifier, *, group='group', pair='pair', candidate='Complete candidate.', gold=0,
        split='confirmation'):
    return {'id': identifier, 'review_id': 'review-' + identifier, 'source': 'browsesafe',
        'candidate': candidate, 'task': 'Read this complete page.', 'policy': None,
        'setting': 'indirect_tool_content', 'group': group, 'pair_id': pair,
        'split_proposal': split, 'semantic_gold': gold, 'upstream_label': gold,
        'review_eligible': True, 'inference_eligible': False, 'exclusion_reasons': []}


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.receipt = self.root / 'results/study-v6-review-resolution/resolution-final.json'

    def tearDown(self):
        self.temp.cleanup()

    def test_no_final_adjudication_receipt_prevents_any_planning(self):
        with patch.object(freeze, 'ROOT', self.root), patch.object(plan, 'build') as build, \
                patch.object(freeze, 'price_gate') as prices:
            with self.assertRaisesRegex(PermissionError, 'Complete independent adjudication'):
                freeze.prepare()
        build.assert_not_called()
        prices.assert_not_called()

    def test_pending_adjudication_flags_are_not_final_admission(self):
        for complete, adjudicated in ((False, False), (False, True), (True, False)):
            with self.subTest(complete=complete, adjudicated=adjudicated):
                write(self.receipt, {'review_resolution_complete': complete,
                    'adjudication_completed': adjudicated})
                with patch.object(freeze, 'ROOT', self.root), \
                        patch('scripts.study_v6.verify_resolution.verify') as verify:
                    with self.assertRaisesRegex(PermissionError, 'Final review gate pending'):
                        freeze.admission()
                verify.assert_not_called()

    def test_completion_flag_cannot_replace_complete_verified_lock(self):
        write(self.receipt, {'review_resolution_complete': True, 'adjudication_completed': True})
        with patch.object(freeze, 'ROOT', self.root), patch.object(plan, 'build') as build, \
                patch('scripts.study_v6.verify_resolution.verify', side_effect=ValueError('partial lock')) as verify:
            with self.assertRaisesRegex(ValueError, 'partial lock'):
                freeze.prepare()
        verify.assert_called_once_with(require_cache=True, with_adjudication=True)
        build.assert_not_called()

    def test_final_gate_rechecks_raw_resolution_and_plan(self):
        receipt = {'review_resolution_complete': True, 'adjudication_completed': True,
            'review_eligible_rows': 4}
        write(self.receipt, receipt)
        with patch.object(freeze, 'ROOT', self.root), \
                patch('scripts.study_v6.verify_resolution.verify') as verify, \
                patch.object(freeze.subprocess, 'run') as run:
            self.assertEqual(freeze.admission(), receipt)
        verify.assert_called_once_with(require_cache=True, with_adjudication=True)
        self.assertEqual(len(run.call_args_list), 2)
        commands = [c.args[0] for c in run.call_args_list]
        self.assertEqual([Path(c[1]).name for c in commands], ['resolve_review.py', 'resolved_plan.py'])
        for command in commands:
            self.assertEqual(command[-2:], ['--with-adjudication', '--verify'])
        self.assertTrue(all(c.kwargs['check'] for c in run.call_args_list))


class CommitTests(unittest.TestCase):
    def test_only_explicit_amendment_versions_select_current_gate_receipts(self):
        self.assertEqual(freeze.amendment_gates(None),
            ('offline-verification-v3.json', 'prefreeze-audit-v2.json', ()))
        for version, offline, audit, count in (
                ('dev-amendment-v6.0.1', 'offline-verification-v4.json', 'prefreeze-audit-v3.json', 1),
                ('dev-amendment-v6.0.2', 'offline-verification-v5.json', 'prefreeze-audit-v4.json', 2)):
            actual = freeze.amendment_gates({'version': version})
            self.assertEqual(actual[:2], (offline, audit))
            self.assertEqual(len(actual[2]), count)
        with self.assertRaisesRegex(PermissionError, 'Unknown development operational'):
            freeze.amendment_gates({'version': 'unreviewed'})

    def test_uncommitted_scientific_change_or_untracked_file_is_refused(self):
        for process in (subprocess.CompletedProcess([], 0, stdout=b'previous scientific code'),
                subprocess.CompletedProcess([], 128, stdout=b'')):
            with self.subTest(returncode=process.returncode), \
                    patch.object(freeze.subprocess, 'run', return_value=process), \
                    patch.object(freeze.subprocess, 'check_output') as head:
                with self.assertRaisesRegex(PermissionError, 'must be committed'):
                    freeze.committed({'scripts/study_v6/fixture.py': sha256(b'changed scientific code')})
            head.assert_not_called()

    def test_identical_committed_bytes_pin_the_actual_head(self):
        data = b'committed exact scientific bytes\n'
        with patch.object(freeze.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout=data)) as show, \
                patch.object(freeze.subprocess, 'check_output', return_value='fixture-head\n') as head:
            result = freeze.committed({'fixture.py': sha256(data)})
        self.assertEqual(result, 'fixture-head')
        self.assertEqual(show.call_args.args[0], ['git', 'show', 'HEAD:fixture.py'])
        head.assert_called_once()


class CoverageTests(unittest.TestCase):
    def test_pending_coverage_cannot_become_frozen_eligibility(self):
        source = row('development', split='development')
        intended = plan.build([source])
        self.assertTrue(intended['cells'])
        self.assertTrue(all(not c['coverage_supported'] and not c['inference_eligible']
            for c in intended['cells']))

        def pending(config, request, **kwargs):
            # Even an internally inconsistent supported flag cannot override the
            # explicit pending disposition at the freeze preparation boundary.
            return {'supported': True, 'coverage_status': 'pending_native_coverage',
                'payload_sha256': sha256(canonical_bytes(request))}

        def read(path):
            return [source] if Path(path).name == 'resolved.jsonl' else []

        with patch.object(freeze, 'admission', return_value={'review_eligible_rows': 1}), \
                patch.object(freeze, 'price_gate'), patch.object(freeze, 'read', side_effect=read), \
                patch('scripts.study_v6.grouping_gate.finalize', return_value=([source], {'fixture': 'synthetic'})), \
                patch.object(plan, 'load_review_subgroups', return_value={}), \
                patch.object(freeze.routes, 'coverage', side_effect=pending), \
                patch.object(freeze, 'immutable') as save:
            with self.assertRaisesRegex(PermissionError, 'coverage remains pending'):
                freeze.prepare()
        save.assert_not_called()

    def test_shared_payload_survives_only_for_covered_references(self):
        rows = [row('a0', group='A', pair='A', candidate='Shared benign page.'),
            row('a1', group='A', pair='A', candidate='Attack A.', gold=1),
            row('b0', group='B', pair='B', candidate='Shared benign page.'),
            row('b1', group='B', pair='B', candidate='Over-limit attack B.', gold=1)]
        coverage = {(r['id'], config, condition): {'status': 'complete'}
            for r in rows for config in plan.CONFIGS
            for condition in ('candidate', 'format', 'task', 'reminder', 'length', 'scrambled')}
        coverage[('b1', 'jev_firstparty', 'length')] = {'status': 'unsupported_over_limit'}
        intended = plan.build(rows, coverage)
        groups = {g['group']: g for g in intended['schedules']['main']}
        self.assertTrue(groups['A']['all_requests_supported'])
        self.assertFalse(groups['B']['all_requests_supported'])
        shared = next(q for q in intended['requests'] if q['config'] == 'jev_firstparty' and
            q['allocation'] == 'main' and {r['id'] for r in q['refs']} == {'a0', 'b0'})
        self.assertTrue(shared['coverage_supported'])
        by_id = {c['id']: c for c in intended['cells'] if c['request_key'] == shared['key']}
        self.assertTrue(by_id['a0']['coverage_supported'])
        self.assertFalse(by_id['b0']['coverage_supported'])
        self.assertTrue(all(not c['inference_eligible'] for c in intended['cells']))


class JournalPrefixTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.dest = self.root / 'data/raw/study-v6/execution-v1'
        self.results = self.root / 'results/study-v6-execution'
        self.hashes = {'scientific-fixture': 'unchanged'}
        self.prefix = b'{"fixture":"historical reservation"}\n'
        dev = write(self.results / 'development-freeze-v1.json', {'fixture': 'development freeze'})
        write(self.dest / 'inherited-accounting.json', {'fixture': 'history'})
        write(self.dest / 'confirmation-frozen-plan.json', {'fixture': 'immutable intended cells'})
        write(self.dest / 'budget.jsonl', self.prefix)
        self.frozen = {'scientific_hashes': self.hashes, 'evidence': {},
            'raw_plan': str((self.dest / 'confirmation-frozen-plan.json').relative_to(self.root)),
            'development_freeze_sha256': sha256(dev), 'development': {'first_attempt_records': []},
            'ledger_before_confirmation_bytes': len(self.prefix),
            'ledger_before_confirmation_sha256': sha256(self.prefix)}
        write(self.results / 'confirmation-freeze-v1.json', self.frozen)
        self.patches = ExitStack()
        self.patches.enter_context(patch.object(freeze, 'ROOT', self.root))
        self.patches.enter_context(patch.object(plan, 'DEST', self.dest))
        self.patches.enter_context(patch.object(plan, 'RESULTS', self.results))
        self.patches.enter_context(patch.object(freeze, 'scientific_hashes', return_value=self.hashes))
        self.history_check = self.patches.enter_context(patch.object(freeze, 'verify_history'))

    def tearDown(self):
        self.patches.close()
        self.temp.cleanup()

    def test_append_only_activity_preserves_frozen_prefix(self):
        with (self.dest / 'budget.jsonl').open('ab') as stream:
            stream.write(b'{"fixture":"later settled usage"}\n')
        frozen, raw_plan = freeze.verify('confirmation', require_committed=False)
        self.assertEqual(frozen, self.frozen)
        self.assertEqual(raw_plan, {'fixture': 'immutable intended cells'})
        self.history_check.assert_called_once()

    def test_truncation_or_modification_of_pre_confirmation_journal_is_refused(self):
        for changed in (self.prefix[:-1], b'X' + self.prefix[1:], b''):
            with self.subTest(changed_bytes=len(changed)):
                write(self.dest / 'budget.jsonl', changed)
                with self.assertRaisesRegex(ValueError, 'journal prefix changed or was truncated'):
                    freeze.verify('confirmation', require_committed=False)

    def test_changed_scientific_hash_stops_before_ledger_readiness(self):
        with patch.object(freeze, 'scientific_hashes', return_value={'scientific-fixture': 'changed'}):
            with self.assertRaisesRegex(PermissionError, 'scientific code/specification changed'):
                freeze.verify('confirmation', require_committed=False)
        self.history_check.assert_not_called()

    def test_development_amendment_accepts_only_its_exact_replacement_hashes(self):
        original = {'scientific_hashes': {'old.py': 'old'}, 'evidence': {},
            'raw_plan': str((self.dest / 'development-frozen-plan.json').relative_to(self.root))}
        original_bytes = write(self.results / 'development-freeze-v1.json', original)
        write(self.dest / 'development-frozen-plan.json', {'fixture': 'original requests'})
        current = {'old.py': 'new', 'amendment.py': 'added'}
        amendment = {'replacement_hashes': dict(current)}
        with patch.object(freeze, 'scientific_hashes', return_value=current), \
                patch.object(freeze, 'development_amendment', return_value=amendment):
            receipt, raw = freeze.verify('development', require_committed=False)
        self.assertEqual(receipt, original)
        self.assertEqual(raw, {'fixture': 'original requests'})
        self.assertEqual((self.results / 'development-freeze-v1.json').read_bytes(), original_bytes)
        amendment['replacement_hashes'].pop('amendment.py')
        with patch.object(freeze, 'scientific_hashes', return_value=current), \
                patch.object(freeze, 'development_amendment', return_value=amendment):
            with self.assertRaisesRegex(PermissionError, 'scientific code/specification changed'):
                freeze.verify('development', require_committed=False)

    def test_confirmation_pins_the_separate_amendment_receipt(self):
        path = self.results / 'development-amendment-v6.0.1.json'
        write(path, {'fixture': 'exact committed amendment'})
        self.frozen['development_amendment_sha256'] = sha256(path.read_bytes())
        write(self.results / 'confirmation-freeze-v1.json', self.frozen)
        with patch.object(freeze, 'development_amendment', return_value={'fixture': 'verified'}):
            freeze.verify('confirmation', require_committed=False)
        write(path, {'fixture': 'changed amendment'})
        with self.assertRaisesRegex(ValueError, 'operational amendment changed'):
            freeze.verify('confirmation', require_committed=False)

    def test_confirmation_pins_latest_explicit_lineage_and_rejects_unknown_receipt(self):
        name = 'development-amendment-v6.0.2.json'
        path = self.results / name
        write(path, {'fixture': 'exact child amendment'})
        self.frozen.update(development_amendment_file=name,
            development_amendment_sha256=sha256(path.read_bytes()))
        write(self.results / 'confirmation-freeze-v1.json', self.frozen)
        with patch.object(freeze, 'development_amendment', return_value={'fixture': 'verified chain'}):
            freeze.verify('confirmation', require_committed=False)
        self.frozen['development_amendment_file'] = '../unreviewed.json'
        write(self.results / 'confirmation-freeze-v1.json', self.frozen)
        with self.assertRaisesRegex(PermissionError, 'Unknown pinned development'):
            freeze.verify('confirmation', require_committed=False)


class SetupTests(unittest.TestCase):
    def inputs(self):
        access = {'inference_calls': 0, 'providers': {p: {'authentication_verified': True,
            'luna_catalog_seen': True, 'astra_catalog_seen': True}
            for p in ('openai_api', 'typesafe_api', 'openai_subscription')}}
        local = {'runtime': '0.40.13', 'model': {'digest': freeze.routes.PANEL['nimble_local']['revision']}}
        return access, local

    def test_metadata_and_authentication_are_not_inference_access(self):
        access, local = self.inputs()
        with patch.object(freeze, 'load', side_effect=[access, local]):
            result = freeze.setup_gate()
        self.assertTrue(result['authentication_verified_without_inference'])
        self.assertTrue(result['native_decision_access_requires_development'])

    def test_missing_authentication_blocks_freeze(self):
        access, _ = self.inputs()
        access['providers']['openai_api']['authentication_verified'] = False
        with patch.object(freeze, 'load', return_value=access):
            with self.assertRaises(PermissionError):
                freeze.setup_gate()

    def test_changed_native_weights_block_freeze(self):
        access, local = self.inputs()
        local['model']['digest'] = 'changed'
        with patch.object(freeze, 'load', side_effect=[access, local]):
            with self.assertRaises(PermissionError):
                freeze.setup_gate()

    def test_prefreeze_audit_requires_no_output_exposure_and_complete_checks(self):
        for values in ({'checks_passed': False, 'new_model_calls': 0, 'model_outputs_inspected': False},
                       {'checks_passed': True, 'new_model_calls': 1, 'model_outputs_inspected': False},
                       {'checks_passed': True, 'new_model_calls': 0, 'model_outputs_inspected': True}):
            with patch.object(freeze, 'development_amendment', return_value=None), \
                    patch.object(freeze, 'load', return_value=values):
                with self.assertRaises(PermissionError):
                    freeze.prefreeze_audit_gate()


class DevelopmentOperationalTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.dest = self.root / 'raw'
        self.enterContext(patch.object(freeze, 'ROOT', self.root))
        self.enterContext(patch.object(plan, 'DEST', self.dest))
        self.requests = []
        for config in plan.CONFIGS:
            self.add(config, config, 'ok')

    def add(self, key, config, status):
        request = {'key': key, 'config': config, 'split': 'development',
                   'coverage_supported': True, 'request_sha256': 'a' * 64,
                   'semantic_gold': 1}
        result = {'request_sha256': request['request_sha256'],
                  'parsed': {'status': status, 'valid': status == 'ok',
                             'prediction': 0 if status == 'ok' else None,
                             'usage': {'input_tokens': 100}}}
        write(self.dest / 'attempts' / key / 'execution-record.json', {'result': result})
        write(self.dest / 'attempts' / key / 'completed.json', result)
        self.requests.append(request)

    def test_operational_success_does_not_optimize_or_require_correct_answers(self):
        result = freeze.development_operational_gate({'requests': self.requests})
        self.assertEqual(result['successful_configuration_count'], 7)
        self.assertEqual(len(result['first_attempt_records']), 7)
        self.assertTrue(result['correctness_not_used'])

    def test_no_supported_interface_success_for_one_configuration_blocks_confirmation(self):
        self.requests[-1]['coverage_supported'] = False
        with self.assertRaisesRegex(PermissionError, 'Every retained configuration'):
            freeze.development_operational_gate({'requests': self.requests})

    def test_reviewed_transient_failure_stays_frozen_with_other_interface_successes(self):
        self.add('failed', 'luna_decisions', 'http_error')
        with patch('scripts.study_v6.accounting.BudgetLedger') as ledger, \
                patch('scripts.study_v6.development_amendment.approved_failure', return_value=False), \
                patch('scripts.study_v6.continuations.approved_failure', return_value=True):
            ledger.return_value.snapshot.return_value = {'continuations': {}}
            result = freeze.development_operational_gate({'requests': self.requests})
        self.assertEqual(result['reviewed_transient_failures'], 1)
        self.assertEqual(len(result['first_attempt_records']), 8)
        self.assertFalse(result['failed_requests_resent'])

    def test_development_capacity_amendment_is_separate_from_transient_failure(self):
        self.add('capacity', 'nimble_local', 'http_error')
        with patch('scripts.study_v6.accounting.BudgetLedger') as ledger, \
                patch('scripts.study_v6.development_amendment.approved_failure', return_value=True), \
                patch('scripts.study_v6.continuations.approved_failure') as transient:
            ledger.return_value.snapshot.return_value = {'continuations': {}, 'development_amendments': {}}
            result = freeze.development_operational_gate({'requests': self.requests})
        transient.assert_not_called()
        self.assertEqual(result['reviewed_transient_failures'], 0)
        self.assertEqual(result['reviewed_development_capacity_failures'], 1)
        self.assertEqual(result['successful_configuration_count'], 7)
        self.assertFalse(result['failed_requests_resent'])

    def test_case_refusal_is_retained_without_accuracy_or_prompt_optimization(self):
        self.add('refused', 'astra_chat', 'refusal')
        result = freeze.development_operational_gate({'requests': self.requests})
        self.assertEqual(result['retained_case_failures'], 1)
        self.assertEqual(result['successful_configuration_count'], 7)
        self.assertEqual(len(result['first_attempt_records']), 8)

    def test_prefreeze_audit_binds_actual_payload_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'plan.json'
            path.write_bytes(b'exact bytes')
            receipt = {'checks_passed': True, 'new_model_calls': 0, 'model_outputs_inspected': False,
                       'inputs': {'plan': {'path': 'plan.json', 'sha256': sha256(path.read_bytes())}}}
            with patch.object(freeze, 'ROOT', Path(directory)), \
                    patch.object(freeze, 'development_amendment', return_value=None), \
                    patch.object(freeze, 'load', return_value=receipt):
                self.assertEqual(freeze.prefreeze_audit_gate(), receipt)
                path.write_bytes(b'changed bytes')
                with self.assertRaises(ValueError):
                    freeze.prefreeze_audit_gate()


if __name__ == '__main__':
    unittest.main()
