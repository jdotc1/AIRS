Current source model: `arm64-bounded-test-bit-branch-v50` adds exact TBZ/TBNZ
through the existing bounded conditional-edge machinery. Unknown predicates fork
and raw stack sources refuse. See TEST_BIT_BRANCH.md and TEST_BIT_BRANCH_RESULTS.md.
Historical checkpoints below retain their meaning.

Current source model: `arm64-bounded-compare-branch-v49` adds CBZ/CBNZ W/X
through existing bounded paths, loops and shared teardowns. Raw stack values
refuse and uncertain edges retain uncertainty. See COMPARE_BRANCH.md and
COMPARE_BRANCH_RESULTS.md. Earlier checkpoints retain their meaning.

Current source model: `arm64-bounded-movk-v48` adds exact W/X MOVK with
conservative retained-bit provenance and existing frame/recovery guards. See
MOVK.md and MOVK_RESULTS.md. Earlier checkpoints retain their meaning.

Current source model: `arm64-bounded-cls-v47` adds scalar W/X count-leading-sign
bits through existing CLZ state handling. The sign bit itself is excluded. Raw-stack,
unknown/provenance, frame and synchronous-recovery boundaries remain conservative.
Exact Python/native admission retains historical labels. See [CLS](CLS.md) and
[bounded qualification](CLS_RESULTS.md). Earlier checkpoints retain meaning.

Current source model: `arm64-bounded-rev32-v46` adds exact scalar X byte reversal
inside 32-bit lanes through shared REV handling. W REV remains its existing form.
Raw-stack/unknown, frame and synchronous-recovery boundaries remain conservative.
Exact Python/native admission retains historical labels. See [REV32](REV32.md)
and [bounded qualification](REV32_RESULTS.md). Earlier checkpoints retain meaning.

Current source model: `arm64-bounded-rev16-v45` adds scalar byte swaps within
16-bit lanes through the existing REV state path. Raw-stack, unknown/provenance,
frame and synchronous-recovery boundaries remain conservative. Exact Python/native
model admission retains historical labels. See [REV16](REV16.md) and
[bounded qualification](REV16_RESULTS.md). Earlier checkpoints retain their meanings.

Current source model: `arm64-bounded-rev-v44` adds exact scalar full-width byte
REV W/X. Raw-stack and unknown-value refusal, zero-extending W writes, frame
transitions and synchronous recovery boundaries remain conservative. Python/native
exact model admission retains historical labels. See [REV](REV.md) and
[bounded qualification](REV_RESULTS.md). Earlier checkpoints retain their meanings.

Current source model: `arm64-bounded-w-udiv-v43` adds scalar W unsigned division
through the existing X transfer and zero-extending W write. Exact controls,
raw-stack refusal, unknown-state and recovery boundaries remain conservative.
Python/native model admission registers exact v43 and retains historical labels.
See [W UDIV](UDIV_W.md) and [qualification scope](UDIV_W_RESULTS.md).
Earlier checkpoint statements below retain their historical meanings.

Current source model: `arm64-bounded-w-sdiv-v42` adds scalar W signed division
through the existing X transfer and zero-extending W write. Raw stack provenance,
unknown inputs and recovery boundaries remain conservative. Exact Python/native
model admission includes v42 while retaining historical identities. See
[the W SDIV contract](SDIV_W.md) and [qualification scope](SDIV_W_RESULTS.md).
The following checkpoints are historical and retain their original meanings.

Current integrated model: `arm64-bounded-cfi-control-v41` adds bounded
fixed-width location advances and remembered recovery state through explicit
engine opt-in. Historical direct-parser defaults preserve v40 refusal, structural
preflight, overlap checks and global budget accounting. Exact report identities
v1–v40 and the alternate historical CFI-v36 remain distinct. See
[the v41 contract](CFI_CONTROL_V41.md). Raw signature evidence is independent
structural byte evidence and does not change unwind scope, verdict or trust.
Historical model checkpoints below retain their original meaning.

Current isolated model: `arm64-bounded-equivalent-compact-v39` admits fully
covering contiguous ranges with exactly equal frame/frameless compact encodings
through the existing auditor. Original metadata remains unchanged; changed rules,
gaps, overlaps, excluded modes and unknown recovery remain conservative. Sixteen
new Python methods, sixteen affected methods and three native admission methods
pass; the real native app debug target built. See EQUIVALENT_COMPACT.md and
EQUIVALENT_COMPACT_RESULTS.md. Accepted v38 workloads were not rerun, and release
integration remains separate. Historical checkpoints below retain their scope.

Current isolated model: `arm64-bounded-w-rbit-v38` adds exact scalar W RBIT,
reusing the X reversal transfer and existing zero-extending W write. Raw stack
sources still decline, symbolic values stay unknown, NZCV is unchanged and body
FP writes remain refused. Twelve new Python methods, three new native admission
methods and 23 affected existing methods pass in composed receipts. The real
native debug app target built; no prepared library was compiled or analyzed.
See RBIT_W.md and RBIT_W_RESULTS.md. Historical checkpoints below retain their
original scope; the release lane is unchanged.

# Analysis contract

Current isolated model: arm64-bounded-sdiv-v37 adds scalar X signed division with
concrete signed64 truncation toward zero, explicit zero/overflow behavior and
unchanged provenance/unknown/frame scope. Eighteen new Python methods, three new
native methods and twelve affected selectors pass. See SDIV_X.md and
SDIV_X_RESULTS.md. The retained complete nonleaf body gains typed call-site
agreement; no new whole-image/workload result or release action is claimed.

Previous isolated development model: arm64-bounded-fp-x-stack-v36 adds bounded
unsigned X29-relative X STR/LDR using known allocated-frame authority and the
existing slot/provenance/frame helpers. Eighteen new Python methods, three new
native methods and six affected checks pass; real native debug products built.
See FP_X_STACK.md, FP_X_STACK_RESULTS.md and CURRENT_ENGINE_MATRIX.md. The last
whole-image receipt remains v35; the prepared nonleaf-v35 workload remains unrun.

Current engine navigation: CURRENT_ENGINE_MATRIX.md identifies the isolated v37
subset, conservative boundaries, accepted receipts and separate release gates.
Frame-effect maintenance now shares one Instruction.changes_fp classification
across legacy and CFG body admission, preserving the prior v35 policy/model.
Five new and three affected methods pass; see FRAME_EFFECT_RESULTS.md. No native
or whole-image check was repeated for this source-only maintenance.

Isolated development checkpoint (21 October 2026): bounded SP-relative X stack
slots are implemented under `arm64-bounded-x-stack-v35`. Exact unsigned scaled
STR/LDR, known whole-slot reads, mixed-width invalidation, pointer escape/lifetime
and frame guards are qualified with 23 new Python methods, three new native
methods and three affected identity checks in composed receipts. The real native
debug products built; independent review and its corrected test typo are recorded
in X_STACK_SLOTS_RESULTS.md. See X_STACK_SLOTS.md for the bounded contract.
The subsequently authorized two-library comparison measured 16 agreement,
0 inconsistency, 0 unresolved with the same 16-function denominator, five
cumulative gains and no observed regressions. See V35_WHOLE_IMAGE_COMPARISON.md.
Release integration and GUI qualification are not claimed.

