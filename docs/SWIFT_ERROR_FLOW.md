# Swift synchronous throwing-call recovery

The independent `swift-sync-error-edges-v3` model identifies bounded structural
success/error return edges in ordinary ARM64 Mach-O images. This is the first
Swift decompilation slice: it does not reconstruct complete `do/catch` source.
The existing unwind audit and its model identity remain unchanged.

```
python3 -I -B airs_cli.py swift-error-flow Example.dylib --output flow.json
```

## Admission and evidence

A direct BL must target an exact LC_FUNCTION_STARTS entry with one public,
file-backed executable-section symbol. Section-end labels, aliases, private,
resolver and alternate entries do not supply declarations. The complete supported
mangling is two length-prefixed ASCII identifiers followed by `yS2iKF`,
`yySiKF` or `yyKF`: ordinary synchronous, untyped throwing free functions with
Int-to-Int, Int-to-Void or parameterless Void signatures, respectively. Other declarations remain declined, including
async, typed throws, generic functions, methods and thunks. Symbol declarations
are structural evidence, not authenticated runtime targets.

An eight-word post-call window tracks x21 and live 64-bit MOV copies, respecting
overwrites and the zero register. NOP is allowed. A forward 64-bit CBZ/CBNZ of a
live error-result alias must have two distinct aligned successors inside the same
caller. Zero means success; nonzero means error. Unknown instructions, other
branches/calls, narrow tests and clobbered aliases stop recovery. Existing data,
relocation and symbol-only boundary exclusions remain effective.

The report retains raw instruction words, preferred VM addresses, relative call
and callee offsets, selected-slice identity, declaration evidence and declined
reasons. Default limits reuse decode inventory bounds: 8 MiB input, 1,024
functions, 4,096 words per function, 16,384 total words, 32 call details per
function and 256 total. Omitted details and incomplete scans are explicit.
Exit status is 0 for complete scanning/detail retention, 1 for partial coverage,
and 2 for input errors; status 0 does not mean all calls were recovered.

## Reuse and limits

The implementation reuses AIRS Mach-O admission, ARM64 instruction decoding,
input resolution and protected atomic exports. The x21 convention follows the
same ordinary-throws distinction used by MacScope. No MacScope source is changed
and no runtime dependency or external demangler is introduced. Primary references:

- https://github.com/swiftlang/swift/blob/main/docs/ABI/CallingConventionSummary.rst
- https://github.com/swiftlang/swift/blob/main/docs/ABIStabilityManifesto.md#error-register
- https://github.com/swiftlang/swift/blob/main/docs/ABI/Mangling.rst

Candidates may occur in unreachable instruction words. This pass proves neither
reachability nor dominance, catch types, handler meaning, source equivalence,
unwind correctness, async behavior or compatibility beyond the admitted subset.
Selected code is parsed as data and never executed.

## Qualification

Twenty-two focused methods cover positive recovery, polarity, aliases and kills,
width, intervening instructions, successor bounds, complete declaration grammar,
symbol attribution, entry exclusions, scan budgets and protected CLI exports.
Accepted cases were reused; only the three CLI methods were repeated after their
temporary-directory setup changed. Independent semantic review found and prompted
a section-end attribution regression test and fix, then found no remaining
correctness issue in the reviewed boundaries.

An owned optimized Swift dylib compiled from
`fixtures/swift-error-flow/OwnedThrows.swift` was independently disassembled and
then analyzed once. Of 14 direct-call candidates in 173 scanned words, one was
recovered and 13 declined; no call details were omitted. The call at 0x934 targets
`AIRSErrorFlow.parse` at 0x890. The x21 test at 0x938 has success successor 0x948
and error successor 0x93c, matching the independent disassembly. This is owned
compiler-output qualification, not a corpus, native app or GUI acceptance claim.
Generated images and detailed execution receipts remain outside tracked source.

Next: qualify additional explicit Swift signatures and recover bounded handler
regions before presenting source-like `do/catch` output. Every extension needs a
positive owned example and an independently reviewed refusal boundary.

