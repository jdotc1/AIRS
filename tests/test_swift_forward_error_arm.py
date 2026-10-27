"""Bounded success-fallthrough / forward error arm; owned words only."""
import unittest
from test_swift_error_flow import image, BASE
from airs.swift_error_flow import recover_swift_error_flow

WORDS = (0xb5000075, 0xd2800000, 0x14000004, 0xaa1503e0, 0x94000010,
         0x92800000, 0xa9427bfd, 0xa94157f6, 0x9100c3ff, 0xd65f03c0)


def report(words=WORDS, **kwargs):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True, **kwargs)


class ForwardErrorFirstTests(unittest.TestCase):
    def test_success_falls_through_and_error_branches_forward(self):
        call = report()['calls'][0]; region = call['error_region']
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['layout'], 'success_fallthrough_error_forward')
        self.assertEqual((region['start_pc'], region['end_pc_exclusive']), (hex(BASE + 16), hex(BASE + 28)))
        self.assertEqual((region['success_interval']['start_pc'], region['success_interval']['end_pc_exclusive']),
                         (hex(BASE + 8), hex(BASE + 16)))
        self.assertEqual(region['join_pc'], hex(BASE + 28))
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertFalse(region['shared_epilogue']['restore_state_proven'])
        self.assertFalse(call['presentation']['source_reconstruction_allowed'])