Previous isolated development checkpoint (21 October 2026): X-only UDIV is implemented
under model `arm64-bounded-udiv-v34`, following the accepted v33 RBIT change.
Sixteen new Python methods and five affected selectors pass in composed receipts;
independent semantic review found no actionable defect. Exact Python/native model
registration is qualified: the real native debug target built and all three new
admission tests passed after competing compilations cleared. This is not release
integration or a new aggregate result. See UDIV.md and UDIV_RESULTS.md. Subsequent older checkpoints
retain their original scope.

Previous isolated development model `arm64-bounded-rbit-v33` adds X-only scalar
RBIT with exact fixed-bit admission, concrete 64-bit reversal, conservative
unknowns, stack-provenance refusal and unchanged NZCV/recovery scope. Python and
native admission register its exact identity. See RBIT_X.md and RBIT_X_RESULTS.md.
This branch is separate from the release lane; no memory/CFI/loop/asynchronous
scope expands.

Previous model `arm64-bounded-clz-v32` adds scalar CLZ W/X only, with exact fixed-bit
admission, concrete width-masked leading-zero count, conservative unknown values,
raw stack-provenance rejection and unchanged flags/recovery scope. See CLZ.md and
CLZ_RESULTS.md. No memory, loop, CFI or asynchronous scope expands. Python report import
now registers the exact v32 model in the existing supported-finding admission
checks, matching native registration. Unknown model labels retain generic
wire-format handling; import acceptance is not semantic verification. See
V32_IMPORT_ADMISSION_RESULTS.md.

Previous model `arm64-bounded-sequential-loops-v31` admits at most two disjoint,
address-ordered natural loops. It retains the existing per-path state, shared
budget, all explored exits, unknown precedence and checked-PC recovery scope.
See `SEQUENTIAL_LOOPS.md` and `SEQUENTIAL_LOOPS_RESULTS.md`. Decoded loop count
is structural evidence, not an execution or termination claim.

Previous model `arm64-bounded-cfa-register-v30` adds only
`DW_CFA_def_cfa_register` (opcode `0x0d`) to the bounded FDE evaluator. It
switches an already-defined CFA base between SP and x29 while preserving its
unsigned bounded offset. Missing prior CFA, other registers, malformed operands,
unknown recovery, and any other unsupported CFI still decline. See
`CFA_REGISTER.md` and `CFA_REGISTER_RESULTS.md`. The previous
`arm64-bounded-loop-calls-v29` adds direct calls inside the v28
single-natural-loop subset when the existing framed-call target and ABI summary
apply. It checks recovery at original BL PCs; exact recurrence retains full
modeled state and whether a call occurred. See `LOOP_CALLS.md` and
`LOOP_CALLS_RESULTS.md`. Historical model sections below remain unchanged.

Previous model `arm64-bounded-loops-v28` added one natural loop with a conditional
backedge, adapting owned MacScope dominance/predecessor-closure code and scalar
loop witnesses. Complete path-local state recurrence closes safety exploration;
changing states are explored to exit or an unresolved budget. Calls inside the
loop in v28, setup/teardown participation and unsupported cycle shapes decline. No
termination or arithmetic-output claim is added. Contract/results:
`docs/BOUNDED_LOOPS.md`, `docs/BOUNDED_LOOPS_RESULTS.md`. Current app:
`dist/AIRS.app`; previous v27: `dist/high-multiply-v27/AIRS.app`. Earlier blocks
retain historical meanings.


Current model `arm64-bounded-high-multiply-v27` adds canonical SMULH/UMULH,
reusing owned MacScope decode/intrinsic operand handling and adding concrete
signed/unsigned high64 evaluation. Ra=31 is the bounded subset;noncanonical
spellings remain unresolved without an ISA-invalid claim. Unknown/provenance,
NZCV and recovery boundaries remain intact. Contract/results:
`docs/HIGH_MULTIPLY.md`, `docs/HIGH_MULTIPLY_RESULTS.md`. Current app:
`dist/AIRS.app`;previous v26:`dist/widening-multiply-v26/AIRS.app`. Earlier
sections retain historical meanings.

Current model `arm64-bounded-widening-multiply-v26` adds SMADDL/SMSUBL/
UMADDL/UMSUBL and SMULL/SMNEGL/UMULL/UMNEGL aliases,adapting owned MacScope
widening and accumulate algorithms. Factors project to signed/unsigned32;
accumulator/result remain64. Raw stack provenance is rejected before projection,
even in leaves. High-half multiplies remain unsupported. Contract/results:
`docs/WIDENING_MULTIPLY.md`, `docs/WIDENING_MULTIPLY_RESULTS.md`. Current app:
`dist/AIRS.app`;previous v25:`dist/multiply-v25/AIRS.app`. Earlier sections
retain historical meanings.

Current model `arm64-bounded-multiply-v25` adds bounded W/X MADD/MSUB and
MUL/MNEG aliases using adapted owned MacScope decoding and accumulate algorithms.
Exact controls,modular width,all-source unknown/provenance checks and unchanged
NZCV/recovery scope are explicit. Widening/high-half multiplies remain unsupported.
Contract/results:`docs/MULTIPLY.md`, `docs/MULTIPLY_RESULTS.md`. Current app:
`dist/AIRS.app`;previous v24:`dist/variable-shift-v24/AIRS.app`. Earlier sections
retain historical meanings.

Current model `arm64-bounded-variable-shift-v24` adds bounded W/X LSLV,
LSRV, ASRV and RORV, including register-count aliases. MacScope modulo-count,
signed/unsigned shift and rotate algorithms were adapted with exact controls,
conservative unknowns and provenance guards. Contract/results:
`docs/VARIABLE_SHIFT.md`, `docs/VARIABLE_SHIFT_RESULTS.md`. Current app:
`dist/AIRS.app`; previous v23:`dist/extract-v23/AIRS.app`. Earlier sections
retain historical meanings.

Current model `arm64-bounded-extract-v23` adds bounded W/X EXTR and immediate
ROR aliases using adapted owned MacScope algorithms and current guarded decoding.
Strict fixed controls, N/width, W shifts, concrete operands and provenance rules
retain conservative unknowns and unchanged checked scope. Contract/results:
`docs/EXTRACT.md`, `docs/EXTRACT_RESULTS.md`. Current app:`dist/AIRS.app`;
previous v22:`dist/bitfield-v22/AIRS.app`. Earlier sections are historical.

Current model `arm64-bounded-bitfield-v22` adds bounded W/X SBFM/BFM/UBFM
and extract/insert/shift/extend/clear aliases,retaining the legacy positive W LSL.
MacScope algorithms were adapted with strict encoding,width,merge and provenance
rules. Contract/results:`docs/BITFIELD.md`, `docs/BITFIELD_RESULTS.md`.
Current app:`dist/AIRS.app`;previous v21:`dist/conditional-select-v21/AIRS.app`.
Earlier sections retain historical meanings.

