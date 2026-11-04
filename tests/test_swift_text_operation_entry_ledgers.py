"""Reconcile retained entry ledgers for the standalone success operation."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION = 'Success operation (structural; runtime unproven):'
PAIR = 'Recorded adjusted-result/error outcomes (structural; runtime unproven):'


class OperationEntryLedgerTests(unittest.TestCase):
    def test_region_ledger_contradictions_withhold_operation_and_preserve_raw(self):
        for name, layout in LAYOUTS:
            original = report(layout((0x91001400,)))
            self.assertIn(OPERATION, render_swift_error_text(original))
            for key, bad in (('status', 'unexpected_direct_entries'), ('scope', 'other'),
                             ('caller_scan_complete', False), ('entry_details_complete', False),
                             ('unclassified_details_complete', False), ('unexpected_entry_count', True),
                             ('unclassified_word_count', 1), ('unexpected_entries', [{}]),
                             ('unclassified_words', None), ('exclusive_entry_proven', 0)):
                value=deepcopy(original); value['calls'][0]['error_region']['incoming_validation'][key]=bad
                with self.subTest(layout=name, field=key):
                    text=render_swift_error_text(value)
                    self.assertNotIn(OPERATION, text); self.assertNotIn(PAIR, text)
                    self.assertIn('Incoming validation:', text)

    def test_cmp_flag_ledger_and_missing_error_outcome(self):
        for name, layout in LAYOUTS:
            original=report(layout((0xd1001400,))); call=original['calls'][0]
            del call['error_constant']
            self.assertIn(OPERATION, render_swift_error_text(original))
            if call.get('test_kind') != 'cmp_zero_bcond': continue
            for key,bad in (('status', 'unexpected_direct_entries'), ('flag_state_proven', 0),
                            ('protected_start_pc', '0x0'), ('protected_end_pc_exclusive', '0x0'),
                            ('scanned_word_count', call['flag_entry_validation']['scanned_word_count']+1)):
                value=deepcopy(original); value['calls'][0]['flag_entry_validation'][key]=bad
                with self.subTest(layout=name, field=key):
                    text=render_swift_error_text(value)
                    self.assertNotIn(OPERATION, text)
                    self.assertIn('Flag-entry validation:', text)
