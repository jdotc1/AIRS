"""Bounded arm64 import-stub attribution through a double indirect-symbol binding.

A `__TEXT` `S_SYMBOL_STUBS` entry is attributed to an undefined external symbol
only when (1) the entry is exactly `ADRP x16; LDR x16, [x16, #imm]; BR x16`,
(2) the loaded 8-byte slot lies in exactly one lazy or non-lazy symbol-pointer
section, and (3) the stub's own indirect entry and the slot's indirect entry
name the same undefined external nlist record. Everything else is declined
with a stable reason, never guessed.

This is attribution only. It decodes no chained fixups or dyld binding
information, so the recorded two-level library ordinal is not a proven runtime
binding, and nothing here claims what the imported callee does at runtime.
The function reads the selected slice bytes itself and requires the raw
section headers to equal the parser-admitted sections.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Mapping

from .types import InputError, MachOImage

STUB_MODEL = 'arm64-import-stub-double-binding-v1'
STUB_SIZE = 12
_SYMBOL_STUBS = 8
_POINTER_TYPES = (6, 7)
_INDIRECT_LOCAL = 0x80000000
_INDIRECT_ABS = 0x40000000
_TOP = 2 ** 64


@dataclass(frozen=True, slots=True)
class StubLimits:
    max_load_commands: int = 4096
    max_sections: int = 4096
    max_stubs: int = 65536
    max_indirect_symbols: int = 1_048_576
    max_symbol_bytes: int = 4096
    max_work: int = 8_000_000

    def __post_init__(self):
        if any(type(getattr(self, key)) is not int or getattr(self, key) < 0
               for key in self.__dataclass_fields__):
            raise InputError('invalid_limits', 'Every stub limit must be a nonnegative integer')


@dataclass(frozen=True, slots=True)
class ImportStub:
    address: int
    section: str
    stub_index: int
    symbol: str
    symbol_index: int
    library_ordinal: int
    pointer_address: int
    pointer_section: str
    provenance: Mapping = field(repr=False)

    def record(self) -> dict:
        provenance = dict(self.provenance)
        provenance['stub_words'] = [dict(word) for word in provenance['stub_words']]
        return dict(address=self.address, section=self.section, stub_index=self.stub_index,
                    symbol=self.symbol, symbol_index=self.symbol_index,
                    library_ordinal=self.library_ordinal, pointer_address=self.pointer_address,
                    pointer_section=self.pointer_section, provenance=provenance)


@dataclass(frozen=True, slots=True)
class StubTable:
    model: str
    complete: bool
    reason: str | None
    attributed: Mapping
    declined: Mapping
    invalid_sections: tuple
    stub_sections: int
    work: int
    valid_sections: tuple = field(default=(), repr=False)

    def lookup(self, address):
        """('attributed', ImportStub), ('declined', reason), or None outside every stub section."""
        if not self.complete:
            return None
        stub = self.attributed.get(address)
        if stub is not None:
            return ('attributed', stub)
        reason = self.declined.get(address)
        if reason is not None:
            return ('declined', reason)
        for start, end, reason in self.invalid_sections:
            if start <= address < end:
                return ('declined', reason)
        for start, end in self.valid_sections:
            if start <= address < end:
                # Every aligned entry of a valid section is attributed or declined.
                return ('declined', 'stub_entry_misaligned')
        return None

    def counts(self) -> dict:
        return dict(attributed_stubs=len(self.attributed), declined_stubs=len(self.declined),
                    invalid_stub_sections=len(self.invalid_sections))


class _Incomplete(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class _RawSection:
    segment: str
    name: str
    address: int
    size: int
    offset: int
    flags: int
    nreloc: int
    reserved1: int
    reserved2: int

    @property
    def label(self):
        return f'{self.segment},{self.name}'

    @property
    def kind(self):
        return self.flags & 0xff


def _empty(model_reason, stub_sections, work):
    return StubTable(STUB_MODEL, False, model_reason, MappingProxyType({}), MappingProxyType({}),
                     (), stub_sections, work)


def attribute_import_stubs(image: MachOImage, *, limits: StubLimits = StubLimits()) -> StubTable:
    if type(image) is not MachOImage or not image.has_valid_admission():
        raise InputError('import_stub_admission', 'Import-stub attribution requires a parser-admitted image')
    if image.architecture != 'arm64' or image.cpu_subtype not in (0, 1):
        raise InputError('import_stub_admission', 'Import-stub attribution requires ordinary arm64')
    if type(limits) is not StubLimits:
        raise InputError('invalid_limits', 'Import-stub limits must be StubLimits')
    state = dict(work=0, stub_sections=0)
    try:
        return _attribute(image, limits, state)
    except _Incomplete as stop:
        return _empty(stop.reason, state['stub_sections'], state['work'])


def _attribute(image, limits, state):
    data = image.data
    size = len(data)

    def charge(amount=1):
        state['work'] += amount
        if state['work'] > limits.max_work:
            raise _Incomplete('stub_work_limit')

    def need(condition, reason):
        if not condition:
            raise _Incomplete(reason)

    def within(offset, length):
        return 0 <= offset and 0 <= length and offset + length <= size

    need(within(0, 32), 'macho_header')
    magic, cputype, _, _, ncmds, sizeofcmds, _, _ = struct.unpack_from('<8I', data, 0)
    need(magic == 0xfeedfacf and cputype == 0x0100000C and within(32, sizeofcmds), 'macho_header')
    need(ncmds <= limits.max_load_commands, 'load_command_limit')
    cursor, end = 32, 32 + sizeofcmds
    raw, symtab, dysymtab = [], None, None
    for _ in range(ncmds):
        charge()
        need(cursor + 8 <= end, 'macho_header')
        command, command_size = struct.unpack_from('<II', data, cursor)
        need(command_size >= 8 and command_size % 8 == 0 and cursor + command_size <= end, 'macho_header')
        if command == 0x19:
            need(command_size >= 72, 'macho_header')
            nsects, = struct.unpack_from('<I', data, cursor + 64)
            need(command_size == 72 + 80 * nsects, 'macho_header')
            need(len(raw) + nsects <= limits.max_sections, 'section_limit')
            for index in range(nsects):
                charge()
                (sectname, segname, address, extent, offset, _, _, nreloc, flags,
                 reserved1, reserved2, _) = struct.unpack_from('<16s16sQQIIIIIIII', data,
                                                               cursor + 72 + 80 * index)
                try:
                    sectname = sectname.split(b'\0', 1)[0].decode('ascii')
                    segname = segname.split(b'\0', 1)[0].decode('ascii')
                except UnicodeDecodeError:
                    raise _Incomplete('raw_section_metadata_mismatch')
                raw.append(_RawSection(segname, sectname, address, extent, offset, flags,
                                       nreloc, reserved1, reserved2))
        elif command == 0x2:
            need(symtab is None and command_size == 24, 'macho_header')
            symtab = struct.unpack_from('<IIII', data, cursor + 8)
        elif command == 0xB:
            need(dysymtab is None and command_size == 80, 'macho_header')
            dysymtab = struct.unpack_from('<18I', data, cursor + 8)
        cursor += command_size
    need(cursor == end, 'macho_header')
    charge(len(raw) + len(image.sections))
    need(tuple((r.segment, r.name, r.address, r.size, r.offset, r.flags) for r in raw)
         == tuple((s.segment, s.name, s.address, s.size, s.file_offset, s.flags) for s in image.sections),
         'raw_section_metadata_mismatch')

    stubs = [r for r in raw if r.kind == _SYMBOL_STUBS]
    state['stub_sections'] = len(stubs)
    if not stubs:
        return StubTable(STUB_MODEL, True, None, MappingProxyType({}), MappingProxyType({}),
                         (), 0, state['work'])
    need(symtab is not None and dysymtab is not None, 'indirect_symbol_table_missing')
    symoff, nsyms, stroff, strsize = symtab
    iundefsym, nundefsym = dysymtab[4], dysymtab[5]
    indirectsymoff, nindirectsyms = dysymtab[12], dysymtab[13]
    need(nindirectsyms <= limits.max_indirect_symbols, 'indirect_symbol_limit')
    need(within(indirectsymoff, 4 * nindirectsyms) and within(symoff, 16 * nsyms)
         and within(stroff, strsize), 'indirect_symbol_table_extent')

    invalid, valid = [], []
    for section in stubs:
        charge()
        if section.segment != '__TEXT':
            reason = 'stub_section_segment'
        elif section.nreloc:
            reason = 'stub_section_relocations'
        elif section.reserved2 != STUB_SIZE:
            reason = 'stub_size_unsupported'
        elif (section.size % STUB_SIZE or section.address % 4 or section.size == 0
              or not within(section.offset, section.size)):
            reason = 'stub_section_extent'
        elif section.reserved1 + section.size // STUB_SIZE > nindirectsyms:
            reason = 'stub_indirect_range'
        else:
            valid.append(section)
            continue
        invalid.append((section.address, section.address + section.size, reason))
    need(sum(section.size // STUB_SIZE for section in valid) <= limits.max_stubs, 'stub_limit')

    pointers = []
    for section in raw:
        if section.kind in _POINTER_TYPES:
            charge()
            pointers.append((section, section.address % 8 == 0 and section.size % 8 == 0
                             and section.reserved1 + section.size // 8 <= nindirectsyms))

    def indirect(index):
        offset = indirectsymoff + 4 * index
        return struct.unpack_from('<I', data, offset)[0], offset

    attributed, declined = {}, {}
    for section in valid:
        for index in range(section.size // STUB_SIZE):
            charge(4 + len(pointers))
            address = section.address + STUB_SIZE * index
            offset = section.offset + STUB_SIZE * index
            words = struct.unpack_from('<III', data, offset)
            reason, stub = _decode_stub(image, limits, charge, section, index, address, offset, words,
                                        pointers, indirect, symtab, iundefsym, nundefsym)
            if stub is None:
                declined[address] = reason
            else:
                attributed[address] = stub
    return StubTable(STUB_MODEL, True, None, MappingProxyType(attributed), MappingProxyType(declined),
                     tuple(invalid), len(stubs), state['work'],
                     tuple((s.address, s.address + s.size) for s in valid))


def _decode_stub(image, limits, charge, section, index, address, offset, words, pointers, indirect,
                 symtab, iundefsym, nundefsym):
    w0, w1, w2 = words
    if not (w0 & 0x9f00001f == 0x90000010 and w1 & 0xffc003ff == 0xf9400210 and w2 == 0xd61f0200):
        return 'stub_instruction_pattern', None
    immediate = (((w0 >> 5) & 0x7ffff) << 2) | ((w0 >> 29) & 3)
    if immediate & (1 << 20):
        immediate -= 1 << 21
    pointer = (address & ~0xfff) + immediate * 4096 + ((w1 >> 10) & 0xfff) * 8
    if pointer < 0 or pointer + 8 > _TOP:
        return 'stub_pointer_unmapped', None
    containing = [(target, ok) for target, ok in pointers
                  if target.address <= pointer and pointer + 8 <= target.address + target.size]
    if len(containing) != 1 or (pointer - containing[0][0].address) % 8:
        return 'stub_pointer_unmapped', None
    target, target_valid = containing[0]
    if not target_valid:
        return 'stub_pointer_section_invalid', None
    slot = (pointer - target.address) // 8
    stub_entry, stub_entry_offset = indirect(section.reserved1 + index)
    pointer_entry, pointer_entry_offset = indirect(target.reserved1 + slot)
    if (stub_entry | pointer_entry) & (_INDIRECT_LOCAL | _INDIRECT_ABS):
        return 'indirect_symbol_local_or_absolute', None
    if stub_entry != pointer_entry:
        return 'stub_pointer_binding_mismatch', None
    symoff, nsyms, stroff, strsize = symtab
    if stub_entry >= nsyms:
        return 'indirect_symbol_index_range', None
    if not iundefsym <= stub_entry < iundefsym + nundefsym:
        return 'indirect_symbol_not_undefined_range', None
    nlist_offset = symoff + 16 * stub_entry
    strx, n_type, n_sect, n_desc, n_value = struct.unpack_from('<IBBHQ', image.data, nlist_offset)
    if n_type & 0xe0 or n_type & 0x0e or not n_type & 0x01 or n_sect or n_value:
        return 'imported_symbol_not_undefined_external', None
    name = _symbol_name(image.data, limits, charge, stroff, strsize, strx)
    if name is None:
        return 'imported_symbol_name', None
    provenance = MappingProxyType(dict(
        stub_words=tuple(MappingProxyType(dict(
            pc=address + 4 * k, word=f'0x{words[k]:08x}', slice_file_offset=offset + 4 * k,
            container_file_offset=offset + 4 * k + image.slice_offset)) for k in range(3)),
        stub_indirect_index=section.reserved1 + index,
        pointer_indirect_index=target.reserved1 + slot,
        stub_indirect_entry_offset=stub_entry_offset,
        pointer_indirect_entry_offset=pointer_entry_offset,
        nlist_offset=nlist_offset))
    return None, ImportStub(address, section.label, index, name, stub_entry, (n_desc >> 8) & 0xff,
                            pointer, target.label, provenance)


def _symbol_name(data, limits, charge, stroff, strsize, strx):
    if not 0 < strx < strsize:
        return None
    start = stroff + strx
    window = min(limits.max_symbol_bytes + 1, strsize - strx)
    terminator = data.find(b'\0', start, start + window)
    charge(window if terminator < 0 else terminator - start + 1)
    if terminator <= start:
        return None
    raw = data[start:terminator]
    if any(byte > 0x7f for byte in raw):
        return None
    return raw.decode('ascii')
