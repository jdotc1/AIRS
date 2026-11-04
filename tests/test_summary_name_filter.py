"""Saved-report name projections: no image reads, audits or provenance checks."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from airs.cli import main
from airs.report_summary_text import render_summary_text
from airs.report_summary import summarize_report
from airs.report import load_report
from airs.types import InputError

ROOT = Path(__file__).resolve().parents[1]


def summary():
    result = summarize_report(load_report(ROOT / 'examples/mixed.audit.json'))
    result['findings'][0]['function']['name'] = '_Café'
    result['findings'][1]['function']['name'] = '_Cafe\u0301'
    result['findings'][2]['function']['name'] = '_CAFÉ'
    result['findings'][3]['function']['name'] = None
    return result


class SummaryNameFilterTests(unittest.TestCase):
    def test_cli_name_filter_composes_before_order_and_limit(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['summary', '--report', str(ROOT / 'examples/mixed.audit.json'),
                                   '--verdict', 'inconsistency', '--reason', 'caller_state_mismatch',
                                   '--name-contains', 'frame', '--sort', 'verdict', '--limit', '1']), 0)
        result = json.loads(output.getvalue())
        self.assertEqual([f['function']['name'] for f in result['findings']], ['_shifted_frame_record'])
        self.assertEqual(result['summary']['function_count'], 9)
        self.assertEqual(result['finding_selection']['selected_count'], 2)
        self.assertEqual(result['finding_name_selection']['input_count'], 2)
        self.assertEqual(result['finding_name_selection']['selected_count'], 1)
        self.assertEqual(result['finding_limit']['selected_count'], 1)
        self.assertEqual(result['finding_order'], 'verdict')

    def test_literal_unicode_case_and_missing_names_are_not_normalized(self):
        from airs.report_summary_names import select_summary_names
        value = summary()
        result = select_summary_names(value, 'Café')
        self.assertEqual([f['function']['name'] for f in result['findings']], ['_Café'])
        self.assertEqual(result['finding_name_selection'], {
            'contains': 'Café', 'case_sensitive': True, 'normalization': 'none',
            'input_count': 9, 'selected_count': 1, 'omitted_count': 8})
        self.assertEqual([f['function']['name'] for f in select_summary_names(value, 'Cafe\u0301')['findings']], ['_Cafe\u0301'])
        self.assertEqual([f['function']['name'] for f in select_summary_names(value, 'CAFÉ')['findings']], ['_CAFÉ'])
        self.assertEqual(select_summary_names(value, 'None')['findings'], [])

    def test_projection_detaches_nested_data_and_preserves_all_full_source_context(self):
        from airs.report_summary_names import select_summary_names
        value = summary()
        before = deepcopy(value)
        result = select_summary_names(value, 'Café')
        for key in value.keys() - {'findings'}:
            self.assertEqual(result[key], value[key])
        result['findings'][0]['function']['name'] = 'changed'
        result['source_report']['image']['display_name'] = 'changed'
        result['summary']['function_count'] = 0
        self.assertEqual(value, before)

    def test_absent_filter_preserves_shape_and_detaches_names(self):
        from airs.report_summary_names import select_summary_names
        value = summary()
        result = select_summary_names(value)
        self.assertEqual(result, value)
        self.assertNotIn('finding_name_selection', result)
        result['findings'][0]['function']['name'] = 'changed'
        self.assertEqual(value['findings'][0]['function']['name'], '_Café')

    def test_invalid_queries_reject_before_saved_report_io(self):
        from airs.report_summary_names import select_summary_names, validate_summary_name
        for query in ['', ' ', '\t', 'a\n', 'a\x00', 'a\x7f', 'x' * 257, 'é' * 129, '\ud800', True, 7]:
            with self.subTest(query=repr(query)), self.assertRaises(InputError) as caught:
                select_summary_names(summary(), query)
            self.assertEqual(caught.exception.code, 'invalid_summary_name')
        self.assertEqual(validate_summary_name('é' * 128), 'é' * 128)
        self.assertEqual(validate_summary_name(' name '), ' name ')
        for query in [' ', 'x' * 257, 'a\n']:
            with patch('airs.cli.load_report') as load, contextlib.redirect_stderr(io.StringIO()) as error:
                self.assertEqual(main(['summary', '--report', '/missing/report', '--name-contains', query]), 2)
                load.assert_not_called()
                self.assertEqual(json.loads(error.getvalue())['error']['code'], 'invalid_summary_name')

    def test_text_discloses_name_selection_using_existing_terminal_escaping(self):
        from airs.report_summary_names import select_summary_names
        text = render_summary_text(select_summary_names(summary(), 'Café'))
        self.assertIn('Finding-name selection (full source counts unchanged):', text)
        self.assertIn('"selected_count": 1', text)
        self.assertIn('first 1 of 1 selected rows', text)
        self.assertIn('Caf\\u00e9', text)
        self.assertNotIn('Café', text)
        self.assertIn('"function_count": 9', text)

    def test_no_matches_preserve_denominators_and_limit_metadata(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['summary', '--report', str(ROOT / 'examples/mixed.audit.json'),
                                   '--name-contains', 'zz_no_such_function', '--limit', '0']), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['findings'], [])
        self.assertEqual(result['finding_name_selection']['selected_count'], 0)
        self.assertEqual(result['finding_name_selection']['omitted_count'], 9)
        self.assertEqual(result['summary']['unresolved_count'], 4)
        self.assertEqual(result['finding_limit']['selected_count'], 0)

    def test_name_filtered_output_cannot_overwrite_saved_input(self):
        storage = ROOT / 'local-evidence/summary-function-name-filter'
        storage.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=storage) as directory:
            path = Path(directory) / 'saved.json'
            original = (ROOT / 'examples/mixed.audit.json').read_bytes()
            path.write_bytes(original)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['summary', '--report', str(path), '--name-contains', 'frame', '--output', str(path)]), 2)
            self.assertEqual(path.read_bytes(), original)
