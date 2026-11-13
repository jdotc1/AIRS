"""Owned synthetic tests for airs.swift_indirect_target_shape (swift-indirect-target-shape-v1).

Every instruction word below is encoded by hand from the Arm Architecture Reference Manual
(helpers at the top); no production decoder is used to build inputs, and no image or word is
ever executed. The owned fixture tests read the committed fixture with the existing Mach-O
reader and check the four value-witness sites that the register census recorded.
"""
import json
import random
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shape_word_helpers import (  # noqa: E402
    BASE, CNTD_X8, ADD_X8_X9_X10, LDXP_X8_X9_X0, MRS_TPIDR_X8, SUB_SP_SP_X9, Fn, add_imm, b, bcond, blr, blraaz,
    braaz, br, cbz, ldp, ldr, ldr_w, ldur, mov, movz, nop, ret, str_, stp, sub_imm)
from airs.macho import parse_macho
from airs.swift_broad_flow import IMPORTS_BROAD_LIMITS
from airs.swift_indirect_target_shape import (
    CLASSES, MAX_FUNCTION_WORDS, MODEL, VALUE_WITNESS_FUNCTION_SLOTS, WINDOW_WORDS,
    classify_indirect_target)
from airs.types import Section

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'swift-error-flow' / 'broad-imports'


