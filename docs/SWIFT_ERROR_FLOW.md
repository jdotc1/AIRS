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

## Bounded success-result evidence

When structured presentation is requested, `swift-success-result-v1` records
whether x0 is preserved along the recorded success path of an exact Swift.Int
throwing call. Swift's ARM64 calling-convention summary assigns the first integer
result to x0. The new result requires eligible caller-local structural evidence
and the existing bounded shared return tail. It reuses admitted caller bytes,
with at most eight post-call words, eight success-arm words and eight tail words.
Post-call NOP and MOV to other registers, success NOP and MOV/MOVZ/MOVN to other
registers, and the exact terminal success branch to the shared join are admitted.
The existing tail whitelist restores x19..x30, adjusts SP and ends in RET x30.
Any x0 write, call, unknown operation, unsupported return, incomplete entry check
or missing shared tail withholds the candidate. Even x0 self-copy is declined
by this initial conservative subset.

The candidate describes selected-path register preservation only. Runtime value,
path exclusivity, caller return type and source-reconstruction proof remain false.
No error-arm result is inferred. Default edge-only output and edge v4, region v5,
incoming v3 and presentation v3 identities are unchanged. JSON carries raw bounded
path evidence; text exposes the same scoped result with explicit omission counts.
The text renderer accepts prior reports lacking the optional result model, but
requires the current model when result evidence is present.

Twelve new focused methods passed in composed runs, including both arm layouts,
x0 clobbers, post-call writes, call/unknown/return refusals, partial scans, direct
side entries, unsupported declarations, default-output isolation and CLI JSON/text.
Exact 24-word coverage and each independent one-word overflow were checked;
text displays the success-result model identity. Independent semantic review
found no false-preserved-result blocker.
Forty-nine affected renderer, declaration, forward-arm and shared-tail controls
passed once. Existing owned-image results are reused only for their original
scopes; this increment has synthetic analysis/CLI qualification and no new native
app, compiled-image, installed-app or release qualification.

## Bounded result-copy recovery (success-result v2)

The v2 result model tracks exact 64-bit MOV copies of the call result across
the existing bounded post-call and success intervals. The initial live set is
{x0}; MOV from a live source adds its destination, and other MOV/MOVZ/MOVN
writes remove that destination. XZR is never a live result location. A saved
copy can survive an x0 overwrite, but a candidate requires x0 to be restored
before entering the unchanged shared tail. The tail may overwrite saved aliases,
so `result_registers_before_tail` explicitly describes the pre-tail state only.

A MOV into x0 from another live result register produces
`copied_register_candidate`; paths without such a move retain
`preserved_register_candidate`. An x0 self-copy is now admitted. W-register
copies, intervening calls, unsupported instructions, missing copies and
unrestored x0 withhold recovery. Bounds remain eight post-call, eight success
and eight tail words; old edge/region/incoming/presentation models are unchanged.
Runtime-value, exclusive-path, caller-return-type and source-reconstruction
proof flags remain false. Only selected-path register evidence is claimed.

Eight new focused methods and 25 affected success-result/renderer methods passed
in composed runs. They cover restoration after clobber, transitive aliases,
alias kills, constants, narrow/XZR refusals, missing restore, self-copy and both
arm layouts. This is synthetic source/text qualification; prior owned-image,
native and release results are reused only within their original scopes.

Independent semantic review found no blocking alias-tracking defect. Two changed
copy-kill controls additionally confirmed eligible presentation and the exact
result-layer refusal reason; only those changed methods were run again. The
narrow-copy control establishes end-to-end pipeline refusal, not direct modeling
of W-register copies.

## Success-entry return tails (success-result v3)

The v3 result model also admits an eligible error-fallthrough interval whose
success entry equals its recorded join and begins the existing bounded
restore/return whitelist. A direct RET x30 is the smallest accepted tail. No
separate success-arm interval or shared-epilogue record is required for this
layout; the result records `return_tail_layout: success_entry` and retains the
actual tail words. Existing shared layouts retain their distinct layout label.

This extension reuses the complete caller-local direct-edge scan. Every direct
edge into any tail word conflicts except the exact recorded XCBZ test to the
join and the terminal error-arm B to that join. An opaque error-arm BL into the
tail is not exempt. Conflicts retain full counts and at most 16 details with an
explicit completeness flag. Indirect and external entries remain unproven.

The new tail is at most eight words; post-call evidence remains at most eight
words and shared-layout paths retain the overall 24-word maximum. Unsupported
operations, x0 writes in the tail, nonstandard returns, missing RET, incomplete
caller classification and conflicting entries withhold recovery. Post-call
64-bit saved-copy restoration composes with the direct-return layout. Runtime
value, caller return type, exclusivity and source reconstruction remain unproven.
Edge, error-region, incoming and presentation identities are unchanged.

Thirteen new methods passed in composed runs, covering direct RET, restore tails,
exact/over-limit tails, tail entry/interior conflicts, opaque calls, conflict
detail caps, partial scans, result-copy composition and CLI JSON/text. Thirty-three
affected success-result, copy and renderer methods passed once. Qualification is
synthetic analysis and CLI output; no new owned-image, native or installed-app
claim is made. Prior accepted binary/release evidence retains its original scope.

Independent semantic review found no false-supported fallback issue. A diagnostic
finding was corrected so a withheld tail-entry result retains the inspected tail
words; one new focused conflict/text test passed after that change.

## Bounded success-path constants

`swift-success-constant-v1` independently records an exact 64-bit pattern assigned
on an admitted Int throwing call's selected success arm. It is separate from
call-result preservation: a success arm returning zero does not preserve the
call's integer result. The new result requires eligible structural presentation,
a recorded bounded success interval and the exact existing shared return tail.

No incoming register or error-arm constant is assumed. Existing decoded 64-bit
MOVZ and MOVN create complete patterns with their encoded shifts; MOV copies
a known pattern or reads XZR as zero. Writes to XZR are discarded. An unknown
MOV source removes knowledge of its destination. No partial MOVK assembly,
32-bit constant, arithmetic or extra instruction family is admitted. A known
pattern must reach x0 before the unchanged tail, whose whitelist cannot write
x0. Maximum evidence is eight success words plus eight tail words.

The result records fixed-width hex `constant_bits`, bit width 64 and
`depends_on_call_result: false`. It does not infer signed source syntax, the
caller's return type, execution, path exclusivity or reconstructed Swift. Those
proof flags remain false. Existing result v3, edge, region, incoming and
presentation models retain their identities. Default edge-only output is
unchanged; JSON and text expose the optional constant model and bounded words.

Twelve new methods and 46 affected result/copy/return-tail/renderer controls
passed in composed runs. Cases include shifted MOVZ/MOVN, transitive copies,
unknown-source kills, XZR, unsupported widths and updates, both arm layouts,
entry conflicts, partial scans, exact 16-word and overflow bounds, and CLI
JSON/text. One boundary fixture initially placed its opaque error call inside
the enlarged tail and correctly declined. Only that changed test was run again
after moving its call target outside the protected interval. Qualification is
synthetic source and CLI output, with no new owned-image or installed-app claim.

Independent semantic review found no blocking issue. Narrow/MOVK/call controls
establish conservative pipeline refusal rather than interpretation by the
constant helper; no instruction-family support is inferred from those controls.

