"""Bounded x0 preservation evidence, never runtime or source proof."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image, BASE
from test_swift_shared_epilogue import WORDS

NOP = 0xd503201f

def report(words=None, symbol='_$s4Demo4readSiyKF', **kwargs):
    if words is None:
        words = WORDS[:5] + (NOP,) + WORDS[6:]
    return recover_swift_error_flow(image(words, symbol=symbol), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True, **kwargs)

class SuccessResultFirstTests(unittest.TestCase):
    def test_success_x0_survives_shared_return_tail(self):
        value = report(); result = value['calls'][0]['success_result']
        self.assertEqual(result['status'], 'preserved_register_candidate')
        self.assertEqual(result['register'], 'x0')
        self.assertEqual(result['return_pc'], hex(BASE + 40))
        self.assertFalse(result['runtime_value_proven'])
        self.assertFalse(result['source_reconstruction_allowed'])
        self.assertEqual(value['success_result_model_version'], 'swift-success-result-v9')

class SuccessResultBoundaryTests(unittest.TestCase):
    def test_success_x0_writes_are_not_preservation(self):
        for word in (0xd2800000, 0x92800000, 0xaa1303e0):
            value = report(WORDS[:5] + (word,) + WORDS[6:])
            self.assertEqual(value['calls'][0]['success_result']['reason'], 'success_result_not_preserved')

    def test_other_register_write_and_forward_layout(self):
        from test_swift_forward_error_arm import WORDS as forward
        for words in (WORDS[:5] + (0xd2800013,) + WORDS[6:],
                      forward[:1] + (NOP,) + forward[2:]):
            result = report(words)['calls'][0]['success_result']
            self.assertEqual(result['status'], 'preserved_register_candidate')
            self.assertLessEqual(len(result['instructions']), 24)

    def test_post_call_x0_write_refuses(self):
        # Copy error x21 into x0, then test the original x21; valid edge, lost result.
        words = (0xaa1503e0,) + WORDS[:5] + (NOP,) + WORDS[6:]
        call = report(words)['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['success_result']['reason'], 'post_call_result_not_preserved')

    def test_void_and_declined_call_have_no_result_candidate(self):
        for symbol in ('_$s4Demo4readyyKF', '_$s4Demo4readyyF'):
            self.assertEqual(report(symbol=symbol)['calls'][0]['success_result']['status'], 'declined')

    def test_success_call_unknown_and_nonstandard_return_withhold(self):
        for word in (0x94000010, 0xffffffff, 0x34000020):
            call = report(WORDS[:5] + (word,) + WORDS[6:])['calls'][0]
            self.assertEqual(call['success_result']['status'], 'declined')
        call = report(WORDS[:5] + (NOP,) + WORDS[6:-1] + (0xd65f0000,))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')

    def test_conflicting_entry_and_partial_scan_withhold(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        # A direct branch after RET enters the protected success word.
        value = report(WORDS[:5] + (NOP,) + WORDS[6:] + (0x17fffffb,))
        self.assertEqual(value['calls'][0]['success_result']['status'], 'declined')
        value = report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=10))
        self.assertEqual(value['calls'][0]['success_result']['status'], 'declined')

    def test_default_output_unchanged_and_direct_return_accepted(self):
        value = recover_swift_error_flow(image())
        self.assertNotIn('success_result_model_version', value)
        self.assertNotIn('success_result', value['calls'][0])
        value = report((0xb4000075, NOP, 0x14000001, 0xd65f03c0))
        self.assertEqual(value['calls'][0]['success_result']['status'], 'preserved_register_candidate')

    def test_renderer_exposes_bounds_and_proof_limits(self):
        from airs.swift_error_text import render_swift_error_text
        from airs.types import InputError
        value = report(); text = render_swift_error_text(value)
        self.assertIn('preserved_register_candidate', text)
        self.assertIn('runtime_value_proven', text)
        self.assertIn('Result-path instruction', text)
        value['success_result_model_version'] = 'foreign'
        with self.assertRaises(InputError):
            render_swift_error_text(value)

class SuccessResultCLIControls(unittest.TestCase):
    def test_cli_json_and_text_retain_result_evidence(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'result.macho'
            source.write_bytes(image(WORDS[:5] + (NOP,) + WORDS[6:], symbol='_$s4Demo4readSiyKF').data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(options + ['--format', format]), 0)
                if format == 'json':
                    value = json.loads(output.getvalue())
                    self.assertEqual(value['calls'][0]['success_result']['status'], 'preserved_register_candidate')
                else:
                    self.assertIn('preserved_register_candidate', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())

class SuccessResultBoundControls(unittest.TestCase):
    def test_exact_combined_word_bound_and_each_overflow(self):
        def words(post=7, success=7, tail=7):
            test = 0xb5000015 | ((success + 2) << 5)
            return (NOP,) * post + (test,) + (NOP,) * success + (0x14000002, NOP) + (NOP,) * tail + (0xd65f03c0,)
        result = report(words())['calls'][0]['success_result']
        self.assertEqual(result['status'], 'preserved_register_candidate')
        self.assertEqual(len(result['instructions']), 24)
        for arguments in ((8, 7, 7), (7, 8, 7), (7, 7, 8)):
            self.assertEqual(report(words(*arguments))['calls'][0]['success_result']['status'], 'declined')

    def test_text_displays_result_model_identity(self):
        from airs.swift_error_text import render_swift_error_text
        self.assertIn('Success-result model: "swift-success-result-v9"', render_swift_error_text(report()))
