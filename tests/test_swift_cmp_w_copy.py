"""Bounded CMP W-register constant copies without full-width alias promotion."""
import unittest
from test_swift_cmp_success_literals import report, WORDS
from test_swift_cmp_movk_literals import words


def wcopy(destination, source):
    return 0x2a0003e0 | (source<<16) | destination


class CmpWCopyFirstTests(unittest.TestCase):
    def test_w_copy_zero_extends_known_x_temporary_literal(self):
        call = report(words((0x92800013, wcopy(0,19))))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['success_constant']['constant_bits'], '0x00000000ffffffff')
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x00000000ffffffff')
        self.assertFalse(call['return_choice']['runtime_value_proven'])

class CmpWCopyBoundaryTests(unittest.TestCase):
    def test_known_self_copy_clears_high_bits(self):
        call = report(words((0x92800000, wcopy(0,0))))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x00000000ffffffff')

    def test_unknown_source_invalidates_known_destination(self):
        call = report(words((0x52800540, wcopy(0,20))))['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_unknown_self_copy_does_not_preserve_call_result(self):
        call = report(words((wcopy(0,0),)))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_zero_source_creates_zero_but_zero_destination_discards(self):
        call = report(words((wcopy(0,31),)))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')
        call = report(words((0x52800540, wcopy(31,20))))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')

    def test_narrow_error_copy_is_never_promoted_to_full_alias(self):
        call = report((wcopy(19,21), 0xf100027f, 0x54000080,
                       0xaa1303e0, 0x9400000b, 0x92800000, 0xd65f03c0))['calls'][0]
        self.assertEqual(call['reason'], 'not_error_result_comparison')
        call = report(words((wcopy(21,21),)))['calls'][0]
        self.assertEqual(call['reason'], 'error_value_clobbered')

    def test_saved_full_width_error_alias_survives_narrow_overwrite(self):
        call = report((0xaa1503f3, 0x52800540, wcopy(21,0),
            0xf100027f, 0x54000080, 0xaa1303e0,
            0x94000009, 0x92800000, 0xd65f03c0))['calls'][0]
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertEqual(call['success_constant']['constant_bits'], '0x000000000000002a')

    def test_repeated_copies_and_updates_retain_low_word(self):
        call = report(words((0x92800000, wcopy(19,0), 0xf2f579b3, wcopy(0,19))))['calls'][0]
        self.assertEqual(call['success_constant']['constant_bits'], '0x00000000ffffffff')

    def test_noncanonical_register_copy_encodings_stay_refused(self):
        for word in (wcopy(0,19) | 0x400, wcopy(0,19) & ~0x20, wcopy(0,19) ^ 0x20000000):
            with self.subTest(word=hex(word)):
                self.assertEqual(report(words((word,)))['calls'][0]['status'], 'declined')

    def test_copy_prefix_does_not_enable_cbz_or_narrow_error_tests(self):
        for branch in (0xb4000095, 0xb5000095, 0x34000095):
            call = report((wcopy(0,31), branch, *WORDS[3:], 0xd65f03c0))['calls'][0]
            self.assertEqual(call['status'], 'declined')

    def test_eight_word_prefix_limit_remains(self):
        exact = report(words((0x52800553, *(wcopy(0,19) for _ in range(5)))))['calls'][0]
        self.assertEqual(exact['success_constant']['constant_bits'], '0x000000000000002a')
        over = report(words((0x52800553, *(wcopy(0,19) for _ in range(6)))))['calls'][0]
        self.assertEqual(over['status'], 'declined')

    def test_tail_entry_still_withholds_copy_outcome(self):
        call = report((*words((0x12800013, wcopy(0,19))), 0x17ffffff))['calls'][0]
        self.assertEqual(call['success_constant']['reason'], 'unexpected_return_tail_entry')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

class CmpWCopyDeliveryTests(unittest.TestCase):
    def test_literal_copy_choice_keeps_all_proof_flags_false(self):
        call = report(words((0x92800013, wcopy(0,19))))['calls'][0]
        for key in ('source_reconstruction_allowed', 'runtime_value_proven',
                    'caller_return_type_proven', 'exclusive_path_proven'):
            self.assertFalse(call['return_choice'][key])

    def test_text_retains_copy_word_and_zero_extended_bits(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report(words((0x92800013, wcopy(0,19)))))
        for expected in ('0x2a1303e0', '0x00000000ffffffff',
                         'structural_choice_candidate', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_json_retains_literal_copy_choice(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        from test_swift_error_flow import image
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-w-copy'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(words((0x92800013, wcopy(0,19)))).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['success']['constant_bits'], '0x00000000ffffffff')
            self.assertFalse(choice['same_constant_bits'])
