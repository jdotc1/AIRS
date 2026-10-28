"""Bounded success arithmetic with a forward CBNZ error handler."""
import unittest
from test_swift_forward_error_arm import WORDS, report


def with_cbnz_arm(arm):
    return (0xb5000015 | ((len(arm) + 2) << 5), *arm, 0x14000004, *WORDS[3:])


class CbnzArithmeticFirstTests(unittest.TestCase):
    def test_success_adjustment_before_handler_skip_is_recovered(self):
        call = report(with_cbnz_arm((0x91001400,)))['calls'][0]
        choice = call['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(choice['success']['immediate'], 5)
        self.assertEqual(choice['condition']['register'], 'x21')
        self.assertEqual(choice['error']['constant_bits'], '0xffffffffffffffff')
        self.assertFalse(choice['runtime_value_proven'])


class CbnzCallBindingTests(unittest.TestCase):
    def test_stale_call_or_changed_callee_cannot_supply_arithmetic_result(self):
        import struct
        from copy import deepcopy
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        words = with_cbnz_arm((0x91001400,)); value = image(words)
        function = value.functions[0]; data = value.bytes_at(function.start, function.size)
        original = report(words)['calls'][0]
        for word in (0xd503201f, 0x94000040):
            raw = bytearray(data); struct.pack_into('<I', raw, 0, word); changed = bytes(raw)
            self.assertEqual(_success_result(changed, function, original,
                _caller_direct_edges(changed, function))['status'], 'declined')
        call = deepcopy(original); call['callee_pc'] = call['success_pc']
        self.assertEqual(_success_result(data, function, call,
            _caller_direct_edges(data, function))['status'], 'declined')


class CbnzArithmeticBoundaryTests(unittest.TestCase):
    def test_shifted_subtract_uses_saved_result_and_error_register_alias(self):
        words = with_cbnz_arm((0xd1400674, 0xaa1403e0))
        words = (0xaa0003f3, 0xaa1503f4, 0xaa1f03f5, (words[0] & ~31) | 20, *words[1:])
        call = report(words)['calls'][0]
        self.assertEqual(call['tested_register'], 'x20')
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_sub_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 4096)
        self.assertEqual((call['success_result']['adjustment_source_register'],
                          call['success_result']['adjustment_register']), (19, 20))

    def test_positive_extreme_shifted_amount_and_eight_word_success_budget(self):
        for count, expected in ((7, 'structural_choice_candidate'), (8, 'unresolved')):
            words = with_cbnz_arm((0x917ffc00, *((0xd503201f,)*(count-1))))
            choice = report(words)['calls'][0]['return_choice']
            self.assertEqual(choice['status'], expected)
            if count == 7:
                self.assertEqual(choice['success']['immediate'], 16773120)
                self.assertEqual(choice['success']['immediate_shift'], 12)

    def test_entry_into_each_arm_skip_or_tail_withholds_arithmetic(self):
        words = with_cbnz_arm((0x91001400,)); source = 4 + len(words)*4
        for target in (4, 8, 12, 16, 20, 24, 28, 32, 40):
            with self.subTest(target=target):
                branch = 0x14000000 | (((target-source)//4) & 0x3ffffff)
                self.assertEqual(report((*words, branch))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_entry_into_saved_result_or_error_alias_window_refuses(self):
        words = (0xaa0003f3, 0xaa1503f4, *with_cbnz_arm((0x91001660,)))
        source = 4 + len(words)*4
        for target in (4, 8, 12):
            branch = 0x14000000 | (((target-source)//4) & 0x3ffffff)
            call = report((*words, branch))['calls'][0]
            self.assertEqual(call['success_result']['reason'], 'success_arithmetic_postcall_evidence_inconsistent')
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_unknown_partial_and_missing_scan_refuse(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS, _success_result
        from test_swift_error_flow import image
        words = with_cbnz_arm((0x91001400,))
        self.assertEqual(report((*words, 0xffffffff))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report(words, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=9))['calls'][0]['return_choice']['status'], 'unresolved')
        value = image(words); function = value.functions[0]
        self.assertEqual(_success_result(value.bytes_at(function.start, function.size), function,
            report(words)['calls'][0], None)['status'], 'declined')

    def test_stale_test_arm_skip_error_and_return_words_refuse(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        words = with_cbnz_arm((0x91001400,)); value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); call = report(words)['calls'][0]
        for offset, word in ((4, 0xb4000075), (8, 0x91001800), (12, 0x14000005),
                             (16, 0xaa1403e0), (20, 0x94000011), (24, 0xd2800540),
                             (28, 0xd503201f), (40, 0xd65f0000)):
            raw = bytearray(data); struct.pack_into('<I', raw, offset, word); changed = bytes(raw)
            self.assertEqual(_success_result(changed, function, call,
                _caller_direct_edges(changed, function))['status'], 'declined')

    def test_forged_region_plan_window_and_scan_cannot_supply_result(self):
        from copy import deepcopy
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        words = with_cbnz_arm((0x91001400,)); value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); scan = _caller_direct_edges(data, function)
        original = report(words)['calls'][0]
        for group, key, changed in (('error_region', 'opaque_call_count', 0),
            ('presentation', 'source_reconstruction_allowed', True)):
            call = deepcopy(original); call[group][key] = changed
            self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
        call = deepcopy(original); call['window'][0]['word'] = '0xb5000074'
        self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
        changed_scan = deepcopy(scan); changed_scan['caller_scan_complete'] = False
        self.assertEqual(_success_result(data, function, original, changed_scan)['status'], 'declined')

    def test_original_untracked_killed_and_narrow_result_aliases_refuse(self):
        for arm in ((0x91001660,), (0xaa0003f3, 0x91001674, 0xaa1303e0),
                    (0x2a0003f3, 0x91001660), (0xaa0003f3, 0xaa1f03f3, 0x91001660),
                    (0x91001413,)):
            self.assertEqual(report(with_cbnz_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_invalid_width_flags_zero_sp_multiple_and_mixed_operations_refuse(self):
        for arm in ((0x91000000,), (0x910017e0,), (0x9100141f,), (0xb1001400,),
                    (0x11001400,), (0x91c00400,), (0x91001400, 0xd1000400),
                    (0x91001400, 0xd2800000), (0x91001400, 0x2a0003e0),
                    (0x91001400, 0x94000010), (0x91001400, 0x14000001)):
            self.assertEqual(report(with_cbnz_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_invalid_skip_target_or_missing_terminal_branch_refuse(self):
        words = with_cbnz_arm((0x91001400,))
        for skip in (0xd503201f, 0x14000001, 0x14000003, 0x14000005, 0x17ffffff):
            self.assertEqual(report((*words[:2], skip, *words[3:]))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_narrow_unrelated_or_clobbered_error_register_cannot_qualify(self):
        words = with_cbnz_arm((0x91001400,))
        for branch in (0x35000075, 0xb5000074, 0xb500007f):
            self.assertEqual(report((branch, *words[1:]))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report((0xaa0003f5, *words))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report((0xaa1503e0, (words[0] & ~31), *words[1:]))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_void_call_does_not_supply_int_arithmetic(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        value = recover_swift_error_flow(image(with_cbnz_arm((0x91001400,)), symbol='_$s4Demo4readyyKF'),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_cli_and_text_retain_scaled_value_condition_and_proof_limits(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_error_flow import image
        words = with_cbnz_arm((0xd1400400,))
        text = render_swift_error_text(report(words))
        self.assertIn('call result - 4096 modulo 2^64', text)
        self.assertIn('Source reconstruction: disabled', text)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder)/'nonzero-arithmetic.macho'; source.write_bytes(image(words).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['success']['immediate'], 4096)
            self.assertEqual(choice['condition']['error_when'], 'nonzero')
            self.assertNotIn('test_condition', choice['condition'])
            for key in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                        'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
                self.assertFalse(choice[key])
