# Broad Swift exact callsite admission

`admit_broad_swift_callsite(image, caller, call_pc)` is an offline syntactic
call-target boundary. It does not execute the inspected image. Its result does
not establish an ABI profile, error register, return type, call-return behavior,
post-call error state, or exclusive runtime entry.

Direct BL and tail B require the exact source function and instruction word, a
unique executable selected-slice mapping, a bounded aligned target at an
independent LC_FUNCTION_STARTS entry, and one public file-backed nlist symbol. A narrow broad-parser exception also
admits one local N_SECT symbol with zero descriptor flags when its entire name
independently parses as a concrete generic specialization with explicit
bindings. Ordinary local N_SECT methods/functions remain refused; this exception
establishes syntax only and never supplies ABI qualification.
All nlist records at the target participate. Contradictory aliases, private or
weak visibility outside the exact exceptions below, alternate entries, resolvers, stubs, relocations, active
encryption, and embedded code-data declarations decline the supported proof.
Tail B produces a candidate without post-call claims. Unsupported declaration
syntax retains the independently admitted target with `syntax_unresolved`.

A BLR can additionally produce `call_kind: blr_constant` when every instruction
from the caller entry to the call belongs to the bounded straight-line constant
model. It supports ADR, ADRP plus immediate ADD, 64-bit MOVZ/MOVN/MOVK, unshifted
register MOV aliases, and NOP. Unknown source values and unknown instructions
remain unresolved. W-register writes invalidate the corresponding X value;
MOVK requires an already known complete register. Arithmetic overflow declines
the constant proof. Literal loads, data loads, vtable/witness dispatch, pointer
authentication, and source/demangler-derived target guesses are unsupported.

The indirect proof also independently reads executable selected-image words,
within `max_entry_screen_instructions`, and checks direct B/BL, B.cond and BC.cond, CBZ/CBNZ,
and TBZ/TBNZ targets for entry after the prefix start through the call itself.
Such incoming edges and all non-debug nlist entries in that interval prevent
admission, including absolute-symbol aliases.
Unknown other indirect transfers prevent admission; conventional RET x30 is
permitted. This is a selected-image syntactic screen. It does not assert absence
of transfers from foreign images, runtime patching, or arbitrary return-address
changes. `exclusive_entry_proven` remains false. Caller-entry execution is the
explicit proof boundary.

Both direct and indirect results retain the selected-image identity, the full
raw CPU header, segment/section mappings and protections, bounded function-start
ULEB data, symbol records, and every instruction byte used. These raw metadata
must agree with the supplied image's cached section/function boundaries.
`callsite_binding_matches` detects changes to these dependencies without
rehashing an already admitted source. It is a binding check for a previously
produced record, not an authentication mechanism for arbitrary supplied JSON.

Every loop/read consumes a work budget; all serialized metadata string fields
are bounded. Indirect work is refused before scanning when the selected-text
instruction count exceeds the configured cap. The implementation does not
silently widen a prefix, perform a corpus scan, or infer a target when the
budget or instruction model is exhausted.

Evidence: the pre-indirect revision `fc3fd2e` passed 16 synthetic unit tests.
The added indirect behavior passed eight new focused test methods, including
independently chosen ADR/ADRP/ADD/MOV-wide words, narrow clobbers, incoming-entry
attacks, target visibility/entry requirements, changed-byte bindings and budget
refusals. Those receipts have different source inputs and are not a claim that
the current entire module or a compiler corpus has been rerun.

The saved fixed-v2 optimized corpus disassembly was read without regeneration.
Examples at `0xe64` and `0x1158` derive x8 from incoming x0 before BLR and provide
no constant target provenance; their code-visible call syntax remains
unresolved. The synthetic constant cases do not constitute compiler coverage.

A subsequent specialization/entry-screen revision passed four new focused
methods after reproducing the missing local specialization support, absolute
symbol entry gap, and FEAT_HBC BC.cond gap. Local/private/alternate-entry and
malformed-specialization negatives remained refused. The raw symbol evidence
retains n_type/n_sect/n_desc, selected-slice and container record offsets,
visibility, a local-specialization flag, and the parsed specialization kind.

The recorded compiler's unique concrete generic specializations can additionally
use exactly N_PEXT|N_SECT (0x1e) with exactly WEAK_DEF (0x80). This exception is
restricted to an exact local direct BL, the same sole-symbol/entry/mapping
checks, and the independent concrete-specialization syntax predicate. It is
recorded as `private_extern_weak_concrete_specialization`, never public. Other
private/weak flag combinations, ordinary declarations, tail B, and BLR do not
gain this exception. Independent byte-level ABI qualification is still required
before any ABI-dependent consumer may use it. Two new focused methods first
reproduced the unsupported flag tuple and then passed with scope negatives.

A separate direct-BL exception admits exactly N_PEXT|N_SECT (0x1e) with
zero descriptor flags for a fully consumed, supported, throwing static-method
declaration whose innermost nominal context is a class. It records
`private_extern_throwing_class_static_body` and `private_extern_static_body: true`.
The raw target must still have one symbol, an independent LC_FUNCTION_STARTS
entry and a unique executable mapping. This names a private implementation body;
it does not infer dynamic dispatch from a class-method spelling. Tail B, BLR,
ordinary local N_SECT, nonthrowing methods, instance methods, struct/enum static
methods, dispatch thunks and function-signature specializations gain no support.
Nominal and ABI admission remain separate mandatory boundaries. Four new
synthetic methods passed in composed focused receipts after reproducing the visibility refusal,
covering exact flags, context, whole parse, aliases, interior targets, changed
bindings and live capability custody. Earlier component and compiler receipts
were reused; no corpus result is claimed for the repaired source here.

## Invocation-owned session and capability

`create_callsite_session(image, limits=...)` independently parses the invariant
raw metadata and the bounded symbol directory once. The frozen session retains
that read footprint and a private symbol/function index. Its
`initial_work_steps` must be charged once by the invocation owner. There is no
global cache, hash pass, or import of report/producer ledgers. Reuse requires the
same immutable image, data, section tuple and function tuple objects, plus the
same selected-image scalar identity. Ordinary constructors, replacement images,
and `dataclasses.replace` cannot inherit factory custody.

`admit_broad_swift_callsite(..., session=session)` still performs each call's
instruction/constant proof, entry screen, symbol-string parse, visibility and
specialization checks. Its `work_steps` are incremental. Session-backed JSON
bindings require that exact live session to check; a copied JSON report is not
an admission capability.

`admit_callsite_capability(...)` returns a private frozen capability whose
`record()` returns a detached JSON-compatible copy, including refusal results.
An implicit session's initial work is included in that record's work count;
with an explicit session it is reported separately. Resource exhaustion during
session creation or bounded capability copying raises `CallsiteSessionError`
with `reason` and `work_steps`.

`validate_callsite_capability(image, capability, max_work=...)` accepts only a
factory-minted successful capability with exact live image/session custody and
matching per-call bytes. A dict, serialized record, lookalike object, failed
admission or replacement image has no authority. Its returned record reports
validation-only `work_steps` and preserves the original count as
`admission_work_steps`, avoiding duplicate admission charges. The capability
boundary assumes a trusted Python process; deliberate private-state mutation
through Python internals is outside this boundary.

Five new focused session methods passed after the missing API initially failed.
They cover image/byte custody, detached/serialized/forged records, frozen
construction, resource limits, implicit versus explicit work charging,
private-weak specialization, and the BC.cond refusal through the cached path.
The independent outcome validator must retain its own metadata ledger; neither
the B5 session nor capability is validator evidence.
