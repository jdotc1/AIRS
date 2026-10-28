"""Bounded selected-path SUB immediate evidence."""
import unittest
from test_swift_owned_postcall_arithmetic import WORDS, report

SUB_WORDS = (*WORDS[:5], 0xd1001400, *WORDS[6:])


class SuccessSubFirstTests(unittest.TestCase):
    def test_single_sub_forms_structural_modulo_result(self):
        call = report(SUB_WORDS)['calls'][0]
        self.assertEqual(call['success_result']['status'], 'adjusted_register_candidate')
        self.assertEqual(call['success_result']['operation'], 'sub_immediate_modulo')
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result_sub_immediate')
        self.assertEqual(call['return_choice']['success']['immediate'], 5)
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xfffffffffffffff9')
        self.assertFalse(call['return_choice']['runtime_value_proven'])
        self.assertFalse(call['return_choice']['source_reconstruction_allowed'])


class SuccessSubBoundaryTests(unittest.TestCase):
    def test_immediate_limits_and_wrapping_descriptor(self):
        for amount in (1, 4095):
            words = (*WORDS[:5], 0xd1000000 | (amount << 10), *WORDS[6:])
            success = report(words)['calls'][0]['return_choice']['success']
            self.assertEqual(success['immediate'], amount)
            self.assertEqual(success['operation'], 'sub_immediate_modulo')
            self.assertEqual(success['bit_width'], 64)

    def test_shift_flags_width_operands_and_zero_remain_refused(self):
        for word in (0xd1000000, 0xd1400400, 0x51001400, 0xf1001400,
                     0xd1001401, 0xd1001420, 0xd10017ff):
            call = report((*WORDS[:5], word, *WORDS[6:]))['calls'][0]
            if word not in (0xd1001401, 0xd1001420):
                self.assertNotEqual(call['presentation']['status'], 'eligible_structural_only')
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_multiple_or_mixed_operations_are_refused(self):
        for second in (0xd1000400, 0x91000400, 0xd2800013):
            words = (*WORDS[:4], 0x14000003, SUB_WORDS[5], second, *WORDS[6:])
            self.assertEqual(report(words)['calls'][0]['return_choice']['status'], 'unresolved')

    def test_saved_full_width_result_and_unrestored_or_narrow_refusal(self):
        positive = (0xaa0003f3, 0xaa1f03e0, 0xaa1303e0, *SUB_WORDS)
        self.assertEqual(report(positive)['calls'][0]['return_choice']['success']['kind'], 'call_result_sub_immediate')
        for prefix in ((0xaa0003f3, 0xaa1f03e0), (0x2a0003f3, 0xaa1f03e0, 0xaa1303e0)):
            self.assertEqual(report((*prefix, *SUB_WORDS))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_cbnz_cmp_and_void_remain_unqualified(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        self.assertNotEqual(report((SUB_WORDS[0] | 0x01000000, *SUB_WORDS[1:]))['calls'][0]['presentation']['status'], 'eligible_structural_only')
        self.assertNotEqual(report((0xf10002bf, 0x540000a0, *SUB_WORDS[1:]))['calls'][0]['presentation']['status'], 'eligible_structural_only')
        void = recover_swift_error_flow(image(SUB_WORDS, symbol='_$s4Demo4readyyKF'),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(void['calls'][0]['return_choice']['status'], 'unresolved')

    def test_eight_word_success_arm_and_one_over(self):
        for count in (8, 9):
            words = (*WORDS[:4], 0x14000000 | (count+1), *((0xd503201f,)*(count-1)), SUB_WORDS[5], *WORDS[6:])
            self.assertEqual(report(words)['calls'][0]['return_choice']['status'],
                             'structural_choice_candidate' if count == 8 else 'unresolved')

    def test_stale_words_and_side_entries_do_not_reuse_evidence(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_owned_postcall_arithmetic import SYMBOL
        from test_swift_error_flow import image
        words = (*SUB_WORDS, 0xd503201f); value = image(words, symbol=SYMBOL); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); call = report(words)['calls'][0]
        for offset, word in ((4, 0xb4000095), (24, 0xd1001800), (28, 0xd65f0000), (44, 0x17fffffb)):
            raw = bytearray(data); struct.pack_into('<I', raw, offset, word)
            self.assertEqual(_success_result(bytes(raw), function, call, _caller_direct_edges(bytes(raw), function))['status'], 'declined')

    def test_forged_operation_or_immediate_cannot_relabel_evidence(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report(SUB_WORDS)['calls'][0]
        for key, value in (('operation', 'add_immediate_modulo'), ('immediate', 6), ('immediate', True),
                           ('bit_width', 32), ('return_pc', '0x0'), ('runtime_value_proven', True)):
            call = deepcopy(original); call['success_result'][key] = value
            self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_text_summary_is_bounded_and_does_not_claim_source(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report(SUB_WORDS))
        self.assertIn('Success operation (structural; runtime unproven): "call result - 5 modulo 2^64"', text)
        self.assertIn('Source reconstruction: disabled', text)

    def test_cli_retains_subtract_choice(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from test_swift_owned_postcall_arithmetic import SYMBOL
        from test_swift_error_flow import image
        root = Path('local-evidence/swift-success-sub-region'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder)/'owned.macho'; source.write_bytes(image(SUB_WORDS, symbol=SYMBOL).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['success']['operation'], 'sub_immediate_modulo')
            self.assertFalse(choice['runtime_value_proven'])

    def test_forged_success_record_cannot_relabel_captured_arm(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report(SUB_WORDS)['calls'][0]
        for mode in ('append', 'replace', 'plan'):
            call = deepcopy(original)
            if mode == 'append':
                call['success_result']['instructions'].append({'phase':'success', 'pc':'0x0', 'word':'0x91001400'})
            if mode == 'replace':
                row = next(row for row in call['success_result']['instructions'] if row['phase'] == 'success')
                row['word'] = '0x91001400'
            if mode == 'plan':
                call['presentation']['display_plan']['success_interval']['instructions'][0]['word'] = '0x91001400'
            self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_forged_metadata_cannot_relabel_text_summary(self):
        from copy import deepcopy
        from airs.swift_error_text import render_swift_error_text
        value = deepcopy(report(SUB_WORDS)); call = value['calls'][0]
        call['success_result']['operation'] = 'add_immediate_modulo'
        call['return_choice']['success']['operation'] = 'add_immediate_modulo'
        call['return_choice']['success']['kind'] = 'call_result_add_immediate'
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(value))

    def test_jointly_forged_plan_result_choice_cannot_relabel_summary(self):
        from copy import deepcopy
        from airs.swift_error_text import render_swift_error_text
        value = deepcopy(report(SUB_WORDS)); call = value['calls'][0]
        call['success_result']['operation'] = 'add_immediate_modulo'
        call['return_choice']['success']['operation'] = 'add_immediate_modulo'
        call['return_choice']['success']['kind'] = 'call_result_add_immediate'
        call['presentation']['display_plan']['success_interval']['instructions'][0]['word'] = '0x91001400'
        row = next(row for row in call['success_result']['instructions'] if row['phase'] == 'success')
        row['word'] = '0x91001400'
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(value))

    def test_malformed_success_instruction_rows_are_refused(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        call = deepcopy(report(SUB_WORDS)['calls'][0]); call['success_result']['instructions'].append('not an instruction')
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_oversized_arm_or_result_records_withhold_summary(self):
        from copy import deepcopy
        from airs.swift_error_text import render_swift_error_text
        for target in ('arm', 'result'):
            value = deepcopy(report(SUB_WORDS)); call = value['calls'][0]
            if target == 'arm':
                call['presentation']['display_plan']['success_interval']['instructions'] *= 9
            else:
                call['success_result']['instructions'] *= 6
            self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(value))

    def test_oversized_adjusted_result_evidence_refuses_choice(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        call = deepcopy(report(SUB_WORDS)['calls'][0]); call['success_result']['instructions'] *= 6
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_jointly_oversized_shared_tail_withholds_summary(self):
        from copy import deepcopy
        from airs.swift_error_text import render_swift_error_text
        value = deepcopy(report(SUB_WORDS)); call = value['calls'][0]
        for tail in (call['error_region']['shared_epilogue'], call['presentation']['display_plan']['shared_epilogue']):
            tail['instructions'] *= 9
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(value))
