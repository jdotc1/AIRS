"""Full-width result copies around bounded success arithmetic."""
import unittest
from test_swift_owned_postcall_arithmetic import WORDS, report


def with_arm(arm):
    return (*WORDS[:4], 0x14000000 | (len(arm)+1), *arm, *WORDS[6:])


class ArithmeticCopiesFirstTests(unittest.TestCase):
    def test_saved_result_restored_before_add_and_adjusted_copy_restored_after(self):
        save, clear, restore, add = 0xaa0003f3, 0xaa1f03e0, 0xaa1303e0, 0x91001400
        call = report(with_arm((save, clear, restore, add, save, clear, restore)))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 5)
        self.assertFalse(call['return_choice']['runtime_value_proven'])


class ArithmeticCopiesBoundaryTests(unittest.TestCase):
    def test_subtraction_and_transitive_adjusted_copy(self):
        arm = (0xd1001400, 0xaa0003f3, 0xaa1303f4, 0xaa1f03e0, 0xaa1403e0)
        call = report(with_arm(arm))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_sub_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 5)

    def test_stale_original_copy_cannot_replace_adjusted_result(self):
        for operation in (0x91001400, 0xd1001400):
            arm = (0xaa0003f3, operation, 0xaa1303e0)
            call = report(with_arm(arm))['calls'][0]
            self.assertEqual(call['success_result']['status'], 'declined')
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_original_result_must_reach_x0_before_adjustment(self):
        arm = (0xaa0003f3, 0xaa1f03e0, 0x91001400)
        call = report(with_arm(arm))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_adjusted_copy_must_be_restored_to_x0(self):
        arm = (0x91001400, 0xaa0003f3, 0xaa1f03e0)
        call = report(with_arm(arm))['calls'][0]
        self.assertEqual(call['success_result']['reason'], 'result_not_restored_to_x0')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_xzr_and_killed_aliases_do_not_invent_value(self):
        for arm in ((0xaa0003ff, 0xaa1f03e0, 0x91001400),
                    (0xaa0003f3, 0xaa1f03f3, 0xaa1f03e0, 0xaa1303e0, 0x91001400),
                    (0x91001400, 0xaa1f03e0, 0xaa1f03e0)):
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_w_copy_literal_or_second_arithmetic_remain_refused(self):
        for word in (0x2a0003f3, 0xd2800013, 0x91000400, 0xd1000400):
            self.assertEqual(report(with_arm((0x91001400, word)))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_eight_word_bound_and_one_over(self):
        for count in (8, 9):
            arm = (0x91001400, *((0xd503201f,)*(count-1)))
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'],
                             'structural_choice_candidate' if count == 8 else 'unresolved')

    def test_actual_side_entries_unknown_caller_and_stale_mov_decline(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        from test_swift_owned_postcall_arithmetic import SYMBOL
        arm = (0x91001400, 0xaa0003f3, 0xaa1f03e0, 0xaa1303e0)
        words = (*with_arm(arm), 0xd503201f)
        source = 4 + len(words[:-1])*4
        branch = 0x14000000 | (((24-source)//4) & 0x3ffffff)
        self.assertEqual(report((*words[:-1], branch))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report((*words[:-1], 0xffffffff))['calls'][0]['return_choice']['status'], 'unresolved')
        value = image(words, symbol=SYMBOL); function = value.functions[0]
        raw = bytearray(value.bytes_at(function.start, function.size)); call = report(words)['calls'][0]
        struct.pack_into('<I', raw, 28, 0xaa0003f4)
        self.assertEqual(_success_result(bytes(raw), function, call, _caller_direct_edges(bytes(raw), function))['status'], 'declined')

    def test_forged_pre_or_post_adjustment_sequence_cannot_relabel_choice(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        arm = (0x91001400, 0xaa0003f3, 0xaa1f03e0, 0xaa1303e0)
        call = deepcopy(report(with_arm(arm))['calls'][0])
        rows = [row for row in call['success_result']['instructions'] if row['phase'] == 'success']
        rows[-1]['word'] = '0xaa1403e0'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_cli_and_text_keep_structural_expression(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_error_flow import image
        from test_swift_owned_postcall_arithmetic import SYMBOL
        words = with_arm((0xd1001400, 0xaa0003f3, 0xaa1f03e0, 0xaa1303e0))
        text = render_swift_error_text(report(words))
        self.assertIn('call result - 5 modulo 2^64', text)
        self.assertIn('Source reconstruction: disabled', text)
        root = Path('local-evidence/swift-success-arithmetic-copies'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder)/'owned.macho'; source.write_bytes(image(words, symbol=SYMBOL).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['success']['kind'], 'call_result_sub_immediate')
            self.assertFalse(choice['runtime_value_proven'])
