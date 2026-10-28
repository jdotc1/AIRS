"""Bounded CMP/B.EQ fallthrough handlers, with independent flag-entry gating."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image, BASE

# BL at +0, CMP at +4, B.EQ +16 at +8 -> success +24.
# Error interval +12..+24: MOV x0,x21; opaque BL +64; MOVN x0,#0.
WORDS = (0xf10002bf, 0x54000080, 0xaa1503e0, 0x9400000c, 0x92800000)


def report(words=WORDS, **kwargs):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, **kwargs)


class CmpHandlerFirstTests(unittest.TestCase):
    def test_eq_error_fallthrough_records_bounded_opaque_interval(self):
        call = report()['calls'][0]
        region = call['error_region']
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['start_pc'], hex(BASE+12))
        self.assertEqual(region['end_pc_exclusive'], hex(BASE+24))
        self.assertEqual(region['join_pc'], hex(BASE+24))
        self.assertEqual([word['kind'] for word in region['instructions']], ['mov', 'bl', 'movn'])
        self.assertEqual(region['instructions'][1]['call_target_pc'], hex(BASE+64))
        self.assertFalse(region['call_return_proven'])
        self.assertFalse(region['join_reachability_proven'])
        self.assertEqual(region['incoming_validation']['status'], 'no_unexpected_direct_entries')

class CmpHandlerBoundaryTests(unittest.TestCase):
    def region(self, words=WORDS, **kwargs):
        return report(words, **kwargs)['calls'][0]['error_region']

    def test_without_flag_entry_opt_in_declines(self):
        call = recover_swift_error_flow(image(WORDS), include_error_regions=True)['calls'][0]
        self.assertEqual(call['error_region']['reason'], 'compare_flag_entries_required')

    def test_entry_to_comparison_or_branch_blocks_handler(self):
        for word in (0x17fffffb, 0x17fffffc):  # +24 -> +4 or +8.
            with self.subTest(word=hex(word)):
                call = report((*WORDS, word))['calls'][0]
                self.assertEqual(call['flag_entry_validation']['status'], 'unexpected_direct_entries')
                self.assertEqual(call['error_region']['reason'], 'compare_flag_entries_not_clear')

    def test_unknown_caller_word_blocks_handler(self):
        call = report((*WORDS, 0xffffffff))['calls'][0]
        self.assertEqual(call['flag_entry_validation']['status'], 'unresolved')
        self.assertEqual(call['error_region']['reason'], 'compare_flag_entries_not_clear')

    def test_partial_caller_blocks_handler_even_if_region_words_scanned(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        region = self.region(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=6))
        self.assertEqual(region['reason'], 'compare_flag_entries_not_clear')

    def test_ne_handler_layout_stays_declined(self):
        region = self.region((WORDS[0], WORDS[1] | 1, *WORDS[2:]))
        self.assertEqual(region['reason'], 'success_region_control_flow_unmodeled')

    def test_live_copy_before_comparison_can_feed_handler(self):
        call = report((0xaa1503f3, 0xf100027f, 0x54000080,
                       0xaa1303e0, 0x9400000b, 0x92800000))['calls'][0]
        self.assertEqual(call['tested_register'], 'x19')
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertEqual(call['error_region']['start_pc'], hex(BASE+16))
        self.assertEqual(call['error_region']['join_pc'], hex(BASE+28))

    def test_classified_but_unsupported_handler_instruction_declines(self):
        region = self.region((*WORDS[:2], 0x91000400, *WORDS[3:]))
        self.assertEqual(region['reason'], 'error_region_instruction_unmodeled')

    def test_terminal_branch_to_success_is_bounded_region(self):
        region = self.region((*WORDS[:-1], 0x14000001))
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['instructions'][-1]['target_pc'], hex(BASE+24))

    def test_error_interval_side_entry_remains_visible(self):
        call = report((*WORDS, 0x17fffffd))['calls'][0]  # +24 -> error +12.
        self.assertEqual(call['flag_entry_validation']['status'], 'no_unexpected_direct_entries')
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        incoming = call['error_region']['incoming_validation']
        self.assertEqual(incoming['status'], 'unexpected_direct_entries')
        self.assertEqual(incoming['unexpected_entries'][0]['target_pc'], hex(BASE+12))

    def test_region_exact_budget_and_over_budget(self):
        exact = self.region((0xf10002bf, 0x54000220, *(0xd503201f,)*16, 0xd65f03c0))
        self.assertEqual(exact['status'], 'structural_region_candidate')
        self.assertEqual(len(exact['instructions']), 16)
        over = self.region((0xf10002bf, 0x54000240, *(0xd503201f,)*17, 0xd65f03c0))
        self.assertEqual(over['reason'], 'error_region_budget')

    def test_shared_tail_is_a_bounded_region(self):
        # EQ -> success +28; final error B at +24 -> shared RET +32.
        region = self.region((0xf10002bf, 0x540000a0, 0xaa1503e0,
            0x9400000c, 0x92800000, 0x14000002, 0xd2800000, 0xd65f03c0))
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['incoming_validation']['status'], 'no_unexpected_direct_entries')

    def test_region_and_presentation_enable_only_bounded_outcomes(self):
        call = report(include_structured_presentation=True)['calls'][0]
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['presentation']['reason'], 'complete_caller_local_direct_validation')
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertEqual(call['error_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

class CmpHandlerBindingFirstTests(unittest.TestCase):
    def test_flag_entry_record_from_another_window_cannot_unlock_region(self):
        from airs.swift_error_flow import _error_region
        value = image(WORDS)
        function = value.functions[0]
        call = recover_swift_error_flow(value, include_error_regions=True,
            validate_region_entries=True)['calls'][0]
        call['flag_entry_validation']['protected_start_pc'] = hex(BASE+8)
        region = _error_region(value.bytes_at(function.start, function.size), function, call)
        self.assertEqual(region['status'], 'declined')
        self.assertEqual(region['reason'], 'compare_flag_entries_not_clear')

class CmpHandlerGeometryFirstTests(unittest.TestCase):
    def test_forward_geometry_cannot_bypass_eq_only_gate(self):
        from airs.swift_error_flow import _error_region
        value = image((0xf10002bf, 0x54000061, 0xd2800000,
                       0x14000003, 0xaa1503e0, 0x92800000, 0xd65f03c0))
        function = value.functions[0]
        call = recover_swift_error_flow(value, include_error_regions=True,
            validate_region_entries=True)['calls'][0]
        call['test_condition'] = 'eq'
        region = _error_region(value.bytes_at(function.start, function.size), function, call)
        self.assertEqual(region['status'], 'declined')
        self.assertEqual(region['reason'], 'compare_handler_layout_not_qualified')

class CmpHandlerBindingBoundaryTests(unittest.TestCase):
    def test_inconsistent_flag_record_cannot_unlock_handler(self):
        from copy import deepcopy
        from airs.swift_error_flow import _error_region
        value = image(WORDS)
        function = value.functions[0]
        original = recover_swift_error_flow(value, include_error_regions=True,
            validate_region_entries=True)['calls'][0]
        mutations = (
            ('protected_end_pc_exclusive', hex(BASE+16)),
            ('scope', 'other_window'), ('caller_scan_complete', 1),
            ('entry_details_complete', False), ('unclassified_details_complete', False),
            ('unexpected_entry_count', True), ('unexpected_entry_count', 1),
            ('unclassified_word_count', False), ('unclassified_word_count', 1),
            ('exclusive_entry_proven', True), ('flag_state_proven', True),
            ('status', 'unresolved'))
        for key, replacement in mutations:
            with self.subTest(key=key, replacement=replacement):
                call = deepcopy(original)
                call['flag_entry_validation'][key] = replacement
                region = _error_region(value.bytes_at(function.start, function.size), function, call)
                self.assertEqual(region['status'], 'declined')
                self.assertEqual(region['reason'], 'compare_flag_entries_not_clear')

    def test_nonadjacent_comparison_metadata_cannot_unlock_handler(self):
        from airs.swift_error_flow import _error_region
        value = image(WORDS)
        function = value.functions[0]
        call = recover_swift_error_flow(value, include_error_regions=True,
            validate_region_entries=True)['calls'][0]
        call['comparison_pc'] = hex(BASE)
        region = _error_region(value.bytes_at(function.start, function.size), function, call)
        self.assertEqual(region['reason'], 'compare_flag_entries_not_clear')

    def test_inconsistent_success_geometry_cannot_unlock_handler(self):
        from airs.swift_error_flow import _error_region
        value = image(WORDS)
        function = value.functions[0]
        call = recover_swift_error_flow(value, include_error_regions=True,
            validate_region_entries=True)['calls'][0]
        call['success_pc'] = call['error_pc']
        region = _error_region(value.bytes_at(function.start, function.size), function, call)
        self.assertEqual(region['reason'], 'compare_handler_layout_not_qualified')


class CmpHandlerDeliveryTests(unittest.TestCase):
    def test_text_preserves_handler_evidence_without_structured_plan(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report(include_structured_presentation=True))
        for expected in ('Error interval:', '0xaa1503e0', '0x9400000c',
                         'opaque_call', 'Flag-entry validation', 'Incoming validation',
                         'Condition (structural):', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)
        self.assertIn('Condition (structural):', text)

    def test_cli_json_and_text_retain_screened_region(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-handler-regions'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'
            source.write_bytes(image(WORDS).data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for extra in ([], ['--format', 'text']):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(options+extra)
                self.assertEqual(status, 0)
                if extra:
                    self.assertIn('Error interval:', output.getvalue())
                    self.assertIn('Condition (structural):', output.getvalue())
                else:
                    value = json.loads(output.getvalue())
                    self.assertEqual(value['error_region_model_version'], 'swift-sync-error-region-v17')
                    self.assertEqual(value['calls'][0]['error_region']['status'], 'structural_region_candidate')
                    self.assertEqual(value['calls'][0]['presentation']['status'], 'eligible_structural_only')

    def test_text_preserves_refusal_and_flag_conflict(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report((*WORDS, 0x17fffffc),
            include_structured_presentation=True))
        self.assertIn('compare_flag_entries_not_clear', text)
        self.assertIn('Unexpected flag-window entry', text)
        self.assertIn('0x17fffffc', text)
