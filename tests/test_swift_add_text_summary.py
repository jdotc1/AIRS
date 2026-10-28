"""Safe human-readable summaries for bounded success ADD evidence."""
import unittest
from copy import deepcopy
from airs.swift_error_text import render_swift_error_text
from test_swift_owned_postcall_arithmetic import report


class SwiftAddTextSummaryTests(unittest.TestCase):
    def test_adjusted_choice_is_readable_without_claiming_runtime(self):
        text = render_swift_error_text(report())
        self.assertIn('Success operation (structural; runtime unproven): "call result + 5 modulo 2^64"', text)
        self.assertIn('Source reconstruction: disabled', text)

    def test_inconsistent_or_unproved_choice_has_no_summary(self):
        original = report()
        for section, key, value in (('return_choice', 'status', 'unresolved'),
                                    ('return_choice', 'runtime_value_proven', True),
                                    ('success_result', 'immediate', 6),
                                    ('success_result', 'bit_width', 32)):
            candidate = deepcopy(original); candidate['calls'][0][section][key] = value
            self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(candidate))

    def test_all_proof_scopes_and_identity_must_remain_consistent(self):
        original = report()
        for section, key, value in (('return_choice','source_reconstruction_allowed',True),
            ('return_choice','exclusive_path_proven',True), ('return_choice','caller_return_type_proven',True),
            ('return_choice','call_return_proven',True), ('return_choice','handler_semantics_proven',True),
            ('success_result','source_reconstruction_allowed',True), ('success_result','exclusive_path_proven',True),
            ('success_result','caller_return_type_proven',True), ('success_result','call_pc','0x0'),
            ('success_result','return_pc','0x0')):
            candidate = deepcopy(original); candidate['calls'][0][section][key] = value
            self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(candidate))

    def test_invalid_or_untrusted_operation_fields_never_enter_summary(self):
        original = report()
        for key, value in (('immediate', True), ('immediate', 0), ('immediate', 4096),
                           ('immediate', '\x1b[2J'), ('operation', 'sub'), ('register', 'x1'), ('bit_width', 32)):
            candidate = deepcopy(original); candidate['calls'][0]['return_choice']['success'][key] = value
            text = render_swift_error_text(candidate)
            self.assertNotIn('Success operation (structural; runtime unproven):', text)
            self.assertNotIn('\x1b', text)

    def test_other_choice_kinds_do_not_gain_an_add_summary(self):
        from test_swift_cmp_ne_handler import report as literal_report
        from test_swift_cmp_ne_success_result import PRESERVED
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(literal_report()))
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(literal_report(PRESERVED)))

    def test_byte_budget_and_report_immutability_are_preserved(self):
        from airs.types import InputError
        value = report(); original = deepcopy(value)
        text = render_swift_error_text(value)
        self.assertEqual(value, original)
        self.assertEqual(render_swift_error_text(value, maximum_bytes=len(text.encode('ascii'))), text)
        with self.assertRaises(InputError) as error:
            render_swift_error_text(value, maximum_bytes=len(text.encode('ascii'))-1)
        self.assertEqual(error.exception.code, 'generated_report_size_limit')

    def test_mismatched_condition_and_success_entry_are_withheld(self):
        original = report()
        for section, key, value in (('return_choice','condition',{'test_pc':'0x0'}),
                                    ('success_result','success_pc','0x0'),
                                    ('return_choice','return_pc',None),
                                    ('return_choice','call_pc',None)):
            candidate = deepcopy(original); candidate['calls'][0][section][key] = value
            self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(candidate))

    def test_summary_requires_recorded_shared_return(self):
        candidate = deepcopy(report()); call = candidate['calls'][0]
        call['presentation']['display_plan']['shared_epilogue']['instructions'][-1]['pc'] = '0x0'
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(candidate))

    def test_agreeing_plan_and_choice_must_still_match_call_condition(self):
        candidate = deepcopy(report()); call = candidate['calls'][0]
        call['return_choice']['condition']['test_pc'] = '0x0'
        call['presentation']['display_plan']['condition']['test_pc'] = '0x0'
        self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(candidate))

    def test_restored_state_and_tail_layout_remain_unproven(self):
        for section in ('tail', 'result'):
            candidate = deepcopy(report()); call = candidate['calls'][0]
            if section == 'tail': call['presentation']['display_plan']['shared_epilogue']['restore_state_proven'] = True
            else: call['success_result']['return_tail_layout'] = 'success_entry'
            self.assertNotIn('Success operation (structural; runtime unproven):', render_swift_error_text(candidate))
