"""Owned shared-return words are inspected as data, never executed."""
import unittest
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image, BASE

# Test/error arm, jump over success result, SP restores/add and RET x30.
WORDS = (0xb40000b5, 0xaa1503e0, 0x94000010, 0x92800000,
         0x14000002, 0xd2800000, 0xa9427bfd, 0xa94157f6,
         0x9100c3ff, 0xd65f03c0)


def report(words=WORDS, **kwargs):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True, **kwargs)


class SharedEpilogueFirstTests(unittest.TestCase):
    def test_distinct_success_entry_and_common_restore_tail(self):
        value = report(); call = value['calls'][0]; region = call['error_region']
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['end_pc_exclusive'], hex(BASE + 24))
        self.assertEqual(region['join_pc'], hex(BASE + 28))
        self.assertEqual(region['success_interval']['start_pc'], hex(BASE + 24))
        self.assertEqual(region['shared_epilogue']['start_pc'], hex(BASE + 28))
        self.assertEqual(region['incoming_validation']['status'], 'no_unexpected_direct_entries')
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertFalse(region['join_reachability_proven'])
        self.assertFalse(call['presentation']['source_reconstruction_allowed'])

class SharedEpilogueBoundaryTests(unittest.TestCase):
    def test_success_arm_control_flow_and_unknown_refuse(self):
        for word in (0x14000001, 0x94000010, 0xb4000035, 0xd65f03c0, 0xffffffff):
            words = list(WORDS); words[5] = word
            self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')

    def test_tail_calls_arithmetic_wrong_base_and_writeback_refuse(self):
        for word in (0x94000010, 0x14000001, 0xd100c3ff, 0x9100c000,
                     0xa9427bbd, 0xa8c27bfd, 0xd65f0000, 0xffffffff):
            words = list(WORDS); words[6] = word
            self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')

    def test_absent_return_and_scanned_prefix_refuse(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        words = list(WORDS); words[9] = 0xffffffff
        self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')
        value = report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=9))
        self.assertEqual(value['calls'][0]['error_region']['status'], 'declined')
        self.assertFalse(value['word_scan_complete'])

    def test_external_edges_into_each_arm_or_tail_block(self):
        for target in (8, 24, 28, 32, 40):
            source = 44
            branch = 0x14000000 | (((target - source) // 4) & 0x3ffffff)
            call = report(WORDS + (branch,))['calls'][0]
            self.assertEqual(call['error_region']['incoming_validation']['unexpected_entry_count'], 1)
            self.assertEqual(call['presentation']['status'], 'blocked')

    def test_opaque_error_call_into_success_or_tail_blocks(self):
        for target in (24, 28, 32, 40):
            words = list(WORDS); words[2] = 0x94000000 | (((target - 12) // 4) & 0x3ffffff)
            call = report(tuple(words))['calls'][0]
            self.assertEqual(call['error_region']['incoming_validation']['status'], 'unexpected_direct_entries')
            self.assertEqual(call['presentation']['status'], 'blocked')

    def test_unclassified_caller_word_withholds_presentation(self):
        call = report(WORDS + (0xffffffff,))['calls'][0]
        self.assertEqual(call['error_region']['status'], 'structural_region_candidate')
        self.assertEqual(call['presentation']['status'], 'unresolved')

    def test_success_arm_exact_budget_and_one_word_over(self):
        for count in (8, 9):
            words = list(WORDS[:5]) + [0xd503201f] * count + list(WORDS[6:])
            words[4] = 0x14000000 | (count + 1)
            call = report(tuple(words))['calls'][0]
            self.assertEqual(call['error_region']['status'], 'structural_region_candidate' if count == 8 else 'declined')

    def test_tail_exact_budget_and_one_word_over(self):
        for count in (8, 9):
            words = WORDS[:6] + (0xd503201f,) * (count - 1) + (0xd65f03c0,)
            self.assertEqual(report(words)['calls'][0]['error_region']['status'],
                             'structural_region_candidate' if count == 8 else 'declined')

    def test_presentation_endpoint_tampering_refuses(self):
        import copy
        from airs.swift_error_flow import _presentation_eligibility
        call = report()['calls'][0]
        for field in ('success_interval', 'shared_epilogue'):
            altered = copy.deepcopy(call)
            altered['error_region'][field]['start_pc'] = hex(BASE + 4)
            self.assertEqual(_presentation_eligibility(altered)['reason'], 'presentation_evidence_inconsistent')
        altered = copy.deepcopy(call); altered['error_region']['join_pc'] = hex(BASE + 32)
        self.assertEqual(_presentation_eligibility(altered)['reason'], 'presentation_evidence_inconsistent')

    def test_display_plan_copy_and_text_retain_distinct_intervals(self):
        from airs.swift_error_text import render_swift_error_text
        value = report(); call = value['calls'][0]
        text = render_swift_error_text(value)
        self.assertIn('Shared restore/return candidate (state unproven)', text)
        self.assertIn('Source reconstruction: disabled', text)
        call['presentation']['display_plan']['shared_epilogue']['instructions'][0]['word'] = 'changed'
        self.assertEqual(call['error_region']['shared_epilogue']['instructions'][0]['word'], '0xa9427bfd')

    def test_new_component_versions_leave_edge_identity_and_default_unchanged(self):
        value = report()
        self.assertEqual(value['model_version'], 'swift-sync-error-edges-v5')
        self.assertEqual(value['error_region_model_version'], 'swift-sync-error-region-v12')
        self.assertEqual(value['region_incoming_model_version'], 'swift-region-direct-entries-v5')
        self.assertEqual(value['structured_presentation_model_version'], 'swift-structural-presentation-v3')
        default = recover_swift_error_flow(image(WORDS))
        self.assertNotIn('error_region', default['calls'][0])
        self.assertNotIn('presentation', default['calls'][0])


class SharedEpilogueEvidenceTests(unittest.TestCase):
    def test_blocked_and_unresolved_text_retain_shared_evidence(self):
        from airs.swift_error_text import render_swift_error_text
        for extra in ((0xffffffff,), (0x17fffffd,)):
            text = render_swift_error_text(report(WORDS + extra))
            self.assertIn('Shared tail instruction', text)
            self.assertIn('Success-arm instruction', text)
            self.assertIn('0xa9427bfd', text)
            self.assertIn('Structured plan: withheld', text)


class SharedEpilogueEntryBindingTests(unittest.TestCase):
    def test_expected_success_entry_exemption_requires_kind_and_source(self):
        from airs.swift_error_flow import _region_incoming
        # Direct scan evidence is bounded and owned; isolate only exemption binding.
        call = report()['calls'][0]; region = call['error_region']
        base = {'caller_scan_complete': True, 'scanned_word_count': 16,
                'unclassified_word_count': 0, 'unclassified_words': []}
        edge = {'source_pc': call['test_pc'], 'target_pc': call['success_pc'],
                'kind': 'xcbz', 'word': '0xb40000b5'}
        self.assertEqual(_region_incoming({**base, 'direct_edges': [edge]}, region, call)['unexpected_entry_count'], 0)
        for mutated in ({**edge, 'kind': 'b'}, {**edge, 'source_pc': hex(BASE)},
                        {**edge, 'target_pc': hex(BASE + 28)}):
            self.assertEqual(_region_incoming({**base, 'direct_edges': [mutated]}, region, call)['unexpected_entry_count'], 1)


if __name__ == '__main__':
    unittest.main()