class ForwardErrorBoundaryTests(unittest.TestCase):
    def test_success_only_branch_is_a_valid_minimal_arm(self):
        words = (0xb5000055, 0x14000004, 0xaa1503e0, 0x94000010, 0x92800000, *WORDS[6:])
        call = report(words)['calls'][0]
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(len(call['error_region']['success_interval']['instructions']), 1)

    def test_success_must_end_with_one_terminal_direct_branch(self):
        for word in (0xd503201f, 0x94000004, 0xb4000080, 0xd61f0000, 0xd65f03c0):
            words = list(WORDS); words[2] = word
            self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')
        for word in (0x14000005, 0x94000010, 0xffffffff):
            words = list(WORDS); words[1] = word
            self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')

    def test_join_must_be_forward_nonoverlapping_and_inside_caller(self):
        for target in (8, 12, 16, 64, 4096):
            words = list(WORDS); words[2] = 0x14000000 | (((target - 12) // 4) & 0x3ffffff)
            self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')

    def test_error_arm_branches_returns_and_unknowns_decline(self):
        for word in (0x14000003, 0xb4000060, 0xd61f0000, 0xd65f03c0, 0xffffffff):
            words = list(WORDS); words[3] = word
            self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')

    def test_bounded_success_arm_exact_limit_and_one_over(self):
        for count in (8, 9):
            error = 8 + count * 4; join = error + 4
            branch = 0x14000000 | ((join - (error - 4)) // 4)
            test = 0xb5000015 | (((error - 4) // 4) << 5)
            words = (test, *((0xd503201f,) * (count - 1)), branch, 0x92800000, 0xd65f03c0)
            call = report(words)['calls'][0]
            self.assertEqual(call['error_region']['status'], 'structural_region_candidate' if count == 8 else 'declined')

    def test_bounded_error_arm_exact_limit_and_one_over(self):
        for count in (16, 17):
            join = 12 + count * 4
            words = (0xb5000055, 0x14000000 | ((join - 8) // 4),
                     *((0xd503201f,) * count), 0xd65f03c0)
            self.assertEqual(report(words)['calls'][0]['error_region']['status'],
                             'structural_region_candidate' if count == 16 else 'declined')

    def test_prefix_cannot_invent_error_or_tail_words(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for limit in (3, 5, 7):
            call = report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=limit))['calls'][0]
            self.assertEqual(call['error_region']['status'], 'declined')
        call = report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=11))['calls'][0]
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertEqual(call['presentation']['status'], 'unresolved')

    def test_other_direct_entries_into_each_arm_and_tail_block(self):
        for target in (8, 12, 16, 20, 28, 32, 40):
            branch = 0x14000000 | (((target - 44) // 4) & 0x3ffffff)
            call = report(WORDS + (branch,))['calls'][0]
            self.assertEqual(call['error_region']['incoming_validation']['unexpected_entry_count'], 1)
            self.assertEqual(call['presentation']['status'], 'blocked')

    def test_opaque_error_calls_into_success_and_tail_block(self):
        for target in (8, 12, 28, 32, 40):
            words = list(WORDS); words[4] = 0x94000000 | (((target - 20) // 4) & 0x3ffffff)
            self.assertEqual(report(tuple(words))['calls'][0]['presentation']['status'], 'blocked')

    def test_test_and_exit_exemptions_require_exact_kind_source_target(self):
        from airs.swift_error_flow import _region_incoming
        call = report()['calls'][0]; region = call['error_region']
        scan = {'caller_scan_complete': True, 'scanned_word_count': 16,
                'unclassified_word_count': 0, 'unclassified_words': []}
        test = {'source_pc': call['test_pc'], 'target_pc': call['error_pc'], 'kind': 'xcbnz', 'word': '0xb5000075'}
        exit_edge = {'source_pc': hex(BASE + 12), 'target_pc': hex(BASE + 28), 'kind': 'b', 'word': '0x14000004'}
        for edge in (test, exit_edge):
            self.assertEqual(_region_incoming({**scan, 'direct_edges': [edge]}, region, call)['unexpected_entry_count'], 0)
            for mutated in ({**edge, 'kind': 'bl'}, {**edge, 'source_pc': hex(BASE)},
                            {**edge, 'target_pc': hex(BASE + 32)}):
                self.assertEqual(_region_incoming({**scan, 'direct_edges': [mutated]}, region, call)['unexpected_entry_count'], 1)

    def test_forward_presentation_binds_all_bounds_and_copies_evidence(self):
        import copy
        from airs.swift_error_flow import _presentation_eligibility
        call = report()['calls'][0]
        for field in ('start_pc', 'end_pc_exclusive', 'join_pc'):
            altered = copy.deepcopy(call); altered['error_region'][field] = hex(BASE + 24)
            self.assertEqual(_presentation_eligibility(altered)['reason'], 'presentation_evidence_inconsistent')
        altered = copy.deepcopy(call); del altered['error_region']['shared_epilogue']
        self.assertEqual(_presentation_eligibility(altered)['reason'], 'presentation_evidence_inconsistent')
        call['presentation']['display_plan']['success_interval']['instructions'][0]['word'] = 'changed'
        self.assertEqual(call['error_region']['success_interval']['instructions'][0]['word'], '0xd2800000')

    def test_blocked_and_unresolved_text_keeps_distinct_arm_evidence(self):
        from airs.swift_error_text import render_swift_error_text
        for extra in ((0xffffffff,), (0x17fffffd,)):
            text = render_swift_error_text(report(WORDS + extra))
            for label in ('Structured plan: withheld', 'Success-arm interval evidence', 'Shared tail interval evidence',
                          'Region evidence', '0xb5000075', 'Source reconstruction: disabled'):
                self.assertIn(label, text)


class ForwardErrorCLIControls(unittest.TestCase):
    def test_synthetic_cli_displays_forward_error_interval(self):
        import contextlib
        import io
        from pathlib import Path
        from airs.cli import main
        from fixture_storage import temporary_directory
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'owned-forward-error.macho'
            source.write_bytes(image(WORDS).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation', '--format', 'text'])
            self.assertEqual(status, 0)
            for value in ('swift-sync-error-region-v7', 'swift-region-direct-entries-v4',
                          'swift-structural-presentation-v3', '0xb5000075', '0x14000004',
                          'Success-arm interval evidence', 'Shared tail interval evidence', 'Source reconstruction: disabled'):
                self.assertIn(value, output.getvalue())


class ForwardErrorDeclineEvidenceTests(unittest.TestCase):
    def test_declined_success_words_remain_visible_with_completeness(self):
        from airs.swift_error_text import render_swift_error_text
        for index, word, complete in ((2, 0xd503201f, True), (1, 0xffffffff, False)):
            words = list(WORDS); words[index] = word
            value = report(tuple(words)); region = value['calls'][0]['error_region']
            self.assertEqual(region['status'], 'declined')
            evidence = region['success_interval']
            self.assertEqual(evidence['instructions_complete'], complete)
            self.assertIn(f'0x{word:08x}', [row['word'] for row in evidence['instructions']])
            self.assertIn('Success-arm interval evidence', render_swift_error_text(value))

    def test_out_of_vm_branch_targets_are_not_published_as_vm_addresses(self):
        import struct
        from types import SimpleNamespace
        from airs.swift_error_flow import _forward_error_region
        for base, branch in ((0, 0x17fffffc), ((1 << 64) - 44, 0x14000010)):
            words = [0x94000010, *WORDS]; words[3] = branch
            edge = {'error_pc': hex(base + 16), 'success_pc': hex(base + 8), 'test_pc': hex(base + 4)}
            region = _forward_error_region(struct.pack('<11I', *words), SimpleNamespace(start=base, end=base + 44), edge)
            self.assertEqual(region['status'], 'declined')
            last = region['success_interval']['instructions'][-1]
            self.assertNotIn('target_pc', last)
            self.assertEqual(last['target_reason'], 'outside_vm_address_space')


class ForwardErrorCompletenessTests(unittest.TestCase):
    def test_partial_success_prefix_is_distinct_from_complete_eligible_evidence(self):
        import copy
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS, _presentation_eligibility
        partial = report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=3))['calls'][0]
        self.assertEqual(partial['error_region']['status'], 'declined')
        self.assertFalse(partial['error_region']['success_interval']['instructions_complete'])
        self.assertEqual(len(partial['error_region']['success_interval']['instructions']), 1)
        call = report()['calls'][0]
        self.assertTrue(call['error_region']['success_interval']['instructions_complete'])
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        altered = copy.deepcopy(call); altered['error_region']['success_interval']['instructions_complete'] = False
        self.assertEqual(_presentation_eligibility(altered)['reason'], 'presentation_evidence_inconsistent')


if __name__ == '__main__':
    unittest.main()
