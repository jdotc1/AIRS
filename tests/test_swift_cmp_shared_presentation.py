"""Bounded CMP EQ shared structural presentation; outcomes remain gated."""
import unittest
from test_swift_cmp_shared_epilogue import report
from test_swift_error_flow import BASE


class CmpSharedPresentationFirstTests(unittest.TestCase):
    def test_screened_shared_region_is_structurally_displayable(self):
        call = report()['calls'][0]
        value = call['presentation']
        self.assertEqual(value['status'], 'eligible_structural_only')
        self.assertFalse(value['source_reconstruction_allowed'])
        plan = value['display_plan']
        self.assertEqual(plan['condition']['comparison_pc'], hex(BASE+4))
        self.assertEqual(plan['condition']['test_pc'], hex(BASE+8))
        self.assertEqual(plan['condition']['test_condition'], 'eq')
        self.assertEqual(plan['condition']['error_when'], 'nonzero')
        self.assertEqual(plan['success_interval']['start_pc'], hex(BASE+28))
        self.assertEqual(plan['shared_epilogue']['start_pc'], hex(BASE+32))
        for key in ('success_result', 'success_constant', 'error_constant'):
            self.assertEqual(call[key]['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

class CmpSharedPresentationBoundaryTests(unittest.TestCase):
    def test_stale_flag_entry_records_do_not_enable_plan(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for key, value in (('protected_start_pc', hex(BASE+8)), ('protected_end_pc_exclusive', hex(BASE+16)),
                           ('status', 'unresolved'), ('caller_scan_complete', False),
                           ('unexpected_entry_count', True), ('unclassified_word_count', 1),
                           ('flag_state_proven', True), ('exclusive_entry_proven', True)):
            call = deepcopy(original); call['flag_entry_validation'][key] = value
            self.assertNotEqual(_presentation_eligibility(call)['status'], 'eligible_structural_only')

    def test_stale_compare_or_branch_evidence_never_enables_plan(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for key, value in (('comparison_pc', hex(BASE)), ('test_condition', 'ne'),
                           ('error_pc', hex(BASE+16)), ('success_pc', hex(BASE+32))):
            call = deepcopy(original);call[key] = value
            self.assertNotEqual(_presentation_eligibility(call)['status'], 'eligible_structural_only')
        for index, word in ((-2, '0x710002bf'), (-1, '0x540000a1'), (-1, '0x54000080')):
            call = deepcopy(original);call['window'][index]['word'] = word
            self.assertNotEqual(_presentation_eligibility(call)['status'], 'eligible_structural_only')

    def test_stale_error_exit_word_or_target_never_enables_plan(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for key, value in (('word', '0x14000001'), ('kind', 'nop'),
                           ('target_pc', hex(BASE+36)), ('pc', hex(BASE+20))):
            call = deepcopy(original);call['error_region']['instructions'][-1][key] = value
            self.assertNotEqual(_presentation_eligibility(call)['status'], 'eligible_structural_only')

    def test_stale_success_or_tail_words_and_metadata_decline(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        cases = (('success_interval', 0, 'word', '0x14000001'),
                 ('success_interval', 0, 'kind', 'nop'),
                 ('shared_epilogue', 0, 'word', '0x94000010'),
                 ('shared_epilogue', -1, 'word', '0xd503201f'),
                 ('shared_epilogue', -1, 'kind', 'nop'),
                 ('shared_epilogue', 0, 'pc', hex(BASE+36)))
        for section, index, key, value in cases:
            with self.subTest(section=section, key=key, value=value):
                call = deepcopy(original);call['error_region'][section]['instructions'][index][key] = value
                self.assertNotEqual(_presentation_eligibility(call)['status'], 'eligible_structural_only')
        call = deepcopy(original); call['error_region']['shared_epilogue']['restore_state_proven'] = True
        self.assertNotEqual(_presentation_eligibility(call)['status'], 'eligible_structural_only')

    def test_invalid_interval_bounds_and_incomplete_rows_decline(self):
        from copy import deepcopy
        from airs.swift_error_flow import _presentation_eligibility
        original = report()['calls'][0]
        for section, key, value in (('success_interval', 'start_pc', hex(BASE+24)),
            ('success_interval', 'end_pc_exclusive', hex(BASE+36)),
            ('shared_epilogue', 'end_pc_exclusive', hex(BASE+44)),
            ('shared_epilogue', 'instructions', [])):
            call = deepcopy(original);call['error_region'][section][key] = value
            self.assertNotEqual(_presentation_eligibility(call)['status'], 'eligible_structural_only')

    def test_flag_and_handler_side_entries_block_presentation(self):
        from test_swift_cmp_shared_epilogue import WORDS
        for target in (4, 8, 12, 28, 32, 36, 44):
            branch = 0x14000000 | (((target-48)//4) & 0x3ffffff)
            call = report((*WORDS, branch))['calls'][0]
            self.assertEqual(call['presentation']['status'], 'blocked')

    def test_ne_partial_and_unknown_callers_stay_blocked(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        from test_swift_cmp_shared_epilogue import WORDS
        values = (report((WORDS[0], WORDS[1] | 1, *WORDS[2:])),
                  report((*WORDS, 0xffffffff)),
                  report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=12)))
        for value in values:
            self.assertEqual(value['calls'][0]['presentation']['status'], 'blocked')

    def test_all_shared_cmp_outcome_helpers_remain_explicitly_gated(self):
        call = report()['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        for key in ('success_result', 'success_constant', 'error_constant', 'return_choice'):
            self.assertEqual(call[key]['reason'], 'compare_shared_outcomes_not_qualified')
            self.assertFalse(call[key]['runtime_value_proven'])
            self.assertFalse(call[key]['source_reconstruction_allowed'])


class CmpSharedPresentationDeliveryTests(unittest.TestCase):
    def test_text_shows_shared_plan_words_and_withheld_outcomes(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report())
        for expected in ('Condition (structural):', 'comparison_pc', 'test_condition',
                         'Shared restore/return candidate', '0xa9427bfd', '0xd65f03c0',
                         'compare_shared_outcomes_not_qualified', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)

    def test_cli_json_retains_plan_and_declined_outcomes(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        from test_swift_error_flow import image
        from test_swift_cmp_shared_epilogue import WORDS
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-cmp-shared-presentation'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(WORDS).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
            self.assertEqual(call['return_choice']['reason'], 'compare_shared_outcomes_not_qualified')