## Bounded error-arm constants

`swift-error-constant-v1` separately records exact 64-bit patterns assigned on
an admitted Int throwing call's recorded error arm. It requires eligible
structural presentation, the bounded error interval and its exact validated
shared return tail. The existing constant walker is reused with an empty state;
success-constant v1 behavior and all previous model identities are unchanged.

The same 64-bit MOVZ/MOVN/MOV and XZR rules apply. Every opaque BL clears all
known constants, including saved-register entries; evidence explicitly marks
the invalidation. A complete assignment after the last call may establish
known x0 bits at the join. A value assigned before an opaque call, or copied
from unknown incoming state, cannot seed a candidate afterward. Neither the
success arm nor the call result supplies error constants.

Evidence is at most 16 error words plus eight return-tail words. The result
retains exact hexadecimal bits and candidate opaque-call counts, while call
return, handler meaning, runtime value, exclusive path, caller return type and
source reconstruction remain unproven. Even an eligible pattern does not prove
a Swift catch clause or that an opaque call returns. Unsupported instructions,
partial scans, conflicting entries and missing tails withhold recovery. Narrow
and MOVK controls establish pipeline refusal rather than interpretation of
those instruction families. Default edge-only output remains unchanged.

Thirteen new methods and 58 affected success-constant/result/copy/return-tail/
renderer controls passed in composed runs. They cover state invalidation before
and after calls, saved-register invalidation, copies/XZR/shifts, separate success
and error values, both arm layouts, exact 24-word and overflow bounds, entry
conflicts, partial scans, optional model binding and CLI JSON/text. This is
synthetic analysis and CLI qualification, not a new compiled-image, native app
or release qualification. Existing binary evidence retains its original scope.

Independent semantic review found no false-supported blocker and confirmed that
the shared walker preserves success-constant behavior. No source image was
executed or newly admitted as part of this synthetic qualification.

## Bound return-choice summaries

`swift-return-choice-v1` joins existing in-process outcome evidence into one
structural review item. Eligible presentation, an error literal and exactly one
success literal or call-result candidate are required. Both outcomes must bind
to the same call, their recorded branch entries, x0 and the same shared return
word. Literal evidence must retain exact 64-bit hexadecimal bits and its
independence from the call result. Incomplete, contradictory or inconsistent
outcomes leave the summary unresolved. This is not saved-report admission.

A choice records the existing error test, its register and nonzero error sense,
plus separate success and error descriptions. Copied call results remain
distinguished from direct preservation. `same_constant_bits` is a static bit
comparison only when both paths have literal candidates; it is null when the
success value is a call result. Null does not assert the outcomes differ.

The summary performs no new image admission or instruction scan and does not
widen any component's existing bounds or model identity. It adds no runtime,
path-exclusive, call-return, handler, caller-return-type or source-reconstruction
proof. CLI text labels it as structural outcomes with source disabled; retained
component rows provide the original bounded instruction evidence.

Twelve new methods and 38 affected constant/renderer controls passed in composed
runs. Coverage includes literal pairs, equal literal patterns, direct/copied call
results, incomplete and contradictory outcomes, call/entry/return bindings,
invalid bit widths and proof claims, both layouts, default-output isolation,
model binding and CLI JSON/text. Qualification is synthetic analysis and output;
existing owned-image, native and release evidence retains its original scope.

Independent review identified a presentation-binding consistency gap. The join
now also requires exact agreement with the eligible display plan condition,
success entry, error-interval start and source-disabled flag. A new focused
valid/tampered/missing-plan control passed after that correction, without
replaying prior accepted checks.

## Owned return-choice qualification and success-entry error literals

The optimized ARM64 input in fixtures/swift-error-flow/OwnedReturnChoice.swift
contains two ordinary throwing Int call sites. One handler forwards the call
result on success and assigns all-ones bits after an opaque error-arm call. The
other assigns zero on success and all-ones-minus-one bits on error. The image
was compiled, disassembled and admitted once, then inspected as data only.

The first complete scan covered 213 words and retained all 18 direct calls:
two recovered candidates and 16 explicit declines. Both recovered error regions
were structurally eligible. At call VM 0xa4c, the existing summary recovered
success zero versus error 0xfffffffffffffffe, ending at RET 0xa74. At call 0xa14,
it recovered x0 preservation through a success-entry return tail, but initially
withheld the combined summary because error-constant v1 required a separate
shared-epilogue record. This refusal exposed a bounded layout gap.

Error-constant v2 now permits that error-arm layout only when a known success
result already supplies a validated success-entry tail. It binds x0, call and
success PCs, join, return PC, exact captured tail words and false proof flags.
The candidate continues to invalidate all constants at opaque calls. Success
constant behavior is unchanged. Return-choice v2 admits the matching outcome
pair only with an explicit known success-result/success-entry-layout guard,
retaining all existing presentation and per-arm consistency checks.

A single changed-boundary replay used seven captured error/tail words from the
first report, compared them with retained disassembly and evaluated only the
changed error-constant and summary logic. It recovered call-result versus error
all-ones at call 0xa14, test 0xa18, success entry 0xa28 and RET 0xa34. No binary
was reopened or rehashed, no image was readmitted, and no compiler, disassembly
or caller-entry scan was repeated. The original complete-scan result remains
separate from this incremental captured-word qualification.

Eleven new synthetic methods and 50 affected error-constant/return-choice/
success-constant/renderer controls passed in composed runs. New cases cover
protected-tail entry conflicts, missing/mismatched word and address bindings,
opaque-call invalidation, copied results, partial scans, exact 24-word and
overflow bounds, model-bound CLI output and mixed/foreign outcome metadata.
Independent review found no binary-triggered false-supported issue and prompted
explicit fallback-source/layout and x0 guards, covered by two new focused tests.
No broader compiler coverage, runtime, reconstructed source, native UI or release
acceptance is claimed; previous evidence retains its original scope.

## Caller-assigned literals after throwing Void calls

Success-constant v2, error-constant v3 and return-choice v3 also admit explicit
caller-assigned literal outcomes after the existing ordinary throwing Void
declarations (`yyKF` and `yySiKF`). A caller can assign zero after validation
and all-ones bits on the error path without using any callee result. No new
declaration grammar or instruction family is introduced.

Only the constant helper's declaration context expands from Int to Int/Void.
Maps still start empty and require supported definitions on the selected arm;
opaque calls still clear them. Call-result preservation remains Int-only, and
a stale integer-result candidate attached to a Void callee is rejected. No
implicit value is inferred from x0 after a Void call. The no-shared-tail Void
case still withholds error recovery because its required validated integer-result
tail source is unavailable. All existing geometry, entry, evidence-bound and
runtime/source proof restrictions remain unchanged.

Eleven new methods and 61 affected constant/choice/return-layout/renderer controls
passed in composed runs. New cases cover both Void signatures, both arm layouts,
missing assignments, stale result types, unsupported signatures, alias ambiguity,
partial scans, entry conflicts and CLI JSON/text. Independent semantic review
found no blocking correctness issue.

