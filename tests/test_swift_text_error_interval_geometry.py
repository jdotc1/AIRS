"""Reject inconsistent retained error-interval geometry in Swift text."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION='Success operation (structural; runtime unproven):'
LITERAL='Recorded literal outcomes (structural; runtime unproven):'


class TextErrorIntervalGeometryTests(unittest.TestCase):
    def test_synchronized_bad_geometry_withholds_structured_output(self):
        for name,layout in LAYOUTS:
            for word,label in ((0x91001400,OPERATION),(0xd2800540,LITERAL)):
                original=report(layout((word,)))
                self.assertIn(label,render_swift_error_text(original))
                for change in ('pc','word','word_case','end','start_format','overflow'):
                    value=deepcopy(original);call=value['calls'][0];region=call['error_region'];plan=call['presentation']['display_plan']['error_interval']
                    if change=='pc': region['instructions'][0]['pc']='0x0'
                    elif change=='word': region['instructions'][0]['word']='0x1'
                    elif change=='word_case': region['instructions'][0]['word']='0xD503201F'
                    elif change=='end': region['end_pc_exclusive']='0x0'
                    elif change=='start_format':
                        region['start_pc']='0x00';call['error_pc']='0x00'
                    else:
                        region['start_pc']='0xfffffffffffffffc';call['error_pc']=region['start_pc']
                        region['end_pc_exclusive']='0x10000000000000008'
                    for key in ('start_pc','end_pc_exclusive','instructions'):plan[key]=deepcopy(region[key])
                    with self.subTest(layout=name,word=word,change=change):
                        text=render_swift_error_text(value)
                        self.assertNotIn(label,text)
                        self.assertNotIn('Condition (structural):',text)
                        self.assertIn('Structured plan malformed (raw):',text)
                        self.assertIn('Region evidence:',text)

    def test_valid_geometry_and_missing_error_keeps_operation(self):
        for name,layout in LAYOUTS:
            value=report(layout((0x91001400,)));del value['calls'][0]['error_constant']
            with self.subTest(layout=name):self.assertIn(OPERATION,render_swift_error_text(value))
