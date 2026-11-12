"""Bounded arm64 GOT-loaded BLR attribution through two independent binding sources.

A plain `BLR Xn` is attributed to an undefined external symbol only when (1) a
proven straight-line window `ADRP Xb; [gap]; LDR Xn, [Xb, #imm]; [gap]; BLR Xn`
loads `Xn` from an 8-byte slot of a valid `S_NON_LAZY_SYMBOL_POINTERS` section,
and (2) the indirect symbol table plus its nlist record (source A) and the
`LC_DYLD_CHAINED_FIXUPS` chain member at that slot plus its import entry
(source B) name the same symbol bytes, library ordinal and weak flag. Every
other outcome is a stable decline reason, never a guess or a one-source
fallback.

This is attribution only. Both tables come from the same linker, so agreement
is internal consistency, not a claim about which library dyld binds at run
time, and nothing here claims what the callee does. The module reads the
selected slice bytes itself, re-walks the load commands and requires the raw
section headers to equal the parser-admitted sections.
"""
from __future__ import annotations

import bisect
import struct
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .types import FunctionRange, InputError, MachOImage

GOT_MODEL = 'arm64-got-blr-two-source-binding-v1'
CHAINED_FIXUPS_MODEL = 'macho-chained-fixups-64-bind-v1'
WINDOW_MODEL = 'adrp-ldr-blr-straight-line-window-v1'
ROW_MODEL = 'swift-broad-got-callsite-v1'
# chained_fixups_status of an incomplete table: never a table-level (6.1) reason and never 'decoded'.
CHAINED_NOT_DECODED = 'not_decoded'

_GOT_TYPE = 6
_ZEROFILL_TYPES = (0x1, 0xC, 0x12)
_INDIRECT_LOCAL = 0x80000000
_INDIRECT_ABS = 0x40000000
_TOP = 2 ** 64
_SEGMENT_64 = 0x19
_SYMTAB = 0x2
_DYSYMTAB = 0xB
_CHAINED_FIXUPS = 0x80000034
_DATA_IN_CODE = 0x29
_DYLD_INFO = (0x22, 0x80000022)
_DYLIB_COMMANDS = (0xC, 0x80000018, 0x8000001F, 0x80000023, 0x20)
_MH_TWOLEVEL = 0x80
_POINTER_FORMATS = (2, 6)
_PAGE_SIZES = (0x1000, 0x4000)
_START_NONE = 0xFFFF
_START_MULTI = 0x8000
_MAX_LIBRARY_ORDINAL = 0xF0
_BLR_MASK, _BLR = 0xfffffc1f, 0xd63f0000


@dataclass(frozen=True, slots=True)
class GotLimits:
    max_load_commands: int = 4096
    max_sections: int = 4096
    max_indirect_symbols: int = 1_048_576
    max_symbol_bytes: int = 4096
    max_got_slots: int = 1_048_576
    max_chained_imports: int = 1_048_576
    max_chain_members: int = 4_000_000
    max_window_gap: int = 3
    max_screen_words: int = 4_000_000
    max_data_in_code_entries: int = 65536
    max_work: int = 16_000_000

    def __post_init__(self):
        if any(type(getattr(self, key)) is not int or getattr(self, key) < 0
               for key in self.__dataclass_fields__):
            raise InputError('invalid_limits', 'Every GOT limit must be a nonnegative integer')


def _thaw(value):
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if type(value) in (tuple, list):
        return [_thaw(item) for item in value]
    return value


def _freeze(value):
    if type(value) is dict:
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if type(value) in (tuple, list):
        return tuple(_freeze(item) for item in value)
    return value


@dataclass(frozen=True, slots=True)
class GotBinding:
    slot_address: int
    slot_section: str
    slot_index: int
    symbol: str
    symbol_index: int
    library_ordinal: int
    library_path: str
    weak_import: bool
    import_ordinal: int
    provenance: Mapping = field(repr=False)

    def record(self) -> dict:
        return dict(slot_address=self.slot_address, slot_section=self.slot_section,
                    slot_index=self.slot_index, symbol=self.symbol, symbol_index=self.symbol_index,
                    library_ordinal=self.library_ordinal, library_path=self.library_path,
                    weak_import=self.weak_import, import_ordinal=self.import_ordinal,
                    provenance=_thaw(self.provenance))


