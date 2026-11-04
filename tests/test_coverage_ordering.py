"""Bounded ordering checks on saved inventory projections; no image analysis."""
from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from airs.cli import main
from airs.coverage_text import render_coverage_text
from airs.types import InputError
from test_coverage_limit import inventory

ROOT = Path(__file__).resolve().parents[1]


class CoverageOrderingTests(unittest.TestCase):
    def test_cli_reason_order_precedes_limit_and_matches_text_order(self):
        outputs = {}
        for format in ['json', 'text']:
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['coverage', '--report', str(ROOT / 'examples/mixed.audit.json'),
                                       '--sort', 'reason', '--limit', '2', '--format', format]), 0)
            outputs[format] = output.getvalue()
        result = json.loads(outputs['json'])
        self.assertEqual(result['reason_order'], 'reason')
        self.assertEqual(result['reason_limit']['returned_count'], 2)
        self.assertEqual(result['reason_limit']['selected_count'], 4)
        self.assertEqual(result['summary']['function_count'], 9)
        reasons = [row['reason'] for row in result['reasons']]
        self.assertEqual(reasons, sorted(reasons))
        printed = [json.loads(line.removeprefix('Reason: '))['reason']
                   for line in outputs['text'].splitlines() if line.startswith('Reason: ')]
        self.assertEqual(printed, reasons)
        self.assertIn('Reason order: "reason"', outputs['text'])

    def test_literal_order_detaches_examples_and_preserves_full_context(self):
        from airs.coverage_ordering import order_coverage_reasons
        original = inventory()
        before = deepcopy(original)
        result = order_coverage_reasons(original, 'reason')
        self.assertEqual([r['reason'] for r in result['reasons']], ['a_tied', 'b_tied', 'z_high'])
        for key in original.keys() - {'reasons'}:
            self.assertEqual(result[key], original[key])
        result['reasons'][0]['examples'][0]['finding_id'] = 'changed'
        result['reports'][0]['duplicate_of'] = 3
        result['reason_selection']['matched'].append('changed')
        self.assertEqual(original, before)

    def test_default_count_order_retains_shape_and_rank(self):
        from airs.coverage_ordering import order_coverage_reasons
        original = inventory()
        result = order_coverage_reasons(original)
        self.assertEqual(result, original)
        self.assertNotIn('reason_order', result)
        result['reasons'][0]['count'] = 999
        self.assertEqual(original['reasons'][0]['count'], 4)

    def test_empty_and_equal_count_rows_use_literal_code_order(self):
        from airs.coverage_ordering import order_coverage_reasons
        original = inventory()
        for row in original['reasons']:
            row['count'] = 2
        result = order_coverage_reasons(original, 'reason')
        self.assertEqual([r['reason'] for r in result['reasons']], ['a_tied', 'b_tied', 'z_high'])
        original['reasons'] = []
        empty = order_coverage_reasons(original, 'reason')
        self.assertEqual(empty['reasons'], [])
        self.assertEqual(empty['summary'], original['summary'])
        self.assertEqual(empty['reason_order'], 'reason')

    def test_invalid_helper_and_cli_orders_reject_before_report_io(self):
        from airs.coverage_ordering import validate_coverage_order, order_coverage_reasons
        for value in [None, True, 1, [], 'COUNT', 'source', 'reason\n']:
            with self.subTest(value=value), self.assertRaises(InputError) as caught:
                order_coverage_reasons(inventory(), value)
            self.assertEqual(caught.exception.code, 'invalid_coverage_order')
        self.assertEqual(validate_coverage_order('count'), 'count')
        with patch('airs.cli.Path.stat') as stat, patch('airs.cli.load_report') as load:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(['coverage', '--report', '/missing/report', '--sort', 'invalid'])
            self.assertEqual(caught.exception.code, 2)
            stat.assert_not_called()
            load.assert_not_called()

    def test_explicit_count_order_keeps_highest_count_first_in_text(self):
        from airs.coverage_ordering import order_coverage_reasons
        text = render_coverage_text(order_coverage_reasons(inventory(), 'count'))
        rows = [json.loads(line.removeprefix('Reason: '))['reason']
                for line in text.splitlines() if line.startswith('Reason: ')]
        self.assertEqual(rows, ['z_high', 'a_tied', 'b_tied'])
        self.assertNotIn('Reason order:', text)

    def test_selection_composes_with_order_and_zero_limit(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(main(['coverage', '--report', str(ROOT / 'examples/mixed.audit.json'),
                                   '--reason', 'zz_unknown', '--sort', 'reason', '--limit', '0']), 0)
        result = json.loads(output.getvalue())
        self.assertEqual(result['reasons'], [])
        self.assertEqual(result['reason_selection']['unmatched'], ['zz_unknown'])
        self.assertEqual(result['reason_limit']['selected_count'], 0)
        self.assertEqual(result['reason_order'], 'reason')
        self.assertEqual(result['summary']['function_count'], 9)
