Later source v46 adds scalar X REV32 separately; see [REV32](REV32.md).
Earlier subset descriptions and receipts below retain their historical meaning.
Vector forms remain excluded.

Historical v44 subset: source v45 adds scalar REV16 separately through the shared
state path. See [REV16](REV16.md). The original v44 scope and receipts below retain
their historical meaning; X REV32 and vector forms remain excluded.

# Bounded scalar byte reversal

Source model `arm64-bounded-rev-v44` adds only full-register byte REV in scalar
W and X forms. The schema remains 1. Exact v44 Python/native import admission
retains v43, v42 and earlier identities. No memory, CFI, loop, vector,
pointer-authentication or asynchronous scope expands.

## Encoding and owned reuse

With mask `0xfffffc00`, the instruction must equal `0x5ac00800` (W) or
`0xdac00c00` (X). Rd and Rn are the only variable fields. The encodings differ
in both sf and opcode, so merely allowing sf to vary would admit the wrong subset.
REV16 W/X, X REV32, the unmodeled W opcode3 neighbor, CLS and vector forms remain
refused. A decoder refusal is not a general ISA-validity classification.

Field mapping and scalar width/opcode distinction reuse the owned MacScope
`ARM64Decoder+DataProcessingRegister.decodeDataProcessingOneSource` design.
Its IR builder's source-before-destination transform handling was inspected
read-only. Donor code/tests were unchanged and unexecuted. AIRS reuses its own
PathState, register helpers, W write, frame-effect classification and recovery
machinery. The new concrete transfer is a bounded four/eight-iteration byte loop.

Arm's A64 REV entry in the [2025 instruction reference](https://documentation-service.arm.com/static/67e40f3398aa3c3b6eea6a85),
page 758, specifies full-width byte order reversal for these two forms. The test
oracle independently uses byte serialization and opposite-endian interpretation
rather than the production shift loop.

## Consumed and produced state

Read the raw source before writing the destination. Reject a derived-stack source
before truncation or discard, even outside strict call-state mode. Concrete inputs
are masked to 32/64 bits and their byte order is reversed. A W result uses the
existing zero-extending W write; an X result uses the full-width register write.
Rn/Rd 31 mean zero/discard, never SP. Aliases consume the old source value.

Original identities and unknowns stay unknown. In particular, two symbolic REV
operations are not simplified into a restored original register identity. Two
concrete REV operations recover only the masked concrete input. W writes cannot
recover an original full-X identity by assumption. NZCV, memory, SP and unrelated
registers are unchanged. Body W29/X29 writes retain the existing frame-transition
refusal. Changed preserved registers still need justified recovery.

Examples: REV W of `0x01234567` yields `0x67452301`; REV X of
`0x0123456789abcdef` yields `0xefcdab8967452301`. Reversing W from a source whose
low32 has its top bit set still zero-extends the resulting 32 bits into X.

## Owned recovery examples

A tiny leaf may reverse a volatile register and retain bounded modeled-leaf
agreement. Halfword/partial reversal neighbors remain unresolved with no checked
PCs. Decode admission alone does not establish supported state or recovery.

The complete owned examples save X19/X20 and FP/LR, put `0x1234` in X0, reverse
into W19 or X19, call a separately declared owned sink, then restore saved state.
Correct X19 recovery metadata agrees. Omitting X19 recovery produces a concrete
synchronous-call-site inconsistency at preferred PC `0x10000101c`: observed
`0x34120000` for W and `0x3412000000000000` for X. Unknown inputs stay unresolved
with no supported checked PCs. Possible-only discrepancies and later unknown
recovery retain unresolved precedence.

Six new finalized Mach-O identities cover correct, wrong and unknown recovery
for both widths. The unchanged owned layout builder is reused with checked
instruction replacements; its unsigned intermediate is never audited or hashed.
The first emitted reports supply native codec fixtures directly. These are
constructed bounded examples, not representative prevalence or whole-image
correctness claims. See REV_RESULTS.md for exact fresh/reused qualification.
