"""Bind the independent success-operation line to the recorded call word."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION = 'Success operation (structural; runtime unproven):'
PAIR = 'Recorded adjusted-result/error outcomes (structural; runtime unproven):'


class TextOperationCallBindingTests(unittest.TestCase):
    def test_recorded_call_is_required_across_existing_adjusted_layouts(self):
        for name, layout in LAYOUTS:
            for word in (0x91001400, 0xd1001400):
                original = report(layout((word,)))
                with self.subTest(layout=name, word=word, case='valid'):
                    self.assertIn(OPERATION, render_swift_error_text(original))
                for field, bad in (('call_word', '0xd503201f'), ('call_word', None),
                                   ('call_word', '0x94000000'), ('callee_pc', '0x0'),
                                   ('call_pc', '0x00')):
                    value = deepcopy(original); value['calls'][0][field] = bad
                    with self.subTest(layout=name, word=word, field=field, bad=bad):
                        text = render_swift_error_text(value)
                        self.assertNotIn(OPERATION, text)
                        self.assertNotIn(PAIR, text)
                        self.assertIn('Result-path instruction:', text)
                        self.assertIn('Call evidence:', text)
                value = deepcopy(original); del value['calls'][0]['call_word']
                self.assertNotIn(OPERATION, render_swift_error_text(value))

    def test_operation_does_not_depend_on_error_pair(self):
        value = report(LAYOUTS[0][1]((0x91001400,)))
        del value['calls'][0]['error_constant']
        text = render_swift_error_text(value)
        self.assertIn(OPERATION, text)
        self.assertNotIn(PAIR, text)
