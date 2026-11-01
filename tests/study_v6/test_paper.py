"""Paper schema, evidence gates and numeric claim references; never creates PDF."""
import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.study_v6 import paper


def fixture():
    analysis = {'version': 'v6-analysis-1', 'analysis_set': 'first_attempt_primary',
        'observed_cells': 8, 'planned_cells': 16, 'analysis_plan': {'primary_family_size': 6}}
    tables = {'version': paper.TABLES_VERSION, 'analysis_set': 'first_attempt_primary',
        'empirical_checks_complete': True, 'review_resolution_complete': True,
        'analysis_sha256': paper.digest(analysis), 'observed_cells': 8,
        'primary_contrasts': [{'source': 'browsesafe', 'planned_groups': 4, 'estimate_pp': -1.2}],
        'source_attrition': [{'source': 'nvidia', 'confirmation_groups': 3}],
        'accounting': {'openai': {'conservative_accounted_usd': .02}}}
    narrative = {'version': paper.VERSION, 'title': 'Decision Context Benchmark: Task Context and Static Decisions',
        'authors': '', 'provenance': dict(paper.PROVENANCE),
        'claims': {
            'groups': {'source': 'tables', 'path': ['primary_contrasts', 0, 'planned_groups'],
                       'value': 4, 'format': 'integer', 'population': 'browsesafe'},
            'effect': {'source': 'tables', 'path': ['primary_contrasts', 0, 'estimate_pp'],
                       'value': -1.2, 'format': 'pp2', 'population': 'browsesafe'},
            'family': {'source': 'analysis', 'path': ['analysis_plan', 'primary_family_size'],
                       'value': 6, 'format': 'integer', 'population': 'protocol'},
            'secondary': {'source': 'tables', 'path': ['source_attrition', 0, 'confirmation_groups'],
                          'value': 3, 'format': 'integer', 'population': 'nvidia'},
            'cost': {'source': 'tables', 'path': ['accounting', 'openai', 'conservative_accounted_usd'],
                     'value': .02, 'format': 'usd6', 'population': 'accounting'}},
        'references': [{'id': 'BrowseSafe', 'authors': 'Source authors', 'title': 'A Source Release',
                        'year': 2026, 'url': 'https://example.org/source'}],
        'pages': [{'role': role, 'heading': heading, 'blocks': [{'type': 'paragraph', 'text': text}]}
            for role, heading, text in zip(paper.ROLES,
                ('Question and context', 'Data and methods', 'Primary results', 'Source diagnostics', 'Discussion'),
                ('We study task information in static decisions. {{cite:BrowseSafe}}',
                 'The fixed main family contains {{family}} tests.',
                 'The main target contains {{groups}} groups, with effect {{effect}}.',
                 'The synthetic secondary arm contains {{secondary}} groups and remains descriptive.',
                 'Conservative accounted cost is {{cost}}; labels are agent-reviewed source agreement.'))]}
    narrative['pages'][-1]['blocks'].append({'type': 'references'})
    return narrative, analysis, tables, pin(narrative, analysis, tables)


def pin(narrative, analysis, tables, **extra):
    return {field: True for field in paper.REQUIRED_CHECKS} | {
        'narrative_sha256': paper.digest(narrative), 'analysis_sha256': paper.digest(analysis),
        'tables_sha256': paper.digest(tables)} | extra


class EvidenceGates(unittest.TestCase):
    def test_validates_five_authored_roles_without_importing_authoring_dependencies(self):
        values = fixture()
        with patch.dict(sys.modules, {'reportlab': None, 'pypdf': None}):
            result = paper.validate(*values)
        self.assertEqual(result['page_count'], 5)
        self.assertFalse(result['pdf_created'])
        self.assertEqual(result['claim_ledger']['effect']['display'], '-1.20 pp')
        self.assertEqual(result['claim_ledger']['cost']['display'], 'US$0.020000')
        self.assertEqual(result['used_reference_ids'], ['BrowseSafe'])
        json.dumps(result, allow_nan=False)

    def test_each_terminal_scientific_and_narrative_gate_is_required(self):
        for field in paper.REQUIRED_CHECKS:
            values = list(fixture())
            values[-1][field] = False
            with self.subTest(gate=field), self.assertRaises(PermissionError):
                paper.validate(*values)
        narrative, analysis, tables, _ = fixture()
        tables['review_resolution_complete'] = False
        with self.assertRaises(PermissionError):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))

    def test_evidence_hashes_and_primary_first_attempt_cannot_change(self):
        values = list(fixture())
        values[1]['planned_cells'] = 999
        with self.assertRaisesRegex(ValueError, 'analysis hash changed'):
            paper.validate(*values)
        narrative, analysis, tables, _ = fixture()
        analysis['analysis_set'] = 'recovery_first_valid_sensitivity'
        with self.assertRaisesRegex(PermissionError, 'recovered'):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))
        narrative, analysis, tables, _ = fixture()
        analysis['observed_cells'] = tables['observed_cells'] = 0
        tables['analysis_sha256'] = paper.digest(analysis)
        with self.assertRaisesRegex(PermissionError, 'unrun scaffold'):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))

    def test_exact_five_pages_and_provenance_are_mandatory(self):
        narrative, analysis, tables, _ = fixture()
        narrative['pages'] = narrative['pages'][:-1]
        with self.assertRaisesRegex(ValueError, 'five ordered'):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))
        narrative, analysis, tables, _ = fixture()
        narrative['provenance']['labels'] = 'human_gold'
        with self.assertRaisesRegex(ValueError, 'provenance'):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))


