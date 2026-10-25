# Bounded scalar CLS

Source model `arm64-bounded-cls-v47` adds scalar count-leading-sign bits in W/X
forms. Schema remains 1. Exact Python/native import admission retains historical
models. No vector, memory, CFI, loop or asynchronous scope expands.

## Exact controls and meaning

Mask `0x7ffffc00` must equal `0x5ac01400`; sf selects W/X. Only source and
destination register fields vary. The owned MacScope one-source dispatch already
recognizes CLS at this opcode; its mapping is reused without donor modifications.
The transfer reuses AIRS's CLZ state, raw-source, write and recovery handling.

Arm's A64 CLS entry in the [2025 instruction reference](https://documentation-service.arm.com/static/67e40f3398aa3c3b6eea6a85),
page 157, counts the repeated sign-bit values below the most significant bit.
That sign bit itself is excluded. Thus W zero/all-ones yields 31 and X zero/all-ones
yields 63. These results differ from CLZ, which counts zeros rather than redundant
sign bits. A zero-register source yields the corresponding CLS zero-input count.

Read raw source before an aliased write. Reject a derived-stack source before
projection or discard, with `cls_stack_address_not_modeled`. Historical CLZ error
codes and messages remain unchanged. Concrete inputs are masked to 32/64 bits.
For negative signed inputs, complement the masked bits within that width; positive
inputs retain their bits. The count is width-minus-one minus normalized bit_length.
A W result uses the existing zero-extending write; X writes its full count.

The independent oracle scans individual bits below the sign bit without using
bit_length or the production normalization. Literal cases cover zero, all-ones,
positive/negative one-step boundaries, sign transitions, high-bit truncation and
aliasing. Original/unknown inputs remain unknown; repeated CLS cannot establish
restored register provenance. Rd/Rn31 mean discard/zero, never SP. NZCV and its
condition consumers, SP, memory and unrelated state remain unchanged. Body
W29/X29 writes and unrestored preserved-register mutations remain refused.

## Owned recovery examples

The complete-image witness saves X19/X20 and FP/LR, puts
`0xffffffffffffedcb` in X0 using MOVN X0,#0x1234, counts into W19 or X19,
calls a separately declared owned sink, then restores saved state. The modeled
counts are 18 (`0x12`) for W and 50 (`0x32`) for X, at preferred call PC
`0x10000101c`.

Correct X19 recovery metadata agrees. Missing X19 recovery produces a concrete
synchronous-call-site inconsistency. Unknown inputs remain unresolved with no
supported checked PCs; possible-only and later-unknown precedence are preserved.
Six new complete final Mach-O identities cover these three outcomes at both
widths through real parsing and engine emission. The unchanged owned layout
builder's intermediate is never audited or hashed. First reports directly supply
native fixtures without replaying accepted inputs.

These constructed examples do not measure prevalence or prove whole-image
correctness. See CLS_RESULTS.md for fresh/reused checks and remaining gates.
