"""Structural shape of an indirect branch target (tier 1, model swift-indirect-target-shape-v1).

Given one indirect branch (blr or br) and the words of its containing function, a bounded
backward slice names where the branch register came from and returns a typed shape record.
The record is a structural fact about one instruction sequence. It never admits a call,
never changes a row, and never claims anything about the callee (claims_callee_behaviour is
always false). Anything the slice cannot decide is `unknown` with a stable reason.

The module performs no I/O, reads no image, and never executes or loads inspected code.
It has its own small decoder for the words the slice needs (src/airs/arm64.py is a stack
model whitelist and is not widened). A word the decoder does not model gets a conservative
write set: an over-approximated write can only turn a site into `unknown`.

Bounds: at most WINDOW_WORDS words backward per register search, at most MAX_REGISTER_HOPS
register hops (target <- table base <- metadata ...), and functions longer than
MAX_FUNCTION_WORDS words are refused. Any input is answered with a record; none raises.
"""
from bisect import bisect_right

MODEL = 'swift-indirect-target-shape-v1'
WINDOW_WORDS = 256
MAX_REGISTER_HOPS = 6
MAX_FUNCTION_WORDS = 262144
# Function slots of the Swift value witness table. +0x40 size, +0x48 stride, +0x50 flags and
# +0x54 extra inhabitants are data fields; +0x70 and beyond are not function slots.
VALUE_WITNESS_FUNCTION_SLOTS = frozenset((0x0, 0x8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x58, 0x60, 0x68))
VTABLE_MIN_OFFSET = 0x50
CLASSES = ('value_witness', 'protocol_witness_slot', 'class_vtable', 'closure_context',
           'got_or_global_fnptr', 'static_address', 'runtime_or_objc_ptr', 'unknown')
_CALLEE_SAVED = frozenset(range(19, 29))
_LEVELS = ('target', 'table', 'metadata', 'deeper')


# --------------------------------------------------------------------------- decoder

