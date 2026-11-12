"""Independently assembled thin ARM64 MH_EXECUTE images with GOT-loaded BLR sites.

Literal layouts from Apple's mach-o/loader.h, mach-o/nlist.h and
mach-o/fixup-chains.h; instruction words are encoded here from the Arm ARM
(ADRP, LDR (immediate, unsigned offset), BLR, MOV, MOVZ/MOVN/MOVK, ADD/SUB
(immediate), B, BL, B.cond, CBZ, TBZ). No production AIRS code is used to
build these images and none of them is ever executed.

File layout (all offsets slice-relative; a segment's VM is base + file offset,
plus vm_gap for every segment after __TEXT):

  0x0000  Mach-O header and load commands
  text    __TEXT,__text at 0x1000 (or the next 4 KiB boundary after the load
          commands); one LC_FUNCTION_STARTS entry per caller function
  page    one segment per data segment name used by pointer sections
          (__DATA_CONST before __DATA), starting data_pad bytes into the
          segment, sections 8-aligned in order (plus any per-section misalign)
  page    __LINKEDIT: chained-fixups blob, optional dyld-info payload,
          function starts, data-in-code entries, nlist table, indirect table,
          strings

Chained-fixups blob (LC_DYLD_CHAINED_FIXUPS payload, 8-aligned at the start of
__LINKEDIT): 28-byte header padded to starts_offset 0x20; starts_in_image
(seg_count = every LC_SEGMENT_64, in load-command order); one 8-aligned
starts_in_segment record per data segment that holds a chained slot; the
imports table (DYLD_CHAINED_IMPORT, import i = imports[i]); the symbol pool
(byte 0 is NUL, then every import name NUL-terminated in import order).
Every slot of a 'bind' pointer section is a bind member (ordinal = its import
index, addend 0); a 'rebase' section's words are rebase members; members of
one page are chained in address order, each page's chain ends with next = 0.

Symbol order: local defined symbols (extra_symbols), defined external caller
symbols (n_type 0x0f, n_sect 1), then undefined imports (n_type 0x01, n_sect 0,
n_value 0, n_desc = ordinal << 8 | N_WEAK_REF if weak). Indirect table: each
type 6/7 pointer section's entries in declaration order.
"""
from __future__ import annotations

import struct
from dataclasses import dataclass, field

PAGE = 0x4000
BASE = 0x100000000
TEXT_FLAGS = 0x80000400
HEADER_FLAGS = 0x00200085          # NOUNDEFS | DYLDLINK | TWOLEVEL | PIE
MH_TWOLEVEL = 0x80
LC_LOAD_DYLIB = 0xC
LC_LOAD_WEAK_DYLIB = 0x80000018
LC_REEXPORT_DYLIB = 0x8000001F
LC_LOAD_UPWARD_DYLIB = 0x80000023
LC_LAZY_LOAD_DYLIB = 0x20
LC_LOAD_DYLINKER = 0xE
LC_DYLD_CHAINED_FIXUPS = 0x80000034
LC_DYLD_INFO_ONLY = 0x80000022
LC_DATA_IN_CODE = 0x29
X16 = 16
X17 = 17
RET = 0xD65F03C0
NOP = 0xD503201F

# Field offsets inside a section_64 header.
SECT_ADDR, SECT_SIZE, SECT_OFFSET, SECT_ALIGN = 32, 40, 48, 52
SECT_FLAGS, SECT_RESERVED1, SECT_RESERVED2 = 64, 68, 72
# Field offsets inside an nlist_64 record.
NL_STRX, NL_TYPE, NL_SECT, NL_DESC, NL_VALUE = 0, 4, 5, 6, 8
# Chained fixups header fields (blob-relative).
CF_VERSION, CF_STARTS, CF_IMPORTS, CF_SYMBOLS, CF_COUNT, CF_IMPORTS_FORMAT, CF_SYMBOLS_FORMAT = range(0, 28, 4)
# starts_in_segment fields (record-relative).
SS_SIZE, SS_PAGE_SIZE, SS_FORMAT, SS_SEGMENT_OFFSET, SS_MAX_VALID, SS_PAGE_COUNT, SS_PAGE_START = (
    0, 4, 6, 8, 16, 20, 22)


def _round(value: int, unit: int) -> int:
    return (value + unit - 1) // unit * unit


def _uleb(value: int) -> bytes:
    out = bytearray()
    while value >= 0x80:
        out.append((value & 0x7F) | 0x80)
        value >>= 7
    out.append(value)
    return bytes(out)