def classify(fn, site=None, **kw):
    record = classify_indirect_target(list(fn.w), fn.start, fn.site if site is None else site, **kw)
    assert record['claims_callee_behaviour'] is False
    assert record['model'] == MODEL and record['class'] in CLASSES
    for d in record['deciding_instructions']:
        assert fn.w[(d['pc'] - fn.start) // 4] == d['word']
    return record


def value_witness(off=8, copy=None, call=blr, accessor=0x100000800):
    f = Fn().bl(accessor)
    meta = 0
    if copy == 'mov':
        f.add(mov(22, 0))
        meta = 22
    elif copy == 'add0':
        f.add(add_imm(22, 0, 0))
        meta = 22
    return f.add(ldur(8, meta, -8), ldr(8, 8, off), call(8))


class ValueWitnessTests(unittest.TestCase):
    def test_function_slot_boundaries(self):
        for off in (0x0, 0x8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x58, 0x60, 0x68):
            with self.subTest(off=off):
                r = classify(value_witness(off))
                self.assertEqual((r['class'], r['slot_offset'], r['unknown_reason']), ('value_witness', off, None))
        self.assertEqual(sorted(VALUE_WITNESS_FUNCTION_SLOTS),
                         [0x0, 0x8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x58, 0x60, 0x68])

    def test_data_field_and_out_of_table_offsets_are_unknown(self):
        for off in (0x40, 0x48, 0x50, 0x70, 0x78, 0x80, 0x100):
            with self.subTest(off=off):
                r = classify(value_witness(off))
                self.assertEqual((r['class'], r['slot_offset'], r['unknown_reason']),
                                 ('unknown', off, 'value_witness_offset_not_function_slot'))

    def test_deciding_instructions_and_roles(self):
        f = value_witness(0x10)
        r = classify(f)
        self.assertEqual([(d['pc'], d['role']) for d in r['deciding_instructions']],
                         [(f.at(0), 'metadata_call_result'), (f.at(1), 'table_load'),
                          (f.at(2), 'target_load'), (f.at(3), 'indirect_branch')])
        self.assertEqual(r['deciding_instructions'][1]['word'], ldur(8, 0, -8))
        self.assertEqual(r['site_kind'], 'blr')
        self.assertIn('slot +0x10', r['evidence'])

    def test_br_site_and_register_copies(self):
        self.assertEqual(classify(value_witness(8, call=br))['site_kind'], 'br')
        self.assertEqual(classify(value_witness(8, call=br))['class'], 'value_witness')
        for copy in ('mov', 'add0'):
            with self.subTest(copy=copy):
                r = classify(value_witness(8, copy=copy))
                self.assertEqual(r['class'], 'value_witness')
                self.assertIn('metadata_copy', [d['role'] for d in r['deciding_instructions']])

    def test_target_copy_and_metadata_register_nonzero(self):
        f = Fn().bl(0x100000800).add(ldur(9, 0, -8), ldr(10, 9, 0x18), mov(8, 10), blr(8))
        self.assertEqual(classify(f)['class'], 'value_witness')

    def test_pair_load_from_table(self):
        f = Fn().bl(0x100000800).add(ldur(9, 0, -8), ldp(10, 8, 9, 0x10), blr(8))
        r = classify(f)
        self.assertEqual((r['class'], r['slot_offset']), ('value_witness', 0x18))


class OtherClassTests(unittest.TestCase):
    def test_protocol_witness_slot(self):
        r = classify(Fn().add(ldr(8, 1, 0x18), blr(8)))
        self.assertEqual((r['class'], r['slot_offset']), ('protocol_witness_slot', 0x18))
        r = classify(Fn().add(ldr(8, 9, 0x10), mov(2, 9), blr(8)))
        self.assertEqual(r['class'], 'protocol_witness_slot')
        # 8 <= offset < 0x50
        self.assertEqual(classify(Fn().add(ldr(8, 1, 0x8), blr(8)))['class'], 'protocol_witness_slot')
        self.assertEqual(classify(Fn().add(ldr(8, 1, 0x48), blr(8)))['class'], 'protocol_witness_slot')
        for off in (0x0, 0x50):
            r = classify(Fn().add(ldr(8, 1, off), blr(8)))
            self.assertEqual((r['class'], r['unknown_reason']), ('unknown', 'base_entry_register_x1'))

    def test_protocol_witness_needs_the_table_still_in_an_argument_register(self):
        r = classify(Fn().add(ldr(8, 1, 0x18), movz(1, 0), blr(8)))
        self.assertEqual(r['class'], 'unknown')

    def test_class_vtable(self):
        r = classify(Fn().add(ldr(9, 0, 0), ldr(8, 9, 0x50), blr(8)))
        self.assertEqual((r['class'], r['slot_offset']), ('class_vtable', 0x50))
        self.assertEqual(classify(Fn().add(ldr(9, 0, 0), ldr(8, 9, 0x68), br(8)))['class'], 'class_vtable')
        r = classify(Fn().add(ldr(9, 0, 0), ldr(8, 9, 0x48), blr(8)))
        self.assertEqual((r['class'], r['unknown_reason']), ('unknown', 'base_loaded_from_memory'))

    def test_got_or_global_fnptr_with_slot_and_section(self):
        f = Fn().adrp(8, 0x100004000).add(ldr(8, 8, 0x10), blr(8))
        r = classify(f)
        self.assertEqual((r['class'], r['slot_address'], r['slot_section']),
                         ('got_or_global_fnptr', 0x100004010, 'unmapped'))
        sections = [Section('__DATA_CONST', '__got', 0x100004000, 0x100, 0x4000)]
        self.assertEqual(classify(f, sections=sections)['slot_section'], '__DATA_CONST,__got')
        as_dicts = [dict(segment='__DATA_CONST', name='__got', address=0x100004000, size=0x100)]
        self.assertEqual(classify(f, sections=as_dicts)['slot_section'], '__DATA_CONST,__got')
        self.assertEqual(classify(f, sections=[object(), 3])['slot_section'], 'unmapped')
        g = Fn().adrp(9, 0x100004000).add(add_imm(9, 9, 0x20), ldr(8, 9, 8), blr(8))
        self.assertEqual(classify(g)['slot_address'], 0x100004028)
        h = Fn()
        h.literal(9, BASE + 0x100)
        h.add(ldr(8, 9, 8), blr(8))
        r = classify(h)
        self.assertEqual((r['class'], r['slot_address']), ('got_or_global_fnptr', None))

    def test_closure_context(self):
        r = classify(Fn().add(ldr(8, 9, 0x10), ldr(20, 9, 0x18), blr(8)))
        self.assertEqual((r['class'], r['slot_offset']), ('closure_context', 0x10))
        self.assertIn('closure_context_load', [d['role'] for d in r['deciding_instructions']])
        self.assertEqual(classify(Fn().add(ldp(8, 20, 9, 0x10), blr(8)))['class'], 'closure_context')
        self.assertEqual(classify(Fn().add(ldp(20, 8, 9, 0x10), blr(8)))['class'], 'closure_context')
        # the context register is rewritten before the call: not a closure pair
        r = classify(Fn().add(ldr(8, 9, 0x10), ldr(20, 9, 0x18), movz(20, 0), blr(8)))
        self.assertNotEqual(r['class'], 'closure_context')

    def test_static_address(self):
        r = classify(Fn().adrp(8, 0x100002000).add(add_imm(8, 8, 0x10), blr(8)))
        self.assertEqual(r['class'], 'static_address')
        self.assertEqual(classify(Fn().adrp(8, 0x100002000).add(blr(8)))['class'], 'static_address')
        self.assertEqual(classify(Fn().adr(8, BASE + 0x40).add(br(8)))['class'], 'static_address')
        f = Fn()
        f.literal(8, BASE + 0x80)
        self.assertEqual(classify(f.add(blr(8)))['class'], 'static_address')

    def test_runtime_or_objc_ptr(self):
        for reg in (0, 1, 2, 3):
            with self.subTest(reg=reg):
                r = classify(Fn().bl(0x100000900).add(blr(reg)))
                self.assertEqual(r['class'], 'runtime_or_objc_ptr')
        r = classify(Fn().bl(0x100000900).add(mov(8, 1), blr(8)))
        self.assertEqual(r['class'], 'runtime_or_objc_ptr')
        self.assertIn('returned by bl', r['evidence'])

    def test_first_match_order(self):
        # a [Xm,#-8] base wins over a protocol-witness reading of the same table
        f = Fn().add(ldur(9, 1, -8), ldr(8, 9, 0x10), mov(2, 9), blr(8))
        self.assertEqual(classify(f)['class'], 'value_witness')
        # a context pair next to a witness-table argument is a closure
        f = Fn().add(ldr(8, 1, 0x10), ldr(20, 1, 0x18), blr(8))
        self.assertEqual(classify(f)['class'], 'closure_context')

    def test_slot_offset_of_pair_and_writeback_forms(self):
        self.assertEqual(classify(Fn().add(ldp(8, 9, 0, 0x10, mode=3), blr(8)))['slot_offset'], 0x10)
        self.assertEqual(classify(Fn().add(ldp(8, 9, 0, 0x10, mode=1), blr(8)))['slot_offset'], 0)
        self.assertEqual(classify(Fn().add(ldp(10, 8, 0, 0x10), mov(8, 8), blr(8)))['slot_offset'], 0x18)


class UnknownReasonTests(unittest.TestCase):
    def reason(self, fn, site=None, **kw):
        r = classify(fn, site, **kw)
        self.assertEqual(r['class'], 'unknown')
        self.assertFalse(r['claims_callee_behaviour'])
        return r['unknown_reason']

    def test_register_and_flow_reasons(self):
        self.assertEqual(self.reason(Fn().add(blr(1))), 'target_is_entry_register_x1')
        self.assertEqual(self.reason(Fn().add(blr(31))), 'sp_or_zero_register')
        self.assertEqual(self.reason(Fn().bl(0x100000900).add(blr(30))), 'link_register')
        self.assertEqual(self.reason(Fn().bl(0x100000900).add(blr(8))), 'clobbered_by_call')
        f = Fn()
        f.add(b(f.pc, f.pc + 4), blr(8))
        self.assertEqual(self.reason(f), 'flow_break_before_def')
        self.assertEqual(self.reason(Fn().add(blr(8))), 'undefined_at_entry')
        self.assertEqual(self.reason(Fn().add(movz(8, 1), blr(8))), 'target_const')
        self.assertEqual(self.reason(Fn().add(add_imm(8, 31, 16), blr(8))), 'target_stack_address')

    def test_definition_reasons(self):
        self.assertEqual(self.reason(Fn().add(add_imm(8, 9, 8), blr(8))), 'add_sub_other')
        self.assertEqual(self.reason(Fn().add(sub_imm(8, 9, 8), blr(8))), 'add_sub_other')
        self.assertEqual(self.reason(Fn().add(ldp(8, 9, 8, 0x10, mode=3), blr(8))), 'writeback')
        self.assertEqual(self.reason(Fn().add(ldp(8, 8, 9, 0), blr(8))), 'ambiguous_pair')
        self.assertEqual(self.reason(Fn().add(MRS_TPIDR_X8, blr(8))), 'other_def:system')
        self.assertEqual(self.reason(Fn().add(ldr_w(8, 9, 0), blr(8))), 'other_def:ldr_narrow')
        self.assertEqual(self.reason(Fn().add(CNTD_X8, blr(8))), 'other_def:other')
        self.assertEqual(self.reason(Fn().add(ADD_X8_X9_X10, blr(8))), 'other_def:dp')
        self.assertEqual(self.reason(Fn().add(LDXP_X8_X9_X0, blr(9))), 'other_def:ldst_exclusive')

    def test_unknown_encodings_get_a_conservative_write_set(self):
        # an unmodeled word that writes x9 must hide an earlier definition of x9
        for word in (LDXP_X8_X9_X0, CNTD_X8 + 1):
            f = Fn().adrp(9, 0x100002000).add(word, ldr(8, 9, 8), blr(8))
            self.assertNotEqual(classify(f)['class'], 'got_or_global_fnptr', hex(word))

    def test_base_reasons(self):
        self.assertEqual(self.reason(Fn().add(ldr(8, 0, 8), blr(8))), 'base_entry_register_x0')
        self.assertEqual(self.reason(Fn().bl(0x100000900).add(ldr(8, 0, 8), blr(8))), 'base_call_result')
        self.assertEqual(self.reason(Fn().add(ldr(8, 9, 8), blr(8))), 'base_unresolved:undefined_at_entry')
        self.assertEqual(self.reason(Fn().add(movz(9, 0), ldr(8, 9, 8), blr(8))), 'base_const')
        self.assertEqual(self.reason(Fn().add(ldp(9, 10, 0, 0), ldr(8, 9, 0x48), blr(8))),
                         'base_loaded_from_memory_pair')

    def test_stack_reasons(self):
        self.assertEqual(self.reason(Fn().add(ldr(8, 31, 8), blr(8))), 'stack_slot_without_store')
        self.assertEqual(self.reason(Fn().add(add_imm(9, 31, 16), ldr(8, 9, 0), blr(8))),
                         'target_loaded_from_stack_object')
        # a store through the same slot, then a reload: traced to the stored value's source
        f = Fn().add(str_(0, 31, 8), nop(), ldr(8, 31, 8), blr(8))
        self.assertEqual(self.reason(f), 'target_is_entry_register_x0')
        f = Fn().add(stp(0, 1, 31, 16), ldr(8, 31, 24), blr(8))
        self.assertEqual(self.reason(f), 'target_is_entry_register_x1')
        f = Fn().adrp(9, 0x100002000).add(str_(9, 29, 8), ldr(8, 29, 8), blr(8))
        self.assertEqual(classify(f)['class'], 'static_address')

    def test_stack_slot_search_stops_at_stack_pointer_changes(self):
        for change in (sub_imm(31, 31, 16), SUB_SP_SP_X9, 0x910003bf):  # sub sp,sp,#16; sub sp,sp,x9; mov sp,x29
            f = Fn().add(str_(0, 31, 8), change, ldr(8, 31, 8), blr(8))
            self.assertEqual(self.reason(f), 'stack_slot_without_store', hex(change))
        f = Fn().add(str_(0, 29, 8), mov(29, 5), ldr(8, 29, 8), blr(8))
        self.assertEqual(self.reason(f), 'stack_slot_without_store')
        # a post-indexed push moves sp
        f = Fn().add(str_(0, 31, 8), 0xf8010fe1, ldr(8, 31, 8), blr(8))  # str x1, [sp, #16]!
        self.assertEqual(self.reason(f), 'stack_slot_without_store')

    def test_window_boundary(self):
        for distance, expected in ((WINDOW_WORDS, 'static_address'), (WINDOW_WORDS + 1, 'window_bound')):
            with self.subTest(distance=distance):
                f = Fn().add(*([nop()] * 10))
                f.adrp(8, 0x100002000)
                f.add(*([nop()] * (distance - 1)), blr(8))
                f.add(*([nop()] * 4))
                r = classify(f, site=f.at(10 + distance))
                if expected == 'static_address':
                    self.assertEqual(r['class'], expected)
                else:
                    self.assertEqual((r['class'], r['unknown_reason']), ('unknown', expected))
        # a short function reaches its entry instead of the window bound
        f = Fn().add(*([nop()] * 300), blr(8))
        self.assertEqual(classify(f)['unknown_reason'], 'window_bound')

    def test_register_hop_boundary(self):
        def chain(copies):
            f = Fn().adrp(8 + copies, 0x100002000)
            for k in range(copies, 0, -1):
                f.add(mov(8 + k - 1, 8 + k))
            return f.add(blr(8))
        self.assertEqual(classify(chain(6))['class'], 'static_address')
        r = classify(chain(7))
        self.assertEqual((r['class'], r['unknown_reason']), ('unknown', 'depth_limit'))


class JoinTests(unittest.TestCase):
    def test_join_between_definition_and_use_demotes_a_class(self):
        f = Fn().bl(0x100000800)
        f.add(cbz(5, f.pc, f.pc + 4))
        f.add(ldur(8, 0, -8), ldr(8, 8, 8), blr(8))
        r = classify(f)
        self.assertEqual((r['class'], r['unknown_reason'], r['class_before_join_refusal']),
                         ('unknown', 'join_in_slice', 'value_witness'))
        self.assertEqual(r['slot_offset'], 8)

    def test_join_from_a_supplied_target_set(self):
        f = value_witness(8)
        self.assertEqual(classify(f)['class'], 'value_witness')
        r = classify(f, branch_targets={f.at(1)})
        self.assertEqual((r['class'], r['unknown_reason']), ('unknown', 'join_in_slice'))
        # a target outside the function, or at the definition itself, is no join
        self.assertEqual(classify(f, branch_targets=[f.at(0), f.at(99), 0])['class'], 'value_witness')

    def test_back_edge_target_inside_the_slice_is_a_join(self):
        f = Fn().bl(0x100000800)
        f.add(ldur(8, 0, -8), ldr(8, 8, 8), blr(8))
        f.add(bcond(f.pc, f.at(2)))
        self.assertEqual(classify(f, site=f.at(3))['unknown_reason'], 'join_in_slice')

    def test_single_writer_callee_saved_register_is_exempt(self):
        def build(second_writer):
            f = Fn().bl(0x100000800).add(mov(22, 0))
            f.add(cbz(5, f.pc, f.pc + 4))
            f.add(ldur(8, 22, -8), ldr(8, 8, 8), blr(8))
            if second_writer:
                f.add(mov(22, 5))
            return f
        r = classify(build(False), site=BASE + 4 * 5)
        self.assertEqual(r['class'], 'value_witness')
        r = classify(build(True), site=BASE + 4 * 5)
        self.assertEqual((r['class'], r['unknown_reason']), ('unknown', 'join_in_slice'))

    def test_bc_cond_target_counts_as_a_join(self):
        f = Fn().bl(0x100000800).add(mov(9, 0))
        f.add(bcond(f.pc, f.at(3), 0) | 0x10)  # bc.cond: bit 4 set
        f.add(ldur(8, 9, -8), ldr(8, 8, 8), blr(8))
        r = classify(f, site=f.at(5))
        self.assertEqual((r['class'], r['unknown_reason']), ('unknown', 'join_in_slice'))

    def test_compare_and_branch_target_counts_as_a_join(self):
        f = Fn().bl(0x100000800).add(mov(9, 0))
        f.add(0x74000000 | (1 << 5))  # cb<cc> with imm9 = 1: target is the next word after itself
        f.add(ldur(8, 9, -8), ldr(8, 8, 8), blr(8))
        r = classify(f, site=f.at(5))
        self.assertEqual((r['class'], r['unknown_reason']), ('unknown', 'join_in_slice'))

    def test_casp_and_ld64b_write_the_following_registers(self):
        from airs.swift_indirect_target_shape import _decode
        self.assertTrue({0, 1} <= _decode(0x48207c82, BASE)['writes'])
        self.assertTrue(set(range(4, 12)) <= _decode(0xf83fd004, BASE)['writes'])  # ld64b x4

    def test_join_demotes_other_classes_too(self):
        f = Fn().adrp(8, 0x100002000)
        f.add(cbz(5, f.pc, f.pc + 4), blr(8))
        r = classify(f)
        self.assertEqual((r['class'], r['class_before_join_refusal']), ('unknown', 'static_address'))
        f = Fn().adrp(8, 0x100004000).add(ldr(8, 8, 0), blr(8))
        self.assertEqual(classify(f, branch_targets=[f.at(1)])['class_before_join_refusal'], 'got_or_global_fnptr')


class InputTotalityTests(unittest.TestCase):
    def refused(self, *args, **kw):
        r = classify_indirect_target(*args, **kw)
        self.assertEqual(r['class'], 'unknown')
        self.assertFalse(r['claims_callee_behaviour'])
        self.assertEqual(r['deciding_instructions'], [])
        return r['unknown_reason']

    def test_site_must_be_an_indirect_branch_in_the_function(self):
        f = value_witness(8)
        self.assertEqual(self.refused(f.w, f.start, f.at(0)), 'site_not_indirect_branch')
        self.assertEqual(classify_indirect_target(f.w, f.start, f.at(0))['site_kind'], 'bl')
        self.assertEqual(self.refused(f.w, f.start, f.at(4)), 'site_outside_function')
        self.assertEqual(self.refused(f.w, f.start, f.start - 4), 'site_outside_function')
        self.assertEqual(self.refused(f.w, f.start, f.site + 2), 'site_outside_function')
        for bad in (None, '0', 1.5, True, 2 ** 70):
            self.assertEqual(self.refused(f.w, f.start, bad), 'site_outside_function')
        self.assertEqual(self.refused([ret()], BASE, BASE), 'site_not_indirect_branch')
        self.assertEqual(self.refused([nop()], BASE, BASE), 'site_not_indirect_branch')

    def test_authenticated_branches_are_not_modeled(self):
        self.assertEqual(self.refused([blraaz(8)], BASE, BASE), 'authenticated_branch_not_modeled')
        self.assertEqual(self.refused([braaz(8)], BASE, BASE), 'authenticated_branch_not_modeled')

    def test_malformed_words_and_start(self):
        f = value_witness(8)
        raw = b''.join(w.to_bytes(4, 'little') for w in f.w)
        self.assertEqual(classify_indirect_target(raw, f.start, f.site)['class'], 'value_witness')
        self.assertEqual(classify_indirect_target(bytearray(raw), f.start, f.site)['class'], 'value_witness')
        self.assertEqual(classify_indirect_target(memoryview(raw), f.start, f.site)['class'], 'value_witness')
        self.assertEqual(classify_indirect_target(tuple(f.w), f.start, f.site)['class'], 'value_witness')
        self.assertEqual(self.refused(raw[:-1], f.start, f.site), 'function_words_truncated')
        self.assertEqual(self.refused(raw[:2], f.start, f.start), 'function_words_truncated')
        for bad in (None, 5, 'abcd', {1: 2}, [1, 2.0], [1, True], [-1], [2 ** 32], [None], iter([1])):
            self.assertEqual(self.refused(bad, BASE, BASE), 'invalid_function_words', repr(bad))
        self.assertEqual(self.refused([], BASE, BASE), 'site_outside_function')
        self.assertEqual(self.refused(b'', BASE, BASE), 'site_outside_function')
        for start in (None, -4, BASE + 2, 1.0, True, '1'):
            self.assertEqual(self.refused(f.w, start, f.site), 'invalid_function_start', repr(start))

    def test_branch_target_argument_is_validated(self):
        f = value_witness(8)
        for bad in (5, 'ab', [1.5], [None], {'a': 1}, [True]):
            self.assertEqual(self.refused(f.w, f.start, f.site, branch_targets=bad), 'invalid_branch_targets', repr(bad))
        self.assertEqual(classify_indirect_target(f.w, f.start, f.site, branch_targets=())['class'], 'value_witness')
        self.assertEqual(classify_indirect_target(f.w, f.start, f.site, branch_targets=frozenset())['class'], 'value_witness')

    def test_function_size_bound(self):
        self.assertEqual(self.refused(bytes(4 * (MAX_FUNCTION_WORDS + 1)), BASE, BASE), 'function_too_large')
        self.assertEqual(self.refused([nop()] * (MAX_FUNCTION_WORDS + 1), BASE, BASE), 'function_too_large')
        words = [nop()] * (MAX_FUNCTION_WORDS - 1) + [blr(8)]
        r = classify_indirect_target(words, BASE, BASE + 4 * (MAX_FUNCTION_WORDS - 1))
        self.assertEqual((r['class'], r['unknown_reason']), ('unknown', 'window_bound'))

    def test_unexpected_failure_is_a_refusal_not_an_exception(self):
        with mock.patch('airs.swift_indirect_target_shape._analyze', side_effect=RuntimeError('boom')):
            r = classify_indirect_target([blr(8)], BASE, BASE)
        self.assertEqual((r['class'], r['unknown_reason'], r['claims_callee_behaviour']),
                         ('unknown', 'analysis_failed', False))

    def test_random_words_never_raise_and_never_claim_behaviour(self):
        rng = random.Random(20261113)
        words = [rng.getrandbits(32) for _ in range(400)]
        for index in range(len(words)):
            if index % 16 == 0:
                words[index] = rng.choice((blr(rng.randrange(32)), br(rng.randrange(32)), ret(), nop()))
        for site in range(0, 400, 16):
            r = classify_indirect_target(words, BASE, BASE + 4 * site)
            self.assertIn(r['class'], CLASSES)
            self.assertFalse(r['claims_callee_behaviour'])
            self.assertEqual(r['model'], MODEL)
        for word in (0, 0xffffffff, 0x80000000, 0xd65f0bff, 0xd69f03e0, 0x54000010, 0xd4000001):
            for site in (classify_indirect_target([word, blr(8)], BASE, BASE + 4),):
                self.assertIn(site['class'], CLASSES)

    def test_record_shape_is_stable_and_json_serializable(self):
        r = classify(value_witness(0x20))
        self.assertEqual(set(r), {'model', 'site_pc', 'site_kind', 'class', 'slot_offset', 'unknown_reason',
                                  'deciding_instructions', 'evidence', 'class_before_join_refusal',
                                  'slot_address', 'slot_section', 'claims_callee_behaviour', 'bounds'})
        self.assertEqual(r['bounds'], dict(window_words=256, max_register_hops=6, max_function_words=MAX_FUNCTION_WORDS))
        self.assertEqual(json.loads(json.dumps(r)), r)
        self.assertEqual(set(r['deciding_instructions'][0]), {'pc', 'word', 'role'})
        self.assertEqual(classify(value_witness(0x20)), r)


class OwnedFixtureTests(unittest.TestCase):
    """The four got_base_not_adrp declines of the owned broad-imports fixture."""

    @classmethod
    def setUpClass(cls):
        expected = json.loads((FIXTURE / 'expected-got.json').read_text())
        cls.sites = [s['call_pc'] for s in expected['branch_sites'] if s.get('reason') == 'got_base_not_adrp']
        cls.image = parse_macho((FIXTURE / 'OwnedImports.macho').read_bytes(), 'OwnedImports.macho',
                                IMPORTS_BROAD_LIMITS)

    def function_words(self, pc):
        fn = next(f for f in self.image.functions if f.start <= pc < f.end)
        text = next(s for s in self.image.sections if s.segment == '__TEXT' and s.name == '__text')
        offset = text.file_offset + fn.start - text.address
        return fn.start, self.image.data[offset:offset + fn.end - fn.start]

    def check(self, pc, slot):
        start, code = self.function_words(pc)
        r = classify_indirect_target(code, start, pc, sections=self.image.sections)
        self.assertEqual((r['class'], r['slot_offset'], r['unknown_reason']), ('value_witness', slot, None))
        self.assertEqual(r['deciding_instructions'][-1]['role'], 'indirect_branch')
        self.assertFalse(r['claims_callee_behaviour'])

    def test_four_sites_recorded(self):
        self.assertEqual(self.sites, [0x100000cdc, 0x100000f9c, 0x1000012a4, 0x100001438])

    def test_site_0x100000cdc_value_witness_slot_0x10(self):
        self.check(0x100000cdc, 0x10)

    def test_site_0x100000f9c_value_witness_slot_0x8(self):
        self.check(0x100000f9c, 0x8)

    def test_site_0x1000012a4_value_witness_slot_0x8(self):
        self.check(0x1000012a4, 0x8)

    def test_site_0x100001438_value_witness_slot_0x8(self):
        self.check(0x100001438, 0x8)


if __name__ == '__main__':
    unittest.main()
