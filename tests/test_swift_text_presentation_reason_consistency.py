"""Require the producer's eligible reason for structured Swift text."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION='Success operation (structural; runtime unproven):'
LITERAL='Recorded literal outcomes (structural; runtime unproven):'


class TextPresentationReasonConsistencyTests(unittest.TestCase):
    def test_contradictory_or_missing_reason_withholds_structured_output(self):
        for name,layout in LAYOUTS:
            for word,label in ((0x91001400,OPERATION),(0xd2800540,LITERAL)):
                original=report(layout((word,)))
                self.assertIn(label,render_swift_error_text(original))
                for bad in ('unexpected_postcall_entries','edge_not_recovered','postcall_entries_unresolved',None,1,[]):
                    value=deepcopy(original);value['calls'][0]['presentation']['reason']=bad
                    with self.subTest(layout=name,word=word,reason=bad):
                        text=render_swift_error_text(value)
                        self.assertNotIn(label,text)
                        self.assertNotIn('Condition (structural):',text)
                        self.assertIn('Structured plan withheld with inconsistent presentation reason (raw):',text)
                        self.assertIn('Presentation:',text)
                value=deepcopy(original);del value['calls'][0]['presentation']['reason']
                self.assertNotIn(label,render_swift_error_text(value))

    def test_valid_reason_with_missing_error_keeps_standalone_operation(self):
        for name,layout in LAYOUTS:
            value=report(layout((0x91001400,)));del value['calls'][0]['error_constant']
            with self.subTest(layout=name):self.assertIn(OPERATION,render_swift_error_text(value))