Current model `arm64-bounded-conditional-select-v21` adds X CSEL and W/X
CSINC/CSINV/CSNEG,including CSET/CSETM/CINC/CINV/CNEG aliases,while retaining W
CSEL. MacScope dispatch and false-arm transforms were adapted; NZCV and bounded
recovery identity rules remain explicit. Contract/results:
`docs/CONDITIONAL_SELECT.md`, `docs/CONDITIONAL_SELECT_RESULTS.md`.
Current app:`dist/AIRS.app`; previous v20:`dist/conditional-compare-v20/AIRS.app`.
Earlier sections retain historical meanings.

Current model `arm64-bounded-conditional-compare-v20` adds bounded W/X
CCMP/CCMN register and imm5 forms,EQ–LE predicates and literal NZCV fallback.
Unknown predicates remain conservative. Existing MacScope field decoding was
adapted; AIRS recovery boundaries remain intact. Contract/results:
`docs/CONDITIONAL_COMPARE.md`, `docs/CONDITIONAL_COMPARE_RESULTS.md`.
Current app:`dist/AIRS.app`; previous v19:`dist/carry-v19/AIRS.app`.
Earlier sections retain historical meanings.

Current model `arm64-bounded-carry-v19` adds bounded W/X ADC/ADCS/SBC/SBCS
register forms and NGC/NGCS aliases, with explicit incoming carry, borrow,
width and NZCV semantics. Unknown carry remains unknown. Exact semantics and
fresh/reused receipts: `docs/CARRY.md`, `docs/CARRY_RESULTS.md`. Current app:
`dist/AIRS.app`; previous v18:`dist/nonflag-register-v18/AIRS.app`.
Earlier sections retain historical model meanings.

Current model `arm64-bounded-nonflag-register-v18` adds bounded W/X AND/BIC/
ORR/ORN/EOR/EON register forms, LSL/LSR/ASR/ROR and MOV/MVN aliases, preserving
prior NZCV and the existing exact X MOV identity behavior. Exact semantics and
fresh/reused receipts are in `docs/NONFLAG_REGISTER.md` and
`docs/NONFLAG_REGISTER_RESULTS.md`. Current app: `dist/AIRS.app`; previous v17:
`dist/nonflag-immediate-v17/AIRS.app`. Earlier sections retain historical meanings.

Current model `arm64-bounded-nonflag-immediate-v17` adds bounded W/X AND, ORR
and EOR immediate and bitmask MOV aliases while preserving prior NZCV, including
unknown flags. Non-flag SP/WSP destinations remain unresolved. Exact semantics
and fresh/reused receipts are in `docs/NONFLAG_IMMEDIATE.md` and
`docs/NONFLAG_IMMEDIATE_RESULTS.md` from repository root. Current app:
`dist/AIRS.app`; previous v16: `dist/logical-immediate-v16/AIRS.app`.

Current model `arm64-bounded-logical-immediate-v16` adds bounded W/X
ANDS-immediate and TST with explicit repeated/rotated bitmask decoding. Exact
semantics and fresh/reused receipts are in `docs/LOGICAL_IMMEDIATE.md` and
`docs/LOGICAL_IMMEDIATE_RESULTS.md` from repository root. Earlier sections retain
historical model meanings. Current app: `dist/AIRS.app`; previous v15:
`dist/logical-flags-v15/AIRS.app`.

Current model `arm64-bounded-logical-flags-v15` adds bounded W/X ANDS/BICS
register forms and TST, with LSL/LSR/ASR/ROR operands. Exact semantics and fresh/
reused receipts are in `docs/LOGICAL_FLAGS.md` and `docs/LOGICAL_FLAGS_RESULTS.md`
from repository root. Earlier sections retain historical model meanings. Current
app: `dist/AIRS.app`; previous v14: `dist/extended-flags-v14/AIRS.app`.

Current model `arm64-bounded-extended-flags-v14` adds bounded extended-register
W/X ADDS/SUBS operands. Exact semantics and fresh/reused receipts are in
`docs/EXTENDED_FLAGS.md` and `docs/EXTENDED_FLAGS_RESULTS.md` from repository root.
Earlier sections retain historical model meanings. Current app: `dist/AIRS.app`;
previous v13: `dist/shifted-flags-v13/AIRS.app`.

Current model `arm64-bounded-shifted-flags-v13` adds bounded LSL/LSR/ASR
shifted operands to W/X ADDS/SUBS register forms. Exact semantics and fresh/reused
receipts are in `docs/SHIFTED_FLAGS.md` and `docs/SHIFTED_FLAGS_RESULTS.md` from
repository root. Earlier sections retain historical model meanings. Current app:
`dist/AIRS.app`; previous v12: `dist/register-flags-v12/AIRS.app`.

Current model `arm64-bounded-register-flags-v12` adds unshifted W/X ADDS and
SUBS register forms, including CMP/CMN aliases and ZR operands. Exact semantics
and fresh/reused evidence are in `docs/REGISTER_FLAGS.md` and
`docs/REGISTER_FLAGS_RESULTS.md` from repository root. Earlier sections retain
historical model meanings. Current app: `dist/AIRS.app`; prior v11:
`dist/flags-v11/AIRS.app`.

Current model `arm64-bounded-flags-v11` adds bounded W ADDS and X ADDS/SUBS
immediate flag producers, including CMN/CMP aliases. Exact semantics and fresh/
reused receipts are in `docs/FLAG_PRODUCERS.md` and
`docs/FLAG_PRODUCERS_RESULTS.md` from repository root. Earlier sections retain
historical model meanings. Current app: `dist/AIRS.app`; v10 is preserved at
`dist/conditions-v10/AIRS.app`.

Current model `arm64-bounded-conditions-v10` adds condition codes EQ through LE
(0–13) to bounded branches and W CSEL. Exact semantics and fresh/reused receipts,
including the completed v10 native overview/detail check after UI-control recovery,
are in `docs/CONDITION_CODES.md` and `docs/CONDITION_CODES_RESULTS.md` from repository
root. Earlier continuation sections retain historical model meanings.

Current model `arm64-bounded-conditional-v9` adds bounded GT/LE return teardown
transfers with recognized successors. Exact semantics and fresh/reused receipts
are in `docs/CONDITIONAL_TEARDOWNS.md` and
`docs/CONDITIONAL_TEARDOWNS_RESULTS.md` from repository root. Earlier continuation
sections retain historical model meanings.

Current model `arm64-bounded-suffixes-v8` adds bounded restore-prefix transfers
to shared return suffixes. Exact semantics and fresh/reused receipts are in
`docs/SHARED_SUFFIXES.md` and `docs/SHARED_SUFFIXES_RESULTS.md` from repository
root. Earlier continuation sections retain historical model meanings.

