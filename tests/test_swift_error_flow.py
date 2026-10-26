"""Owned instruction words and symbol metadata; no target code is executed."""
from dataclasses import replace
import struct
import unittest
from airs.macho import parse_macho
from parser_helpers import build_macho
from airs.swift_error_flow import recover_swift_error_flow, throwing_declaration, DEFAULT_LIMITS
from airs.types import InputError

SYMBOL = '_$s4Demo5parseyS2iKF'
BASE = 0x100001000


def image(window=(0xb4000075,), symbol=SYMBOL, aliases=()):
    callee_offset = max(32, ((1 + len(window)) * 4 + 31) // 32 * 32)
    words = [0x94000000 | (callee_offset // 4), *window]
    words += [0xd65f03c0] * (callee_offset // 4 - len(words))
    words += [0xd65f03c0]
    return parse_macho(build_macho(struct.pack('<' + 'I' * len(words), *words),
        function_offsets=(0, callee_offset), symbols=(('_$s4Demo6handleyS2iF', 0), (symbol, callee_offset), *aliases)))


class SwiftErrorFlowTests(unittest.TestCase):
    def test_direct_throwing_call_has_success_and_error_edges(self):
        report = recover_swift_error_flow(image())
        self.assertEqual(report['summary']['recovered_candidate_count'], 1)
        call = report['calls'][0]
        self.assertEqual(call['success_pc'], hex(BASE + 16))
        self.assertEqual(call['error_pc'], hex(BASE + 8))
        self.assertEqual(call['callee']['symbol'], SYMBOL)


class SwiftErrorFlowAttributionTests(unittest.TestCase):
    def test_section_end_label_does_not_name_adjacent_function(self):
        words = [0x94000008, 0xb4000075] + [0xd65f03c0] * 6
        raw = bytearray(build_macho(struct.pack('<8I', *words), function_offsets=(0, 32),
            unwind_info=struct.pack('<I', 0xd65f03c0), symbols=((SYMBOL, 32),)))
        second_section = 32 + 72 + 80
        raw[second_section:second_section + 16] = b'__text2'.ljust(16, b'\0')
        struct.pack_into('<I', raw, second_section + 64, 0x80000400)
        admitted = parse_macho(bytes(raw))
        self.assertEqual(len(admitted.functions), 2)
        self.assertEqual(recover_swift_error_flow(admitted)['summary']['recovered_candidate_count'], 0)


class SwiftErrorFlowBoundaryTests(unittest.TestCase):
    def first(self, value):
        return recover_swift_error_flow(value)['calls'][0]

    def test_cbnz_polarity(self):
        row = self.first(image((0xb5000075,)))
        self.assertEqual((row['success_pc'], row['error_pc']), (hex(BASE + 8), hex(BASE + 16)))

    def test_live_copy_survives_original_register_kill(self):
        row = self.first(image((0xaa1503f3, 0xaa1f03f5, 0xb4000073)))
        self.assertEqual(row['status'], 'recovered_candidate')
        self.assertEqual(row['tested_register'], 'x19')

    def test_overwritten_alias_is_not_error(self):
        row = self.first(image((0xaa1503f3, 0xaa0003f3, 0xb4000073)))
        self.assertEqual(row['reason'], 'not_error_result_test')

    def test_original_error_overwrite_refuses(self):
        self.assertEqual(self.first(image((0xaa0003f5, 0xb4000075)))['reason'], 'error_value_clobbered')

    def test_zero_register_and_unrelated_register_refuse(self):
        for word in (0xb4000060, 0xb400007f):
            self.assertEqual(self.first(image((word,)))['status'], 'declined')

    def test_w_projection_and_w_test_refuse(self):
        for words in ((0x34000075,), (0x2a1503f3, 0xb4000073)):
            self.assertEqual(self.first(image(words))['status'], 'declined')

    def test_intervening_control_flow_and_unknown_effect_refuse(self):
        for word in (0x14000001, 0x94000007, 0xffffffff, 0xf94003e0):
            self.assertEqual(self.first(image((word, 0xb4000075)))['status'], 'declined')

    def test_nop_and_bounded_window(self):
        self.assertEqual(self.first(image((0xd503201f, 0xb4000075)))['status'], 'recovered_candidate')
        self.assertEqual(self.first(image((0xd503201f,) * 8 + (0xb4000075,)))['reason'], 'postcall_window_exhausted')

    def test_unsupported_successor_regions_refuse(self):
        for word in (0xb4000015, 0xb4000035, 0xb40000f5, 0xb4fffff5):
            self.assertEqual(self.first(image((word,)))['reason'], 'unsupported_successor_region')

    def test_complete_declaration_grammar_only(self):
        for suffix in ('yS2iF', 'yS2iYaKF', 'yS2iAA5FaultOYKF', 'yS2iKFTA', 'yS2iKF.llvm.1'):
            symbol = '_$s4Demo5parse' + suffix
            self.assertIsNone(throwing_declaration(symbol))
            self.assertEqual(self.first(image(symbol=symbol))['status'], 'declined')
        for symbol in ('_$s04Demo5parseyS2iKF', '_$s4Dem5parseyS2iKF', 'ordinary_c_function'):
            self.assertIsNone(throwing_declaration(symbol))

    def test_alias_ambiguity_refuses(self):
        self.assertEqual(self.first(image(aliases=(('ordinary_alias', 32),)))['reason'], 'callee_symbol_absent_or_ambiguous')

    def test_private_alternate_and_resolver_entries_refuse(self):
        for desc, kind in ((0x200, 0x0f), (0x100, 0x0f), (0, 0x1f)):
            admitted = image(); raw = bytearray(admitted.data); cursor = 32
            for _ in range(struct.unpack_from('<I', raw, 16)[0]):
                command, size = struct.unpack_from('<II', raw, cursor)
                if command == 2:
                    symoff = struct.unpack_from('<I', raw, cursor + 8)[0]
                    struct.pack_into('<B', raw, symoff + 16 + 4, kind)
                    struct.pack_into('<H', raw, symoff + 16 + 6, desc)
                    break
                cursor += size
            self.assertEqual(self.first(parse_macho(bytes(raw)))['status'], 'declined')

    def test_target_must_be_exact_function_entry(self):
        admitted = image(); raw = bytearray(admitted.data)
        section = admitted.section('__TEXT', '__text')
        struct.pack_into('<I', raw, section.file_offset, 0x94000009)
        self.assertEqual(self.first(parse_macho(bytes(raw)))['reason'], 'callee_not_exact_function_entry')

    def test_embedded_data_and_relocation_boundary_tags_exclude(self):
        for tag in ('lc_function_starts_with_embedded_data', 'lc_function_starts_with_relocations', 'symbols'):
            admitted = image()
            altered = replace(admitted, functions=tuple(replace(f, boundary_source=tag) for f in admitted.functions))
            report = recover_swift_error_flow(altered)
            self.assertFalse(report['word_scan_complete'])
            self.assertEqual(report['summary']['recovered_candidate_count'], 0)

    def test_word_and_detail_budgets_remain_explicit(self):
        partial = recover_swift_error_flow(image(), replace(DEFAULT_LIMITS, max_total_instructions=1))
        self.assertFalse(partial['word_scan_complete'])
        self.assertEqual(partial['summary']['scanned_word_count'], 1)
        omitted = recover_swift_error_flow(image(), replace(DEFAULT_LIMITS, max_total_evidence=0))
        self.assertFalse(omitted['call_details_complete'])
        self.assertEqual(omitted['summary']['omitted_call_count'], 1)
        self.assertEqual(omitted['summary']['recovered_candidate_count'], 0)

    def test_architecture_and_image_limits_refuse(self):
        for subtype in (2, 0x80000000):
            with self.assertRaises(InputError):
                recover_swift_error_flow(replace(image(), cpu_subtype=subtype))
        with self.assertRaises(InputError):
            recover_swift_error_flow(image(), replace(DEFAULT_LIMITS, max_file_bytes=1))

    def test_unreachable_word_pattern_is_only_a_structural_candidate(self):
        words = (0x14000007, 0x94000007, 0xb4000075, *([0xd65f03c0] * 6))
        admitted = parse_macho(build_macho(struct.pack('<9I', *words), function_offsets=(0, 32), symbols=((SYMBOL, 32),)))
        report = recover_swift_error_flow(admitted)
        self.assertEqual(report['scope'], 'structural_call_return_edges')
        self.assertEqual(report['calls'][0]['status'], 'recovered_candidate')
        self.assertTrue(any('not runtime reachability' in x for x in report['limitations']))
