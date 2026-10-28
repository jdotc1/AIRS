"""Bounded arithmetic from a tracked result alias into a different register."""
import unittest
from test_swift_owned_postcall_arithmetic import report
from test_swift_success_arithmetic_copies import with_arm


class CrossRegisterFirstTests(unittest.TestCase):
    def test_add_from_tracked_copy_directly_to_x0(self):
        call = report(with_arm((0xaa0003f3, 0x91001660)))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 5)
        self.assertEqual(call['success_result']['adjustment_source_register'], 19)
        self.assertEqual(call['success_result']['adjustment_register'], 0)
        self.assertFalse(call['return_choice']['runtime_value_proven'])


class CrossRegisterBoundaryTests(unittest.TestCase):
    def test_subtract_to_different_register_then_restore(self):
        arm = (0xaa0003f3, 0xd1001674, 0xaa1403e0)
        call = report(with_arm(arm))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_sub_immediate')
        self.assertEqual((call['success_result']['adjustment_source_register'], call['success_result']['adjustment_register']), (19, 20))

    def test_untracked_or_killed_source_cannot_qualify(self):
        for arm in ((0x91001660,), (0xaa0003f3, 0xaa1f03f3, 0x91001660),
                    (0x2a0003f3, 0x91001660)):
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_original_values_cannot_be_restored_as_adjusted(self):
        for arm in ((0xaa0003f3, 0x91001674),
                    (0xaa0003f3, 0x91001674, 0xaa1303e0),
                    (0xaa0003f3, 0x91001674, 0xaa0003e0)):
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_narrow_flag_and_sp_operands_are_excluded(self):
        for word in (0x11001660, 0xb1001660, 0x910017e0, 0x9100167f):
            call = report(with_arm((0xaa0003f3, word)))['calls'][0]
            self.assertNotEqual(call['presentation']['status'], 'eligible_structural_only')

    def test_register_boundaries_and_immediate_values(self):
        for register in (0, 30):
            source = (0xaa0003e0 | register) if register else 0xd503201f
            word = 0x91000000 | (4095 << 10) | (register << 5) | 0
            call = report(with_arm((source, word)))['calls'][0]
            self.assertEqual(call['return_choice']['success']['immediate'], 4095)
            self.assertEqual(call['success_result']['adjustment_source_register'], register)

    def test_forged_operand_registers_or_words_do_not_produce_choice_or_text(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        from airs.swift_error_text import render_swift_error_text
        original = report(with_arm((0xaa0003f3, 0x91001660)))
        for key, value in (('adjustment_source_register', 0), ('adjustment_register', 19),
                           ('adjustment_source_register', 31), ('adjustment_register', True)):
            report_copy = deepcopy(original); call = report_copy['calls'][0]; call['success_result'][key] = value
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
            self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(report_copy))

    def test_new_side_entries_or_stale_source_word_refuse(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_owned_postcall_arithmetic import SYMBOL
        from test_swift_error_flow import image
        words = (*with_arm((0xaa0003f3, 0x91001660)), 0xd503201f)
        value = image(words, symbol=SYMBOL); function = value.functions[0]
        raw = bytearray(value.bytes_at(function.start, function.size)); call = report(words)['calls'][0]
        struct.pack_into('<I', raw, 28, 0x91001680)
        self.assertEqual(_success_result(bytes(raw), function, call, _caller_direct_edges(bytes(raw), function))['status'], 'declined')
        source = 4 + len(words[:-1])*4
        branch = 0x14000000 | (((28-source)//4) & 0x3ffffff)
        self.assertEqual(report((*words[:-1], branch))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_second_operation_and_word_copy_remain_excluded(self):
        for extra in (0x91000400, 0xd1000400, 0x2a0003e0):
            arm = (0xaa0003f3, 0x91001660, extra)
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_text_and_cli_keep_structural_expression(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_owned_postcall_arithmetic import SYMBOL
        from test_swift_error_flow import image
        words = with_arm((0xaa0003f3, 0xd1001660))
        self.assertIn('call result - 5 modulo 2^64', render_swift_error_text(report(words)))
        root = Path('local-evidence/swift-success-arithmetic-cross-register'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder)/'owned.macho'; source.write_bytes(image(words, symbol=SYMBOL).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['success_result']['adjustment_source_register'], 19)
            self.assertFalse(call['return_choice']['runtime_value_proven'])

    def test_x0_source_to_x30_and_restore(self):
        call = report(with_arm((0x9100141e, 0xaa1e03e0)))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')
        self.assertEqual((call['success_result']['adjustment_source_register'], call['success_result']['adjustment_register']), (0, 30))
