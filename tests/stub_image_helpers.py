"""Independently assembled thin ARM64 MH_EXECUTE images with import stubs.

Literal layouts from Apple's mach-o/loader.h and mach-o/nlist.h; instruction
words are encoded here from the Arm ARM (ADRP, LDR (immediate, unsigned
offset), LDR (literal), BR, BRAAZ/BRAA, B, BL). No production AIRS code is used
to build these images and none of them is ever executed.

File layout (all offsets are slice-relative; VM = base + file offset):

  0x0000  Mach-O header and load commands (must end before 0x0800)
  0x0800  pointer sections placed in __TEXT (optional, 8-aligned, in order)
  0x1000  __TEXT,__text  (caller functions, one LC_FUNCTION_STARTS entry each)
  next4   __TEXT,__stubs (S_SYMBOL_STUBS, 12-byte entries) when stub_segment
          is '__TEXT'; otherwise at the start of its own r-x segment
  page    one segment per data segment name used by pointer sections
          (__DATA_CONST before __DATA), sections 8-aligned in order (plus any
          per-section misalignment)
  page    __LINKEDIT: function starts, nlist table, indirect table, strings

Symbol order: defined external caller symbols (n_type 0x0f, n_sect 1) first,
then undefined imports (n_type 0x01, n_sect 0, n_value 0,
n_desc = ordinal << 8). Indirect table: the stub section's entries first
(reserved1 = 0), then each pointer section's entries in declaration order.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

PAGE = 0x4000
BASE = 0x100000000
TEXT_OFFSET = 0x1000
TEXT_POINTER_OFFSET = 0x800
STUB_FLAGS = 0x80000408
TEXT_FLAGS = 0x80000400
X16 = 16
X17 = 17
RET = 0xD65F03C0
NOP = 0xD503201F
BR_X16 = 0xD61F0200
BRAAZ_X16 = 0xD61F0A1F
BRAA_X16_X17 = 0xD71F0A11

# Field offsets inside a section_64 header.
SECT_ADDR, SECT_SIZE, SECT_OFFSET, SECT_ALIGN = 32, 40, 48, 52
SECT_FLAGS, SECT_RESERVED1, SECT_RESERVED2 = 64, 68, 72
# Field offsets inside an nlist_64 record.
NL_STRX, NL_TYPE, NL_SECT, NL_DESC, NL_VALUE = 0, 4, 5, 6, 8


def _round(value: int, unit: int) -> int:
    return (value + unit - 1) // unit * unit


def _uleb(value: int) -> bytes:
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


def adrp_imm(rd: int, imm: int) -> int:
    """ADRP Xd, page delta imm (in 4 KiB pages, signed 21-bit)."""
    if not -(1 << 20) <= imm < (1 << 20):
        raise ValueError("ADRP page delta out of range")
    imm &= 0x1FFFFF
    return 0x90000000 | ((imm & 3) << 29) | ((imm >> 2) << 5) | rd


def adrp(rd: int, pc: int, target: int) -> int:
    return adrp_imm(rd, ((target & ~0xFFF) - (pc & ~0xFFF)) >> 12)


def ldr_x_uimm(rt: int, rn: int, byte_offset: int) -> int:
    """LDR Xt, [Xn, #byte_offset] (unsigned offset, scaled by 8)."""
    if byte_offset % 8 or not 0 <= byte_offset // 8 < 4096:
        raise ValueError("LDR offset is not encodable")
    return 0xF9400000 | ((byte_offset // 8) << 10) | (rn << 5) | rt


def ldr_x_literal(rt: int, byte_offset: int) -> int:
    return 0x58000000 | (((byte_offset // 4) & 0x7FFFF) << 5) | rt


def br(rn: int) -> int:
    return 0xD61F0000 | (rn << 5)


def bl(pc: int, target: int) -> int:
    return 0x94000000 | (((target - pc) >> 2) & 0x3FFFFFF)


def b(pc: int, target: int) -> int:
    return 0x14000000 | (((target - pc) >> 2) & 0x3FFFFFF)


def stub_words_for(stub_address: int, pointer_address: int, rd: int = X16) -> tuple[int, int, int]:
    target_page = pointer_address & ~0xFFF
    return (adrp(rd, stub_address, pointer_address),
            ldr_x_uimm(rd, rd, pointer_address - target_page), br(rd))


@dataclass(frozen=True)
class Import:
    name: str | bytes
    ordinal: int = 1


@dataclass(frozen=True)
class PointerSection:
    name: str
    entries: tuple[int, ...]          # import indices -> symbol indices
    kind: int = 6                     # 6 non-lazy, 7 lazy
    segment: str = "__DATA_CONST"     # '__TEXT', '__DATA_CONST' or '__DATA'
    misalign: int = 0                 # bytes added to the 8-aligned address


@dataclass
class Layout:
    base: int
    text_off: int
    text_addr: int
    caller_addrs: list[int]
    stubs_off: int
    stubs_addr: int
    stub_count: int
    stub_section: str
    stub_header_off: int
    stub_pointer_addrs: list[int]
    pointers: dict[str, dict] = field(default_factory=dict)
    section_index: dict[tuple[str, str], int] = field(default_factory=dict)
    symoff: int = 0
    nsyms: int = 0
    stroff: int = 0
    strsize: int = 0
    strx: list[int] = field(default_factory=list)
    names: list[bytes] = field(default_factory=list)
    defined_count: int = 0
    indirect_off: int = 0
    nindirect: int = 0
    symtab_cmd_off: int = 0
    dysymtab_cmd_off: int | None = None
    ncmds: int = 0
    nsections: int = 0
    linkedit_off: int = 0
    function_starts_off: int = 0

    def stub_addr(self, index: int) -> int:
        return self.stubs_addr + 12 * index

    def stub_word_off(self, index: int, word: int) -> int:
        return self.stubs_off + 12 * index + 4 * word

    def import_symbol_index(self, index: int) -> int:
        return self.defined_count + index

    def nlist_off(self, symbol_index: int) -> int:
        return self.symoff + 16 * symbol_index

    def indirect_entry_off(self, entry_index: int) -> int:
        return self.indirect_off + 4 * entry_index

    def dysymtab_word_off(self, word: int) -> int:
        return self.dysymtab_cmd_off + 8 + 4 * word


def patch(data: bytes, offset: int, fmt: str, *values) -> bytes:
    out = bytearray(data)
    struct.pack_into(fmt, out, offset, *values)
    return bytes(out)


def build_stub_image(
    callers: tuple[tuple, ...] = ((("bl", ("stub", 0)), RET),),
    imports: tuple[Import, ...] = (Import("_$s4Test3fooyS2iKF", 2),),
    *,
    stubs: tuple[tuple[int, str, int], ...] | None = None,
    pointer_sections: tuple[PointerSection, ...] | None = None,
    stub_words: dict[int, tuple[int, int, int]] | None = None,
    stub_segment: str = "__TEXT",
    stub_reserved2: int = 12,
    include_stubs: bool = True,
    define_callers: bool = True,
    include_dysymtab: bool = True,
    base: int = BASE,
    cpusubtype: int = 0,
) -> tuple[bytes, Layout]:
    """Build an image. callers: tuple of functions; each item in a function is
    a raw 32-bit word or ('bl'|'b', target) where target is ('stub', i[, delta])
    or an absolute VM address. stubs: (import index, pointer section name, slot)
    per stub; by default stub i -> import i -> '__got' slot i."""
    if stubs is None:
        stubs = tuple((i, "__got", i) for i in range(len(imports))) if include_stubs else ()
    if pointer_sections is None:
        pointer_sections = (PointerSection("__got", tuple(range(len(imports)))),) if include_stubs else ()
    if not include_stubs:
        stubs = ()
    stub_words = dict(stub_words or {})

    # ---- symbols -------------------------------------------------------
    defined_names = [f"_caller{k}".encode() for k in range(len(callers))] if define_callers else []
    import_names = [imp.name.encode() if isinstance(imp.name, str) else imp.name for imp in imports]
    names = defined_names + import_names
    strings = bytearray(b"\0")
    strx = []
    for name in names:
        strx.append(len(strings))
        strings.extend(name + b"\0")
    strings.extend(bytes((-len(strings)) % 8))
    defined_count = len(defined_names)

    # ---- indirect table --------------------------------------------------
    indirect = [defined_count + imp for imp, _, _ in stubs]
    pointer_reserved1 = {}
    for section in pointer_sections:
        pointer_reserved1[section.name] = len(indirect)
        indirect.extend(defined_count + imp for imp in section.entries)

    # ---- __TEXT placement -----------------------------------------------
    text_words_count = [len(fn) for fn in callers]
    text_size = 4 * sum(text_words_count)
    text_off = TEXT_OFFSET
    caller_addrs = []
    cursor = text_off
    for count in text_words_count:
        caller_addrs.append(base + cursor)
        cursor += 4 * count
    text_end = text_off + text_size
    pointer_layout: dict[str, dict] = {}
    position = TEXT_POINTER_OFFSET
    for section in pointer_sections:
        if section.segment != "__TEXT":
            continue
        position = _round(position, 8) + section.misalign
        size = 8 * len(section.entries)
        pointer_layout[section.name] = dict(off=position, size=size)
        position += size
    if position > text_off:
        raise ValueError("__TEXT pointer sections overlap __text")
    stub_size = 12 * len(stubs)
    if stub_segment == "__TEXT":
        stubs_off = _round(text_end, 4)
        text_segment_end = _round(stubs_off + stub_size, PAGE)
        stub_segment_range = None
        next_page = text_segment_end
    else:
        text_segment_end = _round(text_end, PAGE)
        stubs_off = text_segment_end
        stub_segment_range = (stubs_off, _round(stubs_off + max(stub_size, 4), PAGE))
        next_page = stub_segment_range[1]
    stubs_addr = base + stubs_off

    data_segments = []
    for segment_name in ("__DATA_CONST", "__DATA"):
        members = [s for s in pointer_sections if s.segment == segment_name]
        if not members:
            continue
        start = next_page
        position = start
        for section in members:
            position = _round(position, 8) + section.misalign
            size = 8 * len(section.entries)
            pointer_layout[section.name] = dict(off=position, size=size)
            position += size
        end = _round(max(position, start + 1), PAGE)
        data_segments.append((segment_name, start, end, members))
        next_page = end
    linkedit_off = next_page

    for section in pointer_sections:
        entry = pointer_layout[section.name]
        entry.update(addr=base + entry["off"], kind=section.kind, segment=section.segment,
                     reserved1=pointer_reserved1[section.name],
                     section=f"{section.segment},{section.name}",
                     align=3 if (base + entry["off"]) % 8 == 0 else 2)

    # ---- code bytes ------------------------------------------------------
    def resolve(target):
        if isinstance(target, int):
            return target
        kind, index, *rest = target
        if kind != "stub":
            raise ValueError(target)
        return stubs_addr + 12 * index + (rest[0] if rest else 0)

    text = bytearray()
    for fn, start in zip(callers, caller_addrs):
        for k, item in enumerate(fn):
            pc = start + 4 * k
            if isinstance(item, int):
                word = item
            else:
                op, target = item
                word = (bl if op == "bl" else b)(pc, resolve(target))
            text += struct.pack("<I", word)
    stub_bytes = bytearray()
    stub_pointer_addrs = []
    for i, (_, pointer_name, slot) in enumerate(stubs):
        address = stubs_addr + 12 * i
        pointer_address = pointer_layout[pointer_name]["addr"] + 8 * slot
        stub_pointer_addrs.append(pointer_address)
        words = stub_words.get(i) or stub_words_for(address, pointer_address)
        stub_bytes += struct.pack("<III", *words)

    # ---- __LINKEDIT --------------------------------------------------------
    linkedit = bytearray()
    function_starts_off = linkedit_off
    previous = base
    for address in caller_addrs:
        linkedit += _uleb(address - previous)
        previous = address
    linkedit += b"\0"
    linkedit += bytes((-len(linkedit)) % 8)
    function_starts_size = len(linkedit)
    symoff = linkedit_off + len(linkedit)
    for k in range(defined_count):
        linkedit += struct.pack("<IBBHQ", strx[k], 0x0F, 1, 0, caller_addrs[k])
    for j, imp in enumerate(imports):
        linkedit += struct.pack("<IBBHQ", strx[defined_count + j], 0x01, 0, (imp.ordinal & 0xFF) << 8, 0)
    indirect_off = linkedit_off + len(linkedit)
    linkedit += b"".join(struct.pack("<I", e) for e in indirect)
    linkedit += bytes((-len(linkedit)) % 8)
    stroff = linkedit_off + len(linkedit)
    linkedit += strings
    total = linkedit_off + len(linkedit)

    # ---- load commands -----------------------------------------------------
    section_index: dict[tuple[str, str], int] = {}
    commands: list[bytes] = []
    headers_order: list[tuple[str, str]] = []

    def section_header(sectname, segname, address, size, offset, align, flags, r1, r2):
        return struct.pack("<16s16sQQIIIIIIII", sectname.encode(), segname.encode(), address, size,
                           offset, align, 0, 0, flags, r1, r2, 0)

    def segment(name, vmaddr, vmsize, fileoff, filesize, prot, sections):
        return struct.pack("<II16sQQQQiiII", 0x19, 72 + 80 * len(sections), name.encode(), vmaddr,
                           vmsize, fileoff, filesize, prot, prot, len(sections), 0) + b"".join(sections)

    commands.append(segment("__PAGEZERO", 0, base, 0, 0, 0, []))
    text_sections = [(("__TEXT", "__text"), section_header("__text", "__TEXT", base + text_off, text_size,
                                                          text_off, 2, TEXT_FLAGS, 0, 0))]
    if stubs and stub_segment == "__TEXT":
        text_sections.append((("__TEXT", "__stubs"), section_header(
            "__stubs", "__TEXT", stubs_addr, stub_size, stubs_off, 2, STUB_FLAGS, 0, stub_reserved2)))
    for section in pointer_sections:
        if section.segment == "__TEXT":
            p = pointer_layout[section.name]
            text_sections.append((("__TEXT", section.name), section_header(
                section.name, "__TEXT", p["addr"], p["size"], p["off"], p["align"], section.kind,
                p["reserved1"], 0)))
    segment_specs = [("__TEXT", base, text_segment_end, 0, text_segment_end, 5, text_sections)]
    if stubs and stub_segment != "__TEXT":
        start, end = stub_segment_range
        segment_specs.append((stub_segment, base + start, end - start, start, end - start, 5,
                              [((stub_segment, "__stubs"), section_header(
                                  "__stubs", stub_segment, stubs_addr, stub_size, stubs_off, 2,
                                  STUB_FLAGS, 0, stub_reserved2))]))
    for segment_name, start, end, members in data_segments:
        rows = []
        for section in members:
            p = pointer_layout[section.name]
            rows.append(((segment_name, section.name), section_header(
                section.name, segment_name, p["addr"], p["size"], p["off"], p["align"], section.kind,
                p["reserved1"], 0)))
        segment_specs.append((segment_name, base + start, end - start, start, end - start, 3, rows))
    linkedit_vmsize = _round(total - linkedit_off, PAGE)
    segment_specs.append(("__LINKEDIT", base + linkedit_off, linkedit_vmsize, linkedit_off,
                          total - linkedit_off, 1, []))

    stub_header_off = None
    cursor = 32 + len(commands[0])
    for name, vmaddr, vmsize, fileoff, filesize, prot, rows in segment_specs:
        for j, (key, _) in enumerate(rows):
            headers_order.append(key)
            section_index[key] = len(headers_order)
            if key[1] == "__stubs":
                stub_header_off = cursor + 72 + 80 * j
            if key[1] in pointer_layout and key[0] == pointer_layout[key[1]]["segment"]:
                pointer_layout[key[1]]["header_off"] = cursor + 72 + 80 * j
        command = segment(name, vmaddr, vmsize, fileoff, filesize, prot, [row for _, row in rows])
        commands.append(command)
        cursor += len(command)
    commands.append(struct.pack("<IIII", 0x26, 16, function_starts_off, function_starts_size))
    symtab_cmd_off = cursor + 16
    commands.append(struct.pack("<IIIIII", 2, 24, symoff, len(names), stroff, len(strings)))
    dysymtab_cmd_off = None
    if include_dysymtab:
        dysymtab_cmd_off = symtab_cmd_off + 24
        commands.append(struct.pack("<II18I", 0xB, 80, 0, 0, 0, defined_count, defined_count,
                                    len(imports), 0, 0, 0, 0, 0, 0, indirect_off, len(indirect),
                                    0, 0, 0, 0))
    commands.append(struct.pack("<II", 0x1B, 24) + bytes(range(16, 32)))
    command_bytes = b"".join(commands)
    header = struct.pack("<IIIIIIII", 0xFEEDFACF, 0x0100000C, cpusubtype, 2, len(commands),
                         len(command_bytes), 0x00200084, 0)
    if 32 + len(command_bytes) > TEXT_POINTER_OFFSET:
        raise ValueError("load commands overlap section data")

    payload = bytearray(total)
    payload[:32 + len(command_bytes)] = header + command_bytes
    payload[text_off:text_off + text_size] = text
    payload[stubs_off:stubs_off + stub_size] = stub_bytes
    for section in pointer_sections:
        p = pointer_layout[section.name]
        # Rebased pointer contents are unspecified; zero-filled like unbound slots.
        payload[p["off"]:p["off"] + p["size"]] = bytes(p["size"])
    payload[linkedit_off:total] = linkedit

    layout = Layout(base=base, text_off=text_off, text_addr=base + text_off, caller_addrs=caller_addrs,
                    stubs_off=stubs_off, stubs_addr=stubs_addr, stub_count=len(stubs),
                    stub_section=f"{stub_segment},__stubs", stub_header_off=stub_header_off,
                    stub_pointer_addrs=stub_pointer_addrs, pointers=pointer_layout,
                    section_index=section_index, symoff=symoff, nsyms=len(names), stroff=stroff,
                    strsize=len(strings), strx=strx, names=names, defined_count=defined_count,
                    indirect_off=indirect_off, nindirect=len(indirect), symtab_cmd_off=symtab_cmd_off,
                    dysymtab_cmd_off=dysymtab_cmd_off, ncmds=len(commands),
                    nsections=len(headers_order), linkedit_off=linkedit_off,
                    function_starts_off=function_starts_off)
    return bytes(payload), layout
