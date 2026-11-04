"""Render bounded raw evidence when nested producer records are malformed."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from airs.types import InputError
from test_swift_literal_outcome_summary import report
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_return_choice_tail_binding import selected_outcomes, shared_variants

class SwiftTextMalformedEvidenceTests(unittest.TestCase):
    def assert_withheld(self, value):
        before = deepcopy(value)
        text = render_swift_error_text(value)
        for label in ('Recorded literal outcomes', 'Recorded call-result/error outcomes',
                      'Recorded adjusted-result/error outcomes'):
            self.assertNotIn(label, text)
        self.assertEqual(value, before)
        return text

    def test_malformed_outcome_and_region_containers_show_raw(self):
        for field in ('success_result', 'success_constant', 'error_constant', 'error_region', 'return_choice'):
            for bad in (None, [], 'bad\n\x1b', 7, False):
                with self.subTest(field=field, value=bad):
                    value = report(); value['calls'][0][field] = bad
                    text = self.assert_withheld(value)
                    self.assertIn('raw' if field != 'return_choice' else 'Return choice', text)
                    self.assertNotIn('\x1b', text)
                    if field not in ('error_constant',): self.assertIn('Error-constant instruction:', text)

    def test_malformed_selected_rows_and_window_are_explicit(self):
        for path in ('success', 'error', 'window', 'region'):
            for bad in (None, 'not-a-list', 7, {}):
                with self.subTest(path=path, value=bad):
                    value = report(); call = value['calls'][0]
                    if path == 'window': call['window'] = bad
                    elif path == 'region': call['error_region']['instructions'] = bad
                    else: selected_outcomes(call)[0 if path == 'success' else 1]['instructions'] = bad
                    text = self.assert_withheld(value)
                    self.assertIn('malformed detail (raw)', text)
        value = report(); call = value['calls'][0]; del selected_outcomes(call)[1]['instructions']
        self.assertIn('unavailable (missing field)', self.assert_withheld(value))

    def test_ledger_shapes_and_detail_counts_do_not_become_fake_rows(self):
        value0 = report(dict(LAYOUTS)['eq']((0xd2800540,)))
        for field in ('flag', 'incoming'):
            for bad in (None, [], 'bad', 7):
                with self.subTest(field=field, value=bad):
                    value = deepcopy(value0); call = value['calls'][0]
                    if field == 'flag': call['flag_entry_validation'] = bad
                    else: call['error_region']['incoming_validation'] = bad
                    self.assertIn('malformed (raw)', self.assert_withheld(value))
            for key in ('unexpected_entries', 'unclassified_words'):
                value = deepcopy(value0); call = value['calls'][0]
                ledger = call['flag_entry_validation'] if field == 'flag' else call['error_region']['incoming_validation']
                ledger[key] = 'bad'
                self.assertIn('malformed detail (raw)', self.assert_withheld(value))
                del ledger[key]
                self.assertIn('unavailable (missing field)', self.assert_withheld(value))

    def test_malformed_plans_are_withheld_and_raw_region_survives(self):
        for bad in (None, [], 'bad', 7, {}):
            value = report(); value['calls'][0]['presentation']['display_plan'] = bad
            text = self.assert_withheld(value)
            self.assertIn('Structured plan: withheld', text)
            self.assertIn('Structured plan malformed (raw)', text)
            self.assertIn('Region instruction evidence:', text)
        for field, bad in (('condition', None), ('label', 2), ('success_entry_pc', [])):
            value = report(); value['calls'][0]['presentation']['display_plan'][field] = bad
            self.assertIn('Structured plan: withheld', self.assert_withheld(value))
        value = report(); value['calls'][0]['presentation']['display_plan']['error_interval']['instructions'] = 'bad'
        self.assertIn('Structured plan: withheld', self.assert_withheld(value))

    def test_contradictory_plan_instructions_and_condition_are_raw(self):
        for bad in ([], [{}], [{'pc': 7, 'word': '0x00000000', 'kind': 'ret'}],
                    [{'pc': '0x1', 'word': '0x00000000'}], [{}] * 17):
            value = report(); value['calls'][0]['presentation']['display_plan']['error_interval']['instructions'] = bad
            text = self.assert_withheld(value)
            self.assertIn('Structured plan malformed (raw)', text)
            self.assertNotIn('Condition (structural)', text)
        value = report(); value['calls'][0]['presentation']['display_plan']['condition']['error_when'] = 'zero'
        self.assertIn('Structured plan malformed (raw)', self.assert_withheld(value))

    def test_plan_guard_accepts_valid_shapes_and_withholds_incomplete_shared_plan(self):
        for name, words in shared_variants():
            with self.subTest(layout=name):
                value = report(words)
                text = render_swift_error_text(value)
                self.assertIn('Condition (structural)', text)
                self.assertIn('Shared restore/return candidate', text)
                del value['calls'][0]['presentation']['display_plan']['success_interval']
                self.assertIn('Structured plan malformed (raw)', self.assert_withheld(value))
        for name, layout in LAYOUTS:
            with self.subTest(layout=name):
                value = report(layout((0x91001400,)))
                self.assertIn('Condition (structural)', render_swift_error_text(value))

    def test_plan_guard_rejects_synchronized_cmp_and_shared_proof_contradictions(self):
        value = report(dict(LAYOUTS)['eq']((0xd2800540,)))
        call = value['calls'][0]
        call['comparison_pc'] = None
        call['presentation']['display_plan']['condition']['comparison_pc'] = None
        self.assertIn('Structured plan malformed (raw)', self.assert_withheld(value))
        for name, words in shared_variants():
            with self.subTest(layout=name):
                value = report(words); call = value['calls'][0]
                call['error_region']['shared_epilogue']['restore_state_proven'] = True
                call['presentation']['display_plan']['shared_epilogue']['restore_state_proven'] = True
                self.assertIn('Structured plan malformed (raw)', self.assert_withheld(value))

    def test_forward_shared_plan_requires_exact_complete_flag(self):
        seen = 0
        for name, words in shared_variants():
            value = report(words); call = value['calls'][0]
            if call['error_region'].get('layout') != 'success_fallthrough_error_forward':
                continue
            seen += 1
            self.assertIn('Condition (structural)', render_swift_error_text(value))
            call['error_region']['success_interval']['instructions_complete'] = 1
            call['presentation']['display_plan']['success_interval']['instructions_complete'] = 1
            self.assertIn('Structured plan malformed (raw)', self.assert_withheld(value))
        self.assertGreater(seen, 0)

    def test_shared_proof_flags_require_type_identity_in_both_records(self):
        seen_forward = 0
        for name, words in shared_variants():
            with self.subTest(layout=name):
                value = report(words); call = value['calls'][0]
                call['error_region']['shared_epilogue']['restore_state_proven'] = 0
                self.assertIn('Structured plan malformed (raw)', self.assert_withheld(value))
                value = report(words); call = value['calls'][0]
                if call['error_region'].get('layout') == 'success_fallthrough_error_forward':
                    seen_forward += 1
                    call['error_region']['success_interval']['instructions_complete'] = 1
                    self.assertIn('Structured plan malformed (raw)', self.assert_withheld(value))
        self.assertGreater(seen_forward, 0)

    def test_adjusted_missing_operation_does_not_raise_or_render_pair(self):
        value = report(dict(LAYOUTS)['cbz']((0x91001400,)))
        call = value['calls'][0]
        del call['return_choice']['success']['operation']
        del call['success_result']['operation']
        text = self.assert_withheld(value)
        self.assertIn('Result-path instruction:', text)

    def test_declined_outcomes_and_non_dict_call_or_outer_list(self):
        value = report(); call = value['calls'][0]
        call['success_result'] = {'status': 'declined', 'reason': 'not_selected'}
        self.assertIn('Result-path instruction: unavailable (missing field)', render_swift_error_text(value))
        value = report(); value['calls'].append(None)
        self.assertIn('Call evidence malformed (raw): null', render_swift_error_text(value))
        for bad in (None, 'calls', 7, {}):
            value = report(); value['calls'] = bad
            with self.subTest(value=bad), self.assertRaises(InputError) as caught:
                render_swift_error_text(value)
            self.assertEqual(caught.exception.code, 'swift_text_calls')
