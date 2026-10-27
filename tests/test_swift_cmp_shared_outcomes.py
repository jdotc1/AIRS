"""Bounded CMP EQ shared preserved-result and error-literal outcomes."""
import unittest
from test_swift_cmp_shared_epilogue import report, WORDS
from test_swift_error_flow import BASE

# Preserve x0 on success; the error arm assigns -1 before the shared tail.
PRESERVED = (*WORDS[:6], 0xd503201f, *WORDS[7:])


class CmpSharedOutcomeFirstTests(unittest.TestCase):
    def test_preserved_result_and_error_literal_bind_to_shared_tail(self):
        call = report(PRESERVED)['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertEqual(call['success_result']['return_tail_layout'], 'shared_epilogue')
        self.assertEqual(call['error_constant']['constant_bits'], '0xffffffffffffffff')
        choice = call['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['kind'], 'call_result')
        self.assertEqual(choice['condition']['comparison_pc'], hex(BASE+4))
        self.assertEqual(choice['condition']['test_condition'], 'eq')
        self.assertFalse(choice['runtime_value_proven'])
        self.assertFalse(choice['source_reconstruction_allowed'])
        self.assertFalse(choice['call_return_proven'])
        self.assertEqual(call['success_constant']['status'], 'declined')

class CmpSharedOutcomeBoundaryTests(unittest.TestCase):
    def test_postcall_x_copy_roundtrip_recovers_call_result(self):
        call = report((0xaa0003f3, 0xaa1f03e0, 0xaa1303e0, *PRESERVED))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'copied_register_candidate')
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result')

    def test_success_arm_clobber_does_not_become_call_result(self):
        call = report()['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')
        self.assertEqual(call['success_constant']['reason'], 'compare_shared_success_literal_not_qualified')

    def test_narrow_copy_cannot_preserve_unknown_full_width_result(self):
        call = report((0x2a0003e0, *PRESERVED))['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_error_literal_before_opaque_call_is_invalidated(self):
        words = (*PRESERVED[:2], 0x92800000, 0x94000010,
                 0xd503201f, *PRESERVED[5:])
        call = report(words)['calls'][0]
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertEqual(call['error_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_w_error_literal_is_zero_extended(self):
        words = (*PRESERVED[:4], 0x12800000, *PRESERVED[5:])
        call = report(words)['calls'][0]
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0x00000000ffffffff')

    def test_flag_handler_and_tail_side_entries_withhold_choice(self):
        for target in (4, 8, 12, 28, 32, 36, 44):
            branch = 0x14000000 | (((target-48)//4) & 0x3ffffff)
            call = report((*PRESERVED, branch))['calls'][0]
            self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_ne_unknown_and_partial_scan_withhold_choice(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        values = (report((PRESERVED[0], PRESERVED[1] | 1, *PRESERVED[2:])),
                  report((*PRESERVED, 0xffffffff)),
                  report(PRESERVED, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=12)))
        for value in values:
            self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_wrong_tail_and_unmodeled_success_control_decline(self):
        for index, word in ((7, 0xd65f0000), (6, 0x14000001)):
            words = list(PRESERVED); words[index] = word
            self.assertEqual(report(tuple(words))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_actual_comparison_and_branch_words_are_rechecked(self):
        import struct
        from airs.swift_error_flow import _success_result, _caller_direct_edges
        from test_swift_error_flow import image
        value = image(PRESERVED); function = value.functions[0]
        original = report(PRESERVED)['calls'][0]
        for offset, word in ((4, 0xf100029f), (8, 0x540000a1), (8, 0x54000080)):
            data = bytearray(value.bytes_at(function.start, function.size))
            struct.pack_into('<I', data, offset, word)
            result = _success_result(bytes(data), function, original, _caller_direct_edges(bytes(data), function))
            self.assertEqual(result['status'], 'declined')

    def test_choice_requires_bound_shared_return_and_condition(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report(PRESERVED)['calls'][0]
        for section, key, value in (('success_result', 'return_pc', '0x0'),
            ('error_constant', 'return_pc', '0x0'), ('success_result', 'runtime_value_proven', True),
            ('error_constant', 'handler_semantics_proven', True)):
            call = deepcopy(original);call[section][key] = value
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
        call = deepcopy(original);call['presentation']['display_plan']['condition']['comparison_pc'] = hex(BASE)
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_forged_shared_success_literal_cannot_enable_choice(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        call = deepcopy(report(PRESERVED)['calls'][0])
        call['success_constant'] = {'status': 'constant_register_candidate'}
        self.assertEqual(_return_choice(call)['reason'], 'compare_shared_success_result_not_qualified')


class CmpSharedOutcomeDeliveryTests(unittest.TestCase):
    def test_text_exposes_bound_choice_and_false_proofs(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report(PRESERVED))
        for value in ('structural_choice_candidate', '0xffffffffffffffff', 'comparison_pc',
                      '"runtime_value_proven": false', 'Source reconstruction: disabled'):
            self.assertIn(value, text)

    def test_cli_json_retains_shared_result_choice(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        from test_swift_error_flow import image
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-shared-outcomes'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(PRESERVED).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            choice = json.loads(output.getvalue())['calls'][0]['return_choice']
            self.assertEqual(choice['status'], 'structural_choice_candidate')
            self.assertEqual(choice['success']['kind'], 'call_result')
