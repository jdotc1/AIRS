"""Owned synthetic tests for airs.macho_got (arm64-got-blr-two-source-binding-v1).

Expectations derive from the GOT attribution contract
and from the independent byte layout in got_image_helpers (documented there).
Offsets below are hand-derived from that layout, never copied from
implementation output. Focused refusal tests use positive controls and
single-field patches where parser admission permits them. No image is executed.
"""
import ast
import struct
import sys
import unittest
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parent))

from parser_helpers import build_fat  # noqa: E402
from got_image_helpers import (  # noqa: E402
    BASE, CF_COUNT, CF_IMPORTS, CF_IMPORTS_FORMAT, CF_STARTS, CF_SYMBOLS, CF_SYMBOLS_FORMAT, CF_VERSION,
    DEFAULT_DYLIBS, GotImport, HEADER_FLAGS, LC_LAZY_LOAD_DYLIB, LC_LOAD_DYLINKER, LC_LOAD_UPWARD_DYLIB,
    LC_LOAD_WEAK_DYLIB, LC_REEXPORT_DYLIB, MH_TWOLEVEL, NL_DESC, NL_SECT, NL_STRX, NL_TYPE, NL_VALUE, NOP,
    PtrSection, RET, SECT_RESERVED1, SS_FORMAT, SS_MAX_VALID, SS_PAGE_COUNT, SS_PAGE_SIZE,
    SS_SEGMENT_OFFSET, SS_SIZE, THROWING, X16, X17, add_w_imm, add_x_imm, addg, adds_x_imm, adr, adrp,
    adrp_imm, b, bcond, bind_raw, bl, blr, blraaz, br, build_got_image, cbnz_w, cbz, got_call, ldr_w_uimm,
    ldr_x_literal, ldr_x_uimm, ldur_x, mov_w, mov_x, movk_w, movk_x, movn_w, movn_x, movz_w, movz_x,
    orr_x_shifted, patch, rebase_raw, sub_w_imm, sub_x_imm, tbnz, tbz, u32, u64,
)
from airs.macho import parse_macho  # noqa: E402
from airs.types import InputError  # noqa: E402
from airs.swift_broad_flow import EXTENDED_BROAD_LIMITS  # noqa: E402
from airs.macho_got import (  # noqa: E402
    CHAINED_FIXUPS_MODEL, GOT_MODEL, ROW_MODEL, WINDOW_MODEL, GotBinding, GotCall, GotLimits, GotTable,
    attribute_got_bindings,
)

# Hand layout of the default image (got_image_helpers docstring): caller0 @0x1000:
# ADRP x16, page(0x100004000); LDR x16, [x16, #0]; BLR x16; RET. __DATA_CONST @0x4000
# holds __got (one slot). __LINKEDIT @0x8000: the chained-fixups blob first (header
# 0x00, starts_in_image 0x20 with seg_count 4, __DATA_CONST record 0x38, imports 0x50,
# symbol pool 0x54 = "\0<import>\0"), then function starts, nlist (sym0 _caller0,
# sym1 import), the indirect table and the strings.
CALLER = 0x100001000
ADRP_PC, LDR_PC, BLR_PC = CALLER, CALLER + 4, CALLER + 8
GOT = 0x100004000
BLOB = 0x8000
SWIFT_CORE = DEFAULT_DYLIBS[1]


def image_of(data):
    return parse_macho(data, limits=EXTENDED_BROAD_LIMITS)


def table_of(data, limits=None):
    image = image_of(data)
    return image, (attribute_got_bindings(image) if limits is None else attribute_got_bindings(image, limits=limits))


def function_at(image, start):
    return next(f for f in image.functions if f.start == start)


def classify(data, pc=BLR_PC, caller=CALLER, limits=None):
    image, table = table_of(data, limits)
    return table.classify(function_at(image, caller), pc)


def default_call():
    return got_call() + (RET,)


class GotTestCase(unittest.TestCase):
    def assertAttributed(self, data, pc=BLR_PC, caller=CALLER, limits=None):
        found = classify(data, pc, caller, limits)
        self.assertIsNotNone(found)
        self.assertEqual(found[0], 'attributed', found)
        self.assertIs(type(found[1]), GotCall)
        return found[1]

    def assertDeclined(self, data, reason, pc=BLR_PC, caller=CALLER, limits=None):
        self.assertEqual(classify(data, pc, caller, limits), ('declined', reason))

    def assertSlotDeclined(self, data, reason, slot=GOT, limits=None, pc=BLR_PC):
        """Slot-level decline: the table stays complete and decoded, the slot and its call decline."""
        image, table = table_of(data, limits)
        self.assertTrue(table.complete, table.reason)
        self.assertIsNone(table.reason)
        self.assertEqual(table.chained_fixups_status, 'decoded')
        self.assertNotIn(slot, table.bindings)
        self.assertEqual(table.declined_slots.get(slot), reason)
        self.assertEqual(table.classify(function_at(image, CALLER), pc), ('declined', reason))
        return table

    def assertImageDeclined(self, data, reason, limits=None):
        """Image-level status (6.2): complete, status is the reason, every slot declines with it."""
        image, table = table_of(data, limits)
        self.assertTrue(table.complete, table.reason)
        self.assertIsNone(table.reason)
        self.assertEqual(table.chained_fixups_status, reason)
        self.assertEqual(dict(table.bindings), {})
        self.assertTrue(table.declined_slots)
        self.assertEqual(set(table.declined_slots.values()), {reason})
        self.assertEqual(table.classify(function_at(image, CALLER), BLR_PC), ('declined', reason))
        return table

    def assertIncomplete(self, data, reason, limits=None):
        """Table-level reason (6.1): complete False, both maps empty, classify None everywhere."""
        image, table = table_of(data, limits)
        self.assertFalse(table.complete)
        self.assertEqual(table.chained_fixups_status, 'not_decoded')
        self.assertEqual(table.reason, reason)
        self.assertEqual(dict(table.bindings), {})
        self.assertEqual(dict(table.declined_slots), {})
        for function in image.functions:
            for pc in range(function.start, function.end, 4):
                self.assertIsNone(table.classify(function, pc))
        return table


class IdentityAndAdmissionTests(GotTestCase):
    def test_model_identities(self):
        self.assertEqual(GOT_MODEL, 'arm64-got-blr-two-source-binding-v1')
        self.assertEqual(CHAINED_FIXUPS_MODEL, 'macho-chained-fixups-64-bind-v1')
        self.assertEqual(WINDOW_MODEL, 'adrp-ldr-blr-straight-line-window-v1')
        self.assertEqual(ROW_MODEL, 'swift-broad-got-callsite-v1')
        data, _ = build_got_image()
        _, table = table_of(data)
        self.assertIs(type(table), GotTable)
        self.assertEqual(table.model, GOT_MODEL)

    def test_limit_defaults(self):
        self.assertEqual(GotLimits(), GotLimits(
            max_load_commands=4096, max_sections=4096, max_indirect_symbols=1_048_576, max_symbol_bytes=4096,
            max_got_slots=1_048_576, max_chained_imports=1_048_576, max_chain_members=4_000_000,
            max_window_gap=3, max_screen_words=4_000_000, max_data_in_code_entries=65536,
            max_work=16_000_000))

    def test_invalid_limit_fields(self):
        for name in ('max_load_commands', 'max_sections', 'max_indirect_symbols', 'max_symbol_bytes',
                     'max_got_slots', 'max_chained_imports', 'max_chain_members', 'max_window_gap',
                     'max_screen_words', 'max_data_in_code_entries', 'max_work'):
            for value in (-1, 1.0, '1', None):
                with self.subTest(name=name, value=value), self.assertRaises(InputError) as caught:
                    GotLimits(**{name: value})
                self.assertEqual(caught.exception.code, 'invalid_limits')
            GotLimits(**{name: 0})  # zero is a nonnegative int

    def test_limits_object_type(self):
        data, _ = build_got_image()
        image = image_of(data)
        for limits in (None, object(), SimpleNamespace(**{f: getattr(GotLimits(), f) for f in GotLimits.__slots__})):
            with self.subTest(limits=type(limits)), self.assertRaises(InputError) as caught:
                attribute_got_bindings(image, limits=limits)
            self.assertEqual(caught.exception.code, 'invalid_limits')

    def test_admission_requires_a_sealed_arm64_image(self):
        data, _ = build_got_image()
        image = image_of(data)
        self.assertTrue(image.has_valid_admission())
        attribute_got_bindings(image)  # control
        forged = replace(image, data=patch(data, BLOB, '<I', 1))
        self.assertFalse(forged.has_valid_admission())
        not_image = SimpleNamespace(**{k: getattr(image, k) for k in ('data', 'sections', 'functions',
                                                                       'architecture', 'cpu_subtype')})
        for candidate in (forged, not_image, None, data):
            with self.subTest(type(candidate)), self.assertRaises(InputError) as caught:
                attribute_got_bindings(candidate)
            self.assertEqual(caught.exception.code, 'got_binding_admission')

    def test_cpu_subtype(self):
        data, _ = build_got_image(cpusubtype=1)
        self.assertEqual(image_of(data).cpu_subtype, 1)
        self.assertAttributed(data)
        data, _ = build_got_image(cpusubtype=2)  # CPU_SUBTYPE_ARM64E
        try:
            image = image_of(data)
        except InputError:
            return  # the parser refuses it first; either way no table is built
        with self.assertRaises(InputError) as caught:
            attribute_got_bindings(image)
        self.assertEqual(caught.exception.code, 'got_binding_admission')

    def test_classify_requires_an_admitted_function_and_a_pc_inside_it(self):
        data, layout = build_got_image(callers=(default_call(), (NOP, RET)))
        image, table = table_of(data)
        first = function_at(image, CALLER)
        self.assertEqual(first.boundary_source, 'lc_function_starts')
        self.assertEqual(table.classify(first, BLR_PC)[0], 'attributed')
        second = function_at(image, layout.caller_addrs[1])
        self.assertIsNone(table.classify(second, BLR_PC))           # pc outside the function
        self.assertIsNone(table.classify(first, first.end))          # one past the end
        self.assertIsNone(table.classify(first, CALLER - 4))
        self.assertIsNone(table.classify(replace(first, boundary_source='symbol'), BLR_PC))
        self.assertIsNone(table.classify(replace(first, start=first.start - 4), BLR_PC))  # not one of image.functions
        for junk in (None, 'f', 0):
            self.assertIsNone(table.classify(junk, BLR_PC))
        for pc in (None, '0x100001008', BLR_PC + 1, -4):
            self.assertIsNone(table.classify(first, pc))

    def test_classify_none_for_words_that_are_not_plain_blr(self):
        data, _ = build_got_image()
        image, table = table_of(data)
        function = function_at(image, CALLER)
        for pc in (ADRP_PC, LDR_PC, CALLER + 12):
            self.assertIsNone(table.classify(function, pc))
        for word in (br(X16), blraaz(X16), blr(31)):
            with self.subTest(word=hex(word)):
                data, _ = build_got_image(callers=(got_call()[:2] + (word, RET),))
                self.assertIsNone(classify(data))

    def test_module_imports_only_stdlib_and_airs_types(self):
        source = Path(__file__).resolve().parents[1] / 'src' / 'airs' / 'macho_got.py'
        tree = ast.parse(source.read_text())
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                # A relative import inside the airs package names airs.<module>.
                self.assertIn(node.level, (0, 1))
                modules.add(node.module if node.level == 0 else 'airs.' + (node.module or ''))
        airs = {m for m in modules if m == 'airs' or m.startswith('airs.')}
        self.assertLessEqual(airs, {'airs.types'})
        for name in modules - airs:
            self.assertIn(name.split('.')[0], sys.stdlib_module_names, name)
        for forbidden in ('subprocess', 'ctypes', 'mmap', 'multiprocessing', 'socket'):
            self.assertNotIn(forbidden, {m.split('.')[0] for m in modules})


