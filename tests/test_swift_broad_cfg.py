"""Manually selected ARM64 words; synthetic geometry, not compiler coverage."""
from dataclasses import replace
import struct
import unittest
from airs.macho import parse_macho
from parser_helpers import build_macho
from airs.swift_error_cfg import SwiftCFGLimits, build_swift_cfg

BASE = 0x100001000
RET = 0xd65f03c0
NOP = 0xd503201f


def image(words, **kwargs):
    return parse_macho(build_macho(struct.pack('<' + 'I' * len(words), *words), **kwargs))


def cfg(words, limits=SwiftCFGLimits()):
    admitted = image(words)
    return build_swift_cfg(admitted, admitted.functions[0], limits=limits)


class SwiftBroadCFGTests(unittest.TestCase):
    def test_straight_line_and_raw_mapping(self):
        admitted = image([NOP, RET])
        result = build_swift_cfg(admitted, admitted.functions[0])
        self.assertEqual(result['status'], 'eligible_structural_only')
        self.assertEqual(len(result['blocks']), 1)
        edge = result['edges'][0]
        self.assertEqual(edge['word'], '0xd65f03c0')
        self.assertEqual(edge['container_offset'], hex(int(edge['slice_offset'], 16)))

    def test_conditional_diamond(self):
        result = cfg([0xb4000060, NOP, 0x14000002, NOP, RET])
        self.assertEqual(result['status'], 'eligible_structural_only')
        self.assertEqual(len(result['blocks'][-1]['predecessors']), 2)

    def test_backward_loop(self):
        result = cfg([NOP, 0xb5ffffe0, RET])
        self.assertEqual(result['status'], 'eligible_structural_only')
        self.assertTrue(any(e['target_pc'] == hex(BASE) for e in result['edges']))

    def test_call_return_candidate(self):
        admitted = image([0x94000002, RET, RET], function_offsets=(0, 8))
        result = build_swift_cfg(admitted, admitted.functions[0])
        self.assertEqual(result['status'], 'eligible_structural_only')
        self.assertFalse(result['call_return_candidates'][0]['runtime_return_proven'])

    def test_cmp_cond_and_test_bit(self):
        for words in ([0xf100001f, 0x54000040, NOP, RET],
                      [0x36000040, NOP, RET], [0xb7000040, NOP, RET],
                      [0x35000040, NOP, RET]):
            with self.subTest(words=words):
                self.assertEqual(cfg(words)['status'], 'eligible_structural_only')

    def test_side_entry_after_return(self):
        result = cfg([0xb4000040, RET, 0x17ffffff])
        self.assertEqual(result['status'], 'eligible_structural_only')
        self.assertEqual(len(result['blocks'][1]['predecessors']), 2)

    def test_unknown_indirect_and_pac_are_unresolved(self):
        for word in (0xffffffff, 0xd63f0000, 0xd503233f):
            result = cfg([word, RET])
            self.assertEqual(result['status'], 'unresolved')
            self.assertTrue(any(e['kind'] == 'unresolved' for e in result['edges']))

    def test_outside_branch_and_fallthrough_block(self):
        for words in ([0x14000008, RET], [NOP]):
            self.assertEqual(cfg(words)['status'], 'blocked')

    def test_truncated_and_unaligned_boundary(self):
        admitted = image([RET])
        for changed in (replace(admitted, data=admitted.data[:1]),
                        replace(admitted, functions=(replace(admitted.functions[0], end=BASE + 3),))):
            self.assertEqual(build_swift_cfg(changed, changed.functions[0])['status'], 'blocked')

    def test_membership_subtype_and_boundary_decline(self):
        admitted = image([RET])
        self.assertEqual(build_swift_cfg(replace(admitted, cpu_subtype=2), admitted.functions[0])['status'], 'declined')
        self.assertEqual(build_swift_cfg(admitted, replace(admitted.functions[0], name='foreign'))['status'], 'blocked')
        changed = replace(admitted.functions[0], boundary_source='symbol_table')
        self.assertEqual(build_swift_cfg(replace(admitted, functions=(changed,)), changed)['status'], 'declined')

    def test_all_resource_limits(self):
        for field in ('max_work', 'max_blocks', 'max_edges', 'max_depth', 'max_retained_words'):
            with self.subTest(field=field):
                result = cfg([0xb4000040, RET, RET], replace(SwiftCFGLimits(), **{field: 0}))
                self.assertEqual(result['status'], 'blocked')
                self.assertIn('limit', result['reason'])

    def test_limit_caps_and_fat_offsets(self):
        with self.assertRaises(ValueError):
            SwiftCFGLimits(max_work=10**12)
        admitted = replace(image([RET]), slice_offset=8192)
        result = build_swift_cfg(admitted, admitted.functions[0])
        edge = result['edges'][0]
        self.assertEqual(int(edge['container_offset'], 16), 8192 + int(edge['slice_offset'], 16))
        self.assertFalse(result['dominance_proven'])


