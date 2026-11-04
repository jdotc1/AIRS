"""Eligible presentations cannot retain a blocked post-call ledger."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import _return_choice, RETURN_CHOICE_MODEL
from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report


class PostcallPresentationConsistencyTests(unittest.TestCase):
    def test_retained_postcall_ledger_conflicts_with_eligible_presentation(self):
        self.assertEqual(RETURN_CHOICE_MODEL, 'swift-return-choice-v45')
        for name, layout in LAYOUTS:
            for word in (0xd2800540, 0x91001400):
                original=report(layout((word,)))
                self.assertEqual(_return_choice(original['calls'][0])['status'], 'structural_choice_candidate')
                for ledger in ({'status':'unexpected_direct_entries'}, {'status':'unresolved'},
                               {'status':'no_unexpected_direct_entries'}, None, [], 'bad'):
                    value=deepcopy(original); call=value['calls'][0]
                    call['presentation']['postcall_entry_validation']=ledger
                    with self.subTest(layout=name, word=word, ledger=ledger):
                        choice=_return_choice(call)
                        self.assertEqual(choice['status'], 'unresolved')
                        self.assertEqual(choice['reason'], 'outcome_evidence_inconsistent')
                        self.assertIs(choice['runtime_value_proven'], False)
                        text=render_swift_error_text(value)
                        self.assertIn('Post-call entry validation',text)
                        self.assertIn('Structured plan: withheld',text)
                        self.assertNotIn('Recorded literal outcomes (structural; runtime unproven):',text)
                        self.assertNotIn('Recorded adjusted-result/error outcomes (structural; runtime unproven):',text)
                        self.assertNotIn('Success operation (structural; runtime unproven):',text)

    def test_absent_ledger_keeps_independent_success_operation(self):
        for name, layout in LAYOUTS:
            value=report(layout((0x91001400,)));call=value['calls'][0]
            self.assertNotIn('postcall_entry_validation',call['presentation'])
            del call['error_constant']
            with self.subTest(layout=name):
                self.assertIn('Success operation (structural; runtime unproven):',render_swift_error_text(value))

    def test_conflicting_ledger_does_not_label_valid_plan_malformed(self):
        value=report(LAYOUTS[0][1]((0x91001400,)))
        value['calls'][0]['presentation']['postcall_entry_validation']={'status':'unexpected_direct_entries'}
        text=render_swift_error_text(value)
        self.assertIn('Structured plan withheld with conflicting post-call ledger (raw):',text)
        self.assertNotIn('Structured plan malformed (raw):',text)
