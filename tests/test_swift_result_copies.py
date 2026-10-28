"""Selected-path 64-bit result copies, not source reconstruction."""
import unittest
from test_swift_success_result import report, NOP
from test_swift_shared_epilogue import WORDS

SAVE = 0xaa0003f3  # MOV x19,x0
RESTORE = 0xaa1303e0  # MOV x0,x19

class ResultCopiesFirstTests(unittest.TestCase):
    def test_saved_result_restored_after_success_clobber(self):
        words = (SAVE, 0xaa1f03e0) + WORDS[:5] + (RESTORE,) + WORDS[6:]
        value = report(words)
        result = value['calls'][0]['success_result']
        self.assertEqual(result['status'], 'copied_register_candidate')
        self.assertEqual(result['result_registers_before_tail'], ['x0', 'x19'])
        self.assertFalse(result['runtime_value_proven'])

class ResultCopiesBoundaryTests(unittest.TestCase):
    def test_killed_saved_copy_does_not_reappear(self):
        words = (SAVE, 0xaa1f03f3) + WORDS[:5] + (RESTORE,) + WORDS[6:]
        call = report(words)['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['success_result']['reason'], 'success_result_not_preserved')

    def test_live_transitive_copy_survives_other_alias_kills(self):
        words = (SAVE, 0xaa1303f4, 0xaa1f03f3, 0xaa1f03e0) + WORDS[:5] + (0xaa1403e0,) + WORDS[6:]
        result = report(words)['calls'][0]['success_result']
        self.assertEqual(result['status'], 'copied_register_candidate')
        self.assertEqual(result['result_registers_before_tail'], ['x0', 'x20'])

    def test_copy_not_restored_before_tail_withholds(self):
        words = (SAVE, 0xaa1f03e0) + WORDS[:5] + (NOP,) + WORDS[6:]
        self.assertEqual(report(words)['calls'][0]['success_result']['reason'], 'result_not_restored_to_x0')

    def test_pipeline_refuses_narrow_copy_and_zero_register_result(self):
        for save, restore in ((0x2a0003f3, RESTORE), (0xaa0003ff, 0xaa1f03e0)):
            words = (save,) + WORDS[:5] + (restore,) + WORDS[6:]
            self.assertEqual(report(words)['calls'][0]['success_result']['status'], 'declined')

    def test_x0_self_copy_preserves_without_claiming_restoration(self):
        value = report(WORDS[:5] + (0xaa0003e0,) + WORDS[6:])
        self.assertEqual(value['calls'][0]['success_result']['status'], 'preserved_register_candidate')

    def test_success_constant_kills_saved_alias(self):
        # Save x0 before the test; overwrite x19 in success, then attempt restore.
        # Inserting a word in success requires extending the error-arm join branch.
        words = (SAVE,) + WORDS[:4] + (0x14000003, 0xd2800013, RESTORE) + WORDS[6:]
        call = report(words)['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['success_result']['reason'], 'success_result_not_preserved')

    def test_forward_layout_restores_copy_and_retains_proof_limits(self):
        from test_swift_forward_error_arm import WORDS as forward
        from airs.swift_error_text import render_swift_error_text
        words = (SAVE, 0xaa1f03e0) + forward[:1] + (RESTORE,) + forward[2:]
        value = report(words); result = value['calls'][0]['success_result']
        self.assertEqual(result['status'], 'copied_register_candidate')
        for key in ('runtime_value_proven', 'exclusive_path_proven', 'caller_return_type_proven', 'source_reconstruction_allowed'):
            self.assertFalse(result[key])
        self.assertIn('copied_register_candidate', render_swift_error_text(value))
        self.assertIn('swift-success-result-v20', render_swift_error_text(value))
