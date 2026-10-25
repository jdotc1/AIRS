Later source v46 adds scalar X REV32 separately; see [REV32](REV32.md).
Earlier subset descriptions and receipts below retain their historical meaning.
Vector forms remain excluded.

# Bounded scalar REV16

Source model `arm64-bounded-rev16-v45` adds exact scalar REV16 W/X, swapping
bytes within each 16-bit halfword. Schema remains 1. Historical v44 full-width REV
and earlier model identities retain their original import meaning. X REV32,
vector forms, new memory/CFI/loop behavior and asynchronous scope remain excluded.

## Encoding, state and reuse

With mask `0x7ffffc00`, the instruction must equal `0x5ac00400`; sf selects
W/X. All nonoperand controls except sf are fixed. Rd/Rn31 mean discard/zero,
never SP. The mapping reuses the owned MacScope one-source dispatch already
adapted for REV. No donor files or tests changed.

Arm's A64 REV16 entry in the [2025 instruction reference](https://documentation-service.arm.com/static/67e40f3398aa3c3b6eea6a85),
page 760, defines per-halfword byte reversal. Lane positions are preserved; this is
not full-register reversal. For example W `0x01234567` becomes `0x23016745`,
and X `0x0123456789abcdef` becomes `0x23016745ab89efcd`.

AIRS extends the existing REV state-handling path. Read the raw source before
writing an alias. Reject derived-stack sources before projection or discard,
including outside strict-call-state mode. Mask concrete inputs to 32/64 bits,
then swap adjacent bytes with the low-byte lane mask `0x00ff00ff` or
`0x00ff00ff00ff00ff`. A W result uses the existing zero-extending write; X
retains 64 bits. The old full-width REV byte loop remains under its own branch.

Unknown and original values stay unknown, including symbolic double REV16. No
whole-X identity is inferred from a W result. NZCV and condition consumers, memory,
SP and unrelated registers are unchanged. The shared
`rev_stack_address_not_modeled` error and frame/preserved-register guards remain.
W29/X29 body writes refuse, and modified X19 still needs justified recovery.

The independent oracle serializes bytes and reverses each two-byte chunk, rather
than using the production lane-mask expression. Fixed examples cover high bits,
negative values, lane distinction, aliases, ZR/discard and concrete double reversal.

## Owned recovery examples

The complete-image witness saves X19/X20 and FP/LR, sets X0 through
MOVN X0,#0x1234, executes REV16 into W19 or X19, calls a separately declared sink,
then restores the saved registers. The original X0 is `0xffffffffffffedcb`.
The observed result is `0xffffcbed` for W, zero-extended into X, or
`0xffffffffffffcbed` for X. Both retain preferred call PC `0x10000101c`.

Correct X19 recovery metadata agrees. Missing X19 recovery produces a concrete
synchronous-call-site inconsistency. Unknown inputs remain unresolved with no
supported checked PCs; uncertain-path and later-unknown precedence are retained.
Six new finalized images cover these three cases at both widths using the existing
owned layout. The builder intermediate is never audited or hashed. First reports
supply native fixtures without replaying accepted inputs.

These are constructed bounded examples, not real-world prevalence or whole-image
correctness evidence. See REV16_RESULTS.md for fresh, reused and unexecuted scope.