# ---- instruction encoders (Arm ARM) ------------------------------------------
def adrp_imm(rd: int, imm: int) -> int:
    """ADRP Xd, page delta imm (in 4 KiB pages, signed 21-bit)."""
    if not -(1 << 20) <= imm < (1 << 20):
        raise ValueError("ADRP page delta out of range")
    imm &= 0x1FFFFF
    return 0x90000000 | ((imm & 3) << 29) | ((imm >> 2) << 5) | rd


def adrp(rd: int, pc: int, target: int) -> int:
    return adrp_imm(rd, ((target & ~0xFFF) - (pc & ~0xFFF)) >> 12)


def adr(rd: int, imm: int = 0) -> int:
    imm &= 0x1FFFFF
    return 0x10000000 | ((imm & 3) << 29) | ((imm >> 2) << 5) | rd


def ldr_x_uimm(rt: int, rn: int, byte_offset: int) -> int:
    """LDR Xt, [Xn, #byte_offset] (unsigned offset, scaled by 8)."""
    if byte_offset % 8 or not 0 <= byte_offset // 8 < 4096:
        raise ValueError("LDR offset is not encodable")
    return 0xF9400000 | ((byte_offset // 8) << 10) | (rn << 5) | rt


def ldr_w_uimm(rt: int, rn: int, byte_offset: int) -> int:
    """LDR Wt, [Xn, #byte_offset] (32-bit, scaled by 4)."""
    return 0xB9400000 | ((byte_offset // 4) << 10) | (rn << 5) | rt


def ldur_x(rt: int, rn: int, simm9: int) -> int:
    return 0xF8400000 | ((simm9 & 0x1FF) << 12) | (rn << 5) | rt


def ldr_x_literal(rt: int, byte_offset: int) -> int:
    return 0x58000000 | (((byte_offset // 4) & 0x7FFFF) << 5) | rt


def blr(rn: int) -> int:
    return 0xD63F0000 | (rn << 5)


def br(rn: int) -> int:
    return 0xD61F0000 | (rn << 5)


def blraaz(rn: int) -> int:
    return 0xD63F081F | (rn << 5)


def mov_x(rd: int, rm: int) -> int:
    """MOV Xd, Xm (ORR shifted register, Rn = XZR, shift 0)."""
    return 0xAA0003E0 | (rm << 16) | rd


def mov_w(rd: int, rm: int) -> int:
    return 0x2A0003E0 | (rm << 16) | rd


def movz_x(rd: int, imm16: int, hw: int = 0) -> int:
    return 0xD2800000 | (hw << 21) | (imm16 << 5) | rd


def movn_x(rd: int, imm16: int) -> int:
    return 0x92800000 | (imm16 << 5) | rd


def movk_x(rd: int, imm16: int) -> int:
    return 0xF2800000 | (imm16 << 5) | rd


def movz_w(rd: int, imm16: int) -> int:
    return 0x52800000 | (imm16 << 5) | rd


def movn_w(rd: int, imm16: int) -> int:
    return 0x12800000 | (imm16 << 5) | rd


def movk_w(rd: int, imm16: int) -> int:
    return 0x72800000 | (imm16 << 5) | rd


def add_x_imm(rd: int, rn: int, imm12: int) -> int:
    return 0x91000000 | (imm12 << 10) | (rn << 5) | rd


def sub_x_imm(rd: int, rn: int, imm12: int) -> int:
    return 0xD1000000 | (imm12 << 10) | (rn << 5) | rd


def add_w_imm(rd: int, rn: int, imm12: int) -> int:
    return 0x11000000 | (imm12 << 10) | (rn << 5) | rd


def sub_w_imm(rd: int, rn: int, imm12: int) -> int:
    return 0x51000000 | (imm12 << 10) | (rn << 5) | rd


def adds_x_imm(rd: int, rn: int, imm12: int) -> int:
    """ADDS (sets flags): not in the gap allowlist."""
    return 0xB1000000 | (imm12 << 10) | (rn << 5) | rd


def addg(rd: int, rn: int) -> int:
    """ADDG Xd, Xn, #0, #0 (bit 23 set): excluded by the 0xff800000 mask."""
    return 0x91800000 | (rn << 5) | rd


def orr_x_shifted(rd: int, rn: int, rm: int, shift: int) -> int:
    """ORR Xd, Xn, Xm, LSL #shift: not the MOV alias unless rn = 31 and shift = 0."""
    return 0xAA000000 | (rm << 16) | (shift << 10) | (rn << 5) | rd


def b(pc: int, target: int) -> int:
    return 0x14000000 | (((target - pc) >> 2) & 0x3FFFFFF)


def bl(pc: int, target: int) -> int:
    return 0x94000000 | (((target - pc) >> 2) & 0x3FFFFFF)


def bcond(pc: int, target: int, cond: int = 0) -> int:
    return 0x54000000 | ((((target - pc) >> 2) & 0x7FFFF) << 5) | cond


def cbz(pc: int, target: int, rt: int = 0) -> int:
    return 0xB4000000 | ((((target - pc) >> 2) & 0x7FFFF) << 5) | rt


def cbnz_w(pc: int, target: int, rt: int = 0) -> int:
    return 0x35000000 | ((((target - pc) >> 2) & 0x7FFFF) << 5) | rt


def tbz(pc: int, target: int, rt: int = 0, bit: int = 0) -> int:
    return 0x36000000 | ((bit & 0x1F) << 19) | ((((target - pc) >> 2) & 0x3FFF) << 5) | rt


def tbnz(pc: int, target: int, rt: int = 0, bit: int = 0) -> int:
    return 0x37000000 | ((bit & 0x1F) << 19) | ((((target - pc) >> 2) & 0x3FFF) << 5) | rt


_BRANCHES = {'b': b, 'bl': bl, 'bcond': bcond, 'cbz': cbz, 'cbnz_w': cbnz_w, 'tbz': tbz, 'tbnz': tbnz}


def bind_raw(ordinal: int, next_: int = 0, addend: int = 0, reserved: int = 0) -> int:
    """DYLD_CHAINED_PTR_64 bind: ordinal 24, addend 8, reserved 19, next 12, bind 1."""
    return (1 << 63) | ((next_ & 0xFFF) << 51) | ((reserved & 0x7FFFF) << 32) | ((addend & 0xFF) << 24) | ordinal


def rebase_raw(target: int, next_: int = 0, high8: int = 0, reserved: int = 0) -> int:
    """DYLD_CHAINED_PTR_64 rebase: target 36, high8 8, reserved 7, next 12, bind 0."""
    return ((next_ & 0xFFF) << 51) | ((reserved & 0x7F) << 44) | ((high8 & 0xFF) << 36) | (target & 0xFFFFFFFFF)


def patch(data: bytes, offset: int, fmt: str, *values) -> bytes:
    out = bytearray(data)
    struct.pack_into(fmt, out, offset, *values)
    return bytes(out)


def u32(data: bytes, offset: int) -> int:
    return struct.unpack_from('<I', data, offset)[0]


def u64(data: bytes, offset: int) -> int:
    return struct.unpack_from('<Q', data, offset)[0]


@dataclass(frozen=True)
class GotImport:
    name: str | bytes
    ordinal: int = 2           # two-level library ordinal (nlist) == chained lib_ordinal
    weak: bool = False         # N_WEAK_REF and chained weak_import


@dataclass(frozen=True)
class PtrSection:
    name: str
    entries: tuple[int, ...]   # import index per 8-byte slot (types 6/7); word count otherwise
    kind: int = 6              # 6 non-lazy, 7 lazy, 0x14 thread-local pointers, 0 regular
    segment: str = '__DATA_CONST'
    misalign: int = 0          # bytes added to the 8-aligned address
    fixup: str = 'bind'        # 'bind', 'rebase' or 'none' (not a chain member)
    extra_size: int = 0        # bytes added to the section size (beyond 8 * len(entries))


DEFAULT_DYLIBS = ('/usr/lib/libSystem.B.dylib', '/usr/lib/swift/libswiftCore.dylib')
THROWING = '_$s4Test3fooyS2iKF'


def got_call(section: str = '__got', slot: int = 0, rd: int = X16, rn: int | None = None) -> tuple:
    """ADRP rn, slot page; LDR rd, [rn, #pageoff]; BLR rd."""
    rn = rd if rn is None else rn
    ref = ('slot', section, slot)
    return (('adrp', rn, ref), ('ldr', rd, rn, ref), blr(rd))


@dataclass
class GotLayout:
    base: int
    text_off: int
    text_addr: int
    text_size: int
    caller_addrs: list[int]
    caller_sizes: list[int]
    pointers: dict[str, dict] = field(default_factory=dict)
    segments: list[dict] = field(default_factory=list)
    blob_off: int | None = None
    blob_size: int = 0
    starts_offset: int = 0
    imports_offset: int = 0
    symbols_offset: int = 0
    seg_records: dict[str, int] = field(default_factory=dict)      # segment name -> blob-relative record
    seg_info_offsets: list[int] = field(default_factory=list)
    pool_name_offsets: list[int] = field(default_factory=list)     # pool-relative, per import
    members: dict[str, list[tuple[int, int]]] = field(default_factory=dict)  # segment -> [(vm, raw)]
    chained_cmd_off: int | None = None
    dylib_cmd_offs: list[int] = field(default_factory=list)
    dylib_paths: list[str] = field(default_factory=list)
    dyld_info_cmd_off: int | None = None
    data_in_code_cmd_off: int | None = None
    data_in_code_off: int = 0
    symoff: int = 0
    nsyms: int = 0
    stroff: int = 0
    strsize: int = 0
    strx: list[int] = field(default_factory=list)
    local_count: int = 0
    defined_count: int = 0
    indirect_off: int = 0
    nindirect: int = 0
    symtab_cmd_off: int = 0
    dysymtab_cmd_off: int | None = None
    ncmds: int = 0
    nsections: int = 0
    nsegments: int = 0
    linkedit_off: int = 0
    total: int = 0
    executable_words: int = 0

    # -- addresses --------------------------------------------------------
    def word_addr(self, fn: int, k: int) -> int:
        return self.caller_addrs[fn] + 4 * k

    def word_off(self, fn: int, k: int) -> int:
        return self.word_addr(fn, k) - self.base

    def slot_addr(self, section: str, k: int) -> int:
        return self.pointers[section]['addr'] + 8 * k

    def slot_off(self, section: str, k: int) -> int:
        return self.pointers[section]['off'] + 8 * k

    def section_header_off(self, section: str) -> int:
        return self.pointers[section]['header_off']

    def segment(self, name: str) -> dict:
        return next(s for s in self.segments if s['name'] == name)

    # -- symbol tables ------------------------------------------------------
    def import_symbol_index(self, index: int) -> int:
        return self.local_count + self.defined_count + index

    def nlist_off(self, symbol_index: int) -> int:
        return self.symoff + 16 * symbol_index

    def import_nlist_off(self, index: int) -> int:
        return self.nlist_off(self.import_symbol_index(index))

    def indirect_entry_off(self, entry_index: int) -> int:
        return self.indirect_off + 4 * entry_index

    def slot_indirect_off(self, section: str, k: int) -> int:
        return self.indirect_entry_off(self.pointers[section]['reserved1'] + k)

    def symbol_name_off(self, symbol_index: int) -> int:
        return self.stroff + self.strx[symbol_index]

    def dysymtab_word_off(self, word: int) -> int:
        return self.dysymtab_cmd_off + 8 + 4 * word

    # -- chained fixups (slice file offsets unless noted) -------------------------
    def blob(self, rel: int) -> int:
        return self.blob_off + rel

    def chained_cmd_field(self, word: int) -> int:
        """word 0 cmd, 1 cmdsize, 2 dataoff, 3 datasize."""
        return self.chained_cmd_off + 4 * word

    def seg_info_entry_off(self, segment_index: int) -> int:
        return self.blob(self.starts_offset + 4 + 4 * segment_index)

    def seg_record_off(self, segment: str = '__DATA_CONST') -> int:
        return self.blob(self.seg_records[segment])

    def page_start_off(self, segment: str = '__DATA_CONST', page: int = 0) -> int:
        return self.seg_record_off(segment) + SS_PAGE_START + 2 * page

    def import_entry_off(self, index: int) -> int:
        return self.blob(self.imports_offset + 4 * index)

    def pool_name_off(self, index: int) -> int:
        return self.blob(self.symbols_offset + self.pool_name_offsets[index])

    def segment_index(self, name: str) -> int:
        return next(i for i, s in enumerate(self.segments) if s['name'] == name)


def build_got_image(
    callers: tuple[tuple, ...] | None = None,
    imports: tuple[GotImport, ...] = (GotImport(THROWING),),
    *,
    pointer_sections: tuple[PtrSection, ...] | None = None,
    dylibs: tuple = DEFAULT_DYLIBS,
    extra_symbols: tuple[tuple[str, int | tuple, int], ...] = (),
    define_callers: bool = True,
    include_symtab: bool = True,
    include_dysymtab: bool = True,
    include_chained: bool = True,
    duplicate_chained: bool = False,
    pointer_format: int = 6,
    page_size: int = PAGE,
    data_pad: int = 0,
    vm_gap: int = 0,
    segment_offset_override: dict[str, int] | None = None,
    dyld_info: tuple[int, int, int, int, int] | None = None,
    data_in_code: tuple[tuple, ...] | None = None,
    header_flags: int = HEADER_FLAGS,
    base: int = BASE,
    cpusubtype: int = 0,
) -> tuple[bytes, GotLayout]:
    """Build an image.

    callers: tuple of functions; each item is a raw 32-bit word, or
    ('adrp', rd, ref), ('ldr', rt, rn, ref) with ref = ('slot', section, k[, delta])
    or an absolute VM address, or (branch, target[, extra args]) with branch in
    b/bl/bcond/cbz/cbnz_w/tbz/tbnz and target an absolute VM address or
    ('word', fn, k). dylibs: paths (LC_LOAD_DYLIB) or (cmd, path) pairs; a
    (LC_LOAD_DYLINKER, path) entry is emitted but is not a dylib ordinal.
    extra_symbols: (name, address or ('word', fn, k), n_type) local defined
    symbols in __text (n_sect 1). dyld_info: (rebase, bind, weak_bind,
    lazy_bind, export) sizes of an LC_DYLD_INFO_ONLY whose payloads all point at
    one 16-byte zero block. data_in_code: (('word', fn, k) or file offset,
    length) entries.
    """
    if callers is None:
        callers = (got_call() + (RET,),)
    if pointer_sections is None:
        pointer_sections = (PtrSection('__got', tuple(range(len(imports)))),)

    # ---- symbols ----------------------------------------------------------
    local_names = [s[0].encode() for s in extra_symbols]
    defined_names = [f"_caller{k}".encode() for k in range(len(callers))] if define_callers else []
    import_names = [imp.name.encode() if isinstance(imp.name, str) else imp.name for imp in imports]
    names = local_names + defined_names + import_names
    strings = bytearray(b"\0")
    strx = []
    for name in names:
        strx.append(len(strings))
        strings.extend(name + b"\0")
    strings.extend(bytes((-len(strings)) % 8))
    local_count, defined_count = len(local_names), len(defined_names)
    first_import = local_count + defined_count

    # ---- indirect table -----------------------------------------------------
    indirect: list[int] = []
    reserved1 = {}
    for section in pointer_sections:
        reserved1[section.name] = len(indirect) if section.kind in (6, 7) else 0
        if section.kind in (6, 7):
            indirect.extend(first_import + imp for imp in section.entries)

    # ---- dylib commands (sizes only; placement below) -------------------------
    dylib_specs = [(LC_LOAD_DYLIB, d) if isinstance(d, str) else d for d in dylibs]

    def dylib_command(cmd, path):
        raw = path.encode() if isinstance(path, str) else path
        if cmd == LC_LOAD_DYLINKER:
            size = _round(12 + len(raw) + 1, 8)
            return struct.pack('<III', cmd, size, 12) + raw + bytes(size - 12 - len(raw))
        size = _round(24 + len(raw) + 1, 8)
        return struct.pack('<IIIIII', cmd, size, 24, 2, 0x10000, 0x10000) + raw + bytes(size - 24 - len(raw))

    dylib_blobs = [dylib_command(cmd, path) for cmd, path in dylib_specs]
    data_segment_names = [n for n in ('__DATA_CONST', '__DATA') if any(s.segment == n for s in pointer_sections)]
    nsegments = 3 + len(data_segment_names)
    nsections = 1 + len(pointer_sections)
    cmd_bytes_estimate = (72 + 80 + 72 * (nsegments - 1) + 80 * len(pointer_sections) + 16 * (2 + duplicate_chained)
                          + 24 + 80 + 48 + 16 + 24 + sum(len(x) for x in dylib_blobs))
    text_off = max(0x1000, _round(32 + cmd_bytes_estimate, 0x1000))

    # ---- __TEXT placement -----------------------------------------------------
    sizes = [len(fn) for fn in callers]
    text_size = 4 * sum(sizes)
    caller_addrs = []
    cursor = text_off
    for count in sizes:
        caller_addrs.append(base + cursor)
        cursor += 4 * count
    text_segment_end = _round(text_off + text_size, PAGE)
    next_page = text_segment_end

    pointer_layout: dict[str, dict] = {}
    segments = [dict(name='__PAGEZERO', vmaddr=0, vmsize=base, fileoff=0, filesize=0, prot=0),
                dict(name='__TEXT', vmaddr=base, vmsize=text_segment_end, fileoff=0,
                     filesize=text_segment_end, prot=5)]
    for segment_name in data_segment_names:
        start = next_page
        position = start + data_pad
        for section in (s for s in pointer_sections if s.segment == segment_name):
            position = _round(position, 8) + section.misalign
            size = 8 * len(section.entries) + section.extra_size
            pointer_layout[section.name] = dict(off=position, size=size)
            position += size
        end = _round(max(position, start + 1), PAGE)
        segments.append(dict(name=segment_name, vmaddr=base + start + vm_gap, vmsize=end - start,
                             fileoff=start, filesize=end - start, prot=3))
        next_page = end
    linkedit_off = next_page
    for section in pointer_sections:
        entry = pointer_layout[section.name]
        segment = next(s for s in segments if s['name'] == section.segment)
        entry.update(addr=segment['vmaddr'] + entry['off'] - segment['fileoff'], kind=section.kind,
                     segment=section.segment, reserved1=reserved1[section.name], fixup=section.fixup,
                     section=f"{section.segment},{section.name}", count=len(section.entries))
        entry['align'] = 3 if entry['addr'] % 8 == 0 else 2

    def resolve(target):
        if isinstance(target, int):
            return target
        kind = target[0]
        if kind == 'slot':
            return pointer_layout[target[1]]['addr'] + 8 * target[2] + (target[3] if len(target) > 3 else 0)
        if kind == 'word':
            return caller_addrs[target[1]] + 4 * target[2]
        raise ValueError(target)

    # ---- code bytes -------------------------------------------------------------
    text = bytearray()
    for fn, start in zip(callers, caller_addrs):
        for k, item in enumerate(fn):
            pc = start + 4 * k
            if isinstance(item, int):
                word = item
            elif item[0] == 'adrp':
                word = adrp(item[1], pc, resolve(item[2]))
            elif item[0] == 'ldr':
                word = ldr_x_uimm(item[1], item[2], resolve(item[3]) & 0xFFF)
            else:
                word = _BRANCHES[item[0]](pc, resolve(item[1]), *item[2:])
            text += struct.pack('<I', word)

    # ---- chained fixups blob ------------------------------------------------------
    segment_order = [s['name'] for s in segments] + ['__LINKEDIT']
    seg_count = len(segment_order)
    members: dict[str, list[tuple[int, int]]] = {}
    slot_values: dict[int, int] = {}     # file offset -> raw
    blob = bytearray()
    seg_records: dict[str, int] = {}
    seg_info = [0] * seg_count
    rebase_target = (caller_addrs[0] if caller_addrs else base + text_off)
    starts_offset = 0x20
    position = starts_offset + 4 + 4 * seg_count
    records = bytearray()
    record_positions = []
    for segment in segments[2:]:
        addresses = []
        for section in pointer_sections:
            if section.segment != segment['name'] or section.fixup == 'none':
                continue
            entry = pointer_layout[section.name]
            for k in range(len(section.entries)):
                addresses.append((entry['addr'] + 8 * k, section, k))
        if not addresses:
            continue
        addresses.sort(key=lambda item: item[0])
        page_count = segment['vmsize'] // page_size
        page_starts = [0xFFFF] * page_count
        chain = []
        for i, (vm, section, k) in enumerate(addresses):
            page = (vm - segment['vmaddr']) // page_size
            nxt = addresses[i + 1][0] if i + 1 < len(addresses) else None
            if page_starts[page] == 0xFFFF:
                page_starts[page] = vm - segment['vmaddr'] - page * page_size
            next_ = 0
            if nxt is not None and (nxt - segment['vmaddr']) // page_size == page:
                next_ = (nxt - vm) // 4
            if section.fixup == 'bind':
                raw = bind_raw(section.entries[k], next_)
            else:
                target = rebase_target - (base if pointer_format == 6 else 0)
                raw = rebase_raw(target, next_)
            chain.append((vm, raw))
            slot_values[segment['fileoff'] + vm - segment['vmaddr']] = raw
        members[segment['name']] = chain
        size = _round(22 + 2 * page_count, 8)
        record = bytearray(size)
        seg_offset = (segment_offset_override or {}).get(segment['name'], segment['vmaddr'] - base)
        struct.pack_into('<IHHQIH', record, 0, size, page_size, pointer_format, seg_offset, 0, page_count)
        for j, ps in enumerate(page_starts):
            struct.pack_into('<H', record, SS_PAGE_START + 2 * j, ps)
        position = _round(position, 8)
        record_positions.append((segment['name'], position, bytes(record)))
        position += size
    imports_offset = _round(position, 4)
    pool = bytearray(b"\0")
    pool_offsets = []
    for name in import_names:
        pool_offsets.append(len(pool))
        pool.extend(name + b"\0")
    symbols_offset = imports_offset + 4 * len(imports)
    blob = bytearray(_round(symbols_offset + len(pool), 8))
    struct.pack_into('<7I', blob, 0, 0, starts_offset, imports_offset, symbols_offset, len(imports), 1, 0)
    struct.pack_into('<I', blob, starts_offset, seg_count)
    for name, rel, record in record_positions:
        seg_records[name] = rel
        seg_info[segment_order.index(name)] = rel - starts_offset
        blob[rel:rel + len(record)] = record
    for i, value in enumerate(seg_info):
        struct.pack_into('<I', blob, starts_offset + 4 + 4 * i, value)
    for i, imp in enumerate(imports):
        struct.pack_into('<I', blob, imports_offset + 4 * i,
                         (imp.ordinal & 0xFF) | (int(imp.weak) << 8) | (pool_offsets[i] << 9))
    blob[symbols_offset:symbols_offset + len(pool)] = pool

    # ---- __LINKEDIT ------------------------------------------------------------------
    linkedit = bytearray()
    blob_off = None
    if include_chained:
        blob_off = linkedit_off
        linkedit += blob
    dyld_payload_off = None
    if dyld_info is not None:
        dyld_payload_off = linkedit_off + len(linkedit)
        linkedit += bytes(16)
    function_starts_off = linkedit_off + len(linkedit)
    previous = base
    for address in caller_addrs:
        linkedit += _uleb(address - previous)
        previous = address
    linkedit += b"\0"
    linkedit += bytes((-len(linkedit)) % 8)
    function_starts_size = linkedit_off + len(linkedit) - function_starts_off
    data_in_code_off = linkedit_off + len(linkedit)
    for target, length in (data_in_code or ()):
        offset = target if isinstance(target, int) else resolve(target) - base
        linkedit += struct.pack('<IHH', offset, length, 1)
    data_in_code_size = linkedit_off + len(linkedit) - data_in_code_off
    symoff = linkedit_off + len(linkedit)
    for k, (_, where, n_type) in enumerate(extra_symbols):
        linkedit += struct.pack('<IBBHQ', strx[k], n_type, 1, 0, resolve(where))
    for k in range(defined_count):
        linkedit += struct.pack('<IBBHQ', strx[local_count + k], 0x0F, 1, 0, caller_addrs[k])
    for j, imp in enumerate(imports):
        desc = ((imp.ordinal & 0xFF) << 8) | (0x40 if imp.weak else 0)
        linkedit += struct.pack('<IBBHQ', strx[first_import + j], 0x01, 0, desc, 0)
    indirect_off = linkedit_off + len(linkedit)
    linkedit += b"".join(struct.pack('<I', e) for e in indirect)
    linkedit += bytes((-len(linkedit)) % 8)
    stroff = linkedit_off + len(linkedit)
    linkedit += strings
    total = linkedit_off + len(linkedit)
    linkedit_vm = (segments[-1]['vmaddr'] + segments[-1]['vmsize']) if len(segments) > 2 else base + linkedit_off
    segments.append(dict(name='__LINKEDIT', vmaddr=linkedit_vm, vmsize=_round(total - linkedit_off, PAGE),
                         fileoff=linkedit_off, filesize=total - linkedit_off, prot=1))

    # ---- load commands ------------------------------------------------------------------
    def section_header(sectname, segname, address, size, offset, align, flags, r1, r2):
        return struct.pack('<16s16sQQIIIIIIII', sectname.encode(), segname.encode(), address, size,
                           offset, align, 0, 0, flags, r1, r2, 0)

    def segment_command(spec, rows):
        return struct.pack('<II16sQQQQiiII', 0x19, 72 + 80 * len(rows), spec['name'].encode(), spec['vmaddr'],
                           spec['vmsize'], spec['fileoff'], spec['filesize'], spec['prot'], spec['prot'],
                           len(rows), 0) + b"".join(row for _, row in rows)

    commands: list[bytes] = []
    cursor = 32
    section_rows = {
        '__TEXT': [('__text', section_header('__text', '__TEXT', base + text_off, text_size, text_off, 2,
                                             TEXT_FLAGS, 0, 0))],
    }
    for section in pointer_sections:
        p = pointer_layout[section.name]
        section_rows.setdefault(section.segment, []).append((section.name, section_header(
            section.name, section.segment, p['addr'], p['size'], p['off'], p['align'], section.kind,
            p['reserved1'], 0)))
    for spec in segments:
        rows = section_rows.get(spec['name'], [])
        for j, (name, _) in enumerate(rows):
            if name in pointer_layout:
                pointer_layout[name]['header_off'] = cursor + 72 + 80 * j
        command = segment_command(spec, rows)
        spec['cmd_off'] = cursor
        commands.append(command)
        cursor += len(command)
    dyld_info_cmd_off = None
    if dyld_info is not None:
        dyld_info_cmd_off = cursor
        fields = []
        for size in dyld_info:
            fields += [dyld_payload_off if size else 0, size]
        commands.append(struct.pack('<II10I', LC_DYLD_INFO_ONLY, 48, *fields))
        cursor += 48
    chained_cmd_off = None
    if include_chained:
        for _ in range(2 if duplicate_chained else 1):
            if chained_cmd_off is None:
                chained_cmd_off = cursor
            commands.append(struct.pack('<IIII', LC_DYLD_CHAINED_FIXUPS, 16, blob_off, len(blob)))
            cursor += 16
    commands.append(struct.pack('<IIII', 0x26, 16, function_starts_off, function_starts_size))
    cursor += 16
    symtab_cmd_off = None
    dysymtab_cmd_off = None
    if include_symtab:
        symtab_cmd_off = cursor
        commands.append(struct.pack('<IIIIII', 2, 24, symoff, len(names), stroff, len(strings)))
        cursor += 24
        if include_dysymtab:
            dysymtab_cmd_off = cursor
            commands.append(struct.pack('<II18I', 0xB, 80, 0, local_count, local_count, defined_count,
                                        first_import, len(imports), 0, 0, 0, 0, 0, 0, indirect_off,
                                        len(indirect), 0, 0, 0, 0))
            cursor += 80
    data_in_code_cmd_off = None
    if data_in_code is not None:
        data_in_code_cmd_off = cursor
        commands.append(struct.pack('<IIII', LC_DATA_IN_CODE, 16, data_in_code_off, data_in_code_size))
        cursor += 16
    commands.append(struct.pack('<II', 0x1B, 24) + bytes(range(16, 32)))
    cursor += 24
    dylib_cmd_offs = []
    for (cmd, _), raw in zip(dylib_specs, dylib_blobs):
        if cmd != LC_LOAD_DYLINKER:
            dylib_cmd_offs.append(cursor)
        commands.append(raw)
        cursor += len(raw)
    command_bytes = b"".join(commands)
    if 32 + len(command_bytes) > text_off:
        raise ValueError("load commands overlap section data")
    header = struct.pack('<IIIIIIII', 0xFEEDFACF, 0x0100000C, cpusubtype, 2, len(commands),
                         len(command_bytes), header_flags, 0)

    payload = bytearray(total)
    payload[:32 + len(command_bytes)] = header + command_bytes
    payload[text_off:text_off + text_size] = text
    for offset, raw in slot_values.items():
        struct.pack_into('<Q', payload, offset, raw)
    payload[linkedit_off:total] = linkedit

    layout = GotLayout(
        base=base, text_off=text_off, text_addr=base + text_off, text_size=text_size, caller_addrs=caller_addrs,
        caller_sizes=sizes, pointers=pointer_layout, segments=segments, blob_off=blob_off, blob_size=len(blob),
        starts_offset=starts_offset, imports_offset=imports_offset, symbols_offset=symbols_offset,
        seg_records=seg_records, seg_info_offsets=seg_info, pool_name_offsets=pool_offsets, members=members,
        chained_cmd_off=chained_cmd_off, dylib_cmd_offs=dylib_cmd_offs,
        dylib_paths=[p for c, p in dylib_specs if c != LC_LOAD_DYLINKER],
        dyld_info_cmd_off=dyld_info_cmd_off, data_in_code_cmd_off=data_in_code_cmd_off,
        data_in_code_off=data_in_code_off, symoff=symoff, nsyms=len(names), stroff=stroff,
        strsize=len(strings), strx=strx, local_count=local_count, defined_count=defined_count,
        indirect_off=indirect_off, nindirect=len(indirect), symtab_cmd_off=symtab_cmd_off,
        dysymtab_cmd_off=dysymtab_cmd_off, ncmds=len(commands), nsections=nsections,
        nsegments=len(segments), linkedit_off=linkedit_off, total=total, executable_words=text_size // 4)
    return bytes(payload), layout