## Opt-in bounded error-region intervals

```
python3 -I -B airs_cli.py swift-error-flow Example.dylib --include-error-regions --output flow.json
```

The optional `swift-sync-error-region-v1` supplement describes local structural
intervals for recovered calls. Default reports retain the original edge-only
shape and model. A region decline does not invalidate or promote an edge result.
The report adds `error_region_model_version`, per-call `error_region`, and
recovered/declined region counts in the summary. These counts cover retained
recovered edges only; omitted calls and declined edge candidates remain visible
in the original scan/detail counters. Existing exit status describes scan/detail
completeness, not successful region recovery.

The first admitted layout requires the error successor to be the instruction
immediately after the test, before a forward success successor in the same
caller. The success entry is the proposed exclusive-end join boundary. At most
16 words may lie in the interval, and every word must be in the already scanned
caller prefix. Supported words are NOP, 64-bit MOV/MOVZ/MOVN, opaque direct BL,
and a final unconditional B exactly to the proposed join. Other instructions,
reverse layouts, early or differently targeted branches and truncated scan
prefixes decline with explicit reasons. No additional instruction family is
added to the existing decoder or unwind model.

Each admitted word retains its PC, raw encoding and kind. BL retains its target
and `opaque_call` label without claiming a callee identity or behavior. Both
`call_return_proven` and `join_reachability_proven` are false. There is no proof
that calls return, that the join executes, that the interval has no other incoming
edges, or that it is exclusively entered on error. The join is not a proven
postdominator. This is neither catch-type recovery nor source-level handler
reconstruction.

Eleven new focused methods passed, covering the owned shape, default preservation,
CLI opt-in, opaque calls, permitted final join branch, rejected control flow,
reverse layouts, the exact 16-word bound and scan-prefix refusal. Independent
semantic review found no blocking correctness issue. Accepted edge and CLI
qualification was reused rather than replayed.

The same accepted owned compiler image and independent disassembly supplied the
new region qualification. Only the new helper analyzed the accepted caller bytes;
compilation, disassembly, image hashing/admission and edge analysis were not
repeated. It recorded MOV at 0x93c, an opaque BL at 0x940 to 0xaec, and MOVN at
0x944, with proposed join 0x948. Disassembly labels the call as an error-release
stub, but the report deliberately assigns no runtime meaning to that target.
This is source-engine qualification; native presentation, installation and
release acceptance remain separate.

## Opt-in caller-local direct-entry validation

```
python3 -I -B airs_cli.py swift-error-flow Example.dylib --include-error-regions --validate-region-entries --output flow.json
```

`--validate-region-entries` requires `--include-error-regions`. It adds the
`swift-region-direct-entries-v1` model marker and an `incoming_validation`
supplement to retained structural region candidates. Declined regions have no
validation claim; default edge and region reports remain unchanged.

The validator classifies the already bounded caller prefix once per caller using
the existing decoder. It checks direct B, BL, B.cond, CBZ/CBNZ and TBZ/TBNZ targets.
A source outside the half-open candidate interval targeting its start or interior
is an unexpected direct entry. Sources inside the interval are not side entries;
the proposed join is outside the interval. The expected adjacent error-test
fallthrough remains allowed by the region layout. The pass does not execute
code or assume a direct branch is reachable.

Results have three statuses:

- `unexpected_direct_entries`: at least one conflicting direct edge is observed,
  even when scan coverage is partial or other words are unclassified.
- `unresolved`: no conflict is observed, but caller coverage is incomplete or
  at least one word cannot be classified, including unsupported indirect control
  transfers or invalid direct-target arithmetic.
- `no_unexpected_direct_entries`: the full caller is scanned, every word is
  classified, and no conflicting direct target is observed within this scope.

The supplement retains source/target PCs, raw encodings and branch kinds, caller
scan completeness and word counts. Conflict and unclassified-word details are
capped separately at 16 entries while retaining exact totals and detail
completeness fields. Classification shares the existing function/word budgets;
region inspection does not extend the admitted caller prefix. Existing CLI exit
status still reports scan/detail completeness rather than semantic approval.

