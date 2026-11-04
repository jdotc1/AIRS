"""CMP/B.NE forward handler regions are structural evidence only."""
import unittest
from test_swift_error_flow import image, BASE
from airs.swift_error_flow import recover_swift_error_flow

# BL, CMP x21,#0, B.NE -> error +20; success branches over error to RET.
WORDS = (0xf10002bf, 0x54000061, 0xd2800000, 0x14000003,
         0xaa1503e0, 0x92800000, 0xd65f03c0)


def report(words=WORDS, **kwargs):
    return recover_swift_error_flow(image(words), include_error_regions=True,
        validate_region_entries=True, include_structured_presentation=True, **kwargs)


class CmpNeHandlerFirstTests(unittest.TestCase):
    def test_forward_region_and_presentation_remain_structural(self):
        call = report()['calls'][0]
        region = call['error_region']
        self.assertEqual(region['status'], 'structural_region_candidate')
        self.assertEqual(region['start_pc'], hex(BASE + 20))
        self.assertEqual(region['incoming_validation']['status'], 'no_unexpected_direct_entries')
        self.assertFalse(region['call_return_proven'])
        self.assertFalse(region['shared_epilogue']['restore_state_proven'])
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')


class CmpNeHandlerBoundaryTests(unittest.TestCase):
    def test_entry_to_flag_window_or_unknown_caller_blocks_region(self):
        for word in (0x17fffff9, 0x17fffffa, 0xffffffff):
            call = report((*WORDS, word))['calls'][0]
            self.assertEqual(call['error_region']['status'], 'declined')
            self.assertNotEqual(call['presentation']['status'], 'eligible_structural_only')

    def test_partial_caller_and_missing_flag_screen_decline(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        call = report(limits=replace(DEFAULT_LIMITS, max_instructions_per_function=7))['calls'][0]
        self.assertEqual(call['error_region']['reason'], 'compare_flag_entries_not_clear')
        call = recover_swift_error_flow(image(WORDS), include_error_regions=True)['calls'][0]
        self.assertEqual(call['error_region']['reason'], 'compare_flag_entries_required')

    def test_side_entries_into_each_interval_are_conflicts(self):
        for target in (12, 16, 20, 24, 28):
            branch = 0x14000000 | (((target - 32) // 4) & 0x3ffffff)
            call = report((*WORDS, branch))['calls'][0]
            self.assertEqual(call['error_region']['incoming_validation']['status'], 'unexpected_direct_entries')
            self.assertNotEqual(call['presentation']['status'], 'eligible_structural_only')

    def test_unsupported_success_error_and_tail_words_decline(self):
        for index, word in ((2, 0x94000010), (3, 0xd503201f), (4, 0x14000001), (6, 0xd65f0000)):
            words = list(WORDS); words[index] = word
            self.assertEqual(report(tuple(words))['calls'][0]['error_region']['status'], 'declined')

    def test_stale_comparison_branch_and_geometry_are_refused(self):
        import struct
        from copy import deepcopy
        from airs.swift_error_flow import _error_region
        value = image(WORDS); function = value.functions[0]
        original = report()['calls'][0]
        raw = value.bytes_at(function.start, function.size)
        for offset, word in ((4, 0xf100029f), (8, 0x54000060), (8, 0x54000081)):
            data = bytearray(raw); struct.pack_into('<I', data, offset, word)
            self.assertEqual(_error_region(bytes(data), function, original)['status'], 'declined')
        for key, altered in (('success_pc', hex(BASE+16)), ('error_pc', hex(BASE+24)),
                             ('test_condition', 'eq'), ('tested_register', 'x20')):
            call = deepcopy(original); call[key] = altered
            self.assertEqual(_error_region(raw, function, call)['status'], 'declined')

    def test_expected_branch_exemption_requires_exact_recorded_and_encoded_ne(self):
        from copy import deepcopy
        from airs.swift_error_flow import _caller_direct_edges, _region_incoming
        value = image(WORDS); function = value.functions[0]
        call = report()['calls'][0]; region = call['error_region']
        raw = value.bytes_at(function.start, function.size)
        scan = _caller_direct_edges(raw, function)
        for mutation in ('recorded_word', 'edge_word', 'edge_kind', 'target', 'condition'):
            altered = deepcopy(call); edges = deepcopy(scan)
            branch = next(row for row in edges['direct_edges'] if row['source_pc'] == hex(BASE+8))
            if mutation == 'recorded_word': altered['window'][-1]['word'] = '0x54000060'
            if mutation == 'edge_word': branch['word'] = '0x54000060'
            if mutation == 'edge_kind': branch['kind'] = 'b'
            if mutation == 'target': branch['target_pc'] = hex(BASE+24)
            if mutation == 'condition': altered['test_condition'] = 'eq'
            self.assertEqual(_region_incoming(edges, region, altered)['status'], 'unexpected_direct_entries')

    def test_error_and_success_word_bounds(self):
        for count in (8, 9):
            error = 12 + 4 * count; join = error + 4
            words = (0xf10002bf, 0x54000001 | (((error-8)//4) << 5),
                     *((0xd503201f,) * (count-1)), 0x14000000 | ((join-(error-4))//4),
                     0x92800000, 0xd65f03c0)
            self.assertEqual(report(words)['calls'][0]['error_region']['status'],
                             'structural_region_candidate' if count == 8 else 'declined')