class NumericClaimLedger(unittest.TestCase):
    def test_raw_numeric_prose_placeholder_and_unresolved_tokens_are_rejected(self):
        for bad in ('The study achieved 99% accuracy.', 'TODO replace this sentence.',
                    'The estimate is {{missing}}.', 'The effect is {{broken.', 'Text uses a non-ASCII – dash.'):
            narrative, analysis, tables, _ = fixture()
            narrative['pages'][0]['blocks'][0]['text'] = bad
            with self.subTest(text=bad), self.assertRaises(ValueError):
                paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))

    def test_stale_null_and_source_population_claims_fail(self):
        for edit in ('stale', 'null', 'population', 'path', 'unused'):
            narrative, analysis, tables, _ = fixture()
            if edit == 'stale':
                narrative['claims']['effect']['value'] = 1.2
            elif edit == 'null':
                tables['primary_contrasts'][0]['estimate_pp'] = None
            elif edit == 'population':
                narrative['claims']['effect']['population'] = 'nvidia'
            elif edit == 'path':
                narrative['claims']['effect']['path'] = ['primary_contrasts', -1, 'estimate_pp']
            else:
                narrative['claims']['unused'] = dict(narrative['claims']['groups'])
            with self.subTest(edit=edit), self.assertRaises(ValueError):
                paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))

    def test_tables_retain_numerical_claim_tokens_in_every_cell(self):
        narrative, analysis, tables, _ = fixture()
        narrative['pages'][2]['blocks'].append({'type': 'table', 'caption': 'Main source comparison.',
            'rows': [['Target', 'Effect'], ['{{groups}} groups', '{{effect}}']]})
        result = paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))
        self.assertEqual(result['claim_ledger']['groups']['value'], 4)
        narrative['pages'][2]['blocks'][-1]['rows'][1][0] = '999 groups'
        with self.assertRaisesRegex(ValueError, 'Numerical prose'):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))

    def test_display_formats_preserve_checked_units(self):
        self.assertEqual(paper.format_claim(.15, 'percent1'), '15.0%')
        self.assertEqual(paper.format_claim(1.5, 'pp2'), '1.50 pp')
        self.assertEqual(paper.format_claim(1000, 'integer'), '1,000')
        with self.assertRaises(ValueError):
            paper.format_claim(1.5, 'integer')
        with self.assertRaises(ValueError):
            paper.format_claim(True, 'integer')
        with self.assertRaises(ValueError):
            paper.format_claim(15, 'percent1')

    def test_numeric_model_ids_require_checked_route_literal_references(self):
        narrative, analysis, tables, _ = fixture()
        tables['route_metadata'] = {'jev_firstparty': {'model': 'jev-1.14.0'}}
        narrative['claims']['jev_model'] = {'source': 'tables',
            'path': ['route_metadata', 'jev_firstparty', 'model'], 'value': 'jev-1.14.0',
            'format': 'literal', 'population': 'study'}
        narrative['pages'][1]['blocks'][0]['text'] += ' The frozen route is {{jev_model}}.'
        result = paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))
        self.assertEqual(result['claim_ledger']['jev_model']['display'], 'jev-1.14.0')
        narrative['claims']['jev_model']['value'] = 'jev-9.99'
        with self.assertRaisesRegex(ValueError, 'stale'):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))


class FigureSafety(unittest.TestCase):
    def test_approved_figure_hash_table_binding_and_visual_inspection_are_required(self):
        narrative, analysis, tables, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'checked.png'
            path.write_bytes(b'synthetic schema fixture; not an actual figure')
            narrative['pages'][2]['blocks'].append({'type': 'figure', 'figure': 'main',
                                                   'caption': 'Checked main-source effect intervals.'})
            receipt = {'path': str(path), 'sha256': paper.file_digest(path),
                       'tables_sha256': paper.digest(tables), 'visually_verified': True}
            verification = pin(narrative, analysis, tables, figure_artifacts={'main': receipt})
            result = paper.validate(narrative, analysis, tables, verification)
            self.assertEqual(result['figures']['main']['sha256'], receipt['sha256'])
            path.write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError, 'Figure hash'):
                paper.validate(narrative, analysis, tables, verification)
            path.write_bytes(b'synthetic schema fixture; not an actual figure')
            receipt['visually_verified'] = False
            with self.assertRaises(ValueError):
                paper.validate(narrative, analysis, tables, verification)

    def test_reference_tokens_require_readable_secure_source_links(self):
        narrative, analysis, tables, _ = fixture()
        narrative['references'][0]['url'] = 'https://user:secret@example.org/source'
        with self.assertRaisesRegex(ValueError, 'HTTPS source links'):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))
        narrative, analysis, tables, _ = fixture()
        narrative['pages'][0]['blocks'][0]['text'] = '{{cite:Unknown}}'
        with self.assertRaisesRegex(ValueError, 'Unresolved citation'):
            paper.validate(narrative, analysis, tables, pin(narrative, analysis, tables))


if __name__ == '__main__':
    unittest.main()