`exclusive_entry_proven` is always false. This check covers caller-local direct
edges only. It does not exclude indirect or external entries, prove reachability,
prove that calls return, establish a postdominator or recover catch semantics.
An observed side entry supplements the candidate; it does not erase the original
structural region or alter the unwind result. Consumers must inspect validation
status before using an interval as a structured presentation candidate.

Seventeen new focused methods passed across positive, boundary and review controls.
They cover all supported direct families, start/interior/join boundaries,
internal opaque calls, unknown/indirect words, invalid target arithmetic, partial
scans, conflict precedence, evidence caps, default preservation and API/CLI option
requirements. Independent semantic review found no blocking correctness issue.
Accepted edge/region qualification was reused.

Only the new classifier and entry validator analyzed the accepted owned caller
bytes at 0x920 through 0x958. All 14 words were classified, with zero unexpected
caller-local direct entries to the accepted interval [0x93c, 0x948). The output
retains `exclusive_entry_proven: false`. Compiler, disassembly, identity, edge and
region results were reused without replay. This is source-engine qualification,
not native UI, installation, distribution or release acceptance.

## Structured-presentation eligibility

```
python3 -I -B airs_cli.py swift-error-flow Example.dylib --include-error-regions --validate-region-entries --include-structured-presentation --output flow.json
```

The opt-in `swift-structural-presentation-v1` supplement consumes the in-process
producer results and creates a bounded display plan. Both region recovery and
incoming-entry validation options are required. This helper is not an admission
boundary for arbitrary saved reports. Default reports remain unchanged.

Each retained call receives a `presentation` result:

- `blocked`: the edge or region was not recovered, or unexpected direct entries
  were observed. Existing instruction and validation evidence remains available.
- `unresolved`: validation is missing, incomplete, unclassified or inconsistent,
  or presentation addresses/interval words cannot be bound to the producer facts.
- `eligible_structural_only`: the recovered interval has complete caller-local
  direct validation with zero conflicting or unclassified words, and its condition,
  register, addresses and instruction PCs form a consistent bounded display plan.

Eligible plans retain a structural-candidate label, condition PC and tested
register, nonzero error condition, error interval with copied raw instruction
records, and success entry PC. Instructions stay in producer order, with at most
16 words. Opaque calls retain their raw targets and opaque label. Warnings travel
with every presentation result. No display plan is emitted for blocked or
unresolved cases.

The helper requires literal completeness/proof flags and zero integer validation
counts; missing or contradictory fields cannot silently enable presentation.
Summary counts partition all retained calls across the three statuses. They do
not cover omitted calls; original scan/detail completeness and omission counters
remain authoritative. CLI exit status is unchanged and does not grant semantic
approval. This is a JSON display plan, not a native renderer or UI activation.

`source_reconstruction_allowed` is always false. Eligibility permits a labeled
structural diagram only, never a source-like do/catch claim. Caller-local checks
do not exclude indirect/external entry, prove reachable branches, establish call
return or exclusive entry, or reconstruct handler meaning.

Seventeen new focused methods passed across positive, boundary and review
controls. They cover conflicts, unresolved states, missing/inconsistent metadata,
strict integer/boolean fields, interval/word/register bindings, default shape,
retained-call accounting, API/CLI prerequisites, opaque warnings and instruction
copy isolation. Independent semantic review found no blocking correctness issue.
Accepted edge, region and incoming-validation results were reused.

The new eligibility helper alone consumed the accepted owned example's edge,
region and incoming-validation records. It produced an eligible structural plan
for test PC 0x938, x21 nonzero error interval [0x93c, 0x948), and success entry
0x948. It preserved the opaque call at 0x940 and disabled source reconstruction.
No binary read/hash/admission, compiler, disassembly, edge, region or incoming
analysis was repeated for this qualification. Native UI, installation and release
acceptance remain separate.

## Bounded terminal renderer

