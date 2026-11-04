"""Reject misleading retained plan identity in structured Swift text."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION='Success operation (structural; runtime unproven):'
LITERAL='Recorded literal outcomes (structural; runtime unproven):'


class TextPlanIdentityTests(unittest.TestCase):
    def test_inconsistent_kind_or_label_withholds_structured_output(self):
        for name,layout in LAYOUTS:
            for word,label in ((0x91001400,OPERATION),(0xd2800540,LITERAL)):
                original=report(layout((word,)))
                self.assertIn(label,render_swift_error_text(original))
                for field,values in (('kind',('runtime_handler',None,1,[])),
                                     ('label',('Confirmed runtime handler',None,1,[]))):
                    for bad in values:
                        value=deepcopy(original);value['calls'][0]['presentation']['display_plan'][field]=bad
                        with self.subTest(layout=name,word=word,field=field,bad=bad):
                            text=render_swift_error_text(value)
                            self.assertNotIn(label,text)
                            self.assertNotIn('Condition (structural):',text)
                            self.assertIn('Structured plan malformed (raw):',text)
                    value=deepcopy(original);del value['calls'][0]['presentation']['display_plan'][field]
                    self.assertNotIn(label,render_swift_error_text(value))

    def test_misleading_label_stays_raw_and_missing_error_is_independent(self):
        for name,layout in LAYOUTS:
            value=report(layout((0x91001400,)));del value['calls'][0]['error_constant']
            with self.subTest(layout=name):
                self.assertIn(OPERATION,render_swift_error_text(value))
                value['calls'][0]['presentation']['display_plan']['label']='Confirmed runtime handler'
                text=render_swift_error_text(value)
                self.assertNotIn(OPERATION,text)
                self.assertNotIn('  Label: "Confirmed runtime handler"',text)
                self.assertIn('"label": "Confirmed runtime handler"',text)