Current model `arm64-bounded-teardowns-v7` adds independently checked differing
contiguous return teardowns. Exact semantics and fresh/reused receipts are in
`docs/DIFFERING_TEARDOWNS.md` and `docs/DIFFERING_TEARDOWNS_RESULTS.md` from
repository root. Earlier continuation sections retain historical model meanings.

Current model `arm64-bounded-returns-v6` adds multiple RET terminals with identical
bounded teardowns. Exact semantics and fresh/reused evidence are in
`docs/MULTIPLE_RETURNS.md` and `docs/MULTIPLE_RETURNS_RESULTS.md` from repository
root. Earlier continuation sections retain their historical model meanings.

Current model `arm64-bounded-dwarf-cfg-v5` adds bounded FDE recovery at direct
calls through forward CFGs. The exact intersection and fresh/reused evidence
are recorded in `docs/DWARF_CFG.md` and `docs/DWARF_CFG_RESULTS.md` from repository
root. Earlier continuation sections below describe historical model subsets.

Current continuation: `arm64-bounded-calls-v4` adds bounded compact-frame direct
calls through forward CFGs. See `docs/CFG_CALLS.md` (from repository root) and
`docs/CFG_CALLS_RESULTS.md` for exact semantics, fresh evidence and reused receipts.
Older model sections below retain their historical scope.

## 1. What a result means

AIRS is a bounded static diagnostic model. It compares a supported
metadata rule with symbolic caller-recovery state derived from a supported
function shape. It does not prove arbitrary execution, runtime memory validity,
exception personality behavior or whole-binary correctness.

Each finding has three independent dimensions: coverage, verdict and scope.
Coverage reports metadata presence and, for CFI, bounded evaluation status. Verdict records the comparison outcome.
Scope states which observation class was checked. Never infer one dimension
from another, and never collapse unresolved into agreement.

### Verdict lattice used by the starter

| Condition | Result |
| --- | --- |
| Missing rule, unavailable boundary, unsupported instruction/format/model, uncertain recovered value, or budget exhaustion | Unresolved |
| Fully supported model, at least one known recovery discrepancy, and no unknown required recovery value | Supported inconsistency |
| Fully supported model, at least one justified observation, and all required recovery identities agree | Agreement within scope |

If a modeled observation has both a known discrepancy and an unknown required
recovery value, the starter reports unresolved. This is a deliberate conservative
precedence rule. Future versions may expose a local discrepancy alongside a
separate incomplete-analysis status, but must version and explain that change.

Input-table corruption is a separate parse error. A supported inconsistency
does not by itself establish which compiler, linker, assembly author or runtime
component is responsible.

## 2. Synchronous and asynchronous interpretation

Apple compact unwind is used for exception unwinding; its existence does not
promise valid recovery at every arbitrary stopped instruction. Prologue and
epilogue transitions can require different treatment in a sampling profiler or
debugger. The LLVM CFI-validation discussion and existing stack-unwinding work
make this distinction material to an auditor's claims. [R3, R5 in
REFERENCES.md](REFERENCES.md)

The starter therefore has two supported observation scopes:

* **`synchronous_call_sites`:** frame-mode or supported DWARF comparisons at listed modeled direct
  BL suspension states. BL writes its next PC into LR. The callee is summarized
  under the documented ABI assumptions before caller recovery is compared.
* **`modeled_leaf_body`:** frameless or supported DWARF leaf structural comparisons before identified
  body instructions, after supported setup and before supported teardown. This
  is explicitly not asynchronous unwind validation or proof that an exception
  will be raised at those instructions.

`checked_pcs` records the call instruction address for call observations and the
body instruction address for leaf observations. A runtime adapter must not
reinterpret these as raw sampled PCs or normalized return PCs without an explicit
mapping. No runtime slide is applied by the engine.

Frame-mode functions without a supported direct call are unresolved in v0.
Frameless functions containing a call are unresolved. A lone RET without a
distinct supported body state is unresolved. These limits are intentional, not
parser failures or evidence of bad code.

## 3. Identity and address spaces

| Name | Meaning | Representation |
| --- | --- | --- |
| Container file offset | Byte position in a thin/FAT input file | Integer; includes the selected slice offset where relevant |
| Slice-relative file offset | Byte position from the selected Mach-O header | Integer; used by load commands/sections internally |
| Preferred VM address | Unslid image virtual address | Internal integer; lowercase hexadecimal string on the wire |
| Image-relative offset | Preferred address minus `__TEXT.vmaddr` | Hexadecimal string on the wire |
| Runtime address | Preferred address plus a verified process slide | Outside the starter's input/output interpretation |

Use the `__TEXT` segment base for compact function offsets. A page-zero segment
must not become that base. UUID, architecture/subtype and selected-slice digest
identify the image; the full-container digest records the original container.
Equal filenames or equal numeric addresses across builds do not establish
identity. A UUID alone is not a replacement for an exact-byte match in handoff.

All ranges are half open: `[start, end)`. The end does not belong to the range.
The sentinel supplies the final compact range endpoint. A finding ID includes
schema/model identity, selected-slice digest, architecture and function range.
It is stable for the same bytes, not a cross-build source-function identifier.

## 4. Function boundaries and rule joins

The parser reads function starts independently from unwind entries. Preferred
provenance is `LC_FUNCTION_STARTS`. Names may come from symbols, but aliases do
not create duplicate functions and interior labels must not split authoritative
function-start ranges. Symbol-only fallback is displayed as weaker provenance.

Executable sections with embedded data or relocations are visibly qualified.
The starter's semantic checker accepts only exact `lc_function_starts`
provenance. A range inferred from compact metadata alone cannot prove a complete
function and does not receive a semantic finding.

For a known start, the next supported start in the same executable section or
that section's end bounds the candidate function. This is still a model of the
available layout. Full decoding, a recognized return, and allowed trailing NOP
padding are additional requirements; start metadata alone does not prove that
every byte in the candidate range is semantically reachable code.

A compact rule can cover more than one function. That is accepted. A function
spanning multiple compact rules requires PC-sensitive selection and is unresolved
in v0. Never assign the first rule to every PC and then report an apparent
discrepancy caused by that shortcut.

## 5. Symbolic state and ABI assumptions

The model begins with symbolic identities for entry SP and registers x0–x30.
It can represent a known constant, an original register identity with a constant
displacement, an entry-SP-relative address, or an explicit unknown. Stack storage
contains only values written by supported instructions to known allocated slots.

The required caller state is entry SP and original x19–x30 identities. Original
x30 means the function's caller-return identity, not an assertion that x30 is an
ordinary callee-saved register. A direct BL changes LR; later restoration must be
modeled explicitly. Symbols can have equal concrete values on some executions,
but different symbolic identities do not establish restoration for arbitrary
allowed entry states.

A direct callee is summarized as ABI-conforming: it preserves SP and x19–x29,
and does not modify the caller's unescaped allocated stack storage. Volatile
registers become unknown. After recording the BL suspension state, resuming from
the callee makes LR unknown until restored. Callee code is not analyzed, and a
BL into the current function's own range is not summarized this way.

