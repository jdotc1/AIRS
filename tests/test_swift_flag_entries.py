"""Bounded direct entries into CMP-zero flag/alias windows; no dominance proof."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image, BASE


def report(tail=(), **kwargs):
    # BL; CMP x21,#0; B.EQ +12; RET; RET; caller-local tail.
    return recover_swift_error_flow(image((0xf10002bf, 0x54000060,
        0xd65f03c0, 0xd65f03c0, *tail)), include_error_regions=True,
        validate_region_entries=True, **kwargs)


class FlagEntryFirstTests(unittest.TestCase):
    def test_complete_window_reports_scoped_absence_with_region_withheld(self):
        value = report()
        call = value['calls'][0]
        entry = call.get('flag_entry_validation', {})
        self.assertEqual(entry.get('status'), 'no_unexpected_direct_entries')
        self.assertEqual(entry['protected_start_pc'], hex(BASE+4))
        self.assertEqual(entry['protected_end_pc_exclusive'], hex(BASE+12))
        self.assertFalse(entry['flag_state_proven'])
        self.assertFalse(entry['exclusive_entry_proven'])
        self.assertEqual(call['error_region']['reason'], 'compare_branch_region_not_qualified')

class FlagEntryBoundaryTests(unittest.TestCase):
    def entry(self, tail=(), **kwargs):
        return report(tail, **kwargs)['calls'][0]['flag_entry_validation']

    def test_branch_to_comparison_conflicts(self):
        value = self.entry((0x17fffffc,))  # +20 -> +4.
        self.assertEqual(value['status'], 'unexpected_direct_entries')
        self.assertEqual(value['unexpected_entries'][0]['target_pc'], hex(BASE+4))

    def test_branch_to_conditional_test_conflicts(self):
        value = self.entry((0x17fffffd,))  # +20 -> +8, bypassing CMP.
        self.assertEqual(value['status'], 'unexpected_direct_entries')
        self.assertEqual(value['unexpected_entries'][0]['target_pc'], hex(BASE+8))

    def test_direct_branch_families_and_calls_conflict(self):
        for word in (0x17fffffd, 0x97fffffd, 0x54ffffa0, 0xb4ffffa0,
                     0xb5ffffa0, 0x3607ffa0, 0x3707ffa0):
            with self.subTest(word=hex(word)):
                value = self.entry((word,))
                self.assertEqual(value['status'], 'unexpected_direct_entries')
                self.assertEqual(value['unexpected_entry_count'], 1)
                self.assertEqual(value['unexpected_entries'][0]['target_pc'], hex(BASE+8))

    def test_alias_copy_window_is_protected(self):
        value = recover_swift_error_flow(image((0xaa1503f3, 0xf100027f,
            0x54000060, 0xd65f03c0, 0x17fffffc)), include_error_regions=True,
            validate_region_entries=True)['calls'][0]['flag_entry_validation']
        self.assertEqual(value['protected_start_pc'], hex(BASE+4))
        self.assertEqual(value['protected_end_pc_exclusive'], hex(BASE+16))
        self.assertEqual(value['unexpected_entries'][0]['target_pc'], hex(BASE+4))
        self.assertEqual(value['status'], 'unexpected_direct_entries')

    def test_unknown_and_indirect_leave_absence_unresolved(self):
        for word in (0xffffffff, 0xd61f0000, 0xd63f0000):
            with self.subTest(word=hex(word)):
                value = self.entry((word,))
                self.assertEqual(value['status'], 'unresolved')
                self.assertEqual(value['unclassified_word_count'], 1)
                self.assertEqual(value['unclassified_words'][0]['pc'], hex(BASE+20))

    def test_partial_prefix_cannot_establish_absence(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        value = self.entry(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=3))
        self.assertEqual(value['status'], 'unresolved')
        self.assertFalse(value['caller_scan_complete'])
        self.assertEqual(value['scanned_word_count'], 3)

    def test_observed_conflict_wins_over_incomplete_scan(self):
        value = self.entry((0x17fffffd, 0xffffffff))
        self.assertEqual(value['status'], 'unexpected_direct_entries')
        self.assertEqual(value['unclassified_word_count'], 1)

    def test_unprotected_targets_do_not_conflict(self):
        for word in (0x17fffffb, 0x17fffffe, 0x14000000, 0x14000001):
            with self.subTest(word=hex(word)):
                value = self.entry((word,))  # Targets +0, +12, +20, +24.
                self.assertEqual(value['status'], 'no_unexpected_direct_entries')
                self.assertEqual(value['unexpected_entry_count'], 0)

    def test_conflict_details_are_bounded_but_total_is_exact(self):
        words = tuple(0x14000000 | ((-3-index) & 0x3ffffff) for index in range(20))
        value = self.entry(words)
        self.assertEqual(value['unexpected_entry_count'], 20)
        self.assertEqual(len(value['unexpected_entries']), 16)
        self.assertFalse(value['entry_details_complete'])

    def test_unknown_details_are_bounded_but_total_is_exact(self):
        value = self.entry((0xffffffff,)*20)
        self.assertEqual(value['status'], 'unresolved')
        self.assertEqual(value['unclassified_word_count'], 20)
        self.assertEqual(len(value['unclassified_words']), 16)
        self.assertFalse(value['unclassified_details_complete'])

    def test_opt_in_only_and_cbz_not_relabelled(self):
        plain = recover_swift_error_flow(image((0xf10002bf, 0x54000060)))
        self.assertNotIn('flag_entry_validation', plain['calls'][0])
        self.assertNotIn('flag_entry_model_version', plain)
        cbz = recover_swift_error_flow(image(), include_error_regions=True,
                                      validate_region_entries=True)
        self.assertNotIn('flag_entry_validation', cbz['calls'][0])

    def test_no_status_unlocks_structured_outcomes(self):
        for tail in ((), (0x17fffffd,), (0xffffffff,)):
            with self.subTest(tail=tail):
                value = report(tail, include_structured_presentation=True)
                call = value['calls'][0]
                self.assertEqual(call['presentation']['status'], 'blocked')
                self.assertNotEqual(call['return_choice']['status'], 'structural_choice_candidate')
                self.assertFalse(call['flag_entry_validation']['flag_state_proven'])

class FlagEntryTextFirstTests(unittest.TestCase):
    def test_text_retains_flag_conflict_and_raw_branch(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report((0x17fffffd,), include_structured_presentation=True))
        self.assertIn('Flag-entry validation', text)
        self.assertIn('Unexpected flag-window entry', text)
        self.assertIn('0x17fffffd', text)
        self.assertIn('Structured plan: withheld', text)

class FlagEntryDeliveryTests(unittest.TestCase):
    def test_renderer_rejects_missing_or_foreign_flag_model(self):
        from airs.swift_error_text import render_swift_error_text
        from airs.types import InputError
        for model in (None, 'foreign'):
            value = report(include_structured_presentation=True)
            value['flag_entry_model_version'] = model
            with self.assertRaises(InputError):
                render_swift_error_text(value)

    def test_renderer_keeps_unknown_scan_and_false_proof_visible(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report((0xffffffff,), include_structured_presentation=True))
        self.assertIn('Unclassified flag-scan word', text)
        self.assertIn('0xffffffff', text)
        self.assertIn('"status": "unresolved"', text)
        self.assertIn('"flag_state_proven": false', text)

    def test_cli_json_and_text_preserve_scoped_flag_evidence(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-flag-entry-validation'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'
            source.write_bytes(image((0xf10002bf, 0x54000060,
                0xd65f03c0, 0xd65f03c0, 0x17fffffd)).data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for extra in ([], ['--format', 'text']):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    status = main(options+extra)
                self.assertEqual(status, 0)
                if extra:
                    self.assertIn('Unexpected flag-window entry', output.getvalue())
                    self.assertIn('Structured plan: withheld', output.getvalue())
                else:
                    value = json.loads(output.getvalue())
                    self.assertEqual(value['flag_entry_model_version'], 'swift-compare-flag-entries-v1')
                    self.assertEqual(value['calls'][0]['flag_entry_validation']['unexpected_entry_count'], 1)

class FlagEntrySharedScanTests(unittest.TestCase):
    def test_observed_conflict_survives_partial_caller(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        value = report((0x17fffffd,), limits=replace(DEFAULT_LIMITS,
            max_instructions_per_function=6))['calls'][0]['flag_entry_validation']
        self.assertEqual(value['status'], 'unexpected_direct_entries')
        self.assertFalse(value['caller_scan_complete'])
        self.assertEqual(value['unexpected_entry_count'], 1)

    def test_same_caller_scan_protects_each_retained_window_separately(self):
        # Callee starts at +64. Second BL at +16 targets it; first B.EQ
        # targets the second CMP at +20, an incoming conflict for that window.
        value = recover_swift_error_flow(image((0xf10002bf, 0x54000060,
            0xd65f03c0, 0x9400000c, 0xf10002bf, 0x54000060,
            0xd65f03c0, 0xd65f03c0, 0xd65f03c0, 0xd65f03c0)),
            include_error_regions=True, validate_region_entries=True)
        first, second = value['calls']
        self.assertEqual(first['flag_entry_validation']['status'], 'no_unexpected_direct_entries')
        entry = second['flag_entry_validation']
        self.assertEqual(entry['status'], 'unexpected_direct_entries')
        self.assertEqual(entry['unexpected_entries'][0]['source_pc'], hex(BASE+8))
        self.assertEqual(entry['unexpected_entries'][0]['target_pc'], hex(BASE+20))
        self.assertEqual(entry['protected_start_pc'], hex(BASE+20))
        self.assertEqual(entry['protected_end_pc_exclusive'], hex(BASE+28))
        self.assertEqual(entry['scanned_word_count'], 16)

class FlagEntryModelDisplayTests(unittest.TestCase):
    def test_text_identifies_flag_entry_evidence_model(self):
        from airs.swift_error_text import render_swift_error_text
        text = render_swift_error_text(report(include_structured_presentation=True))
        self.assertIn('Flag-entry model: "swift-compare-flag-entries-v1"', text)
