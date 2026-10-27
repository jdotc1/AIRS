"""Error-arm literals after opaque calls; no catch/source/runtime claims."""
import unittest
from test_swift_success_result import report
from test_swift_shared_epilogue import WORDS

class ErrorConstantFirstTests(unittest.TestCase):
    def test_literal_after_opaque_error_call_is_retained(self):
        value = report(WORDS)
        result = value['calls'][0]['error_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        self.assertEqual(result['constant_bits'], '0xffffffffffffffff')
        self.assertEqual(result['opaque_call_count'], 1)
        self.assertFalse(result['call_return_proven'])
        self.assertFalse(result['handler_semantics_proven'])
        self.assertEqual(value['error_constant_model_version'], 'swift-error-constant-v18')

def error_arm(body, tail=(0xd65f03c0,)):
    test = 0xb4000015 | ((len(body) + 2) << 5)
    return report((test,) + tuple(body) + (0x14000002, 0xd2800000) + tuple(tail))

class ErrorConstantBoundaryTests(unittest.TestCase):
    def test_constant_before_opaque_call_is_invalidated(self):
        value = error_arm((0x92800000, 0x94000100))
        result = value['calls'][0]['error_constant']
        self.assertEqual(result['reason'], 'error_x0_constant_not_known')
        self.assertTrue(any(row.get('constant_state') == 'cleared_after_opaque_call' for row in result['instructions']))

    def test_opaque_call_clears_even_saved_register_constants(self):
        result = error_arm((0xd2800553, 0x94000100, 0xaa1303e0))['calls'][0]['error_constant']
        self.assertEqual(result['reason'], 'error_x0_constant_not_known')

    def test_full_assignment_after_last_opaque_call_can_recover(self):
        result = error_arm((0xd2800000, 0x94000100, 0x94000100, 0x92800000))['calls'][0]['error_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        self.assertEqual(result['opaque_call_count'], 2)
        self.assertEqual(result['constant_bits'], '0xffffffffffffffff')

    def test_error_and_success_patterns_are_kept_distinct(self):
        call = report(WORDS)['calls'][0]
        self.assertEqual(call['error_constant']['constant_bits'], '0xffffffffffffffff')
        self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')
        self.assertFalse(call['error_constant']['depends_on_call_result'])

    def test_unknown_incoming_value_does_not_seed_literal(self):
        result = error_arm((0xaa1303e0,))['calls'][0]['error_constant']
        self.assertEqual(result['reason'], 'error_x0_constant_not_known')

    def test_copies_xzr_and_shifted_patterns(self):
        for body, bits in (((0xd2e24693, 0xaa1303e0), '0x1234000000000000'),
                           ((0xaa1f03e0,), '0x0000000000000000')):
            self.assertEqual(error_arm(body)['calls'][0]['error_constant']['constant_bits'], bits)

    def test_forward_error_arm_has_no_source_or_call_return_proof(self):
        from test_swift_forward_error_arm import WORDS as forward
        result = report(forward)['calls'][0]['error_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        for key in ('runtime_value_proven', 'call_return_proven', 'handler_semantics_proven',
                    'exclusive_path_proven', 'caller_return_type_proven', 'source_reconstruction_allowed'):
            self.assertFalse(result[key])

    def test_exact_twentyfour_word_bound_and_each_overflow(self):
        from test_swift_success_result import NOP
        result = error_arm((0x92800000,) + (NOP,) * 14, (NOP,) * 7 + (0xd65f03c0,))['calls'][0]['error_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        self.assertEqual(len(result['instructions']), 24)
        for body, tail in (((0x92800000,) + (NOP,) * 15, (0xd65f03c0,)),
                           ((0x92800000,), (NOP,) * 8 + (0xd65f03c0,))):
            self.assertEqual(error_arm(body, tail)['calls'][0]['error_constant']['status'], 'declined')

    def test_conflicts_incomplete_scan_and_unsupported_declaration_withhold(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for value in (report(WORDS + (0x17fffffb,)),
                      report(WORDS, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=10)),
                      report(WORDS, symbol='_$s4Demo4readyyF')):
            self.assertEqual(value['calls'][0]['error_constant']['status'], 'declined')

    def test_pipeline_refuses_reserved_w_update_and_unknown_instructions(self):
        for word in (0x52c00020, 0xf2800020, 0xffffffff):
            self.assertEqual(error_arm((word,))['calls'][0]['error_constant']['status'], 'declined')

class ErrorConstantEvidenceTests(unittest.TestCase):
    def test_default_absence_and_renderer_model_binding(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        from airs.swift_error_text import render_swift_error_text
        from airs.types import InputError
        value = recover_swift_error_flow(image())
        self.assertNotIn('error_constant_model_version', value)
        self.assertNotIn('error_constant', value['calls'][0])
        for mode in ('foreign', None):
            value = report(WORDS)
            if mode is None:
                del value['error_constant_model_version']
            else:
                value['error_constant_model_version'] = mode
            with self.assertRaises(InputError):
                render_swift_error_text(value)

    def test_cli_separates_error_constant_and_exposes_call_invalidation(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'error-constant.macho'
            source.write_bytes(image(WORDS, symbol='_$s4Demo4readSiyKF').data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(options + ['--format', format]), 0)
                if format == 'json':
                    value = json.loads(output.getvalue()); call = value['calls'][0]
                    self.assertEqual(call['error_constant']['constant_bits'], '0xffffffffffffffff')
                    self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')
                else:
                    self.assertIn('Error-constant model: "swift-error-constant-v18"', output.getvalue())
                    self.assertIn('cleared_after_opaque_call', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())
