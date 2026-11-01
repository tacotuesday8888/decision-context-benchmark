"""Complete grouping-observation accounting and monotone execution quarantine."""
from contextlib import ExitStack
import copy
import csv
import io
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.study_v6 import grouping_gate as gate
from scripts.study_v6.common import canonical_bytes, sha256
from scripts.study_v6.evidence import load


def row(rid, group, *, reviewed=True, gold=0, source='browsesafe'):
    return {'id': 'source-' + rid, 'review_id': rid, 'group': group,
        'source': source, 'candidate': 'Exact original candidate\n', 'task': 'Exact task.',
        'policy': None, 'setting': 'indirect_tool_content', 'split_proposal': 'confirmation',
        'review_eligible': reviewed, 'semantic_gold': gold if reviewed else None,
        'inference_eligible': False, 'exclusion_reasons': [] if reviewed else ['original_quarantine']}


def fixture():
    rows = [row('rev-a', 'G1'), row('rev-partner', 'G1', gold=1),
        row('rev-b', 'G2', gold=1), row('rev-c', 'G3', source='nvidia'),
        row('rev-d', 'G4', reviewed=False), row('rev-e', 'G5')]
    bcsv = [{'review_id': 'rev-a', 'group_merge_ids': 'rev-b'},
        {'review_id': 'rev-b', 'group_merge_ids': ''}, {'review_id': 'rev-c', 'group_merge_ids': ''}]
    sidecar = {'kind': 'packet_only_grouping_proposals', 'certified': False,
        'unique_pair_count': 2, 'pairs': [['rev-a', 'rev-b'], ['rev-b', 'rev-c']],
        'observations': [
            {'source': 'reviewer-B.csv', 'review_id': 'rev-a', 'group_merge_ids': ['rev-b']},
            {'source': 'root-log.jsonl', 'record': {'review_ids': ['rev-b', 'rev-a'], 'reason': 'Related page'}},
            {'source': 'worker-log.jsonl', 'record': {'ids': ['rev-b', 'rev-c'], 'reason': 'Sidecar only'}}]}
    return rows, sidecar, bcsv


