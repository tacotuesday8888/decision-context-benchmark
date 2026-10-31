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


if __name__ == '__main__':
    unittest.main()
