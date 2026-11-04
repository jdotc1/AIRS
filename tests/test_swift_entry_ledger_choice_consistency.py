"""Withhold choices when retained entry ledgers contradict eligibility."""
from copy import deepcopy
import unittest
from airs.swift_error_flow import _return_choice
from test_swift_literal_outcome_summary import report
from test_swift_return_choice_tail_binding import shared_variants
from test_swift_success_entry_choice_tail import direct_variants

class EntryLedgerChoiceConsistencyTests(unittest.TestCase):
    def cases(self):
        for name, words in list(shared_variants()) + list(direct_variants()):
            yield name, report(words)['calls'][0]

    def test_valid_direct_shared_and_caller_lengths_remain_eligible(self):
        for name, call in self.cases():
            with self.subTest(name=name):
                before = deepcopy(call)
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
                self.assertEqual(call, before)

    def test_region_ledger_contradictions_withhold(self):
        changes = (('status', 'unexpected_direct_entries'), ('status', 'unresolved'), ('scope', 'foreign'),
                   ('caller_scan_complete', False), ('entry_details_complete', False),
                   ('unclassified_details_complete', False), ('exclusive_entry_proven', True),
                   ('unexpected_entry_count', True), ('unclassified_word_count', 1),
                   ('scanned_word_count', True), ('scanned_word_count', 0),
                   ('unexpected_entries', [{}]), ('unclassified_words', [{}]), ('unexpected_entries', None))
        for name, original in self.cases():
            for key, value in changes:
                with self.subTest(name=name, field=key, value=value):
                    call = deepcopy(original); call['error_region']['incoming_validation'][key] = value
                    self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')
            for value in (None, [], {}):
                call = deepcopy(original); call['error_region']['incoming_validation'] = value
                self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_cmp_flag_ledger_contradictions_and_scan_mismatch_withhold(self):
        changes = (('status', 'unexpected_direct_entries'), ('scope', 'foreign'),
                   ('caller_scan_complete', False), ('flag_state_proven', True),
                   ('exclusive_entry_proven', True), ('unexpected_entry_count', False),
                   ('unclassified_word_count', 1), ('unexpected_entries', [{}]),
                   ('unclassified_words', [{}]), ('entry_details_complete', False),
                   ('protected_start_pc', '0x0'), ('protected_end_pc_exclusive', '0x0'))
        for name, original in self.cases():
            if original.get('test_kind') != 'cmp_zero_bcond': continue
            for key, value in changes:
                with self.subTest(name=name, field=key):
                    call = deepcopy(original); call['flag_entry_validation'][key] = value
                    self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')
            call = deepcopy(original); call['flag_entry_validation']['scanned_word_count'] += 1
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
            for value in (None, [], {}):
                call = deepcopy(original); call['flag_entry_validation'] = value
                self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_renderer_withholds_stale_ledger_summary_but_keeps_raw_rows(self):
        from airs.swift_error_text import render_swift_error_text
        value = report(); self.assertIn('Recorded literal outcomes', render_swift_error_text(value))
        value['calls'][0]['error_region']['incoming_validation']['status'] = 'unresolved'
        text = render_swift_error_text(value)
        self.assertNotIn('Recorded literal outcomes', text)
        self.assertNotIn('Recorded call-result/error outcomes', text)
        self.assertNotIn('Recorded adjusted-result/error outcomes', text)
        self.assertIn('Error-constant instruction:', text)

    def test_valid_complete_ledgers_with_varied_caller_lengths(self):
        from test_swift_arithmetic_call_binding import LAYOUTS
        for name, layout in LAYOUTS:
            for extra in (0, 1, 5):
                with self.subTest(name=name, extra=extra):
                    call = report(layout((0xd2800540,)) + (0xd503201f,) * extra)['calls'][0]
                    self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