class ApplicationTests(unittest.TestCase):
    def test_every_endpoint_component_and_partner_quarantined_without_relabeling(self):
        rows, sidecar, bcsv = fixture()
        original = copy.deepcopy(rows)
        derived, aggregate, raw = gate.apply(rows, sidecar, bcsv)
        self.assertEqual(rows, original)
        for before, after in zip(rows, derived):
            self.assertEqual({k: after[k] for k in before}, before)
            self.assertEqual(set(after)-set(before), {'execution_group_eligible', 'execution_exclusion_reasons'})
        by_review = {r['review_id']: r for r in derived}
        for rid in ('rev-a', 'rev-partner', 'rev-b', 'rev-c'):
            self.assertFalse(by_review[rid]['execution_group_eligible'])
            self.assertEqual(by_review[rid]['execution_exclusion_reasons'], [gate.REASON])
        self.assertTrue(by_review['rev-e']['execution_group_eligible'])
        self.assertFalse(by_review['rev-d']['review_eligible'])
        self.assertIsNone(by_review['rev-d']['semantic_gold'])
        self.assertEqual((aggregate['csv_unique_pairs'], aggregate['sidecar_only_pairs']), (1, 1))
        self.assertEqual((aggregate['held_final_components'], aggregate['execution_admitted_rows']), (3, 1))
        self.assertEqual(aggregate['newly_execution_excluded_review_eligible_rows'], 4)
        self.assertEqual(aggregate['review_quarantined_rows_preserved'], 1)
        self.assertEqual(raw['pairs'][0]['observation_count'], 2)
        self.assertTrue(all(not r['inference_eligible'] for r in derived))

    def test_preexisting_exclusions_stay_separate_from_new_attrition(self):
        rows, sidecar, bcsv = fixture()
        rows[3] = row('rev-c', 'G3', reviewed=False, source='nvidia')
        derived, aggregate, _ = gate.apply(rows, sidecar, bcsv)
        self.assertEqual(aggregate['source_counts']['nvidia']['review_quarantined_rows_preserved'], 1)
        self.assertEqual(aggregate['source_counts']['nvidia']['newly_execution_excluded_review_eligible_rows'], 0)
        self.assertEqual(aggregate['newly_execution_excluded_review_eligible_rows'], 3)
        self.assertFalse(derived[3]['review_eligible'])
        self.assertFalse(derived[3]['execution_group_eligible'])
        self.assertIsNone(derived[3]['semantic_gold'])

    def test_duplicate_self_unknown_and_unobserved_pairs_fail_closed(self):
        for change in ('duplicate', 'self', 'unknown', 'missing_observation'):
            rows, sidecar, bcsv = fixture()
            if change == 'duplicate':
                sidecar['pairs'].append(['rev-b', 'rev-a'])
            elif change == 'self':
                sidecar['pairs'][0] = ['rev-a', 'rev-a']
            elif change == 'unknown':
                sidecar['pairs'][0] = ['rev-a', 'unknown']
            else:
                sidecar['observations'].pop()
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.apply(rows, sidecar, bcsv)

    def test_csv_must_be_unique_known_and_fully_represented(self):
        for change in ('duplicate_row', 'duplicate_target', 'unknown_target', 'self', 'unlisted_link', 'observation_drift'):
            rows, sidecar, bcsv = fixture()
            if change == 'duplicate_row': bcsv.append(dict(bcsv[0]))
            elif change == 'duplicate_target': bcsv[0]['group_merge_ids'] = 'rev-b;rev-b'
            elif change == 'unknown_target': bcsv[0]['group_merge_ids'] = 'unknown'
            elif change == 'self': bcsv[0]['group_merge_ids'] = 'rev-a'
            elif change == 'unlisted_link': bcsv[0]['group_merge_ids'] = 'rev-e'
            else: sidecar['observations'][0]['group_merge_ids'] = ['rev-c']
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.apply(rows, sidecar, bcsv)

    def test_observation_schemas_and_exact_duplicates_validated(self):
        for change in ('duplicate', 'missing_ids', 'both_id_keys', 'self', 'unknown', 'ambiguous_schema'):
            rows, sidecar, bcsv = fixture()
            if change == 'duplicate': sidecar['observations'].append(copy.deepcopy(sidecar['observations'][1]))
            elif change == 'missing_ids': sidecar['observations'][1]['record'].pop('review_ids')
            elif change == 'both_id_keys': sidecar['observations'][1]['record']['ids'] = ['rev-a', 'rev-b']
            elif change == 'self': sidecar['observations'][1]['record']['review_ids'] = ['rev-a', 'rev-a']
            elif change == 'unknown': sidecar['observations'][1]['record']['review_ids'] = ['rev-a', 'unknown']
            else: sidecar['observations'][1]['review_id'] = 'rev-a'
            with self.subTest(change=change), self.assertRaises(ValueError):
                gate.apply(rows, sidecar, bcsv)

    def test_duplicate_source_or_review_ids_and_reapplication_refused(self):
        rows, sidecar, bcsv = fixture()
        with self.assertRaises(ValueError):
            gate.apply(rows + [dict(rows[0])], sidecar, bcsv)
        derived, _, _ = gate.apply(rows, sidecar, bcsv)
        with self.assertRaises(ValueError):
            gate.apply(derived, sidecar, bcsv)


class WrapperTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.raw = self.root / 'data/raw/study-v6'
        self.dest = self.raw / 'execution-v1'
        self.results = self.root / 'results/study-v6-execution'
        self.rows, self.sidecar, self.bcsv = fixture()
        self.rows_path = self.raw / 'review-resolution-v3/resolved.jsonl'
        self.sidecar_path = self.raw / 'adjudication-v1/reviewer-B-grouping-proposals.json'
        self.bcsv_path = self.raw / 'adjudication-v1/reviewer-B.csv'
        self.inputs = {}

        def save(path, data):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            return {'path': str(path.relative_to(self.root)), 'sha256': sha256(data)}
        self.save = save
        rows_receipt = save(self.rows_path, b''.join(canonical_bytes(r)+b'\n' for r in self.rows))
        sidecar_body = canonical_bytes(self.sidecar)+b'\n'
        save(self.sidecar_path, sidecar_body)
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=['review_id', 'group_merge_ids'])
        writer.writeheader(); writer.writerows(self.bcsv)
        self.inputs['adjudication_reviews'] = save(self.bcsv_path, stream.getvalue().encode())
        self.inputs['adjudication_packet'] = save(self.raw/'adjudication-v1/packet.jsonl',
            b''.join(canonical_bytes({'review_id': r['review_id']})+b'\n' for r in self.bcsv))
        self.inputs['adjudication_session'] = save(self.raw/'adjudication-v1/reviewer-B-session.json', b'{}\n')
        lock = {'rows': 3, 'reviews_sha256': self.inputs['adjudication_reviews']['sha256'],
            'packet_sha256': self.inputs['adjudication_packet']['sha256'],
            'session_sha256': self.inputs['adjudication_session']['sha256']}
        self.inputs['adjudication_lock'] = save(self.raw/'adjudication-v1/reviewer-B-lock.json', canonical_bytes(lock)+b'\n')
        self.resolution_path = self.root/'results/study-v6-review-resolution/resolution-final.json'
        self.resolution = {'review_resolution_complete': True, 'adjudication_completed': True,
            'inputs': self.inputs, 'outputs': {'resolved': rows_receipt}}
        save(self.resolution_path, canonical_bytes(self.resolution)+b'\n')
        self.stack = ExitStack()
        for name, value in {'ROOT': self.root, 'RAW': self.raw, 'DEST': self.dest, 'RESULTS': self.results,
                'EXPECTED_SIDECAR_SHA256': sha256(sidecar_body), 'EXPECTED_PAIRS': 2,
                'EXPECTED_OBSERVATIONS': 3, 'EXPECTED_B_ROWS': 3}.items():
            self.stack.enter_context(patch.object(gate, name, value))

    def tearDown(self):
        self.stack.close(); self.temp.cleanup()

    def test_immutable_finalize_and_read_only_recompute(self):
        before = self.rows_path.read_bytes()
        derived, receipt = gate.finalize()
        self.assertEqual(self.rows_path.read_bytes(), before)
        self.assertEqual(receipt['execution_admitted_rows'], 1)
        self.assertTrue((self.dest/'group-admitted-rows.jsonl').is_file())
        self.assertTrue((self.dest/'grouping-dispositions.json').is_file())
        self.assertEqual(load(self.results/'grouping-admission-v1.json'), receipt)
        for rid in [r['review_id'] for r in self.rows]:
            self.assertNotIn(rid, canonical_bytes(receipt).decode())
        with patch.object(gate, 'immutable') as writes:
            checked_rows, checked_receipt = gate.verify()
        writes.assert_not_called()
        self.assertEqual((checked_rows, checked_receipt), (derived, receipt))
        self.assertEqual(gate.finalize(), (derived, receipt))

    def test_sidecar_and_derived_tampering_cannot_verify(self):
        gate.finalize()
        path = self.dest/'group-admitted-rows.jsonl'
        path.write_bytes(path.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError, 'artifact changed'):
            gate.verify()
        self.sidecar_path.write_bytes(self.sidecar_path.read_bytes()+b'\n')
        with self.assertRaisesRegex(ValueError, 'complete reviewer-B handoff'):
            gate.verify()

    def test_incomplete_original_resolution_or_lock_cannot_admit(self):
        self.resolution['adjudication_completed'] = False
        self.save(self.resolution_path, canonical_bytes(self.resolution)+b'\n')
        with self.assertRaises(PermissionError): gate.finalize()
        self.resolution['adjudication_completed'] = True
        lock_path = self.root/self.inputs['adjudication_lock']['path']
        lock = load(lock_path); lock['rows'] = 2
        self.inputs['adjudication_lock'] = self.save(lock_path, canonical_bytes(lock)+b'\n')
        self.save(self.resolution_path, canonical_bytes(self.resolution)+b'\n')
        with self.assertRaisesRegex(ValueError, 'Complete distinct adjudication'):
            gate.finalize()


if __name__ == '__main__':
    unittest.main()
