"""Owned synthetic tests for airs.swift_value_witness_admission (swift-value-witness-admission-v1).

Instruction words are hand-encoded (tests/shape_word_helpers.py); no image or word is executed.
Symbol knowledge is supplied through small lookup tables, so no test does I/O except the owned
fixture class, which reads the committed broad-imports fixture with the existing Mach-O reader.
"""
import json
import random
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shape_word_helpers import (  # noqa: E402
    BASE, Fn, add_imm, blr, br, cbz, ldr, ldur, mov, movz, nop, ret, str_)
from airs import swift_value_witness_admission as adm
from airs.macho import parse_macho
from airs.macho_stubs import attribute_import_stubs
from airs.swift_broad_flow import IMPORTS_BROAD_LIMITS
from airs.swift_indirect_target_shape import analyze_indirect_target
from airs.swift_value_witness_admission import (
    MODEL, PROVENANCE_KINDS, RUNTIME_METADATA_FUNCTIONS, _first_clobber, admit_value_witness)

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'swift-error-flow' / 'broad-imports'

LOCAL_ACCESSOR = 0x100000800     # in-image function entry named as a type metadata accessor
IMPORT_ACCESSOR = 0x100000900    # attributed import stub named as a type metadata accessor
OTHER_FUNCTION = 0x100000a00     # in-image function entry that is not a metadata accessor
OBJC_METADATA = 0x100000b00      # import stub for swift_getObjCClassMetadata
UNLISTED_STUB = 0x100000c00      # import stub for a runtime function not on the list
NAMELESS_ENTRY = 0x100000d00     # exact function entry without a symbol
RUNTIME_BASE = 0x100001000 + 0x1000   # one stub per runtime name, 0x100 apart

TABLE = {
    LOCAL_ACCESSOR: ('$s7Example3FooVMa', 'function_entry'),
    IMPORT_ACCESSOR: ('_$sSS10FoundationE8EncodingVMa', 'import_stub'),
    OTHER_FUNCTION: ('$s7Example3fooyyF', 'function_entry'),
    OBJC_METADATA: ('_swift_getObjCClassMetadata', 'import_stub'),
    UNLISTED_STUB: ('_swift_retain', 'import_stub'),
    NAMELESS_ENTRY: (None, 'function_entry'),
}
RUNTIME_ADDRESSES = {}
for _i, _name in enumerate(sorted(RUNTIME_METADATA_FUNCTIONS)):
    RUNTIME_ADDRESSES[_name] = RUNTIME_BASE + 0x100 * _i
    TABLE[RUNTIME_BASE + 0x100 * _i] = ('_' + _name, 'import_stub')


def lookup(address):
    return TABLE.get(address)


def tail(meta, off=8, call=blr):
    return [ldur(8, meta, -8), ldr(8, 8, off), call(8)]


def vw(accessor=LOCAL_ACCESSOR, meta=0, off=8, copy=None, call=blr):
    f = Fn().bl(accessor)
    if copy == 'mov':
        f.add(mov(22, 0))
        meta = 22
    elif copy == 'add0':
        f.add(add_imm(22, 0, 0))
        meta = 22
    elif copy == 'chain':
        f.add(mov(21, 0), add_imm(22, 21, 0))
        meta = 22
    return f.add(*tail(meta, off, call))


def admit(fn, symbol_lookup=lookup, **kw):
    r = admit_value_witness(list(fn.w), fn.start, fn.site, symbol_lookup, **kw)
    assert r['model'] == MODEL and r['provenance_kind'] in PROVENANCE_KINDS
    assert r['claims_callee_behaviour'] is False and r['tier1']['claims_callee_behaviour'] is False
    assert r['first_failing_condition'] in (None, 1, 2, 3)
    assert (r['first_failing_condition'] is None) == r['admitted']
    assert (r['abi_basis'] is not None) == r['admitted']
    return r


def verdict(r):
    return r['admitted'], r['provenance_kind'], r['first_failing_condition'], r['reason']


