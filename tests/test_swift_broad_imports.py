"""Owned synthetic fixtures for broad-imports-v1 and airs.macho_stubs.

Expectations derive from the written contract for the profile (summarised in
docs/SWIFT_BROAD_IMPORTS_PROFILE.md) and from the independent byte layout in
stub_image_helpers (documented there).
Addresses and offsets below are hand-derived from that layout, never copied
from implementation output. No image is executed.
"""
import contextlib
import io
import json
import struct
import sys
import tempfile
import unittest
from dataclasses import asdict, replace
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parser_helpers import build_fat  # noqa: E402
from stub_image_helpers import (  # noqa: E402
    BRAA_X16_X17, BRAAZ_X16, BR_X16, Import, NOP, NL_DESC, NL_SECT, NL_STRX, NL_TYPE, NL_VALUE,
    PointerSection, RET, SECT_RESERVED1, SECT_RESERVED2, SECT_SIZE, X16, X17, adrp, adrp_imm, br,
    build_stub_image, ldr_x_literal, ldr_x_uimm, patch,
)
from airs.macho import parse_macho  # noqa: E402
from airs.types import InputError  # noqa: E402
from airs.swift_import_declarations import parse_import_declaration  # noqa: E402
from airs.swift_broad_flow import (  # noqa: E402
    EXTENDED_BROAD_LIMITS, IMPORTS_BROAD_LIMITS, PROFILE_LIMITS, recover_swift_broad_flow,
)
from airs.macho_stubs import STUB_MODEL, StubLimits, attribute_import_stubs  # noqa: E402

PROFILE = 'broad-imports-v1'
MODEL = 'swift-broad-error-flow-imports-v1'
THROWING = '_$s4Test3fooyS2iKF'
THROWING2 = '_$s4Test3baryS2iKF'
NON_THROWING = '_$s4Test3fooyS2iF'
UNRESOLVED = '_$sZZZ'
OLD_LIMITATIONS = ['structural_only', 'no_source_or_handler_semantics',
                   'unsupported_abi_and_dispatch_remain_unresolved',
                   'recorded_checks_are_historical_when_saved']
IMPORT_KEYS = {'import_stub_model', 'import_stubs_complete', 'import_stub_reason', 'import_stub_counts'}

# Hand layout of the default image (see stub_image_helpers docstring):
# caller0 @0x1000: BL stub0 (0x94000002); RET. __stubs @0x1008 (one entry),
# __DATA_CONST,__got @0x4000 (one slot), __LINKEDIT @0x8000: function starts
# 8 bytes, nlist @0x8008 (sym0 _caller0, sym1 import), indirect @0x8028
# (entries [1, 1]), strings @0x8030 ("\0_caller0\0<import>\0" padded).
CALLER = 0x100001000
STUB = 0x100001008
GOT = 0x100004000
NLIST = 0x8008
INDIRECT = 0x8028


def image_of(data):
    return parse_macho(data, limits=EXTENDED_BROAD_LIMITS)


def flow(image, limits=None, profile=PROFILE):
    return recover_swift_broad_flow(image, limits, profile=profile)


def provenance(stub=STUB, slice_file=0x1008, words=(0xF0000010, 0xF9400210, 0xD61F0200),
               stub_entry=INDIRECT, pointer_entry=INDIRECT + 4, nlist=NLIST + 16, container_delta=0):
    return {
        'stub_words': [{'pc': stub + 4 * k, 'word': '0x%08x' % words[k],
                        'slice_file_offset': slice_file + 4 * k,
                        'container_file_offset': slice_file + 4 * k + container_delta} for k in range(3)],
        'stub_indirect_entry_offset': stub_entry,
        'pointer_indirect_entry_offset': pointer_entry,
        'nlist_offset': nlist,
    }


