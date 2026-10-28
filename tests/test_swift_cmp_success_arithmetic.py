"""Arithmetic on the bounded success arm of a CMP-zero/B.EQ handler."""
import unittest

from test_swift_cmp_shared_epilogue import WORDS, report


def with_cmp_arm(arm):
    return (*WORDS[:5], 0x14000000 | (len(arm) + 1), *arm, *WORDS[7:])


class CmpArithmeticFirstTests(unittest.TestCase):
    def test_compare_eq_add_yields_bound_structural_choice(self):
        call = report(with_cmp_arm((0x91001400,)))['calls'][0]
        choice = call['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(choice['success']['immediate'], 5)
        self.assertEqual(choice['condition']['test_kind'], 'cmp_zero_bcond')
        self.assertEqual(choice['condition']['test_condition'], 'eq')
        self.assertEqual(choice['error']['constant_bits'], '0xffffffffffffffff')
        self.assertFalse(choice['runtime_value_proven'])


class CmpArithmeticBoundaryTests(unittest.TestCase):
    def test_subtract_shifted_amount_through_distinct_aliases(self):
        call = report(with_cmp_arm((0xaa0003f3, 0xd1400674, 0xaa1403e0)))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_sub_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 4096)
        self.assertEqual(call['return_choice']['success']['immediate_shift'], 12)
        self.assertEqual((call['success_result']['adjustment_source_register'],
                          call['success_result']['adjustment_register']), (19, 20))

    def test_missing_flag_or_entry_screen_withholds_recovery(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from airs.types import InputError
        from test_swift_error_flow import image
        with self.assertRaises(InputError) as caught:
            recover_swift_error_flow(image(with_cmp_arm((0x91001400,))),
                include_error_regions=True, include_structured_presentation=True)
        self.assertEqual(caught.exception.code, 'swift_presentation_option')

    def test_side_entries_into_flags_arms_and_tail_withhold_recovery(self):
        words = with_cmp_arm((0x91001400,))
        source = 4 + len(words)*4
        for target in (4, 8, 12, 20, 24, 28, 32, 40, 44):
            with self.subTest(target=target):
                branch = 0x14000000 | (((target-source)//4) & 0x3ffffff)
                self.assertEqual(report((*words, branch))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_unknown_and_partial_caller_withhold_recovery(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        words = with_cmp_arm((0x91001400,))
        self.assertEqual(report((*words, 0xffffffff))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report(words, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=10))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_stale_actual_comparison_branch_error_success_and_tail_decline(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        words = (*with_cmp_arm((0x91001400,)), 0xd503201f)
        value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size)
        call = report(words)['calls'][0]
        for offset, word in ((4, 0xf100029f), (8, 0x540000a1), (12, 0xaa1403e0),
                             (20, 0xd2800540), (24, 0x14000003), (28, 0x91001800),
                             (32, 0xd503201f), (44, 0xd65f0000), (48, 0x17fffff6)):
            with self.subTest(offset=offset):
                raw = bytearray(data); struct.pack_into('<I', raw, offset, word)
                changed = bytes(raw)
                self.assertEqual(_success_result(changed, function, call,
                    _caller_direct_edges(changed, function))['status'], 'declined')

    def test_forged_flag_region_and_plan_evidence_decline(self):
        from copy import deepcopy
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        words = with_cmp_arm((0x91001400,)); value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); scan = _caller_direct_edges(data, function)
        original = report(words)['calls'][0]
        for group, key, changed in (('flag_entry_validation', 'flag_state_proven', True),
            ('flag_entry_validation', 'caller_scan_complete', False),
            ('error_region', 'opaque_call_count', 0), ('presentation', 'source_reconstruction_allowed', True)):
            call = deepcopy(original); call[group][key] = changed
            self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
        call = deepcopy(original); call.pop('flag_entry_validation')
        self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')

    def test_untracked_original_narrow_and_killed_aliases_refuse(self):
        for arm in ((0x91001660,), (0xaa0003f3, 0x91001674, 0xaa1303e0),
                    (0x2a0003f3, 0x91001660), (0xaa0003f3, 0xaa1f03f3, 0x91001660)):
            self.assertEqual(report(with_cmp_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_zero_narrow_flags_sp_repeated_and_literal_arithmetic_refuse(self):
        for arm in ((0x91000000,), (0x11001400,), (0xb1001400,), (0x910017e0,),
                    (0x9100141f,), (0x91001400, 0xd1000400), (0x91001400, 0xd2800000)):
            self.assertEqual(report(with_cmp_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_arm_budget_accepts_eight_and_refuses_nine(self):
        for count, expected in ((8, 'structural_choice_candidate'), (9, 'unresolved')):
            arm = (0x91001400, *((0xd503201f,)*(count-1)))
            self.assertEqual(report(with_cmp_arm(arm))['calls'][0]['return_choice']['status'], expected)

    def test_ne_forward_arithmetic_uses_its_separate_layout(self):
        from test_swift_cmp_ne_handler import WORDS as NE, report as ne_report
        call = ne_report((*NE[:2], 0x91001400, *NE[3:]))['calls'][0]
        self.assertEqual(call['error_region']['layout'], 'success_fallthrough_error_forward')
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')

    def test_void_callee_cannot_supply_an_int_result(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        value = recover_swift_error_flow(image(with_cmp_arm((0x91001400,)), symbol='_$s4Demo4readyyKF'),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_error_alias_in_x0_is_not_a_preserved_call_result(self):
        words = with_cmp_arm((0x91001400,))
        call = report((0xaa1503e0, 0xf100001f, *words[1:]))['calls'][0]
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_cli_and_text_retain_condition_amount_and_unproven_flags(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_error_flow import image
        words = with_cmp_arm((0xd1400400,))
        text = render_swift_error_text(report(words))
        self.assertIn('call result - 4096 modulo 2^64', text)
        self.assertIn('Source reconstruction: disabled', text)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder)/'compare-arithmetic.macho'; source.write_bytes(image(words).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['condition']['test_condition'], 'eq')
            self.assertEqual(choice['success']['immediate'], 4096)
            for key in ('runtime_value_proven', 'source_reconstruction_allowed', 'exclusive_path_proven',
                        'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
                self.assertFalse(choice[key])
