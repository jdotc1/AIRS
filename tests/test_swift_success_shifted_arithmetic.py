"""Selected-path arithmetic with an encoded 12-bit immediate shift."""
import unittest

from test_swift_owned_postcall_arithmetic import report
from test_swift_success_arithmetic_copies import with_arm


class ShiftedArithmeticFirstTests(unittest.TestCase):
    def test_shifted_add_reports_effective_4096_not_encoded_one(self):
        call = report(with_arm((0x91400400,)))['calls'][0]
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertEqual(call['success_result']['immediate'], 4096)
        self.assertEqual(call['success_result']['immediate_shift'], 12)
        self.assertEqual(call['return_choice']['success']['immediate'], 4096)
        self.assertEqual(call['return_choice']['success']['immediate_shift'], 12)
        self.assertFalse(call['return_choice']['runtime_value_proven'])


class ShiftedArithmeticBoundaryTests(unittest.TestCase):
    def test_subtract_from_alias_into_another_register_and_restore(self):
        call = report(with_arm((0xaa0003f3, 0xd1400674, 0xaa1403e0)))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_sub_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 4096)
        self.assertEqual((call['success_result']['adjustment_source_register'],
                          call['success_result']['adjustment_register']), (19, 20))

    def test_largest_and_interior_shifted_immediates(self):
        for word, amount, operation in ((0x91400800, 8192, 'add_immediate_modulo'),
                                        (0x917ffc00, 16773120, 'add_immediate_modulo'),
                                        (0xd17ffc00, 16773120, 'sub_immediate_modulo')):
            with self.subTest(word=hex(word)):
                choice = report(with_arm((word,)))['calls'][0]['return_choice']
                self.assertEqual(choice['success']['immediate'], amount)
                self.assertEqual(choice['success']['operation'], operation)
                self.assertEqual(choice['success']['bit_width'], 64)

    def test_x30_source_and_destination_are_distinct_from_sp(self):
        for arm in ((0xaa0003fe, 0x914007c0), (0x9140041e, 0xaa1e03e0)):
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['success']['immediate'], 4096)

    def test_zero_narrow_flags_reserved_bit_and_sp_operands_refuse(self):
        for word in (0x91400000, 0xd1400000, 0x11400400, 0x51400400,
                     0xb1400400, 0xf1400400, 0x91c00400, 0x914007e0, 0x9140041f):
            with self.subTest(word=hex(word)):
                self.assertEqual(report(with_arm((word,)))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_untracked_killed_or_original_alias_cannot_be_adjusted_return(self):
        for arm in ((0x91400660,),
                    (0xaa0003f3, 0xaa1f03f3, 0x91400660),
                    (0x2a0003f3, 0x91400660),
                    (0xaa0003f3, 0x91400674, 0xaa1303e0),
                    (0x91400413, 0xaa1f03f3, 0xaa1303e0)):
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_second_adjustment_narrow_copy_and_literal_stay_outside_scope(self):
        for extra in (0x91000400, 0xd1400400, 0x2a0003e0, 0xd2800000):
            self.assertEqual(report(with_arm((0x91400400, extra)))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_success_arm_remains_limited_to_eight_words(self):
        for count, expected in ((8, 'structural_choice_candidate'), (9, 'unresolved')):
            arm = (0x91400400, *((0xd503201f,)*(count-1)))
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], expected)

    def test_malformed_or_unbound_immediate_metadata_cannot_produce_choice_or_text(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        from airs.swift_error_text import render_swift_error_text
        original = report(with_arm((0x91400400,)))
        changes = [('immediate_shift', value) for value in (0, 1, True, '12', None, -12, 4096)]
        changes += [('immediate', value) for value in (0, True, 1, 4095, 4097, 8192, 16773121, 16777216)]
        changes += [('adjustment_source_register', value) for value in (31, -1, True)]
        changes += [('adjustment_register', 31), ('bit_width', True), ('operation', 'multiply')]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                changed = deepcopy(original)
                call = changed['calls'][0]; call['success_result'][key] = value
                self.assertEqual(_return_choice(call)['status'], 'unresolved')
                self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(changed))

    def test_consistently_relabeling_shift_and_value_cannot_override_word(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        from airs.swift_error_text import render_swift_error_text
        changed = deepcopy(report(with_arm((0x91400400,))))
        call = changed['calls'][0]
        for outcome in (call['success_result'], call['return_choice']['success']):
            outcome.update(immediate_shift=0, immediate=1)
        self.assertEqual(_return_choice(call)['status'], 'unresolved')
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(changed))

    def test_choice_shift_must_match_result_in_text(self):
        from copy import deepcopy
        from airs.swift_error_text import render_swift_error_text
        original = report(with_arm((0x91400400,)))
        for value in (0, True, None, '12'):
            changed = deepcopy(original)
            changed['calls'][0]['return_choice']['success']['immediate_shift'] = value
            self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(changed))

    def test_stale_shift_bit_and_unexpected_entries_withhold_recovery(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        from test_swift_owned_postcall_arithmetic import SYMBOL
        words = (*with_arm((0x91400400,)), 0xd503201f)
        value = image(words, symbol=SYMBOL); function = value.functions[0]
        raw = bytearray(value.bytes_at(function.start, function.size))
        call = report(words)['calls'][0]
        struct.pack_into('<I', raw, 24, 0x91000400)
        self.assertEqual(_success_result(bytes(raw), function, call,
                                        _caller_direct_edges(bytes(raw), function))['status'], 'declined')
        source_pc = 4 + len(words[:-1])*4
        for target in (24, 28):
            branch = 0x14000000 | (((target-source_pc)//4) & 0x3ffffff)
            self.assertEqual(report((*words[:-1], branch))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report((*words[:-1], 0xffffffff))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_cli_and_text_use_scaled_amount_without_source_or_runtime_proof(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_error_flow import image
        from test_swift_owned_postcall_arithmetic import SYMBOL
        words = with_arm((0xd1400400,))
        text = render_swift_error_text(report(words))
        self.assertIn('call result - 4096 modulo 2^64', text)
        self.assertIn('Source reconstruction: disabled', text)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder)/'shifted.macho'; source.write_bytes(image(words, symbol=SYMBOL).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                               '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['success']['immediate'], 4096)
            for key in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                        'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
                self.assertFalse(choice[key])
