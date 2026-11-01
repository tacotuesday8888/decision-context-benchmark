"""Synthetic, hand-computable tests; no corpora or model calls."""
import itertools
import math
import hashlib
import json
from pathlib import Path
import tempfile
import numpy as np
import unittest
from scripts.study_v7 import analysis as a
from scripts.study_v7 import simulate as s

def fixture(groups=4):
    (planned, records) = ([], [])
    for group in range(groups):
        for config in a.NATIVE_CONFIGS:
            for condition in a.CONDITIONS:
                for gold in (0, 1):
                    row = {'id': f'page-{group}-{gold}', 'group_id': f'group-{group}', 'pair_id': f'pair-{group}', 'upstream_label': gold, 'source': 'browsesafe', 'partition': 'confirmation', 'config': config, 'condition': condition}
                    planned.append(row)
                    wrong = condition != 'task' and group < 2
                    pred = 1 - gold if wrong else gold
                    records.append({'id': row['id'], 'config': config, 'condition': condition, 'namespace': 'primary', 'attempt': 0, 'status': 'ok', 'valid': True, 'prediction': pred, 'score': 0.9 if pred else 0.1})
    return (planned, records)

class AnalysisTests(unittest.TestCase):

    def test_hand_computable_group_test_and_holm(self):
        assert a.group_difference([1, 0, 0, 0]) == 0.5
        assert a.group_difference([0, 0, 1, 1]) == -1
        result = a.paired_t([1, 1, 0, 0])
        assert result['mean'] == 0.5
        self.assertAlmostEqual(result['sd'], math.sqrt(1 / 3))
        self.assertAlmostEqual(result['t'], math.sqrt(3))
        assert result['df'] == 3
        # Closed form for df=3, t=sqrt(3): two-sided p = 1/2 - 1/pi.
        self.assertAlmostEqual(result['p'], 0.5 - 1/math.pi)
        assert a.paired_t([0, 0, 0])['p'] == 1
        assert a.paired_t([1, 1, 1])['p'] == 0
        assert a.paired_t([])['p'] is None
        assert a.paired_t([1])['p'] is None
        corrected = a.holm([0.001, 0.01, 0.02, 0.04, 0.2, None])
        assert [x['adjusted_p'] for x in corrected] == [0.006, 0.05, 0.08, 0.12, 0.4, None]
        assert [x['reject'] for x in corrected] == [True, True, False, False, False, False]
        assert not a.holm([0.01, None, None, None, None, None])[0]['reject']

    def test_complete_schedule_shared_cohort_and_specific_sensitivity(self):
        (plan, observations) = fixture()
        result = a.analyze_main(a.collect_main(plan, observations), draws=200, seed='fixture')
        assert result['planned_groups'] == result['primary_complete_groups'] == 4
        assert len(result['contrasts']) == 6
        for contrast in result['contrasts']:
            assert contrast['primary']['test']['mean'] == 0.5
            self.assertAlmostEqual(contrast['primary']['test']['t'], math.sqrt(3))
            assert contrast['all_planned_error_difference_bounds'] == [0.5, 0.5]
        missing = next((i for (i, r) in enumerate(observations) if r['id'] == 'page-0-0' and r['config'] == a.NATIVE_CONFIGS[0] and (r['condition'] == 'length')))
        observations.pop(missing)
        result = a.analyze_main(a.collect_main(plan, observations), draws=200, seed='fixture')
        assert result['primary_complete_groups'] == 3
        assert {c['primary']['test']['n'] for c in result['contrasts']} == {3}
        for contrast in result['contrasts']:
            affected = contrast['config'] == a.NATIVE_CONFIGS[0] and contrast['control'] == 'length'
            assert contrast['contrast_complete_sensitivity']['test']['n'] == (3 if affected else 4)
            if affected:
                assert contrast['all_planned_error_difference_bounds'] == [0.375, 0.5]

    def test_all_planned_bounds_retain_each_known_error(self):
        for missing in itertools.product((False, True), repeat=4):
            observed = [None if m else e for (m, e) in zip(missing, [1, 0, 1, 0])]
            unknown = [i for (i, v) in enumerate(observed) if v is None]
            possible = []
            for fills in itertools.product((0, 1), repeat=len(unknown)):
                complete = observed.copy()
                for (index, error) in zip(unknown, fills):
                    complete[index] = error
                possible.append(a.group_difference(complete))
            assert a.difference_bounds(observed) == [min(possible), max(possible)]
        assert a.difference_bounds([None] * 4) == [-1, 1]
        assert a.difference_bounds([1, 0, 0, 0]) == [0.5, 0.5]

    def test_no_retries_repeats_or_malformed_schedule(self):
        (plan, observations) = fixture()
        with self.assertRaisesRegex(ValueError, 'Incomplete planned'):
            a.collect_main(plan[:-1], observations)
        bad = [dict(r) for r in observations]
        bad[0]['attempt'] = 1
        with self.assertRaisesRegex(ValueError, 'first attempts'):
            a.collect_main(plan, bad)
        (bad[0]['attempt'], bad[0]['namespace']) = (0, 'repeat')
        with self.assertRaisesRegex(ValueError, 'first attempts'):
            a.collect_main(plan, bad)
        with self.assertRaisesRegex(ValueError, 'Duplicate planned'):
            a.collect_main(plan + plan[:1], observations)
        with self.assertRaisesRegex(ValueError, 'Unplanned or duplicate'):
            a.collect_main(plan, observations + observations[:1])
        plan[0]['upstream_label'] = 1
        with self.assertRaisesRegex(ValueError, 'changed across'):
            a.collect_main(plan, observations)

    def test_runner_first_namespace_and_split_are_admissible(self):
        plan, observations = fixture()
        for row in plan:
            row['split'] = row.pop('partition')
        for row in observations:
            row['namespace'] = 'first'
        self.assertEqual(len(a.collect_main(plan, observations)), len(plan))
        plan[0]['coverage_supported'] = False
        with self.assertRaisesRegex(ValueError, 'unsupported'):
            a.collect_main(plan, observations)

    def test_reconstruct_frozen_runner_first_attempts_without_repeat_replacement(self):
        cells, normalized = fixture(groups=1)
        requests = {}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            payload=b'{}'
            payload_sha=hashlib.sha256(payload).hexdigest()
            for i, (cell, observation) in enumerate(zip(cells, normalized)):
                cell['split'] = cell.pop('partition')
                cell['namespace'] = 'first'
                key = hashlib.sha256(str(i).encode()).hexdigest()
                cell['request_key'] = key
                requests[key] = dict(cell, key=key, payload_sha256=payload_sha)
                directory = root/key
                directory.mkdir()
                (directory/'request.json').write_bytes(payload)
                result = dict(parsed={k: observation[k] for k in ('status','valid','prediction','score')},
                              request_sha256=payload_sha, namespace='first', first_attempt_primary=True,
                              raw_hashes={'request.json':payload_sha})
                (directory/'completed.json').write_text(json.dumps(result))
            # First cell was interrupted; a valid separate repeat cannot replace it.
            first_key = cells[0]['request_key']
            (root/first_key/'completed.json').unlink()
            (root/first_key/'interrupted.json').write_text(json.dumps(dict(payload_sha256=payload_sha,namespace='first')))
            repeat = dict(cells[0], namespace='repeat-1',request_key='e'*64)
            requests[repeat['request_key']] = dict(repeat,payload_sha256=payload_sha)
            planned, records = a.reconstruct_main_observations({'cells':cells+[repeat], 'requests':requests},root)
            self.assertEqual(len(planned),len(cells))
            result = a.analyze_main(a.collect_main(planned,records),draws=100)
            self.assertEqual(result['primary_complete_groups'],0)
            self.assertEqual(sum(c['status_counts'].get('interrupted_unknown',0) for c in result['coverage']),1)
            # Changed retained identity fails loudly instead of entering analysis.
            key=cells[1]['request_key']
            altered=json.loads((root/key/'completed.json').read_text())
            altered['request_sha256']='0'*64
            (root/key/'completed.json').write_text(json.dumps(altered))
            with self.assertRaisesRegex(ValueError,'payload differs'):
                a.reconstruct_main_observations({'cells':cells,'requests':requests},root)

    def test_ties_abstain_but_native_scores_still_enter_diagnostics(self):
        (plan, observations) = fixture()
        observations[0].update(status='tie', valid=False, prediction=None, score=0.5)
        rows = a.collect_main(plan, observations)
        result = a.analyze_main(rows, draws=100)
        assert result['primary_complete_groups'] == 3
        summary = next((s for s in result['coverage'] if s['config'] == observations[0]['config'] and s['condition'] == observations[0]['condition']))
        assert summary['valid_rows'] == 7
        assert summary['score_diagnostics']['n'] == 8
        assert summary['status_counts']['tie'] == 1
        observations[0].update(status='ok', valid=True, prediction=1)
        with self.assertRaisesRegex(ValueError, 'exactly 0.5'):
            a.collect_main(plan, observations)

    def test_bootstrap_is_whole_group_empirical_and_reproducible(self):
        result = a.bootstrap_mean([-1, 1], draws=20000, seed='two-groups')
        assert result['pointwise_95'] == [-1, 1]
        assert result['conservative_six_99_166667'] == [-1, 1]
        assert result['omitted_draws'] == 0
        assert result == a.bootstrap_mean([-1, 1], draws=20000, seed='two-groups')
        assert a.bootstrap_mean([0.5] * 3)['pointwise_95'] == [0.5, 0.5]
        assert a.bootstrap_mean([])['omitted_draws'] == 20000
        values = np.array([-1, 0, 1])
        index_counts = {}
        for indices in itertools.product(range(3), repeat=3):
            total = int(values[list(indices)].sum())
            index_counts[total] = index_counts.get(total, 0) + 1
        count_counts = {}
        for c0 in range(4):
            for c1 in range(4 - c0):
                c2 = 3 - c0 - c1
                multiplicity = math.factorial(3) // (math.factorial(c0) * math.factorial(c1) * math.factorial(c2))
                total = -c0 + c2
                count_counts[total] = count_counts.get(total, 0) + multiplicity
        assert count_counts == index_counts

    def test_synthetic_errors_are_coherent_bounded_and_missing_bounds_hold(self):
        rng = np.random.default_rng(1234)
        for shape in ('symmetric', 'skewed'):
            for effect in (0.0, 0.03, 0.05):
                errors = s.generate_errors(rng, 10000, shape=shape, effect=effect)
                assert set(np.unique(errors)) == {0, 1}
                d = s.group_differences(errors)
                assert d.shape == (10000, 6)
                self.assertAlmostEqual(d.mean(), effect, delta=0.025)
                assert np.max(np.abs(d)) <= 1
                for mechanism in ('none', 'mcar_cells', 'informative'):
                    mask = s.missing_mask(rng, errors, mechanism)
                    (lower, upper) = s.masked_bounds(errors, mask)
                    assert np.all(lower - 1e-12 <= d.mean(axis=0))
                    assert np.all(d.mean(axis=0) <= upper + 1e-12)

    def test_synthetic_harness_uses_six_tests_and_two_interval_levels(self):
        spec = {'name': 'tiny-fixture', 'groups': 40, 'shape': 'skewed', 'q': 1.0, 'effect': 0.0, 'missingness': 'mcar_cells'}
        result = s.scenario(spec, repetitions=4, interval_repetitions=2, bootstrap_draws=50, seed='fixture')
        assert len(result['contrast_rejection']) == 6
        assert len(result['pointwise_95_coverage']) == len(result['conservative_99_166667_coverage']) == 6
        assert result['family_any_rejection']['trials'] == 4
        assert result['all_planned_bounds_contain_realized_full_group_means']['rate'] == 1

    def test_descriptive_group_error_and_brier_intervals(self):
        rows=[]
        for group in range(3):
            for gold in (0,1):
                rows.append(dict(id=f'{group}-{gold}',group_id=str(group),source='promptshield',
                                 config='luna_decisions',condition='external',gold=gold,
                                 status='ok',valid=True,prediction=gold,score=.75 if gold else .25))
        result=a.classification_summary(rows,draws=200,seed='descriptive-fixture')[0]
        self.assertEqual(result['intervals']['fpr'],[0.,0.])
        self.assertEqual(result['intervals']['fnr'],[0.,0.])
        self.assertEqual(result['intervals']['balanced_error'],[0.,0.])
        self.assertEqual(result['intervals']['brier'],[.0625,.0625])
        self.assertEqual(result['score_diagnostics']['auroc'],1.)
        # Scores from native ties enter Brier while classification is missing.
        for row in rows:
            row.update(status='tie',valid=False,prediction=None,score=.5)
        result=a.classification_summary(rows,draws=200,seed='ties')[0]
        self.assertIsNone(result['intervals']['balanced_error'])
        self.assertEqual(result['intervals']['omitted_draws_by_metric']['balanced_error'],200)
        self.assertEqual(result['intervals']['brier'],[.25,.25])
        self.assertEqual(result['score_diagnostics']['auroc'],.5)
        rows[0]['config']='sol_responses'
        with self.assertRaisesRegex(ValueError,'invent confidence'):
            a.classification_summary(rows,draws=200)
