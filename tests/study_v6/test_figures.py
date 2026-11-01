"""Aggregate sanitization and render contracts, using declared synthetic fixtures."""
import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.study_v6 import analyze, figures


def fixture(observed=True):
    planned, records = [], []
    for config in analyze.PRIMARY_CONFIGS:
        for index, label in enumerate((0, 1)):
            for condition in ('format', 'task', 'reminder', 'length'):
                row = {'id': f'RESTRICTED-CASE-{index}', 'source': 'browsesafe', 'group': 'RESTRICTED-GROUP',
                       'config': config, 'condition': condition, 'gold': label, 'upstream_label': label,
                       'split': 'confirmation', 'inference_eligible': True, 'coverage_supported': True,
                       'review_subgroups': {}, 'candidate': 'RESTRICTED-RAW-TEXT', 'pair_id': 'RESTRICTED-PAIR'}
                planned.append(row)
                records.append({'id': row['id'], 'config': config, 'condition': condition,
                                'status': 'ok', 'valid': True, 'prediction': label,
                                'score': .1 if label == 0 else .9, 'attempt': 0})
    result = analyze.analyze(planned, records if observed else [], bootstrap_draws=20, randomization_draws=20)
    result['unused_private_payload'] = {'candidate': 'RESTRICTED-RAW-TEXT', 'token': 'RESTRICTED-TOKEN'}
    verification = {'analysis_sha256': figures.digest(result), **{field: True for field in figures.VERIFY_FIELDS}}
    return result, verification


class AggregateTables(unittest.TestCase):
    def test_allowlist_removes_all_raw_ids_group_ids_payloads_paths_and_free_text(self):
        analysis, verification = fixture()
        tables = figures.build_tables(analysis, verification=verification)
        body = json.dumps(tables, allow_nan=False)
        self.assertNotIn('RESTRICTED-', body)
        self.assertNotIn('unused_private_payload', body)
        self.assertNotIn('individual_group_class_effects', body)
        self.assertEqual(len(tables['primary_contrasts']), 6)
        self.assertEqual(tables['planned_cells'], 16)
        self.assertTrue(tables['empirical_checks_complete'])

    def test_requires_external_checks_pinning_exact_analysis(self):
        analysis, verification = fixture()
        with self.assertRaisesRegex(ValueError, 'separate complete verification'):
            figures.build_tables(analysis)
        stale = copy.deepcopy(verification)
        stale['analysis_sha256'] = '0' * 64
        with self.assertRaises(ValueError):
            figures.build_tables(analysis, verification=stale)
        stale = copy.deepcopy(verification)
        stale['accounting_verified'] = False
        with self.assertRaises(ValueError):
            figures.build_tables(analysis, verification=stale)

    def test_null_unrun_cells_do_not_become_zero_estimates(self):
        analysis, _ = fixture(observed=False)
        tables = figures.build_tables(analysis)
        self.assertTrue(all(row['status'] == 'unrun' for row in tables['primary_contrasts']))
        self.assertTrue(all(row['estimate_pp'] is None for row in tables['primary_contrasts']))
        self.assertEqual(tables['observed_cells'], 0)
        self.assertFalse(tables['empirical_checks_complete'])

    def test_rejects_inconsistent_intervals_denominators_and_estimates(self):
        analysis, verification = fixture()
        analysis['strata'][0]['conditions'][0]['planned_rows'] = 900
        verification['analysis_sha256'] = figures.digest(analysis)
        with self.assertRaisesRegex(ValueError, 'do not reconcile'):
            figures.build_tables(analysis, verification=verification)
        analysis, verification = fixture()
        analysis['primary_six_test_family'][0]['estimate'] = .5
        verification['analysis_sha256'] = figures.digest(analysis)
        with self.assertRaisesRegex(ValueError, 'estimates disagree'):
            figures.build_tables(analysis, verification=verification)
        self.assertIsNone(figures.interval([None, None]))
        with self.assertRaisesRegex(ValueError, 'Unordered'):
            figures.interval([.8, .2])

    def test_attrition_support_reconciles_without_mapping_or_labels(self):
        analysis, verification = fixture()
        resolution = {'review_resolution_complete': True, 'source_counts': {'browsesafe': {
            'prepared': 10, 'review_eligible': 8, 'quarantined': 2,
            'labels': {'allowed': 4, 'violation': 4},
            'splits': {'confirmation': {'rows': 6, 'groups': 3}, 'development': {'rows': 2, 'groups': 1}},
            'private_mapping': {'RESTRICTED-CASE': 'RESTRICTED-LABEL'}}}}
        tables = figures.build_tables(analysis, verification=verification, resolution=resolution)
        self.assertEqual(tables['source_attrition'][0]['confirmation_groups'], 3)
        self.assertNotIn('RESTRICTED-', json.dumps(tables))
        resolution['source_counts']['browsesafe']['quarantined'] = 3
        with self.assertRaisesRegex(ValueError, 'attrition does not reconcile'):
            figures.build_tables(analysis, verification=verification, resolution=resolution)

    def test_unknown_error_body_is_counted_as_generic_failure(self):
        analysis, verification = fixture(observed=False)
        statuses = analysis['strata'][0]['conditions'][0]['status_counts']
        statuses['RESTRICTED-ERROR-BODY'] = statuses.pop('not_attempted')
        tables = figures.build_tables(analysis)
        self.assertNotIn('RESTRICTED-', json.dumps(tables))
        self.assertEqual(tables['condition_support'][0]['status_counts'], {'other_parser_failure': 2})


class FigureRendering(unittest.TestCase):
    def test_null_panel_contains_no_empirical_point_and_export_is_reproducible(self):
        analysis, _ = fixture(observed=False)
        tables = figures.build_tables(analysis)
        fig = figures.contrast_figure(tables)
        # The dashed zero reference is the only line. Unrun estimates add none.
        self.assertEqual(len(fig.axes[0].lines), 1)
        self.assertEqual(sum(t.get_text() == 'Unrun' for t in fig.axes[0].texts), 6)
        figures._mpl().close(fig)
        with tempfile.TemporaryDirectory() as directory:
            paths = figures.export(tables, directory)
            self.assertEqual(len(paths), 6)
            self.assertTrue(all(p.stat().st_size > 1000 for p in paths))
            figures.export(tables, directory)
            self.assertTrue((Path(directory) / 'tables.json').exists())

    def test_empirical_intervals_export_uses_table_units_and_denominators(self):
        analysis, verification = fixture()
        tables = figures.build_tables(analysis, verification=verification)
        figure = figures.contrast_figure(tables)
        labels = [text.get_text() for text in figure.axes[0].texts]
        self.assertTrue(all('1/1 groups' in text and '2/2 rows' in text for text in labels))
        self.assertEqual(len(figure.axes[0].collections), 12)
        figures._mpl().close(figure)
        with tempfile.TemporaryDirectory() as directory:
            paths = figures.export(tables, directory)
            self.assertEqual(len(paths), 8)


if __name__ == '__main__':
    unittest.main()
