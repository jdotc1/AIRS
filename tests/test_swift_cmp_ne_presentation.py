"""Screened CMP/B.NE forward presentation remains structural only."""
import unittest
from test_swift_cmp_ne_handler import report, WORDS
from test_swift_error_flow import BASE, image


class NePresentationFirstTests(unittest.TestCase):
    def test_screened_forward_plan_retains_condition_and_bounded_intervals(self):
        call = report()['calls'][0]
        presentation = call['presentation']
        self.assertEqual(presentation['status'], 'eligible_structural_only')
        self.assertEqual(presentation['display_plan']['condition']['test_condition'], 'ne')
        self.assertEqual(presentation['display_plan']['condition']['error_when'], 'nonzero')
        self.assertEqual(presentation['display_plan']['error_interval']['start_pc'], hex(BASE+20))
        self.assertFalse(presentation['source_reconstruction_allowed'])
        for key in ('success_result', 'success_constant', 'error_constant'):
            self.assertEqual(call[key]['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')


def inspect(call):
    from airs.swift_error_flow import _presentation_eligibility
    value = image(WORDS); function = value.functions[0]
    return _presentation_eligibility(call, value.bytes_at(function.start, function.size), function)


class NePresentationBoundaryTests(unittest.TestCase):
    def test_stale_condition_geometry_or_comparison_is_refused(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for key, replacement in (('comparison_pc', hex(BASE)), ('test_condition', 'eq'),
                                 ('success_pc', hex(BASE+16)), ('error_pc', hex(BASE+24)),
                                 ('tested_register', 'x20')):
            call = deepcopy(original); call[key] = replacement
            self.assertNotEqual(inspect(call)['status'], 'eligible_structural_only')
        for index, word in ((-2, '0x710002bf'), (-2, '0xf100029f'),
                            (-1, '0x54000060'), (-1, '0x54000081'), (-1, '0xffffffff')):
            call = deepcopy(original); call['window'][index]['word'] = word
            self.assertEqual(inspect(call)['status'], 'unresolved')

    def test_stale_supported_arm_and_tail_words_are_refused(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for region_key, index, word in (('success_interval', 0, '0xd2800540'),
                                        ('error', 1, '0xd2800540'),
                                        ('shared_epilogue', 0, '0xd65f0000')):
            call = deepcopy(original); region = call['error_region']
            rows = region['instructions'] if region_key == 'error' else region[region_key]['instructions']
            rows[index]['word'] = word
            self.assertEqual(inspect(call)['status'], 'unresolved')

    def test_stale_exit_target_or_encoded_exit_is_refused(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for key, value in (('target_pc', hex(BASE+24)), ('word', '0x14000002'), ('kind', 'bl')):
            call = deepcopy(original)
            call['error_region']['success_interval']['instructions'][-1][key] = value
            self.assertEqual(inspect(call)['status'], 'unresolved')

    def test_flag_and_incoming_records_must_be_complete_and_bound(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for group, key, value in (('flag_entry_validation', 'protected_start_pc', hex(BASE+8)),
            ('flag_entry_validation', 'flag_state_proven', True),
            ('flag_entry_validation', 'caller_scan_complete', False),
            ('incoming_validation', 'unexpected_entry_count', True),
            ('incoming_validation', 'unclassified_word_count', 1),
            ('incoming_validation', 'exclusive_entry_proven', True)):
            call = deepcopy(original)
            section = call[group] if group == 'flag_entry_validation' else call['error_region'][group]
            section[key] = value
            self.assertNotEqual(inspect(call)['status'], 'eligible_structural_only')

    def test_actual_side_entries_and_unknown_caller_block_plan(self):
        from test_swift_cmp_ne_handler import WORDS
        for target in (4, 8, 12, 16, 20, 24, 28):
            branch = 0x14000000 | (((target-32)//4) & 0x3ffffff)
            self.assertNotEqual(report((*WORDS, branch))['calls'][0]['presentation']['status'], 'eligible_structural_only')
        self.assertNotEqual(report((*WORDS, 0xffffffff))['calls'][0]['presentation']['status'], 'eligible_structural_only')

    def test_outcomes_remain_gated_even_if_supplied_candidate(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        call = deepcopy(report()['calls'][0])
        call['success_constant'] = {'status': 'constant_register_candidate'}
        call['error_constant'] = {'status': 'constant_register_candidate'}
        self.assertEqual(_return_choice(call)['reason'], 'compare_ne_outcomes_not_qualified')

    def test_text_exposes_ne_plan_and_withheld_outcomes(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report())
        for expected in ('Condition (structural):', '"test_condition": "ne"',
                         'compare_ne_outcomes_not_qualified', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_missing_caller_bytes_and_forged_call_metadata_decline(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        call = report()['calls'][0]
        self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')
        modified = deepcopy(call)
        modified['error_region']['opaque_call_count'] = 1
        self.assertEqual(inspect(modified)['status'], 'unresolved')

    def test_opaque_call_target_metadata_must_match_instruction(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        words = (*WORDS[:4], 0x94000010, *WORDS[5:])
        value = image(words); function = value.functions[0]
        call = report(words)['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        call = deepcopy(call); call['error_region']['instructions'][0]['call_target_pc'] = hex(BASE+4)
        self.assertEqual(_presentation_eligibility(call, value.bytes_at(function.start, function.size), function)['status'], 'unresolved')

    def test_cli_json_preserves_ne_plan_and_closed_outcomes(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        root = Path('local-evidence/swift-cmp-ne-presentation')
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(WORDS).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['presentation']['display_plan']['condition']['test_condition'], 'ne')
            self.assertEqual(call['return_choice']['reason'], 'compare_ne_outcomes_not_qualified')
