"""Hand-encoded ARM64 words and a tiny function builder for the indirect-target tests.

Every word is encoded from the Arm Architecture Reference Manual; no production decoder is
used to build inputs, and no word is ever executed.
"""

BASE = 0x100001000


def blr(rn): return 0xd63f0000 | rn << 5
def br(rn): return 0xd61f0000 | rn << 5
def ret(): return 0xd65f03c0
def blraaz(rn): return 0xd63f081f | rn << 5
def braaz(rn): return 0xd61f081f | rn << 5
def nop(): return 0xd503201f
def mov(rd, rm): return 0xaa0003e0 | rm << 16 | rd
def add_imm(rd, rn, imm): return 0x91000000 | imm << 10 | rn << 5 | rd
def sub_imm(rd, rn, imm): return 0xd1000000 | imm << 10 | rn << 5 | rd
def movz(rd, imm): return 0xd2800000 | imm << 5 | rd
def ldr(rt, rn, off): return 0xf9400000 | (off // 8) << 10 | rn << 5 | rt
def str_(rt, rn, off): return 0xf9000000 | (off // 8) << 10 | rn << 5 | rt
def ldur(rt, rn, imm): return 0xf8400000 | (imm & 0x1ff) << 12 | rn << 5 | rt
def ldp(rt, rt2, rn, off, mode=2):
    return {2: 0xa9400000, 1: 0xa8c00000, 3: 0xa9c00000}[mode] | ((off // 8) & 0x7f) << 15 | rt2 << 10 | rn << 5 | rt
def stp(rt, rt2, rn, off): return 0xa9000000 | ((off // 8) & 0x7f) << 15 | rt2 << 10 | rn << 5 | rt
def ldr_w(rt, rn, off): return 0xb9400000 | (off // 4) << 10 | rn << 5 | rt
def ldr_literal(rt, pc, target): return 0x58000000 | (((target - pc) // 4) & 0x7ffff) << 5 | rt
def bl(pc, target): return 0x94000000 | (((target - pc) // 4) & 0x3ffffff)
def b(pc, target): return 0x14000000 | (((target - pc) // 4) & 0x3ffffff)
def bcond(pc, target, cond=0): return 0x54000000 | (((target - pc) // 4) & 0x7ffff) << 5 | cond
def cbz(rt, pc, target): return 0xb4000000 | (((target - pc) // 4) & 0x7ffff) << 5 | rt
def adrp(rd, pc, page):
    imm = (page - (pc & ~0xfff)) >> 12
    return 0x90000000 | (imm & 3) << 29 | ((imm >> 2) & 0x7ffff) << 5 | rd
def adr(rd, pc, target):
    imm = target - pc
    return 0x10000000 | (imm & 3) << 29 | ((imm >> 2) & 0x7ffff) << 5 | rd
MRS_TPIDR_X8 = 0xd53bd048   # mrs x8, tpidr_el0 (system group, writes x8)
CNTD_X8 = 0x04e0e3e8        # cntd x8 (SVE group, writes x8)
ADD_X8_X9_X10 = 0x8b0a0128  # add x8, x9, x10
LDXP_X8_X9_X0 = 0xc87f2408  # ldxp x8, x9, [x0] (writes two registers)
SUB_SP_SP_X9 = 0xcb2963ff   # sub sp, sp, x9 (writes sp through the extended-register form)


class Fn:
    """A function under construction at a fixed address."""

    def __init__(self, start=BASE):
        self.start, self.w = start, []

    @property
    def pc(self):
        return self.start + 4 * len(self.w)

    def add(self, *words):
        self.w.extend(words)
        return self

    def bl(self, target):
        return self.add(bl(self.pc, target))

    def adrp(self, rd, page):
        return self.add(adrp(rd, self.pc, page))

    def adr(self, rd, target):
        return self.add(adr(rd, self.pc, target))

    def literal(self, rt, target):
        return self.add(ldr_literal(rt, self.pc, target))

    def at(self, index):
        return self.start + 4 * index

    @property
    def site(self):
        return self.start + 4 * (len(self.w) - 1)


