"""Presentation permission remains narrower than source reconstruction."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image, BASE


class SwiftPresentationFirstTests(unittest.TestCase):
    def test_qualified_candidate_gets_only_structural_display_plan(self):
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000)),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        result = report['calls'][0]['presentation']
        self.assertEqual(result['status'], 'eligible_structural_only')
        self.assertFalse(result['source_reconstruction_allowed'])
        self.assertEqual(result['display_plan']['kind'], 'structural_error_interval')
        self.assertEqual(result['display_plan']['condition']['test_pc'], hex(BASE + 4))
        self.assertEqual(result['display_plan']['condition']['error_when'], 'nonzero')
        self.assertEqual(result['display_plan']['error_interval']['start_pc'], hex(BASE + 8))
        self.assertEqual(result['display_plan']['success_entry_pc'], hex(BASE + 20))
        self.assertTrue(result['limitations'])
        self.assertEqual(report['summary']['presentation_eligible_structural_only_count'], 1)


class SwiftPresentationBoundaryTests(unittest.TestCase):
    def report(self, tail=(), **kwargs):
        return recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000, *tail)),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True, **kwargs)

    def call(self):
        return recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000)),
            include_error_regions=True, validate_region_entries=True)['calls'][0]

    def test_conflicting_entry_blocks_plan_without_erasing_evidence(self):
        call = self.report((0x17fffffd,))['calls'][0]
        self.assertEqual(call['presentation']['status'], 'blocked')
        self.assertEqual(call['presentation']['reason'], 'unexpected_direct_entries')
        self.assertNotIn('display_plan', call['presentation'])
        self.assertEqual(call['error_region']['incoming_validation']['unexpected_entry_count'], 1)
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')

    def test_unclassified_or_indirect_word_prevents_plan(self):
        for word in (0xffffffff, 0xd61f0000):
            result = self.report((word,))['calls'][0]['presentation']
            self.assertEqual(result['status'], 'unresolved')
            self.assertNotIn('display_plan', result)

    def test_incomplete_caller_prevents_plan(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        result = self.report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=5))['calls'][0]['presentation']
        self.assertEqual(result['status'], 'unresolved')
        self.assertFalse(result['source_reconstruction_allowed'])

    def test_declined_region_is_blocked(self):
        report = recover_swift_error_flow(image((0xb5000095, 0xaa1503e0, 0xd503201f, 0x92800000)),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(report['calls'][0]['presentation']['reason'], 'region_not_recovered')
        self.assertEqual(report['calls'][0]['presentation']['status'], 'blocked')

    def test_declined_edge_is_blocked_and_summary_counts_all_retained_calls(self):
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000)),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual([r['presentation']['status'] for r in report['calls']], ['eligible_structural_only', 'blocked'])
        self.assertEqual(report['summary']['presentation_eligible_structural_only_count'], 1)
        self.assertEqual(report['summary']['presentation_blocked_count'], 1)
        self.assertEqual(report['summary']['presentation_unresolved_count'], 0)
        plan = report['calls'][0]['presentation']['display_plan']
        self.assertEqual(plan['error_interval']['instructions'][1]['semantics'], 'opaque_call')

    def test_missing_validation_is_unresolved(self):
        from airs.swift_error_flow import _presentation_eligibility
        call = self.call(); del call['error_region']['incoming_validation']
        result = _presentation_eligibility(call)
        self.assertEqual(result['status'], 'unresolved')
        self.assertEqual(result['reason'], 'incoming_validation_missing')

    def test_inconsistent_validation_fields_fail_closed(self):
        import copy
        from airs.swift_error_flow import _presentation_eligibility
        original = self.call()
        changes = (('scope', 'all_entries'), ('caller_scan_complete', False),
                   ('unclassified_word_count', 1), ('unexpected_entry_count', 1),
                   ('unexpected_entry_count', False), ('entry_details_complete', False),
                   ('unclassified_details_complete', False), ('exclusive_entry_proven', True),
                   ('status', 'unrecognized'))
        for key, value in changes:
            call = copy.deepcopy(original)
            call['error_region']['incoming_validation'][key] = value
            result = _presentation_eligibility(call)
            self.assertEqual(result['status'], 'unresolved')
            self.assertNotIn('display_plan', result)

    def test_unexpected_proof_claims_never_enable_source_output(self):
        from airs.swift_error_flow import _presentation_eligibility
        for key in ('call_return_proven', 'join_reachability_proven'):
            call = self.call(); call['error_region'][key] = True
            result = _presentation_eligibility(call)
            self.assertEqual(result['status'], 'unresolved')
            self.assertFalse(result['source_reconstruction_allowed'])

    def test_interval_and_instruction_binding_fail_closed(self):
        import copy
        from airs.swift_error_flow import _presentation_eligibility
        original = self.call()
        for key in ('start_pc', 'join_pc', 'end_pc_exclusive'):
            call = copy.deepcopy(original); call['error_region'][key] = hex(BASE + 24)
            self.assertEqual(_presentation_eligibility(call)['reason'], 'presentation_evidence_inconsistent')
        for changes in ('pc', 'word', 'missing', 'empty', 'register'):
            call = copy.deepcopy(original)
            if changes == 'pc': call['error_region']['instructions'][0]['pc'] = hex(BASE + 12)
            elif changes == 'word': call['error_region']['instructions'][0]['word'] = 'unencoded'
            elif changes == 'missing': del call['success_pc']
            elif changes == 'empty': call['error_region']['instructions'] = []
            else: call['tested_register'] = 'x31'
            self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')

    def test_opt_in_absence_preserves_existing_report_shape(self):
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000)),
            include_error_regions=True, validate_region_entries=True)
        self.assertNotIn('structured_presentation_model_version', report)
        self.assertNotIn('presentation', report['calls'][0])
        self.assertNotIn('presentation_blocked_count', report['summary'])

    def test_both_prerequisites_required(self):
        from airs.types import InputError
        for options in ({}, {'include_error_regions': True}, {'validate_region_entries': True}):
            with self.assertRaises(InputError):
                recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000)),
                    include_structured_presentation=True, **options)

    def test_display_plan_instruction_copies_do_not_mutate_region(self):
        call = self.report()['calls'][0]
        call['presentation']['display_plan']['error_interval']['instructions'][0]['pc'] = '0x0'
        self.assertEqual(call['error_region']['instructions'][0]['pc'], hex(BASE + 8))

    def test_cli_serializes_plan_and_rejects_missing_prerequisites(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-error-flow'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'presentation.macho'
            source.write_bytes(image((0xb4000095, 0xaa1503e0, 0xd503201f, 0x92800000)).data)
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
                status = main(['swift-error-flow', str(source), '--include-error-regions', '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            report = json.loads(output.getvalue())
            self.assertEqual(report['structured_presentation_model_version'], 'swift-structural-presentation-v7')
            self.assertEqual(report['calls'][0]['presentation']['status'], 'eligible_structural_only')
            with contextlib.redirect_stderr(errors):
                self.assertEqual(main(['swift-error-flow', str(source), '--include-structured-presentation']), 2)


class SwiftPresentationReviewTests(unittest.TestCase):
    def call(self):
        return recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000)),
            include_error_regions=True, validate_region_entries=True)['calls'][0]

    def test_missing_or_nonmapping_stages_fail_closed(self):
        from airs.swift_error_flow import _presentation_eligibility
        for value in (None, [], 'candidate'):
            call = self.call(); call['error_region'] = value
            self.assertEqual(_presentation_eligibility(call)['status'], 'blocked')
            call = self.call(); call['error_region']['incoming_validation'] = value
            self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')

    def test_integer_completeness_flags_cannot_replace_booleans(self):
        from airs.swift_error_flow import _presentation_eligibility
        for key in ('caller_scan_complete', 'entry_details_complete', 'unclassified_details_complete'):
            call = self.call(); call['error_region']['incoming_validation'][key] = 1
            self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')
        for key in ('call_return_proven', 'join_reachability_proven'):
            call = self.call(); call['error_region'][key] = 0
            self.assertEqual(_presentation_eligibility(call)['status'], 'unresolved')

    def test_opaque_call_targets_retain_explicit_warning_and_raw_evidence(self):
        from airs.swift_error_flow import _presentation_eligibility
        call = self.call(); result = _presentation_eligibility(call)
        self.assertEqual(result['status'], 'eligible_structural_only')
        self.assertTrue(any('opaque' in text for text in result['limitations']))
        instruction = result['display_plan']['error_interval']['instructions'][1]
        self.assertEqual(instruction['word'], '0x94000005')
        self.assertEqual(instruction['semantics'], 'opaque_call')
        self.assertFalse(result['source_reconstruction_allowed'])
