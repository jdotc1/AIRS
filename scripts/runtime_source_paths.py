#!/usr/bin/env python3
"""Fixed-width normalization of qualified source/build path C-string literals.

This transforms qualified literals in sections not marked as instructions, for
a pinned owned runtime staging copy. It is not proof of runtime behavior or a
general Mach-O validator: marker-free inputs return unchanged without an
admission claim. Runtime behavior must be checked separately on a fresh staging copy.
"""
from __future__ import annotations
import re
import struct

MAX_FILE_BYTES = 128 * 1024 * 1024
MAX_CSTRING_BYTES = 8 * 1024 * 1024
MAX_LOAD_COMMANDS = 512
MAX_COMMAND_BYTES = 1024 * 1024
MAX_SLICES = 8
MAX_PATHS = 16384
HOME_PREFIX = re.compile(rb'/(?:Users|home)/[^/\x00\r\n]+/', re.IGNORECASE)
SOURCE_PATH = re.compile(rb'/(?:Users|home)/[A-Za-z0-9_.+\-]+/(?:[A-Za-z0-9_.+\-]+/)*(?:[A-Za-z0-9_.+\-]+\.(?:c|h|cc|cpp)|build_source)')
CPUS = frozenset((0x0100000c, 0x01000007))


def _extent(start, size, limit, label):
    if start < 0 or size < 0 or start > limit or size > limit - start:
        raise ValueError('Malformed ' + label + ' extent')


def _no_overlaps(ranges):
    ranges = sorted((start, end) for start, end in ranges if end > start)
    if any(left[1] > right[0] for left, right in zip(ranges, ranges[1:])):
        raise ValueError('Overlapping native metadata extents')


def _label(raw):
    first, _, padding = raw.partition(b'\x00')
    if any(padding): raise ValueError('Malformed native section/segment name')
    return first


def _thin(data, start, size, expected=None):
    _extent(start, size, len(data), 'slice')
    if size < 32: raise ValueError('Truncated native header')
    magic, cpu, subtype, filetype, count, command_bytes, _, _ = struct.unpack_from('<IiiIIIII', data, start)
    if magic != 0xfeedfacf or cpu not in CPUS or filetype not in (2, 6, 8):
        raise ValueError('Unsupported native source-path container')
    if expected is not None and (cpu, subtype) != expected:
        raise ValueError('Universal and slice architecture metadata disagree')
    if count > MAX_LOAD_COMMANDS or command_bytes > MAX_COMMAND_BYTES:
        raise ValueError('Native load command budget exceeded')
    _extent(32, command_bytes, size, 'load commands')
    cursor = 32; end = 32 + command_bytes
    file_segments = []; names = set(); output = []
    for _ in range(count):
        if cursor + 8 > end: raise ValueError('Truncated native load command')
        command, length = struct.unpack_from('<II', data, start + cursor)
        if length < 8 or length % 8 or cursor + length > end:
            raise ValueError('Malformed native load command')
        if command == 0x19:
            if length < 72: raise ValueError('Truncated segment command')
            fields = struct.unpack_from('<II16sQQQQiiII', data, start + cursor)
            _, _, raw_name, address, vm_size, offset, file_size, maximum, initial, section_count, _ = fields
            name = _label(raw_name)
            if name in names or length != 72 + 80 * section_count:
                raise ValueError('Ambiguous segment or section table')
            names.add(name)
            _extent(offset, file_size, size, 'segment')
            if file_size > vm_size or address + vm_size > 1 << 64:
                raise ValueError('Malformed segment mapping')
            if file_size: file_segments.append((offset, offset + file_size))
            section_ranges = []; section_names = set()
            for index in range(section_count):
                values = struct.unpack_from('<16s16sQQIIIIIIII', data, start + cursor + 72 + index * 80)
                raw_section, owner, section_address, section_size, section_offset, alignment, relocation, relocation_count, flags, _, _, _ = values
                section = _label(raw_section)
                if _label(owner) != name or section in section_names or alignment > 31:
                    raise ValueError('Ambiguous native section attribution')
                section_names.add(section)
                if section_address < address or section_address + section_size > address + vm_size:
                    raise ValueError('Native section VM mapping escapes its segment')
                if relocation_count: _extent(relocation, relocation_count * 8, size, 'relocations')
                if flags & 0xff in (1, 0x0c, 0x12): continue
                _extent(section_offset, section_size, size, 'section')
                if (section_offset < offset or section_offset + section_size > offset + file_size
                        or (section_size and section_offset < end)
                        or section_address % (1 << alignment) or section_offset % (1 << alignment)
                        or section_address != address + section_offset - offset):
                    raise ValueError('Native section mapping escapes its segment')
                if section_size: section_ranges.append((section_offset, section_offset + section_size))
                if name == b'__TEXT' and section == b'__cstring' and flags & 0xff == 2:
                    if section_size > MAX_CSTRING_BYTES:
                        raise ValueError('Native C-string section exceeds its bound')
                    if ((maximum | initial) & 2 == 0 and (maximum | initial) & ~7 == 0
                            and maximum & 1 and initial & 1 and initial & maximum == initial
                            and flags & 0x80000400 == 0 and relocation_count == 0):
                        output.append((start + section_offset, start + section_offset + section_size))
            _no_overlaps(section_ranges)
        cursor += length
    if cursor != end: raise ValueError('Native load command totals disagree')
    _no_overlaps(file_segments)
    return output


