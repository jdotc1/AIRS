"""Broad-only exact instruction descriptors; no execution or FP value model.

Encodings follow LLVM AArch64InstrFormats.td / AArch64InstrInfo.td:
https://github.com/llvm/llvm-project/tree/main/llvm/lib/Target/AArch64
Historical decoding and its effect meanings remain unchanged.
"""
from .arm64 import Instruction, ModelError, _signed
from .swift_error_flow import decode_instruction as historical_decode


FP_DESTINATION_KINDS = frozenset(
    [f'scvtf_{fp}_{gp}' for fp in ('s', 'd') for gp in ('w', 'x')] +
    ['fmov_s_w', 'fmov_d_x'] +
    [f'fmov_{fp}_{form}' for fp in ('s', 'd') for form in ('reg', 'imm')] +
    [f'fdiv_{fp}' for fp in ('s', 'd')] + ['qldr', 'sldr', 'dldr', 'movi_2s_lsl24'])
GPR_DESTINATION_KINDS = frozenset(
    ['adr', 'adrp', 'fmov_w_s', 'fmov_x_d', 'wldrb', 'wldrh',
     'xadd_reg', 'xsub_reg', 'wadd_reg', 'wsub_reg', 'xadd_ext', 'xsub_ext',
     'xldr_raw', 'xldur', 'wldr_raw', 'wldur'] +
    [f'fcvtzs_{gp}_{fp}' for gp in ('w', 'x') for fp in ('s', 'd')])
NARROW_MEMORY_WIDTHS = {'wstrb': 1, 'wldrb': 1, 'wstrh': 2, 'wldrh': 2}
MEMORY_WIDTHS = {**NARROW_MEMORY_WIDTHS, 'xstr_raw': 8, 'xldr_raw': 8,
                 'xstur': 8, 'xldur': 8, 'qstr': 16, 'qldr': 16,
                 'wstr_raw': 4, 'wldr_raw': 4, 'wstur': 4, 'wldur': 4,
                 'sstr': 4, 'sldr': 4, 'dstr': 8, 'dldr': 8}
FP_MEMORY_STORES = frozenset(('sstr','dstr','qstr'))
FP_FLAG_KINDS = frozenset(f'fcmp_{fp}_{form}' for fp in ('s', 'd')
                          for form in ('reg', 'zero'))


class BroadInstruction(Instruction):
    @property
    def changes_sp(self):
        return ((self.kind in ('xadd_ext','xsub_ext') and self.rd==31) or
            (self.kind in ('xstr','xldr','xldr_post') and self.rn==31
                and self.addressing in ('pre','post')) or super().changes_sp)

    @property
    def changes_fp(self):
        # "fp" here means the GPR frame pointer x29, not SIMD register v29.
        return ((self.kind in GPR_DESTINATION_KINDS or self.kind=='xldr_post') and self.rd==29) or (
            self.kind in ('xstr','xldr','xldr_post') and self.rn==29
            and self.addressing in ('pre','post')) or super().changes_fp


def destination_register_bank(instruction):
    """Bank for newly described destinations; None for stores/flag writes.

    Historical instructions retain their existing consumer-specific handling.
    """
    if instruction.kind in FP_DESTINATION_KINDS:
        return 'fp'
    if instruction.kind in GPR_DESTINATION_KINDS:
        return 'gpr'
    return None


