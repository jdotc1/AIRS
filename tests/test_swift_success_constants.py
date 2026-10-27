"""Bounded constants assigned on the selected success arm."""
import unittest
from test_swift_success_result import report
from test_swift_shared_epilogue import WORDS

class SuccessConstantFirstTests(unittest.TestCase):
    def test_zero_success_result_is_distinct_from_call_result(self):
        value = report(WORDS)
        call = value['calls'][0]
        constant = call['success_constant']
        self.assertEqual(constant['status'], 'constant_register_candidate')
        self.assertEqual(constant['constant_bits'], '0x0000000000000000')
        self.assertFalse(constant['depends_on_call_result'])
        self.assertFalse(constant['runtime_value_proven'])
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(value['success_constant_model_version'], 'swift-success-constant-v12')

def success(body, tail=None, error_call=0x94000010):
    if tail is None:
        tail = WORDS[6:]
    return report(WORDS[:2] + (error_call,) + WORDS[3:4] + (0x14000000 | (len(body) + 1),) + tuple(body) + tuple(tail))

class SuccessConstantBoundaryTests(unittest.TestCase):
    def test_movz_movn_shifted_bit_patterns(self):
        for word, bits in ((0x92800000, '0xffffffffffffffff'),
                           (0xd2e24680, '0x1234000000000000'),
                           (0x92a00020, '0xfffffffffffeffff')):
            self.assertEqual(success((word,))['calls'][0]['success_constant']['constant_bits'], bits)

    def test_constant_copies_are_tracked_transitively(self):
        result = success((0xd2800553, 0xaa1303f4, 0xaa1403e0))['calls'][0]['success_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        self.assertEqual(result['constant_bits'], '0x000000000000002a')

    def test_unknown_overwrite_kills_a_known_constant(self):
        result = success((0xd2800020, 0xaa1303e0))['calls'][0]['success_constant']
        self.assertEqual(result['reason'], 'success_x0_constant_not_known')

    def test_error_arm_and_incoming_registers_do_not_seed_constants(self):
        from test_swift_success_result import NOP
        for body in ((NOP,), (0xaa1303e0,)):
            result = success(body)['calls'][0]['success_constant']
            self.assertEqual(result['reason'], 'success_x0_constant_not_known')

    def test_xzr_is_zero_and_discarded_writes_do_not_create_storage(self):
        result = success((0xd280003f, 0xaa1f03e0))['calls'][0]['success_constant']
        self.assertEqual(result['constant_bits'], '0x0000000000000000')

    def test_unknown_update_reserved_w_constant_call_and_unknown_stay_outside_subset(self):
        for word in (0xf2800020, 0x52c00020, 0x94000010, 0xffffffff):
            self.assertEqual(success((word,))['calls'][0]['success_constant']['status'], 'declined')

    def test_forward_layout_constant_has_same_scope(self):
        from test_swift_forward_error_arm import WORDS as forward
        result = report(forward)['calls'][0]['success_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        self.assertEqual(result['constant_bits'], '0x0000000000000000')
        for key in ('runtime_value_proven', 'exclusive_path_proven', 'caller_return_type_proven', 'source_reconstruction_allowed'):
            self.assertFalse(result[key])

    def test_conflicting_entries_partial_scan_and_unsupported_declaration_withhold(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for value in (report(WORDS + (0x17fffffb,)),
                      report(WORDS, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=10)),
                      report(WORDS, symbol='_$s4Demo4readyyF')):
            self.assertEqual(value['calls'][0]['success_constant']['status'], 'declined')

    def test_exact_sixteen_word_evidence_and_each_overflow(self):
        from test_swift_success_result import NOP
        value = success((0xd2800000,) + (NOP,) * 7, (NOP,) * 7 + (0xd65f03c0,), error_call=0x94000100)
        result = value['calls'][0]['success_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        self.assertEqual(len(result['instructions']), 16)
        for body, tail in (((0xd2800000,) + (NOP,) * 8, (0xd65f03c0,)),
                           ((0xd2800000,), (NOP,) * 8 + (0xd65f03c0,))):
            self.assertEqual(success(body, tail, error_call=0x94000100)['calls'][0]['success_constant']['status'], 'declined')

    def test_default_absence_and_text_model_binding(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        from airs.swift_error_text import render_swift_error_text
        from airs.types import InputError
        value = recover_swift_error_flow(image())
        self.assertNotIn('success_constant_model_version', value)
        value = report(WORDS)
        text = render_swift_error_text(value)
        self.assertIn('Success-constant model: "swift-success-constant-v12"', text)
        self.assertIn('0x0000000000000000', text)
        self.assertIn('Constant-path instruction', text)
        value['success_constant_model_version'] = 'foreign'
        with self.assertRaises(InputError):
            render_swift_error_text(value)

class SuccessConstantCLIControls(unittest.TestCase):
    def test_json_and_text_distinguish_constant_from_preserved_call_result(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'success-constant.macho'
            source.write_bytes(image(WORDS, symbol='_$s4Demo4readSiyKF').data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(options + ['--format', format]), 0)
                if format == 'json':
                    value = json.loads(output.getvalue()); call = value['calls'][0]
                    self.assertEqual(call['success_constant']['constant_bits'], '0x0000000000000000')
                    self.assertEqual(call['success_result']['status'], 'declined')
                else:
                    self.assertIn('constant_register_candidate', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())
