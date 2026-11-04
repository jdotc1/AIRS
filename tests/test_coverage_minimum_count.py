"""Frequency-based presentation over supplied saved-report inventory only."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from airs.cli import main
from airs.coverage import coverage_inventory
from airs.coverage_text import render_coverage_text
from airs.report import load_report
from airs.types import InputError

ROOT = Path(__file__).resolve().parents[1]


class CoverageMinimumCountTests(unittest.TestCase):
    def test_cli_threshold_composes_with_selection_order_and_limit(self):
        path = ROOT / 'examples/mixed.audit.json'
        complete = coverage_inventory([load_report(path)])
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['coverage', '--report', str(path), '--minimum-count', '2',
                                   '--reason', 'unsupported_control_flow', '--reason', 'missing_reason',
                                   '--sort', 'reason', '--limit', '1']), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['summary'], complete['summary'])
        self.assertEqual(result['reason_selection']['unmatched'], ['missing_reason'])
        self.assertEqual(result['reason_frequency_selection'], {
            'minimum_count': 2, 'input_count': 1, 'selected_count': 0, 'omitted_count': 1})
        self.assertEqual(result['reason_order'], 'reason')
        self.assertEqual(result['reason_limit']['selected_count'], 0)

    def test_inclusive_boundary_preserves_context_and_detaches_nested_values(self):
        from airs.coverage_frequency import select_coverage_frequency
        value = coverage_inventory([load_report(ROOT / 'examples/mixed.audit.json')])
        value['reasons'][0]['count'] = 3
        value['reasons'][1]['count'] = 2
        before = deepcopy(value)
        result = select_coverage_frequency(value, 2)
        self.assertEqual([r['count'] for r in result['reasons']], [3, 2])
        for key in value.keys() - {'reasons'}:
            self.assertEqual(result[key], value[key])
        result['reasons'][0]['examples'].clear()
        result['reports'].clear()
        self.assertEqual(value, before)

    def test_absent_and_positive_boundaries(self):
        from airs.coverage_frequency import select_coverage_frequency
        value = coverage_inventory([load_report(ROOT / 'examples/mixed.audit.json')])
        default = select_coverage_frequency(value)
        self.assertEqual(default, value)
        self.assertNotIn('reason_frequency_selection', default)
        default['reports'].clear()
        self.assertTrue(value['reports'])
        self.assertEqual(select_coverage_frequency(value, 1)['reasons'], value['reasons'])
        result = select_coverage_frequency(value, 10**30)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['reason_frequency_selection']['omitted_count'], len(value['reasons']))

    def test_invalid_values_reject_before_report_io(self):
        from airs.coverage_frequency import validate_coverage_minimum_count
        for value in [True, False, 0, -1, 1.5, '2']:
            with self.subTest(value=value), self.assertRaises(InputError) as caught:
                validate_coverage_minimum_count(value)
            self.assertEqual(caught.exception.code, 'invalid_coverage_minimum_count')
        for value in ['0', '-1']:
            with patch('airs.cli.Path.stat') as stat, patch('airs.cli.load_report') as load:
                with contextlib.redirect_stderr(io.StringIO()) as error:
                    self.assertEqual(main(['coverage', '--report', '/missing', '--minimum-count', value]), 2)
                stat.assert_not_called()
                load.assert_not_called()
                self.assertEqual(json.loads(error.getvalue())['error']['code'], 'invalid_coverage_minimum_count')

    def test_text_exposes_frequency_omissions_and_original_denominators(self):
        from airs.coverage_frequency import select_coverage_frequency
        value = coverage_inventory([load_report(ROOT / 'examples/mixed.audit.json')])
        text = render_coverage_text(select_coverage_frequency(value, 2))
        self.assertIn('Reason frequency selection (does not filter denominators)', text)
        self.assertIn('"minimum_count": 2', text)
        self.assertIn('"selected_count": 0', text)
        self.assertIn('"function_count": 9', text)
        self.assertIn('this is not real-world prevalence', text)

    def test_duplicate_inputs_do_not_inflate_frequency(self):
        from airs.coverage_frequency import select_coverage_frequency
        value = load_report(ROOT / 'examples/mixed.audit.json')
        inventory = coverage_inventory([value, deepcopy(value)])
        result = select_coverage_frequency(inventory, 2)
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['reports'], inventory['reports'])
        self.assertEqual(result['summary'], inventory['summary'])