def _sx(value, bits):
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def _decode(word, pc):
    """Decode one word into a dict. `writes` over-approximates the general registers written.

    Registers are 0..30; the zero register and sp (31) are never listed. A word outside the
    modeled subset gets kind 'other' (or a group kind) with every register field it could
    write, which can only make a register look overwritten.
    """
    w = word & 0xffffffff
    rt, rn = w & 31, (w >> 5) & 31
    rt2, rs = (w >> 10) & 31, (w >> 16) & 31
    X = lambda n: 'xzr' if n == 31 else 'x%d' % n
    XS = lambda n: 'sp' if n == 31 else 'x%d' % n

    def make(kind, text, writes=(), **extra):
        d = dict(pc=pc, word=w, kind=kind, text=text,
                 writes=frozenset(r for r in writes if r < 31))
        d.update(extra)
        return d

    if w == 0xd503201f:
        return make('nop', 'nop')
    if w & 0xfc000000 == 0x94000000:
        target = pc + _sx(w & 0x3ffffff, 26) * 4
        return make('bl', 'bl %#x' % target, {30}, target=target)
    if w & 0xfc000000 == 0x14000000:
        target = pc + _sx(w & 0x3ffffff, 26) * 4
        return make('b', 'b %#x' % target, target=target)
    if w >> 25 == 0x6b:  # unconditional branch (register) group
        opc = (w >> 21) & 15
        if opc in (0, 8):
            if w & 0xfffffc1f == 0xd61f0000:
                return make('br', 'br %s' % X(rn), rn=rn)
            return make('bra', 'authenticated br', rn=rn)
        if opc in (1, 9):
            if w & 0xfffffc1f == 0xd63f0000:
                return make('blr', 'blr %s' % X(rn), {30}, rn=rn)
            return make('blra', 'authenticated blr', {30}, rn=rn)
        return make('ret', 'ret/eret')
    if w & 0xff000000 == 0x54000000:  # b.cond and bc.cond (bit 4 set)
        target = pc + _sx((w >> 5) & 0x7ffff, 19) * 4
        return make('bcond', 'b.cond %#x' % target, target=target)
    if w & 0x7e000000 == 0x74000000:  # compare-and-branch (FEAT_CMPBR): imm9 at bits 13..5
        target = pc + _sx((w >> 5) & 0x1ff, 9) * 4
        return make('cbz', 'cb<cc> %#x' % target, target=target)
    if w & 0x7e000000 == 0x34000000:
        target = pc + _sx((w >> 5) & 0x7ffff, 19) * 4
        return make('cbz', 'cbz/cbnz %#x' % target, target=target)
    if w & 0x7e000000 == 0x36000000:
        target = pc + _sx((w >> 5) & 0x3fff, 14) * 4
        return make('tbz', 'tbz/tbnz %#x' % target, target=target)
    if w & 0x9f000000 == 0x90000000:
        value = (pc & ~0xfff) + _sx((((w >> 5) & 0x7ffff) << 2) | ((w >> 29) & 3), 21) * 4096
        return make('adrp', 'adrp %s, %#x' % (X(rt), value), {rt}, rd=rt, value=value)
    if w & 0x9f000000 == 0x10000000:
        value = pc + _sx((((w >> 5) & 0x7ffff) << 2) | ((w >> 29) & 3), 21)
        return make('adr', 'adr %s, %#x' % (X(rt), value), {rt}, rd=rt, value=value)
    if w & 0xff800000 in (0x91000000, 0xd1000000):
        imm = ((w >> 10) & 0xfff) << (12 if w & (1 << 22) else 0)
        name = 'add' if w & 0xff800000 == 0x91000000 else 'sub'
        return make(name + '_imm', '%s %s, %s, #%#x' % (name, XS(rt), XS(rn), imm), {rt},
                    rd=rt, rn=rn, imm=imm)
    if w & 0xffe0ffe0 == 0xaa0003e0:
        return make('mov', 'mov %s, %s' % (X(rt), X(rs)), {rt}, rd=rt, rm=rs)
    if w & 0xff800000 in (0xd2800000, 0x92800000, 0xf2800000):
        name = {0xd2800000: 'movz', 0x92800000: 'movn', 0xf2800000: 'movk'}[w & 0xff800000]
        return make(name, '%s %s, #%#x' % (name, X(rt), (w >> 5) & 0xffff), {rt}, rd=rt)
    op0 = (w >> 25) & 15
    if op0 in (4, 6, 12, 14):
        return _decode_load_store(w, pc, make, X, XS)
    if op0 in (8, 9, 5, 13):
        # Conditional compares write only flags (the low field is nzcv, not a register).
        if (w >> 21) & 0xff == 0xd2 and (w >> 29) & 1:
            return make('flags', 'ccmp/ccmn')
        sp_write = False
        if rt == 31:
            # add/sub (extended register) and logical (immediate) without flag update may write sp.
            if (w >> 24) & 0x1f == 0x0b and (w >> 21) & 1 and not (w >> 29) & 1:
                sp_write = True
            if (w >> 23) & 0x3f == 0x24 and (w >> 29) & 3 != 3:
                sp_write = True
        return make('dp', 'dp %#010x (rd=%s)' % (w, X(rt)), {rt}, rd=rt, sp_write=sp_write)
    if op0 in (10, 11):
        # System, exception and any branch form not modeled above: rt (mrs, sysl) and x30
        # (pointer-authentication hints change it) are treated as written.
        return make('system', 'system %#010x' % w, {rt, 30})
    if op0 in (7, 15):
        return make('simd_or_fp', 'simd/fp %#010x' % w, {rt})
    # Reserved, SVE and SME groups: every register field could be written.
    return make('other', 'unmodeled %#010x' % w, {rt, rn, rt2, rs})


