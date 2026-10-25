# Bounded scalar REV32 X

Source model `arm64-bounded-rev32-v46` adds exact scalar REV32 X. It reverses
bytes within each 32-bit word of a 64-bit register without exchanging the two words.
The corresponding W encoding remains the existing full-register REV W; no new
W REV32 form is introduced. Schema remains 1. Historical model meanings are retained.
No vector, memory, CFI, loop or asynchronous scope expands.

## Exact controls and shared state handling

Mask `0xfffffc00` must equal `0xdac00800`. Only Rd and Rn vary. The owned MacScope
one-source mapping distinguishes this X form from W REV at the same opcode and
from X full-register REV at the next opcode. Donor code/tests are unchanged.
The unmodeled W opcode3 neighbor, CLS and vector forms remain refused; refusal
is an AIRS admission boundary, not a general ISA-validity claim.

Arm's A64 REV32 entry in the [2025 instruction reference](https://documentation-service.arm.com/static/67e40f3398aa3c3b6eea6a85),
page 762, describes the per-word byte transformation. For example
`0x0123456789abcdef` becomes `0x67452301efcdab89`. Full-register REV and REV16
would produce different results from that input.

The shared REV transfer reads the raw source before any aliased write. Derived
stack addresses reject before masking or destination discard. Concrete inputs
are masked to 64 bits. The existing adjacent-byte swap stage is followed by a
16-bit-half swap within each 32-bit lane using mask `0x0000ffff0000ffff`.
The existing full-REV loop and REV16 lane expression retain their separate paths.
Rd/Rn31 mean discard/zero, never SP. X writes preserve the full modeled 64-bit value.

Unknown and original values stay unknown, including symbolic double reversal.
Concrete double reversal recovers only the masked concrete value. NZCV/condition
consumers, SP, memory and unrelated registers remain unchanged. Existing raw-stack,
frame-body X29 and unrestored preserved-register guards remain conservative.

An independent oracle serializes the masked 64-bit value and reverses each four-
byte chunk. Literal cases detect accidental word exchange, halfword-only reversal,
whole-register reversal, sign effects or failure to discard bits above 64.

## Owned recovery evidence

The complete-image witness saves X19/X20 and FP/LR, sets X0 with
MOVN X0,#0x1234 to `0xffffffffffffedcb`, reverses bytes within each 32-bit word
into X19, calls a separately declared owned sink, then restores saved state.
The modeled result is `0xffffffffcbedffff`, observed at preferred call PC
`0x10000101c` when X19 recovery is omitted.

Correct recovery metadata agrees. Missing X19 recovery gives a concrete
synchronous-call-site inconsistency. An unknown source remains unresolved with
no supported checked PCs; possible-only and later-unknown precedence are retained.
Three new complete final Mach-O identities exercise these outcomes through real
parsing and engine emission without mocks. The unchanged layout builder is reused
with checked instruction replacements; its intermediate is never audited or hashed.
First reports supply native codec fixtures directly.

These deliberately owned examples do not measure representative prevalence or
prove whole-image correctness. See REV32_RESULTS.md for exact qualification scope.