@dataclass(frozen=True, slots=True)
class GotCall:
    call_pc: int
    register: int
    adrp_pc: int
    ldr_pc: int
    gap_ldr_to_blr: int
    gap_adrp_to_ldr: int
    binding: GotBinding
    provenance: Mapping = field(repr=False)

    def record(self) -> dict:
        return dict(call_pc=self.call_pc, register=self.register, adrp_pc=self.adrp_pc,
                    ldr_pc=self.ldr_pc, gap_ldr_to_blr=self.gap_ldr_to_blr,
                    gap_adrp_to_ldr=self.gap_adrp_to_ldr, binding=self.binding.record(),
                    provenance=_thaw(self.provenance))


@dataclass(frozen=True)
class _RawSection:
    segment: str
    name: str
    address: int
    size: int
    offset: int
    flags: int
    reserved1: int

    @property
    def label(self):
        return f'{self.segment},{self.name}'

    @property
    def kind(self):
        return self.flags & 0xff


@dataclass(frozen=True)
class _Segment:
    name: str
    vmaddr: int
    vmsize: int
    fileoff: int
    filesize: int


@dataclass(frozen=True, slots=True)
class GotTable:
    model: str
    complete: bool
    reason: str | None
    chained_fixups_status: str
    bindings: Mapping
    declined_slots: Mapping
    work: int
    _window: object = field(default=None, repr=False, compare=False)

    def classify(self, function, call_pc):
        """None (no GOT shape or incomplete table), ('declined', reason) or ('attributed', GotCall)."""
        if not self.complete or self._window is None:
            return None
        try:
            return self._window.classify(function, call_pc, self.bindings, self.declined_slots)
        except Exception:  # classify never raises; an unexpected state keeps the existing path
            return None

    def counts(self) -> dict:
        return dict(got_slots=len(self.bindings) + len(self.declined_slots),
                    agreeing_got_slots=len(self.bindings), declined_got_slots=len(self.declined_slots))


