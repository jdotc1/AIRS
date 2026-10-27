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