```
python3 -I -B airs_cli.py swift-error-flow Example.dylib --include-error-regions --validate-region-entries --include-structured-presentation --format text --output review.txt
```

`--format text` renders current in-process producer output. All three structural
options are required; default output remains JSON. The renderer does not admit
saved reports or perform new binary analysis, and does not activate native UI.
It reuses the existing bounded text builder and ASCII JSON escaping.

Eligible calls show the structural candidate label, condition, raw error-interval
instructions and success entry. Blocked/unresolved calls show their reason and
region evidence with the structured plan withheld. All displayed calls retain
call identity/encoding, relative call offset, recorded test/success/error PCs,
post-call MOV/NOP/test words, incoming validation and candidate limitations.
Direct targets remain opaque evidence. The header always disables source
reconstruction and preserves indirect/external-entry and runtime-proof limits.

Rendering caps are 32 call rows, eight post-call words, 16 region words, 16 entries
for each incoming-evidence list, 16 issue/reason rows and 16 limitation rows per
list. Every capped list has an explicit renderer-omission count. Full producer
summary counters, original scan/detail completeness, validation totals and source
detail-completeness flags remain visible. Renderer omissions are additional to
producer omissions and do not change source denominators or eligibility.

Text is capped at 1 MiB, including escaping and the final newline. Invalid byte
limits or oversized output refuse before any partial text is returned; CLI
atomic export preserves an existing destination on rendering failure. Every
variable value, including keys, names and warning text, is ASCII JSON escaped to
avoid terminal control sequences. The original report is not mutated.

Thirteen focused methods passed in composed receipts. They cover eligible,
blocked and unresolved displays, raw post-call evidence, row caps, source-count
preservation, terminal controls/Unicode, exact byte fit and one-byte overflow,
invalid/global limits, model prerequisites, nonmutation, default JSON, protected
input export and destination preservation on size refusal. Independent review
identified the initial omitted post-call window; a new red/green regression
control and bounded evidence output corrected it. Final review found no remaining
blocking issue. Accepted producer qualification was reused.

A renderer-only fixture assembled from the accepted owned-example records kept
all 14 original call rows and source counts: one eligible plan and 13 expected
blocked outcomes for declined edges. The rendered text retained test PC 0x938,
raw test word 0xb4000095 and opaque target 0xaec. This checks rendering of accepted
facts and expected blocked-display records, not a replay of the full producer.
No binary read/hash/admission, compiler, disassembly, edge, region, incoming or
eligibility analysis was repeated for this fixture. Native UI, installation and
release acceptance remain separate.

## Int-to-Void declaration extension (edge model v2)

The v2 edge model adds the exact `yySiKF` suffix for ordinary synchronous,
untyped throwing free functions taking one unlabeled Swift.Int and returning
Swift.Void. This admits common validation functions such as
`validate(_ value: Int) throws`. The previous `yS2iKF` mapping remains unchanged;
v1 reports retain their historical meaning and identity. Renderer model admission
follows the current producer identity rather than silently relabeling old reports.
Region, incoming and presentation component models are unchanged.

The exact full-symbol matcher reuses the existing bounded identifier parser,
Swift declaration facts and x21 convention. No demangler dependency is added.
Nonthrowing, async, typed-throws, methods, generic declarations, argument-count
changes, thunk/specialization suffixes and ambiguous symbols still decline. The
primary grammar reference remains the Swift project's Mangling.rst linked above.
A development-only Swift demangler independently confirmed the owned spelling as
`AIRSValidate.validate(Swift.Int) throws -> ()`.

Ten new focused methods passed, covering the declaration, prior scalar mapping,
full-suffix refusals, identifier/context boundaries, symbol ambiguity, error-test
width, JSON/text integration and the owned handler-layout refusal. Independent
semantic review found no blocking correctness issue. Prior accepted unchanged
edge, region, entry and renderer checks were reused.