Passing a derived stack address to an unmodeled call could allow caller storage
to change, so such escapes are unresolved. The normal FP frame-chain assumption
is stated separately; it is not permission to assume arbitrary unknown memory
cannot alias saved slots.

The decoder accepts only explicitly implemented forms. Unsupported instructions
are errors in the model, not implicit no-ops. Word-size changes, indirect calls,
PAC instructions, SIMD accesses, unfamiliar hints and general branches require
new semantics before they can contribute to a supported result. See
[DECODER_SCOPE.md](DECODER_SCOPE.md) for exact forms.

## 6. Recovery rules checked in v0

For ordinary ARM64 frame mode, the compact rule restores caller SP from FP+16,
caller FP from the saved word at FP, and caller LR from FP+8. Selected integer
pairs are recovered in the order defined by the format/implementation. The lower
numbered register is at the higher address: the first selected pair begins with
its lower register at FP−8 and its higher register at FP−16. Subsequent selected
pairs continue downward. [R1, R2](REFERENCES.md)

The model compares all required preserved identities. If a metadata pair is
omitted but those registers still contain their original values at the checked
state, omission alone is not a discrepancy. If the needed value changed and the
rule cannot recover its original identity, a fully known supported comparison
can report an inconsistency. If the saved location was never modeled, report an
unknown, not a guessed value.

For the supported frameless leaf subset, there are no saved-pair flags. The
encoded stack field gives stack size in units of 16 bytes; the comparison checks
that body SP plus that size recovers entry SP and that required register
identities remain available. [R1](REFERENCES.md)

Authenticated LR frame mode `0x05`, ordinary ARM64e/PAC behavior, SIMD saved
pairs and frameless saved-pair semantics remain unresolved. Preserve mode `0x05`
as its own metadata mode. It must not be decoded as ordinary `0x04` frame mode.

## 7. Complete-function requirements

A supported result requires all of the following:

1. Accepted ordinary ARM64 image and independent code-only function provenance.
2. One metadata rule covering the complete candidate function range.
3. Supported nonzero mode/encoding fields, with no unimplemented save semantics.
4. A nonempty aligned function within configured limits.
5. Complete decoding using the explicit whitelist.
6. A recognized RET x30; only NOP padding may follow it.
7. A supported setup/body/teardown shape with no unmodeled SP/FP transition in
   the body and at least one justified observation.
8. A complete modeled return restoring entry SP and original x19–x30.
9. No unknown value in any required recovery comparison.

These conditions establish the scope of a static comparison. They are not a
formal proof of actual control-flow reachability, runtime stack validity,
exception correctness or every possible interruption point.

## 8. Limits and uncertainty

Defaults are defined in `types.Limits`: 512 MiB input, 4,096 load commands,
4,096 sections, 50,000 functions, 200,000 unwind entries, 16,384 instructions
per function and 1,000,000 candidate instructions per audit. An additional cap
allows 256 observations per function, 32 retained evidence entries per function
and 8,192 evidence entries per report. The parser has
additional bounded FAT, symbol and decoded-name ceilings documented in code.
Native and imported audit reports are bounded to 64 MiB. Generated JSON is also
capped at 64 MiB before output commit; an oversized serialization produces a
clear error and no partial file. Effective limits are recorded in
`analysis_config.limits`. Baseline comparison identifies differing or missing
configurations as an interpretation note.

Observation exhaustion makes the function unresolved. Evidence-display
truncation does not stop recovery comparison: all collected values are checked,
any unknown still overrides mismatches, and a supported inconsistency retains a
concrete discrepancy. The report states when retained evidence is a sample.

A global analysis budget does not remove functions from the report. It produces
unresolved results for those that cannot be analyzed. Parser limits fail with
a stable input-error code before unsafe iteration. Limits may be configurable
in a later preview, but changing them must not change the meaning of a verdict.

Historical `arm64-linear-v1` preserves DWARF references without evaluating
FDEs. `arm64-linear-dwarf-v2` adds only the subset in [DWARF_CFI.md](DWARF_CFI.md):
exact FDE/function joins, bounded rows and supported recovery at the existing
observation scopes. Merely finding `__eh_frame` or an in-range offset still
establishes neither evaluated CFI nor an asynchronous promise. Other CFI remains
unresolved. Evaluated metadata coverage is separate from supported verdicts.

## 9. Report and comparison invariants

Summary counts must equal actual findings. Supported findings need checked PCs,
present metadata and compatible scope. Known-model imports additionally require
the exact architecture, boundary and encoding relationships that the analyzer
supports. Unknown future model strings are preserved; comparisons with the
current model are ambiguous rather than silently equivalent.

For exact bytes, numeric offsets identify the same function range. Equivalent
hexadecimal formatting must not create added/removed rows. Across builds,
unique eligible symbol names are review candidates only. Generic entry/section
labels and generated address-shaped labels provide no cross-build symbol evidence
(see GENERATED_SYMBOL_MATCHING.md). Unnamed and duplicate-name
functions need future identity work; no nearest-address heuristic is used.

Saved-report comparisons can explicitly pair cross-build findings through the
API/CLI (MANUAL_FUNCTION_PAIRS.md). Pairs must be one-to-one and refer to IDs in
the selected reports. They record user review selection, not proven function
identity. Exact-image offsets remain authoritative; model/configuration mismatch
remains ambiguous. Pairing does not change source findings or analysis scope.

Every handoff preserves the evidence's source model and address space. The
destination must verify exact selected-image identity before applying the range.
Imported-report validation is not a signature or a claim that the imported
analysis was actually run.

## 10. Changing the model

When adding a supported instruction or rule family, document its consumed state,
produced state, alias behavior, unknown propagation and observation scope. Add
reviewed owned examples and a meaningful boundary test. Changes that alter the
meaning of supported results require a new analysis-model version and explicit
comparison behavior. Keep schema versioning separate from analysis semantics.


## 11. Source annotations are independent evidence labels

Optional source_annotations v1 binds a companion dSYM to the original report's
container/selected-slice identity and maps existing function-entry preferred PCs.
It cannot change code identity, function boundaries, checked scope, denominator,
recovery evidence or verdicts. Missing/ambiguous source stays explicit; matching
a dSYM does not evaluate CFI. Available local source contents are not verified
against the build. No source label establishes cross-build function identity.
See [SOURCE_ANNOTATIONS.md](SOURCE_ANNOTATIONS.md) for the bounded format and
[C10_RESULTS.md](C10_RESULTS.md) for actual evidence.


## 12. Bounded v3 leaf control flow

`arm64-bounded-cfg-v3` retains the v2 linear/CFI rules and adds only the
instruction/path subset in [BOUNDED_CFG.md](BOUNDED_CFG.md). Both unknown
conditional successors are retained with separate states at reconvergence.
Agreement requires every conservative body path-state to recover caller
identities and every terminal state to restore them. A supported inconsistency
needs a known-reachable concrete mismatch; a possible-only bad path is unresolved.
Required unknowns and resource exhaustion still override discrepancies.

