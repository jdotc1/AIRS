"""Qualified fixed-width source-path literal transforms; no executable is run."""
import importlib.util
from pathlib import Path
import struct
import unittest
ROOT = Path(__file__).resolve().parents[1]

def load():
    spec = importlib.util.spec_from_file_location('runtime_source_paths', ROOT / 'scripts/runtime_source_paths.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

PRIVATE = b'/' + b'Users' + b'/builder/'
HOME = b'/' + b'home' + b'/builder/'
OFFSET = 512


def thin(literal=None, *, cpu=0x0100000c, protections=5, section_name=b'__cstring', flags=2, suffix=b'owned padding'):
    if literal is None: literal = PRIVATE + b'work/parser.c'
    strings = literal + b'\x00'
    size = OFFSET + len(strings) + len(suffix)
    header = struct.pack('<IiiIIIII', 0xfeedfacf, cpu, 0, 6, 1, 152, 0, 0)
    segment = struct.pack('<II16sQQQQiiII', 0x19, 152, b'__TEXT', 0x100000000, size, 0, size,
                          protections, protections, 1, 0)
    section = struct.pack('<16s16sQQIIIIIIII', section_name, b'__TEXT', 0x100000000 + OFFSET,
                          len(strings), OFFSET, 0, 0, 0, flags, 0, 0, 0)
    return header + segment + section + bytes(OFFSET - len(header + segment + section)) + strings + suffix


def fat(slices, *, wide=False):
    offset = 4096; stride = 4096
    data = bytearray(offset + stride * len(slices))
    struct.pack_into('>II', data, 0, 0xcafebabf if wide else 0xcafebabe, len(slices))
    entry_size = 32 if wide else 20
    for index, (cpu, payload) in enumerate(slices):
        location = offset + stride * index
        if wide: struct.pack_into('>iiQQII', data, 8 + index * entry_size, cpu, 0, location, len(payload), 12, 0)
        else: struct.pack_into('>iiIII', data, 8 + index * entry_size, cpu, 0, location, len(payload), 12)
        data[location:location + len(payload)] = payload
    return bytes(data)


class RuntimeSourcePathsFirstTests(unittest.TestCase):
    def test_only_source_literal_home_prefix_changes_at_fixed_offsets(self):
        tool = load(); source = thin()
        output, count = tool.normalize_source_paths(source)
        expected = bytearray(source)
        expected[OFFSET:OFFSET + len(PRIVATE)] = b'/AIRS/' + b'/' * (len(PRIVATE) - 6)
        self.assertEqual(output, bytes(expected)); self.assertEqual(len(output), len(source))
        self.assertEqual(count, 1)


class RuntimeSourcePathsBoundaryTests(unittest.TestCase):
    def setUp(self): self.tool = load()
    def reject(self, source):
        with self.assertRaises(ValueError): self.tool.normalize_source_paths(source)

    def test_both_universal_slices_are_changed_without_touching_tables_or_padding(self):
        for wide in (False, True):
            left = thin(PRIVATE + b'build_macos_installer-v3.15.0/source.c')
            right = thin(HOME + b'build_source', cpu=0x01000007)
            source = fat([(0x0100000c, left), (0x01000007, right)], wide=wide)
            output, count = self.tool.normalize_source_paths(source)
            expected = bytearray(source)
            expected[4096 + OFFSET:4096 + OFFSET + len(PRIVATE)] = b'/AIRS/' + b'/' * (len(PRIVATE) - 6)
            expected[8192 + OFFSET:8192 + OFFSET + len(HOME)] = b'/AIRS/' + b'/' * (len(HOME) - 6)
            self.assertEqual(output, bytes(expected)); self.assertEqual(count, 2)
            self.assertEqual(len(source), len(output))

    def test_each_admitted_source_extension_and_build_source(self):
        for filename in (b'file.c', b'file.h', b'file.cc', b'file.cpp', b'build_source'):
            output, count = self.tool.normalize_source_paths(thin(PRIVATE + b'work/sub-dir_1.2+fix/' + filename))
            self.assertEqual(count, 1); self.assertIn(filename + b'\x00', output)

    def test_multiple_literal_boundaries_and_non_source_values_are_preserved(self):
        source = thin(PRIVATE + b'a.c\x00ordinary literal\x00' + HOME + b'b.h')
        output, count = self.tool.normalize_source_paths(source)
        self.assertEqual(count, 2); self.assertIn(b'\x00ordinary literal\x00', output)
        self.assertEqual(output[:OFFSET], source[:OFFSET]); self.assertTrue(output.endswith(b'owned padding'))
        self.assertEqual(output.count(b'\x00'), source.count(b'\x00'))

    def test_non_source_private_paths_refuse(self):
        for final in (b'file.py', b'file.json', b'file.c.bak', b'file.C', b'file.c:12', b'build_source_log', b'file.c '):
            self.reject(thin(PRIVATE + b'work/' + final))

    def test_non_ascii_and_embedded_prefix_paths_refuse(self):
        self.reject(thin(PRIVATE + 'café/file.c'.encode()))
        self.reject(thin(b'error at ' + PRIVATE + b'file.c'))
        self.reject(thin(PRIVATE + b'spaced directory/file.c'))
        self.reject(thin(PRIVATE + b'work/' + HOME + b'file.c'))

    def test_prefix_outside_cstring_or_in_writable_segment_refuses(self):
        self.reject(thin(suffix=PRIVATE + b'outside.c'))
        self.reject(thin(protections=7))
        self.reject(thin(section_name=b'__text', flags=0))
        self.reject(thin(flags=0))
        value = bytearray(thin()); struct.pack_into('<i', value, 88, 7); self.reject(bytes(value))

    def test_literal_must_terminate_inside_declared_section(self):
        value = bytearray(thin()); size = struct.unpack_from('<Q', value, 144)[0]
        struct.pack_into('<Q', value, 144, size - 1); self.reject(bytes(value))

    def test_invalid_load_command_counts_lengths_and_totals_refuse(self):
        for field, number in ((16, 513), (20, 1024 * 1024 + 8), (36, 8), (36, 151), (20, 160), (16, 0)):
            value = bytearray(thin()); struct.pack_into('<I', value, field, number); self.reject(bytes(value))

    def test_section_bounds_owner_type_and_alignment_refuse(self):
        for field, number, format in ((152, 0xfffffff0, '<I'), (144, 9 * 1024 * 1024, '<Q'),
                                      (156, 32, '<I'), (156, 20, '<I'), (164, 1000000, '<I')):
            value = bytearray(thin()); struct.pack_into(format, value, field, number); self.reject(bytes(value))
        value = bytearray(thin()); value[120:136] = b'__OTHER'.ljust(16, b'\x00'); self.reject(bytes(value))
        value = bytearray(thin()); struct.pack_into('<I', value, 152, 32); struct.pack_into('<Q', value, 136, 0x100000020)
        self.reject(bytes(value))

    def test_overlapping_sections_cannot_alias_instruction_data(self):
        value = bytearray(thin()); struct.pack_into('<I', value, 20, 232); struct.pack_into('<I', value, 36, 232)
        struct.pack_into('<I', value, 96, 2)
        value[184:264] = struct.pack('<16s16sQQIIIIIIII', b'__text', b'__TEXT', 0x100000000 + OFFSET,
                                   4, OFFSET, 0, 0, 0, 0, 0, 0, 0)
        self.reject(bytes(value))

    def test_overlapping_segments_refuse_even_with_separate_names(self):
        value = bytearray(thin()); struct.pack_into('<I', value, 16, 2); struct.pack_into('<I', value, 20, 224)
        value[184:256] = struct.pack('<II16sQQQQiiII', 0x19, 72, b'__OTHER', 0x200000000, len(value),
                                   0, len(value), 3, 3, 0, 0)
        self.reject(bytes(value))

    def test_universal_slice_count_offsets_overlap_and_alignment_refuse(self):
        original = fat([(0x0100000c, thin()), (0x01000007, thin(cpu=0x01000007))])
        for field, value in ((4, 0), (4, 9), (16, 4), (20, 0xffffffff), (24, 32)):
            data = bytearray(original); struct.pack_into('>I', data, field, value); self.reject(bytes(data))
        data = bytearray(original); struct.pack_into('>I', data, 36, 4096); self.reject(bytes(data))

    def test_universal_table_architecture_mismatch_and_reserved_data_refuse(self):
        data = bytearray(fat([(0x0100000c, thin())])); struct.pack_into('>i', data, 8, 0x01000007)
        self.reject(bytes(data))
        data = bytearray(fat([(0x0100000c, thin())], wide=True)); struct.pack_into('>I', data, 36, 1)
        self.reject(bytes(data))

    def test_prefix_in_universal_padding_refuses(self):
        data = bytearray(fat([(0x0100000c, thin())])); value = PRIVATE + b'outside.c'
        data[1000:1000 + len(value)] = value; self.reject(bytes(data))

    def test_prefix_count_section_and_file_budgets_are_bounded(self):
        from unittest.mock import patch
        with patch.object(self.tool, 'MAX_PATHS', 1): self.reject(thin(PRIVATE + b'a.c\x00' + HOME + b'b.h'))
        with patch.object(self.tool, 'MAX_CSTRING_BYTES', 8): self.reject(thin())
        with patch.object(self.tool, 'MAX_FILE_BYTES', 128): self.reject(thin())
        with patch.object(self.tool, 'MAX_COMMAND_BYTES', 128): self.reject(thin())

    def test_marker_free_bytes_return_unchanged_without_admission_claim(self):
        for source in (b'', b'owned opaque marker-free bytes', thin(b'/AIRS/source.c')):
            output, count = self.tool.normalize_source_paths(source)
            self.assertIs(output, source); self.assertEqual(count, 0)

    def test_private_marker_requires_supported_header_architecture_and_file_type(self):
        self.reject(PRIVATE + b'file.c')
        for field, number in ((4, 0), (12, 1), (0, 0xfeedface)):
            source = bytearray(thin()); struct.pack_into('<I', source, field, number); self.reject(bytes(source))

    def test_short_home_prefix_retains_exact_width(self):
        literal = b'/' + b'home' + b'/a/file.c'
        source = thin(literal); output, count = self.tool.normalize_source_paths(source)
        self.assertEqual(count, 1); self.assertEqual(len(output), len(source))
        self.assertIn(b'/AIRS///file.c\x00', output)


class RuntimeSourcePathsReviewTests(unittest.TestCase):
    def test_instruction_markers_and_noncanonical_home_prefix_case_refuse(self):
        tool = load()
        for flags in (2 | 0x80000000, 2 | 0x400, 2 | 0x80000400):
            with self.assertRaises(ValueError): tool.normalize_source_paths(thin(flags=flags))
        for literal in (PRIVATE.upper() + b'file.c', HOME.upper() + b'file.c'):
            with self.assertRaises(ValueError): tool.normalize_source_paths(thin(literal))

    def test_literals_require_readable_consistent_initial_and_maximum_protection(self):
        tool = load()
        for maximum, initial in ((0, 0), (4, 4), (5, 0), (0, 5), (1, 5)):
            data = bytearray(thin())
            struct.pack_into('<ii', data, 88, maximum, initial)
            with self.assertRaises(ValueError): tool.normalize_source_paths(bytes(data))
