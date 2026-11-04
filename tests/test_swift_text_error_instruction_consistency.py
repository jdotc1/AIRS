"""Reconcile structured error words with retained instruction metadata."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION='Success operation (structural; runtime unproven):'


class TextErrorInstructionConsistencyTests(unittest.TestCase):
    def test_valid_layouts_and_missing_error_outcome_remain_visible(self):
        for name,layout in LAYOUTS:
            for word in (0x91001400,0xd1001400):
                value=report(layout((word,)));del value['calls'][0]['error_constant']
                with self.subTest(layout=name,word=word):
                    text=render_swift_error_text(value)
                    self.assertIn(OPERATION,text);self.assertIn('Condition (structural):',text)

    def test_synchronized_false_kind_and_unsupported_word_withhold_plan(self):
        for name,layout in LAYOUTS:
            original=report(layout((0x91001400,)))
            for change in ('kind','false_call','unknown','count','bool_count'):
                value=deepcopy(original);call=value['calls'][0];region=call['error_region']
                row=region['instructions'][0]
                if change=='kind':row['kind']='nop' if row['kind']!='nop' else 'mov'
                elif change=='false_call':row.update(kind='bl',call_target_pc='0x0',semantics='opaque_call')
                elif change=='unknown':row.update(word='0xffffffff',kind='nop')
                elif change=='count':region['opaque_call_count']+=1
                else:region['opaque_call_count']=True
                call['presentation']['display_plan']['error_interval']['instructions']=deepcopy(region['instructions'])
                with self.subTest(layout=name,change=change):
                    text=render_swift_error_text(value)
                    self.assertNotIn(OPERATION,text);self.assertNotIn('Condition (structural):',text)
                    self.assertIn('Structured plan malformed (raw):',text)
                    self.assertIn('Region instruction evidence:',text)

    def test_opaque_call_and_branch_metadata_are_reconciled(self):
        original=report();call=original['calls'][0]
        self.assertIn('Condition (structural):',render_swift_error_text(original))
        for kind,field,bad in (('bl','call_target_pc','0x0'),('bl','semantics','returns'),('b','target_pc','0x0')):
            value=deepcopy(original);region=value['calls'][0]['error_region']
            rows=[row for row in region['instructions'] if row['kind']==kind]
            self.assertEqual(len(rows),1)
            rows[0][field]=bad
            value['calls'][0]['presentation']['display_plan']['error_interval']['instructions']=deepcopy(region['instructions'])
            with self.subTest(kind=kind,field=field):
                text=render_swift_error_text(value)
                self.assertNotIn('Condition (structural):',text)
                self.assertIn('Region instruction evidence:',text)