One optimized owned Swift dylib was compiled from
`fixtures/swift-error-flow/OwnedVoidThrows.swift`, independently disassembled and
analyzed once. The v2 pass scanned 174 words and retained all 14 direct calls:
one recovered throwing-call candidate and 13 declines. The call at 0x930 targets
`validate` at 0x890; the x21 test at 0x934 has success successor 0x948 and error
successor 0x938, matching the disassembly. The image was inspected as data and
never executed.

The actual error block ends with a B at 0x944 targeting epilogue 0x94c, rather
than success entry 0x948. Existing region rules deliberately decline that layout
as `error_region_control_flow_unmodeled`; presentation remains blocked. This
qualification establishes new declaration/call-edge coverage, not full handler
recovery. The different-success-entry/epilogue layout is a concrete next bounded
region extension requiring separate positive and refusal controls. Native app,
GUI, installation and release qualification remain separate.

## Bounded shared restore/return tail (region, entry and presentation v2)

`swift-sync-error-region-v2` retains the earlier forward-success interval and adds
one shared-tail layout. The final error-arm instruction must be a direct B past
the success entry to a later aligned join in the same admitted, scanned function.
The error interval still ends at the success entry; `join_pc` records the distinct
shared-tail start. No error instruction is attributed to the success arm or tail.

The error arm remains capped at 16 words. The success arm and shared tail are each
capped at eight words and must fit the existing caller scan prefix. The success
arm admits only straight-line NOP/MOV/MOVZ/MOVN. The tail admits NOP, nonnegative
SP-offset LDP of distinct registers x19–x30, positive 16-byte-aligned SP-to-SP ADD
up to 4096, and exact RET x30. Calls, branches, unknown words, unsupported memory
bases/writeback, missing returns and over-budget intervals decline. These are
instruction-shape restrictions, not frame-state or stack-memory validation.

`swift-region-direct-entries-v2` additionally checks direct targets into the
success arm and shared tail, including calls originating in the error arm. Only
the recorded XCBZ test to the exact success entry and terminal error B to the
exact shared join are exempt. Other explicit entries, including extra entries at
the join, conflict. Incomplete caller scans or unclassified words withhold the
absence result. Indirect/external entries and runtime reachability remain unproven.

`swift-structural-presentation-v2` binds and copies the separate intervals into
its structural plan. The bounded text renderer preserves success/tail bounds and
raw words even when the plan is blocked or unresolved, with row omission counts.
Source reconstruction remains disabled; restored return state, call return,
exclusive entry, postdominance and handler meaning are not proven. The edge model
remains v2, default edge-only output and unwind verdicts are unchanged, and older
component reports retain their historical identities.

Fourteen new focused methods passed in composed runs, including red/green recovery
and withheld-evidence cases, side entries, expected-edge binding, tail restrictions,
exact limits, truncated prefixes, presentation tampering and copied evidence.
Sixty affected region/entry/presentation/text and selected Void-call controls
passed once. Unchanged declaration/admission suites were reused. Independent
semantic review found no remaining blocking issue after the withheld-evidence
renderer correction.

The already captured owned Void-handler example was qualified only at the changed
region, entry and presentation stages, using its accepted call-edge facts and
retained disassembly words. It now yields error interval 0x938–0x948, success arm
0x948–0x94c and shared tail 0x94c–0x95c, eligible for structural presentation.
No sealed binary read/hash/admission, compiler or disassembly pass was repeated.
This is not a new end-to-end real-binary CLI or native-app qualification. No
packaging, publication, installation or production-store changes were performed.

## Final post-indexed SP restore (region v3)

`swift-sync-error-region-v3` adds one common return-tail shape using the existing
ARM64 decoder: a final SP-based post-indexed LDP immediately followed by exact
RET x30. Destination registers must be distinct x19–x30. The positive stack
increment must be divisible by 16 and at most 496, the aligned signed scaled
encoding bound. Offset restores may precede it under the existing restrictions.

