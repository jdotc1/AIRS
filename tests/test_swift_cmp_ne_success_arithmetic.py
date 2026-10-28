"""Arithmetic before a CMP/B.NE success arm branches over its error handler."""
import unittest
from test_swift_cmp_ne_handler import WORDS, report


def with_ne_arm(arm):
    return (WORDS[0], 0x54000001 | ((len(arm) + 2) << 5),
            *arm, 0x14000003, *WORDS[4:])


class NeArithmeticFirstTests(unittest.TestCase):
    def test_add_before_forward_error_skip_yields_structural_choice(self):
        call = report(with_ne_arm((0x91001400,)))['calls'][0]
        choice = call['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(choice['success']['immediate'], 5)
        self.assertEqual(choice['condition']['test_condition'], 'ne')
        self.assertEqual(choice['error']['constant_bits'], '0xffffffffffffffff')
        self.assertFalse(choice['runtime_value_proven'])


class NeArithmeticBoundaryTests(unittest.TestCase):
    def test_shifted_subtraction_on_alias_restored_from_another_register(self):
        call = report(with_ne_arm((0xaa0003f3, 0xd1400674, 0xaa1403e0)))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_sub_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 4096)
        self.assertEqual(call['return_choice']['success']['immediate_shift'], 12)
        self.assertEqual((call['success_result']['adjustment_source_register'],
                          call['success_result']['adjustment_register']), (19, 20))

    def test_eight_word_budget_includes_terminal_branch(self):
        for count, expected in ((7, 'structural_choice_candidate'), (8, 'unresolved')):
            arm = (0x91001400, *((0xd503201f,)*(count-1)))
            self.assertEqual(report(with_ne_arm(arm))['calls'][0]['return_choice']['status'], expected)

    def test_terminal_branch_must_skip_exact_error_interval(self):
        words = with_ne_arm((0x91001400,))
        for skip in (0xd503201f, 0x14000001, 0x14000002, 0x14000004, 0x17ffffff):
            with self.subTest(skip=hex(skip)):
                self.assertEqual(report((*words[:3], skip, *words[4:]))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_side_entries_to_flag_window_arms_skip_and_return_withhold_recovery(self):
        words = with_ne_arm((0x91001400,)); source = 4 + len(words)*4
        for target in (4, 8, 12, 16, 20, 24, 28):
            branch = 0x14000000 | (((target-source)//4) & 0x3ffffff)
            self.assertEqual(report((*words, branch))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_unknown_partial_and_missing_screen_refuse(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS, recover_swift_error_flow
        from airs.types import InputError
        from test_swift_error_flow import image
        words = with_ne_arm((0x91001400,))
        self.assertEqual(report((*words, 0xffffffff))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report(words, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=7))['calls'][0]['return_choice']['status'], 'unresolved')
        with self.assertRaises(InputError):
            recover_swift_error_flow(image(words), include_error_regions=True, include_structured_presentation=True)

    def test_stale_comparison_branch_arithmetic_skip_error_or_return_refuse(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        words = (*with_ne_arm((0x91001400,)), 0xd503201f)
        value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); call = report(words)['calls'][0]
        for offset, word in ((4, 0xf100029f), (8, 0x54000060), (12, 0x91001800),
                             (16, 0x14000002), (20, 0xaa1403e0), (24, 0xd2800540),
                             (28, 0xd65f0000), (32, 0x17fffffb)):
            raw = bytearray(data); struct.pack_into('<I', raw, offset, word); changed = bytes(raw)
            self.assertEqual(_success_result(changed, function, call,
                _caller_direct_edges(changed, function))['status'], 'declined')

    def test_forged_window_scan_flags_region_and_plan_refuse(self):
        from copy import deepcopy
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        words = with_ne_arm((0x91001400,)); value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); scan = _caller_direct_edges(data, function)
        original = report(words)['calls'][0]
        for group, key, changed in (('flag_entry_validation', 'flag_state_proven', True),
            ('error_region', 'opaque_call_count', 1), ('presentation', 'source_reconstruction_allowed', True)):
            call = deepcopy(original); call[group][key] = changed
            self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
        call = deepcopy(original); call['window'][0]['word'] = '0xf100029f'
        self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
        call = deepcopy(original); call['error_region']['incoming_validation']['unexpected_entry_count'] = 1
        self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
        self.assertEqual(_success_result(data, function, original, None)['status'], 'declined')
        changed_scan = deepcopy(scan); changed_scan['caller_scan_complete'] = False
        self.assertEqual(_success_result(data, function, original, changed_scan)['status'], 'declined')

    def test_original_untracked_killed_or_narrow_alias_cannot_reach_return(self):
        for arm in ((0x91001660,), (0xaa0003f3, 0x91001674, 0xaa1303e0),
                    (0x2a0003f3, 0x91001660), (0x91001413,),
                    (0xaa0003f3, 0xaa1f03f3, 0x91001660)):
            self.assertEqual(report(with_ne_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_zero_sp_flags_narrow_reserved_and_multiple_operations_refuse(self):
        for arm in ((0x91000000,), (0x910017e0,), (0x9100141f,), (0xb1001400,),
                    (0xf1001400,), (0x11001400,), (0x51400400,), (0x91c00400,),
                    (0x91001400, 0xd1000400), (0x91001400, 0x91400400)):
            self.assertEqual(report(with_ne_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_literal_narrow_copy_call_and_early_branch_are_not_arithmetic_arm(self):
        for word in (0xd2800000, 0x2a0003e0, 0x94000010, 0x14000001):
            self.assertEqual(report(with_ne_arm((0x91001400, word)))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_cbnz_forward_arithmetic_remains_outside_scope(self):
        words = with_ne_arm((0x91001400,))
        self.assertEqual(report((0xb5000095, *words[2:]))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_void_and_x0_error_alias_cannot_supply_int_result(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        words = with_ne_arm((0x91001400,))
        void = recover_swift_error_flow(image(words, symbol='_$s4Demo4readyyKF'),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(void['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report((0xaa1503e0, 0xf100001f, *words[1:]))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_cli_and_text_bind_ne_condition_and_adjusted_amount(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_error_flow import image
        words = with_ne_arm((0xd1400400,))
        text = render_swift_error_text(report(words))
        self.assertIn('call result - 4096 modulo 2^64', text)
        self.assertIn('Source reconstruction: disabled', text)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder)/'forward-arithmetic.macho'; source.write_bytes(image(words).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['condition']['test_condition'], 'ne')
            self.assertEqual(choice['success']['immediate'], 4096)
            for key in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                        'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
                self.assertFalse(choice[key])

    def test_choice_and_text_refuse_unbound_adjustment_or_condition(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        from airs.swift_error_text import render_swift_error_text
        original = report(with_ne_arm((0x91400400,)))
        changed = deepcopy(original); call = changed['calls'][0]
        for outcome in (call['success_result'], call['return_choice']['success']):
            outcome.update(immediate_shift=0, immediate=1)
        self.assertEqual(_return_choice(call)['status'], 'unresolved')
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(changed))
        changed = deepcopy(original); call = changed['calls'][0]
        call['presentation']['display_plan']['condition']['test_condition'] = 'eq'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(changed))

    def test_choice_binds_both_returns_and_success_text_binds_success_return(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        from airs.swift_error_text import render_swift_error_text
        original = report(with_ne_arm((0x91001400,)))
        for section in ('success_result', 'error_constant'):
            changed = deepcopy(original); call = changed['calls'][0]
            call[section]['return_pc'] = call['success_pc']
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
            if section == 'success_result':
                self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(changed))
