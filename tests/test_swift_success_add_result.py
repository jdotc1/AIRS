"""Selected 64-bit add-immediate result evidence on a shared success arm."""
import unittest
from test_swift_owned_postcall_arithmetic import report


class SuccessAddFirstTests(unittest.TestCase):
    def test_frontend_add_forms_bounded_machine_expression_choice(self):
        call = report()['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['success_result']['status'], 'adjusted_register_candidate')
        self.assertEqual(call['success_result']['immediate'], 5)
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 5)
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xfffffffffffffff9')
        self.assertFalse(call['return_choice']['runtime_value_proven'])
        self.assertFalse(call['return_choice']['source_reconstruction_allowed'])


class SuccessAddBoundaryTests(unittest.TestCase):
    def test_immediate_bounds_and_machine_wrap_are_explicit(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        for immediate in (1, 4095):
            word = 0x91000000 | (immediate << 10)
            call = report((*WORDS[:5], word, *WORDS[6:]))['calls'][0]
            self.assertEqual(call['return_choice']['success']['immediate'], immediate)
            self.assertEqual(call['return_choice']['success']['operation'], 'add_immediate_modulo')
            self.assertEqual(call['return_choice']['success']['bit_width'], 64)

    def test_unadmitted_width_flags_shift_operands_and_sub_refuse(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        for word in (0x91000000, 0x91400400, 0x11001400, 0xb1001400,
                     0xd1001401, 0x91001401, 0x91001420, 0x910017ff):
            call = report((*WORDS[:5], word, *WORDS[6:]))['calls'][0]
            if word not in (0xd1001401, 0x91001401, 0x91001420):
                self.assertNotEqual(call['presentation']['status'], 'eligible_structural_only')
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_add_with_literal_or_second_add_remains_declined(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        # Extend error branch's shared join across an extra success word.
        for second in (0xd2800013, 0x91000400):
            words = (*WORDS[:4], 0x14000003, WORDS[5], second, *WORDS[6:])
            self.assertEqual(report(words)['calls'][0]['return_choice']['status'], 'unresolved')

    def test_nop_before_and_after_add_remain_bounded(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        words = (*WORDS[:4], 0x14000004, 0xd503201f, WORDS[5], 0xd503201f, *WORDS[6:])
        choice = report(words)['calls'][0]['return_choice']
        self.assertEqual(choice['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(choice['success']['immediate'], 5)

    def test_side_entry_unknown_or_partial_caller_withholds_choice(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        from test_swift_error_flow import image
        from airs.swift_error_flow import recover_swift_error_flow, DEFAULT_LIMITS
        from dataclasses import replace
        for target in (8, 12, 24, 28, 40):
            branch = 0x14000000 | (((target-44)//4) & 0x3ffffff)
            self.assertEqual(report((*WORDS, branch))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report((*WORDS, 0xffffffff))['calls'][0]['return_choice']['status'], 'unresolved')
        value = recover_swift_error_flow(image(WORDS), limits=replace(DEFAULT_LIMITS, max_instructions_per_function=10),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_stale_result_and_side_entry_bytes_refuse(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_owned_postcall_arithmetic import WORDS, SYMBOL
        from test_swift_error_flow import image
        words = (*WORDS, 0xd503201f); value = image(words, symbol=SYMBOL); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); call = report(words)['calls'][0]
        for offset, word in ((4, 0xb4000095), (24, 0x91001800), (28, 0xd65f0000), (44, 0x17fffffb)):
            raw = bytearray(data); struct.pack_into('<I', raw, offset, word)
            self.assertEqual(_success_result(bytes(raw), function, call, _caller_direct_edges(bytes(raw), function))['status'], 'declined')

    def test_choice_rejects_forged_adjustment_and_proof(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report()['calls'][0]
        for key, value in (('immediate', 0), ('immediate', 4096), ('immediate', True),
                           ('operation', 'sub'), ('bit_width', 32), ('runtime_value_proven', True), ('return_pc', '0x0')):
            call = deepcopy(original); call['success_result'][key] = value
            self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_text_and_cli_retain_expression_with_false_proofs(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_owned_postcall_arithmetic import WORDS, SYMBOL
        from test_swift_error_flow import image
        text = render_swift_error_text(report())
        for expected in ('call_result_add_immediate', 'add_immediate_modulo', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)
        root = Path('local-evidence/swift-success-add-region'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder)/'owned.macho'; source.write_bytes(image(WORDS, symbol=SYMBOL).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['success']['immediate'], 5)
            self.assertFalse(choice['runtime_value_proven'])

    def test_saved_full_width_result_restored_before_add(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        words = (0xaa0003f3, 0xaa1f03e0, 0xaa1303e0, *WORDS)
        self.assertEqual(report(words)['calls'][0]['return_choice']['success']['kind'], 'call_result_add_immediate')

    def test_unrestored_or_narrow_pretest_result_refuses(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        for prefix in ((0xaa0003f3, 0xaa1f03e0), (0x2a0003f3, 0xaa1f03e0, 0xaa1303e0)):
            self.assertEqual(report((*prefix, *WORDS))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_void_callee_does_not_become_adjusted_result(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_owned_postcall_arithmetic import WORDS
        from test_swift_error_flow import image
        value = recover_swift_error_flow(image(WORDS, symbol='_$s4Demo4readyyKF'),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(value['calls'][0]['success_result']['status'], 'declined')
        self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_cbnz_and_cmp_layouts_remain_outside_add_subset(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        self.assertNotEqual(report((WORDS[0] | 0x01000000, *WORDS[1:]))['calls'][0]['presentation']['status'], 'eligible_structural_only')
        words = (0xf10002bf, 0x540000a0, *WORDS[1:])
        self.assertNotEqual(report(words)['calls'][0]['presentation']['status'], 'eligible_structural_only')

    def test_success_arm_limit_eight_and_nine(self):
        from test_swift_owned_postcall_arithmetic import WORDS
        for count in (8, 9):
            words = (*WORDS[:4], 0x14000000 | (count+1), *((0xd503201f,)*(count-1)), WORDS[5], *WORDS[6:])
            call = report(words)['calls'][0]
            self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate' if count == 8 else 'unresolved')