def _decode_load_store(w, pc, make, X, XS):
    rt, rn = w & 31, (w >> 5) & 31
    rt2, rs = (w >> 10) & 31, (w >> 16) & 31
    group = (w >> 27) & 7
    vector = (w >> 26) & 1
    size = (w >> 30) & 3
    opc = (w >> 22) & 3
    # Pair and multi-register forms (casp writes Rs+1, ld64b writes Xt..Xt+7) write registers
    # beyond the named fields, so the over-approximation adds the following registers too.
    everything = {rt, rn, rt2, rs, rs + 1} | set(range(rt, rt + 8))
    if group == 7 and (w >> 24) & 3 == 1:  # unsigned immediate
        off = ((w >> 10) & 0xfff) << size
        if vector == 0 and opc == 1 and size == 3:
            return make('ldr', 'ldr %s, [%s, #%#x]' % (X(rt), XS(rn), off), {rt}, rt=rt, rn=rn, off=off)
        if vector == 0 and opc == 0:
            return make('str', 'str %s, [%s, #%#x]' % (X(rt), XS(rn), off), (), rt=rt, rn=rn, off=off, size=size, wb=False)
        if vector == 0:
            return make('ldr_narrow', 'ldr* %s, [%s, #%#x]' % (X(rt), XS(rn), off), {rt}, rt=rt, rn=rn, off=off)
        return make('ldst_vector', 'simd/fp load or store', ())
    if group == 7 and (w >> 24) & 3 == 0:
        if (w >> 21) & 1 == 0:  # imm9 forms
            mode = (w >> 10) & 3
            off = _sx((w >> 12) & 0x1ff, 9)
            wb = {rn} if mode in (1, 3) else set()
            extra = dict(wb_base=rn) if wb else {}
            if vector == 0 and opc == 1 and size == 3:
                name = {0: 'ldur', 1: 'ldr_post', 3: 'ldr_pre'}.get(mode, 'ldtr')
                return make(name, '%s %s, [%s, #%d]' % (name, X(rt), XS(rn), off), {rt} | wb,
                            rt=rt, rn=rn, off=off, **extra)
            if vector == 0 and opc == 0:
                name = {0: 'stur', 1: 'str_post', 3: 'str_pre'}.get(mode, 'sttr')
                return make('str', '%s %s, [%s, #%d]' % (name, X(rt), XS(rn), off), wb,
                            rt=rt, rn=rn, off=off, size=size, wb=bool(wb), **extra)
            if vector == 0:
                return make('ldr_narrow', 'ldr*/ldur* narrow', {rt} | wb, rt=rt, rn=rn, **extra)
            return make('ldst_vector', 'simd/fp imm9', wb, **extra)
        if (w >> 10) & 3 == 2:  # register offset
            if vector == 0 and opc == 0:
                return make('str', 'str (register offset)', (), rt=rt, rn=rn, off=None, size=size, wb=False)
            if vector == 0:
                return make('ldr_reg', 'ldr (register offset)', {rt}, rt=rt, rn=rn)
            return make('ldst_vector', 'simd/fp register offset', ())
        return make('ldst_other', 'atomic or pointer-authenticated load', everything,
                    wb_base=rn)
    if group == 3 and (w >> 24) & 1 == 0:  # literal
        target = pc + _sx((w >> 5) & 0x7ffff, 19) * 4
        if vector == 0 and size == 1:
            return make('ldr_lit', 'ldr %s, %#x' % (X(rt), target), {rt}, rt=rt, target=target)
        if vector == 0 and size in (0, 2):
            return make('ldr_narrow', 'ldr* literal', {rt}, rt=rt)
        return make('ldst_vector', 'simd/fp or prefetch literal', ())
    if group == 5:  # pair
        mode = (w >> 23) & 3
        load = (w >> 22) & 1
        off = _sx((w >> 15) & 0x7f, 7) << (2 + (size >> 1) if vector == 0 else 2 + size)
        wb = {rn} if mode in (1, 3) else set()
        extra = dict(wb_base=rn) if wb else {}
        if vector == 0 and size == 2 and load:
            return make('ldp', 'ldp %s, %s, [%s, #%d]' % (X(rt), X(rt2), XS(rn), off), {rt, rt2} | wb,
                        rt=rt, rt2=rt2, rn=rn, off=off, mode=mode, **extra)
        if vector == 0 and size == 2:
            return make('stp', 'stp %s, %s, [%s, #%d]' % (X(rt), X(rt2), XS(rn), off), wb,
                        rt=rt, rt2=rt2, rn=rn, off=off, mode=mode, **extra)
        return make('ldst_pair_other', 'pair other', ({rt, rt2} if load and vector == 0 else set()) | wb, **extra)
    if group in (0, 1):  # exclusive, ordered, compare-and-swap: status, data and pair registers
        return make('ldst_exclusive', 'exclusive/ordered', everything)
    return make('ldst_other', 'load/store other', everything, wb_base=rn)


