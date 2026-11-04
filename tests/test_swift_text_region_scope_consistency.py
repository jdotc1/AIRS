"""Retained region proof scope gates structured Swift text."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION='Success operation (structural; runtime unproven):'


class TextRegionScopeConsistencyTests(unittest.TestCase):
    def test_region_status_and_proof_flags_withhold_structured_text(self):
        for name, layout in LAYOUTS:
            for word in (0x91001400, 0xd1001400):
                original=report(layout((word,))); del original['calls'][0]['error_constant']
                self.assertIn(OPERATION,render_swift_error_text(original))
                for field, values in (('status', ('blocked', None, 1)),
                                      ('call_return_proven', (True, 0, None)),
                                      ('join_reachability_proven', (True, 0, None))):
                    for bad in values:
                        value=deepcopy(original);value['calls'][0]['error_region'][field]=bad
                        with self.subTest(layout=name, word=word, field=field, bad=bad):
                            text=render_swift_error_text(value)
                            self.assertNotIn(OPERATION,text)
                            self.assertNotIn('Condition (structural):',text)
                            self.assertIn('Structured plan withheld with inconsistent region scope (raw):',text)
                            self.assertIn('Region evidence:',text)
                    value=deepcopy(original);del value['calls'][0]['error_region'][field]
                    self.assertNotIn(OPERATION,render_swift_error_text(value))

    def test_original_region_and_missing_error_outcome_keep_operation(self):
        for name, layout in LAYOUTS:
            value=report(layout((0x91001400,)));del value['calls'][0]['error_constant']
            with self.subTest(layout=name):
                text=render_swift_error_text(value)
                self.assertIn(OPERATION,text);self.assertIn('Condition (structural):',text)

    def test_literal_pair_withheld_on_region_proof_contradiction(self):
        label='Recorded literal outcomes (structural; runtime unproven):'
        for name, layout in LAYOUTS:
            value=report(layout((0xd2800540,)))
            with self.subTest(layout=name):
                self.assertIn(label,render_swift_error_text(value))
                value['calls'][0]['error_region']['call_return_proven']=True
                text=render_swift_error_text(value)
                self.assertNotIn(label,text)
                self.assertIn('"call_return_proven": true',text)
