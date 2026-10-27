"""Bounded CMP W MOVK success updates with known-state and zero extension."""
import unittest
from test_swift_cmp_success_literals import report, WORDS
from test_swift_cmp_movk_literals import words


def wmovk(value, shift=0, register=0):
    return 0x72800000 | ((shift//16)<<21) | (value<<5) | register


class CmpWMovkFirstTests(unittest.TestCase):
    def test_w_update_clears_x_high_bits_in_bound_literal_choice(self):
        call = report(words((0x92800000, wmovk(0,16))))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000ffff')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x000000000000ffff')
        self.assertFalse(call['return_choice']['runtime_value_proven'])

class CmpWMovkBoundaryTests(unittest.TestCase):
    def test_both_lanes_truncate_prior_x_seed(self):
        for shift, expected in ((0, '0x00000000ffff1234'), (16, '0x000000001234ffff')):
            call = report(words((0x92800000, wmovk(0x1234,shift))))['calls'][0]
            self.assertEqual(call['success_constant']['constant_bits'], expected)

    def test_repeated_updates_and_w_seed(self):
        call = report(words((0x52800540, wmovk(0x1234), wmovk(0xabcd,16))))['calls'][0]
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x00000000abcd1234')

    def test_unknown_movk_is_not_a_seed(self):
        call = report(words((wmovk(1), wmovk(2,16))))['calls'][0]
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_unknown_copy_invalidates_seed(self):
        call = report(words((0x52800540, 0xaa1403e0, wmovk(1,16))))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'declined')

    def test_update_temporary_then_x_copy(self):
        call = report(words((0x12800013, wmovk(0x1234,16,19), 0xaa1303e0)))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000001234ffff')

    def test_x_update_can_restore_high_bits_after_w_truncation(self):
        call = report(words((0x92800000, wmovk(0,16), 0xf2f579a0)))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0xabcd00000000ffff')

    def test_reserved_w_shifts_stay_rejected(self):
        for word in (0x72c00000, 0x72e00000):
            self.assertEqual(report(words((0x52800540, word)))['calls'][0]['status'], 'declined')

    def test_w_update_invalidates_entire_error_alias(self):
        call = report(words((wmovk(1,16,21),)))['calls'][0]
        self.assertEqual(call['reason'], 'error_value_clobbered')
        call = report((0xaa1503f3, wmovk(1,16,21), 0x52800540,
            0xf100027f, 0x54000080, 0xaa1303e0, 0x94000009,
            0x92800000, 0xd65f03c0))['calls'][0]
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_unknown_w_copy_and_cbz_prefixes_do_not_produce_outcome(self):
        call = report(words((0x52800540, wmovk(1), 0x2a1303e0)))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'declined')
        for branch in (0xb4000095, 0xb5000095):
            call = report((0x52800540, wmovk(1), branch, *WORDS[3:], 0xd65f03c0))['calls'][0]
            self.assertEqual(call['reason'], 'literal_prefix_requires_compare_test')

    def test_prefix_budget_remains_eight(self):
        exact = report(words((0x52800540, *(wmovk(i) for i in range(5)))))['calls'][0]
        self.assertEqual(exact['success_constant']['status'], 'constant_register_candidate')
        over = report(words((0x52800540, *(wmovk(i) for i in range(6)))))['calls'][0]
        self.assertEqual(over['status'], 'declined')

    def test_tail_side_entry_prevents_updated_literal(self):
        call = report((*words((0x52800540, wmovk(1,16))), 0x17ffffff))['calls'][0]
        self.assertEqual(call['success_constant']['reason'], 'unexpected_return_tail_entry')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

class CmpWMovkDeliveryTests(unittest.TestCase):
    def test_zero_register_update_is_discarded_with_false_proof_flags(self):
        call = report(words((0x52800540, wmovk(0xffff,16,31))))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')
        for key in ('source_reconstruction_allowed', 'runtime_value_proven',
                    'caller_return_type_proven', 'exclusive_path_proven'):
            self.assertFalse(call['return_choice'][key])

    def test_text_preserves_width_update_and_bits(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report(words((0x92800000, wmovk(0,16)))))
        for expected in ('0x72a00000', '0x000000000000ffff',
                         'structural_choice_candidate', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_json_retains_updated_w_literal_choice(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        from test_swift_error_flow import image
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-w-movk'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(words((0x92800000, wmovk(0,16)))).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['success']['constant_bits'], '0x000000000000ffff')
            self.assertFalse(choice['same_constant_bits'])