Both instructions must fit the already scanned prefix and eight-word tail budget.
Zero/negative/misaligned increments, duplicate or unsupported registers, other
bases, pre-indexed forms, nonstandard returns and any instruction between the
pop and RET decline. Direct-entry guards still cover the new tail, and
restore_state_proven remains false. No stack balance, restored LR or unwind proof
is inferred from this syntactic shape. Edge v2, incoming v2 and presentation v2
retain their identities, endpoints and limitations; default output is unchanged.

Eleven new focused methods passed in composed runs, including the first red/green
case, encoding limits, malformed controls, return/budget/prefix restrictions,
side-entry blocking, offset-restore composition and one synthetic CLI text case.
Three changed-boundary region/CLI and legacy-tail controls passed. Accepted
shared-epilogue results were reused; no unchanged full suite or real binary
admission, hash, compiler or disassembly pass was repeated. Independent semantic
review found no blocking issue. This is synthetic source/CLI qualification, not
real-binary prevalence, native-app or release qualification.

## Exact frame-pointer-reset tail (region v4)

`swift-sync-error-region-v4` adds the exact three-word tail shape ADD SP, X29, #0
(raw 0x910003bf, the MOV SP, X29 alias), followed immediately by SP post-indexed
LDP X29, X30 with a positive 16-byte-aligned increment up to 496, then exact
RET X30. The ordered restore pair is required. Existing offset restores may
precede this sequence within the shared-tail budget.

All three words must fit the eight-word tail budget, admitted function and
already scanned prefix. Shifted-zero aliases, WSP/SUB/nonzero-immediate forms,
other reset sources, swapped/wrong restore pairs, other bases/addressing modes,
intervening instructions and unsupported returns decline. Caller-local direct
side entries retain their existing blocked/unresolved behavior. Edge v2,
incoming v2 and presentation v2 contracts are unchanged; restored-state and
source-reconstruction proof flags remain false. No FP provenance, stack balance,
restored LR, unwind validity or runtime reachability is established by this shape.

Twelve new focused methods passed in composed runs, including the first red/green
case, encoding/pair restrictions, increment boundaries, immediate adjacency,
exact budget/prefix boundaries, side entries, offset-restore composition and one
synthetic CLI text check. Four changed model/CLI controls passed. Accepted
shared/post-indexed results were reused without repeating full suites or
real-binary admission, hashing, compilation or disassembly. Independent semantic
review found no blocking issue. This is synthetic source/CLI qualification only;
no native app, release, installation or production-store changes were performed.

## Success fallthrough with a forward error arm (region v5)

`swift-sync-error-region-v5` adds the other ordinary error-test polarity: a
recovered XCBNZ test whose success entry is the next word and whose error target
lies later in the same caller. The success arm must contain at most eight words,
with only NOP/MOV/MOVZ/MOVN before one final direct B immediately before the error
entry. That B must target a later nonoverlapping shared join. The error arm then
falls through to the join in at most 16 words, allowing the existing straight-line
word subset and opaque BL calls, but no branch or RET. The existing eight-word
restore/return-tail recognizer is reused without adding tail opcodes.

The new layout is recorded as success_fallthrough_error_forward. Its error
interval is error-entry to join; its separate success interval is test+4 to error
entry; its shared tail starts at join. All words must fit the already scanned
caller prefix and function. Unsupported layouts, overlapping/backward/outside
joins, missing terminal success branches, exceeded budgets and unmodeled words
remain declined. Recovered candidates still make no runtime reachability or
handler-meaning claim.

`swift-region-direct-entries-v3` exempts only the recorded XCBNZ test to the exact
error entry and the success arm's terminal B to the exact shared join. The older
XCBZ error-fallthrough layout retains its distinct exemptions. Other explicit
cross-arm and tail entries conflict, including opaque error-arm calls targeting
success/tail words. Incomplete or unclassified caller coverage withholds an
absence result; indirect and external entries remain outside this proof.