class SwiftBroadCFGBudgetBoundaryTests(unittest.TestCase):
    """Exact-cap and mid-pass assertions use independently counted small graphs."""

    def test_work_exact_cap_and_one_less(self):
        # One member + one section + two decodes + one RET edge + two
        # block-word assignments + one edge assignment + one discovery = 9.
        exact = cfg([NOP, RET], replace(SwiftCFGLimits(), max_work=9))
        self.assertEqual(exact['status'], 'eligible_structural_only')
        self.assertEqual(exact['accounting']['work'], 9)
        less = cfg([NOP, RET], replace(SwiftCFGLimits(), max_work=8))
        self.assertEqual((less['status'], less['reason']), ('blocked', 'work_limit'))
        self.assertEqual(less['accounting'], {'work': 8, 'retained_words': 2,
            'blocks': 1, 'edges': 1, 'max_discovery_depth': 0})
        self.assertFalse(less['completeness']['complete'])

    def test_retained_words_exact_cap_and_preallocation_refusal(self):
        exact = cfg([NOP, RET], replace(SwiftCFGLimits(), max_retained_words=2))
        self.assertEqual(exact['status'], 'eligible_structural_only')
        self.assertEqual(exact['accounting']['retained_words'], 2)
        less = cfg([NOP, RET], replace(SwiftCFGLimits(), max_retained_words=1))
        self.assertEqual((less['status'], less['reason']), ('blocked', 'retained_words_limit'))
        self.assertEqual(less['accounting']['retained_words'], 0)
        self.assertEqual(less['edges'], [])
        self.assertEqual(less['blocks'], [])

    def test_block_and_edge_exact_caps_and_midpass_refusals(self):
        words = [0xb4000040, RET, RET]
        exact = cfg(words, replace(SwiftCFGLimits(), max_blocks=3, max_edges=4))
        self.assertEqual(exact['status'], 'eligible_structural_only')
        self.assertEqual((exact['accounting']['blocks'], exact['accounting']['edges']), (3, 4))
        blocks = cfg(words, replace(SwiftCFGLimits(), max_blocks=2))
        self.assertEqual((blocks['status'], blocks['reason']), ('blocked', 'blocks_limit'))
        self.assertEqual(blocks['accounting']['retained_words'], 1)
        self.assertEqual(blocks['accounting']['edges'], 2)
        self.assertEqual(blocks['accounting']['blocks'], 0)
        edges = cfg(words, replace(SwiftCFGLimits(), max_edges=3))
        self.assertEqual((edges['status'], edges['reason']), ('blocked', 'edges_limit'))
        self.assertEqual(edges['accounting']['retained_words'], 3)
        self.assertEqual(edges['accounting']['edges'], len(edges['edges']))
        self.assertEqual(len(edges['edges']), 3)
        self.assertEqual(edges['accounting']['blocks'], 0)
        self.assertFalse(edges['completeness']['complete'])

    def test_nonzero_work_exhaustion_during_edge_emission(self):
        # Member + section + CBZ decode + its two edges + first RET decode.
        result = cfg([0xb4000040, RET, RET], replace(SwiftCFGLimits(), max_work=6))
        self.assertEqual((result['status'], result['reason']), ('blocked', 'work_limit'))
        self.assertEqual(result['accounting'], {'work': 6, 'retained_words': 2,
            'blocks': 0, 'edges': 2, 'max_discovery_depth': 0})
        self.assertEqual(len(result['edges']), 2)
        self.assertEqual(result['returns'], [])
        self.assertFalse(result['completeness']['complete'])

    def test_depth_exact_cap_and_midpass_refusal(self):
        words = [0x14000001, 0x14000001, RET]
        exact = cfg(words, replace(SwiftCFGLimits(), max_depth=3))
        self.assertEqual(exact['status'], 'eligible_structural_only')
        self.assertEqual(exact['accounting']['max_discovery_depth'], 3)
        less = cfg(words, replace(SwiftCFGLimits(), max_depth=2))
        self.assertEqual((less['status'], less['reason']), ('blocked', 'depth_limit'))
        self.assertEqual(less['accounting']['max_discovery_depth'], 2)
        self.assertEqual((less['accounting']['blocks'], less['accounting']['edges']), (3, 3))
        self.assertFalse(less['completeness']['complete'])


class SwiftBroadCFGExceptionTransferTests(unittest.TestCase):
    def test_brk_tail_exact_provenance_and_unknown_resumption(self):
        result=cfg([0xd4200020])  # BRK #1
        self.assertEqual(result['status'],'eligible_structural_only',result)
        self.assertEqual(result['returns'],[])
        transfer=result['exception_transfers'][0]
        self.assertEqual(transfer['word'],'0xd4200020')
        self.assertEqual(transfer['pc'],hex(BASE))
        self.assertEqual(transfer['kind'],'brk')
        self.assertEqual(transfer['exception'],'breakpoint')
        self.assertFalse(transfer['resume_proven'])
        self.assertTrue(result['external_exception_handling_unmodeled'])
        self.assertFalse(result['exception_resume_proven'])
        self.assertEqual([(e['kind'],e['target_pc']) for e in result['edges']],
                         [('exception_transfer',None)])

    def test_middle_brk_retains_lexical_code_without_normal_continuation(self):
        result=cfg([0xd4200000,NOP,RET])
        self.assertEqual(result['status'],'eligible_structural_only',result)
        self.assertEqual(len(result['blocks']),2)
        self.assertEqual(result['blocks'][1]['start_pc'],hex(BASE+4))
        self.assertEqual(result['blocks'][1]['predecessors'],[])
        self.assertTrue(result['completeness']['all_words_classified'])
        self.assertEqual(result['accounting']['retained_words'],3)
        unknown=cfg([0xd4200000,0xffffffff,RET])
        self.assertEqual(unknown['status'],'unresolved')
        self.assertFalse(unknown['completeness']['all_words_classified'])

    def test_brk_edge_and_work_budgets_refuse_incomplete(self):
        for limits,reason in ((replace(SwiftCFGLimits(),max_edges=0),'edges_limit'),
                              (replace(SwiftCFGLimits(),max_work=3),'work_limit'),
                              (replace(SwiftCFGLimits(),max_blocks=1),'blocks_limit')):
            result=cfg([0xd4200000,RET],limits)
            self.assertEqual(result['status'],'blocked',result)
            self.assertEqual(result['reason'],reason)
            self.assertFalse(result['completeness']['complete'])