class _Incomplete(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class _Window:
    """Immutable per-image call-site context: words, entry screen, sections."""

    def __init__(self, data, slice_offset, limits, functions, executable, raw, valid_got,
                 edges, entries, data_in_code):
        self.data = data
        self.slice_offset = slice_offset
        self.gap = limits.max_window_gap
        self.functions = functions
        self.executable = executable
        self.raw = raw
        self.valid_got = valid_got
        self.edges = edges
        self.entries = entries
        self.dic_starts = tuple(start for start, _ in data_in_code)
        self.dic_ends = tuple(end for _, end in data_in_code)

    def _word(self, section, pc):
        return struct.unpack_from('<I', self.data, section.file_offset + pc - section.address)[0]

    def _offset(self, section, pc):
        return section.file_offset + pc - section.address

    def classify(self, function, call_pc, bindings, declined):
        if type(function) is not FunctionRange or function not in self.functions:
            return None
        if type(call_pc) is not int or call_pc % 4 or not function.start <= call_pc < function.end:
            return None
        section = next((s for s in self.executable
                        if s.address <= call_pc and call_pc + 4 <= s.address + s.size), None)
        if section is None:
            return None
        word = self._word(section, call_pc)
        if word & _BLR_MASK != _BLR:
            return None
        register = (word >> 5) & 31
        if register == 31:
            return None
        floor = max(function.start, section.address)

        pc, gap_late = call_pc - 4, 0
        for _ in range(self.gap + 1):
            if pc < floor:
                return None
            load = self._word(section, pc)
            if _skippable(load, register):
                gap_late += 1
                pc -= 4
                continue
            break
        else:
            return None
        if load & 0xffc00000 != 0xf9400000 or load & 31 != register:
            return None
        ldr_pc = pc
        base = (load >> 5) & 31
        offset = ((load >> 10) & 0xfff) * 8

        if base == 31:
            return ('declined', 'got_base_not_adrp')
        pc, gap_early = ldr_pc - 4, 0
        for _ in range(self.gap + 1):
            if pc < floor:
                return ('declined', 'got_window_outside_function')
            adrp = self._word(section, pc)
            if _skippable(adrp, base):
                gap_early += 1
                pc -= 4
                continue
            if adrp & 0x9f000000 != 0x90000000 or adrp & 31 != base:
                return ('declined', 'got_base_not_adrp')
            break
        else:
            return ('declined', 'got_window_gap_limit')
        adrp_pc = pc

        if _hits(self.edges, adrp_pc, call_pc):
            return ('declined', 'got_window_incoming_edge')
        if _hits(self.entries, adrp_pc, call_pc):
            return ('declined', 'got_window_symbol_entry')
        first, last = self._offset(section, adrp_pc), self._offset(section, call_pc) + 4
        index = bisect.bisect_right(self.dic_starts, last - 1) - 1
        if index >= 0 and self.dic_ends[index] > first:
            return ('declined', 'got_window_data_in_code')

        immediate = (((adrp >> 5) & 0x7ffff) << 2) | ((adrp >> 29) & 3)
        if immediate & (1 << 20):
            immediate -= 1 << 21
        slot = (adrp_pc & ~0xfff) + immediate * 4096 + offset
        if slot < 0 or slot + 8 > _TOP:
            return ('declined', 'got_slot_unmapped')
        containing = [r for r in self.raw if r.address <= slot and slot + 8 <= r.address + r.size]
        if len(containing) != 1:
            return ('declined', 'got_slot_unmapped')
        target = containing[0]
        if target.kind != _GOT_TYPE:
            return ('declined', 'got_slot_section_kind')
        if (target.address, target.size, target.offset) not in self.valid_got:
            return ('declined', 'got_slot_section_invalid')
        reason = declined.get(slot)
        if reason is not None:
            return ('declined', reason)
        binding = bindings.get(slot)
        if binding is None:
            # A valid GOT section decodes every aligned slot; this one is misaligned.
            return ('declined', 'got_slot_unmapped')
        words = []
        for pc in range(adrp_pc, call_pc + 4, 4):
            role = ('adrp' if pc == adrp_pc else 'ldr' if pc == ldr_pc
                    else 'blr' if pc == call_pc else 'gap')
            file_offset = self._offset(section, pc)
            words.append(dict(pc=pc, word=f'0x{self._word(section, pc):08x}',
                              slice_file_offset=file_offset,
                              container_file_offset=file_offset + self.slice_offset, role=role))
        provenance = _freeze(dict(model=WINDOW_MODEL, window_words=words))
        return ('attributed', GotCall(call_pc, register, adrp_pc, ldr_pc, gap_late, gap_early,
                                      binding, provenance))


def _skippable(word, register):
    """Closed gap allowlist; each member writes exactly `word & 31` (or nothing)."""
    if word == 0xd503201f:
        return True
    if (word & 0xffe0ffe0 in (0xaa0003e0, 0x2a0003e0)
            or word & 0xff800000 in (0xd2800000, 0x92800000, 0xf2800000,
                                     0x52800000, 0x12800000, 0x72800000)
            or word & 0xff800000 in (0x91000000, 0xd1000000, 0x11000000, 0x51000000)):
        return word & 31 != register
    return False


def _hits(points, low, high):
    """Whether a sorted tuple has a value in (low, high]."""
    index = bisect.bisect_right(points, low)
    return index < len(points) and points[index] <= high


def _sext(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def _empty(reason, work):
    return GotTable(GOT_MODEL, False, reason, CHAINED_NOT_DECODED, MappingProxyType({}),
                    MappingProxyType({}), work)


def attribute_got_bindings(image: MachOImage, *, limits: GotLimits = GotLimits()) -> GotTable:
    if type(image) is not MachOImage or not image.has_valid_admission():
        raise InputError('got_binding_admission', 'GOT attribution requires a parser-admitted image')
    if image.architecture != 'arm64' or image.cpu_subtype not in (0, 1):
        raise InputError('got_binding_admission', 'GOT attribution requires ordinary arm64')
    if type(limits) is not GotLimits:
        raise InputError('invalid_limits', 'GOT limits must be GotLimits')
    state = dict(work=0, members=0)
    try:
        return _attribute(image, limits, state)
    except _Incomplete as stop:
        return _empty(stop.reason, state['work'])


def _attribute(image, limits, state):
    data = image.data
    size = len(data)

    def charge(amount=1):
        state['work'] += amount
        if state['work'] > limits.max_work:
            raise _Incomplete('got_work_limit')

    def need(condition, reason):
        if not condition:
            raise _Incomplete(reason)

    def within(offset, length):
        return 0 <= offset and 0 <= length and offset + length <= size

    # Header and load commands.
    need(within(0, 32), 'macho_header')
    magic, cputype, _, _, ncmds, sizeofcmds, mh_flags, _ = struct.unpack_from('<8I', data, 0)
    need(magic == 0xfeedfacf and cputype == 0x0100000C and within(32, sizeofcmds), 'macho_header')
    need(ncmds <= limits.max_load_commands, 'load_command_limit')
    cursor, end = 32, 32 + sizeofcmds
    raw, segments, dylibs, chained = [], [], [], []
    symtab = dysymtab = data_in_code = None
    classic_binds = False
    for _ in range(ncmds):
        charge()
        need(cursor + 8 <= end, 'macho_header')
        command, command_size = struct.unpack_from('<II', data, cursor)
        need(command_size >= 8 and command_size % 8 == 0 and cursor + command_size <= end, 'macho_header')
        if command == _SEGMENT_64:
            need(command_size >= 72, 'macho_header')
            segname, vmaddr, vmsize, fileoff, filesize = struct.unpack_from('<16sQQQQ', data, cursor + 8)
            nsects, = struct.unpack_from('<I', data, cursor + 64)
            need(command_size == 72 + 80 * nsects, 'macho_header')
            need(len(raw) + nsects <= limits.max_sections, 'section_limit')
            try:
                segname = segname.split(b'\0', 1)[0].decode('ascii')
            except UnicodeDecodeError:
                raise _Incomplete('macho_header')
            segments.append(_Segment(segname, vmaddr, vmsize, fileoff, filesize))
            for index in range(nsects):
                charge()
                (sectname, sectseg, address, extent, offset, _, _, _, flags,
                 reserved1, _, _) = struct.unpack_from('<16s16sQQIIIIIIII', data, cursor + 72 + 80 * index)
                try:
                    sectname = sectname.split(b'\0', 1)[0].decode('ascii')
                    sectseg = sectseg.split(b'\0', 1)[0].decode('ascii')
                except UnicodeDecodeError:
                    raise _Incomplete('raw_section_metadata_mismatch')
                raw.append(_RawSection(sectseg, sectname, address, extent, offset, flags, reserved1))
        elif command == _SYMTAB:
            need(symtab is None and command_size == 24, 'macho_header')
            symtab = struct.unpack_from('<IIII', data, cursor + 8)
        elif command == _DYSYMTAB:
            need(dysymtab is None and command_size == 80, 'macho_header')
            dysymtab = struct.unpack_from('<18I', data, cursor + 8)
        elif command == _DATA_IN_CODE:
            need(data_in_code is None, 'macho_header')
            data_in_code = (struct.unpack_from('<II', data, cursor + 8)
                            if command_size == 16 else None, command_size)
        elif command == _CHAINED_FIXUPS:
            chained.append((command_size, struct.unpack_from('<II', data, cursor + 8)
                            if command_size >= 16 else None))
        elif command in _DYLD_INFO:
            if command_size != 48:
                classic_binds = True
            else:
                fields = struct.unpack_from('<10I', data, cursor + 8)
                if fields[3] or fields[5] or fields[7]:
                    classic_binds = True
        elif command in _DYLIB_COMMANDS:
            dylibs.append((cursor, command_size))
        cursor += command_size
    need(cursor == end, 'macho_header')
    charge(len(raw) + len(image.sections))
    need(tuple((r.segment, r.name, r.address, r.size, r.offset, r.flags) for r in raw)
         == tuple((s.segment, s.name, s.address, s.size, s.file_offset, s.flags) for s in image.sections),
         'raw_section_metadata_mismatch')

    # Symbol tables.
    got_sections = [r for r in raw if r.kind == _GOT_TYPE]
    if got_sections:
        need(symtab is not None and dysymtab is not None, 'indirect_symbol_table_missing')
    nindirectsyms = indirectsymoff = 0
    if dysymtab is not None and got_sections:
        indirectsymoff, nindirectsyms = dysymtab[12], dysymtab[13]
        need(nindirectsyms <= limits.max_indirect_symbols, 'indirect_symbol_limit')
        need(within(indirectsymoff, 4 * nindirectsyms), 'indirect_symbol_table_extent')
    if symtab is not None:
        need(within(symtab[0], 16 * symtab[1]) and within(symtab[2], symtab[3]),
             'indirect_symbol_table_extent')

    # GOT sections and slot limit, before any slot is decoded.
    valid_got = []
    for section in got_sections:
        charge()
        if (section.address % 8 == 0 and section.size % 8 == 0 and section.size > 0
                and within(section.offset, section.size)
                and section.reserved1 + section.size // 8 <= nindirectsyms):
            valid_got.append(section)
    need(sum(section.size // 8 for section in valid_got) <= limits.max_got_slots, 'got_slot_limit')

    # Entry screen over every executable section, built once.
    executable = tuple(s for s in image.sections if s.executable)
    need(sum(s.size // 4 for s in executable) <= limits.max_screen_words, 'got_entry_screen_limit')
    edges = set()
    for section in executable:
        # Words of an executable section must be file backed to be screened.
        need((section.flags & 0xff) not in _ZEROFILL_TYPES and within(section.file_offset, section.size),
             'macho_header')
        count = section.size // 4
        charge(count)
        pc = section.address
        for (word,) in struct.iter_unpack('<I', data[section.file_offset:section.file_offset + 4 * count]):
            if word & 0x7c000000 == 0x14000000:
                edges.add(pc + 4 * _sext(word & 0x3ffffff, 26))
            elif word & 0xff000000 == 0x54000000 or word & 0x7e000000 == 0x34000000:
                edges.add(pc + 4 * _sext((word >> 5) & 0x7ffff, 19))
            elif word & 0x7e000000 == 0x36000000:
                edges.add(pc + 4 * _sext((word >> 5) & 0x3fff, 14))
            pc += 4
    entries = {function.start for function in image.functions}
    charge(len(entries))
    if symtab is not None:
        symoff, nsyms = symtab[0], symtab[1]
        charge(nsyms)
        for index in range(nsyms):
            n_type, = struct.unpack_from('<B', data, symoff + 16 * index + 4)
            if n_type & 0xe0 == 0 and n_type & 0x0e == 0x0e:
                entries.add(struct.unpack_from('<Q', data, symoff + 16 * index + 8)[0])

    # Data in code.
    intervals = []
    if data_in_code is not None:
        fields, command_size = data_in_code
        need(command_size == 16 and fields is not None, 'got_data_in_code_limit')
        dataoff, datasize = fields
        need(datasize % 8 == 0 and within(dataoff, datasize), 'got_data_in_code_limit')
        need(datasize // 8 <= limits.max_data_in_code_entries, 'got_data_in_code_limit')
        charge(datasize // 8)
        spans = sorted((offset, offset + length) for offset, length, _ in
                       struct.iter_unpack('<IHH', data[dataoff:dataoff + datasize]) if length)
        for start, stop in spans:
            if intervals and start <= intervals[-1][1]:
                intervals[-1] = (intervals[-1][0], max(intervals[-1][1], stop))
            else:
                intervals.append((start, stop))

    functions = frozenset(f for f in image.functions if f.boundary_source == 'lc_function_starts')
    window = _Window(data, image.slice_offset, limits, functions, executable, tuple(raw),
                     frozenset((s.address, s.size, s.offset) for s in valid_got),
                     tuple(sorted(edges)), tuple(sorted(entries)), tuple(intervals))

    status, context = _chained_image(data, size, within, charge, limits, mh_flags, chained,
                                     classic_binds, segments, dylibs)
    bindings, declined = {}, {}
    if valid_got:
        symoff, nsyms, stroff, strsize = symtab
        iundefsym, nundefsym = dysymtab[4], dysymtab[5]
        source_b = _SourceB(data, within, charge, limits, state, context, segments)
        for section in valid_got:
            for index in range(section.size // 8):
                charge(8)
                slot = section.address + 8 * index
                if status != 'decoded':
                    declined[slot] = status
                    continue
                reason, binding = _decode_slot(data, limits, charge, section, index, slot, indirectsymoff,
                                               nsyms, symoff, stroff, strsize, iundefsym, nundefsym,
                                               source_b, context, image.slice_offset)
                if binding is None:
                    declined[slot] = reason
                else:
                    bindings[slot] = binding
    return GotTable(GOT_MODEL, True, None, status, MappingProxyType(bindings),
                    MappingProxyType(declined), state['work'], window)


def _chained_image(data, size, within, charge, limits, mh_flags, chained, classic_binds, segments, dylibs):
    """C1 to C6 once per image: ('decoded', context) or (reason, None)."""
    if not chained:
        return 'chained_fixups_absent', None
    if len(chained) > 1:
        return 'chained_fixups_duplicate', None
    command_size, fields = chained[0]
    if command_size != 16:
        return 'chained_fixups_extent', None
    if classic_binds:
        return 'binding_encoding_ambiguous', None
    if not mh_flags & _MH_TWOLEVEL:
        return 'binding_namespace_flat', None
    dataoff, datasize = fields
    linkedit = [s for s in segments if s.name == '__LINKEDIT']
    if not (dataoff % 4 == 0 and datasize >= 28 and within(dataoff, datasize) and len(linkedit) == 1
            and linkedit[0].fileoff <= dataoff
            and dataoff + datasize <= linkedit[0].fileoff + linkedit[0].filesize):
        return 'chained_fixups_extent', None
    (version, starts_offset, imports_offset, symbols_offset, imports_count, imports_format,
     symbols_format) = struct.unpack_from('<7I', data, dataoff)
    if version != 0:
        return 'chained_fixups_version', None
    if not (28 <= starts_offset and starts_offset % 4 == 0
            and starts_offset < imports_offset <= symbols_offset <= datasize):
        return 'chained_header_layout', None
    if imports_format != 1:
        return 'chained_imports_format_unsupported', None
    if symbols_format != 0:
        return 'chained_symbols_compressed', None
    if imports_count > limits.max_chained_imports:
        return 'chained_imports_limit', None
    if imports_offset + 4 * imports_count > symbols_offset:
        return 'chained_header_layout', None
    if starts_offset + 4 > imports_offset:
        return 'chained_starts_layout', None
    seg_count, = struct.unpack_from('<I', data, dataoff + starts_offset)
    if seg_count != len(segments) or starts_offset + 4 + 4 * seg_count > imports_offset:
        return 'chained_starts_layout', None
    charge(seg_count)
    seg_info = struct.unpack_from(f'<{seg_count}I', data, dataoff + starts_offset + 4)
    if len(dylibs) > _MAX_LIBRARY_ORDINAL:
        return 'binding_library_table_limit', None
    paths = []
    for cursor, command_size in dylibs:
        charge(command_size)
        path = None
        if command_size >= 24:
            name_offset, = struct.unpack_from('<I', data, cursor + 8)
            if 24 <= name_offset < command_size:
                terminator = data.find(b'\0', cursor + name_offset, cursor + command_size)
                if terminator > cursor + name_offset:
                    text = data[cursor + name_offset:terminator]
                    if all(byte <= 0x7f for byte in text):
                        path = text.decode('ascii')
        paths.append(path)
    text = [s for s in segments if s.name == '__TEXT']
    if len(text) != 1 or text[0].fileoff != 0:
        return 'chained_starts_layout', None
    return 'decoded', dict(dataoff=dataoff, datasize=datasize, starts_offset=starts_offset,
                           imports_offset=imports_offset, symbols_offset=symbols_offset,
                           imports_count=imports_count, seg_info=seg_info, paths=tuple(paths),
                           image_base=text[0].vmaddr)


class _SourceB:
    """Segment, page and slot levels of the chained-fixups decoder (C7 to C12)."""

    def __init__(self, data, within, charge, limits, state, context, segments):
        self.data, self.within, self.charge = data, within, charge
        self.limits, self.state, self.context, self.segments = limits, state, context, segments
        self.segment_cache, self.page_cache = {}, {}

    def segment(self, index):
        if index not in self.segment_cache:
            self.segment_cache[index] = self._segment(index)
        return self.segment_cache[index]

    def _segment(self, index):
        context, data = self.context, self.data
        seg_info_offset = context['seg_info'][index]
        if seg_info_offset == 0:
            return 'chained_slot_not_covered'
        record = context['starts_offset'] + seg_info_offset
        if record + 22 > context['imports_offset']:
            return 'chained_segment_record_extent'
        base = context['dataoff'] + record
        extent, page_size, pointer_format, segment_offset, max_valid_pointer, page_count = (
            struct.unpack_from('<IHHQIH', data, base))
        if 22 + 2 * page_count > extent or record + extent > context['imports_offset']:
            return 'chained_segment_record_extent'
        segment = self.segments[index]
        if page_size not in _PAGE_SIZES:
            return 'chained_page_size_unsupported'
        if pointer_format not in _POINTER_FORMATS or max_valid_pointer != 0:
            return 'chained_pointer_format_unsupported'
        # SDK fixup-chains.h: segment_offset is the offset in memory to the start of the segment.
        if segment_offset != segment.vmaddr - context['image_base']:
            return 'chained_segment_offset_mismatch'
        if page_count * page_size < segment.vmsize or (page_count - 1) * page_size >= segment.vmsize:
            return 'chained_segment_record_extent'
        self.charge(page_count)
        starts = struct.unpack_from(f'<{page_count}H', data, base + 22)
        return dict(record_offset=base, page_size=page_size, pointer_format=pointer_format,
                    page_starts=starts)

    def page(self, index, record, page):
        key = (index, page)
        if key not in self.page_cache:
            self.page_cache[key] = self._page(index, record, page)
        return self.page_cache[key]

    def _page(self, index, record, page):
        segment, page_size = self.segments[index], record['page_size']
        start = record['page_starts'][page]
        if start == _START_NONE:
            return 'chained_slot_not_covered'
        if start & _START_MULTI:
            return 'chained_page_start_multi'
        if start >= page_size or start % 4:
            return 'chained_chain_malformed'
        limit = segment.vmaddr + min((page + 1) * page_size, segment.filesize)
        member = segment.vmaddr + page * page_size + start
        members, step = {}, 0
        while True:
            if member + 8 > limit:
                return 'chained_chain_malformed'
            file_offset = segment.fileoff + (member - segment.vmaddr)
            if not self.within(file_offset, 8):
                return 'chained_chain_malformed'
            raw, = struct.unpack_from('<Q', self.data, file_offset)
            self.state['members'] += 1
            if self.state['members'] > self.limits.max_chain_members:
                raise _Incomplete('got_work_limit')
            self.charge()
            bind, following = raw >> 63, (raw >> 51) & 0xfff
            if bind:
                if (raw >> 32) & 0x7ffff:
                    return 'chained_pointer_reserved_bits'
                if raw & 0xffffff >= self.context['imports_count']:
                    return 'chained_import_ordinal_range'
            elif (raw >> 44) & 0x7f:
                return 'chained_pointer_reserved_bits'
            members[member] = (raw, step, file_offset)
            if following == 0:
                return members
            if following * 4 < 8:
                return 'chained_chain_malformed'
            member += 4 * following
            step += 1


def _decode_slot(data, limits, charge, section, index, slot, indirectsymoff, nsyms, symoff, stroff,
                 strsize, iundefsym, nundefsym, source_b, context, slice_offset):
    # Source A: indirect symbol table and nlist.
    indirect_offset = indirectsymoff + 4 * (section.reserved1 + index)
    entry, = struct.unpack_from('<I', data, indirect_offset)
    if entry & (_INDIRECT_LOCAL | _INDIRECT_ABS):
        return 'indirect_symbol_local_or_absolute', None
    if entry >= nsyms:
        return 'indirect_symbol_index_range', None
    if not iundefsym <= entry < iundefsym + nundefsym:
        return 'indirect_symbol_not_undefined_range', None
    nlist_offset = symoff + 16 * entry
    strx, n_type, n_sect, n_desc, n_value = struct.unpack_from('<IBBHQ', data, nlist_offset)
    if n_type & 0xe0 or n_type & 0x0e or not n_type & 0x01 or n_sect or n_value:
        return 'imported_symbol_not_undefined_external', None
    name_a = _string(data, limits, charge, stroff, strsize, strx)
    if name_a is None:
        return 'imported_symbol_name', None
    library_a, weak_a = (n_desc >> 8) & 0xff, bool(n_desc & 0x0040)

    # Source B: chained fixups, reached only by walking the slot's page chain.
    containing = [k for k, s in enumerate(source_b.segments)
                  if s.vmaddr <= slot and slot + 8 <= s.vmaddr + s.vmsize]
    if len(containing) != 1:
        return 'got_slot_unmapped', None
    segment_index = containing[0]
    record = source_b.segment(segment_index)
    if type(record) is str:
        return record, None
    segment = source_b.segments[segment_index]
    page = (slot - segment.vmaddr) // record['page_size']
    members = source_b.page(segment_index, record, page)
    if type(members) is str:
        return members, None
    member = members.get(slot)
    if member is None:
        return 'chained_slot_not_member', None
    raw, step, member_offset = member
    if not raw >> 63:
        return 'chained_slot_rebase', None
    ordinal, addend = raw & 0xffffff, (raw >> 24) & 0xff
    if addend:
        return 'chained_bind_addend_nonzero', None
    dataoff, datasize = context['dataoff'], context['datasize']
    import_offset = dataoff + context['imports_offset'] + 4 * ordinal
    value, = struct.unpack_from('<I', data, import_offset)
    library_b, weak_b, name_offset = value & 0xff, bool((value >> 8) & 1), value >> 9
    name_start = context['symbols_offset'] + name_offset
    name_b = None
    if name_start < datasize:
        name_b = _string(data, limits, charge, dataoff, datasize, name_start, allow_zero=True)
    if name_b is None:
        return 'chained_import_name', None

    # Agreement: both sources are required; no fallback, no normalisation.
    if name_a != name_b:
        return 'binding_name_mismatch', None
    if library_a in (0, 0xFE, 0xFF) or library_b == 0 or library_b > _MAX_LIBRARY_ORDINAL:
        return 'binding_library_ordinal_special', None
    paths = context['paths']
    if library_a > len(paths) or library_b > len(paths):
        return 'binding_library_ordinal_range', None
    if library_a != library_b:
        return 'binding_library_mismatch', None
    if weak_a != weak_b:
        return 'binding_weak_mismatch', None
    path = paths[library_a - 1]
    if path is None:
        return 'binding_library_name', None
    chained = dict(model=CHAINED_FIXUPS_MODEL, blob_offset=dataoff, segment_index=segment_index,
                   segment_record_offset=record['record_offset'], pointer_format=record['pointer_format'],
                   page_index=page, page_start=record['page_starts'][page], chain_step=step,
                   member_slice_file_offset=member_offset,
                   member_container_file_offset=member_offset + slice_offset, raw=f'0x{raw:016x}',
                   import_entry_offset=import_offset, name_offset=dataoff + name_start)
    provenance = _freeze(dict(indirect_entry_offset=indirect_offset, nlist_offset=nlist_offset,
                              chained=chained))
    return None, GotBinding(slot, section.label, index, name_a, entry, library_a, path, weak_a,
                            ordinal, provenance)


def _string(data, limits, charge, base, extent, index, *, allow_zero=False):
    """ASCII, nonempty, NUL-terminated within max_symbol_bytes + 1 bytes and the table."""
    if not (0 <= index if allow_zero else 0 < index) or index >= extent:
        return None
    start = base + index
    window = min(limits.max_symbol_bytes + 1, extent - index)
    terminator = data.find(b'\0', start, start + window)
    charge(window if terminator < 0 else terminator - start + 1)
    if terminator <= start:
        return None
    text = data[start:terminator]
    if any(byte > 0x7f for byte in text):
        return None
    return text.decode('ascii')


def got_report_fields(table: GotTable) -> dict:
    """Report keys the GOT profile adds; call-level counters start at zero."""
    return dict(got_binding_model=GOT_MODEL, chained_fixups_model=CHAINED_FIXUPS_MODEL,
                got_window_model=WINDOW_MODEL, got_bindings_complete=table.complete,
                got_binding_reason=table.reason, chained_fixups_status=table.chained_fixups_status,
                got_counts=dict(table.counts(), blr_instructions=0, got_candidates=0,
                                attributed_got_calls=0, declined_got_calls=0, selected_got_calls=0,
                                non_throwing_swift_got_calls=0, non_swift_got_calls=0),
                got_decline_counts={},
                got_slot_decline_counts=dict(sorted(_count(table.declined_slots.values()).items())))


def _count(values):
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def got_callsite_admission(function, pc: int, call: GotCall, declaration: dict, reason: str) -> dict:
    """Attribution and declaration syntax only: no ABI, witness or runtime binding claim."""
    binding = call.binding
    provenance = call.record()['provenance']
    provenance.update(binding=binding.record()['provenance'], got_model=GOT_MODEL)
    return dict(model_version=ROW_MODEL, status='unresolved', reason=reason, call_kind='blr_got',
                call_pc=pc, caller_start=function.start, register=f'x{call.register}',
                adrp_pc=call.adrp_pc, ldr_pc=call.ldr_pc, slot_address=binding.slot_address,
                slot_section=binding.slot_section, symbol=binding.symbol,
                library_ordinal=binding.library_ordinal, library_path=binding.library_path,
                weak_import=binding.weak_import, import_ordinal=binding.import_ordinal,
                declaration=declaration, got_provenance=provenance, details_complete=True,
                call_return_proven=False, syntactic_call_target_admitted=False,
                import_attribution_admitted=True,
                work_steps=16 + len(binding.symbol) + len(provenance['window_words']))
