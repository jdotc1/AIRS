# Bounded scalar W UDIV

The source model `arm64-bounded-w-udiv-v43` adds exact scalar W unsigned division
to the existing X UDIV family. Schema remains 1. Historical identities, including
v42 signed division, remain distinct under Python and native import admission.
No memory, CFI, loop, pointer-authentication or asynchronous scope expands.

## Shared decoding and transfer

The mask `0x7fe0fc00` must equal `0x1ac00800`; sf selects W or X. All other
nonoperand bits remain fixed. Rd, Rn and Rm layout reuses the owned MacScope
two-source mapping already adapted for X UDIV. Donor source and tests are unchanged.
The transfer reuses AIRS's unsigned quotient calculation and `PathState.write_w`.

Read both raw source operands before writing an aliased destination. Reject
either derived-stack operand before projection, zero-divisor simplification or
destination discard, including outside strict-call-state mode. Both inputs must
be concrete; original/unknown inputs stay unknown even with a known zero divisor
or equal register operands. Registers 31 are zero/discard registers, never SP.

Mask each concrete operand to low32 and interpret it as unsigned. A concrete zero
divisor yields zero; otherwise compute an integer unsigned quotient. Write through
the existing W helper, zero-extending into X and destroying full-X provenance.
For example `0xffffffff / 2` stores `0x000000007fffffff`, and high bits of either
incoming X operand cannot change its low32 unsigned interpretation. NZCV, SP,
memory and unrelated registers remain unchanged. Frame-body W29 writes refuse;
modified preserved registers require justified recovery.

Arm's [2025 instruction reference](https://documentation-service.arm.com/static/67e40f3398aa3c3b6eea6a85),
A64 UDIV page 1057, specifies the 32-bit form, unsigned operand interpretation,
zero-divisor result and unchanged flags. The independent test oracle performs
fixed 32-step long division without the production host-quotient operation.

## Owned examples and recovery boundaries

A tiny owned leaf performs W UDIV and RET without modifying required preserved
identities. It gains bounded modeled-leaf agreement. A fixed-control neighbor
stays unresolved with no checked PCs. Decoder admission alone does not guarantee
supported symbolic effects or valid recovery.

The nonleaf witness saves X19/X20 and FP/LR, places all-ones in X0 and 2 in X1,
computes UDIV W19,W0,W1, calls a separately declared owned sink, and restores its
saved registers. Correct saved-X19 metadata agrees. Omitting X19 recovery gives
a concrete synchronous-call-site inconsistency: observed X19 is `0x7fffffff` at
preferred VM PC `0x10000101c`. Unknown inputs, possible-only discrepancies and
later unknown recovery retain unresolved precedence.

Two independent complete owned Mach-O variants carry these code bytes, compact
unwind records and LC_FUNCTION_STARTS. They are parsed and audited without parser
substitutes. The first wrong-metadata report supplies the native admission fixture
without re-auditing or rehashing it. This is new bounded parser/engine composition,
not an unchanged library audit, representative prevalence study or whole-image
correctness claim.

The model transition also updates affected refusal controls and separates
historical import tests from current-producer assertions. Historical native v42
fixtures remain unchanged. See UDIV_W_RESULTS.md for fresh/reused/unexecuted scope.
