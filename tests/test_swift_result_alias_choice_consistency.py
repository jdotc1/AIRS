"""Reconcile recorded call-result aliases at the paired-choice boundary."""
from copy import deepcopy
import unittest
from airs.swift_error_flow import _return_choice, _bind_choice_result_aliases
from test_swift_literal_outcome_summary import report
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_return_choice_tail_binding import shared_variants, selected_outcomes
from test_swift_success_entry_choice_tail import direct_variants
from test_swift_success_arm_choice_binding import sync_success_records

class ResultAliasChoiceConsistencyTests(unittest.TestCase):
    def test_existing_result_variants_remain_choices(self):
        cases = [(name, words) for name, words in shared_variants() if not name.endswith('_literal')]
        cases += [(name, words) for name, words in direct_variants() if not name.endswith('_literal')]
        for name, words in cases:
            with self.subTest(name=name):
                call = report(words)['calls'][0]; before = deepcopy(call)
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
                self.assertEqual(call, before)

    def test_synchronized_unknown_arithmetic_source_is_withheld(self):
        for name, layout in LAYOUTS:
            with self.subTest(name=name):
                call = report(layout((0x91001400,)))['calls'][0]
                row = call['error_region']['success_interval']['instructions'][0]
                row['word'] = '0x91001660'
                call['success_result']['adjustment_source_register'] = 19
                sync_success_records(call)
                arm = [row for row in call['success_result']['instructions'] if row['phase'] == 'success']
                with self.assertRaisesRegex(ValueError, 'Result arithmetic source'):
                    _bind_choice_result_aliases(call, call['success_result'], arm)
                self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')

    def test_false_status_and_stale_alias_list_are_withheld(self):
        for name, words in direct_variants():
            if name.endswith('_literal'): continue
            call = report(words)['calls'][0]
            for key, value in (('status', 'copied_register_candidate' if 'preserved' in name else 'preserved_register_candidate'),
                               ('result_registers_before_tail', ['x0', 'x19', 'x20'])):
                with self.subTest(name=name, field=key):
                    changed = deepcopy(call); changed['success_result'][key] = value
                    self.assertEqual(_return_choice(changed)['status'], 'unresolved')

    def test_cross_register_shift_and_stale_original_boundaries(self):
        for name, layout in LAYOUTS:
            with self.subTest(name=name):
                good = report(layout((0xaa0003f3, 0x91400674, 0xaa1403e0)))['calls'][0]
                self.assertEqual(_return_choice(good)['status'], 'structural_choice_candidate')
                self.assertEqual(good['return_choice']['success']['immediate'], 4096)
                bad = report(layout((0xaa0003f3, 0x91001400, 0xaa1303e0)))['calls'][0]
                self.assertEqual(_return_choice(bad)['status'], 'unresolved')

    def test_synchronized_stale_original_copy_is_withheld_after_adjustment(self):
        for name, layout in LAYOUTS:
            with self.subTest(name=name):
                call = report(layout((0xaa0003f3, 0x91400674, 0xaa1403e0)))['calls'][0]
                call['error_region']['success_interval']['instructions'][2]['word'] = '0xaa1303e0'
                sync_success_records(call)
                arm = [row for row in call['success_result']['instructions'] if row['phase'] == 'success']
                with self.assertRaisesRegex(ValueError, 'Result alias outcome mismatch'):
                    _bind_choice_result_aliases(call, call['success_result'], arm)
                self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')