A single changed-context replay used nine captured arm/tail words from the
previously accepted owned parameterless-validation example, checked against its
retained disassembly. At call VM 0x9dc, it recovered success zero versus error
all-ones, with shared RET 0xa04. No old binary was reopened or rehashed; no
compilation, disassembly, image admission or caller-entry scan was repeated.
This is incremental helper-context qualification over retained owned evidence,
not a new complete-image, runtime, native UI or release acceptance claim.

## Known-seeded 64-bit MOVK outcome literals

Region v6 adds only the existing decoder's X-width MOVK form to the bounded
success/error arm whitelists. The outcome constant walkers can now construct
full-width literal patterns from a complete known seed and partial replacements.
The existing CFG decoder is reused unchanged; no new core instruction admission
or unwind rule is introduced. Edge v4, incoming v3 and presentation v3 keep their
scopes. Result v4, success-constant v3, error-constant v4 and return-choice v4
record the expanded outcome semantics.

Following Arm's MOVK definition, each update clears and replaces the selected
16-bit lane while retaining the other bits. X shifts are 0, 16, 32 and 48. The
constant must already be completely known, whether seeded by MOVZ/MOVN or a
known MOV/XZR value. Unknown registers stay unknown even after four lane writes;
this subset does not track partial-known bits. Unknown overwrites and opaque
error calls still discard knowledge. XZR writes are ignored.

MOVK conservatively kills its destination's call-result alias, even when a
particular write might be a no-op. Other live aliases remain available. W MOVK
and MOVK inside the post-call error-test window remain refused. Return-tail
whitelists, arm/evidence budgets and all runtime/source proof flags are unchanged.

Thirteen new methods and 171 affected region/outcome/renderer/model controls
passed in composed runs. New cases cover four-lane assembly, MOVN seeds, repeated
lane replacement, unknown and overwritten seeds, saved-result invalidation,
other-register preservation, XZR, opaque calls, both arm geometries, exact bounds
and CLI JSON/text with raw update evidence. Independent semantic review found no
blocking correctness issue. This is synthetic source and CLI qualification; no
new compiled-image, native app or release acceptance is claimed. Existing owned
image evidence remains accepted only within its original instruction scope.