def decode_instruction(word: int, address: int = 0):
    if type(word) is not int or not 0 <= word <= 0xffffffff:
        return historical_decode(word, address)
    rd, rn = word & 31, (word >> 5) & 31
    if word & 0x1f000000 == 0x10000000:
        immediate = _signed(((word >> 5) & 0x7ffff) << 2 | ((word >> 29) & 3), 21)
        page = bool(word & 0x80000000)
        return BroadInstruction(address, word, 'adrp' if page else 'adr', rd=rd,
                                immediate=immediate * 4096 if page else immediate)

    # Exception generation is a transfer descriptor, never a proof of a
    # language-level never-returning function or of exception-handler behavior.
    if word & 0xffe0001f == 0xd4200000:
        return BroadInstruction(address, word, 'brk', immediate=(word >> 5) & 0xffff)
    # Newly needed X arithmetic: shifted-register LSL #0 only, no flag writes.
    # Register 31 is XZR in every operand, never SP.
    arithmetic = {0x8b000000: 'xadd_reg', 0xcb000000: 'xsub_reg',
                  0x0b000000: 'wadd_reg', 0x4b000000: 'wsub_reg'}
    kind = arithmetic.get(word & 0xffe0fc00)
    if kind:
        return BroadInstruction(address, word, kind, rd=rd, rn=rn,
                                rt2=(word >> 16) & 31, addressing='lsl')
    # Nonflag X extended-register ADD/SUB. Rn/Rd31 are SP, Rm31 is ZR.
    form=word&0xffe00000
    if form in (0x8b200000,0xcb200000):
        shift=(word>>10)&7
        if shift>4:raise ModelError('broad_extend_shift','Extended-register shift exceeds four',address)
        return BroadInstruction(address,word,'xadd_ext' if form==0x8b200000 else 'xsub_ext',
            rd=rd,rn=rn,rt2=(word>>16)&31,immediate=shift,
            addressing=('uxtb','uxth','uxtw','uxtx','sxtb','sxth','sxtw','sxtx')[(word>>13)&7])
    # Ordinary X pre/post-index only. Exclude unprivileged/register-offset and
    # signed-load variants; overlapping non-SP writeback is constrained.
    single=word&0xffe00c00
    writeback={0xf8000400:('xstr','post'),0xf8000c00:('xstr','pre'),
        0xf8400400:('xldr_post','post'),0xf8400c00:('xldr','pre')}.get(single)
    if writeback:
        if rn!=31 and rn==rd:raise ModelError('broad_memory_writeback_overlap','Memory writeback overlaps data register',address)
        return BroadInstruction(address,word,writeback[0],rd=rd,rn=rn,
            immediate=_signed((word>>12)&0x1ff,9),addressing=writeback[1])
    # W raw bases and unscaled words, and scalar FP memory: exact size/V/opc.
    # Historical SP W descriptors retain their existing names and semantics.
    memory={0xb9000000:('wstr_raw',4),0xb9400000:('wldr_raw',4),
        0xbd000000:('sstr',4),0xbd400000:('sldr',4),
        0xfd000000:('dstr',8),0xfd400000:('dldr',8)}.get(word&0xffc00000)
    if memory and (memory[0] not in ('wstr_raw','wldr_raw') or rn!=31):
        return BroadInstruction(address,word,memory[0],rd=rd,rn=rn,
            immediate=((word>>10)&0xfff)*memory[1],addressing='offset')
    unscaled={0xb8000000:'wstur',0xb8400000:'wldur',0xbc000000:'sstr',
        0xbc400000:'sldr',0xfc000000:'dstr',0xfc400000:'dldr'}.get(single)
    if unscaled:
        return BroadInstruction(address,word,unscaled,rd=rd,rn=rn,
            immediate=_signed((word>>12)&0x1ff,9),addressing='offset')
    # MOVI .2s, #imm8, LSL #24: Q=0, op=0, cmode=0110, op2=0.
    # Immediate is the encoded imm8; no vector/FP value evaluation is implied.
    if word & 0xfff8fc00 == 0x0f006400:
        return BroadInstruction(address, word, 'movi_2s_lsl24', rd=rd,
                                immediate=((word >> 16) & 7) << 5 | ((word >> 5) & 31))
    # Preserve historical xstr/xldr descriptors for their admitted SP/X29 bases.
    raw = {0xf9000000: ('xstr_raw', 8), 0xf9400000: ('xldr_raw', 8),
           0x3d800000: ('qstr', 16), 0x3dc00000: ('qldr', 16)}
    form = raw.get(word & 0xffc00000)
    if form and (form[0].startswith('q') or rn not in (29, 31)):
        kind, size = form
        return BroadInstruction(address, word, kind, rd=rd, rn=rn,
                                immediate=((word >> 10) & 0xfff) * size,
                                addressing='offset')
    kind = {0xf8000000: 'xstur', 0xf8400000: 'xldur'}.get(word & 0xffe00c00)
    if kind:
        return BroadInstruction(address, word, kind, rd=rd, rn=rn,
                                immediate=_signed((word >> 12) & 0x1ff, 9),
                                addressing='offset')

    # Exact scalar unscaled conversion encodings. Only S/D and W/X forms;
    # half precision, fixed-point scales, lane moves and unsigned conversions
    # are deliberately absent. All bits except Rd/Rn are matched.
    conversions = {}
    for fp, type_bits in (('s', 0), ('d', 0x400000)):
        for gp, sf in (('w', 0), ('x', 0x80000000)):
            conversions[0x1e220000 | type_bits | sf] = f'scvtf_{fp}_{gp}'
            conversions[0x1e380000 | type_bits | sf] = f'fcvtzs_{gp}_{fp}'
    conversions.update({0x1e270000: 'fmov_s_w', 0x9e670000: 'fmov_d_x',
                        0x1e260000: 'fmov_w_s', 0x9e660000: 'fmov_x_d',
                        0x1e204000: 'fmov_s_reg', 0x1e604000: 'fmov_d_reg'})
    kind = conversions.get(word & 0xfffffc00)
    if kind:
        return BroadInstruction(address, word, kind, rd=rd, rn=rn)
    for fp, type_bits in (('s', 0), ('d', 0x400000)):
        if word & 0xffe01fe0 == (0x1e201000 | type_bits):
            # Encoded imm8, not an integer or a computed floating point value.
            return BroadInstruction(address, word, f'fmov_{fp}_imm', rd=rd,
                                    immediate=(word >> 13) & 0xff)
        if word & 0xffe0fc00 == (0x1e201800 | type_bits):
            return BroadInstruction(address, word, f'fdiv_{fp}', rd=rd, rn=rn,
                                    rt2=(word >> 16) & 31)
        if word & 0xffe0fc1f == (0x1e202000 | type_bits):
            return BroadInstruction(address, word, f'fcmp_{fp}_reg', rn=rn,
                                    rt2=(word >> 16) & 31)
        # Canonical Rm=0 comparison with +0.0. FCMPE remains unsupported.
        if word & 0xfffffc1f == (0x1e202008 | type_bits):
            return BroadInstruction(address, word, f'fcmp_{fp}_zero', rn=rn)

    # Narrow unsigned-offset and signed-unscaled accesses only. The same kind
    # has byte offset semantics in either encoding; no base writeback. Signed
    # loads, pre/post-index, register offsets, atomics and FP accesses excluded.
    unsigned = {0x39000000: ('wstrb', 1), 0x39400000: ('wldrb', 1),
                0x79000000: ('wstrh', 2), 0x79400000: ('wldrh', 2)}
    unscaled = {0x38000000: 'wstrb', 0x38400000: 'wldrb',
                0x78000000: 'wstrh', 0x78400000: 'wldrh'}
    form = unsigned.get(word & 0xffc00000)
    if form:
        kind, size = form
        return BroadInstruction(address, word, kind, rd=rd, rn=rn,
                                immediate=((word >> 10) & 0xfff) * size,
                                addressing='offset')
    kind = unscaled.get(word & 0xffe00c00)
    if kind:
        return BroadInstruction(address, word, kind, rd=rd, rn=rn,
                                immediate=_signed((word >> 12) & 0x1ff, 9),
                                addressing='offset')
    return historical_decode(word, address)
