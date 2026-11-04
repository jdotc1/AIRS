"""Reconcile recorded error literal bits with the bounded error arm."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import _return_choice, _bind_choice_error_arm
from test_swift_literal_outcome_summary import report
from test_swift_error_arm_choice_binding import with_error_arm, sync_error_records
from test_swift_error_constants import error_arm


class ErrorLiteralChoiceConsistencyTests(unittest.TestCase):
    def test_changed_literal_bits_and_false_equality_are_withheld(self):
        for layout in ('cbz_direct', 'eq_direct', 'cbz_shared', 'eq_shared', 'cbnz', 'ne'):
            with self.subTest(layout=layout):
                call = report(with_error_arm(layout, (0x92800000,)))['calls'][0]
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
                call['error_constant']['constant_bits'] = '0x000000000000002a'
                self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_valid_move_widths_updates_copies_zero_and_reseed(self):
        arms = ((0x92800000,), (0x12800000,), (0xd2800540, 0xf2a00020),
                (0x12800000, 0x72a00020), (0xd2800553, 0xaa1303e0),
                (0x92800013, 0x2a1303e0), (0xaa1f03e0,),
                (0xd2800000, 0x94000100, 0x92800000))
        for layout in ('cbz_direct', 'eq_direct', 'cbz_shared', 'eq_shared', 'cbnz', 'ne'):
            for arm in arms:
                with self.subTest(layout=layout, arm=arm):
                    call = report(with_error_arm(layout, arm))['calls'][0]
                    original = deepcopy(call)
                    self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
                    self.assertEqual(call, original)

    def test_opaque_call_and_unknown_partial_or_copy_do_not_seed_a_value(self):
        for arm in ((0x92800000, 0x94000100), (0xf2800020,), (0xaa1303e0,),
                    (0xd2800553, 0x94000100, 0xaa1303e0)):
            with self.subTest(arm=arm):
                call = error_arm(arm)['calls'][0]
                self.assertNotEqual(call['error_constant']['status'], 'constant_register_candidate')
                self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_malformed_literal_and_proof_scope_do_not_become_choices(self):
        original = report(with_error_arm('cbz_shared', (0x92800000,)))['calls'][0]
        for bits in (None, 0, '0xFFFFFFFFFFFFFFFF', '0x0', '0x0000000000000000'):
            with self.subTest(bits=bits):
                call = deepcopy(original); call['error_constant']['constant_bits'] = bits
                result = _return_choice(call)
                self.assertEqual(result['status'], 'unresolved')
                self.assertFalse(result['runtime_value_proven'])
                self.assertFalse(result['source_reconstruction_allowed'])

    def test_forged_bound_unknown_error_arm_does_not_create_known_bits(self):
        valid = report(with_error_arm('cbz_shared', (0x92800000,)))['calls'][0]
        for arm in ((0xf2800020,), (0xaa1303e0,), (0x92800000, 0x94000100)):
            with self.subTest(arm=arm):
                call = report(with_error_arm('cbz_shared', arm))['calls'][0]
                replacement = deepcopy(valid['error_constant'])
                replacement['call_pc'] = call['call_pc']
                replacement['error_pc'] = call['error_pc']
                replacement['return_pc'] = call['success_constant']['return_pc']
                replacement['opaque_call_count'] = call['error_region']['opaque_call_count']
                replacement['instructions'] = [deepcopy(row) for row in call['success_constant']['instructions'] if row['phase'] == 'return_tail']
                call['error_constant'] = replacement
                sync_error_records(call)
                tail_count = sum(row['phase'] == 'return_tail' for row in call['error_constant']['instructions'])
                with self.assertRaisesRegex(ValueError, 'Error arm literal mismatch'):
                    _bind_choice_error_arm(call, tail_count, int(call['error_region']['join_pc'], 16))
                self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')