def _cstring_ranges(data):
    if len(data) >= 4 and data[:4] == b'\xcf\xfa\xed\xfe':
        return _thin(data, 0, len(data))
    if len(data) < 8 or data[:4] not in (b'\xca\xfe\xba\xbe', b'\xca\xfe\xba\xbf'):
        raise ValueError('Unsupported native source-path container')
    count = struct.unpack_from('>I', data, 4)[0]
    if not 1 <= count <= MAX_SLICES: raise ValueError('Universal slice budget exceeded')
    wide = data[:4] == b'\xca\xfe\xba\xbf'; stride = 32 if wide else 20
    table_end = 8 + stride * count
    _extent(8, stride * count, len(data), 'universal table')
    slices = []; identities = set()
    for index in range(count):
        values = struct.unpack_from('>iiQQII' if wide else '>iiIII', data, 8 + index * stride)
        cpu, subtype, offset, size, alignment = values[:5]
        if (cpu not in CPUS or (cpu, subtype) in identities or alignment > 31
                or offset < table_end or offset % (1 << alignment) or (wide and values[5] != 0)):
            raise ValueError('Malformed or ambiguous universal slice')
        identities.add((cpu, subtype)); _extent(offset, size, len(data), 'universal slice')
        slices.append((offset, size, (cpu, subtype)))
    _no_overlaps([(offset, offset + size) for offset, size, _ in slices])
    output = []
    for offset, size, identity in slices: output.extend(_thin(data, offset, size, identity))
    return output


def normalize_source_paths(data: bytes) -> tuple[bytes, int]:
    if type(data) is not bytes or len(data) > MAX_FILE_BYTES:
        raise ValueError('Native source-path input exceeds its type/size bound')
    matches = []
    for match in HOME_PREFIX.finditer(data):
        if len(matches) >= MAX_PATHS: raise ValueError('Native source-path count exceeds its bound')
        matches.append(match)
    if not matches: return data, 0
    ranges = _cstring_ranges(data)
    replacements = []
    for match in matches:
        section = next(((start, end) for start, end in ranges if start <= match.start() and match.end() <= end), None)
        if section is None: raise ValueError('Home prefix is outside a qualified source-path section')
        start, end = section
        literal_start = data.rfind(b'\x00', start, match.start()) + 1
        if literal_start <= start: literal_start = start
        literal_end = data.find(b'\x00', match.end(), end)
        if literal_start != match.start() or literal_end < 0:
            raise ValueError('Home prefix is not a complete source-path literal')
        literal = data[literal_start:literal_end]
        if SOURCE_PATH.fullmatch(literal) is None or len(list(HOME_PREFIX.finditer(literal))) != 1:
            raise ValueError('Home prefix is not an admitted source/build path')
        length = match.end() - match.start()
        if length < 6: raise ValueError('Home prefix cannot be replaced without widening')
        replacements.append((match.start(), match.end(), b'/AIRS/' + b'/' * (length - 6)))
    output = bytearray(data)
    for start, end, value in replacements: output[start:end] = value
    if len(output) != len(data): raise ValueError('Native source-path width changed')
    return bytes(output), len(replacements)