class AcceptedProvenanceTests(unittest.TestCase):
    def test_local_metadata_accessor(self):
        r = admit(vw())
        self.assertEqual(verdict(r), (True, 'metadata_accessor_call', None, 'meets_tier2_conditions'))
        self.assertEqual((r['symbol'], r['metadata_register'], r['slot_offset'], r['site_kind']),
                         ('$s7Example3FooVMa', 'x0', 8, 'blr'))
        self.assertEqual(r['abi_basis'], 'value_witness_function_slots_cannot_throw')
        self.assertEqual(r['tier1']['class'], 'value_witness')
        self.assertEqual(r['evidence'], r['tier1']['deciding_instructions'])

    def test_imported_metadata_accessor(self):
        r = admit(vw(IMPORT_ACCESSOR))
        self.assertEqual(verdict(r), (True, 'imported_metadata_accessor_call', None, 'meets_tier2_conditions'))
        self.assertEqual(r['symbol'], '_$sSS10FoundationE8EncodingVMa')

    def test_every_runtime_name_with_and_without_underscore(self):
        self.assertEqual(len(RUNTIME_METADATA_FUNCTIONS), 6)
        for name, address in RUNTIME_ADDRESSES.items():
            for symbol in ('_' + name, name):
                with self.subTest(symbol=symbol):
                    r = admit(vw(address), lambda a, s=symbol, ad=address: (s, 'import_stub') if a == ad else None)
                    self.assertEqual(verdict(r), (True, 'runtime_metadata_call', None, 'meets_tier2_conditions'))
                    self.assertEqual(r['symbol'], symbol)

    def test_copies_through_mov_and_add_zero(self):
        for copy, reg in (('mov', 'x22'), ('add0', 'x22'), ('chain', 'x22')):
            with self.subTest(copy=copy):
                r = admit(vw(copy=copy))
                self.assertEqual((r['admitted'], r['metadata_register']), (True, reg))

    def test_br_site_is_admitted(self):
        r = admit(vw(call=br))
        self.assertEqual((r['admitted'], r['site_kind']), (True, 'br'))

    def test_every_function_slot(self):
        for off in (0x0, 0x8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x58, 0x60, 0x68):
            with self.subTest(off=off):
                self.assertTrue(admit(vw(off=off))['admitted'])

    def test_callee_saved_copy_survives_an_intervening_call(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(mov(22, 0)).bl(OTHER_FUNCTION).add(*tail(22))
        self.assertTrue(admit(f)['admitted'])

    def test_unrelated_writes_do_not_refuse(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(movz(1, 0), mov(22, 0), movz(5, 1), movz(19, 2)).add(*tail(22))
        self.assertTrue(admit(f)['admitted'])

    def test_lookup_result_shapes(self):
        class Info:
            def __init__(self, symbol, kind):
                self.symbol, self.kind = symbol, kind
        for shape in (lambda s, k: (s, k), lambda s, k: [s, k], Info):
            with self.subTest(shape=shape):
                r = admit(vw(), lambda a, shape=shape: shape('$s7Example3FooVMa', 'function_entry'))
                self.assertTrue(r['admitted'])

    def test_lookup_called_with_the_direct_target_only(self):
        seen = []
        admit(vw(), lambda a: seen.append(a) or TABLE.get(a))
        self.assertEqual(seen, [LOCAL_ACCESSOR])


class Condition1Tests(unittest.TestCase):
    def test_off_slot_offsets_are_refused(self):
        for off in (0x40, 0x48, 0x50, 0x70):
            with self.subTest(off=off):
                r = admit(vw(off=off))
                self.assertEqual(verdict(r), (False, 'unknown', 1, 'value_witness_offset_not_function_slot'))
                self.assertEqual(r['slot_offset'], off)

    def test_class_vtable_is_refused(self):
        r = admit(Fn().add(ldr(9, 19, 0), ldr(8, 9, 0x58), blr(8)))
        self.assertEqual(verdict(r), (False, 'unknown', 1, 'tier1_class_class_vtable'))

    def test_closure_context_is_refused(self):
        r = admit(Fn().add(ldr(9, 20, 0), ldr(8, 20, 8), blr(8)))
        self.assertEqual((r['admitted'], r['first_failing_condition']), (False, 1))
        self.assertEqual(r['reason'], 'tier1_class_' + r['tier1']['class'] if r['tier1']['class'] != 'unknown'
                         else r['tier1']['unknown_reason'])

    def test_join_in_slice_is_refused(self):
        f = Fn().bl(LOCAL_ACCESSOR)
        f.add(cbz(5, f.pc, f.pc + 4))        # a conditional branch whose target is the next word
        f.add(*tail(0))
        r = admit(f)
        self.assertEqual(verdict(r), (False, 'unknown', 1, 'join_in_slice'))
        self.assertEqual(r['tier1']['class_before_join_refusal'], 'value_witness')

    def test_join_from_a_supplied_target_set(self):
        f = vw()
        self.assertTrue(admit(f)['admitted'])
        r = admit(f, branch_targets=[f.at(1)])
        self.assertEqual(verdict(r), (False, 'unknown', 1, 'join_in_slice'))

    def test_table_register_clobbered_by_a_call(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(ldur(8, 0, -8)).bl(OTHER_FUNCTION).add(ldr(8, 8, 8), blr(8))
        r = admit(f)
        self.assertEqual((r['admitted'], r['first_failing_condition']), (False, 1))
        self.assertIn('clobbered_by_call', r['reason'])

    def test_target_register_clobbered_by_a_call(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(ldur(9, 0, -8), ldr(8, 9, 8)).bl(OTHER_FUNCTION).add(blr(8))
        r = admit(f)
        self.assertEqual(verdict(r), (False, 'unknown', 1, 'clobbered_by_call'))

    def test_non_branch_site_and_bad_input_are_condition_1(self):
        f = vw()
        for site in (f.start, f.start - 4, f.site + 4, 3):
            with self.subTest(site=site):
                r = admit_value_witness(list(f.w), f.start, site, lookup)
                self.assertEqual((r['admitted'], r['first_failing_condition']), (False, 1))
                self.assertFalse(r['claims_callee_behaviour'])


class Condition2Tests(unittest.TestCase):
    def test_isa_load_is_refused(self):
        r = admit(Fn().add(ldr(9, 19, 0)).add(*tail(9)))
        self.assertEqual(verdict(r), (False, 'isa_load', 2, 'isa_is_not_proven_swift_metadata'))
        self.assertEqual(r['metadata_register'], 'x9')

    def test_entry_register_is_refused(self):
        r = admit(Fn().add(*tail(0)))
        self.assertEqual(verdict(r), (False, 'entry_register', 2, 'entry_metadata_signature_unmapped'))

    def test_metadata_stack_transport_is_refused(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(str_(0, 31, 8), ldr(9, 31, 8)).add(*tail(9))
        self.assertEqual(verdict(admit(f)), (False, 'stack_transport', 2, 'metadata_stack_transport_not_admitted'))

    def test_stack_slot_without_store_is_refused(self):
        f = Fn().add(ldr(9, 31, 8)).add(*tail(9))
        r = admit(f)
        self.assertEqual((r['admitted'], r['provenance_kind'], r['first_failing_condition']),
                         (False, 'stack_transport', 2))

    def test_objc_class_metadata_is_refused(self):
        r = admit(vw(OBJC_METADATA))
        self.assertEqual(verdict(r), (False, 'objc_class_metadata', 2, 'objc_class_metadata_not_admitted'))
        self.assertEqual(r['symbol'], '_swift_getObjCClassMetadata')
        r = admit(vw(OBJC_METADATA), lambda a: ('swift_getObjCClassMetadata', 'import_stub'))
        self.assertEqual(r['provenance_kind'], 'objc_class_metadata')

    def test_unlisted_runtime_stub_is_refused(self):
        r = admit(vw(UNLISTED_STUB))
        self.assertEqual(verdict(r), (False, 'unknown', 2, 'runtime_symbol_not_allowlisted'))

    def test_runtime_list_is_exact_not_prefix(self):
        for symbol in ('_swift_getGenericMetadataX', '_swift_getGenericMetadat', '__swift_getGenericMetadata',
                       '_swift_getGenericMetadata ', '_Swift_getGenericMetadata', '_swift_getTypeByMangledName',
                       '_swift_getTypeByMangledNameInContext'):
            with self.subTest(symbol=symbol):
                r = admit(vw(), lambda a, s=symbol: (s, 'import_stub'))
                self.assertEqual(verdict(r)[:3], (False, 'unknown', 2))

    def test_local_non_accessor_symbol_is_refused(self):
        r = admit(vw(OTHER_FUNCTION))
        self.assertEqual(verdict(r), (False, 'unknown', 2, 'grammar_not_metadata_accessor'))
        self.assertEqual(r['symbol'], '$s7Example3fooyyF')

    def test_local_runtime_name_is_not_a_runtime_call(self):
        # The runtime list applies to import stubs only; an in-image function entry with that name is
        # not a type metadata accessor.
        r = admit(vw(), lambda a: ('_swift_getGenericMetadata', 'function_entry'))
        self.assertEqual((r['admitted'], r['first_failing_condition']), (False, 2))

    def test_undecodable_local_symbol_carries_the_grammar_reason(self):
        r = admit(vw(), lambda a: ('not a swift symbol', 'function_entry'))
        self.assertEqual((r['admitted'], r['first_failing_condition']), (False, 2))
        self.assertTrue(r['reason'].startswith('grammar_'))

    def test_function_entry_without_symbol_is_refused(self):
        self.assertEqual(verdict(admit(vw(NAMELESS_ENTRY))),
                         (False, 'unknown', 2, 'direct_target_symbol_missing'))

    def test_lookup_answers(self):
        cases = [
            (None, 'symbol_lookup_unavailable'),
            ('not callable', 'symbol_lookup_unavailable'),
            (lambda a: None, 'direct_target_unattributed'),
            (lambda a: ('x', 'data'), 'direct_target_not_function_entry_or_stub'),
            (lambda a: ('x', None), 'direct_target_not_function_entry_or_stub'),
            (lambda a: 5, 'symbol_lookup_invalid_result'),
            (lambda a: ('a', 'b', 'c'), 'symbol_lookup_invalid_result'),
            (lambda a: (7, 'import_stub'), 'symbol_lookup_invalid_result'),
            (lambda a: (b'$s7Example3FooVMa', 'function_entry'), 'symbol_lookup_invalid_result'),
            (lambda a: ('A' * 5000, 'function_entry'), 'symbol_lookup_invalid_result'),
            (lambda a: (None, 'import_stub'), 'direct_target_symbol_missing'),
        ]
        for fn, reason in cases:
            with self.subTest(reason=reason, fn=fn):
                r = admit(vw(), fn)
                self.assertEqual((r['admitted'], r['first_failing_condition'], r['reason']), (False, 2, reason))

    def test_raising_lookup_is_refused_not_raised(self):
        def boom(address):
            raise RuntimeError('boom')
        self.assertEqual(admit(vw(), boom)['reason'], 'symbol_lookup_failed')

        class Bad:
            @property
            def symbol(self):
                raise ValueError

            kind = 'function_entry'
        self.assertEqual(admit(vw(), lambda a: Bad())['reason'], 'symbol_lookup_invalid_result')

    def test_result_register_must_be_x0(self):
        r = admit(Fn().bl(LOCAL_ACCESSOR).add(*tail(1)))
        self.assertEqual(verdict(r), (False, 'unknown', 2, 'metadata_result_not_x0'))
        self.assertEqual(r['metadata_register'], 'x1')

    def test_metadata_call_must_be_direct_bl(self):
        r = admit(Fn().add(blr(9)).add(*tail(0)))
        self.assertEqual(verdict(r), (False, 'unknown', 2, 'metadata_call_not_direct_bl'))

    def test_metadata_defined_by_adrp_or_constant_is_refused(self):
        f = Fn()
        f.adrp(0, BASE + 0x1000)
        r = admit(f.add(*tail(0)))
        self.assertEqual(verdict(r), (False, 'unknown', 2, 'metadata_definition_adrp'))
        r = admit(Fn().bl(LOCAL_ACCESSOR).add(movz(0, 5)).add(*tail(0)))
        self.assertEqual(verdict(r), (False, 'unknown', 2, 'metadata_definition_const'))

    def test_refused_conditions_never_fall_through_to_admission(self):
        for fn in (vw(OBJC_METADATA), vw(UNLISTED_STUB), vw(OTHER_FUNCTION), Fn().add(*tail(0))):
            self.assertFalse(admit(fn)['admitted'])


class ClobberTests(unittest.TestCase):
    """A write on any definition-to-use interval refuses; calls clobber x0..x17 and x30."""

    def test_metadata_register_overwritten_by_a_later_call(self):
        # the nearest definition of x0 is the second call, which is not an accessor
        f = Fn().bl(LOCAL_ACCESSOR).bl(OTHER_FUNCTION).add(*tail(0))
        self.assertEqual(verdict(admit(f)), (False, 'unknown', 2, 'grammar_not_metadata_accessor'))

    def test_metadata_register_overwritten_by_a_move(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(movz(0, 1)).add(*tail(0))
        self.assertEqual(admit(f)['first_failing_condition'], 2)

    def test_copy_overwritten_before_the_table_load(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(mov(22, 0), movz(22, 0)).add(*tail(22))
        self.assertEqual(admit(f)['first_failing_condition'], 2)

    def test_copy_in_a_call_clobbered_register(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(mov(9, 0)).bl(OTHER_FUNCTION).add(*tail(9))
        r = admit(f)
        self.assertEqual((r['admitted'], r['first_failing_condition']), (False, 2))

    def test_table_register_interval(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(ldur(9, 0, -8)).bl(OTHER_FUNCTION).add(ldr(8, 9, 8), blr(8))
        r = admit(f)
        self.assertEqual((r['admitted'], r['first_failing_condition']), (False, 1))

    def test_target_register_interval(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(ldur(9, 0, -8), ldr(8, 9, 8), movz(8, 0)).add(blr(8))
        self.assertFalse(admit(f)['admitted'])
        f = Fn().bl(LOCAL_ACCESSOR).add(ldur(9, 0, -8), ldr(8, 9, 8)).bl(OTHER_FUNCTION).add(blr(8))
        self.assertEqual(admit(f)['first_failing_condition'], 1)

    def test_stack_transport_in_the_table_or_target_chain_is_condition_3(self):
        for f in (Fn().bl(LOCAL_ACCESSOR).add(ldur(8, 0, -8), str_(8, 31, 16), ldr(9, 31, 16), ldr(8, 9, 8), blr(8)),
                  Fn().bl(LOCAL_ACCESSOR).add(ldur(9, 0, -8), ldr(8, 9, 8), str_(8, 31, 16), ldr(8, 31, 16), blr(8))):
            r = admit(f)
            self.assertEqual(verdict(r), (False, 'metadata_accessor_call', 3, 'stack_transport_not_admitted'))

    def test_condition_3_reports_the_clobbering_register_and_address(self):
        f = vw()
        with mock.patch.object(adm, '_first_clobber', return_value=0x100001008) as m:
            r = admit(f)
        self.assertTrue(m.called)
        self.assertEqual((r['admitted'], r['provenance_kind'], r['first_failing_condition']),
                         (False, 'metadata_accessor_call', 3))
        self.assertRegex(r['reason'], r'^register_x\d+_written_at_0x100001008$')
        self.assertEqual(r['symbol'], '$s7Example3FooVMa')

    def test_condition_3_checks_every_interval_of_the_chain(self):
        f = vw(copy='mov')
        seen = []

        def spy(function, reg, low, high):
            seen.append((reg, low, high))
            return None
        with mock.patch.object(adm, '_first_clobber', side_effect=spy):
            self.assertTrue(admit(f)['admitted'])
        self.assertEqual({reg for reg, _, _ in seen}, {0, 22, 8})
        self.assertTrue(all(low < high for _, low, high in seen))

    def test_first_clobber_directly(self):
        f = Fn().bl(LOCAL_ACCESSOR).add(mov(22, 0), movz(5, 1), movz(19, 2)).bl(OTHER_FUNCTION).add(*tail(22))
        function = analyze_indirect_target(list(f.w), f.start, f.site).function
        lo, hi = f.at(0), f.at(6)
        self.assertEqual(_first_clobber(function, 22, lo, hi), f.at(1))
        self.assertEqual(_first_clobber(function, 5, lo, hi), f.at(2))
        self.assertEqual(_first_clobber(function, 19, lo, hi), f.at(3))
        self.assertEqual(_first_clobber(function, 30, lo, hi), f.at(4))     # a call writes x30
        self.assertEqual(_first_clobber(function, 0, lo, hi), f.at(4))      # and x0..x17
        self.assertEqual(_first_clobber(function, 17, lo, hi), f.at(4))
        self.assertIsNone(_first_clobber(function, 18, lo, hi))             # but not x18..x28
        self.assertIsNone(_first_clobber(function, 21, lo, hi))
        self.assertIsNone(_first_clobber(function, 22, f.at(1), hi))        # endpoints are exclusive
        self.assertIsNone(_first_clobber(function, 19, f.at(3), hi))
        self.assertIsNone(_first_clobber(function, 5, lo, f.at(2)))
        self.assertIsNone(_first_clobber(function, 5, lo, lo))


class TotalityTests(unittest.TestCase):
    def test_malformed_and_truncated_inputs_never_raise(self):
        f = vw()
        cases = [
            (b'', f.start, f.start), (b'\x00' * 3, f.start, f.start), (bytes(range(9)), f.start, f.start),
            (None, f.start, f.start), (5, f.start, f.start), ([1, 2, None], f.start, f.start),
            (list(f.w), None, f.site), (list(f.w), f.start, None), (list(f.w), f.start + 1, f.site),
            (list(f.w), f.start, f.site + 1), (list(f.w), 'x', f.site), (list(f.w), f.start, 'x'),
            ([2 ** 40] * 4, f.start, f.start), ([-1] * 4, f.start, f.start), (list(f.w), 2 ** 70, 2 ** 70),
            (b'\xff' * 4096, f.start, f.start + 8),
        ]
        for words, start, site in cases:
            with self.subTest(start=start, site=site):
                for symbol_lookup in (lookup, None, lambda a: 1 / 0):
                    r = admit_value_witness(words, start, site, symbol_lookup)
                    self.assertFalse(r['admitted'])
                    self.assertEqual(r['first_failing_condition'], 1)
                    self.assertFalse(r['claims_callee_behaviour'])
                    self.assertEqual(r['model'], MODEL)

    def test_bad_branch_targets_and_sections_are_refused(self):
        f = vw()
        for targets in ('abc', [None], [1.5], 5):
            with self.subTest(targets=targets):
                r = admit_value_witness(list(f.w), f.start, f.site, lookup, branch_targets=targets)
                self.assertEqual((r['admitted'], r['first_failing_condition']), (False, 1))
        r = admit_value_witness(list(f.w), f.start, f.site, lookup, sections=object())
        self.assertFalse(r['claims_callee_behaviour'])

    def test_exception_inside_admission_becomes_analysis_failed(self):
        with mock.patch.object(adm, '_provenance', side_effect=RuntimeError('boom')):
            r = admit(vw())
        self.assertEqual((r['admitted'], r['first_failing_condition'], r['reason']), (False, 1, 'analysis_failed'))

    def test_random_words_and_random_lookups(self):
        rng = random.Random(0x4e57)
        answers = [None, ('$s7Example3FooVMa', 'function_entry'), ('_swift_getGenericMetadata', 'import_stub'),
                   (None, 'function_entry'), ('_swift_getObjCClassMetadata', 'import_stub'), 7, ('x', 'y')]
        for n in range(300):
            count = rng.randint(1, 40)
            words = [rng.getrandbits(32) for _ in range(count)]
            if rng.random() < 0.5:   # plant an indirect call at the end
                words[-1] = blr(rng.randint(0, 30))
                if count > 2 and rng.random() < 0.5:
                    words[-2] = ldr(words[-1] >> 5 & 31, rng.randint(0, 30), 8 * rng.randint(0, 20))
            site = BASE + 4 * rng.randint(0, count - 1)
            ans = rng.choice(answers)
            r = admit_value_witness(words, BASE, site, lambda a, ans=ans: ans)
            self.assertFalse(r['claims_callee_behaviour'])
            self.assertEqual((r['first_failing_condition'] is None), r['admitted'])
            self.assertIn(r['provenance_kind'], PROVENANCE_KINDS)
            self.assertIsInstance(r['reason'], str)

    def test_every_result_says_it_claims_no_callee_behaviour(self):
        for fn in (vw(), vw(OBJC_METADATA), Fn().add(*tail(0)), vw(off=0x40)):
            r = admit(fn)
            self.assertIs(r['claims_callee_behaviour'], False)
            self.assertIs(r['tier1']['claims_callee_behaviour'], False)

    def test_admission_does_not_depend_on_unrelated_code_after_the_site(self):
        f = vw()
        before = admit(f)
        f.add(ret(), nop(), nop())
        after = admit_value_witness(list(f.w), f.start, f.site - 12, lookup)
        self.assertEqual(verdict(before), verdict(after))


class OwnedFixtureTests(unittest.TestCase):
    """The four got_base_not_adrp sites of the owned broad-imports fixture, with fixture symbols."""

    @classmethod
    def setUpClass(cls):
        expected = json.loads((FIXTURE / 'expected-got.json').read_text())
        cls.sites = [s['call_pc'] for s in expected['branch_sites'] if s.get('reason') == 'got_base_not_adrp']
        cls.image = parse_macho((FIXTURE / 'OwnedImports.macho').read_bytes(), 'OwnedImports.macho',
                                IMPORTS_BROAD_LIMITS)
        cls.stubs = attribute_import_stubs(cls.image)
        cls.entries = {f.start: f for f in cls.image.functions}

    def symbol_lookup(self, address):
        found = self.stubs.lookup(address)
        if found and found[0] == 'attributed':
            return found[1].symbol, 'import_stub'
        if address in self.entries:
            name = self.entries[address].name
            # the reader names unsymbolized functions sub_<address>; that is not symbol knowledge
            return (None if not name or name.startswith('sub_') else name), 'function_entry'
        return None

    def run_site(self, pc):
        fn = next(f for f in self.image.functions if f.start <= pc < f.end)
        text = next(s for s in self.image.sections if s.segment == '__TEXT' and s.name == '__text')
        offset = text.file_offset + fn.start - text.address
        code = self.image.data[offset:offset + fn.end - fn.start]
        r = admit_value_witness(code, fn.start, pc, self.symbol_lookup, sections=self.image.sections)
        self.assertEqual(r['tier1']['class'], 'value_witness')
        self.assertFalse(r['claims_callee_behaviour'])
        return r

    def test_four_sites_recorded(self):
        self.assertEqual(self.sites, [0x100000cdc, 0x100000f9c, 0x1000012a4, 0x100001438])

    def test_site_0x100000cdc_metadata_through_the_stack_is_refused(self):
        r = self.run_site(0x100000cdc)
        self.assertEqual(verdict(r), (False, 'stack_transport', 2, 'metadata_stack_transport_not_admitted'))

    def test_site_0x100000f9c_imported_metadata_accessor_is_admitted(self):
        r = self.run_site(0x100000f9c)
        self.assertEqual(verdict(r), (True, 'imported_metadata_accessor_call', None, 'meets_tier2_conditions'))
        self.assertEqual(r['symbol'], '_$sSS10FoundationE8EncodingVMa')

    def test_site_0x1000012a4_unnamed_local_callee_is_refused(self):
        r = self.run_site(0x1000012a4)
        self.assertEqual(verdict(r), (False, 'unknown', 2, 'direct_target_symbol_missing'))

    def test_site_0x100001438_unnamed_local_callee_is_refused(self):
        r = self.run_site(0x100001438)
        self.assertEqual(verdict(r), (False, 'unknown', 2, 'direct_target_symbol_missing'))


if __name__ == '__main__':
    unittest.main()