class PositiveTests(GotTestCase):
    def test_default_layout_matches_hand_derivation(self):
        data, layout = build_got_image()
        self.assertEqual((layout.text_off, layout.caller_addrs, layout.slot_addr('__got', 0)),
                         (0x1000, [CALLER], GOT))
        self.assertEqual(struct.unpack_from('<4I', data, 0x1000), (0xF0000010, 0xF9400210, 0xD63F0200, RET))
        self.assertEqual((layout.blob_off, layout.starts_offset, layout.seg_records, layout.imports_offset,
                          layout.symbols_offset, layout.pool_name_offsets), (BLOB, 0x20, {'__DATA_CONST': 0x38},
                                                                              0x50, 0x54, [1]))
        self.assertEqual(struct.unpack_from('<7I', data, BLOB), (0, 0x20, 0x50, 0x54, 1, 1, 0))
        self.assertEqual(struct.unpack_from('<5I', data, BLOB + 0x20), (4, 0, 0, 0x18, 0))
        self.assertEqual(struct.unpack_from('<IHHQIHH', data, BLOB + 0x38), (24, 0x4000, 6, 0x4000, 0, 1, 0))
        self.assertEqual(u32(data, BLOB + 0x50), (1 << 9) | 2)
        self.assertEqual(data[BLOB + 0x54:BLOB + 0x55 + len(THROWING) + 1], b'\0' + THROWING.encode() + b'\0')
        self.assertEqual(u64(data, 0x4000), 0x8000000000000000)  # bind, ordinal 0, next 0
        self.assertEqual(u32(data, layout.indirect_off), 1)
        self.assertEqual(struct.unpack_from('<IBBHQ', data, layout.nlist_off(1))[1:],
                         (0x01, 0, 0x0200, 0))
        self.assertEqual(layout.dylib_paths, list(DEFAULT_DYLIBS))

    def test_binding_record_and_provenance(self):
        data, layout = build_got_image()
        _, table = table_of(data)
        self.assertTrue(table.complete)
        self.assertIsNone(table.reason)
        self.assertEqual(table.chained_fixups_status, 'decoded')
        self.assertEqual(dict(table.declined_slots), {})
        self.assertEqual(set(table.bindings), {GOT})
        binding = table.bindings[GOT]
        self.assertIs(type(binding), GotBinding)
        self.assertEqual((binding.slot_address, binding.slot_section, binding.slot_index, binding.symbol,
                          binding.symbol_index, binding.library_ordinal, binding.library_path,
                          binding.weak_import, binding.import_ordinal),
                         (GOT, '__DATA_CONST,__got', 0, THROWING, 1, 2, SWIFT_CORE, False, 0))
        record = binding.record()
        self.assertIs(type(record), dict)
        for key in ('slot_address', 'slot_section', 'slot_index', 'symbol', 'symbol_index', 'library_ordinal',
                    'library_path', 'weak_import', 'import_ordinal'):
            self.assertEqual(record[key], getattr(binding, key), key)
        provenance = record['provenance']
        chained = dict(provenance['chained'])
        step = chained.pop('chain_step')
        name_offset = chained.pop('name_offset')
        self.assertEqual(step, 0)  # members count from 0 in walk order within a page
        self.assertEqual(name_offset, BLOB + 0x54 + 1)  # slice file offset of the name, not the import field
        self.assertEqual({k: v for k, v in provenance.items() if k != 'chained'},
                         {'indirect_entry_offset': layout.indirect_off, 'nlist_offset': layout.nlist_off(1)})
        self.assertEqual(chained, {
            'model': CHAINED_FIXUPS_MODEL, 'blob_offset': BLOB, 'segment_index': 2,
            'segment_record_offset': BLOB + 0x38, 'pointer_format': 6, 'page_index': 0, 'page_start': 0,
            'member_slice_file_offset': 0x4000, 'member_container_file_offset': 0x4000,
            'raw': '0x8000000000000000', 'import_entry_offset': BLOB + 0x50})
        self.assertEqual(table.counts(), {'got_slots': 1, 'agreeing_got_slots': 1, 'declined_got_slots': 0})
        self.assertIs(type(table.work), int)
        self.assertGreater(table.work, 0)

    def test_attributed_call_record(self):
        data, _ = build_got_image()
        call = self.assertAttributed(data)
        _, table = table_of(data)
        self.assertEqual((call.call_pc, call.register, call.adrp_pc, call.ldr_pc, call.gap_ldr_to_blr,
                          call.gap_adrp_to_ldr), (BLR_PC, 16, ADRP_PC, LDR_PC, 0, 0))
        self.assertEqual(call.binding, table.bindings[GOT])
        record = call.record()
        self.assertEqual(record['provenance'], {'model': WINDOW_MODEL, 'window_words': [
            {'pc': ADRP_PC, 'word': '0xf0000010', 'slice_file_offset': 0x1000, 'container_file_offset': 0x1000,
             'role': 'adrp'},
            {'pc': LDR_PC, 'word': '0xf9400210', 'slice_file_offset': 0x1004, 'container_file_offset': 0x1004,
             'role': 'ldr'},
            {'pc': BLR_PC, 'word': '0xd63f0200', 'slice_file_offset': 0x1008, 'container_file_offset': 0x1008,
             'role': 'blr'}]})

    def test_fat_container_offsets(self):
        data, _ = build_got_image()
        image = parse_macho(build_fat((data,)), limits=EXTENDED_BROAD_LIMITS)
        self.assertEqual(image.slice_offset, 0x1000)
        table = attribute_got_bindings(image)
        chained = table.bindings[GOT].record()['provenance']['chained']
        self.assertEqual((chained['member_slice_file_offset'], chained['member_container_file_offset'],
                          chained['blob_offset']), (0x4000, 0x5000, BLOB))
        found = table.classify(function_at(image, CALLER), BLR_PC)
        words = found[1].record()['provenance']['window_words']
        self.assertEqual([(w['slice_file_offset'], w['container_file_offset']) for w in words],
                         [(0x1000, 0x2000), (0x1004, 0x2004), (0x1008, 0x2008)])

    def test_three_slots_one_chain(self):
        imports = (GotImport(THROWING), GotImport('_objc_retain', 1), GotImport('_$s4Test3baryS2iKF', 2, True))
        callers = (got_call(slot=0) + got_call(slot=1) + got_call(slot=2, rd=X17) + (RET,),)
        data, layout = build_got_image(callers, imports)
        self.assertEqual([raw >> 51 & 0xFFF for _, raw in layout.members['__DATA_CONST']], [2, 2, 0])
        _, table = table_of(data)
        self.assertEqual(table.counts(), {'got_slots': 3, 'agreeing_got_slots': 3, 'declined_got_slots': 0})
        got = [(b.symbol, b.library_ordinal, b.library_path, b.weak_import, b.import_ordinal, b.slot_index)
               for _, b in sorted(table.bindings.items())]
        self.assertEqual(got, [(THROWING, 2, SWIFT_CORE, False, 0, 0),
                               ('_objc_retain', 1, DEFAULT_DYLIBS[0], False, 1, 1),
                               ('_$s4Test3baryS2iKF', 2, SWIFT_CORE, True, 2, 2)])
        steps = [table.bindings[GOT + 8 * k].record()['provenance']['chained']['chain_step'] for k in range(3)]
        self.assertEqual(steps, [0, 1, 2])
        for k, register in ((0, 16), (1, 16), (2, 17)):
            call = self.assertAttributed(data, pc=CALLER + 12 * k + 8)
            self.assertEqual((call.register, call.binding.slot_address), (register, GOT + 8 * k))

    def test_both_sources_weak(self):
        data, _ = build_got_image(imports=(GotImport(THROWING, 2, True),))
        call = self.assertAttributed(data)
        self.assertTrue(call.binding.weak_import)

    def test_pointer_format_2_and_page_size_4k(self):
        for kwargs in ({'pointer_format': 2}, {'page_size': 0x1000}, {'pointer_format': 2, 'page_size': 0x1000}):
            with self.subTest(**kwargs):
                data, layout = build_got_image(**kwargs)
                page_count = struct.unpack_from('<H', data, layout.seg_record_off() + SS_PAGE_COUNT)[0]
                self.assertEqual(page_count, 0x4000 // kwargs.get('page_size', 0x4000))
                call = self.assertAttributed(data)
                chained = call.binding.record()['provenance']['chained']
                self.assertEqual(chained['pointer_format'], kwargs.get('pointer_format', 6))

    def test_got_in_data_segment_and_late_page(self):
        data, layout = build_got_image(pointer_sections=(PtrSection('__got', (0,), segment='__DATA'),))
        self.assertAttributed(data)
        # The slot on the segment's second 4 KiB page with 4 KiB chain pages: page_index 1.
        data, layout = build_got_image(page_size=0x1000, data_pad=0x1008)
        self.assertEqual(layout.slot_addr('__got', 0), GOT + 0x1008)
        call = self.assertAttributed(data)
        chained = call.binding.record()['provenance']['chained']
        self.assertEqual((chained['page_index'], chained['page_start']), (1, 8))

    def test_dylib_ordinal_table_kinds(self):
        # Ordinals count LC_LOAD_DYLIB, LC_LOAD_WEAK_DYLIB, LC_REEXPORT_DYLIB, LC_LOAD_UPWARD_DYLIB and
        # LC_LAZY_LOAD_DYLIB in load-command order; LC_LOAD_DYLINKER is not a dylib.
        dylibs = ((LC_LOAD_DYLINKER, '/usr/lib/dyld'), '/usr/lib/libA.dylib',
                  (LC_LOAD_WEAK_DYLIB, '/usr/lib/libB.dylib'),
                  (LC_REEXPORT_DYLIB, '/usr/lib/libC.dylib'), (LC_LOAD_UPWARD_DYLIB, '/usr/lib/libD.dylib'),
                  (LC_LAZY_LOAD_DYLIB, '/usr/lib/libE.dylib'))
        for ordinal, path in enumerate(('/usr/lib/libA.dylib', '/usr/lib/libB.dylib', '/usr/lib/libC.dylib',
                                        '/usr/lib/libD.dylib', '/usr/lib/libE.dylib'), 1):
            with self.subTest(ordinal=ordinal):
                data, _ = build_got_image(imports=(GotImport(THROWING, ordinal),), dylibs=dylibs)
                call = self.assertAttributed(data)
                self.assertEqual((call.binding.library_ordinal, call.binding.library_path), (ordinal, path))

    def test_gap_allowlist_each_form(self):
        rd = X16
        forms = {
            'nop': NOP, 'mov_x': mov_x(0, 1), 'mov_w': mov_w(2, 3), 'movz_x': movz_x(0, 1), 'movn_x': movn_x(1, 2),
            'movk_x': movk_x(2, 3), 'movz_w': movz_w(3, 4), 'movn_w': movn_w(4, 5), 'movk_w': movk_w(5, 6),
            'add_x': add_x_imm(0, 1, 8), 'sub_x': sub_x_imm(1, 2, 8), 'add_w': add_w_imm(2, 3, 8),
            'sub_w': sub_w_imm(3, 4, 8),
        }
        adrp_word, ldr_word, blr_word = got_call(rd=rd)
        for name, word in forms.items():
            for where in ('ldr_to_blr', 'adrp_to_ldr'):
                with self.subTest(name=name, where=where):
                    fn = ((adrp_word, word, ldr_word, blr_word) if where == 'adrp_to_ldr'
                          else (adrp_word, ldr_word, word, blr_word)) + (RET,)
                    data, _ = build_got_image((fn,))
                    call = self.assertAttributed(data, pc=CALLER + 12)
                    self.assertEqual((call.gap_adrp_to_ldr, call.gap_ldr_to_blr),
                                     (1, 0) if where == 'adrp_to_ldr' else (0, 1))
                    roles = [w['role'] for w in call.record()['provenance']['window_words']]
                    self.assertEqual(roles, ['adrp', 'gap', 'ldr', 'blr'] if where == 'adrp_to_ldr'
                                     else ['adrp', 'ldr', 'gap', 'blr'])

    def test_gap_of_exactly_max_window_gap(self):
        adrp_word, ldr_word, blr_word = got_call()
        fn = (adrp_word, NOP, NOP, NOP, ldr_word, NOP, mov_x(0, 1), NOP, blr_word, RET)
        data, _ = build_got_image((fn,))
        call = self.assertAttributed(data, pc=CALLER + 32)
        self.assertEqual((call.adrp_pc, call.ldr_pc, call.gap_adrp_to_ldr, call.gap_ldr_to_blr),
                         (CALLER, CALLER + 16, 3, 3))
        self.assertEqual(len(call.record()['provenance']['window_words']), 9)
        # A larger limit admits a longer gap; a smaller one does not.
        fn = (adrp_word, NOP, NOP, NOP, NOP, ldr_word, blr_word, RET)
        data, _ = build_got_image((fn,))
        self.assertDeclined(data, 'got_window_gap_limit', pc=CALLER + 24)
        self.assertAttributed(data, pc=CALLER + 24, limits=GotLimits(max_window_gap=4))
        data, _ = build_got_image(((adrp_word, NOP, ldr_word, blr_word, RET),))
        self.assertDeclined(data, 'got_window_gap_limit', pc=CALLER + 12, limits=GotLimits(max_window_gap=0))

    def test_distinct_base_and_target_registers(self):
        # ADRP x9; MOV x0, x1; LDR x16, [x9, #off]; MOV x9, x2 (writes the base after the load: allowed); BLR x16
        fn = (('adrp', 9, ('slot', '__got', 0)), mov_x(0, 1), ('ldr', X16, 9, ('slot', '__got', 0)), mov_x(9, 2),
              blr(X16), RET)
        data, _ = build_got_image((fn,))
        call = self.assertAttributed(data, pc=CALLER + 16)
        self.assertEqual((call.register, call.adrp_pc, call.ldr_pc), (16, CALLER, CALLER + 8))

    def test_lazy_pointer_section_is_not_decoded(self):
        sections = (PtrSection('__got', (0,)), PtrSection('__la_symbol_ptr', (0,), kind=7, segment='__DATA',
                                                          fixup='none'))
        data, layout = build_got_image(pointer_sections=sections)
        _, table = table_of(data)
        self.assertEqual(table.counts(), {'got_slots': 1, 'agreeing_got_slots': 1, 'declined_got_slots': 0})
        self.assertEqual(set(table.bindings), {GOT})

    def test_vm_offset_segment_with_sdk_segment_offset(self):
        # __DATA_CONST VM is 0x4000 above its file offset: segment_offset is vmaddr - image base (0x8000),
        # not the file offset (0x4000).
        data, layout = build_got_image(vm_gap=0x4000)
        segment = layout.segment('__DATA_CONST')
        self.assertEqual((segment['vmaddr'] - BASE, segment['fileoff']), (0x8000, 0x4000))
        self.assertEqual(u64(data, layout.seg_record_off() + SS_SEGMENT_OFFSET), 0x8000)
        call = self.assertAttributed(data)
        self.assertEqual(call.binding.slot_address, BASE + 0x8000)
        self.assertEqual(call.binding.record()['provenance']['chained']['member_slice_file_offset'], 0x4000)
        # The file-offset reading of segment_offset declines.
        data, _ = build_got_image(vm_gap=0x4000, segment_offset_override={'__DATA_CONST': 0x4000})
        self.assertSlotDeclined(data, 'chained_segment_offset_mismatch', slot=BASE + 0x8000)

    def test_other_br_and_blr_words_are_not_refusals(self):
        # Unlike the direct-edge screen of the stub model, BR/BLR words elsewhere do not refuse.
        data, _ = build_got_image((default_call(), (br(X17), blr(X17), blraaz(X17), RET)))
        self.assertAttributed(data)

    def test_screen_boundaries(self):
        # A branch to the ADRP itself, a symbol at the ADRP, a branch just past the BLR: all outside (A, c].
        target = ('word', 0, 0)
        for extra, symbols in (((('b', target),), ()), ((('bl', ('word', 0, 3)),), ()),
                               ((RET,), (('_l', target, 0x0E),))):
            with self.subTest(extra=extra, symbols=symbols):
                data, _ = build_got_image((default_call(), extra + (RET,)), extra_symbols=symbols)
                self.assertAttributed(data)

    def test_stab_and_undefined_symbols_are_not_symbol_entries(self):
        for n_type in (0x24, 0x64):  # N_FUN, N_SO: n_type & 0xe0 != 0
            with self.subTest(n_type=hex(n_type)):
                data, _ = build_got_image(extra_symbols=(('_stab', ('word', 0, 1), n_type),))
                try:
                    image_of(data)
                except InputError:
                    continue
                self.assertAttributed(data)

    def test_data_in_code_elsewhere_does_not_decline(self):
        # The parser marks every function of a section that holds nonzero-length data-in-code, and this
        # builder has one executable section, so the entries here are zero-length (they cover no word).
        data, _ = build_got_image((default_call(), (NOP, NOP, RET)), data_in_code=((('word', 1, 0), 0),
                                                                                 (0x4000, 0)))
        image = image_of(data)
        self.assertEqual(function_at(image, CALLER).boundary_source, 'lc_function_starts')
        self.assertAttributed(data)


class TableLevelTests(GotTestCase):
    def test_macho_header_non_ascii_segment_name(self):
        data, layout = build_got_image()
        self.assertAttributed(data)
        # parse_macho replaces non-ASCII names; the GOT decoder requires ASCII.
        # __PAGEZERO has no sections whose declared segment name would also need changing.
        name = layout.segment('__PAGEZERO')['cmd_off'] + 8
        self.assertIncomplete(patch(data, name, '<B', 0xff), 'macho_header')

    def test_load_command_limit(self):
        data, layout = build_got_image()
        self.assertTrue(table_of(data, GotLimits(max_load_commands=layout.ncmds))[1].complete)
        self.assertIncomplete(data, 'load_command_limit', GotLimits(max_load_commands=layout.ncmds - 1))

    def test_section_limit(self):
        data, layout = build_got_image()
        self.assertEqual(layout.nsections, 2)
        self.assertTrue(table_of(data, GotLimits(max_sections=2))[1].complete)
        self.assertIncomplete(data, 'section_limit', GotLimits(max_sections=1))

    def test_raw_section_metadata_mismatch(self):
        data, layout = build_got_image()
        name = layout.section_header_off('__got')
        self.assertEqual(data[name:name + 6], b'__got\0')
        self.assertIncomplete(patch(data, name + 4, '<B', 0xFF), 'raw_section_metadata_mismatch')

    def test_indirect_symbol_table_missing(self):
        data, _ = build_got_image(include_dysymtab=False)
        self.assertIncomplete(data, 'indirect_symbol_table_missing')
        # Without a GOT section the absent LC_DYSYMTAB is not a refusal.
        data, _ = build_got_image(((NOP, RET),), pointer_sections=(), include_dysymtab=False)
        _, table = table_of(data)
        self.assertTrue(table.complete, table.reason)

    def test_indirect_symbol_limit(self):
        sections = (PtrSection('__got', (0,)), PtrSection('__la_symbol_ptr', (0, 0), kind=7, segment='__DATA',
                                                          fixup='none'))
        data, layout = build_got_image(pointer_sections=sections)
        self.assertEqual(layout.nindirect, 3)
        self.assertAttributed(data, limits=GotLimits(max_indirect_symbols=3))
        self.assertIncomplete(data, 'indirect_symbol_limit', GotLimits(max_indirect_symbols=2))

    def test_got_slot_limit_counts_valid_sections_only(self):
        imports = (GotImport(THROWING), GotImport('_b'), GotImport('_c'))
        sections = (PtrSection('__got', (0, 1)), PtrSection('__got_bad', (2, 2), extra_size=4))
        data, _ = build_got_image(imports=imports, pointer_sections=sections)
        _, table = table_of(data, GotLimits(max_got_slots=2))
        self.assertTrue(table.complete, table.reason)
        self.assertEqual(table.counts()['got_slots'], 2)
        self.assertIncomplete(data, 'got_slot_limit', GotLimits(max_got_slots=1))
        data, _ = build_got_image(imports=imports[:2], pointer_sections=sections[:1])
        self.assertIncomplete(data, 'got_slot_limit', GotLimits(max_got_slots=1))
        self.assertIncomplete(data, 'got_slot_limit', GotLimits(max_got_slots=0))

    def test_got_entry_screen_limit(self):
        data, layout = build_got_image((default_call(), (NOP, RET)))
        self.assertEqual(layout.executable_words, 6)
        self.assertAttributed(data, limits=GotLimits(max_screen_words=6))
        self.assertIncomplete(data, 'got_entry_screen_limit', GotLimits(max_screen_words=5))

    def test_got_data_in_code_limit(self):
        data, _ = build_got_image((default_call(), (NOP, NOP, RET)), data_in_code=((('word', 1, 0), 0),
                                                                                 (('word', 1, 1), 0)))
        self.assertAttributed(data, limits=GotLimits(max_data_in_code_entries=2))
        self.assertIncomplete(data, 'got_data_in_code_limit', GotLimits(max_data_in_code_entries=1))
        self.assertIncomplete(data, 'got_data_in_code_limit', GotLimits(max_data_in_code_entries=0))

    def test_got_work_limit(self):
        data, _ = build_got_image()
        self.assertIncomplete(data, 'got_work_limit', GotLimits(max_work=0))
        imports = (GotImport(THROWING), GotImport('_b'), GotImport('_c'))
        data, _ = build_got_image(imports=imports)
        self.assertAttributed(data, limits=GotLimits(max_chain_members=3))
        self.assertIncomplete(data, 'got_work_limit', GotLimits(max_chain_members=2))

    def test_work_limit_boundary_is_the_reported_work(self):
        data, _ = build_got_image()
        work = table_of(data)[1].work
        self.assertAttributed(data, limits=GotLimits(max_work=work))
        self.assertIncomplete(data, 'got_work_limit', GotLimits(max_work=work - 1))


class ImageLevelTests(GotTestCase):
    def test_chained_fixups_absent(self):
        data, _ = build_got_image(include_chained=False)
        self.assertImageDeclined(data, 'chained_fixups_absent')

    def test_chained_fixups_duplicate(self):
        data, _ = build_got_image(duplicate_chained=True)
        self.assertImageDeclined(data, 'chained_fixups_duplicate')

    def test_chained_fixups_extent(self):
        data, layout = build_got_image()
        dataoff, datasize = layout.chained_cmd_field(2), layout.chained_cmd_field(3)
        self.assertEqual(struct.unpack_from('<4I', data, layout.chained_cmd_off), (0x80000034, 16, BLOB,
                                                                                   layout.blob_size))
        for name, offset, value in (('dataoff % 4', dataoff, BLOB + 2), ('datasize < 28', datasize, 24),
                                    ('outside __LINKEDIT', dataoff, 0x4000)):
            with self.subTest(name):
                try:
                    patched = patch(data, offset, '<I', value)
                    image_of(patched)
                except InputError:
                    self.fail('the parser refused the single-field patch: ' + name)
                self.assertImageDeclined(patched, 'chained_fixups_extent')
        # datasize 28 is enough for the extent rule (later steps then judge the header layout).
        _, table = table_of(patch(data, datasize, '<I', 28))
        self.assertNotEqual(table.chained_fixups_status, 'chained_fixups_extent')

    def test_binding_encoding_ambiguous(self):
        data, _ = build_got_image(dyld_info=(8, 0, 0, 0, 8))  # rebase and export opcodes only
        self.assertAttributed(data)
        for sizes in ((0, 8, 0, 0, 0), (0, 0, 8, 0, 0), (0, 0, 0, 8, 0)):
            with self.subTest(sizes=sizes):
                data, _ = build_got_image(dyld_info=sizes)
                self.assertImageDeclined(data, 'binding_encoding_ambiguous')

    def test_binding_namespace_flat(self):
        data, layout = build_got_image()
        self.assertEqual(u32(data, 24) & MH_TWOLEVEL, MH_TWOLEVEL)
        self.assertImageDeclined(patch(data, 24, '<I', HEADER_FLAGS & ~MH_TWOLEVEL), 'binding_namespace_flat')

    def test_chained_fixups_version(self):
        data, _ = build_got_image()
        self.assertImageDeclined(patch(data, BLOB + CF_VERSION, '<I', 1), 'chained_fixups_version')

    def test_chained_header_layout(self):
        data, layout = build_got_image()
        cases = (('starts < 28', CF_STARTS, 24), ('starts % 4', CF_STARTS, 0x22),
                 ('imports == starts', CF_IMPORTS, 0x20), ('symbols < imports', CF_SYMBOLS, 0x4C),
                 ('symbols > datasize', CF_SYMBOLS, layout.blob_size + 4), ('imports overrun', CF_COUNT, 2))
        for name, field, value in cases:
            with self.subTest(name):
                self.assertImageDeclined(patch(data, BLOB + field, '<I', value), 'chained_header_layout')
        # Boundary: symbols_offset == datasize is admitted by the layout rule.
        _, table = table_of(patch(data, BLOB + CF_SYMBOLS, '<I', layout.blob_size))
        self.assertNotEqual(table.chained_fixups_status, 'chained_header_layout')

    def test_chained_imports_format_and_symbols_format(self):
        data, _ = build_got_image()
        for value in (2, 3, 0):
            self.assertImageDeclined(patch(data, BLOB + CF_IMPORTS_FORMAT, '<I', value),
                                     'chained_imports_format_unsupported')
        self.assertImageDeclined(patch(data, BLOB + CF_SYMBOLS_FORMAT, '<I', 1), 'chained_symbols_compressed')

    def test_chained_imports_limit(self):
        data, _ = build_got_image()
        self.assertAttributed(data, limits=GotLimits(max_chained_imports=1))
        self.assertImageDeclined(data, 'chained_imports_limit', GotLimits(max_chained_imports=0))

    def test_chained_starts_layout(self):
        data, layout = build_got_image()
        for value in (3, 5):
            with self.subTest(seg_count=value):
                self.assertImageDeclined(patch(data, BLOB + 0x20, '<I', value), 'chained_starts_layout')
        # seg_count is right, but the seg_info_offset array overruns imports_offset (0x20 + 4 + 16 > 0x24).
        self.assertImageDeclined(patch(data, BLOB + CF_IMPORTS, '<I', 0x24), 'chained_starts_layout')

    def test_chained_starts_layout_text_file_offset(self):
        for shift in (0, 0x100):
            with self.subTest(text_fileoff=shift):
                data, layout = build_got_image()
                text = layout.segment('__TEXT')
                # Keep VM addresses and function-start deltas unchanged. Move the
                # section bytes with its file offset so offset - fileoff is stable.
                code = data[layout.text_off:layout.text_off + layout.text_size]
                data = patch(data, text['cmd_off'] + 40, '<QQ', shift, text['filesize'] - shift)
                data = patch(data, text['cmd_off'] + 72 + 48, '<I', layout.text_off + shift)
                data = patch(data, layout.text_off, f'{layout.text_size}s', bytes(layout.text_size))
                data = patch(data, layout.text_off + shift, f'{layout.text_size}s', code)

                # Neither earlier starts-layout return can explain the decline.
                starts = u32(data, BLOB + CF_STARTS)
                imports = u32(data, BLOB + CF_IMPORTS)
                seg_count = u32(data, BLOB + starts)
                self.assertEqual(seg_count, layout.nsegments)
                self.assertEqual(seg_count, sum(u32(data, s['cmd_off']) == 0x19
                                                for s in layout.segments))
                self.assertLessEqual(starts + 4 + 4 * seg_count, imports)
                image = image_of(data)
                self.assertEqual(function_at(image, CALLER).start, CALLER)
                if shift:
                    self.assertImageDeclined(data, 'chained_starts_layout')
                else:
                    self.assertAttributed(data)

    def test_binding_library_table_limit(self):
        dylibs = tuple('/usr/lib/libX%03d.dylib' % k for k in range(0xF0))
        data, layout = build_got_image(dylibs=dylibs)
        caller = layout.caller_addrs[0]
        self.assertGreater(caller, CALLER)  # the load commands push __text to a later page
        call = self.assertAttributed(data, pc=caller + 8, caller=caller)
        self.assertEqual(call.binding.library_path, dylibs[1])
        data, layout = build_got_image(dylibs=dylibs + ('/usr/lib/libExtra.dylib',))
        caller = layout.caller_addrs[0]
        image, table = table_of(data)
        self.assertTrue(table.complete)
        self.assertEqual(table.chained_fixups_status, 'binding_library_table_limit')
        self.assertEqual(dict(table.bindings), {})
        self.assertEqual(set(table.declined_slots.values()), {'binding_library_table_limit'})
        self.assertEqual(table.classify(function_at(image, caller), caller + 8),
                         ('declined', 'binding_library_table_limit'))


class SourceATests(GotTestCase):
    def test_indirect_symbol_local_or_absolute(self):
        data, layout = build_got_image()
        entry = layout.slot_indirect_off('__got', 0)
        for value in (0x80000000, 0x40000000, 0xC0000000, 0x80000001):
            with self.subTest(hex(value)):
                self.assertSlotDeclined(patch(data, entry, '<I', value), 'indirect_symbol_local_or_absolute')

    def test_indirect_symbol_index_range(self):
        data, layout = build_got_image()
        self.assertEqual(layout.nsyms, 2)
        self.assertSlotDeclined(patch(data, layout.slot_indirect_off('__got', 0), '<I', 2),
                                'indirect_symbol_index_range')

    def test_indirect_symbol_not_undefined_range(self):
        data, layout = build_got_image()
        self.assertSlotDeclined(patch(data, layout.slot_indirect_off('__got', 0), '<I', 0),
                                'indirect_symbol_not_undefined_range')
        # Shrinking nundefsym (dysymtab word 5) to 0 moves the entry out of the range.
        self.assertSlotDeclined(patch(data, layout.dysymtab_word_off(5), '<I', 0),
                                'indirect_symbol_not_undefined_range')

    def test_imported_symbol_not_undefined_external(self):
        data, layout = build_got_image()
        nlist = layout.import_nlist_off(0)
        cases = (('not external', NL_TYPE, '<B', 0x00), ('stab bits', NL_TYPE, '<B', 0x21),
                 ('N_ABS', NL_TYPE, '<B', 0x03), ('N_INDR', NL_TYPE, '<B', 0x0B), ('N_PBUD', NL_TYPE, '<B', 0x0D),
                 ('n_sect', NL_SECT, '<B', 1), ('n_value', NL_VALUE, '<Q', 8))
        for name, field, fmt, value in cases:
            with self.subTest(name):
                patched = patch(data, nlist + field, fmt, value)
                try:
                    image_of(patched)
                except InputError:
                    continue  # the parser refuses this variant before the GOT model
                self.assertSlotDeclined(patched, 'imported_symbol_not_undefined_external')
        # At least the plain non-external and the n_value cases must reach the model.
        for field, fmt, value in ((NL_TYPE, '<B', 0x00), (NL_VALUE, '<Q', 8)):
            self.assertSlotDeclined(patch(data, nlist + field, fmt, value), 'imported_symbol_not_undefined_external')

    def test_imported_symbol_name(self):
        data, layout = build_got_image()
        nlist = layout.import_nlist_off(0)
        name = layout.symbol_name_off(1)
        self.assertEqual(data[name:name + len(THROWING) + 1], THROWING.encode() + b'\0')
        self.assertSlotDeclined(patch(data, nlist + NL_STRX, '<I', 0), 'imported_symbol_name')
        self.assertSlotDeclined(patch(data, nlist + NL_STRX, '<I', layout.strx[1] - 1), 'imported_symbol_name')
        self.assertSlotDeclined(patch(data, name + 3, '<B', 0xC3), 'imported_symbol_name')  # non-ASCII
        length = len(THROWING)
        self.assertAttributed(data, limits=GotLimits(max_symbol_bytes=length))
        self.assertSlotDeclined(data, 'imported_symbol_name', limits=GotLimits(max_symbol_bytes=length - 1))


class SourceBTests(GotTestCase):
    def two_slot_image(self):
        imports = (GotImport(THROWING), GotImport('_$s4Test3baryS2iKF'))
        return build_got_image((got_call(slot=0) + got_call(slot=1) + (RET,),), imports)

    def test_chained_slot_not_covered(self):
        data, layout = build_got_image()
        self.assertSlotDeclined(patch(data, layout.seg_info_entry_off(2), '<I', 0), 'chained_slot_not_covered')
        self.assertSlotDeclined(patch(data, layout.page_start_off(), '<H', 0xFFFF), 'chained_slot_not_covered')

    def test_chained_segment_record_extent(self):
        data, layout = build_got_image()
        record = layout.seg_record_off()
        cases = (('size < 22 + 2*page_count', record + SS_SIZE, '<I', 22),
                 ('record overruns imports', record + SS_SIZE, '<I', 32),
                 ('page_count 0', record + SS_PAGE_COUNT, '<H', 0),
                 ('page_count too large', record + SS_PAGE_COUNT, '<H', 2),
                 ('R + 22 > imports', layout.seg_info_entry_off(2), '<I', layout.imports_offset - 0x20 - 20))
        for name, offset, fmt, value in cases:
            with self.subTest(name):
                self.assertSlotDeclined(patch(data, offset, fmt, value), 'chained_segment_record_extent')

    def test_chained_page_size_unsupported(self):
        data, layout = build_got_image()
        for value in (0x2000, 0x800, 0):
            self.assertSlotDeclined(patch(data, layout.seg_record_off() + SS_PAGE_SIZE, '<H', value),
                                    'chained_page_size_unsupported')

    def test_chained_pointer_format_unsupported(self):
        data, layout = build_got_image()
        record = layout.seg_record_off()
        for value in (1, 3, 9, 12):
            with self.subTest(pointer_format=value):
                self.assertSlotDeclined(patch(data, record + SS_FORMAT, '<H', value),
                                        'chained_pointer_format_unsupported')
        self.assertSlotDeclined(patch(data, record + SS_MAX_VALID, '<I', 0x100000),
                                'chained_pointer_format_unsupported')

    def test_chained_segment_offset_mismatch(self):
        data, layout = build_got_image()
        record = layout.seg_record_off()
        for value in (0x4004, 0, 0x8000):
            self.assertSlotDeclined(patch(data, record + SS_SEGMENT_OFFSET, '<Q', value),
                                    'chained_segment_offset_mismatch')

    def test_chained_page_start_multi(self):
        data, layout = build_got_image()
        self.assertSlotDeclined(patch(data, layout.page_start_off(), '<H', 0x8000), 'chained_page_start_multi')

    def test_chained_chain_malformed(self):
        data, layout = build_got_image()
        for value in (2, 0x4000, 0x7FFC):
            with self.subTest(page_start=hex(value)):
                self.assertSlotDeclined(patch(data, layout.page_start_off(), '<H', value), 'chained_chain_malformed')
        self.assertSlotDeclined(patch(data, 0x4000, '<Q', bind_raw(0, next_=1)), 'chained_chain_malformed')

    def test_chain_may_not_leave_its_page(self):
        data, layout = build_got_image(data_pad=0x4000 - 8)  # the slot is the page's last qword
        slot = layout.slot_addr('__got', 0)
        self.assertEqual(slot, GOT + 0x3FF8)
        self.assertAttributed(data)
        self.assertSlotDeclined(patch(data, layout.slot_off('__got', 0), '<Q', bind_raw(0, next_=2)),
                                'chained_chain_malformed', slot=slot)

    def test_chained_pointer_reserved_bits_decline_the_whole_page(self):
        data, layout = self.two_slot_image()
        self.assertAttributed(data)
        self.assertAttributed(data, pc=CALLER + 20)
        for raw in (bind_raw(1, reserved=1), bind_raw(1, reserved=0x40000), rebase_raw(0x1000, reserved=1)):
            with self.subTest(raw=hex(raw)):
                patched = patch(data, layout.slot_off('__got', 1), '<Q', raw)
                table = self.assertSlotDeclined(patched, 'chained_pointer_reserved_bits', slot=GOT + 8,
                                                pc=CALLER + 20)
                # The failure is on the page, so slot 0 (walked before it) declines too.
                self.assertEqual(dict(table.declined_slots), {GOT: 'chained_pointer_reserved_bits',
                                                              GOT + 8: 'chained_pointer_reserved_bits'})
                self.assertDeclined(patched, 'chained_pointer_reserved_bits')

    def test_chained_import_ordinal_range(self):
        data, layout = build_got_image()
        self.assertSlotDeclined(patch(data, 0x4000, '<Q', bind_raw(1)), 'chained_import_ordinal_range')
        self.assertSlotDeclined(patch(data, 0x4000, '<Q', bind_raw(0xFFFFFF)), 'chained_import_ordinal_range')

    def test_chained_slot_not_member(self):
        # I4: slot 1 carries a valid-looking bind qword, but the chain ends at slot 0.
        data, layout = self.two_slot_image()
        cut = patch(data, layout.slot_off('__got', 0), '<Q', bind_raw(0, next_=0))
        self.assertEqual(u64(cut, layout.slot_off('__got', 1)), bind_raw(1))
        table = self.assertSlotDeclined(cut, 'chained_slot_not_member', slot=GOT + 8, pc=CALLER + 20)
        self.assertIn(GOT, table.bindings)
        self.assertAttributed(cut)
        # The page chain starts at slot 1: slot 0 is skipped.
        skipped = patch(data, layout.page_start_off(), '<H', 8)
        table = self.assertSlotDeclined(skipped, 'chained_slot_not_member', slot=GOT)
        self.assertIn(GOT + 8, table.bindings)
        # A chain hop that steps over slot 1 (next = 4 words = 16 bytes from slot 0).
        imports = (GotImport(THROWING), GotImport('_$s4Test3baryS2iKF'), GotImport('_c'))
        data, layout = build_got_image((got_call(slot=0) + got_call(slot=1) + (RET,),), imports)
        hop = patch(data, layout.slot_off('__got', 0), '<Q', bind_raw(0, next_=4))
        self.assertSlotDeclined(hop, 'chained_slot_not_member', slot=GOT + 8, pc=CALLER + 20)

    def test_chained_slot_rebase(self):
        data, _ = build_got_image()
        self.assertSlotDeclined(patch(data, 0x4000, '<Q', rebase_raw(0x1000)), 'chained_slot_rebase')
        data, _ = build_got_image(pointer_sections=(PtrSection('__got', (0,), fixup='rebase'),))
        self.assertSlotDeclined(data, 'chained_slot_rebase')

    def test_chained_bind_addend_nonzero(self):
        data, _ = build_got_image()
        for addend in (1, 0x80, 0xFF):
            self.assertSlotDeclined(patch(data, 0x4000, '<Q', bind_raw(0, addend=addend)),
                                    'chained_bind_addend_nonzero')

    def test_chained_import_name(self):
        data, layout = build_got_image()
        entry = layout.import_entry_off(0)
        pool_size = layout.blob_size - layout.symbols_offset
        for name, value in (('empty (pool NUL)', 2 | (0 << 9)), ('past datasize', 2 | (pool_size << 9)),
                            ('far past the blob', 2 | (0x7FFFFF << 9))):
            with self.subTest(name):
                self.assertSlotDeclined(patch(data, entry, '<I', value), 'chained_import_name')
        self.assertSlotDeclined(patch(data, layout.pool_name_off(0) + 3, '<B', 0x80), 'chained_import_name')


class AgreementTests(GotTestCase):
    """I1: a patch to either source alone flips the attribution to the matching decline."""

    def test_binding_name_mismatch(self):
        data, layout = build_got_image()
        self.assertAttributed(data)
        self.assertSlotDeclined(patch(data, layout.pool_name_off(0) + 4, '<B', ord('Z')), 'binding_name_mismatch')
        self.assertSlotDeclined(patch(data, layout.symbol_name_off(1) + 4, '<B', ord('Z')), 'binding_name_mismatch')
        # No underscore stripping: the chained name without its leading underscore.
        entry = layout.import_entry_off(0)
        self.assertSlotDeclined(patch(data, entry, '<I', 2 | (2 << 9)), 'binding_name_mismatch')
        # The nlist index moved to another (undefined) symbol with a different name.
        imports = (GotImport(THROWING), GotImport('_$s4Test3baryS2iKF'))
        data, layout = build_got_image(imports=imports, pointer_sections=(PtrSection('__got', (0,)),))
        self.assertAttributed(data)
        self.assertSlotDeclined(patch(data, layout.slot_indirect_off('__got', 0), '<I',
                                      layout.import_symbol_index(1)), 'binding_name_mismatch')
        # The chained ordinal moved to the other import.
        self.assertSlotDeclined(patch(data, layout.slot_off('__got', 0), '<Q', bind_raw(1)),
                                'binding_name_mismatch')

    def test_binding_library_ordinal_special(self):
        data, layout = build_got_image()
        desc = layout.import_nlist_off(0) + NL_DESC
        for ordinal in (0, 0xFE, 0xFF):
            with self.subTest(source='A', ordinal=ordinal):
                self.assertSlotDeclined(patch(data, desc, '<H', ordinal << 8), 'binding_library_ordinal_special')
        entry = layout.import_entry_off(0)
        for ordinal in (0, 0xF1, 0xFD, 0xFE, 0xFF):
            with self.subTest(source='B', ordinal=ordinal):
                self.assertSlotDeclined(patch(data, entry, '<I', ordinal | (1 << 9)),
                                        'binding_library_ordinal_special')

    def test_binding_library_ordinal_range(self):
        data, layout = build_got_image()
        self.assertSlotDeclined(patch(data, layout.import_nlist_off(0) + NL_DESC, '<H', 3 << 8),
                                'binding_library_ordinal_range')
        self.assertSlotDeclined(patch(data, layout.import_entry_off(0), '<I', 3 | (1 << 9)),
                                'binding_library_ordinal_range')
        # 0xF0 is not special; it is out of range for two dylibs.
        self.assertSlotDeclined(patch(data, layout.import_entry_off(0), '<I', 0xF0 | (1 << 9)),
                                'binding_library_ordinal_range')

    def test_binding_library_mismatch(self):
        data, layout = build_got_image()
        self.assertSlotDeclined(patch(data, layout.import_nlist_off(0) + NL_DESC, '<H', 1 << 8),
                                'binding_library_mismatch')
        self.assertSlotDeclined(patch(data, layout.import_entry_off(0), '<I', 1 | (1 << 9)),
                                'binding_library_mismatch')

    def test_binding_weak_mismatch(self):
        data, layout = build_got_image()
        self.assertSlotDeclined(patch(data, layout.import_nlist_off(0) + NL_DESC, '<H', (2 << 8) | 0x40),
                                'binding_weak_mismatch')
        self.assertSlotDeclined(patch(data, layout.import_entry_off(0), '<I', 2 | (1 << 8) | (1 << 9)),
                                'binding_weak_mismatch')
        data, layout = build_got_image(imports=(GotImport(THROWING, 2, True),))
        self.assertSlotDeclined(patch(data, layout.import_nlist_off(0) + NL_DESC, '<H', 2 << 8),
                                'binding_weak_mismatch')

    def test_binding_library_name(self):
        data, layout = build_got_image()
        command = layout.dylib_cmd_offs[1]
        path = command + 24
        self.assertEqual(data[path:path + len(SWIFT_CORE) + 1], SWIFT_CORE.encode() + b'\0')
        cmdsize = u32(data, command + 4)
        cases = (('name.offset < 24', command + 8, '<I', 20), ('non-ASCII', path + 5, '<B', 0xE9),
                 ('empty', path, '<B', 0), ('name.offset past cmdsize', command + 8, '<I', cmdsize))
        for name, offset, fmt, value in cases:
            with self.subTest(name):
                self.assertSlotDeclined(patch(data, offset, fmt, value), 'binding_library_name')
        # No NUL inside cmdsize: fill the path and its padding with 'a'.
        filled = bytearray(data)
        filled[path:command + cmdsize] = b'a' * (command + cmdsize - path)
        self.assertSlotDeclined(bytes(filled), 'binding_library_name')
        # An invalid path for ANOTHER ordinal does not affect this binding.
        other = layout.dylib_cmd_offs[0] + 24
        self.assertAttributed(patch(data, other, '<B', 0))


class OrderTests(GotTestCase):
    def test_source_a_precedes_source_b(self):
        data, layout = build_got_image()
        both = patch(patch(data, layout.slot_indirect_off('__got', 0), '<I', 0x80000000), 0x4000, '<Q',
                     bind_raw(0, addend=1))
        self.assertSlotDeclined(both, 'indirect_symbol_local_or_absolute')

    def test_source_a_steps_in_order(self):
        data, layout = build_got_image()
        nlist = layout.import_nlist_off(0)
        bad_nlist = patch(patch(data, nlist + NL_VALUE, '<Q', 8), nlist + NL_STRX, '<I', 0)
        self.assertSlotDeclined(bad_nlist, 'imported_symbol_not_undefined_external')
        entry = layout.slot_indirect_off('__got', 0)
        self.assertSlotDeclined(patch(bad_nlist, entry, '<I', 0xC0000005), 'indirect_symbol_local_or_absolute')
        self.assertSlotDeclined(patch(bad_nlist, entry, '<I', 7), 'indirect_symbol_index_range')

    def test_source_b_precedes_agreement(self):
        data, layout = build_got_image()
        both = patch(patch(data, 0x4000, '<Q', bind_raw(0, addend=1)), layout.symbol_name_off(1) + 4, '<B',
                     ord('Z'))
        self.assertSlotDeclined(both, 'chained_bind_addend_nonzero')

    def test_source_b_steps_in_order(self):
        data, layout = build_got_image()
        record = layout.seg_record_off()
        mixed = patch(patch(data, record + SS_PAGE_SIZE, '<H', 0x2000), record + SS_FORMAT, '<H', 1)
        self.assertSlotDeclined(mixed, 'chained_page_size_unsupported')
        mixed = patch(patch(data, record + SS_FORMAT, '<H', 1), record + SS_SEGMENT_OFFSET, '<Q', 0)
        self.assertSlotDeclined(mixed, 'chained_pointer_format_unsupported')
        mixed = patch(patch(data, layout.page_start_off(), '<H', 0x8000), 0x4000, '<Q', bind_raw(0, addend=1))
        self.assertSlotDeclined(mixed, 'chained_page_start_multi')
        mixed = patch(data, 0x4000, '<Q', bind_raw(5, addend=1))
        self.assertSlotDeclined(mixed, 'chained_import_ordinal_range')
        mixed = patch(data, 0x4000, '<Q', bind_raw(0, addend=1, reserved=1))
        self.assertSlotDeclined(mixed, 'chained_pointer_reserved_bits')

    def test_agreement_steps_in_order(self):
        data, layout = build_got_image()
        desc = layout.import_nlist_off(0) + NL_DESC
        entry = layout.import_entry_off(0)
        name = layout.pool_name_off(0) + 4
        self.assertSlotDeclined(patch(patch(data, name, '<B', ord('Z')), desc, '<H', 0), 'binding_name_mismatch')
        self.assertSlotDeclined(patch(patch(data, desc, '<H', 0xFE << 8), entry, '<I', 3 | (1 << 9)),
                                'binding_library_ordinal_special')
        self.assertSlotDeclined(patch(patch(data, desc, '<H', (3 << 8) | 0x40), entry, '<I', 1 | (1 << 9)),
                                'binding_library_ordinal_range')
        self.assertSlotDeclined(patch(data, desc, '<H', (1 << 8) | 0x40), 'binding_library_mismatch')
        path = layout.dylib_cmd_offs[1] + 24
        self.assertSlotDeclined(patch(patch(data, path, '<B', 0), desc, '<H', (2 << 8) | 0x40),
                                'binding_weak_mismatch')

    def test_image_level_precedes_slot_level_source_b(self):
        data, layout = build_got_image()
        both = patch(patch(data, BLOB + CF_VERSION, '<I', 1), 0x4000, '<Q', bind_raw(0, addend=1))
        self.assertImageDeclined(both, 'chained_fixups_version')

    def test_window_reason_precedes_slot_reason(self):
        fn = (movz_x(X16, 4), ('ldr', X16, X16, ('slot', '__got', 0)), blr(X16), RET)
        data, layout = build_got_image((fn,))
        bad = patch(data, layout.slot_indirect_off('__got', 0), '<I', 0x80000000)
        self.assertDeclined(bad, 'got_base_not_adrp')

    def test_slot_mapping_precedes_slot_reason(self):
        data, layout = build_got_image()
        bad = patch(data, layout.slot_indirect_off('__got', 0), '<I', 0x80000000)
        self.assertDeclined(bad, 'indirect_symbol_local_or_absolute')
        self.assertDeclined(patch(bad, layout.word_off(0, 1), '<I', ldr_x_uimm(X16, X16, 8)), 'got_slot_unmapped')


class WindowTests(GotTestCase):
    """5.1 / I3: single-word changes flip an attribution to the specified reason or to None."""

    def call_with(self, before_ldr=(), after_ldr=(), *, rd=X16, rn=None, extra_callers=(), **kwargs):
        adrp_word, ldr_word, blr_word = got_call(rd=rd, rn=rn)
        fn = (adrp_word, *before_ldr, ldr_word, *after_ldr, blr_word, RET)
        data, layout = build_got_image((fn,) + tuple(extra_callers), **kwargs)
        return data, CALLER + 4 * (len(fn) - 2)

    def test_blr_x31_and_unrelated_loads_are_shape_absent(self):
        fn = (('adrp', 30, ('slot', '__got', 0)), ('ldr', 30, 30, ('slot', '__got', 0)), blr(31), RET)
        data, _ = build_got_image((fn,))
        self.assertIsNone(classify(data))
        data, _ = build_got_image(((('adrp', X16, ('slot', '__got', 0)), ('ldr', X17, X16, ('slot', '__got', 0)),
                                    blr(X16), RET),))
        self.assertIsNone(classify(data))

    def test_target_register_gap_cases_are_shape_absent(self):
        control, pc = self.call_with(after_ldr=(NOP,))
        self.assertAttributed(control, pc=pc)
        for name, word in (('write to Xn', mov_x(X16, 0)), ('W write to Xn', movz_w(X16, 1)),
                           ('add to Xn', add_x_imm(X16, X16, 8)), ('non-allowlisted', adds_x_imm(0, 1, 1)),
                           ('ADDG', addg(0, 1)), ('ORR with shift', orr_x_shifted(0, 31, 1, 1)),
                           ('ORR rn != zr', orr_x_shifted(0, 2, 1, 0)), ('BL', 0x94000000),
                           ('LDR W', ldr_w_uimm(0, 1, 0))):
            with self.subTest(name):
                data, pc = self.call_with(after_ldr=(word,))
                self.assertIsNone(classify(data, pc=pc))
        data, pc = self.call_with(after_ldr=(NOP,) * 4)
        self.assertIsNone(classify(data, pc=pc))
        data, pc = self.call_with(after_ldr=(NOP,) * 3)
        self.assertAttributed(data, pc=pc)

    def test_load_forms_other_than_ldr_u64_are_shape_absent(self):
        for word in (ldr_x_literal(X16, 8), ldur_x(X16, X16, 8), ldr_w_uimm(X16, X16, 0)):
            with self.subTest(hex(word)):
                data, _ = build_got_image(((('adrp', X16, ('slot', '__got', 0)), word, blr(X16), RET),))
                self.assertIsNone(classify(data))

    def test_function_start_before_load_is_shape_absent(self):
        data, _ = build_got_image(((NOP, blr(X16), RET),))
        self.assertIsNone(classify(data, pc=CALLER + 4))
        data, _ = build_got_image(((blr(X16), RET),))
        self.assertIsNone(classify(data, pc=CALLER))
        # A load in the previous function is not visible across the start.
        data, layout = build_got_image((got_call()[:2], (blr(X16), RET)))
        self.assertIsNone(classify(data, pc=layout.caller_addrs[1], caller=layout.caller_addrs[1]))

    def test_got_base_not_adrp(self):
        cases = {
            'base is sp': (None, ldr_x_uimm(X16, 31, 8)),
            'movz base': (movz_x(X16, 4), None),
            'adr base': (adr(X16), None),
            'adrp other register': (adrp_imm(X17, 3), None),
            'ldr base': (ldr_x_uimm(X16, 0, 0), None),
            'base written in gap': ('gap', mov_x(X16, 1)),
            'base written by W in gap': ('gap', add_w_imm(X16, X16, 1)),
            'non-allowlisted gap word': ('gap', adds_x_imm(0, 1, 1)),
        }
        for name, (first, second) in cases.items():
            with self.subTest(name):
                slot = ('slot', '__got', 0)
                if first is None:
                    fn = (('adrp', X16, slot), second, blr(X16), RET)
                elif first == 'gap':
                    fn = (('adrp', X16, slot), second, ('ldr', X16, X16, slot), blr(X16), RET)
                else:
                    fn = (first, ('ldr', X16, X16, slot), blr(X16), RET)
                data, _ = build_got_image((fn,))
                pc = CALLER + 4 * (len(fn) - 2)
                self.assertDeclined(data, 'got_base_not_adrp', pc=pc)

    def test_got_window_gap_limit(self):
        data, pc = self.call_with(before_ldr=(NOP,) * 3)
        self.assertAttributed(data, pc=pc)
        data, pc = self.call_with(before_ldr=(NOP,) * 4)
        self.assertDeclined(data, 'got_window_gap_limit', pc=pc)
        data, pc = self.call_with(before_ldr=(mov_x(0, 1), NOP, movk_x(2, 1), sub_x_imm(3, 3, 1)))
        self.assertDeclined(data, 'got_window_gap_limit', pc=pc)

    def test_got_window_outside_function(self):
        slot = ('slot', '__got', 0)
        data, _ = build_got_image(((('ldr', X16, X16, slot), blr(X16), RET),))
        self.assertDeclined(data, 'got_window_outside_function', pc=CALLER + 4)
        data, _ = build_got_image(((NOP, NOP, ('ldr', X16, X16, slot), blr(X16), RET),))
        self.assertDeclined(data, 'got_window_outside_function', pc=CALLER + 12)
        # The ADRP sits at the end of the previous function: the walk may not cross the start.
        data, layout = build_got_image(((RET, ('adrp', X16, slot)), (('ldr', X16, X16, slot), blr(X16), RET)))
        start = layout.caller_addrs[1]
        self.assertDeclined(data, 'got_window_outside_function', pc=start + 4, caller=start)

    def test_got_window_outside_function_at_section_edge(self):
        data, layout = build_got_image()
        self.assertAttributed(data)
        # Function and executable section both begin here. Skipping the patched
        # first word reaches the section edge before finding an ADRP.
        self.assertDeclined(patch(data, layout.word_off(0, 0), '<I', NOP),
                            'got_window_outside_function')

    def test_got_window_incoming_edge_each_branch_form(self):
        # A second function branches to the LDR (in (A, c]) or to the BLR itself (c is included).
        forms = (('b', ()), ('bl', ()), ('bcond', (1,)), ('cbz', (3,)), ('cbnz_w', (3,)), ('tbz', (3, 5)),
                 ('tbnz', (3, 33)))
        for target_word in (1, 2):
            for kind, args in forms:
                with self.subTest(kind=kind, target=target_word):
                    data, _ = build_got_image((default_call(), ((kind, ('word', 0, target_word), *args), RET)))
                    self.assertDeclined(data, 'got_window_incoming_edge')
        # A backward branch from later in the same function.
        data, _ = build_got_image((default_call()[:3] + (('b', ('word', 0, 1)), RET),))
        self.assertDeclined(data, 'got_window_incoming_edge')
        # A branch to a gap word.
        data, pc = self.call_with(after_ldr=(NOP,), extra_callers=(((('cbz', ('word', 0, 2))), RET),))
        self.assertDeclined(data, 'got_window_incoming_edge', pc=pc)

    def test_got_window_symbol_entry(self):
        for n_type in (0x0E, 0x0F, 0x1E):  # N_SECT local, external, private external
            for word in (1, 2):
                with self.subTest(n_type=hex(n_type), word=word):
                    data, _ = build_got_image(extra_symbols=(('_inside', ('word', 0, word), n_type),))
                    self.assertDeclined(data, 'got_window_symbol_entry')

    def test_entry_screen_spans_every_executable_section_and_bisects_bounds(self):
        # Edge from the function that follows into the window's last word only.
        data, _ = build_got_image((default_call(), (('b', ('word', 0, 2)), RET)))
        self.assertDeclined(data, 'got_window_incoming_edge')
        data, _ = build_got_image((default_call(), (('b', ('word', 0, 3)), RET)))  # the RET after the BLR
        self.assertAttributed(data)

    def test_data_in_code_in_window_function_is_not_classified(self):
        # Unreachable reason got_window_data_in_code: the parser marks a function with a nonzero-length
        # LC_DATA_IN_CODE entry 'lc_function_starts_with_embedded_data', and classify only accepts
        # 'lc_function_starts' functions, so the site returns None before the window is built.
        data, _ = build_got_image((default_call() + (NOP,),), data_in_code=((('word', 0, 4), 4),))
        image, table = table_of(data)
        function = image.functions[0]
        self.assertEqual(function.boundary_source, 'lc_function_starts_with_embedded_data')
        self.assertIsNone(table.classify(function, BLR_PC))

    def test_got_slot_unmapped(self):
        data, layout = build_got_image()
        ldr = layout.word_off(0, 1)
        self.assertAttributed(data)
        self.assertDeclined(patch(data, ldr, '<I', ldr_x_uimm(X16, X16, 8)), 'got_slot_unmapped')  # past __got
        self.assertDeclined(patch(data, layout.word_off(0, 0), '<I', adrp_imm(X16, -0x100000)), 'got_slot_unmapped')
        self.assertDeclined(patch(data, layout.word_off(0, 0), '<I', adrp_imm(X16, 0x7FFFF)), 'got_slot_unmapped')

    def test_got_slot_section_kind(self):
        for kind in (7, 0x14, 0):
            with self.subTest(kind=hex(kind)):
                data, _ = build_got_image(pointer_sections=(PtrSection('__ptrs', (0,), kind=kind,
                                                                       fixup='bind'),),
                                          callers=(got_call(section='__ptrs') + (RET,),))
                self.assertDeclined(data, 'got_slot_section_kind')
        # A load from __text.
        data, layout = build_got_image()
        self.assertDeclined(patch(data, layout.word_off(0, 0), '<I', adrp_imm(X16, 0)), 'got_slot_section_kind')
        # No GOT section at all: complete, empty, every candidate declines got_slot_section_kind.
        data, _ = build_got_image(pointer_sections=(PtrSection('__la_symbol_ptr', (0,), kind=7, fixup='none'),),
                                  callers=(got_call(section='__la_symbol_ptr') + (RET,),))
        _, table = table_of(data)
        self.assertTrue(table.complete)
        self.assertIsNone(table.reason)
        self.assertEqual((dict(table.bindings), dict(table.declined_slots)), ({}, {}))
        self.assertEqual(table.counts(), {'got_slots': 0, 'agreeing_got_slots': 0, 'declined_got_slots': 0})
        self.assertDeclined(data, 'got_slot_section_kind')

    def test_got_slot_section_invalid(self):
        cases = (('size % 8', {'pointer_sections': (PtrSection('__got', (0,), extra_size=4),)}),
                 ('addr % 8', {'pointer_sections': (PtrSection('__got', (0, 0), misalign=4),),
                               'callers': ((('adrp', X16, ('slot', '__got', 0, 4)),
                                            ('ldr', X16, X16, ('slot', '__got', 0, 4)), blr(X16), RET),)}))
        for name, kwargs in cases:
            with self.subTest(name):
                data, layout = build_got_image(**kwargs)
                image, table = table_of(data)
                self.assertTrue(table.complete, table.reason)
                self.assertEqual(table.counts()['got_slots'], 0)
                self.assertDeclined(data, 'got_slot_section_invalid')
        data, layout = build_got_image()
        bad = patch(data, layout.section_header_off('__got') + SECT_RESERVED1, '<I', 1)  # 1 + 1 > nindirect 1
        self.assertDeclined(bad, 'got_slot_section_invalid')


class BoundedAndTotalTests(GotTestCase):
    """I5 and I2: bounded byte flips never raise and never attribute to anything but source A's binding."""

    def test_blob_and_slot_byte_flips(self):
        data, layout = build_got_image()
        offsets = list(range(BLOB, BLOB + layout.blob_size)) + list(range(0x4000, 0x4008))
        for offset in offsets:
            for mask in (0x01, 0x80, 0xFF):
                patched = patch(data, offset, '<B', data[offset] ^ mask)
                try:
                    image = image_of(patched)
                except InputError:
                    continue
                table = attribute_got_bindings(image)
                self.assertEqual(table.model, GOT_MODEL)
                found = table.classify(function_at(image, CALLER), BLR_PC)
                self.assertIsNotNone(found, hex(offset))
                if found[0] == 'attributed':
                    binding = found[1].binding
                    self.assertEqual((binding.symbol, binding.library_ordinal, binding.weak_import,
                                      binding.library_path, binding.slot_address),
                                     (THROWING, 2, False, SWIFT_CORE, GOT), hex(offset))
                else:
                    self.assertEqual(found[0], 'declined')
                    self.assertIs(type(found[1]), str)

    def test_classify_every_pc_has_valid_shape_and_only_expected_blr_is_attributed(self):
        data, layout = build_got_image((default_call(), (NOP, ('b', ('word', 0, 0)), RET)))
        image, table = table_of(data)
        attributed = []
        for function in image.functions:
            for pc in range(function.start - 8, function.end + 8):
                with self.subTest(function=function.start, pc=pc):
                    result = table.classify(function, pc)
                    if result is None:
                        continue
                    self.assertIs(type(result), tuple)
                    self.assertEqual(len(result), 2)
                    kind, payload = result
                    self.assertIn(kind, {'declined', 'attributed'})
                    if kind == 'declined':
                        self.assertIs(type(payload), str)
                    else:
                        self.assertIs(type(payload), GotCall)
                        self.assertEqual(payload.call_pc, pc)
                    offset = pc - layout.text_addr
                    is_blr = (0 <= offset <= layout.text_size - 4 and offset % 4 == 0
                              and (u32(data, layout.text_off + offset) & 0xFFFFFC1F) == 0xD63F0000)
                    if not is_blr:
                        self.assertNotEqual(kind, 'attributed')
                    if kind == 'attributed':
                        attributed.append((function.start, pc))
        self.assertEqual(attributed, [(layout.caller_addrs[0], layout.word_addr(0, 2))])


if __name__ == '__main__':
    unittest.main()
