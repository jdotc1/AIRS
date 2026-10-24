# Bounded scalar W SDIV

The new source model is `arm64-bounded-w-sdiv-v42`; schema remains 1. V41 and
older identities retain their exact import meaning. This increment adds only
scalar W SDIV to the existing X SDIV family. W UDIV remains refused. No memory,
CFI, loop, pointer-authentication or asynchronous scope expands.

## Encoding and transfer

Mask `0x7fe0fc00` must equal `0x1ac00c00`. All nonoperand controls except sf
are fixed; sf selects W or X. Rd, Rn and Rm mapping reuses the owned MacScope
`ARM64Decoder+DataProcessingRegister.decodeDataProcessingTwoSource` layout.
MacScope was inspected read-only; its source and tests were not changed or run.
AIRS reuses the existing X signed transfer and `PathState.write_w`, not a parallel
symbolic engine.

Read both raw original source values before any write or width projection.
Reject either derived-stack source before zero-divisor simplification or discard,
including outside strict call-state mode. Both inputs must be concrete. Original
identities and unknowns produce unknown, including unknown/zero and symbolic x/x.
Registers 31 are zero/discard registers, never SP.

Concrete W operands are masked to low32, interpreted as signed32 and divided
using integer magnitude division with sign reapplied, truncating toward zero.
A concrete zero divisor yields zero; INT32_MIN/-1 yields low32 `0x80000000`.
Mask the result to32 and zero-extend through the existing W write. In particular,
-7/3 stores X value `0x00000000fffffffe`, not a sign-extended X result. NZCV,
memory and unrelated state remain unchanged. W writes do not preserve original
full-X identities. Frame-body W29 writes remain refused; un-restored preserved
registers remain unresolved.

The architectural reference is Arm's A64 SDIV entry in the
[2025 instruction reference](https://documentation-service.arm.com/static/67e40f3398aa3c3b6eea6a85).
The source review used the indexed SDIV excerpt for its 32-bit form, signed
magnitude quotient and zero-divisor behavior; no target code was executed.

## Owned examples and independent expectations

The minimal owned leaf uses literal SDIV W0,W0,W1 followed by RET. It modifies
only a volatile register and preserves required caller identities; bounded leaf
agreement is expected even though its arithmetic inputs are symbolic. The W UDIV
neighbor remains unresolved with no checked PCs.

The owned nonleaf saves X19/X20 and FP/LR, puts -7 and3 in X0/X1, writes W19
through SDIV, calls an independent owned sink, then restores the saved registers.
Correct saved-X19 metadata agrees. Omitting X19's recovery rule produces a concrete
call-site inconsistency: the observed X19 is `0xfffffffe`, not original X19.
Unknown inputs, possible-only mismatches and later unknown recovery retain
unresolved precedence. This is a constructed witness, not a compiler sample or
measured real-world frequency improvement.

The test oracle uses fixed 32-step long division independently of the production
host-integer quotient. It covers mixed signs, truncation, zero division, signed
minimum overflow, high-bit truncation of both inputs, aliases, ZR/discard,
provenance refusal and recovery. Python/native strict v42 admission remains an
import contract, not verification of a producer's semantic claims.

See SDIV_W_RESULTS.md for actual checks and separate distribution gates.