The new subset is forward-only compact-frameless leaf code, with one shared
setup/teardown shape and exact ordinary ARM64 subtype. W writes zero-extend
and cannot preserve full-X identity by assumption; partial stack writes
invalidate overlapping saved words. Calls, loops, indirect edges and DWARF CFG
remain unresolved. Scope stays modeled_leaf_body; no async/all-PC claim follows.
Historical model versions remain separately interpreted.


## 13. Optional exact-body review evidence

Explicit API/CLI opt-in can add bounded exact-byte fingerprints to existing
supported functions; see FUNCTION_BODY_FINGERPRINTS.md. This evidence preserves
encoded immediates and is not relocation-insensitive or function-identity proof.
It cannot affect findings, checked PCs, analysis budgets or comparison signatures.
Imported annotations receive structural validation, not byte verification. The
native app keeps this option off; automatic matching is not part of this producer.


## 14. Optional exact-body candidate selection

Saved-report API/CLI comparison can opt into unique remaining exact-body review
candidates (EXACT_BODY_CANDIDATES.md). Established manual/symbol matches and exact
image offsets retain precedence; ambiguous symbol groups and duplicate body keys
are not guessed. Imported digests are structurally admitted but unauthenticated.
Model/configuration differences remain ambiguous and body equality cannot override
changed finding signatures. This comparison phase does not change unwind findings.


## 15. Native fingerprint preservation

Native FunctionInfo can retain optional exact-byte body fingerprints through its
typed codec (NATIVE_BODY_FINGERPRINT_CODEC.md). Missing evidence remains absent;
null, extra fields and contradictory context reject. Imported digests are not
rehashed or authenticated. Native production/matching defaults and analysis
semantics remain unchanged; numeric normalization is explicitly qualified.


## 16. Native comparison-context facts

Native typed comparison records preserve optional configuration/candidate status
and bounded one-to-one manual-pair metadata (NATIVE_COMPARISON_CONTEXT.md).
Absence remains unavailable, explicit false/empty values retain meaning, and
malformed selections reject. Import does not bind IDs to source reports,
authenticate evidence, recompute matches or change row classifications. Native
production/matching defaults and analysis semantics remain unchanged.


## 17. Explicit native manual-endpoint binding

An opt-in Data API can bind recorded manual endpoints and row verdict/scope facts
to two admitted audit reports (MANUAL_PAIR_SOURCE_BINDING.md). Declared image/model
flags must agree, and pair rows must correspond one-to-one. This is not digest
authentication, configuration-identity verification, change-signature computation
or validation of other match bases. It supplies no automatic native activation
or full comparison-readiness claim.


## 18. Explicit native manual-pair compatibility

The optional compatibility helper extends endpoint binding with original saved
configuration comparison (MANUAL_PAIR_COMPATIBILITY.md). Reported change status,
when present, must match source configurations; differing configurations or models
require ambiguous manual rows. Two legacy omissions compare equal without
inventing defaults. This does not authenticate evidence, recompute change
signatures, qualify nonmanual rows or activate native workflows.


## 19. Explicit native manual-row change evidence

The opt-in manual change validator extends source and compatibility prerequisites
with the host's selected finding signature (MANUAL_PAIR_CHANGES.md). Compatible
manual rows require the recomputed changed/unchanged label; incompatible rows
remain ambiguous. Relative addresses preserve sign and exact free-form strings
retain wire distinctions. Names and explanatory prose are not change evidence.
This does not authenticate selected reports, validate nonmanual rows or summaries,
activate matching, establish function identity, or change engine model semantics.


## 20. Explicit comparison row accounting

The opt-in row accounting validator (COMPARISON_ROW_ACCOUNTING.md) checks category
shapes, per-side selected endpoint uniqueness and exact summary totals over bounded
recorded rows. A selected ambiguous pair counts as matched; unselected ambiguity
groups do not invent matches. Typed endpoint facts follow selected IDs. This is
neither source completeness nor identity/matching/signature verification. Existing
decoding, native workflow activation and engine model semantics remain unchanged.


## 21. Explicit selected-source facts across comparison rows

The opt-in selected-source validator (COMPARISON_SOURCE_FACTS.md) composes row
accounting and existing source-context/manual-endpoint checks, then binds every
selected baseline/current ID and its verdict/scope to the corresponding admitted
source finding. Unknown IDs fail rather than disappearing. Omitted ambiguity
endpoints do not imply source completeness. Matching semantics, configuration
identity, nonmanual signatures, binary authenticity and GUI activation remain
separate; engine model semantics are unchanged.


## 22. Explicit observation labels for all selected pairs

The opt-in matched-label validator (MATCHED_CHANGE_LABELS.md) composes selected
source facts and manual verification, then applies the shared host observation
signature to other two-endpoint rows. Comparable pairs require changed/unchanged;
model/configuration differences require ambiguous. Unselected groups and one-sided
rows do not invent pairs. This does not verify matching-basis semantics, source
completeness, source-function identity, original binary bytes or GUI behavior.
Default decoding, matching and engine model semantics remain unchanged.


## 23. Explicit exact-image offset authority

The opt-in exact-image validator (EXACT_IMAGE_OFFSET_ROWS.md) composes prior source,
accounting and observation checks. Cross-image rows cannot claim exact-image
matching; same-image rows require canonical numeric offset groups. Only singleton
side groups select IDs, multiplicity stays ambiguous, and unique one-sided groups
remain added/removed. This checks declared groups against admitted source reports,
not original bytes, source completeness or cross-image matching semantics. Default
matching/decoding, GUI activation and engine model semantics remain unchanged.


## 24. Explicit unique-symbol pair evidence

The opt-in unique-symbol pair validator (UNIQUE_SYMBOL_PAIRS.md) composes existing
source/accounting/observation and exact-image rules. Selected cross-image symbol
pairs require exact usable wire names, canonical symbol keys and singleton source
groups after validated manual pins. Missing or generated names and hidden duplicates
cannot provide symbol evidence. One-sided groups, body/other bases, source
completeness, source-function identity and binary authenticity remain separate.
Default matching/decoding, GUI activation and engine model semantics are unchanged.


## 25. Explicit exact-body pair evidence

The opt-in native body-pair validator (BODY_CANDIDATE_PAIRS.md) composes prior
source, accounting, observation, offset and symbol checks. Selected body rows
require explicit opt-in, matching architecture/subtype, equal admitted fingerprint
tuples and canonical keys. Post-manual source buckets exclude established symbol
pairs but retain ambiguous-group blockers; only unique standalone endpoints select.
Imported digests remain unauthenticated, omitted candidates remain unverified,
and matching defaults, engine semantics and native GUI workflows are unchanged.


## 26. Explicit duplicate-symbol group evidence