`swift-structural-presentation-v3` binds the new geometry and requires complete
success evidence as well as existing entry validation before emitting a structural
plan. Text retains separate success/error/tail bounds and words for eligible,
blocked and unresolved candidates. Declined success-arm scans retain inspected
words, including unclassified raw words, and instructions_complete describes only
word-evidence coverage, not semantic validity. Invalid branch targets are omitted
as VM addresses and receive an explicit reason. Source reconstruction and all
restored-state, exclusive-entry, call-return and reachability proof claims remain
false. Edge identity v2 and default edge-only output are unchanged.

Seventeen new methods passed in composed focused runs, including the first
red/green layout case, minimal and exact/over-limit arms, branch/entry binding,
side entries, scan-prefix boundaries, presentation tampering, retained declined
success evidence, invalid VM targets and one synthetic CLI text case. Ninety-five
affected region/entry/presentation/renderer and prior-tail controls passed once
after extracting the shared-tail recognizer. Their accepted scopes were reused
for the subsequent forward-only diagnostic correction. Independent semantic
review found no remaining blocking issue. No sealed binary admission, hashing,
compilation, disassembly, native app, release or installation check was repeated.
This is synthetic source/CLI qualification, not real-binary or installed-app proof.

## Parameterless throwing Void declarations (edge v3)

`swift-sync-error-edges-v3` adds only exact `yyKF` after the existing bounded ASCII
module/free-name identifiers. It records parameters as a fresh empty list and
result as Swift.Void. Swift's Mangling.rst specifies empty-list `y` for Void result
and no parameters, plus `K` for untyped throws. The development demangler confirms
`AIRSNoArgs.validate() throws -> ()`. Neither demangling nor a new dependency is
introduced at runtime. Existing Int-to-Int and Int-to-Void declaration facts remain
unchanged; historical edge-v2 reports retain their identity.

Async, typed-throws, methods, generic contexts, thunks, nonthrowing functions and
other parameterless result types remain refused. Exact entry/symbol admission,
alias ambiguity, bounded x21 tracking and narrow-register refusal are unchanged.
Region v5, incoming v3, presentation v3 and unwind model identities retain their
existing scopes. Symbols remain structural declaration evidence, not runtime
identity, target authentication or reconstructed Swift source.

Twelve new focused methods passed in composed runs, including the first red/green
case, prior signature facts, near-match/context refusals, parameter-list isolation,
alias ambiguity, width/copy tracking, forward-handler integration, CLI JSON and
direct text rendering. Thirty affected declaration/admission/renderer/model
controls passed; unchanged region and corpus checks were reused. Independent
semantic review found no blocking issue.

One new optimized owned ARM64 dylib was compiled from
fixtures/swift-error-flow/OwnedNoArgThrows.swift, independently disassembled and
analyzed once. The first scan covered 187 words and retained all 15 direct calls:
one recovered candidate and 14 explicit declines. The call at preferred VM 0x9dc
targets parameterless validate at 0x914. Its x21 test at 0x9e0 has error successor
0x9e4 and success successor 0x9f4; the error arm jumps at 0x9f0 to shared join
0x9f8, whose tail ends at 0xa08. These facts agree with retained disassembly and
produce an eligible structural presentation. The image was inspected as data,
never loaded or executed. This establishes one owned compiler case, not broad
compiler/layout coverage, native UI, clean-host or release qualification. No
sealed earlier binary was reread/rehashed/recompiled, and no installed app or
production settings/stores were modified.

## Parameterless throwing Int declarations (edge v4)

Edge v4 adds only exact `SiyKF` free-function declarations: no parameters and
Swift.Int result, ordinary synchronous untyped throws. Prior declaration facts
remain unchanged. Other result types, methods, async, typed throws, generics and
thunks remain refused. Region v5, incoming v3 and presentation v3 are unchanged;
source reconstruction and runtime identity proof remain disabled.

Five new focused tests and 38 affected declaration/renderer/component controls
passed in composed runs. One initial test incorrectly compared a declaration
with a call record containing additional attribution fields; only that changed
test was rerun after correcting its comparison. Existing owned-image results
are reused for their original signatures; this extension has synthetic source
and renderer qualification, not a new compiled-image or installed-app claim.