Instruction semantics reference: [Arm A64 MOVK](https://support.arm.com/documentation/ddi0596/2021-06/Base-Instructions/MOVK--Move-wide-with-keep-).

## Swift-local W move-wide literal seeds

The Swift structural analyzer now recognizes exact W MOVZ and MOVN words through
a local adapter. It reuses the existing X move-wide decoder's field extraction,
rejects reserved W shifts 32/48, and restores the original word and W kind in
its instruction record. The core CFG/linear decoder, Mach-O admission and unwind
engine remain unchanged. Only shifts zero and 16 are admitted for W seeds.

Literal state applies 32-bit inversion/masking, then retains the resulting
zero-extended x-register bits. Thus MOVN w0,#0 yields 0x00000000ffffffff, while
MOVN x0,#0 remains 0xffffffffffffffff. A W seed clears any prior upper bits.
Known W seeds may feed existing 64-bit copies and X MOVK updates. Any such W
write invalidates its destination's call-result alias; WZR writes are discarded.

Region v7 and incoming v4 identify the expanded arm/classifiable-word scope.
Result v5, success-constant v4, error-constant v5 and return-choice v5 record the
new width semantics. Error-edge and presentation identities remain unchanged.
No W MOVK, W-register copy, post-call-window or return-tail support is added.
Opaque calls, unknown overwrites, interval limits, entry checks and all runtime
and source proof restrictions retain their prior behavior.

Twelve new methods and 218 affected region/entry/presentation/outcome/renderer
controls passed in composed runs. Cases cover shifts, raw word provenance,
zero extension, upper-bit clearing, alias invalidation, WZR, opaque calls, both
arm geometries, bounds, excluded operations and CLI JSON/text. One synthetic
forward-layout displacement was corrected after it pointed at the branch rather
than the error entry; only that changed case and previously unrun methods were
then executed. Qualification is synthetic analysis and output, without a new
compiled-image, native GUI or release acceptance claim.

Instruction semantics reference: [Arm A64 instruction reference](https://documentation-service.arm.com/static/67e40f3398aa3c3b6eea6a85).

Independent semantic review found no blocking issue and confirmed local adapter
scope, original-word retention, zero extension and unchanged global decoding.

## Known-seeded W MOVK outcome updates

Region v8 admits the existing decoder's W MOVK form within bounded success/error
arms. Result v6, success-constant v5, error-constant v6 and return-choice v6
record the expanded outcome semantics. Incoming v4 is unchanged because the
existing decoder already classified W MOVK as non-control flow. The Swift seed
adapter, core decoder/admission, post-call windows and tail whitelists remain
unchanged. Reserved W shifts 32/48 remain rejected.

For a completely known prior value, MOVK replaces the selected 16-bit lane and
masks the result to 32 bits, clearing the upper X-register bits. This applies
even when the seed came from a 64-bit instruction. Unknown values remain unknown,
including after both W lanes are written; partial-known-bit tracking is outside
this subset. Unknown overwrites and opaque calls still invalidate state. WZR
writes are discarded and updated result aliases are conservatively removed.

Twelve new methods and 196 affected controls passed in composed runs. The new
cases cover seed assembly, upper-bit clearing, repeated lane replacement, unknown
and invalidated seeds, aliases, WZR, both layouts, opaque calls, reserved shifts,
bounds and CLI JSON/text. The affected run stopped at an older negative control
that rejected the newly admitted known-seeded form; that control was changed to
reserved W encodings. Its corrected run and previously unrun cases passed, while
165 earlier passes were reused. Independent semantic review found no blocking
correctness issue. Qualification is synthetic analysis/output; no compiled-image,
native GUI or release acceptance is added. Existing owned results retain scope.

Instruction semantics reference: [Arm A64 MOVK](https://support.arm.com/documentation/ddi0596/2021-06/Base-Instructions/MOVK--Move-wide-with-keep-).

## Canonical W-register outcome copies

Region v9 admits only the canonical W MOV register alias: ORR Wd,WZR,Wm with
unshifted LSL zero and no inversion. The Swift-local adapter reuses existing
logical-register field decoding and retains the original word. General ORR,
shifted/rotated forms and inverted-source forms are not admitted by this rule.
The global decoder/admission and existing entry-classification scope are unchanged.

A known source constant is truncated to 32 bits and zero-extended into the
destination X register. Unknown sources clear destination knowledge, including
a previously known constant. WZR reads establish zero and WZR writes are
discarded. Transitive and self copies follow the same width rule. A W copy never
propagates an unknown 64-bit call-result alias: its written destination loses
that alias, even for MOV w0,w0. Unmodified result locations remain available.

Result v7, success-constant v6, error-constant v7 and return-choice v7 record the
new outcome scope. Post-call error windows and return tails continue to refuse
W copies. Arm/evidence bounds, opaque-call invalidation, entry checks and all
runtime/source proof restrictions retain their prior behavior.

Twelve new methods and 208 affected controls passed in composed runs. Coverage
includes exact alias fields and near misses, W versus X bit patterns, copies and
self copies, unknown-source kills, result-alias refusal, WZR, opaque calls, both
arm geometries, limits and CLI JSON/text after an admitted Void call. This is
synthetic analysis/output qualification; no compiled-image, native GUI or release
acceptance is added. Prior owned evidence retains its original scope.

Instruction semantics reference: [Arm MOV register alias](https://documentation-service.arm.com/static/5f3fa899428f7a6b3328fd44).

Independent semantic review found no blocking issue and confirmed the exact
alias mask, source-field reuse, zero extension and conservative alias invalidation.

## Owned Swift word-outcome qualification

fixtures/swift-error-flow/OwnedWordOutcomes.swift supplies two independent
optimized ARM64 handlers after an admitted throwing Void validation call.
`handleWords` assigns 0x89abcdef on success and 0x12345678 on error.
`handleWidth` assigns 0xffffffff on success and -1 on error. The input was
compiled, disassembled, admitted and analyzed once as data; it was never loaded
or executed. No analyzer semantics or model identity changed in this increment.

The first scan covered 205 instruction words and retained all 17 direct calls:
two recovered candidates and 15 explicit declines. Both recorded error regions
were eligible for structural presentation and both outcome summaries recovered.
At call VM 0x9e4, W MOVZ/MOVK pairs establish success 0x0000000089abcdef and
error 0x0000000012345678, sharing RET 0xa14. At call 0xa2c, W MOVN on success
and X MOVN on error establish 0x00000000ffffffff versus 0xffffffffffffffff,
sharing RET 0xa54. Literal equality remains false and source/runtime proof
flags remain disabled. Opaque error calls retain their unproven return semantics.

Twenty-two selected test/arm/tail instruction records were compared with the
retained independent disassembly and with the relocated word tuples in
tests/test_swift_owned_word_outcomes.py. Six new synthetic regression methods
passed: both positive pairs, missing-seed refusal, width-bit sensitivity,
conflicting-entry refusal and CLI JSON/text. Relocated synthetic admission is
separate from the owned dylib's first admission; it is not another dylib scan.
The owned dylib was not reopened or rehashed for these comparisons, and
no compiler/disassembler/admission workflow was repeated.

This qualifies two compiler-produced W-seed/update/width cases, not a broad
compiler corpus, runtime behavior, native UI or release acceptance. No W MOV
register copies were emitted by this fixture; their compiler qualification
remains open and their accepted synthetic evidence retains its original scope.
Earlier analyzer/renderer and binary results were reused without unrelated
repeat checks.

Independent review found no blocking fixture or evidence issue. It confirmed
that the relocated windows match retained disassembly and that compiled W-copy
coverage must remain open. No source equivalence or runtime claim is added.

## Scalar SP-relative restore-tail candidates

Region v10 also admits the existing decoder's unsigned scaled 64-bit LDR form
inside bounded return tails. The destination must be x19..x30, the base must
be SP and the decoded byte offset must be an eight-byte multiple from zero to
4096. The offset ceiling is this structural subset's bound, not a statement
about actual frame size. Existing core decoding and image admission are reused.

Scalar loads may mix with existing pair loads and SP adjustments within the
eight-word tail limit, ending in exact RET x30. W loads, x0/volatile/xzr
destinations, FP-based loads, stores, indexed loads and larger offsets remain
refused. No new instruction is admitted in error/success arms or post-call
windows. Result v8, success-constant v7, error-constant v8 and return-choice v8
record the expanded tail scope; edge, entry and presentation identities retain
their prior meaning.

The new loads cannot write x0. Recorded result aliases describe the state
before the tail, not saved registers after the loads. `restore_state_proven`
remains false: stack contents, frame validity, restored LR, memory-access success
and runtime return are not established. All runtime/source proof restrictions,
scanned-prefix and direct-entry protections remain in force.

Twelve new methods and 226 affected controls passed in composed runs. New cases
cover register/offset boundaries, excluded modes, scalar/pair mixing, exact and
over-limit tails, missing/nonstandard returns, both arm geometries, success-entry
fallback, entry conflicts, partial scans, copied results and CLI raw words.
Independent semantic review found no blocking correctness issue. Qualification
is synthetic analysis and output; no new compiled-image, native GUI or release
acceptance is claimed. Previous owned results retain their original scope.

Instruction semantics reference: [Arm LDR immediate reference](https://documentation-service.arm.com/static/6245c734b059dc5ff9a8bdab).

## Terminal scalar post-index restore-tail candidates

Region v11 adds a narrow terminal SP post-index 64-bit LDR shape. The destination
must be x19..x30, the signed byte increment must be a positive multiple of 16
from 16 through 240, and the next word must be exact RET x30. The pair must fit
inside the existing eight-word tail and scanned prefix. Zero, negative, unaligned
and larger increments, W loads, other bases/destinations, stores, pre-indexed
loads and intervening words remain outside this subset.

A Swift-local exact encoding adapter reuses unsigned-load operand extraction
and the existing signed-immediate helper, retaining the original word and
marking the post-index form separately. Global CFG/linear decoding and execution
are unchanged. The tail evidence records `sp_writeback_bytes` explicitly rather
than silently treating the stack update as a no-op. It does not simulate stack
contents or establish frame validity, restored LR, successful memory access or
runtime return; restored-state and source/runtime proof flags remain false.

Incoming v5 records the expanded local classification of SP post-index loads
as non-control instructions. The tail guard imposes the stricter register and
increment subset above. Result v9, success-constant v8, error-constant v9 and
return-choice v9 reflect the expanded tail scope. Arm and post-call whitelists,
image admission and all direct-entry protections retain their prior scope.

Twelve new methods and 272 affected region/entry/presentation/outcome/renderer
controls passed in composed runs. New cases cover exact operand/sign fields,
register and increment boundaries, excluded forms, immediate-return adjacency,
mixed tails, exact/over-limit tails, both arm layouts, success-entry fallback,
conflicting entries, partial scans, raw word and writeback CLI evidence. This
is synthetic analysis/output qualification; no new compiled-image, native GUI
or release acceptance is claimed. Prior owned results retain original scope.

Instruction semantics reference: [Arm LDR immediate reference](https://documentation-service.arm.com/static/67e40f3398aa3c3b6eea6a85).

Independent semantic review found no blocking issue. The new instruction kind
is confined to nonexecuting Swift structural helpers and explicit writeback
metadata; generic core SP-effect/state simulation is not extended to this kind.

## Exact split FP/LR restore sequence

Region v12 adds one exact composition after the existing FP-to-SP reset:
MOV sp,x29; unsigned LDR x30,[sp,#8]; post-index LDR x29,[sp],#16; RET x30.
It recognizes the LR load from the upper eight-byte slot before the FP pop
from the lower slot. Swapped registers/order, other offsets or increments,
near-match resets and intervening instructions remain outside this rule.
The existing reset/pair-pop/return form retains its earlier scope.

The four-word composition must fit wholly within the eight-word tail and
scanned prefix. It uses already admitted scalar decoding and writeback
metadata; no decoder, entry-classifier, core execution, arm or post-call
whitelist is expanded. Result v10, success-constant v9, error-constant v10
and return-choice v10 identify the expanded tail scope. Entry and presentation
identities retain their prior meanings.

This shape cannot write x0. Actual frame location, memory contents, restored
FP/LR, memory-access success and runtime return remain unproven. The copied
word evidence retains the explicit 16-byte SP writeback, while
`restore_state_proven` and all runtime/source proof flags remain false.

Twelve new methods and 250 affected tail/outcome/renderer controls passed in
composed runs. New cases cover exact reset and scalar fields, order/adjacency,
all lookahead prefix cuts, exact/over-limit tail budgets, entries into each of
the four words, both arm layouts, success-entry fallback, old pair composition
and raw CLI evidence. Qualification is synthetic source/output only; no new
compiled-image, native GUI or release acceptance is claimed. Prior owned
results retain their original instruction/layout scopes.

Independent semantic review found no blocking issue and confirmed exact field
bindings, bounded lookahead and unchanged pair-pop handling. Actual frame
provenance and restored-state/runtime proofs remain open.

## Owned assembler-backed epilogue and W-copy qualification

OwnedEpilogueProvider.swift supplies an admitted throwing Void validation
function. OwnedEpilogueHandlers.s supplies two fixed owned assembly handlers
that call it. The provider was compiled, the handlers assembled, and the input
linked, disassembled, admitted and analyzed once. The dylib was never loaded
or executed. Its runtime ABI and CFI correctness are not qualified.

The first scan covered 232 instruction words and retained all 21 direct calls:
two recovered candidates and 19 explicit declines. At call VM 0xb84, a canonical
W copy feeds success bits 0x0000000000001234 versus error all-ones. Its tail
contains unsigned SP scalar loads and a 32-byte scalar post-load, ending at
RET 0xbb0. At call 0xbc8, success bits 0x0000000000005678 pair with error
0xfffffffffffffffe. A pair-load prefix leads into the exact FP reset, LR load
from SP+8, FP post-load by 16 and RET 0xbf4. Both structural choices recover,
with restored-state, source and runtime proof flags still disabled.

Twenty-two captured test/arm/tail records matched retained disassembly and
the relocated tuples in tests/test_swift_owned_epilogue_fixtures.py. Six new
regression methods passed: both outcome pairs, lost W-seed refusal, wrong
split-pop increment refusal, tail side-entry refusal and CLI JSON/text.
Synthetic-image admission of relocated tuples is separate from the dylib's
first admission; no binary was reopened or rehashed for these comparisons.
No build, disassembly or admission workflow was repeated.

This is assembler/linker-produced evidence for the encoded W copy and epilogue
shapes. It does not establish that the Swift frontend emitted those handlers.
Swift-compiler W-copy/tail coverage, runtime execution, CFI/ABI correctness,
clean-host behavior and native app/release acceptance remain open. Analyzer
semantics and models are unchanged; prior accepted checks retain their scope
and were reused without unrelated repeats.

Independent fixture review found no blocking issue and confirmed word-window
fidelity, outcome bits and the assembler-versus-Swift-frontend distinction.
No runtime, ABI or CFI attestation is added.

## Adjacent compare-zero return edges

The current edge model is `swift-sync-error-edges-v5`. In the existing eight-word
post-call window, exact unshifted `SUBS XZR,Xn,#0` (the 64-bit CMP alias) may test
a live x21 alias when immediately followed by B.EQ or B.NE. EQ targets success;
NE targets error. Both successors must remain distinct, forward and inside the
caller. Raw comparison/branch words, comparison PC, condition and tested register
are retained. W comparisons, nonzero/shifted immediates, unrelated registers,
intervening instructions and other conditions are refused.

This addition recovers selected-word edges only. For this form, error-region
recovery declines with `compare_branch_region_not_qualified`; incoming-entry,
structured presentation and outcome recovery remain withheld. In particular,
no flag-entry or general NZCV dataflow proof is claimed. Existing CBZ/CBNZ region
behavior retains its prior qualification. Compiler-produced CMP emission,
flag-entry qualification and native/release acceptance remain open.

Ten new focused methods and 94 affected edge/signature/tail/CLI/rendering methods
passed. Prior owned-image qualification is reused without recompilation,
disassembly, binary admission or hashing.

## Bounded compare-window flag-entry inspection

The current edge model is `swift-sync-error-edges-v6`. With error-region recovery
and entry validation enabled, retained recovered CMP-zero edges receive a
separate `flag_entry_validation` record under `swift-compare-flag-entries-v1`.
The existing bounded caller classification is reused once per caller. Its
protected interval starts immediately after the throwing call and ends after
the conditional branch, including alias copies, CMP and B.cond.

Every observed caller-local direct branch or call into that interval is a
conflict. No absence claim is made when the admitted caller prefix is partial
or contains unclassified words. An observed conflict takes precedence over
those gaps. Counts remain exact while entry and unknown-word details are each
capped at 16, with explicit completeness fields. Default edge recovery remains
opt-in-free; declined comparison sequences receive no flag-entry record.

The record distinguishes `unexpected_direct_entries`, `unresolved`, and
`no_unexpected_direct_entries`. The last status is only an absence of observed
caller-local direct entries. It does not prove NZCV state, dominance, reachability,
exclusive entry, or absence of indirect/external entries. Both
`flag_state_proven` and `exclusive_entry_proven` remain false. Text output binds
the dedicated model and retains conflict/unknown evidence independently of the
withheld handler plan.

Comparison-based handler regions and structured outcomes still decline with
`compare_branch_region_not_qualified`, regardless of flag-entry status. This
increment does not implement general flag-state dataflow or compiler-emission
qualification. Existing CBZ/CBNZ behavior retains its scope. Twenty new focused
methods and 121 affected methods passed; independent semantic review found no
blocking issue. Prior owned-image results were reused without repeating compiler,
disassembly, hashing, or binary-admission workflows.

## Bounded CMP/B.EQ error-fallthrough regions

The current edge model is `swift-sync-error-edges-v7` and the region model is
`swift-sync-error-region-v13`. A recovered CMP-zero/B.EQ edge can now feed the
existing bounded error-interval decoder when caller-local flag-entry inspection
is complete, fully classified and free of observed conflicts. Its record must
match this call's protected window and adjacent comparison. Error starts at the
branch fallthrough; success must be later. Missing, stale, partial, unknown or
conflicting flag-entry evidence declines region recovery.

The existing 16-word region bound and instruction subset apply. Raw words,
preferred VM bounds, opaque call targets, ordinary incoming-entry evidence and
false call-return/join-reachability proof flags remain explicit. A direct entry
into the error interval remains visible as an incoming conflict, independently
of the flag window. B.NE/forward-error layouts and shared epilogues remain
unqualified for CMP-based handlers. Other instruction forms remain conservative.

All CMP-based structured presentation and outcomes remain explicitly blocked,
even when this simple region is recovered. The candidate does not establish
catch types, handler meaning, NZCV state, dominance, exclusive entry, source
reconstruction or runtime behavior. Compiler-emission and native/release gates
remain open. Existing CBZ/CBNZ behavior retains its prior scope.

Twenty-one new methods passed across bounded runs, including geometry/window
binding, opaque intervals, refusals, limits, incoming conflicts, CLI JSON/text
and exact downstream refusal states. Two hundred eight affected methods passed.
Accepted pre-pause results were reused; only changed failed/strengthened and
new selections ran after resumption. No compiler, disassembly, binary admission,
provenance hashing or native workflow was repeated.

## CMP structural presentation eligibility

The current edge model is `swift-sync-error-edges-v8` and the presentation model
is `swift-structural-presentation-v4`. A qualified CMP-zero/B.EQ simple
error-fallthrough region may now receive an `eligible_structural_only` display
plan. Both flag-window inspection and ordinary handler-entry inspection must be
complete, fully classified and free of observed conflicts. Flag bounds must match
the same call/window; comparison and branch PCs must be adjacent. The raw CMP
must be the canonical 64-bit zero comparison of the recorded register, and the
raw B.EQ must target the recorded success entry. Shared and forward-error layouts
remain outside this presentation subset.

The condition retains `comparison_pc`, `test_pc`, `test_kind` and
`test_condition: eq`, alongside `error_when: nonzero`. EQ describes the encoded
branch to success; nonzero describes the logical error predicate. Raw words,
opaque calls, image identity, bounds and entry evidence remain visible in JSON
and terminal-safe text. Missing or inconsistent evidence remains blocked or
unresolved. This consumes current in-process producer evidence; it does not admit
arbitrary saved reports or establish flag state, reachability or exclusive entry.

Presentation eligibility does not enable CMP outcome recovery. Explicit guards
keep success-result, success-constant and error-constant records declined and
return choices unresolved, with `compare_outcome_recovery_not_qualified`.
Source reconstruction remains disabled. B.NE handlers, shared CMP tails,
compiler-emission qualification and native/runtime/release gates remain open.

Twelve new focused methods and 206 affected methods passed in composed bounded
runs. Two text assertions were corrected to reflect per-call structural plans
rather than the earlier blocked layout; accepted passing selections were retained.
Prior owned-image and compiler results were reused without repeating workflows.

## Bounded CMP outcome recovery

The current edge model is `swift-sync-error-edges-v9`, success-result model is
`swift-success-result-v11`, error-constant model is `swift-error-constant-v11`
and return-choice model is `swift-return-choice-v11`. Qualified CMP-zero/B.EQ
simple error-fallthrough plans may now reuse the bounded selected-path outcome
logic. No shared or forward-error CMP layout is added.

Success-result tracking reuses full-width MOV aliases and re-reads the admitted
caller words. It permits only the exact adjacent 64-bit zero comparison and EQ
branch to the recorded success entry; testing x0 cannot establish preserved
call-result evidence. The existing bounded restore/RET tail and caller-local
incoming checks remain required. The expected EQ branch is exempted only at its
recorded source and success target; other direct tail entries withhold recovery.

An error literal can pair with that validated success-entry return tail. Opaque
calls clear prior constant state; a literal must be established afterward.
Existing W zero-extension, move-wide/copy restrictions and bounds remain intact.
The structural choice binds the full CMP condition, including both PCs, to the
presentation and both outcomes. It distinguishes a preserved/copied call result
from literal bits. Runtime, caller return type, exclusive path, source and handler
meaning remain unproven; opaque calls are not guaranteed to return.

Success-path literal recovery remains explicitly withheld for CMP. Unknown or
conflicting entry evidence, unsupported tails, changed comparison/branch words,
missing error literals and inconsistent outcome bindings remain declined or
unresolved. B.NE, shared CMP tails, compiler-emission and native/release gates
remain open. Fifteen new and 215 affected methods passed in bounded composed
runs. One affected test expectation was corrected: replacing an error literal
with a branch does not produce constant evidence. Prior passed selections and
owned-image/compiler results were reused without repeated binary workflows.

## Bounded CMP success literals

The current edge model is `swift-sync-error-edges-v10`, success-constant model is
`swift-success-constant-v10`, error-constant model is `swift-error-constant-v12`
and return-choice model is `swift-return-choice-v12`. The existing eight-word
post-call window now admits X MOVZ/MOVN seeds before an adjacent CMP-zero branch.
Seed destinations invalidate error aliases; a surviving alias is still required.
A literal prefix cannot enable CBZ/CBNZ recovery. W seeds and MOVK prefixes remain
outside this subset.

Qualified simple CMP/B.EQ presentation can interpret the prefix using existing
constant transfer, starting with no known values. X MOV copies, XZR and NOP keep
their established semantics; unknown-source copies invalidate knowledge. Only the
exact comparison and EQ branch are skipped, after re-decoding and binding their
register, PCs and success target. The prefix remains bounded to eight words.

A success literal requires its own bounded restore/RET tail and cached caller
entry check: a failed call-result preservation record is not tail authority.
Only the exact EQ success edge and qualifying terminal error branch may enter
the tail without conflict. Other entries withhold recovery, retaining exact
counts and up to 16 details. Tail evidence remains bounded to eight words.

Error-literal recovery may reuse a success-literal tail only when its captured
instructions, call/entry/return identity and false proof flags match. Return
choice accepts exactly one success source: preserved/copied call result or
literal bits, with a bound success-entry tail. Equality compares explicit bits
only. Int/Void callee contexts do not establish the caller's return type.

B.NE handlers, shared CMP tails, W/MOVK success prefixes, compiler-emission and
native/runtime/release qualification remain open. All source/runtime/exclusive
path/caller-return-type proof flags remain false. Twenty-four new and 256 affected
methods passed in bounded runs. A copied-seed fixture was extended to keep its
success target inside its declared caller; prior passing selections were reused.
No compiler, binary-admission or native workflow was repeated.

CMP success-prefix evidence is labeled `post_call`: those assignments precede
the conditional branch and are not exclusive to success. The reported success
entry is bound to the decoded EQ target and region join. Inspected tail words
remain visible even when an entry conflict withholds the literal; successful
records retain the same tail once, without duplicate evidence.

## Bounded CMP MOVK success-prefix updates

The current edge model is `swift-sync-error-edges-v11`, success-constant model is
`swift-success-constant-v11`, error-constant model is `swift-error-constant-v13`
and return-choice model is `swift-return-choice-v13`. X MOVK may now update a
known success-prefix literal before the adjacent CMP-zero test. The existing
constant-transfer path replaces only the selected halfword and retains the other
bits. MOVK on an unknown value does not establish known literal bits.

The extension reuses existing decoding, shift validation, constant transfer,
register copies and XZR discard semantics. Updated destinations invalidate error
aliases. Literal prefixes still require CMP, never CBZ/CBNZ; W MOVK and W seeds
remain refused. Prefix and protected-tail bounds remain eight words each. The
existing flag/handler/tail entry checks, exact outcome binding and false proof
flags remain intact. B.NE/shared CMP handlers, compiler-emission and native/runtime
qualification remain open.

Fifteen new methods and 268 affected methods passed. New controls cover all four
halfwords, repeated updates, MOVN seeds, known/unknown copies, error aliases,
unseeded refusal, XZR, bounds, tail conflicts and CLI/text evidence. Prior owned
image/compiler results were reused without repeating their workflows.

## Bounded CMP W-register success seeds

The current edge model is `swift-sync-error-edges-v12`, success-constant model is
`swift-success-constant-v12`, error-constant model is `swift-error-constant-v14`
and return-choice model is `swift-return-choice-v14`. CMP success prefixes now
admit W MOVZ/MOVN seeds through the existing local decoder and constant transfer.
Legal shifts are 0 and 16; reserved W halfword encodings remain refused.

A W seed establishes 32 bits and clears the corresponding X register's upper
32 bits. Thus W MOVN zero gives `0x00000000ffffffff`, independently of an X MOVN
error literal of `0xffffffffffffffff`. The full destination error alias is
invalidated by a W write. A separately saved full-width alias can survive; a
narrow write cannot preserve or create full-width error provenance.

Existing X copies and X MOVK updates may consume the zero-extended literal.
W copies and W MOVK remain outside the prefix subset. CBZ/CBNZ literal-prefix
widening and narrow error tests remain refused. Prefix/tail bounds, cached entry
checks, raw-word binding and false proof flags retain their prior scopes.
B.NE/shared CMP handlers and compiler/runtime/native acceptance remain open.

Fifteen new methods and 271 affected methods passed. New controls cover both
legal shifts, reserved encodings, high-bit clearing, aliases, excluded forms,
zero-register writes, bounds, conflicts and JSON/text evidence. No decoder,
dependency, compiler, binary-admission or native workflow was added or repeated.

## Bounded CMP W MOVK success updates

The current edge model is `swift-sync-error-edges-v13`, success-constant model is
`swift-success-constant-v13`, error-constant model is `swift-error-constant-v15`
and return-choice model is `swift-return-choice-v15`. W MOVK may now update a
known prefix literal through the existing decoder and constant transfer. The
selected 16-bit lane is replaced and the result is masked to 32 bits, clearing
upper X bits even when the seed was X-width. Unknown input remains unknown.

Both legal lanes, repeated updates and subsequent X copies/updates retain their
existing bit semantics. Reserved W shifts remain rejected. Every W update
invalidates the full destination error alias; a separately saved alias can survive.
CMP-only prefixes, eight-word prefix/tail bounds, cached entry validation and
exact outcome/proof binding remain unchanged. W-copy prefixes, B.NE/shared CMP
handlers and compiler/runtime/native qualification remain open.

Fifteen new and 286 affected methods passed. New controls cover width truncation,
legal/reserved lanes, known/unknown states, aliases, XZR, bounds, tail conflicts
and CLI/text evidence. Independent semantic review found no blocking issue.
Prior compiler, binary and native results were reused within their scopes.

## Bounded CMP W-register literal copies

The current edge model is `swift-sync-error-edges-v14`, success-constant model is
`swift-success-constant-v14`, error-constant model is `swift-error-constant-v16`
and return-choice model is `swift-return-choice-v16`. Canonical W MOV copies may
now participate in CMP-only success prefixes through existing local decoding and
constant transfer. Known sources supply zero-extended low 32 bits; unknown sources
invalidate destination knowledge. WZR supplies zero and destination WZR discards
writes.

W copies invalidate the destination's full-width error alias; they never promote
a narrow source into an error alias. A separately saved X alias may survive.
Call-result preservation remains conservative: copying an unknown call result
through W, including a self-copy, cannot establish a preserved full-width result.
Noncanonical copy encodings, CBZ/CBNZ literal prefixes and narrow error tests
remain refused. Existing prefix/tail limits, entry checks and outcome/proof
binding are unchanged.

Fifteen new and 301 affected methods passed, with independent semantic review
finding no blocking issue. New controls cover known/unknown and self copies,
upper-bit clearing, aliases, WZR, canonical encodings, bounds, conflicts and
JSON/text evidence. B.NE/shared CMP handlers and compiler/runtime/native
qualification remain open. No decoder, dependency or binary workflow was added.

## Bounded CMP shared-epilogue regions

The current edge model is `swift-sync-error-edges-v15`, region model is
`swift-sync-error-region-v14` and incoming-entry model is
`swift-region-direct-entries-v6`. A flag-screened CMP-zero/B.EQ error-fallthrough
candidate may now reuse the existing bounded success-arm and shared restore/RET
tail recognizer. The error interval, success arm and shared tail retain their
raw words, preferred VM bounds and false call-return, join-reachability and
restore-state proof flags.

Caller-local entry inspection exempts only the exact recorded canonical B.EQ
at the recorded test PC when its decoded target is the recorded success entry.
The qualifying terminal error branch remains the only expected error exit into
the shared tail. Other direct entries into the error interval, success arm or
tail remain conflicts. Incomplete or unclassified flag windows withhold region
recovery; an incomplete scan cannot establish absence of entries.

CMP shared-tail presentation and outcomes remain explicitly blocked. B.NE and
forward-error CMP layouts remain unqualified. No flag-state, dominance, runtime,
exclusive-entry, restored-state, source reconstruction or handler-semantics
proof is introduced. Prefix, success-arm and tail limits retain their existing
bounds; compiler-emission and native/release qualification remain open.

Thirteen new and 364 affected methods passed in bounded composed runs. A prior
test expectation was updated from unresolved to blocked for shared presentation;
126 preceding passing selections were retained. No compiler, binary admission or
native workflow was repeated.

## CMP shared-epilogue structural presentation

The current edge model is `swift-sync-error-edges-v16` and presentation model is
`swift-structural-presentation-v5`. A qualified CMP-zero/B.EQ error-fallthrough
region with a shared restore/RET tail can now receive an eligible structural
plan. The existing exact CMP/branch, flag-window and caller-local incoming-entry
checks remain required. B.NE and forward-error CMP layouts remain outside scope.

The presentation binds the terminal error branch's recorded PC and decoded target
to the join. After checking canonical words, contiguous PCs and bounded interval
sizes, it re-decodes the recorded success arm and tail as bounded in-memory word
evidence through the existing recognizer and requires the complete resulting
records to match. This is in-process structural consistency, not target execution
or saved-report admission. The plan retains both CMP/branch PCs, the encoded EQ
condition, nonzero error predicate, raw intervals and false restore-state proof.

CMP shared outcomes remain explicitly gated: success-result, success-constant and
error-constant records decline, and return choice remains unresolved. No source,
runtime, reachability, exclusive-entry or handler-semantics proof is added.
Compiler-emission and native/release qualification remain open. Eleven new and
330 affected methods passed; prior accepted compiler/binary results were reused.

## CMP shared-epilogue outcomes

The edge model is `swift-sync-error-edges-v17`, the success-result model is
`swift-success-result-v12`, the error-constant model is
`swift-error-constant-v17`, and the return-choice model is
`swift-return-choice-v17`. For an eligible, entry-screened CMP-zero/B.EQ
error-fallthrough region with a shared return tail, the existing bounded
analysis can pair a preserved or copied Int call result on the success arm with
an error-arm literal. It re-decodes the compare and branch and the shared tail;
error-path constant tracking clears known values at opaque calls. The choice
binds the complete condition and the common return PC.

An error literal can be a candidate independently when the success result is
clobbered; the choice remains unresolved. Shared CMP success literals and
NE/forward layouts remain withheld. This structural evidence does not prove a
runtime value, caller return type, exclusive path, handler semantics, restored
state, or source reconstruction. Fourteen new and 284 affected methods passed;
independent review found no blocking issue. Prior compiler, binary and native
results were reused within their existing scope.

## CMP shared success literals

`swift-sync-error-edges-v18`, `swift-success-constant-v15` and
`swift-return-choice-v18` extend screened CMP-zero/B.EQ shared-epilogue
outcomes to success-path literals. Constant tracking follows the post-call
prefix and then the selected success arm, applying the existing conservative
register and width rules. The success arm and tail are re-decoded and matched
against their complete recorded instruction evidence before a candidate is
accepted. The return choice retains the existing condition and common-return
bindings. Error-arm calls and writes do not flow into success-path constants.

These are selected-path structural candidates, not proof of runtime values,
caller return type, exclusive entry, handler semantics, restored state or
source reconstruction. NE and forward CMP handlers remain outside this
subset. Independent review found and prompted correction of a stale-arm
binding gap; a changed supported instruction is now refused. The focused and
affected checks passed after updating an obsolete refusal expectation; prior
compiler, binary and native results retain their existing scope.

## CMP/B.NE forward error regions

`swift-sync-error-edges-v19`, `swift-sync-error-region-v15` and
`swift-region-direct-entries-v7` admit a screened CMP-zero/B.NE success-
fallthrough, forward-error region through the existing bounded arm and shared
return recognizer. The actual adjacent compare and B.NE words, recorded window,
tested register, branch target, and forward geometry must agree. Flag-window
screening is required; the incoming-entry exemption applies only to the exact
recorded canonical B.NE edge. Other caller-local entries remain conflicts.

This is a structural region candidate only. CMP/B.NE presentation and outcomes
remain withheld; call return, reachability, exclusive entry, flag state,
handler meaning, restored state and source reconstruction are not proven.
Eight new methods and the affected selection passed after two older refusal
expectations were updated to the forward recognizer's refusal reason. Independent
semantic review found no blocking issue. Prior compiler, binary and native
results remain valid only within their existing scope.

## CMP/B.NE forward structural presentation

`swift-sync-error-edges-v20` and `swift-structural-presentation-v6` allow a
screened CMP-zero/B.NE success-fallthrough, forward-error region to receive a
structural plan. Exact compare and branch semantics, complete caller-local flag
and entry screens, bounded intervals and a shared tail remain mandatory. The
plan requires the actual bounded caller bytes: recorded comparison, branch,
success, error and tail words must match them. It then rebuilds the entire
forward region from those words with the existing recognizer and matches the
complete recorded region apart from the separately validated incoming record.

This is not source reconstruction or a proof of runtime values, exclusive
entry, flag state, handler behavior or restored state. B.NE success-result,
success-literal, error-literal and return-choice outcomes remain explicitly
gated. Eleven new and 232 affected methods passed. Independent review found no
remaining blocker after a focused stale-instruction binding correction. Prior
compiler, binary and native results retain their existing scope.

## CMP/B.NE forward error literals

`swift-sync-error-edges-v21` and `swift-error-constant-v18` admit an error-arm
literal candidate for a screened CMP-zero/B.NE forward-error region. The
analyzer derives a bounded caller-local edge scan from the supplied bytes and
requires exact agreement with the flag-window and incoming-entry records. It
also rechecks the structural plan against actual compare, branch, arm and tail
bytes before applying the existing error-path constant transfer. Opaque calls
clear known constants; a later complete assignment may establish new bits. W
assignments zero-extend, and unknown copies or partial updates remain unknown.

The candidate is selected-path structural evidence, not proof of call return,
handler meaning, runtime value, exclusive entry, caller return type, restored
state or reconstructed source. B.NE success outcomes and return choice remain
gated. Nine new and 260 affected methods passed; independent review found no
blocking issue. The per-call caller rescan is bounded by the existing function
scan limits. Prior compiler, binary and native evidence retains its earlier scope.

## CMP/B.NE forward success result

`swift-sync-error-edges-v22` and `swift-success-result-v13` admit selected-path
Int call-result preservation or a full-width copy restored to x0 for screened
CMP-zero/B.NE forward-error regions. The supplied caller bytes are rescanned
for flag-window and region entries and rebound to the structural plan. The
post-call prefix and success arm are inspected in order, with the B.NE target
bound to the error arm, followed by the recorded shared return tail. Narrow
writes do not preserve an unknown full-width result.

This is structural evidence, not proof of call return, runtime value, caller
return type, exclusive entry, handler semantics, restored state or source.
B.NE success literals and return choices remain gated. Twelve new and 280
affected methods passed, with independent semantic review. Prior compiler,
binary and native evidence remains valid only within its existing scope. The
caller rescan is bounded by existing function scan limits.

## CMP/B.NE forward return choice

`swift-sync-error-edges-v23` and `swift-return-choice-v19` can pair a screened
CMP-zero/B.NE forward success-path preserved or copied Int call result with an
error-arm literal. The existing producer facts must identify the same call,
respective arm entries, full condition and common recorded shared return PC.
The forward shared layout and success-result tail layout are required; success
literal candidates and conflicting success sources remain refused.

The choice is selected-path structural evidence only. It does not prove runtime
values, call return, exclusive entry, caller return type, handler meaning,
restored state or reconstructed source. Ten new and 314 affected methods passed
after one older unresolved-choice expectation was updated. Independent semantic
review found no blocker. Prior compiler, binary and native evidence retains its
existing scope.

## CMP/B.NE forward success literals

`swift-sync-error-edges-v24`, `swift-success-constant-v16` and
`swift-return-choice-v20` admit selected success-path literal bits for screened
CMP-zero/B.NE forward-error regions. The complete recorded post-call window is
bound to supplied caller bytes, caller-local entries are rederived, and the
forward presentation is revalidated before transfer. Literal tracking walks the
post-call prefix then the fallthrough success arm, including its exact terminal
branch over the error arm to the shared tail. W writes zero-extend; unknown
copies and unseeded partial updates do not invent known values.

A structural choice can pair exactly one success source, either literal bits or
a preserved/copied Int call result, with the error literal. Call, condition,
arm and shared return bindings and false proof flags remain required. This does
not prove runtime values, call return, caller return type, exclusive entry,
handler meaning, restored state or source reconstruction. Thirteen new and 336
affected methods passed after updating an older clobbered-result expectation.
Independent review found no blocker. Prior compiler, binary and native evidence
retains its existing scope; qualifying NE evidence uses bounded caller rescans.

## Owned assembler-backed CMP/B.NE literal qualification

OwnedCmpNeHandlers.s supplies a fixed owned success-fallthrough, forward-error
handler that calls the previously built OwnedEpilogueProvider object. The new
handler was assembled, linked and disassembled once; the resulting image was
admitted and analyzed once, and never loaded or executed. The prior provider
object was reused without repeating its build or verification.

The bounded image scan covered 208 instruction words and retained all 19 direct
calls: one recovered candidate and 18 explicit declines. The selected call at
VM 0xb74 records CMP/B.NE, a success literal of 0x0000000000001234 and an error
literal of 0xffffffffffffffff at the shared return 0xb94. Eight retained
compare, branch, arm and tail words matched the disassembly and relocated
regression tuple. Five new methods passed, covering both literals, missing
success seed, opaque-call invalidation, side entries and CLI output. Synthetic
relocation is separate from original-image admission.

This qualifies an assembler/linker-produced structural example; it does not
establish Swift frontend emission of the handler, runtime execution, ABI or CFI
correctness, restored state, clean-host behavior or native app/release
acceptance. Existing proof flags remain false, and prior results retain their
original scope. Analyzer semantics and models are unchanged.
