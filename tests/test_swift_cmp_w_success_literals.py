"""Bounded W move-wide CMP success seeds with explicit zero extension."""
import unittest
from test_swift_cmp_success_literals import report, WORDS


class CmpWFirstTests(unittest.TestCase):
    def test_w_movn_zero_extends_literal_in_structural_choice(self):
        call = report((0x12800000, *WORDS[1:]))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'], '0x00000000ffffffff')
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x00000000ffffffff')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xffffffffffffffff')
        self.assertFalse(call['return_choice']['same_constant_bits'])
        self.assertFalse(call['return_choice']['runtime_value_proven'])

class CmpWBoundaryTests(unittest.TestCase):
    def test_movz_and_movn_at_both_legal_shifts(self):
        for seed, expected in ((0x52824680, '0x0000000000001234'),
            (0x52a24680, '0x0000000012340000'), (0x12824680, '0x00000000ffffedcb'),
            (0x12a24680, '0x00000000edcbffff')):
            with self.subTest(seed=hex(seed)):
                call = report((seed, *WORDS[1:]))['calls'][0]
                self.assertEqual(call['success_constant']['constant_bits'], expected)

    def test_w_seed_clears_high_bits_of_prior_x_literal(self):
        call = report((0x92800000, 0x52800540, *WORDS[1:], 0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')

    def test_full_width_copy_preserves_zero_extended_seed(self):
        call = report((0x12800013, 0xaa1303e0, *WORDS[1:], 0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x00000000ffffffff')

    def test_existing_x_movk_can_update_zero_extended_w_seed(self):
        call = report((0x12800000, 0xf2f579a0, *WORDS[1:], 0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0xabcd0000ffffffff')

    def test_reserved_w_halfword_positions_decline(self):
        for seed in (0x52c00000, 0x52e00000, 0x12c00000, 0x12e00000):
            with self.subTest(seed=hex(seed)):
                self.assertEqual(report((seed, *WORDS[1:]))['calls'][0]['status'], 'declined')

    def test_w_writes_invalidate_full_error_alias(self):
        call = report((0x52800555, *WORDS[1:]))['calls'][0]
        self.assertEqual(call['reason'], 'error_value_clobbered')
        call = report((0xaa1503f3, 0x52800553, 0xf100027f,
                       0x54000080, 0xaa1303e0, 0x9400000b,
                       0x92800000, 0xd65f03c0))['calls'][0]
        self.assertEqual(call['reason'], 'not_error_result_comparison')

    def test_saved_x_error_alias_survives_w_overwrite_of_original(self):
        call = report((0xaa1503f3, 0x52800555, 0xaa1503e0,
                       0xf100027f, 0x54000080, 0xaa1303e0,
                       0x94000009, 0x92800000, 0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_unknown_w_copy_does_not_create_literal(self):
        for word in (0x2a1303e0,):
            call = report((0x52800540, word, *WORDS[1:], 0xd65f03c0))['calls'][0]
            self.assertEqual(call['success_constant']['status'], 'declined')

    def test_w_seed_does_not_enable_cbz_or_narrow_error_test(self):
        for branch in (0xb4000095, 0xb5000095, 0x34000095):
            call = report((0x52800540, branch, *WORDS[3:]))['calls'][0]
            self.assertEqual(call['status'], 'declined')

    def test_tail_entry_and_unknown_caller_still_withhold_literal(self):
        for tail in ((0xd65f03c0, 0x17ffffff), (0xffffffff,)):
            call = report((0x12800000, *WORDS[1:], *tail))['calls'][0]
            self.assertEqual(call['success_constant']['status'], 'declined')
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_prefix_budget_remains_eight_words(self):
        exact = report((*(0xd503201f,)*5, 0x12800000, *WORDS[1:]))['calls'][0]
        self.assertEqual(exact['success_constant']['constant_bits'], '0x00000000ffffffff')
        over = report((*(0xd503201f,)*6, 0x12800000, *WORDS[1:]))['calls'][0]
        self.assertEqual(over['status'], 'declined')

class CmpWDeliveryTests(unittest.TestCase):
    def test_zr_write_does_not_corrupt_literal_or_enable_proof(self):
        call = report((0x52800540, 0x1280001f, *WORDS[1:], 0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')
        for key in ('source_reconstruction_allowed', 'runtime_value_proven',
                    'caller_return_type_proven', 'exclusive_path_proven'):
            self.assertFalse(call['return_choice'][key])

    def test_text_retains_word_width_and_literal_bits(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report((0x12800000, *WORDS[1:])))
        for expected in ('0x12800000', '0x00000000ffffffff', '0xffffffffffffffff',
                         'post_call', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_json_retains_zero_extended_literal_choice(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        from test_swift_error_flow import image
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-w-success-literals'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image((0x12800000, *WORDS[1:])).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['success']['constant_bits'], '0x00000000ffffffff')
            self.assertFalse(choice['same_constant_bits'])