# --------------------------------------------------------------------------- function view

class _Function:
    """Decoded function words plus the branch-target set and per-register writer counts."""

    def __init__(self, start, words, extra_targets=()):
        self.start = start
        self.end = start + 4 * len(words)
        self.ins = [_decode(word, start + 4 * i) for i, word in enumerate(words)]
        targets = set(extra_targets)
        self.writers = {}
        for ins in self.ins:
            if ins['kind'] in ('b', 'bcond', 'cbz', 'tbz'):
                targets.add(ins['target'])
            for reg in ins['writes']:
                self.writers[reg] = self.writers.get(reg, 0) + 1
        self.targets = sorted(t for t in targets if self.start <= t < self.end)

    def at(self, pc):
        return self.ins[(pc - self.start) // 4]

    def join_between(self, low, high):
        """True when a branch target t lies in low < t <= high (another path may enter after the def)."""
        k = bisect_right(self.targets, low)
        return k < len(self.targets) and self.targets[k] <= high


# --------------------------------------------------------------------------- backward slice

def _node(kind, pc=None, reg=None, consumer=None, **extra):
    n = dict(kind=kind, pc=pc, reg=reg, consumer=consumer)
    n.update(extra)
    return n


def _resolve(F, reg, pc, depth=0):
    """Provenance of `reg` just before the instruction at `pc`, within the bounded window."""
    if depth > MAX_REGISTER_HOPS:
        return _node('unknown', reason='depth_limit', consumer=pc)
    if reg == 31:
        return _node('unknown', reason='sp_or_zero_register', consumer=pc)
    idx = (pc - F.start) // 4
    lowest = max(-1, idx - 1 - WINDOW_WORDS)
    j = idx - 1
    while j > lowest:
        ins = F.ins[j]
        kind = ins['kind']
        if kind in ('bl', 'blr', 'blra'):
            if reg == 30:
                return _node('unknown', pc=ins['pc'], reason='link_register', consumer=pc)
            if reg <= 3:
                return _node('call_result', pc=ins['pc'], reg=reg, consumer=pc, text=ins['text'],
                             callee=ins.get('target'), call_kind=kind)
            if reg <= 17:
                return _node('unknown', pc=ins['pc'], reason='clobbered_by_call', consumer=pc)
            j -= 1
            continue
        if reg in ins['writes']:
            return _definition(F, reg, ins, pc, depth)
        if kind in ('b', 'ret', 'br', 'bra'):
            return _node('unknown', pc=ins['pc'], reason='flow_break_before_def', consumer=pc)
        j -= 1
    if j < 0:
        if reg <= 7 or reg in _CALLEE_SAVED or reg in (20, 21, 29):
            return _node('entry_live', reg=reg, pc=F.start, consumer=pc)
        return _node('unknown', reason='undefined_at_entry', consumer=pc)
    return _node('unknown', reason='window_bound', consumer=pc)


def _definition(F, reg, ins, pc, depth):
    kind, p = ins['kind'], ins['pc']
    base = dict(pc=p, reg=reg, consumer=pc, text=ins['text'])
    if kind == 'mov':
        return _node('copy', child=_resolve(F, ins['rm'], p, depth + 1), **base)
    if kind in ('add_imm', 'sub_imm'):
        rn = ins['rn']
        if kind == 'add_imm' and ins['imm'] == 0 and rn != 31:
            return _node('copy', child=_resolve(F, rn, p, depth + 1), **base)
        if rn in (31, 29):
            return _node('stack_address', **base)
        if kind == 'add_imm':
            inner = _resolve(F, rn, p, depth + 1)
            leaf = _leaf(inner)
            if inner['kind'] == 'adrp' or (inner['kind'] == 'copy' and leaf['kind'] == 'adrp'):
                return _node('addr', child=inner, value=leaf['value'] + ins['imm'], **base)
        return _node('unknown', reason='add_sub_other', **base)
    if kind in ('adrp', 'adr'):
        return _node(kind, value=ins['value'], **base)
    if kind == 'ldr_lit':
        return _node('literal', value=ins['target'], **base)
    if kind in ('movz', 'movn', 'movk'):
        return _node('const', **base)
    if kind in ('ldr', 'ldur', 'ldp'):
        rn = ins['rn']
        off = ins['off']
        if kind == 'ldp':
            if ins['mode'] in (1, 3) and reg == rn:
                return _node('unknown', reason='writeback', **base)
            if ins['rt'] == ins['rt2']:
                return _node('unknown', reason='ambiguous_pair', **base)
            if ins['mode'] == 1:  # post-index loads from the unmodified base
                off = 0
            if reg == ins['rt2']:
                off += 8
        if rn in (31, 29):
            return _stack(F, reg, ins, off, pc, depth, base)
        return _node('load', via=kind, off=off, rn=rn, pair=(kind == 'ldp'), rt=ins.get('rt'),
                     rt2=ins.get('rt2'), base=_resolve(F, rn, p, depth + 1), **base)
    return _node('unknown', reason='other_def:' + kind, **base)


def _stack(F, reg, ins, off, pc, depth, base):
    """A reload from [sp or x29 + off]: the nearest earlier straight-line store to the same slot."""
    rn, p = ins['rn'], ins['pc']
    idx = (p - F.start) // 4
    for j in range(idx - 1, max(-1, idx - 1 - WINDOW_WORDS), -1):
        s = F.ins[j]
        kind = s['kind']
        if kind in ('b', 'ret', 'br', 'bra'):
            break
        if s.get('wb_base') == rn or s.get('sp_write') and rn == 31:
            break
        if rn == 31 and kind in ('add_imm', 'sub_imm') and s['rd'] == 31:
            break
        if rn == 29 and 29 in s['writes']:
            break
        if kind == 'str' and s['rn'] == rn and s['off'] == off and s.get('size') == 3 and not s.get('wb'):
            return _node('stack_reload', child=_resolve(F, s['rt'], s['pc'], depth + 1),
                         store_pc=s['pc'], store_text=s['text'], **base)
        if kind == 'stp' and s['rn'] == rn and s['mode'] == 2 and off in (s['off'], s['off'] + 8):
            r = s['rt'] if off == s['off'] else s['rt2']
            return _node('stack_reload', child=_resolve(F, r, s['pc'], depth + 1),
                         store_pc=s['pc'], store_text=s['text'], **base)
    return _node('unknown', reason='stack_slot_without_store', **base)


def _leaf(n):
    while n['kind'] in ('copy', 'stack_reload') and 'child' in n:
        n = n['child']
    return n


def _walk(n):
    yield n
    for key in ('child', 'base'):
        if isinstance(n.get(key), dict):
            yield from _walk(n[key])


def _join(F, n):
    """True when a used definition has a branch target between it and its use.

    Exception (census rule): a register in x19..x28 with exactly one writer in the whole
    function is exempt, since its single definition must dominate every use.
    """
    for m in _walk(n):
        if m.get('pc') is None or m['kind'] in ('entry_live', 'unknown') or m.get('consumer') is None:
            continue
        if m.get('reg') in _CALLEE_SAVED and F.writers.get(m['reg'], 0) == 1:
            continue
        if F.join_between(m['pc'], m['consumer']):
            return True
        if m['kind'] == 'stack_reload' and F.join_between(m['store_pc'], m['pc']):
            return True
    return False


def _holders(F, base_reg, from_pc, to_pc):
    """Registers still holding the value of base_reg (through mov copies) just before to_pc."""
    holders = {base_reg}
    for ins in F.ins[(from_pc - F.start) // 4 + 1:(to_pc - F.start) // 4]:
        kind = ins['kind']
        if kind in ('bl', 'blr', 'blra'):
            holders = {r for r in holders if r >= 18}
            continue
        if kind == 'mov':
            if ins['rm'] in holders:
                holders.add(ins['rd'])
            else:
                holders.discard(ins['rd'])
            continue
        holders -= ins['writes']
    return holders


def _written(F, reg, after_pc, before_pc):
    return any(reg in i['writes'] for i in F.ins[(after_pc - F.start) // 4 + 1:(before_pc - F.start) // 4])


def _x20_pair(F, n, load_pc, site_pc):
    """Closure pair {function, context}: the context word is loaded into x20 and still live at the call."""
    if n['pair'] and 20 in (n['rt'], n['rt2']) and n['rt'] != n['rt2']:
        other = n['rt2'] if n['reg'] == n['rt'] else n['rt']
        if other == 20 and not _written(F, 20, load_pc, site_pc):
            return load_pc
    lo = max(F.start, load_pc - 64)
    for ins in F.ins[(lo - F.start) // 4:(site_pc - F.start) // 4]:
        if ins['kind'] in ('ldr', 'ldur') and ins['rn'] == n['rn'] and ins['rt'] == 20 and ins['off'] == n['off'] + 8:
            if not _written(F, 20, ins['pc'], site_pc):
                return ins['pc']
    return None


def _section_label(sections, address):
    for s in sections:
        if s[2] <= address < s[2] + s[3]:
            return '%s,%s' % (s[0], s[1])
    return 'unmapped'


def _describe(b):
    kind = b['kind']
    if kind == 'unknown':
        return 'unresolved:' + b.get('reason', '?')
    if kind == 'entry_live':
        return 'entry_register_x%d' % b['reg']
    if kind == 'call_result':
        return 'call_result'
    if kind == 'load':
        return 'loaded_from_memory' + ('_pair' if b['pair'] else '') + ('_stack' if b['rn'] in (29, 31) else '')
    return kind


def _decide(F, n, site_pc, sections):
    """First match wins. Returns (class, evidence, reason, extra deciding pcs, slot address)."""
    t = _leaf(n)
    kind = t['kind']
    if kind == 'call_result':
        return 'runtime_or_objc_ptr', 'function pointer is x%d returned by %s' % (t['reg'], t['text']), None, {}, None
    if kind in ('adrp', 'addr', 'literal', 'adr'):
        return 'static_address', 'branch target is a materialized code address, not a load', None, {}, None
    if kind == 'entry_live':
        return 'unknown', None, 'target_is_entry_register_x%d' % t['reg'], {}, None
    if kind == 'load':
        off, base = t['off'], t['base']
        b = _leaf(base)
        if b['kind'] == 'load' and b['via'] == 'ldur' and b['off'] == -8:
            if off in VALUE_WITNESS_FUNCTION_SLOTS:
                return ('value_witness',
                        'table base loaded from [x%d, #-8] (type metadata -8 = value witness table), slot +%#x' % (b['rn'], off),
                        None, {}, None)
            return 'unknown', None, 'value_witness_offset_not_function_slot', {}, None
        if b['kind'] == 'load' and b['via'] == 'ldr' and b['off'] == 0 and off >= VTABLE_MIN_OFFSET and not b['pair']:
            return ('class_vtable', 'base loaded from [x%d, #0] (isa/metadata), vtable offset +%#x' % (b['rn'], off),
                    None, {}, None)
        if b['kind'] in ('adrp', 'addr', 'literal'):
            if b['kind'] == 'literal':
                return 'got_or_global_fnptr', 'load via literal base', None, {}, None
            slot = b['value'] + off
            return ('got_or_global_fnptr', 'load from adrp-based slot %#x in %s' % (slot, _section_label(sections, slot)),
                    None, {}, slot)
        ctx = _x20_pair(F, t, t['pc'], site_pc)
        if ctx is not None:
            return ('closure_context',
                    'function pointer at [x%d, +%#x] with context pair loaded into x20 at %#x' % (t['rn'], off, ctx),
                    None, {ctx: 'closure_context_load'}, None)
        held = sorted(r for r in _holders(F, t['rn'], t['pc'], site_pc) if 1 <= r <= 7)
        if t['rn'] == 31 or b['kind'] == 'stack_address':
            return 'unknown', None, 'target_loaded_from_stack_object', {}, None
        if held and 8 <= off < VTABLE_MIN_OFFSET:
            return ('protocol_witness_slot',
                    'slot +%#x of a table also passed to the callee in x%d (trailing witness-table argument)' % (off, held[0]),
                    None, {}, None)
        return 'unknown', None, 'base_' + _describe(b), {}, None
    if kind == 'unknown':
        return 'unknown', None, t.get('reason', 'unresolved'), {}, None
    return 'unknown', None, 'target_' + kind, {}, None


_WHAT = {'copy': 'copy', 'load': 'load', 'call_result': 'call_result', 'adrp': 'address', 'addr': 'address',
         'adr': 'address', 'literal': 'literal', 'const': 'constant', 'stack_reload': 'stack_reload',
         'stack_address': 'stack_address', 'unknown': 'blocker'}


def _deciding(F, root, site_pc, extra):
    """pc -> role for the site and every instruction on the traced provenance chain."""
    roles = {site_pc: 'indirect_branch'}

    def visit(m, level):
        pc = m.get('pc')
        if pc is not None and m['kind'] != 'entry_live':
            roles.setdefault(pc, '%s_%s' % (_LEVELS[min(level, 3)], _WHAT.get(m['kind'], 'definition')))
        if m['kind'] == 'stack_reload':
            roles.setdefault(m['store_pc'], '%s_stack_store' % _LEVELS[min(level, 3)])
        if isinstance(m.get('child'), dict):
            visit(m['child'], level)
        if isinstance(m.get('base'), dict):
            visit(m['base'], level + 1)

    visit(root, 0)
    for pc, role in extra.items():
        roles.setdefault(pc, role)
    return [dict(pc=pc, word=F.at(pc)['word'], role=role) for pc, role in sorted(roles.items())]


# --------------------------------------------------------------------------- public interface

class ShapeAnalysis:
    """Result of one tier 1 analysis: the public `record` plus the traced tree for tier 2.

    `function`, `root` and `target` are None when the input was refused.
    """
    __slots__ = ('record', 'function', 'root', 'target')

    def __init__(self, record, function=None, root=None, target=None):
        self.record, self.function, self.root, self.target = record, function, root, target


def _record(site_pc, site_kind, cls='unknown', reason=None, slot=None, deciding=(), evidence=None,
            undemoted=None, slot_address=None, slot_section=None):
    return dict(model=MODEL, site_pc=site_pc, site_kind=site_kind, **{'class': cls},
                slot_offset=slot, unknown_reason=reason, deciding_instructions=list(deciding),
                evidence=evidence, class_before_join_refusal=undemoted,
                slot_address=slot_address, slot_section=slot_section,
                claims_callee_behaviour=False,
                bounds=dict(window_words=WINDOW_WORDS, max_register_hops=MAX_REGISTER_HOPS,
                            max_function_words=MAX_FUNCTION_WORDS))


def _refused(site_pc, reason, site_kind=None):
    pc = site_pc if type(site_pc) is int else None
    return ShapeAnalysis(_record(pc, site_kind, reason=reason))


def _words(value):
    if isinstance(value, (bytes, bytearray, memoryview)):
        raw = bytes(value)
        if len(raw) % 4:
            return None, 'function_words_truncated'
        if len(raw) // 4 > MAX_FUNCTION_WORDS:
            return None, 'function_too_large'
        return [int.from_bytes(raw[i:i + 4], 'little') for i in range(0, len(raw), 4)], None
    if isinstance(value, (list, tuple)):
        if len(value) > MAX_FUNCTION_WORDS:
            return None, 'function_too_large'
        if all(type(w) is int and 0 <= w <= 0xffffffff for w in value):
            return list(value), None
    return None, 'invalid_function_words'


def _targets(value):
    if value is None:
        return (), None
    if isinstance(value, (set, frozenset, list, tuple)) and len(value) <= MAX_FUNCTION_WORDS \
            and all(type(t) is int for t in value):
        return tuple(value), None
    return (), 'invalid_branch_targets'


def _sections(value):
    out = []
    try:
        for s in value or ():
            get = s.get if isinstance(s, dict) else (lambda k, s=s: getattr(s, k))
            row = (str(get('segment')), str(get('name')), get('address'), get('size'))
            if type(row[2]) is int and type(row[3]) is int:
                out.append(row)
    except Exception:
        return ()
    return tuple(out[:4096])


def analyze_indirect_target(words, function_start, site_pc, *, branch_targets=None, sections=()):
    """Analyze one blr/br site. Never raises; returns a ShapeAnalysis.

    words: the whole containing function, as little-endian bytes (length a multiple of 4)
    or a list of 32-bit integers, starting at function_start.
    branch_targets: optional collection of in-function branch target addresses. It is united
    with the targets the module derives from the words (extra targets only add refusals).
    sections: optional rows with segment, name, address and size, used only to label GOT-style slots.
    """
    try:
        return _analyze(words, function_start, site_pc, branch_targets, sections)
    except Exception:  # totality: an unexpected failure is a refusal, never an exception
        return _refused(site_pc, 'analysis_failed')


def _analyze(words, function_start, site_pc, branch_targets, sections):
    decoded, problem = _words(words)
    if problem:
        return _refused(site_pc, problem)
    if type(function_start) is not int or function_start < 0 or function_start % 4:
        return _refused(site_pc, 'invalid_function_start')
    if type(site_pc) is not int:
        return _refused(site_pc, 'site_outside_function')
    end = function_start + 4 * len(decoded)
    if site_pc % 4 or not function_start <= site_pc < end:
        return _refused(site_pc, 'site_outside_function')
    extra, problem = _targets(branch_targets)
    if problem:
        return _refused(site_pc, problem)
    F = _Function(function_start, decoded, extra)
    site = F.at(site_pc)
    if site['kind'] in ('bra', 'blra'):
        return _refused(site_pc, 'authenticated_branch_not_modeled', site['kind'])
    if site['kind'] not in ('blr', 'br'):
        return _refused(site_pc, 'site_not_indirect_branch', site['kind'])
    labelled = _sections(sections)
    root = _resolve(F, site['rn'], site_pc)
    cls, evidence, reason, extra_pcs, slot_address = _decide(F, root, site_pc, labelled)
    target = _leaf(root)
    slot = target['off'] if target['kind'] == 'load' else None
    undemoted = None
    if cls != 'unknown' and _join(F, root):
        cls, undemoted, reason = 'unknown', cls, 'join_in_slice'
    if cls != 'got_or_global_fnptr' and undemoted != 'got_or_global_fnptr':
        slot_address = None
    record = _record(site_pc, site['kind'], cls, reason, slot, _deciding(F, root, site_pc, extra_pcs),
                     evidence, undemoted, slot_address,
                     _section_label(labelled, slot_address) if slot_address is not None else None)
    return ShapeAnalysis(record, F, root, target)


def classify_indirect_target(words, function_start, site_pc, *, branch_targets=None, sections=()):
    """Return the tier 1 shape record (a dict) for one indirect branch site.

    Keys: model, site_pc, site_kind ('blr' or 'br'), class (one of CLASSES), slot_offset,
    unknown_reason, deciding_instructions (list of pc, word, role), evidence,
    class_before_join_refusal, slot_address, slot_section, claims_callee_behaviour (always
    False) and bounds. The record keeps no row and admits nothing.
    """
    return analyze_indirect_target(words, function_start, site_pc, branch_targets=branch_targets,
                                   sections=sections).record
