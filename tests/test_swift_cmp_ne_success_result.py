"""Selected CMP/B.NE success-path call-result preservation."""
import unittest
from test_swift_cmp_ne_handler import report, WORDS

PRESERVED = (*WORDS[:2], 0xd503201f, *WORDS[3:])


class NeSuccessResultFirstTests(unittest.TestCase):
    def test_preserved_call_result_is_structural_candidate(self):
        call = report(PRESERVED)['calls'][0]
        result = call['success_result']
        self.assertEqual(result['status'], 'preserved_register_candidate')
        self.assertEqual(result['return_tail_layout'], 'shared_epilogue')
        for key in ('runtime_value_proven', 'exclusive_path_proven', 'caller_return_type_proven', 'source_reconstruction_allowed'):
            self.assertFalse(result[key])
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')


class NeSuccessResultBoundaryTests(unittest.TestCase):
    def test_saved_full_width_copy_can_be_restored_on_success(self):
        save, clear, restore = 0xaa0003f3, 0xaa1f03e0, 0xaa1303e0
        words = (save, clear, *PRESERVED[:2], restore, *PRESERVED[3:])
        result = report(words)['calls'][0]['success_result']
        self.assertEqual(result['status'], 'copied_register_candidate')
        self.assertIn('x19', result['result_registers_before_tail'])

    def test_literal_clobber_or_unrestored_result_is_declined(self):
        call = report()['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')
        words = (0xaa0003f3, 0xaa1f03e0, *PRESERVED)
        self.assertEqual(report(words)['calls'][0]['success_result']['reason'], 'result_not_restored_to_x0')

    def test_narrow_copy_cannot_preserve_unknown_full_width_result(self):
        for word in (0x2a0003e0, 0x2a0003f3):
            words = (word, 0xaa1f03e0, *PRESERVED[:2], 0xaa1303e0, *PRESERVED[3:])
            self.assertEqual(report(words)['calls'][0]['success_result']['status'], 'declined')

    def test_success_movk_and_narrow_write_do_not_preserve_x0(self):
        for word in (0xf2a00020, 0x2a0003e0, 0x52800000):
            words = (*PRESERVED[:2], word, *PRESERVED[3:])
            self.assertEqual(report(words)['calls'][0]['success_result']['status'], 'declined')

    def test_side_entries_unknown_and_partial_callers_decline(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for target in (4, 8, 12, 16, 20, 24, 28):
            branch = 0x14000000 | (((target - 32)//4) & 0x3ffffff)
            self.assertEqual(report((*PRESERVED, branch))['calls'][0]['success_result']['status'], 'declined')
        self.assertEqual(report((*PRESERVED, 0xffffffff))['calls'][0]['success_result']['status'], 'declined')
        self.assertEqual(report(PRESERVED, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=7))['calls'][0]['success_result']['status'], 'declined')

    def test_stale_cmp_branch_arm_tail_or_new_side_entry_declines(self):
        import struct
        from test_swift_error_flow import image
        from airs.swift_error_flow import _success_result
        words = (*PRESERVED, 0xd503201f)
        value = image(words); function = value.functions[0]
        data = value.bytes_at(function.start, function.size)
        call = report(words)['calls'][0]
        for offset, word in ((4, 0xf100029f), (8, 0x54000060), (12, 0xd2800540),
                             (16, 0x14000002), (20, 0xd2800540), (28, 0xd65f0000), (32, 0x17fffffd)):
            raw = bytearray(data); struct.pack_into('<I', raw, offset, word)
            self.assertEqual(_success_result(bytes(raw), function, call, None)['status'], 'declined')

    def test_forged_screen_and_region_evidence_decline(self):
        from copy import deepcopy
        from test_swift_error_flow import image
        from airs.swift_error_flow import _success_result
        value = image(PRESERVED); function = value.functions[0]
        data = value.bytes_at(function.start, function.size); original = report(PRESERVED)['calls'][0]
        for group, key, changed in (('flag_entry_validation', 'flag_state_proven', True),
            ('incoming_validation', 'unexpected_entry_count', 1), ('error_region', 'opaque_call_count', 1)):
            call = deepcopy(original)
            section = call[group] if group == 'flag_entry_validation' else call['error_region'] if group == 'error_region' else call['error_region'][group]
            section[key] = changed
            self.assertEqual(_success_result(data, function, call, None)['status'], 'declined')

    def test_text_retains_candidate_and_closed_choice(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report(PRESERVED))
        for expected in ('preserved_register_candidate', 'compare_ne_outcomes_not_qualified', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_void_callee_and_x0_error_alias_are_not_result_candidates(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        value = recover_swift_error_flow(image(PRESERVED, symbol='_$s4Demo4readyyKF'),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(value['calls'][0]['success_result']['status'], 'declined')
        words = (0xaa1503e0, 0xf100001f, *PRESERVED[1:])
        self.assertEqual(report(words)['calls'][0]['success_result']['status'], 'declined')

    def test_ne_success_literal_and_incomplete_choice_remain_gated(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        call = report(PRESERVED)['calls'][0]
        self.assertEqual(call['success_constant']['reason'], 'compare_ne_outcomes_not_qualified')
        altered = deepcopy(call); altered['return_choice'] = {}; altered['error_constant'] = {'status': 'constant_register_candidate'}
        self.assertEqual(_return_choice(altered)['status'], 'unresolved')

    def test_cli_preserves_candidate_and_closed_choice(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from test_swift_error_flow import image
        root = Path('local-evidence/swift-cmp-ne-success-result')
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(PRESERVED).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
            self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
