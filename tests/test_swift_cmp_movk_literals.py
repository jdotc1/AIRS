"""Bounded X MOVK updates of known CMP success-prefix literals."""
import unittest
from test_swift_cmp_success_literals import report, WORDS


def movk(value, shift=0, register=0):
    return 0xf2800000 | ((shift//16)<<21) | (value<<5) | register


def words(prefix):
    # Extra RET keeps success inside the caller after prefix length changes.
    return (*prefix, *WORDS[1:], 0xd65f03c0)


class CmpMovkFirstTests(unittest.TestCase):
    def test_seeded_movk_forms_exact_success_literal_choice(self):
        call = report(words((0xd2800540, movk(0x1234, 16))))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000001234002a')
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x000000001234002a')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertFalse(call['return_choice']['runtime_value_proven'])

class CmpMovkBoundaryTests(unittest.TestCase):
    def test_all_four_halfword_positions(self):
        for shift, expected in ((0, '0x0000000000001234'), (16, '0x000000001234002a'),
                                (32, '0x000012340000002a'), (48, '0x123400000000002a')):
            with self.subTest(shift=shift):
                call = report(words((0xd2800540, movk(0x1234, shift))))['calls'][0]
                self.assertEqual(call['success_constant']['constant_bits'], expected)

    def test_multiple_updates_and_movn_seed(self):
        call = report(words((0xd2800000, movk(0x1111), movk(0x2222,16),
                             movk(0x3333,32), movk(0x4444,48))))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x4444333322221111')
        call = report(words((0x92800000, movk(0x1234,48))))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x1234ffffffffffff')

    def test_unseeded_movk_does_not_create_known_bits(self):
        call = report(words((movk(0x1234,16),)))['calls'][0]
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual(call['success_constant']['reason'], 'success_x0_constant_not_known')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_unknown_source_copy_invalidates_seed_before_update(self):
        call = report(words((0xd2800540, 0xaa1403e0, movk(0x1234,16))))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_update_then_copy_from_known_temporary(self):
        call = report(words((0xd2800553, movk(0x1234,16,19), 0xaa1303e0)))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000001234002a')

    def test_update_invalidates_error_alias(self):
        call = report(words((movk(0x1234,16,21),)))['calls'][0]
        self.assertEqual(call['status'], 'declined')
        self.assertEqual(call['reason'], 'error_value_clobbered')

    def test_saved_error_alias_survives_partial_update(self):
        call = report((0xaa1503f3, movk(0x1234,16,21), 0xd2800540,
                       0xf100027f, 0x54000080, 0xaa1303e0,
                       0x94000009, 0x92800000, 0xd65f03c0))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_movk_prefix_cannot_enable_cbz_or_cbnz(self):
        for branch in (0xb4000095, 0xb5000095):
            call = report((0xd2800540, movk(0x1234), branch, *WORDS[3:], 0xd65f03c0))['calls'][0]
            self.assertEqual(call['status'], 'declined')
            self.assertEqual(call['reason'], 'literal_prefix_requires_compare_test')

    def test_w_movk_stays_unmodeled(self):
        call = report(words((0xd2800540, 0x72a24680)))['calls'][0]
        self.assertEqual(call['status'], 'declined')

    def test_eight_word_prefix_limit_is_not_extended(self):
        exact = report(words((0xd2800540, *(movk(i) for i in range(5)))))['calls'][0]
        self.assertEqual(exact['return_choice']['status'], 'structural_choice_candidate')
        over = report(words((0xd2800540, *(movk(i) for i in range(6)))))['calls'][0]
        self.assertEqual(over['status'], 'declined')

    def test_tail_side_entry_still_withholds_updated_literal(self):
        call = report((*words((0xd2800540, movk(0x1234,16))), 0x17ffffff))['calls'][0]
        self.assertEqual(call['success_constant']['reason'], 'unexpected_return_tail_entry')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

class CmpMovkDeliveryTests(unittest.TestCase):
    def test_zr_destination_does_not_change_known_success_bits(self):
        call = report(words((0xd2800540, movk(0x1234,48,31))))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')
        self.assertFalse(call['return_choice']['caller_return_type_proven'])

    def test_text_preserves_update_word_and_exact_bits(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report(words((0xd2800540, movk(0x1234,16)))))
        for expected in ('0xf2a24680', '0x000000001234002a', 'post_call',
                         'structural_choice_candidate', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_json_retains_updated_literal_choice(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        from test_swift_error_flow import image
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-movk-literals'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'
            source.write_bytes(image(words((0xd2800540, movk(0x1234,16)))).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['return_choice']['success']['constant_bits'], '0x000000001234002a')
            self.assertFalse(call['return_choice']['runtime_value_proven'])