The opt-in duplicate-symbol validator (DUPLICATE_SYMBOL_GROUPS.md) composes prior
source, accounting, observation, offset, symbol-pair and body-pair checks. Declared
symbol keys must name existing usable source groups after validated manual pins.
Source-name multiplicity requires ambiguous classification and selects only actual
singleton sides; body matching cannot consume these blocked groups. Unselected
ambiguity without multiplicity rejects, while incompatible selected unique pairs
retain their prior ambiguous labels. Singleton one-sided matching outcomes,
completeness, binary authenticity and GUI activation remain separate.


## 27. Explicit singleton symbol outcomes

The opt-in one-sided symbol validator (ONE_SIDED_SYMBOL_ROWS.md) composes prior
validation and binds declared singleton added/removed rows to exact source groups
after manual pins and eligible body selection. Omitted body rows cannot restore
consumed endpoints. Missing body status remains unavailable: affected outcomes
refuse, while outcomes independent of that status can be checked. Established
symbol pairs cannot hide one endpoint. Completeness, unmatched/future matching,
binary authenticity, GUI activation and engine semantics remain separate.


## 28. Explicit unmatched-row evidence

The opt-in unmatched-row validator (UNMATCHED_ROWS.md) composes prior comparison
validation. Declared unmatched rows require one exact side-specific source ID,
a canonical key, the corresponding added/removed label and a host-unusable name.
Validated manual pins and eligible body pairs consume endpoints independently of
imported row omissions. Missing body status remains unavailable when consumption
could affect the row. Native source-name admission, omitted groups, future bases,
completeness, binary authenticity, GUI activation and engine semantics are unchanged.


## 29. Explicit recorded matching-policy consistency

The opt-in matching-policy validator (MATCHING_POLICY.md) composes declared-row
checks and requires a known host basis vocabulary. Canonical policy metadata follows
validated nonempty manual selections and explicit true body opt-in; missing status
remains unavailable, not an invented false value. Body opt-in stays recorded when
same-image or subtype authority prevents selection. Unknown policy/basis strings
reject only at this explicit boundary. Complete producer reconstruction, remaining
field semantics, source identity, binary authenticity and GUI activation are not
established; generic decoding and matching defaults remain unchanged.


## 30. Explicit canonical manual-pair keys

The opt-in manual-key validator (MANUAL_PAIR_KEYS.md) composes recorded-policy
and prior declared-row checks. Manual review keys require the exact ordered
baseline/current selected IDs under the host's canonical namespace. Pin membership,
source facts, compatibility and observation labels remain prerequisites. Keys do
not establish identity, authenticity or complete output. Earlier APIs retain their
existing key scope; generic decoding, producer defaults and GUI behavior are unchanged.


## 31. Explicit selected function-name facts

The opt-in selected-name validator (SELECTED_FUNCTION_NAMES.md) composes canonical
manual keys and prior declared-row checks. A selected current source name takes
precedence over a selected baseline name; exact UTF-8 labels preserve empty and
generated names without normalization or display fallbacks. Rows with neither
endpoint selected retain an unverified representative label. This checks saved
presentation facts, not authenticated symbols, source-function identity or complete
producer output. Earlier APIs, decoding, matching and GUI behavior are unchanged.


## 32. Explicit unselected symbol-group names

The opt-in unselected-symbol name validator (UNSELECTED_SYMBOL_NAMES.md) composes
selected-name and prior declared-row proofs. Symbol rows with no selected endpoint
must retain the exact UTF-8 source-group name established by canonical key and
post-pin membership validation. Unselected exact-offset representative labels
remain outside this boundary. This is presentation consistency, not identity,
binary authentication or complete-output reconstruction; earlier APIs and native
workflows retain their scope.


## 33. Explicit unselected exact-offset representative names

The opt-in offset-name validator (UNSELECTED_OFFSET_NAMES.md) composes earlier
symbol-group and selected-name checks. Exact-image rows without selected endpoints
must use the first current group member's name in recorded finding order, falling
back to the first baseline member only when the current group is absent. Names
are exact UTF-8 presentation facts, including empty/generated names. Numeric
offsets, source membership and multiplicity remain prerequisites from composition.
Recorded source order is not authenticated; complete output, identity and native
activation remain separate. Earlier APIs and defaults retain their scope.


## 34. Explicit canonical declared-row ordering

The opt-in row-order validator (CANONICAL_ROW_ORDER.md) composes all prior
declared-row/name checks and requires strictly ascending complete row keys in
raw UTF-8 lexical order. This matches the producer's Unicode scalar sorting,
preserving spelling and avoiding numeric, localized or display-name sorting.
It does not reorder input. Empty, singleton and ordered partial comparisons
remain possible; completeness, authenticity, identity and native activation
remain separate. Earlier APIs, decoding and matching defaults retain their scope.


## 35. Explicit same-image saved-report group coverage

The opt-in same-image coverage validator (SAME_IMAGE_ROW_COVERAGE.md) composes
all prior declared-row/name/order proofs and explicitly requires same-image
authority. Declared canonical keys must cover the union of numeric offset groups
in both admitted saved reports. Duplicate findings and alternate source spellings
contribute one group each. Empty same-image snapshots may have empty coverage;
cross-image use refuses even when empty. Coverage does not establish original
binary-function completeness, authenticity, identity or exact remaining producer
fields. Earlier APIs retain partial-output scope; defaults and GUI behavior are
unchanged.


## 36. Explicit-body-disabled cross-image saved-report coverage

The opt-in body-disabled coverage validator (BODY_DISABLED_ROW_COVERAGE.md)
composes declared-row/name/order proofs and requires cross-image sources with
explicitly false body status. Expected raw UTF-8 keys include validated manual
pairs and remaining usable-name symbol or side-specific unmatched groups after
pins. Duplicate raw names collapse; generated labels retain separate side keys.
Missing/enabled body status and same-image use refuse, even for empty sources.
This adds saved-report omission detection, not original-binary completeness,
authenticity, identity, exact remaining fields or native activation. Earlier APIs
retain partial-output scope; defaults are unchanged.


## 37. Explicit-body-enabled cross-image saved-report coverage

The opt-in body-enabled coverage validator (BODY_ENABLED_ROW_COVERAGE.md)
composes declared-row/name/order proofs and requires cross-image sources with
explicit true body status. The existing body projection, guarded by equal source
architecture and exact subtype, supplies all required body keys after manual pins.
Consumed endpoints are excluded per side before rebuilding remaining symbol and
unmatched groups. Established symbols and duplicate blockers retain precedence.
Model/configuration incompatibility retains ambiguous labels without suppressing
coverage. Missing/false status or same-image use refuses, even when empty. Coverage
is limited to saved-report groups, not original bytes, function identity, complete
remaining producer fields or GUI activation. Earlier APIs/defaults retain scope.


## 38. Explicit covered saved-report comparison decoding

