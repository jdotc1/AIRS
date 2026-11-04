"""Bind the standalone success operation to its retained callee declaration."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION = 'Success operation (structural; runtime unproven):'
PAIR = 'Recorded adjusted-result/error outcomes (structural; runtime unproven):'


class OperationCalleeBindingTests(unittest.TestCase):
    def test_callee_result_is_required_across_adjusted_layouts(self):
        for name, layout in LAYOUTS:
            for word in (0x91001400, 0xd1001400):
                original=report(layout((word,)))
                self.assertIn(OPERATION, render_swift_error_text(original))
                for bad in ('Swift.Void', 'Unknown', None, 1):
                    value=deepcopy(original); value['calls'][0]['callee']['result']=bad
                    with self.subTest(layout=name, word=word, result=bad):
                        text=render_swift_error_text(value)
                        self.assertNotIn(OPERATION, text); self.assertNotIn(PAIR, text)
                        self.assertIn('Callee declaration (not runtime identity):', text)
                value=deepcopy(original); del value['calls'][0]['callee']['result']
                self.assertNotIn(OPERATION, render_swift_error_text(value))
                for bad in (None, [], 'callee', 1):
                    value=deepcopy(original); value['calls'][0]['callee']=bad
                    self.assertNotIn(OPERATION, render_swift_error_text(value))
                value=deepcopy(original); del value['calls'][0]['callee']
                self.assertNotIn(OPERATION, render_swift_error_text(value))

    def test_missing_error_outcome_keeps_int_operation(self):
        for name, layout in LAYOUTS:
            value=report(layout((0x91001400,))); del value['calls'][0]['error_constant']
            with self.subTest(layout=name):
                text=render_swift_error_text(value)
                self.assertIn(OPERATION, text); self.assertNotIn(PAIR, text)
