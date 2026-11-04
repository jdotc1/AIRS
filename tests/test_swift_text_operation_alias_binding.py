"""Reconcile the independent success operation with recorded result aliases."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION = 'Success operation (structural; runtime unproven):'
PAIR = 'Recorded adjusted-result/error outcomes (structural; runtime unproven):'


class TextOperationAliasBindingTests(unittest.TestCase):
    def test_unknown_source_alias_is_not_described_as_call_result(self):
        for name, layout in LAYOUTS:
            value = report(layout((0x91001400,)))
            call = value['calls'][0]; result = call['success_result']
            self.assertIn(OPERATION, render_swift_error_text(value))
            # add x0, x19, #5: x19 was never assigned a call-result alias.
            for rows in (call['error_region']['success_interval']['instructions'],
                         call['presentation']['display_plan']['success_interval']['instructions'],
                         result['instructions']):
                for row in rows:
                    if row['word'] == '0x91001400': row['word'] = '0x91001660'
            result['adjustment_source_register'] = 19
            text = render_swift_error_text(value)
            with self.subTest(layout=name):
                self.assertNotIn(OPERATION, text)
                self.assertNotIn(PAIR, text)
                self.assertIn('Result-path instruction:', text)
                self.assertIn('0x91001660', text)

    def test_alias_list_must_match_but_error_pair_remains_independent(self):
        for name, layout in LAYOUTS:
            for word in (0x91001400, 0xd1001400):
                value = report(layout((word,)))
                del value['calls'][0]['error_constant']
                with self.subTest(layout=name, word=word):
                    self.assertIn(OPERATION, render_swift_error_text(value))
                    value['calls'][0]['success_result']['result_registers_before_tail'] = ['x0', 'x19']
                    self.assertNotIn(OPERATION, render_swift_error_text(value))

    def test_live_copied_alias_and_shifted_adjustment_remain_available(self):
        for name, layout in LAYOUTS:
            for operation in (0x91400674, 0xd1400674):
                words = (0xaa0003f3, 0xaa1f03e0, *layout((operation, 0xaa1403e0)))
                value = report(words)
                del value['calls'][0]['error_constant']
                with self.subTest(layout=name, operation=hex(operation)):
                    self.assertIn(OPERATION, render_swift_error_text(value))

    def test_stale_postcall_branch_withholds_operation_and_preserves_raw_rows(self):
        for name, layout in LAYOUTS:
            value = report(layout((0x91001400,)))
            value['calls'][0]['window'][-1]['word'] = '0xd503201f'
            with self.subTest(layout=name):
                text = render_swift_error_text(value)
                self.assertNotIn(OPERATION, text)
                self.assertIn('Post-call instruction evidence:', text)
                self.assertIn('0xd503201f', text)
