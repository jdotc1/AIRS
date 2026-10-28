"""Bounded success-entry return tails, with caller-local entry protection."""
import unittest
from test_swift_success_result import report, NOP
from test_swift_error_flow import BASE

# CBZ x21 to success RET, error sets another result and branches to same RET.
WORDS = (0xb4000075, 0x92800000, 0x14000001, 0xd65f03c0)

class SuccessReturnTailFirstTests(unittest.TestCase):
    def test_direct_success_return_preserves_call_result(self):
        call = report(WORDS)['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertNotIn('shared_epilogue', call['error_region'])
        result = call['success_result']
        self.assertEqual(result['status'], 'preserved_register_candidate')
        self.assertEqual(result['return_tail_layout'], 'success_entry')
        self.assertEqual(result['return_pc'], hex(BASE + 16))
        self.assertFalse(result['exclusive_path_proven'])

class SuccessReturnTailBoundaryTests(unittest.TestCase):
    def test_restore_tail_and_exact_eight_word_bound(self):
        for tail in ((0xa8c17bfd, 0xd65f03c0), (NOP,) * 7 + (0xd65f03c0,)):
            call = report(WORDS[:-1] + tail)['calls'][0]
            self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        call = report(WORDS[:-1] + (NOP,) * 8 + (0xd65f03c0,))['calls'][0]
        self.assertEqual(call['success_result']['reason'], 'bounded_return_tail_missing')

    def test_external_branch_to_tail_entry_withholds(self):
        call = report(WORDS + (0x17ffffff,))['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        result = call['success_result']
        self.assertEqual(result['reason'], 'unexpected_return_tail_entry')
        self.assertEqual(result['unexpected_tail_entry_count'], 1)
        self.assertTrue(result['tail_entry_details_complete'])

    def test_external_branch_to_tail_interior_withholds(self):
        words = WORDS[:-1] + (NOP, 0xa9427bfd, 0xd65f03c0, 0x17fffffe)
        call = report(words)['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['success_result']['reason'], 'unexpected_return_tail_entry')

    def test_opaque_error_call_into_tail_is_not_exempt(self):
        call = report((WORDS[0], 0x94000002) + WORDS[2:])['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['success_result']['reason'], 'unexpected_return_tail_entry')

    def test_x0_write_and_nonstandard_return_do_not_pass_tail_whitelist(self):
        for tail in ((0xd2800000, 0xd65f03c0), (0xaa1303e0, 0xd65f03c0),
                     (0xd65f0000,), (0xffffffff,), (0x94000010, 0xd65f03c0)):
            self.assertEqual(report(WORDS[:-1] + tail)['calls'][0]['success_result']['status'], 'declined')

    def test_partial_scan_withholds_even_when_tail_is_visible(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        value = report(WORDS, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=5))
        self.assertEqual(value['calls'][0]['success_result']['status'], 'declined')

    def test_postcall_copy_restores_x0_before_direct_return(self):
        words = (0xaa0003f3, 0xaa1f03e0, 0xaa1303e0) + WORDS
        result = report(words)['calls'][0]['success_result']
        self.assertEqual(result['status'], 'copied_register_candidate')
        self.assertEqual(result['return_tail_layout'], 'success_entry')

    def test_error_fallthrough_without_terminal_branch_is_structural_only(self):
        call = report((WORDS[0], NOP, NOP, WORDS[-1]))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertFalse(call['success_result']['runtime_value_proven'])
        self.assertFalse(call['success_result']['caller_return_type_proven'])

    def test_renderer_retains_tail_layout_model_and_raw_words(self):
        from airs.swift_error_text import render_swift_error_text
        value = report(WORDS); text = render_swift_error_text(value)
        self.assertIn('success_entry', text)
        self.assertIn('swift-success-result-v19', text)
        self.assertIn('0xd65f03c0', text)
        self.assertFalse(value['calls'][0]['success_result']['source_reconstruction_allowed'])

class SuccessReturnTailEvidenceTests(unittest.TestCase):
    def test_tail_entry_conflict_details_are_bounded_with_full_count(self):
        branches = tuple(0x14000000 | (((16 - (20 + i * 4)) // 4) & 0x3ffffff) for i in range(17))
        result = report(WORDS + branches)['calls'][0]['success_result']
        self.assertEqual(result['reason'], 'unexpected_return_tail_entry')
        self.assertEqual(result['unexpected_tail_entry_count'], 17)
        self.assertEqual(len(result['unexpected_tail_entries']), 16)
        self.assertFalse(result['tail_entry_details_complete'])

    def test_direct_return_cli_json_and_text(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        from test_swift_error_flow import image
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'success-return.macho'
            source.write_bytes(image(WORDS, symbol='_$s4Demo4readSiyKF').data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(options + ['--format', format]), 0)
                if format == 'json':
                    value = json.loads(output.getvalue())
                    self.assertEqual(value['calls'][0]['success_result']['return_tail_layout'], 'success_entry')
                    self.assertEqual(value['success_result_model_version'], 'swift-success-result-v19')
                else:
                    self.assertIn('success_entry', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())

class SuccessReturnTailDiagnosticTests(unittest.TestCase):
    def test_conflict_retains_protected_tail_words_in_text(self):
        from airs.swift_error_text import render_swift_error_text
        words = WORDS[:-1] + (0xa8c17bfd, 0xd65f03c0, 0x17fffffe)
        value = report(words); result = value['calls'][0]['success_result']
        self.assertEqual(result['reason'], 'unexpected_return_tail_entry')
        tail = [row for row in result['instructions'] if row['phase'] == 'return_tail']
        self.assertEqual([row['word'] for row in tail], ['0xa8c17bfd', '0xd65f03c0'])
        self.assertLessEqual(len(result['instructions']), 24)
        text = render_swift_error_text(value)
        self.assertIn('0xa8c17bfd', text)
        self.assertIn('unexpected_return_tail_entry', text)