def listify(value):
    # Report rows pass through the coordinator's public-row copy, which (for every
    # existing row too) turns tuples into JSON lists; values are otherwise asdict().
    if isinstance(value, dict):
        return {k: listify(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [listify(v) for v in value]
    return value


def zero_import_counts(**overrides):
    counts = dict(attributed_stubs=0, declined_stubs=0, invalid_stub_sections=0, selected_import_calls=0,
                  non_throwing_swift_import_calls=0, non_swift_import_calls=0, declined_stub_calls=0)
    counts.update(overrides)
    return counts


class StubImageBuilderTests(unittest.TestCase):
    def test_default_layout_matches_hand_derivation(self):
        data, layout = build_stub_image()
        self.assertEqual((layout.text_addr, layout.stubs_addr, layout.pointers['__got']['addr']),
                         (CALLER, STUB, GOT))
        self.assertEqual((layout.symoff, layout.indirect_off, layout.stroff, layout.strx),
                         (NLIST, INDIRECT, 0x8030, [1, 10]))
        self.assertEqual(layout.pointers['__got']['reserved1'], 1)
        self.assertEqual(struct.unpack_from('<IIIII', data, 0x1000), (0x94000002, RET, 0xF0000010,
                                                                      0xF9400210, 0xD61F0200))
        self.assertEqual(struct.unpack_from('<II', data, INDIRECT), (1, 1))
        self.assertEqual(struct.unpack_from('<IBBHQ', data, NLIST + 16), (10, 0x01, 0, 0x200, 0))
        image = image_of(data)
        self.assertEqual([f.start for f in image.functions], [CALLER])
        # The pre-existing pipeline accepts the image unchanged.
        report = flow(image, profile='broad-extended-v1')
        self.assertEqual(report['observed_call_instructions'], 1)
        self.assertEqual(report['selected_call_candidates'], 0)


class StubTableTests(unittest.TestCase):
    def expected_record(self, **prov):
        return {'address': STUB, 'section': '__TEXT,__stubs', 'stub_index': 0, 'symbol': THROWING,
                'symbol_index': 1, 'library_ordinal': 2, 'pointer_address': GOT,
                'pointer_section': '__DATA_CONST,__got', 'provenance': provenance(**prov)}

    def test_positive_attribution_record_and_lookup(self):
        data, _ = build_stub_image()
        table = attribute_import_stubs(image_of(data))
        self.assertEqual(table.model, STUB_MODEL)
        self.assertEqual(STUB_MODEL, 'arm64-import-stub-double-binding-v1')
        self.assertTrue(table.complete)
        self.assertIsNone(table.reason)
        self.assertEqual(table.stub_sections, 1)
        self.assertEqual(tuple(table.invalid_sections), ())
        self.assertEqual(dict(table.declined), {})
        self.assertEqual(list(table.attributed), [STUB])
        stub = table.attributed[STUB]
        self.assertEqual((stub.address, stub.section, stub.stub_index, stub.symbol, stub.symbol_index,
                          stub.library_ordinal, stub.pointer_address, stub.pointer_section),
                         (STUB, '__TEXT,__stubs', 0, THROWING, 1, 2, GOT, '__DATA_CONST,__got'))
        record = stub.record()
        self.assertIs(type(record), dict)
        self.assertEqual(record, self.expected_record())
        json.dumps(record)
        with self.assertRaises(TypeError):
            stub.provenance['nlist_offset'] = 0
        kind, value = table.lookup(STUB)
        self.assertEqual(kind, 'attributed')
        self.assertEqual(value.record(), self.expected_record())
        self.assertEqual(table.lookup(STUB + 4), ('declined', 'stub_entry_misaligned'))
        self.assertEqual(table.lookup(STUB + 8), ('declined', 'stub_entry_misaligned'))
        self.assertIsNone(table.lookup(STUB + 12))
        self.assertIsNone(table.lookup(CALLER))
        self.assertIsNone(table.lookup(GOT))
        self.assertEqual(table.counts(), {'attributed_stubs': 1, 'declined_stubs': 0,
                                          'invalid_stub_sections': 0})

    def test_fat_container_offsets(self):
        data, _ = build_stub_image()
        image = parse_macho(build_fat((data,)), limits=EXTENDED_BROAD_LIMITS)
        self.assertEqual(image.slice_offset, 0x1000)  # parser_helpers.build_fat page-aligns slices
        record = attribute_import_stubs(image).attributed[STUB].record()
        self.assertEqual(record['provenance'], provenance(container_delta=0x1000))

    def test_second_stub_and_lazy_pointer_section(self):
        # Two stubs: stub1 @0x1014 -> __got slot 1 @0x4008. Symbols: sym0 _caller0,
        # sym1/sym2 imports; nlist 0x8008..0x8038, indirect @0x8038 = [1, 2 | 1, 2].
        data, layout = build_stub_image(imports=(Import(THROWING, 2), Import('_objc_msgSend', 3)))
        self.assertEqual(layout.indirect_off, 0x8038)  # nlist 0x8008 + 3*16
        stub1 = attribute_import_stubs(image_of(data)).attributed[0x100001014].record()
        self.assertEqual((stub1['stub_index'], stub1['symbol'], stub1['symbol_index'], stub1['library_ordinal'],
                          stub1['pointer_address']), (1, '_objc_msgSend', 2, 3, 0x100004008))
        self.assertEqual(stub1['provenance'], provenance(
            stub=0x100001014, slice_file=0x1014, words=(0xF0000010, 0xF9400610, 0xD61F0200),
            stub_entry=0x8038 + 4, pointer_entry=0x8038 + 12, nlist=NLIST + 32))
        lazy, _ = build_stub_image(
            pointer_sections=(PointerSection('__la_symbol_ptr', (0,), kind=7, segment='__DATA'),),
            stubs=((0, '__la_symbol_ptr', 0),))
        record = attribute_import_stubs(image_of(lazy)).attributed[STUB].record()
        self.assertEqual((record['pointer_address'], record['pointer_section']),
                         (GOT, '__DATA,__la_symbol_ptr'))

    def test_negative_adrp_page_to_text_pointer_section(self):
        # __TEXT,__got @0x800 lies one 4 KiB page below the stub page: imm = -1.
        data, _ = build_stub_image(pointer_sections=(PointerSection('__got', (0,), segment='__TEXT'),))
        self.assertEqual(struct.unpack_from('<II', data, 0x1008), (0xF0FFFFF0, 0xF9440210))
        record = attribute_import_stubs(image_of(data)).attributed[STUB].record()
        self.assertEqual((record['pointer_address'], record['pointer_section']), (0x100000800, '__TEXT,__got'))
        self.assertEqual(record['provenance']['stub_words'][0]['word'], '0xf0fffff0')

    def test_small_base_image(self):
        data, layout = build_stub_image(base=0x100000)
        record = attribute_import_stubs(image_of(data)).attributed[0x101008].record()
        self.assertEqual(record['pointer_address'], 0x104000)

    def test_symbol_name_length_boundary(self):
        data, _ = build_stub_image()
        image = image_of(data)
        self.assertIn(STUB, attribute_import_stubs(image, limits=StubLimits(max_symbol_bytes=len(THROWING))).attributed)
        table = attribute_import_stubs(image, limits=StubLimits(max_symbol_bytes=len(THROWING) - 1))
        self.assertTrue(table.complete)
        self.assertEqual(dict(table.declined), {STUB: 'imported_symbol_name'})

    def test_stub_indirect_range_boundary_is_valid(self):
        # reserved1 = 1: 1 + 1 == nindirectsyms (2) is in range; entry 1 equals the pointer entry.
        data, layout = build_stub_image()
        data = patch(data, layout.stub_header_off + SECT_RESERVED1, '<I', 1)
        table = attribute_import_stubs(image_of(data))
        self.assertEqual(tuple(table.invalid_sections), ())
        record = table.attributed[STUB].record()
        self.assertEqual(record['provenance']['stub_indirect_entry_offset'], INDIRECT + 4)
        self.assertEqual(record['provenance']['pointer_indirect_entry_offset'], INDIRECT + 4)

    def test_admission_is_required(self):
        data, _ = build_stub_image()
        image = image_of(data)
        for candidate in (replace(image, data=data[:-1] + b'\x01'), None, data):
            with self.assertRaises(InputError) as error:
                attribute_import_stubs(candidate)
            self.assertEqual(error.exception.code, 'import_stub_admission')
        arm64e, _ = build_stub_image(cpusubtype=2)
        image = parse_macho(arm64e, limits=EXTENDED_BROAD_LIMITS)
        self.assertEqual(image.architecture, 'arm64e')
        with self.assertRaises(InputError) as error:
            attribute_import_stubs(image)
        self.assertEqual(error.exception.code, 'import_stub_admission')


class PerStubDeclineTests(unittest.TestCase):
    def assertDeclined(self, data, reason, limits=None, run_flow=True):
        image = image_of(data)
        table = attribute_import_stubs(image, **({'limits': limits} if limits else {}))
        self.assertTrue(table.complete, table.reason)
        self.assertIsNone(table.reason)
        self.assertEqual(dict(table.declined), {STUB: reason})
        self.assertNotIn(STUB, table.attributed)
        self.assertEqual(table.lookup(STUB), ('declined', reason))
        self.assertEqual(table.counts()['declined_stubs'], 1)
        if run_flow:
            report = flow(image)
            self.assertTrue(report['import_stubs_complete'])
            self.assertEqual(report['import_stub_counts'], zero_import_counts(declined_stubs=1, declined_stub_calls=1))
            self.assertEqual(report['selected_call_candidates'], 0)
            self.assertEqual(report['observed_call_instructions'], 1)
            self.assertEqual(report['calls'], [])
            self.assertTrue(report['call_details_complete'])

    def base(self, **kwargs):
        return build_stub_image(**kwargs)

    def with_words(self, w0=None, w1=None, w2=None):
        data, layout = self.base()
        for k, word in enumerate((w0, w1, w2)):
            if word is not None:
                data = patch(data, layout.stub_word_off(0, k), '<I', word)
        return data

    def test_stub_instruction_pattern(self):
        cases = {
            'adrp_x17': (adrp(X17, STUB, GOT), None, None),
            'adr_x16': (0x10000010, None, None),
            'ldr_rt_x17': (None, ldr_x_uimm(X17, X16, 0), None),
            'ldr_rn_x17': (None, ldr_x_uimm(X16, X17, 0), None),
            'ldr_literal': (None, ldr_x_literal(X16, 8), None),
            'ldr_w_register': (None, 0xB9400210, None),
            'br_x17': (None, None, br(X17)),
            'braaz_x16': (None, None, BRAAZ_X16),
            'braa_x16_x17': (None, None, BRAA_X16_X17),
            'braa_x16_sp_style': (None, None, 0xD71F0A1F),
            'blr_x16': (None, None, 0xD63F0200),
        }
        for name, words in cases.items():
            with self.subTest(name):
                self.assertDeclined(self.with_words(*words), 'stub_instruction_pattern')

    def test_pattern_precedes_later_failures(self):
        data, layout = self.base()
        data = patch(data, layout.stub_word_off(0, 2), '<I', BRAAZ_X16)
        data = patch(data, layout.indirect_entry_off(0), '<I', 0x80000000)
        self.assertDeclined(data, 'stub_instruction_pattern')

    def test_stub_pointer_unmapped(self):
        # P in the gap after __got (0x100004800), P inside __text (not a pointer
        # section), and P one slot past the end of a valid __got.
        self.assertDeclined(self.with_words(None, ldr_x_uimm(X16, X16, 0x800)), 'stub_pointer_unmapped')
        self.assertDeclined(self.with_words(adrp(X16, STUB, CALLER), ldr_x_uimm(X16, X16, 0)),
                            'stub_pointer_unmapped')
        self.assertDeclined(self.with_words(None, ldr_x_uimm(X16, X16, 8)), 'stub_pointer_unmapped')

    def test_stub_pointer_misaligned_within_section(self):
        # __got at 0x100004004 (align 2), two slots -> [0x4004, 0x4014). The stub
        # loads P = 0x100004008, inside the section at offset 4.
        data, layout = self.base(
            pointer_sections=(PointerSection('__got', (0, 0), misalign=4),),
            stub_words={0: (adrp(X16, STUB, GOT), ldr_x_uimm(X16, X16, 8), BR_X16)})
        self.assertEqual(layout.pointers['__got']['addr'], 0x100004004)
        self.assertDeclined(data, 'stub_pointer_unmapped')

    def test_stub_pointer_negative_page(self):
        # base 0x100000: stub 0x101008, page 0x101000; ADRP imm -0x102 -> page -0x1000.
        data, layout = self.base(base=0x100000)
        data = patch(data, layout.stub_word_off(0, 0), '<I', adrp_imm(X16, -0x102))
        image = image_of(data)
        table = attribute_import_stubs(image)
        self.assertEqual(dict(table.declined), {0x101008: 'stub_pointer_unmapped'})

    def test_stub_pointer_section_invalid(self):
        data, layout = self.base()
        got = layout.pointers['__got']['header_off']
        # reserved1 + size//8 > nindirectsyms
        self.assertDeclined(patch(data, got + SECT_RESERVED1, '<I', layout.nindirect), 'stub_pointer_section_invalid')
        # size % 8 != 0 (12): P = start, P + 8 <= end, offset 0
        self.assertDeclined(patch(data, got + SECT_SIZE, '<Q', 12), 'stub_pointer_section_invalid')

    def test_indirect_symbol_local_or_absolute(self):
        data, layout = self.base()
        pointer_entry = layout.indirect_entry_off(layout.pointers['__got']['reserved1'])
        for name, offset, value in (('stub_local', layout.indirect_entry_off(0), 0x80000000),
                                    ('stub_abs', layout.indirect_entry_off(0), 0x40000000),
                                    ('stub_both', layout.indirect_entry_off(0), 0xC0000000),
                                    ('pointer_local', pointer_entry, 0x80000000),
                                    ('pointer_abs', pointer_entry, 0x40000000)):
            with self.subTest(name):
                self.assertDeclined(patch(data, offset, '<I', value), 'indirect_symbol_local_or_absolute')
        both = patch(patch(data, layout.indirect_entry_off(0), '<I', 0x80000000), pointer_entry, '<I', 0x80000000)
        self.assertDeclined(both, 'indirect_symbol_local_or_absolute')

    def test_stub_pointer_binding_mismatch(self):
        data, layout = self.base()
        pointer_entry = layout.indirect_entry_off(layout.pointers['__got']['reserved1'])
        self.assertDeclined(patch(data, pointer_entry, '<I', 0), 'stub_pointer_binding_mismatch')
        # Both indices valid imports, but different.
        data, layout = self.base(imports=(Import(THROWING, 2), Import(THROWING2, 2)))
        pointer_entry = layout.indirect_entry_off(layout.pointers['__got']['reserved1'])
        image = image_of(patch(data, pointer_entry, '<I', 2))
        table = attribute_import_stubs(image)
        self.assertEqual(dict(table.declined), {STUB: 'stub_pointer_binding_mismatch'})
        self.assertIn(0x100001014, table.attributed)

    def test_indirect_symbol_index_range(self):
        data, layout = self.base()
        pointer_entry = layout.indirect_entry_off(layout.pointers['__got']['reserved1'])
        for value in (layout.nsyms, 0x3FFFFFFF):
            with self.subTest(value):
                patched = patch(patch(data, layout.indirect_entry_off(0), '<I', value), pointer_entry, '<I', value)
                self.assertDeclined(patched, 'indirect_symbol_index_range')

    def test_indirect_symbol_not_undefined_range(self):
        data, layout = self.base()
        pointer_entry = layout.indirect_entry_off(layout.pointers['__got']['reserved1'])
        # Both entries name the defined external caller symbol (index 0).
        patched = patch(patch(data, layout.indirect_entry_off(0), '<I', 0), pointer_entry, '<I', 0)
        self.assertDeclined(patched, 'indirect_symbol_not_undefined_range')
        # nundefsym = 0 leaves the import (index 1) outside the undefined range.
        self.assertDeclined(patch(data, layout.dysymtab_word_off(5), '<I', 0), 'indirect_symbol_not_undefined_range')

    def test_imported_symbol_not_undefined_external(self):
        data, layout = self.base()
        nlist = layout.nlist_off(layout.import_symbol_index(0))
        got_section = layout.section_index[('__DATA_CONST', '__got')]
        self.assertEqual(got_section, 3)
        cases = {
            'defined_in_got': [(NL_TYPE, '<B', 0x0F), (NL_SECT, '<B', got_section), (NL_VALUE, '<Q', GOT)],
            'nonzero_n_sect': [(NL_SECT, '<B', 1)],
            'stab_bit': [(NL_TYPE, '<B', 0x21)],
            'not_external': [(NL_TYPE, '<B', 0x00)],
            'absolute_type': [(NL_TYPE, '<B', 0x03)],
            'nonzero_value': [(NL_VALUE, '<Q', 8)],
        }
        for name, fields in cases.items():
            with self.subTest(name):
                patched = data
                for field_offset, fmt, value in fields:
                    patched = patch(patched, nlist + field_offset, fmt, value)
                self.assertDeclined(patched, 'imported_symbol_not_undefined_external')
        # n_desc carries only the recorded ordinal; changing it is not a decline.
        changed = patch(data, nlist + NL_DESC, '<H', 0x0500)
        record = attribute_import_stubs(image_of(changed)).attributed[STUB].record()
        self.assertEqual(record['library_ordinal'], 5)

    def test_imported_symbol_name(self):
        data, layout = self.base()
        nlist = layout.nlist_off(layout.import_symbol_index(0))
        with self.subTest('strx_zero'):
            self.assertDeclined(patch(data, nlist + NL_STRX, '<I', 0), 'imported_symbol_name')
        with self.subTest('empty_name'):
            # strx 9 is the NUL terminating '_caller0' (strx 1, 8 bytes).
            self.assertDeclined(patch(data, nlist + NL_STRX, '<I', 9), 'imported_symbol_name')
        with self.subTest('unterminated_at_table_end'):
            # strsize ends exactly at the import's terminator (excluded).
            strsize = layout.strx[1] + len(THROWING)
            self.assertDeclined(patch(data, layout.symtab_cmd_off + 20, '<I', strsize), 'imported_symbol_name')
        with self.subTest('non_ascii'):
            other, _ = self.base(imports=(Import(b'_$s4T\xc3\xa9st3fooyS2iKF', 2),))
            self.assertDeclined(other, 'imported_symbol_name')
        with self.subTest('over_name_limit'):
            self.assertDeclined(data, 'imported_symbol_name', limits=StubLimits(max_symbol_bytes=8), run_flow=False)


class SectionLevelTests(unittest.TestCase):
    def assertInvalidSection(self, data, reason, start=STUB, end=STUB + 12, *, lookup=True):
        image = image_of(data)
        table = attribute_import_stubs(image)
        self.assertTrue(table.complete, table.reason)
        self.assertEqual(tuple(tuple(x) for x in table.invalid_sections), ((start, end, reason),))
        self.assertEqual(table.stub_sections, 1)
        self.assertEqual(dict(table.attributed), {})
        self.assertEqual(dict(table.declined), {})
        self.assertEqual(table.counts(), {'attributed_stubs': 0, 'declined_stubs': 0, 'invalid_stub_sections': 1})
        if lookup:
            self.assertEqual(table.lookup(start), ('declined', reason))
            report = flow(image)
            self.assertEqual(report['import_stub_counts'],
                             zero_import_counts(invalid_stub_sections=1, declined_stub_calls=1))
            self.assertEqual(report['calls'], [])
        return table

    def test_stub_section_segment(self):
        # Stubs in their own r-x segment at the next 16 KiB page: 0x100004000.
        data, layout = build_stub_image(stub_segment='__TEXT_EXEC')
        self.assertEqual(layout.stubs_addr, 0x100004000)
        self.assertInvalidSection(data, 'stub_section_segment', 0x100004000, 0x10000400C)
        # Segment check precedes reserved2.
        data, layout = build_stub_image(stub_segment='__TEXT_EXEC', stub_reserved2=16)
        self.assertInvalidSection(data, 'stub_section_segment', 0x100004000, 0x10000400C)

    def test_stub_size_unsupported(self):
        data, _ = build_stub_image(stub_reserved2=16)
        self.assertInvalidSection(data, 'stub_size_unsupported')
        data, layout = build_stub_image()
        self.assertInvalidSection(patch(data, layout.stub_header_off + SECT_RESERVED2, '<I', 0), 'stub_size_unsupported')

    def test_stub_section_extent(self):
        data, layout = build_stub_image()
        self.assertInvalidSection(patch(data, layout.stub_header_off + SECT_SIZE, '<Q', 8),
                                  'stub_section_extent', STUB, STUB + 8)
        # An empty stub section contains no address.
        table = self.assertInvalidSection(patch(data, layout.stub_header_off + SECT_SIZE, '<Q', 0),
                                          'stub_section_extent', STUB, STUB, lookup=False)
        self.assertIsNone(table.lookup(STUB))

    def test_stub_indirect_range(self):
        data, layout = build_stub_image()
        self.assertInvalidSection(patch(data, layout.stub_header_off + SECT_RESERVED1, '<I', layout.nindirect),
                                  'stub_indirect_range')

    def test_extent_precedes_indirect_range(self):
        data, layout = build_stub_image()
        data = patch(data, layout.stub_header_off + SECT_RESERVED1, '<I', layout.nindirect)
        self.assertInvalidSection(patch(data, layout.stub_header_off + SECT_SIZE, '<Q', 8),
                                  'stub_section_extent', STUB, STUB + 8)

    def test_stub_entry_misaligned_call(self):
        data, _ = build_stub_image(callers=((('bl', ('stub', 0, 4)), RET),))
        image = image_of(data)
        table = attribute_import_stubs(image)
        self.assertIn(STUB, table.attributed)
        self.assertEqual(table.lookup(STUB + 4), ('declined', 'stub_entry_misaligned'))
        report = flow(image)
        self.assertEqual(report['import_stub_counts'], zero_import_counts(attributed_stubs=1, declined_stub_calls=1))
        self.assertEqual(report['calls'], [])

    def test_stub_limit_counts_only_valid_sections(self):
        data, _ = build_stub_image(imports=(Import(THROWING, 2), Import(THROWING2, 2)), stub_reserved2=16)
        table = attribute_import_stubs(image_of(data), limits=StubLimits(max_stubs=1))
        self.assertTrue(table.complete)
        self.assertEqual(table.counts()['invalid_stub_sections'], 1)


class TableIncompleteTests(unittest.TestCase):
    def assertIncomplete(self, table, reason, stubs=(STUB,)):
        self.assertFalse(table.complete)
        self.assertEqual(table.reason, reason)
        self.assertEqual(dict(table.attributed), {})
        self.assertEqual(dict(table.declined), {})
        for stub in stubs:
            self.assertIsNone(table.lookup(stub))
            self.assertIsNone(table.lookup(stub + 4))

    def assertFlowIncomplete(self, image, reason):
        report = flow(image)
        self.assertFalse(report['import_stubs_complete'])
        self.assertEqual(report['import_stub_reason'], reason)
        self.assertFalse(report['call_details_complete'])
        self.assertEqual(report['calls'], [])
        self.assertEqual(report['selected_call_candidates'], 0)
        self.assertEqual(report['import_stub_counts'], zero_import_counts())
        self.assertEqual(report['limitations'], OLD_LIMITATIONS + ['imported_callees_attribution_only'])

    def two_stub_image(self):
        data, _ = build_stub_image(imports=(Import(THROWING, 2), Import(THROWING2, 2)))
        return image_of(data)

    def test_stub_limit(self):
        image = self.two_stub_image()
        self.assertIncomplete(attribute_import_stubs(image, limits=StubLimits(max_stubs=1)), 'stub_limit',
                              (STUB, 0x100001014))
        self.assertTrue(attribute_import_stubs(image, limits=StubLimits(max_stubs=2)).complete)

    def test_indirect_symbol_limit(self):
        image = self.two_stub_image()  # nindirectsyms = 4
        self.assertIncomplete(attribute_import_stubs(image, limits=StubLimits(max_indirect_symbols=3)),
                              'indirect_symbol_limit')
        self.assertTrue(attribute_import_stubs(image, limits=StubLimits(max_indirect_symbols=4)).complete)

    def test_load_command_and_section_limits(self):
        data, layout = build_stub_image()
        image = image_of(data)
        self.assertEqual((layout.ncmds, layout.nsections), (8, 3))
        self.assertIncomplete(attribute_import_stubs(image, limits=StubLimits(max_load_commands=7)),
                              'load_command_limit')
        self.assertTrue(attribute_import_stubs(image, limits=StubLimits(max_load_commands=8)).complete)
        self.assertIncomplete(attribute_import_stubs(image, limits=StubLimits(max_sections=2)), 'section_limit')
        self.assertTrue(attribute_import_stubs(image, limits=StubLimits(max_sections=3)).complete)

    def test_stub_work_limit(self):
        data, _ = build_stub_image()
        self.assertIncomplete(attribute_import_stubs(image_of(data), limits=StubLimits(max_work=1)),
                              'stub_work_limit')

    def test_indirect_symbol_table_missing(self):
        data, _ = build_stub_image(include_dysymtab=False)
        image = image_of(data)  # parse_macho admits LC_SYMTAB without LC_DYSYMTAB
        self.assertIncomplete(attribute_import_stubs(image), 'indirect_symbol_table_missing')
        self.assertFlowIncomplete(image, 'indirect_symbol_table_missing')

    def test_default_stub_limit_in_flow(self):
        # 65537 stubs > StubLimits().max_stubs (65536); all load __got slot 0.
        count = 65537
        data, layout = build_stub_image(stubs=((0, '__got', 0),) * count)
        image = image_of(data)
        self.assertIncomplete(attribute_import_stubs(image), 'stub_limit', (STUB,))
        self.assertFlowIncomplete(image, 'stub_limit')


class NoStubTests(unittest.TestCase):
    def test_no_stub_sections(self):
        for kwargs in ({}, {'include_dysymtab': False}):
            with self.subTest(kwargs):
                data, _ = build_stub_image(callers=((RET,),), include_stubs=False, **kwargs)
                image = image_of(data)
                table = attribute_import_stubs(image)
                self.assertTrue(table.complete)
                self.assertIsNone(table.reason)
                self.assertEqual((dict(table.attributed), dict(table.declined), tuple(table.invalid_sections),
                                  table.stub_sections), ({}, {}, (), 0))
                self.assertEqual(table.counts(), {'attributed_stubs': 0, 'declined_stubs': 0,
                                                  'invalid_stub_sections': 0})
                report = flow(image)
                self.assertTrue(report['import_stubs_complete'])
                self.assertIsNone(report['import_stub_reason'])
                self.assertEqual(report['import_stub_counts'], zero_import_counts())
                self.assertTrue(report['call_details_complete'])


class ImportFlowTests(unittest.TestCase):
    def expected_admission(self, *, symbol=THROWING, call_kind='bl', call_pc=CALLER, caller_start=CALLER,
                           declaration=None):
        if declaration is None:
            declaration = {'status': 'syntax_admitted',
                           'identity': listify(asdict(parse_import_declaration(symbol).identity)), 'reason': None}
        return {
            'model_version': 'swift-broad-import-callsite-v1',
            'status': 'unresolved', 'reason': 'imported_callee_abi_unqualified',
            'call_kind': call_kind, 'call_pc': call_pc, 'caller_start': caller_start,
            'callee_stub_pc': STUB, 'symbol': symbol, 'library_ordinal': 2,
            'declaration': declaration,
            'import_provenance': {**provenance(), 'stub_model': STUB_MODEL, 'stub_section': '__TEXT,__stubs',
                                  'stub_index': 0, 'symbol_index': 1, 'pointer_address': GOT,
                                  'pointer_section': '__DATA_CONST,__got'},
            'details_complete': True, 'call_return_proven': False,
            'syntactic_call_target_admitted': False, 'import_attribution_admitted': True,
        }

    def assertImportRow(self, row, *, caller_pc, call_pc, **kwargs):
        self.assertEqual(set(row), {'caller_pc', 'call_pc', 'candidate', 'validation', 'admission'})
        self.assertEqual((row['caller_pc'], row['call_pc'], row['candidate'], row['validation']),
                         (hex(caller_pc), hex(call_pc), None, None))
        admission = dict(row['admission'])
        work = admission.pop('work_steps')
        self.assertIs(type(work), int)
        self.assertGreaterEqual(work, 0)
        self.assertEqual(admission, self.expected_admission(call_pc=call_pc, caller_start=caller_pc, **kwargs))

    def test_profile_constants(self):
        from airs.swift_broad_profiles import BROAD_IMPORTS_MODEL, BROAD_IMPORTS_PROFILE
        self.assertEqual((BROAD_IMPORTS_PROFILE, BROAD_IMPORTS_MODEL), (PROFILE, MODEL))
        self.assertEqual(IMPORTS_BROAD_LIMITS, EXTENDED_BROAD_LIMITS)
        self.assertEqual(PROFILE_LIMITS[PROFILE], EXTENDED_BROAD_LIMITS)

    def test_throwing_import_bl_is_selected(self):
        data, _ = build_stub_image()
        report = flow(image_of(data))
        self.assertEqual((report['model_version'], report['profile']), (MODEL, PROFILE))
        self.assertEqual(report['import_stub_model'], STUB_MODEL)
        self.assertTrue(report['import_stubs_complete'])
        self.assertIsNone(report['import_stub_reason'])
        self.assertEqual(report['import_stub_counts'], zero_import_counts(attributed_stubs=1, selected_import_calls=1))
        self.assertEqual(report['limitations'], OLD_LIMITATIONS + ['imported_callees_attribution_only'])
        self.assertEqual((report['scanned_words'], report['observed_call_instructions'],
                          report['selected_call_candidates'], report['omitted_calls']), (2, 1, 1, 0))
        self.assertTrue(report['word_scan_complete'])
        self.assertTrue(report['call_details_complete'])
        self.assertTrue(report['outcome_witnesses_complete'])
        self.assertEqual(report['status_counts'], {'unresolved': 1})
        self.assertEqual(report['reason_counts'], {'imported_callee_abi_unqualified': 1})
        self.assertEqual(len(report['calls']), 1)
        self.assertImportRow(report['calls'][0], caller_pc=CALLER, call_pc=CALLER)
        declaration = json.loads(json.dumps(report['calls'][0]['admission']['declaration']))
        self.assertEqual(declaration['status'], 'syntax_admitted')
        self.assertIs(declaration['identity']['throws'], True)
        self.assertEqual(declaration['identity']['symbol'], '_$s4Test3fooyS2iKF')
        self.assertEqual(declaration['identity']['entity'], 'function')
        self.assertEqual(declaration['identity']['syntax_model'], 'swift-import-declaration-syntax-v1')
        from airs.report import dumps
        json.loads(dumps(report))

    def test_tail_branch_to_stub(self):
        # caller0: NOP; B stub0 (B at 0x100001004, stub at 0x100001008).
        data, _ = build_stub_image(callers=((NOP, ('b', ('stub', 0))),))
        self.assertEqual(struct.unpack_from('<I', data, 0x1004)[0], 0x14000001)
        report = flow(image_of(data))
        self.assertEqual(report['import_stub_counts'], zero_import_counts(attributed_stubs=1, selected_import_calls=1))
        self.assertImportRow(report['calls'][0], caller_pc=CALLER, call_pc=CALLER + 4, call_kind='b')

        declaration = json.loads(json.dumps(report['calls'][0]['admission']['declaration']))
        self.assertEqual(declaration['status'], 'syntax_admitted')
        self.assertIs(declaration['identity']['throws'], True)
        self.assertEqual(declaration['identity']['symbol'], '_$s4Test3fooyS2iKF')
        self.assertEqual(declaration['identity']['entity'], 'function')
        self.assertEqual(declaration['identity']['syntax_model'], 'swift-import-declaration-syntax-v1')

    def test_second_caller_start(self):
        # caller0 @0x1000: RET; caller1 @0x1004: NOP; BL stub0; RET -> stub @0x1010.
        data, layout = build_stub_image(callers=((RET,), (NOP, ('bl', ('stub', 0)), RET)))
        self.assertEqual((layout.caller_addrs, layout.stubs_addr), ([CALLER, CALLER + 4], 0x100001010))
        row = flow(image_of(data))['calls'][0]
        self.assertEqual((row['caller_pc'], row['call_pc']), ('0x100001004', '0x100001008'))
        self.assertEqual((row['admission']['caller_start'], row['admission']['call_pc'],
                          row['admission']['callee_stub_pc'], row['admission']['call_kind']),
                         (CALLER + 4, CALLER + 8, 0x100001010, 'bl'))

    def test_non_swift_import_not_selected(self):
        data, _ = build_stub_image(imports=(Import('_objc_msgSend', 2),))
        image = image_of(data)
        self.assertEqual(attribute_import_stubs(image).attributed[STUB].symbol, '_objc_msgSend')
        report = flow(image)
        self.assertEqual(report['import_stub_counts'], zero_import_counts(attributed_stubs=1, non_swift_import_calls=1))
        self.assertEqual((report['observed_call_instructions'], report['selected_call_candidates']), (1, 0))
        self.assertEqual(report['calls'], [])

    def test_non_throwing_swift_import_not_selected(self):
        parsed = parse_import_declaration(NON_THROWING)
        self.assertTrue(parsed.supported)
        self.assertFalse(parsed.identity.throws)
        data, _ = build_stub_image(imports=(Import(NON_THROWING, 2),))
        report = flow(image_of(data))
        self.assertEqual(report['import_stub_counts'],
                         zero_import_counts(attributed_stubs=1, non_throwing_swift_import_calls=1))
        self.assertEqual((report['observed_call_instructions'], report['selected_call_candidates']), (1, 0))
        self.assertEqual(report['calls'], [])

    def test_unresolved_swift_import_is_selected(self):
        self.assertFalse(parse_import_declaration(UNRESOLVED).supported)
        data, _ = build_stub_image(imports=(Import(UNRESOLVED, 2),))
        report = flow(image_of(data))
        self.assertEqual(report['import_stub_counts'], zero_import_counts(attributed_stubs=1, selected_import_calls=1))
        row = report['calls'][0]
        declaration = row['admission']['declaration']
        self.assertEqual((declaration['status'], declaration['identity']), ('syntax_unresolved', None))
        self.assertIs(type(declaration['reason']), str)
        self.assertTrue(declaration['reason'])
        self.assertImportRow(row, caller_pc=CALLER, call_pc=CALLER, symbol=UNRESOLVED, declaration=declaration)

    def test_non_stub_non_function_target_is_skipped(self):
        # caller0: BL caller1+4 (inside caller1, not a start, not a stub); RET.
        data, _ = build_stub_image(callers=((('bl', CALLER + 12), RET), (NOP, NOP, RET)))
        report = flow(image_of(data))
        self.assertEqual(report['import_stub_counts'], zero_import_counts(attributed_stubs=1))
        self.assertEqual((report['observed_call_instructions'], report['selected_call_candidates']), (1, 0))

    def test_profile_isolation(self):
        data, _ = build_stub_image()
        image = image_of(data)
        imports = flow(image)
        for profile in ('broad-v1', 'broad-large-v1', 'broad-extended-v1'):
            with self.subTest(profile):
                old = flow(image, profile=profile)
                self.assertFalse(IMPORT_KEYS & set(old))
                self.assertEqual(old['limitations'], OLD_LIMITATIONS)
                self.assertEqual(old['calls'], [])
                self.assertEqual(old['selected_call_candidates'], 0)
        extended = flow(image, profile='broad-extended-v1')
        self.assertEqual(set(imports) - set(extended), IMPORT_KEYS)
        self.assertEqual(set(extended) - set(imports), set())
        for key in ('scanned_words', 'observed_call_instructions', 'word_scan_complete', 'identity'):
            self.assertEqual(imports[key], extended[key], key)

    def test_per_function_retention_cap(self):
        # caller0: BL stub0; BL stub1; RET  (12 bytes; stubs at 0x10000100c, 0x100001018).
        data, _ = build_stub_image(callers=((('bl', ('stub', 0)), ('bl', ('stub', 1)), RET),),
                                   imports=(Import(THROWING, 2), Import(THROWING2, 2)))
        image = image_of(data)
        full = flow(image)
        self.assertEqual(len(full['calls']), 2)
        self.assertEqual(full['import_stub_counts']['selected_import_calls'], 2)
        report = flow(image, replace(IMPORTS_BROAD_LIMITS, max_observations_per_function=1))
        self.assertEqual(len(report['calls']), 1)
        self.assertEqual(report['calls'][0]['admission']['symbol'], THROWING)
        self.assertEqual(report['calls'][0]['admission']['callee_stub_pc'], 0x10000100c)
        self.assertEqual(report['omitted_calls'], 1)
        self.assertFalse(report['call_details_complete'])
        self.assertFalse(report['outcome_witnesses_complete'])
        self.assertEqual(report['selected_call_candidates'], 2)
        self.assertEqual(report['import_stub_counts']['selected_import_calls'], 2)
        self.assertEqual(report['status_counts'], {'unresolved': 1})

    def test_cli_json_and_text(self):
        from airs.cli import main
        data, _ = build_stub_image()
        flags = ['--swift-profile', PROFILE, '--include-outcome-witnesses', '--include-error-regions',
                 '--validate-region-entries', '--include-structured-presentation']
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'imports.macho'
            path.write_bytes(data)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['swift-error-flow', str(path), *flags])
            self.assertEqual(code, 0)
            report = json.loads(out.getvalue())
            self.assertEqual(report['profile'], PROFILE)
            self.assertEqual(len(report['calls']), 1)
            self.assertEqual(report['calls'][0]['admission']['symbol'], THROWING)
            self.assertEqual(report['calls'][0]['admission']['callee_stub_pc'], STUB)
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = main(['swift-error-flow', str(path), *flags, '--format', 'text'])
            self.assertEqual(code, 0)
            text = out.getvalue()
            self.assertIn('broad-imports-v1', text)
            self.assertIn(THROWING, text)
            self.assertIn('imported_callee_abi_unqualified', text)


class StubSectionRelocationTests(unittest.TestCase):
    """Implementer-added rule: relocated stub words are never decoded."""

    def test_stub_section_relocations_decline_the_section(self):
        data, layout = build_stub_image()
        # Section header: reloff at +56, nreloc at +60 (Mach-O section_64).
        # One 8-byte relocation record placed over the symbol table bytes, inside the file.
        data = patch(data, layout.stub_header_off + 56, '<II', layout.symoff, 1)
        image = image_of(data)
        table = attribute_import_stubs(image)
        self.assertTrue(table.complete, table.reason)
        self.assertEqual(tuple(tuple(x) for x in table.invalid_sections),
                         ((layout.stubs_addr, layout.stubs_addr + 12, 'stub_section_relocations'),))
        self.assertEqual(dict(table.attributed), {})
        self.assertEqual(dict(table.declined), {})
        self.assertEqual(table.lookup(layout.stubs_addr), ('declined', 'stub_section_relocations'))
        # The segment check still comes first.
        data, layout = build_stub_image(stub_segment='__TEXT_EXEC')
        data = patch(data, layout.stub_header_off + 56, '<II', layout.symoff, 1)
        table = attribute_import_stubs(image_of(data))
        self.assertEqual(table.invalid_sections[0][2], 'stub_section_segment')


class RawSectionMetadataTests(unittest.TestCase):
    """Implementer-added after review: the parser admits a non-ASCII section name
    that the stub model's strict raw decode does not match."""

    def test_non_ascii_pointer_section_name_makes_the_table_incomplete(self):
        data, layout = build_stub_image()
        name = data.find(b'__got\0', 0, layout.symoff)
        self.assertGreater(name, 0)
        data = patch(data, name + 4, '<B', 0xff)  # '__go\xff'
        image = image_of(data)
        table = attribute_import_stubs(image)
        self.assertFalse(table.complete)
        self.assertEqual(table.reason, 'raw_section_metadata_mismatch')
        self.assertEqual(dict(table.attributed), {})
        self.assertIsNone(table.lookup(layout.stubs_addr))
        # The full flow refuses this image earlier, in metadata admission.
        with self.assertRaises(InputError) as caught:
            flow(image)
        self.assertEqual(caught.exception.code, 'swift_broad_metadata_admission')
        self.assertIn('section_name_encoding', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
