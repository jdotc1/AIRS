"""New bounded saved-inventory presentation checks; never analyze an image."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from airs.cli import main
from airs.coverage import coverage_inventory
from airs.coverage_text import render_coverage_text
from airs.report import load_report
from airs.types import InputError

ROOT = Path(__file__).resolve().parents[1]


def inventory():
    return {
        'status': 'conflicting_reports',
        'summary': {'function_count': 9, 'unresolved_count': 8,
                    'duplicate_report_count': 1, 'conflicting_report_count': 2},
        'models': {'owned-model': 2},
        'reports': [{'index': 0, 'duplicate_of': None}, {'index': 1, 'duplicate_of': 0}],
        'conflicting_report_indices': [0, 2],
        'reasons': [{'reason': code, 'count': count, 'examples': [{'finding_id': code}]} for code, count in
                    [('z_high', 4), ('a_tied', 2), ('b_tied', 2)]],
        'limitations': ['Supplied saved reports only.'],
        'reason_selection': {'requested': ['a_tied', 'z_high', 'unknown'],
                             'matched': ['a_tied', 'z_high'], 'unmatched': ['unknown']},
    }


class CoverageLimitTests(unittest.TestCase):
    def test_cli_limit_is_accepted_and_preserves_complete_source_counts(self):
        path = ROOT / 'examples/mixed.audit.json'
        complete = coverage_inventory([load_report(path)])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['coverage', '--report', str(path), '--limit', '0']), 0)
        limited = json.loads(output.getvalue())
        self.assertEqual(limited['reasons'], [])
        self.assertEqual(limited['summary'], complete['summary'])
        self.assertEqual(limited['reports'], complete['reports'])
        self.assertEqual(limited['reason_limit']['omitted_count'], len(complete['reasons']))

    def test_projection_preserves_order_full_context_and_detaches_nested_data(self):
        from airs.coverage_limit import limit_coverage_reasons
        original = inventory()
        before = deepcopy(original)
        result = limit_coverage_reasons(original, 2)
        self.assertEqual([r['reason'] for r in result['reasons']], ['z_high', 'a_tied'])
        self.assertEqual(result['reason_limit'], {'maximum': 2, 'returned_count': 2,
                                               'omitted_count': 1, 'selected_count': 3})
        for field in original.keys() - {'reasons'}:
            self.assertEqual(result[field], original[field])
        result['reasons'][0]['examples'][0]['finding_id'] = 'changed'
        result['reports'][0]['duplicate_of'] = 9
        result['reason_selection']['requested'].append('changed')
        self.assertEqual(original, before)

    def test_zero_large_and_default_limits_have_explicit_omission_semantics(self):
        from airs.coverage_limit import limit_coverage_reasons, validate_coverage_limit
        original = inventory()
        self.assertEqual(limit_coverage_reasons(original), original)
        self.assertNotIn('reason_limit', limit_coverage_reasons(original))
        zero = limit_coverage_reasons(original, 0)
        self.assertEqual(zero['reason_limit']['returned_count'], 0)
        self.assertEqual(zero['reason_limit']['omitted_count'], 3)
        large = limit_coverage_reasons(original, 200_000)
        self.assertEqual(large['reasons'], original['reasons'])
        self.assertEqual(large['reason_limit']['omitted_count'], 0)
        self.assertEqual(validate_coverage_limit(None), None)
        for invalid in [True, False, -1, 200_001, 1.5, '1']:
            with self.subTest(value=invalid), self.assertRaises(InputError) as caught:
                limit_coverage_reasons(original, invalid)
            self.assertEqual(caught.exception.code, 'invalid_coverage_limit')

    def test_invalid_numeric_cli_limits_fail_before_any_report_io(self):
        for value in ['-1', '200001']:
            with self.subTest(value=value), patch('airs.cli.Path.stat') as stat, patch('airs.cli.load_report') as load:
                error = io.StringIO()
                with contextlib.redirect_stderr(error):
                    self.assertEqual(main(['coverage', '--report', '/missing/report', '--limit', value]), 2)
                stat.assert_not_called()
                load.assert_not_called()
                self.assertEqual(json.loads(error.getvalue())['error']['code'], 'invalid_coverage_limit')

    def test_text_discloses_limit_separately_from_unchanged_denominators(self):
        from airs.coverage_limit import limit_coverage_reasons
        text = render_coverage_text(limit_coverage_reasons(inventory(), 1))
        self.assertIn('Reason limit (does not filter denominators):', text)
        self.assertIn('"omitted_count": 2', text)
        self.assertIn('"unresolved_count": 8', text)
        self.assertIn('"duplicate_of": 0', text)
        self.assertEqual(text.count('\nReason: '), 1)
        self.assertNotIn('Reason limit (does not filter denominators):', render_coverage_text(inventory()))

    def test_reason_selection_precedes_limit_in_both_cli_formats(self):
        path = ROOT / 'examples/mixed.audit.json'
        complete = coverage_inventory([load_report(path)])
        reason = complete['reasons'][0]['reason']
        for format in ['json', 'text']:
            output = io.StringIO()
            with self.subTest(format=format), contextlib.redirect_stdout(output):
                self.assertEqual(main(['coverage', '--report', str(path), '--reason', reason,
                                       '--reason', 'zz_unknown', '--limit', '0', '--format', format]), 0)
            if format == 'json':
                result = json.loads(output.getvalue())
                self.assertEqual(result['reason_selection']['matched'], [reason])
                self.assertEqual(result['reason_selection']['unmatched'], ['zz_unknown'])
                self.assertEqual(result['reason_limit']['selected_count'], 1)
                self.assertEqual(result['summary'], complete['summary'])
            else:
                self.assertIn('"selected_count": 1', output.getvalue())
                self.assertIn('zz_unknown', output.getvalue())

    def test_limited_output_cannot_overwrite_its_input(self):
        storage = ROOT / 'local-evidence/coverage-reason-limit'
        storage.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=storage) as directory:
            path = Path(directory) / 'saved.json'
            original = (ROOT / 'examples/mixed.audit.json').read_bytes()
            path.write_bytes(original)
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['coverage', '--report', str(path), '--limit', '0', '--output', str(path)]), 2)
            self.assertEqual(path.read_bytes(), original)
