"""Bounded arithmetic on a tracked full-width call-result register."""
import unittest
from test_swift_owned_postcall_arithmetic import report
from test_swift_success_arithmetic_copies import with_arm


class ArithmeticRegisterFirstTests(unittest.TestCase):
    def test_adjust_tracked_copy_then_restore_x0(self):
        arm = (0xaa0003f3, 0x91001673, 0xaa1303e0)
        call = report(with_arm(arm))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 5)
        self.assertFalse(call['return_choice']['runtime_value_proven'])
        self.assertFalse(call['return_choice']['source_reconstruction_allowed'])


class ArithmeticRegisterBoundaryTests(unittest.TestCase):
    def test_subtract_on_tracked_register_and_transitive_restore(self):
        arm = (0xaa0003f3, 0xd1001673, 0xaa1303f4, 0xaa1403e0)
        call = report(with_arm(arm))['calls'][0]
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_sub_immediate')
        self.assertEqual(call['success_result']['adjustment_register'], 19)
        self.assertEqual(call['return_choice']['success']['immediate'], 5)

    def test_untracked_or_killed_operand_cannot_be_adjusted(self):
        for arm in ((0x91001673, 0xaa1303e0),
                    (0xaa0003f3, 0xaa1f03f3, 0x91001673, 0xaa1303e0),
                    (0x2a0003f3, 0x91001673, 0xaa1303e0)):
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_original_x0_or_stale_alias_is_not_adjusted_return(self):
        for arm in ((0xaa0003f3, 0x91001673),
                    (0xaa0003f3, 0xaa0003f4, 0x91001673, 0xaa1403e0)):
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_distinct_registers_sp_narrow_shift_and_flags_refuse(self):
        for word in (0x91001674, 0x91001653, 0x910017ff, 0x11001673, 0x91401673, 0xb1001673, 0x91000273):
            self.assertEqual(report(with_arm((0xaa0003f3, word, 0xaa1303e0)))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_valid_immediate_boundaries(self):
        for amount in (1, 4095):
            word = 0x91000000 | (amount << 10) | (19 << 5) | 19
            call = report(with_arm((0xaa0003f3, word, 0xaa1303e0)))['calls'][0]
            self.assertEqual(call['return_choice']['success']['immediate'], amount)

    def test_second_arithmetic_and_unrestored_adjusted_value_decline(self):
        for arm in ((0xaa0003f3, 0x91001673, 0xd1000673, 0xaa1303e0),
                    (0xaa0003f3, 0x91001673, 0xaa1f03f3, 0xaa1303e0)):
            self.assertEqual(report(with_arm(arm))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_forged_register_or_instruction_cannot_relabel_choice(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report(with_arm((0xaa0003f3, 0x91001673, 0xaa1303e0)))['calls'][0]
        for mode in ('register', 'word', 'plan'):
            call = deepcopy(original)
            if mode == 'register': call['success_result']['adjustment_register'] = 0
            if mode == 'word':
                next(row for row in call['success_result']['instructions'] if row.get('word') == '0x91001673')['word'] = '0x91001400'
            if mode == 'plan': call['presentation']['display_plan']['success_interval']['instructions'][1]['word'] = '0x91001400'
            self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_stale_words_and_side_entries_decline(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_owned_postcall_arithmetic import SYMBOL
        from test_swift_error_flow import image
        arm = (0xaa0003f3, 0x91001673, 0xaa1303e0)
        words = (*with_arm(arm), 0xd503201f); value = image(words, symbol=SYMBOL); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); call = report(words)['calls'][0]
        for offset, word in ((24, 0xaa0003f4), (28, 0x91001a73), (32, 0xaa1403e0)):
            raw = bytearray(data); struct.pack_into('<I', raw, offset, word)
            self.assertEqual(_success_result(bytes(raw), function, call, _caller_direct_edges(bytes(raw), function))['status'], 'declined')
        source = 4 + len(words[:-1])*4
        branch = 0x14000000 | (((28-source)//4) & 0x3ffffff)
        self.assertEqual(report((*words[:-1], branch))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_text_summary_uses_encoded_register_without_source_claim(self):
        from copy import deepcopy
        from airs.swift_error_text import render_swift_error_text
        value = report(with_arm((0xaa0003f3, 0x91001673, 0xaa1303e0)))
        text = render_swift_error_text(value)
        self.assertIn('call result + 5 modulo 2^64', text)
        self.assertIn('Source reconstruction: disabled', text)
        forged = deepcopy(value); forged['calls'][0]['success_result']['adjustment_register'] = 0
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(forged))

    def test_cli_preserves_expression(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from test_swift_owned_postcall_arithmetic import SYMBOL
        from test_swift_error_flow import image
        words = with_arm((0xaa0003f3, 0xd1001673, 0xaa1303e0))
        root = Path('local-evidence/swift-success-arithmetic-registers'); root.mkdir(parents=True, exist_ok=True)
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

    def test_register_zero_and_thirty_boundaries(self):
        for arm in ((0x91001400,), (0xaa0003fe, 0x910017de, 0xaa1e03e0)):
            call = report(with_arm(arm))['calls'][0]
            self.assertEqual(call['return_choice']['success']['kind'], 'call_result_add_immediate')
        for register in (-1, 31, True):
            from copy import deepcopy
            from airs.swift_error_flow import _return_choice
            call = deepcopy(report(with_arm((0xaa0003f3, 0x91001673, 0xaa1303e0)))['calls'][0])
            call['success_result']['adjustment_register'] = register
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
