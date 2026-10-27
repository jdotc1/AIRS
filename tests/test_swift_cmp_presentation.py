"""CMP EQ structural display eligibility, without source or outcome inference."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_cmp_handler_regions import WORDS
from test_swift_error_flow import image, BASE


def report(words=WORDS):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True)


class CmpPresentationFirstTests(unittest.TestCase):
    def test_screened_eq_interval_is_structurally_displayable(self):
        call = report()['calls'][0]
        value = call['presentation']
        self.assertEqual(value['status'], 'eligible_structural_only')
        self.assertFalse(value['source_reconstruction_allowed'])
        condition = value['display_plan']['condition']
        self.assertEqual(condition['comparison_pc'], hex(BASE+4))
        self.assertEqual(condition['test_pc'], hex(BASE+8))
        self.assertEqual(condition['test_kind'], 'cmp_zero_bcond')
        self.assertEqual(condition['test_condition'], 'eq')
        self.assertEqual(condition['error_when'], 'nonzero')
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertEqual(call['error_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['success_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

class CmpPresentationBoundaryTests(unittest.TestCase):
    def test_missing_or_inconsistent_flag_records_never_become_eligible(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for key, replacement in (
            ('scope', 'foreign'), ('protected_start_pc', hex(BASE+8)),
            ('protected_end_pc_exclusive', hex(BASE+16)),
            ('caller_scan_complete', 1), ('entry_details_complete', False),
            ('unclassified_details_complete', False),
            ('unexpected_entry_count', True), ('unclassified_word_count', 1),
            ('flag_state_proven', True), ('exclusive_entry_proven', True)):
            with self.subTest(key=key):
                call = deepcopy(original)
                call['flag_entry_validation'][key] = replacement
                self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')
        for replacement in (None, {}):
            call = deepcopy(original)
            call['flag_entry_validation'] = replacement
            self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')

    def test_stale_comparison_geometry_and_shared_metadata_decline(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for key, replacement in (('comparison_pc', hex(BASE)), ('test_condition', 'ne'),
                                 ('error_pc', hex(BASE+16)), ('success_pc', hex(BASE+12))):
            with self.subTest(key=key):
                call = deepcopy(original); call[key] = replacement
                self.assertNotEqual(_presentation_eligibility(call)['status'], 'eligible_structural_only')
        call = deepcopy(original); call['error_region']['shared_epilogue'] = {}
        self.assertEqual(_presentation_eligibility(call)['status'], 'blocked')
        call = deepcopy(original); call['error_region']['layout'] = 'success_fallthrough_error_forward'
        self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')

    def test_raw_comparison_and_branch_must_match_display_condition(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for index, word in ((-2, '0x710002bf'), (-2, '0xf100029f'),
                            (-1, '0x54000081'), (-1, '0x540000a0'),
                            (-1, '0xffffffff')):
            with self.subTest(index=index, word=word):
                call = deepcopy(original); call['window'][index]['word'] = word
                self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')

    def test_flag_and_handler_entries_remain_separate_blockers(self):
        for word in (0x17fffffc, 0x17fffffd):  # +24 -> B.EQ or handler start.
            with self.subTest(word=hex(word)):
                call = report((*WORDS, word))['calls'][0]
                self.assertEqual(call['presentation']['status'], 'blocked')
                for key in ('success_result', 'success_constant', 'error_constant'):
                    self.assertEqual(call[key]['status'], 'declined')

    def test_unknown_partial_and_ne_remain_ineligible(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for words, limits in (((*WORDS, 0xffffffff), DEFAULT_LIMITS),
            (WORDS, replace(DEFAULT_LIMITS, max_instructions_per_function=6)),
            ((WORDS[0], WORDS[1] | 1, *WORDS[2:]), DEFAULT_LIMITS)):
            call = recover_swift_error_flow(image(words), limits=limits,
                include_error_regions=True, validate_region_entries=True,
                include_structured_presentation=True)['calls'][0]
            self.assertEqual(call['presentation']['status'], 'blocked')

    def test_ordinary_incoming_record_must_be_complete_and_consistent(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for key, replacement in (('scope', 'foreign'), ('caller_scan_complete', False),
                                 ('unexpected_entry_count', True), ('unclassified_word_count', 1)):
            call = deepcopy(original)
            call['error_region']['incoming_validation'][key] = replacement
            self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')

    def test_unknown_success_literal_stays_declined_with_eligible_presentation(self):
        call = report()['calls'][0]
        for key in ('success_constant',):
            self.assertEqual(call[key]['reason'], 'success_x0_constant_not_known')
            self.assertFalse(call[key]['source_reconstruction_allowed'])
            self.assertFalse(call[key]['runtime_value_proven'])


class CmpPresentationDeliveryTests(unittest.TestCase):
    def test_text_displays_comparison_and_condition_but_no_outcome(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report())
        for expected in ('Condition (structural):', 'comparison_pc', 'cmp_zero_bcond',
                         'test_condition', '0xf10002bf', '0x54000080',
                         'Source reconstruction: disabled', 'success_x0_constant_not_known'):
            self.assertIn(expected, text)
        first_call = text.split('Call candidate\n')[1]
        self.assertNotIn('Structured plan: withheld', first_call)

    def test_cli_json_and_text_preserve_eligible_plan_and_closed_outcomes(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-presentation'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(WORDS).data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for extra in ([], ['--format', 'text']):
                output = io.StringIO()
                with contextlib.redirect_stdout(output): status = main(options+extra)
                self.assertEqual(status, 0)
                if extra:
                    self.assertIn('Condition (structural):', output.getvalue())
                else:
                    call = json.loads(output.getvalue())['calls'][0]
                    self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
                    self.assertEqual(call['error_constant']['status'], 'constant_register_candidate')

class CmpPresentationAdditionalShapeTests(unittest.TestCase):
    def test_copied_error_alias_can_be_displayed_with_bounded_outcomes(self):
        call = report((0xaa1503f3, 0xf100027f, 0x54000080,
                       0xaa1303e0, 0x9400000b, 0x92800000))['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        condition = call['presentation']['display_plan']['condition']
        self.assertEqual(condition['register'], 'x19')
        self.assertEqual(condition['comparison_pc'], hex(BASE+8))
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')

    def test_terminal_error_branch_to_success_remains_displayable(self):
        call = report((*WORDS[:-1], 0x14000001))['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        words = call['presentation']['display_plan']['error_interval']['instructions']
        self.assertEqual(words[-1]['target_pc'], hex(BASE+24))
        self.assertEqual(call['error_constant']['status'], 'declined')
