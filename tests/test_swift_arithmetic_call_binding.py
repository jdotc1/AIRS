"""Bind every arithmetic layout to its original call and caller instructions."""
import struct
import unittest
from airs.swift_error_flow import _caller_direct_edges, _success_result, recover_swift_error_flow
from test_swift_error_flow import image
from test_swift_success_arithmetic_copies import with_arm
from test_swift_cmp_success_arithmetic import with_cmp_arm
from test_swift_cmp_ne_success_arithmetic import with_ne_arm
from test_swift_cbnz_success_arithmetic import with_cbnz_arm

LAYOUTS = (('cbz', with_arm), ('eq', with_cmp_arm), ('ne', with_ne_arm), ('cbnz', with_cbnz_arm))


def recorded(words):
    value = image(words); function = value.functions[0]
    report = recover_swift_error_flow(value, include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True)
    return function, value.bytes_at(function.start, function.size), report['calls'][0]


class ArithmeticCallBindingFirstTests(unittest.TestCase):
    def test_changed_call_instruction_or_target_invalidates_all_arithmetic_layouts(self):
        for name, layout in LAYOUTS:
            function, data, call = recorded(layout((0x91001400,)))
            for word in (0xd503201f, 0x94000040):
                with self.subTest(layout=name, word=hex(word)):
                    raw = bytearray(data); struct.pack_into('<I', raw, 0, word); changed = bytes(raw)
                    self.assertEqual(_success_result(changed, function, call,
                        _caller_direct_edges(changed, function))['status'], 'declined')


class ArithmeticCallBindingBoundaryTests(unittest.TestCase):
    def test_valid_shifted_result_and_error_aliases_survive_common_binding(self):
        for name, layout in LAYOUTS:
            with self.subTest(layout=name):
                words = list(layout((0xd1400674, 0xaa1403e0)))
                words[0] = ((words[0] & ~(31 << 5)) | (22 << 5) if name in ('eq', 'ne')
                            else (words[0] & ~31) | 22)
                function, data, call = recorded((0xaa0003f3, 0xaa1503f6, *words))
                result = _success_result(data, function, call, _caller_direct_edges(data, function))
                self.assertEqual(result['status'], 'adjusted_register_candidate')
                self.assertEqual(result['operation'], 'sub_immediate_modulo')
                self.assertEqual(result['immediate'], 4096)
                self.assertEqual(result['immediate_shift'], 12)
                self.assertEqual(call['tested_register'], 'x22')
                self.assertEqual(call['return_choice']['success']['immediate'], 4096)
                for key in ('runtime_value_proven', 'source_reconstruction_allowed',
                            'exclusive_path_proven', 'caller_return_type_proven'):
                    self.assertFalse(result[key])

    def test_missing_or_mismatched_call_metadata_refuses_all_layouts(self):
        from copy import deepcopy
        for name, layout in LAYOUTS:
            function, data, original = recorded(layout((0x91001400,)))
            scan = _caller_direct_edges(data, function)
            for key, value in (('call_word', '0x94000040'), ('call_word', None),
                               ('callee_pc', original['success_pc']), ('callee_pc', None),
                               ('call_pc', hex(function.start + 1))):
                with self.subTest(layout=name, field=key, value=value):
                    call = deepcopy(original); call[key] = value
                    self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
            call = deepcopy(original); del call['call_word']
            self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')

    def test_direct_entry_bypassing_postcall_copies_withholds_choice(self):
        for name, layout in LAYOUTS:
            words = (0xaa0003f3, 0xaa1503f6, *layout((0x91001660,)))
            source = 4 + len(words)*4
            for target in (4, 8, 12):
                with self.subTest(layout=name, target=target):
                    branch = 0x14000000 | (((target-source)//4) & 0x3ffffff)
                    _, _, call = recorded((*words, branch))
                    self.assertEqual(call['success_result']['status'], 'declined')
                    self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_stale_error_arm_or_error_call_never_reuses_old_arithmetic(self):
        for name, layout in LAYOUTS:
            function, data, call = recorded(layout((0x91001400,)))
            error_rows = call['error_region']['instructions']
            first_row = error_rows[0]
            mutations = [(int(first_row['pc'], 16) - function.start, 0xaa1403e0)]
            for row in error_rows:
                if row['kind'] == 'bl':
                    mutations.append((int(row['pc'], 16) - function.start, 0x94000040))
            for offset, word in mutations:
                with self.subTest(layout=name, offset=offset):
                    raw = bytearray(data); struct.pack_into('<I', raw, offset, word); changed = bytes(raw)
                    self.assertEqual(_success_result(changed, function, call,
                        _caller_direct_edges(changed, function))['status'], 'declined')

    def test_forged_error_region_or_display_plan_refuses_cbz_result(self):
        from copy import deepcopy
        function, data, original = recorded(with_arm((0x91001400,)))
        scan = _caller_direct_edges(data, function)
        for key, value in (('opaque_call_count', 0), ('call_return_proven', True),
                           ('join_reachability_proven', True)):
            call = deepcopy(original); call['error_region'][key] = value
            self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')
        call = deepcopy(original); call['presentation']['display_plan']['condition']['register'] = 'x20'
        self.assertEqual(_success_result(data, function, call, scan)['status'], 'declined')

    def test_error_alias_clobbered_before_test_cannot_be_forged_as_live(self):
        from copy import deepcopy
        for name, layout in LAYOUTS:
            words = (0xaa1503f6, *layout((0x91001400,)))
            function, data, original = recorded(words)
            raw = bytearray(data); struct.pack_into('<I', raw, 4, 0xaa0003f5); changed = bytes(raw)
            call = deepcopy(original)
            call['window'][0]['word'] = '0xaa0003f5'
            self.assertEqual(_success_result(changed, function, call,
                _caller_direct_edges(changed, function))['status'], 'declined')

    def test_unknown_or_truncated_caller_cannot_clear_call_binding(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for name, layout in LAYOUTS:
            words = layout((0x91001400,))
            _, _, call = recorded((*words, 0xffffffff))
            self.assertEqual(call['return_choice']['status'], 'unresolved')
            result = recover_swift_error_flow(image(words), include_error_regions=True,
                validate_region_entries=True, include_structured_presentation=True,
                limits=replace(DEFAULT_LIMITS, max_instructions_per_function=5))
            self.assertEqual(result['calls'][0]['return_choice']['status'], 'unresolved')

    def test_declined_cbz_arithmetic_has_no_concise_operation_in_cli_text(self):
        import contextlib, io
        from pathlib import Path
        from fixture_storage import temporary_directory
        from airs.cli import main
        words = with_arm((0x91001400,)); source_pc = 4 + len(words)*4
        branch = 0x14000000 | (((4-source_pc)//4) & 0x3ffffff)
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder)/'bypassed-call-result.macho'
            source.write_bytes(image((*words, branch)).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation', '--format', 'text'])
            self.assertEqual(status, 0)
            text = output.getvalue()
            self.assertIn('unexpected_postcall_entries', text)
            self.assertIn('Source reconstruction: disabled', text)
            self.assertNotIn('Success operation (structural; runtime unproven):', text)