The opt-in covered decoder (COVERED_COMPARISON_DECODE.md) bounds comparison bytes
before existing generic admission. It selects same-image coverage while preserving
body metadata, or the explicit false/true cross-image coverage branch. Missing
cross-image body status refuses. Composed source-context checks reject forged
dispatch flags. The decoded modeled fields are returned unchanged; generic decode,
matching defaults and native workflows retain their scope. Success establishes
saved-report group coverage plus composed field checks, not authenticated bytes,
function identity, every producer field or GUI acceptance.


## 39. Explicit producer body-option metadata

New comparisons always serialize the validated body-candidate Boolean, including
false for the existing default (EXPLICIT_BODY_STATUS.md). This additive wire field
records caller configuration independently of fingerprint presence or phase output.
Matching, policy suffixes, limitations, precedence and schema/model versions retain
their meaning. Historical absent metadata remains unavailable; no decoder default
or source report mutation is introduced. Native caller activation and runtime
acceptance remain separate.


## 40. Opt-in covered batch comparison acceptance

The explicit covered batch policy (COVERED_BATCH_COMPARISON.md) delegates to the
bounded covered decoder at the existing acceptance point, before budget decrement
or payload/model storage. Validation failures remain unavailable with no accepted
comparison fields; later pairs continue under existing progress/cancellation
rules. The policy is immutable per runner. The exact no-argument initializer and
GUI callers retain legacy acceptance; source pairing, retained reports and export
contracts are unchanged. This is source/unit integration, not GUI activation,
authenticated bytes, function identity or native workflow acceptance.


## 41. Structural comparison schema vocabulary

The baseline-diff v1 schema and generator (COMPARISON_SCHEMA_ALIGNMENT.md) admit
the four supported policies and five bases. Optional body status is Boolean;
optional manual pairs are bounded exact two-ID objects with strict endpoint text
shape. Historical absence remains valid. This structural contract does not prove
bijection, source membership, metadata consistency, coverage, authenticity or
identity; explicit native validators retain those scopes. Runtime dependencies,
matching defaults, other schema contracts and GUI behavior are unchanged.


## 42. Owned producer/native coverage integration controls

The producer coverage controls (PRODUCER_COVERAGE_BRIDGE.md) join existing Python
comparison generation to the covered native decoder through strict batch acceptance.
Exact serialized strings and independent expected counts/bases/status preserve the
protocol boundary. Synthetic digests are placeholders; mutations isolate missing
groups and foreign source endpoints while retaining structural validity. These
controls do not change matching or GUI activation, authenticate bytes, establish
analysis truth or prove packaged-engine transport and original-binary completeness.


## 43. Owned producer/native observation-label parity

The separate observation controls (PRODUCER_OBSERVATION_PARITY.md) qualify the
producer/native signature boundary for reason sorting with duplicate preservation,
relative addresses, checked-PC ordering, raw evidence text and presentation-only
messages. Expected changed/unchanged labels are independently prescribed; flipped
labels with consistent accounting must refuse strict acceptance. Existing matching
and observation implementations remain unchanged. Synthetic saved-report parity
does not prove machine-code equivalence, analysis truth, regression severity,
authenticity, packaged transport or GUI acceptance.

## Swift synchronous error-flow recovery

`swift-sync-error-edges-v1` is a separate structural model, exposed through
`swift-error-flow`. Its exact declaration subset, bounded alias window, explicit
scan/detail completeness and excluded claims are specified in SWIFT_ERROR_FLOW.md.
Its candidates do not enter unwind agreement or inconsistency accounting.

The opt-in `swift-sync-error-region-v1` supplement admits only bounded structural
error-fallthrough intervals ending at a forward success entry. Opaque calls and
raw targets are retained without return, reachability, exclusive-entry or
postdominator proof. Region refusal preserves the underlying edge result.
SWIFT_ERROR_FLOW.md specifies the 16-word and already-scanned-prefix limits.

The additional opt-in `swift-region-direct-entries-v1` validator checks only
caller-local direct B/BL/conditional/register-test branch targets into each
candidate half-open interval. Unknown words or partial caller coverage prevent
an absence result; observed conflicts remain visible with exact counts and
bounded details. It never establishes exclusive entry, indirect/external-entry
absence, reachability, a postdominator or handler semantics. Default edge/region
reports and unwind verdicts remain unchanged. See SWIFT_ERROR_FLOW.md.

The opt-in `swift-structural-presentation-v1` consumer assigns blocked, unresolved
or eligible_structural_only presentation status to retained producer candidates.
Only complete, consistent caller-local direct validation can enable a labeled
bounded structural display plan. Source reconstruction is always disabled;
indirect/external entry, reachability, call return and handler meaning remain
unproven. The consumer does not admit arbitrary saved reports. Default analysis
and unwind results remain unchanged; see SWIFT_ERROR_FLOW.md.

The bounded Swift text renderer consumes current in-process producer facts only.
Eligible structural plans, blocked/unresolved evidence, raw post-call/region words,
opaque targets, full source counts and proof limits remain distinct. Renderer
row/byte caps never widen eligibility or source claims. Rendering failure returns
no partial text; default JSON and unwind semantics remain unchanged. See
SWIFT_ERROR_FLOW.md for explicit caps and qualification scope.

Edge model `swift-sync-error-edges-v2` adds only exact ordinary synchronous
untyped Int-to-Void throwing free-function declarations (`yySiKF`), retaining the
previous Int-to-Int mapping. Historical v1 results keep their identity. Region,
entry, presentation and unwind semantics remain unchanged; the owned later-
epilogue jump remains a region refusal. See SWIFT_ERROR_FLOW.md.

Region/entry/presentation v2 adds bounded shared restore/return tails for a terminal
error-arm B past a separate straight-line success arm. The error interval excludes
both success and tail words. Eight-word success/tail caps, narrow SP-restore shape,
complete scanned-prefix evidence and exact expected-edge exemptions are required.
Other caller-local direct entries conflict, unknown coverage withholds eligibility,
and blocked/unresolved text retains all bounded interval evidence. Edge identity,
default output and unwind semantics are unchanged. Historical region-v1 refusal
of the owned later-epilogue example is superseded only within this new component
scope. Restored state, reachability and reconstructed Swift remain unproven. See
SWIFT_ERROR_FLOW.md for qualification and limits.

Region v3 additionally admits a final SP post-indexed LDP of distinct callee-saved
registers with a positive 16-byte-aligned increment up to 496, immediately followed
by exact RET x30. Both words must fit the existing tail budget and scan prefix.
It reuses the existing decoder and direct-entry guards; other component identities,
default output and proof limitations remain unchanged. The tail's restored-state
claim remains false. See SWIFT_ERROR_FLOW.md for focused qualification.

Region v4 additionally admits exact raw ADD SP,X29,#0 only as the start of an
adjacent ordered SP-post-index LDP X29,X30 / RET X30 sequence. Existing positive
aligned increment and caller/tail bounds apply to all three words. Other reset
aliases/forms or intervening words decline. It reuses the existing decoder,
entry guards and presentation contracts without proving FP provenance, stack
balance, restored state or unwind correctness. See SWIFT_ERROR_FLOW.md.
