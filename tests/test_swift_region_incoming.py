"""Caller-local direct-entry controls; no indirect/external exclusivity proof."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image, BASE


class SwiftRegionIncomingFirstTests(unittest.TestCase):
    def test_complete_caller_has_only_expected_error_fallthrough(self):
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000)),
            include_error_regions=True, validate_region_entries=True)
        entry = report['calls'][0]['error_region']['incoming_validation']
        self.assertEqual(entry['status'], 'no_unexpected_direct_entries')
        self.assertEqual(entry['scope'], 'caller_local_direct_edges')
        self.assertEqual(entry['unexpected_entry_count'], 0)
        self.assertTrue(entry['caller_scan_complete'])
        self.assertFalse(entry['exclusive_entry_proven'])


class SwiftRegionIncomingBoundaryTests(unittest.TestCase):
    def report(self, tail=(), **kwargs):
        return recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000, *tail)),
            include_error_regions=True, validate_region_entries=True, **kwargs)

    def entry(self, tail=(), **kwargs):
        return self.report(tail, **kwargs)['calls'][0]['error_region']['incoming_validation']

    def test_all_existing_direct_branch_families_and_calls_find_side_entry(self):
        # Each instruction is at +20 and targets +8 (delta -12).
        branches = (0x14000000 | ((-3) & 0x3ffffff),
                    0x94000000 | ((-3) & 0x3ffffff),
                    0x54000000 | (((-3) & 0x7ffff) << 5),
                    0xb4000000 | (((-3) & 0x7ffff) << 5),
                    0x35000000 | (((-3) & 0x7ffff) << 5),
                    0x36000000 | (((-3) & 0x3fff) << 5),
                    0xb7000000 | (((-3) & 0x3fff) << 5))
        for word in branches:
            item = self.entry((word,))
            self.assertEqual(item['status'], 'unexpected_direct_entries')
            self.assertEqual(item['unexpected_entry_count'], 1)
            self.assertEqual(item['unexpected_entries'][0]['source_pc'], hex(BASE + 20))
            self.assertEqual(item['unexpected_entries'][0]['target_pc'], hex(BASE + 8))

    def test_entry_to_region_interior_also_conflicts(self):
        item = self.entry((0x17fffffe,)) # +20 -> +12.
        self.assertEqual(item['unexpected_entry_count'], 1)
        self.assertEqual(item['unexpected_entries'][0]['target_pc'], hex(BASE + 12))

    def test_join_and_outside_targets_are_not_region_entries(self):
        for word in (0x14000000, 0x14000001):
            self.assertEqual(self.entry((word,))['status'], 'no_unexpected_direct_entries')

    def test_unknown_and_indirect_words_leave_absence_unresolved(self):
        for word in (0xffffffff, 0xd61f0000, 0xd63f0000):
            item = self.entry((word,))
            self.assertEqual(item['status'], 'unresolved')
            self.assertEqual(item['unclassified_word_count'], 1)
            self.assertEqual(item['unclassified_words'][0]['pc'], hex(BASE + 20))

    def test_partial_caller_never_claims_absence(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        item = self.entry(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=5))
        self.assertEqual(item['status'], 'unresolved')
        self.assertFalse(item['caller_scan_complete'])
        self.assertEqual(item['scanned_word_count'], 5)

    def test_observed_conflict_survives_unknown_words(self):
        item = self.entry((0x17fffffd, 0xffffffff))
        self.assertEqual(item['status'], 'unexpected_direct_entries')
        self.assertEqual(item['unexpected_entry_count'], 1)
        self.assertEqual(item['unclassified_word_count'], 1)

    def test_conflict_details_bounded_with_exact_total(self):
        branches = tuple(0x14000000 | (((8 - (20 + i * 4)) // 4) & 0x3ffffff) for i in range(20))
        item = self.entry(branches)
        self.assertEqual(item['unexpected_entry_count'], 20)
        self.assertEqual(len(item['unexpected_entries']), 16)
        self.assertFalse(item['entry_details_complete'])

    def test_unknown_details_bounded_with_exact_total(self):
        item = self.entry((0xffffffff,) * 20)
        self.assertEqual(item['status'], 'unresolved')
        self.assertEqual(item['unclassified_word_count'], 20)
        self.assertEqual(len(item['unclassified_words']), 16)
        self.assertFalse(item['unclassified_details_complete'])

    def test_opt_in_does_not_change_base_region_result(self):
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000)), include_error_regions=True)
        self.assertNotIn('region_incoming_model_version', report)
        self.assertNotIn('incoming_validation', report['calls'][0]['error_region'])

    def test_conflict_does_not_promote_or_remove_structural_candidate(self):
        region = self.report((0x17fffffd,))['calls'][0]['error_region']
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['incoming_validation']['status'], 'unexpected_direct_entries')
        self.assertFalse(region['incoming_validation']['exclusive_entry_proven'])

    def test_declined_region_gets_no_validation_claim(self):
        report = recover_swift_error_flow(image((0xb5000095, 0xaa1503e0, 0xd503201f, 0x92800000)),
            include_error_regions=True, validate_region_entries=True)
        region = report['calls'][0]['error_region']
        self.assertEqual(region['status'], 'declined')
        self.assertNotIn('incoming_validation', region)

    def test_entry_validation_requires_region_option(self):
        from airs.types import InputError
        with self.assertRaises(InputError):
            recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000)), validate_region_entries=True)

    def test_cli_entry_option_and_missing_region_rejection(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-error-flow'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'incoming.macho'
            source.write_bytes(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000, 0x17fffffd)).data)
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(['swift-error-flow', str(source), '--include-error-regions', '--validate-region-entries'])
            self.assertEqual(status, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report['region_incoming_model_version'], 'swift-region-direct-entries-v1')
            self.assertEqual(report['calls'][0]['error_region']['incoming_validation']['unexpected_entry_count'], 1)
            with contextlib.redirect_stderr(errors):
                self.assertEqual(main(['swift-error-flow', str(source), '--validate-region-entries']), 2)


class SwiftRegionIncomingReviewTests(unittest.TestCase):
    def test_inside_opaque_call_is_not_external_side_entry(self):
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0x94000000, 0x92800000)),
            include_error_regions=True, validate_region_entries=True)
        item = report['calls'][0]['error_region']['incoming_validation']
        self.assertEqual(item['status'], 'no_unexpected_direct_entries')
        self.assertEqual(item['unexpected_entry_count'], 0)
        self.assertFalse(item['exclusive_entry_proven'])

    def test_partial_scan_preserves_observed_conflict(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000, 0x17fffffd)),
            replace(DEFAULT_LIMITS, max_instructions_per_function=6),
            include_error_regions=True, validate_region_entries=True)
        item = report['calls'][0]['error_region']['incoming_validation']
        self.assertEqual(item['status'], 'unexpected_direct_entries')
        self.assertFalse(item['caller_scan_complete'])

    def test_invalid_vm_target_remains_unclassified(self):
        import struct
        from types import SimpleNamespace
        from airs.swift_error_flow import _caller_direct_edges
        scan = _caller_direct_edges(struct.pack('<I', 0x17ffffff), SimpleNamespace(start=0, size=4))
        self.assertEqual(scan['direct_edges'], [])
        self.assertEqual(scan['unclassified_word_count'], 1)
