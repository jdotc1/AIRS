"""CMP EQ shared handler regions with scoped caller-entry evidence."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image, BASE

WORDS = (0xf10002bf, 0x540000a0, 0xaa1503e0, 0x94000010,
         0x92800000, 0x14000002, 0xd2800000, 0xa9427bfd,
         0xa94157f6, 0x9100c3ff, 0xd65f03c0)


def report(words=WORDS, **kwargs):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True, **kwargs)


class CmpSharedFirstTests(unittest.TestCase):
    def test_screened_eq_shared_tail_recovers_region_and_entry_evidence(self):
        call = report()['calls'][0]
        region = call['error_region']
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['start_pc'], hex(BASE+12))
        self.assertEqual(region['end_pc_exclusive'], hex(BASE+28))
        self.assertEqual(region['success_interval']['start_pc'], hex(BASE+28))
        self.assertEqual(region['shared_epilogue']['start_pc'], hex(BASE+32))
        self.assertEqual(region['incoming_validation']['status'], 'no_unexpected_direct_entries')
        self.assertFalse(region['shared_epilogue']['restore_state_proven'])
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

class CmpSharedBoundaryTests(unittest.TestCase):
    def test_direct_entries_into_error_success_or_tail_remain_conflicts(self):
        for target in (12, 28, 32, 36, 44):
            with self.subTest(target=target):
                branch = 0x14000000 | (((target - 48)//4) & 0x3ffffff)
                call = report((*WORDS, branch))['calls'][0]
                self.assertEqual(call['error_region']['incoming_validation']['status'], 'unexpected_direct_entries')
                self.assertEqual(call['presentation']['status'], 'blocked')

    def test_entry_into_cmp_or_flag_branch_prevents_region(self):
        for target in (4, 8):
            branch = 0x14000000 | (((target - 48)//4) & 0x3ffffff)
            call = report((*WORDS, branch))['calls'][0]
            self.assertEqual(call['flag_entry_validation']['status'], 'unexpected_direct_entries')
            self.assertEqual(call['error_region']['reason'], 'compare_flag_entries_not_clear')

    def test_unknown_or_partial_caller_does_not_qualify_region(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        values = (report((*WORDS, 0xffffffff)),
                  report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=12)))
        for value in values:
            self.assertEqual(value['calls'][0]['error_region']['reason'], 'compare_flag_entries_not_clear')

    def test_ne_and_missing_flag_validation_stay_declined(self):
        words = (WORDS[0], WORDS[1] | 1, *WORDS[2:])
        self.assertEqual(report(words)['calls'][0]['error_region']['reason'], 'compare_handler_layout_not_qualified')
        value = recover_swift_error_flow(image(WORDS), include_error_regions=True)
        self.assertEqual(value['calls'][0]['error_region']['reason'], 'compare_flag_entries_required')

    def test_success_arm_control_flow_and_unsupported_tail_decline(self):
        for index, word in ((6, 0x14000001), (6, 0x94000010),
                            (7, 0xd100c3ff), (7, 0xd65f0000)):
            with self.subTest(index=index, word=hex(word)):
                words = list(WORDS); words[index] = word
                self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')

    def test_tail_and_success_arm_bounds_remain_eight_words(self):
        exact = report((*WORDS[:7], *(0xd503201f,)*7, 0xd65f03c0))['calls'][0]['error_region']
        self.assertEqual(len(exact['shared_epilogue']['instructions']), 8)
        over = report((*WORDS[:7], *(0xd503201f,)*8, 0xd65f03c0))['calls'][0]['error_region']
        self.assertEqual(over['status'], 'declined')
        exact = report((*WORDS[:5], 0x14000009, *(0xd503201f,)*8, 0xd65f03c0))['calls'][0]['error_region']
        self.assertEqual(len(exact['success_interval']['instructions']), 8)
        over = report((*WORDS[:5], 0x1400000a, *(0xd503201f,)*9, 0xd65f03c0))['calls'][0]['error_region']
        self.assertEqual(over['status'], 'declined')

    def test_expected_branch_exemption_requires_exact_recorded_eq_evidence(self):
        from copy import deepcopy
        from airs.swift_error_flow import _caller_direct_edges, _region_incoming
        value = image(WORDS); function = value.functions[0]
        call = report()['calls'][0]; region = call['error_region']
        scan = _caller_direct_edges(value.bytes_at(function.start, function.size), function)
        for change in ('recorded_word', 'recorded_pc', 'condition', 'edge_word', 'edge_kind', 'encoded_target'):
            with self.subTest(change=change):
                altered = deepcopy(call); modified = deepcopy(scan)
                edge = next(e for e in modified['direct_edges'] if e['source_pc'] == hex(BASE+8))
                if change == 'recorded_word': altered['window'][-1]['word'] = '0x54000081'
                if change == 'recorded_pc': altered['window'][-1]['pc'] = hex(BASE+4)
                if change == 'condition': altered['test_condition'] = 'ne'
                if change == 'edge_word': edge['word'] = '0x540000a1'
                if change == 'edge_kind': edge['kind'] = 'xcbz'
                if change == 'encoded_target':
                    altered['window'][-1]['word'] = '0x54000080'; edge['word'] = '0x54000080'
                incoming = _region_incoming(modified, region, altered)
                self.assertEqual(incoming['status'], 'unexpected_direct_entries')

    def test_shared_region_enables_presentation_but_not_outcomes(self):
        call = report()['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        for key in ('success_result', 'success_constant'):
            self.assertEqual(call[key]['status'], 'declined')
        self.assertEqual(call['error_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

class CmpSharedEvidenceTests(unittest.TestCase):
    def test_opaque_error_call_into_success_or_tail_is_a_conflict(self):
        for target in (28, 32, 36, 44):
            words = list(WORDS); words[3] = 0x94000000 | (((target-16)//4) & 0x3ffffff)
            region = report(tuple(words))['calls'][0]['error_region']
            self.assertEqual(region['incoming_validation']['status'], 'unexpected_direct_entries')

    def test_conflict_count_exact_when_details_are_capped(self):
        branches = tuple(0x14000000 | (((28-(48+4*i))//4) & 0x3ffffff) for i in range(20))
        entry = report((*WORDS, *branches))['calls'][0]['error_region']['incoming_validation']
        self.assertEqual(entry['unexpected_entry_count'], 20)
        self.assertEqual(len(entry['unexpected_entries']), 16)
        self.assertFalse(entry['entry_details_complete'])

    def test_text_retains_shared_tail_with_structured_plan_withheld(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report())
        for expected in ('Shared tail interval evidence', '0xa9427bfd', '0xd65f03c0',
                         'Incoming validation', 'compare_shared_success_literal_not_qualified',
                         'Condition (structural):', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_json_retains_region_and_eligible_shared_presentation(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-shared-epilogue'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(WORDS).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
            self.assertEqual(call['error_region']['incoming_validation']['status'], 'no_unexpected_direct_entries')
            self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
