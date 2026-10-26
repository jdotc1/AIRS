# AIRS bounded development roadmap

This public repository is the single development baseline. Plans describe intended
work; acceptance records establish completed scope. Build 12 remains the published
preview and is not replaced by source-only increments.

| Milestone | Current position | Remaining boundary |
| --- | --- | --- |
| Native evidence review and saved workflows | Build 12 includes accepted Settings, comparison and persistent sidebar corrections | Qualify each changed user interaction after pending work settles |
| Conservative ARM64/CFI model | Merged through CLS v47; MOVK v48 and CBZ/CBNZ v49 merged in PR32; TBZ/TBNZ v50 merged in PR33 with bounded source/native qualification; historical identities remain distinct | New instruction/rule families require distinct positive and refusal evidence and independent review |
| Saved-report coverage triage | Reason selection, terminal-safe output, bounded detail and literal code ordering implemented | Additional triage tools must preserve full denominators, overlap, duplicate/conflict and exact identity context |
| Public distribution | Single repository; build 12 signed/notarized/stapled release, public browser download and actual App Translocation accepted on the development Mac | Clean-machine, minimum-macOS, Intel-app and offline qualification remain incomplete |

## Current bounded increment

Coverage triage, W SDIV/W UDIV and owned-image qualification are merged through
PRs #13–20; scalar REV/REV16/REV32 through PRs #21–23. Accepted results are reused.
Scalar [CLS W/X v47](CLS.md) is merged in PR #24 with accepted
[qualification results](CLS_RESULTS.md) reused.

Exact model-admission registry hardening is merged in PR #25; its accepted
[qualification](MODEL_ADMISSION_REGISTRY.md) is reused.

Historical/unknown-model decoder boundary tests are merged in PR #26; their
[accepted results](MODEL_ADMISSION_BOUNDARIES.md) are reused.

Coverage-text escaped-allocation preflight is merged in PR #27 with
[accepted results](COVERAGE_TEXT_PREFLIGHT.md) reused.

Exact refusal-instruction evidence is merged in PR #28 with
[accepted results](REFUSAL_INSTRUCTION_EVIDENCE.md) reused.

Refused direct-edge target diagnostics are merged in PR #29 with
[accepted results](REFUSED_BRANCH_TARGETS.md) reused.

Unknown CFG recovery evidence is merged in PR #30 with
[accepted results](CFG_UNKNOWN_RECOVERY_EVIDENCE.md) reused.

Possible-path discrepancy evidence is merged in PR #31 with
[accepted results](CFG_POSSIBLE_DISCREPANCY_EVIDENCE.md) reused.

The preceding local analysis improvement retains configured and completed CFG
state-visit counts in the existing work-budget exhaustion evidence row. Limits
still stop exploration immediately and retain unresolved status without checked
PCs; no supported subset or model change is added.
See [work-budget qualification](CFG_WORK_BUDGET_EVIDENCE.md).
Installation and release remain unchanged.

## MacScope reuse implementation

MOVK W/X v48 and CBZ/CBNZ W/X v49 are merged in PR32 with independent review,
owned-image qualification and native admission. See MOVK_RESULTS.md and
COMPARE_BRANCH_RESULTS.md. MacScope is read-only; no new binary is installed.
Recent multiply/CMN literal boundary cases are adapted as three passing regression
methods; existing AIRS arithmetic needed no change. Function matching and proof
fact recording remain subsequent work, not claimed implemented by this increment.

TBZ/TBNZ v50 is merged in PR33, with separate owned positive/refusal
evidence. See TEST_BIT_BRANCH.md and TEST_BIT_BRANCH_RESULTS.md. Binary release
and installation remain separate.

The first function-matching reuse increment, merged in PR34, adapts MacScope's generated-name
guard to saved-report comparison. Generic entry/section and address-shaped donor
labels no longer create cross-build symbol joins. Exact-image matching and model/
configuration checks remain authoritative. See GENERATED_SYMBOL_MATCHING.md for
behavior and eight new plus three affected passing methods. No fingerprint
matcher or new analysis model is claimed.

Manual finding pairs, merged in PR35, add validated explicit selections to the
saved-report API and CLI. MacScope's one-to-one pin precedence is adapted without
copying its framework or adding fingerprints. See MANUAL_FUNCTION_PAIRS.md for
nine new API, five isolated CLI and eleven affected passing methods. Manual pairs
remain review candidates and cannot override exact-image or compatibility guards.

The producer, merged in PR36, emits optional exact-byte body fingerprints through
an audit API/CLI opt-in, using only already-supported substantial functions.
See FUNCTION_BODY_FINGERPRINTS.md for bounds and twelve new plus fourteen affected
passing methods. Default/native-app output is unchanged. Fingerprints do not
perform matching or change unwind findings.

Exact-body candidate matching, merged in PR37, adds explicit API/CLI opt-in
matching after manual/unique-symbol matches. Duplicate evidence and ambiguous
symbol groups are not guessed; compatibility guards remain authoritative.
See EXACT_BODY_CANDIDATES.md for fourteen new API, four isolated CLI, one fresh
pipeline and twenty-five affected passing methods. Default/native-app matching
is unchanged; no identity proof or new analysis semantics is claimed.

The native codec increment, merged in PR39, preserves optional fingerprint fields through
typed report round trips, validates exact shape and qualifying context, and leaves
missing evidence unavailable. It does not enable fingerprint production or
matching in the app. See NATIVE_BODY_FINGERPRINT_CODEC.md for qualification.

The comparison-context codec, merged in PR40, preserves configuration-change status,
exact-body opt-in status and manual-pair records. Missing facts stay unavailable;
malformed or conflicting selection metadata rejects. See NATIVE_COMPARISON_CONTEXT.md
for eleven focused passing methods and a successful real app build. No native
matching or GUI activation is included.

The endpoint helper, merged in PR41, explicitly binds recorded manual endpoints and row facts
to two selected source audit reports. It validates declared identities/flags and
source-side ID membership without authenticating reports or recomputing change
classification/configuration identity. See MANUAL_PAIR_SOURCE_BINDING.md for ten
new passing methods and a successful real app build. No app workflow is activated.

Manual-pair compatibility, merged in public PR2, adds saved-configuration/model prerequisites on top of
endpoint binding. Explicit status must match original source data, and incompatible
manual rows must stay ambiguous. See MANUAL_PAIR_COMPATIBILITY.md for eleven new
passing methods and a real app build. Change-signature verification and native
workflow activation remain separate.

Manual-row change verification, merged in public PR3, checks changed/unchanged labels against selected
source finding signatures, reusing the donor comparator's separation of matching
and audit observations. See MANUAL_PAIR_CHANGES.md for bounded native qualification.
Nonmanual rows, summary integrity and automatic workflow activation remain separate.

Comparison row accounting, merged in public PR4, checks bounded row shape, per-side endpoint
uniqueness and exact six-field summary totals. See COMPARISON_ROW_ACCOUNTING.md
for focused native qualification. It is separate from source binding, matching
truth and signature verification; native app activation remains unchanged.

Selected-source fact binding, merged in public PR5, extends side-specific ID/verdict/scope
binding to every selected row, including nonmanual and one-sided rows. See
COMPARISON_SOURCE_FACTS.md. This does not verify matching semantics, source
completeness, configuration identity or nonmanual finding signatures.

Matched-change label verification, merged in public PR6, composes selected-source/accounting and
manual checks, then verifies all other selected pairs with the same observation
signature. See MATCHED_CHANGE_LABELS.md. Matching-basis semantics, source
completeness and native GUI activation remain separate.

Exact-image offset validation, merged in public PR7, checks host offset authority and declared
numeric offset groups, rejecting guessed selections from duplicate groups. See
EXACT_IMAGE_OFFSET_ROWS.md. Source completeness and cross-image symbol/body
matching semantics remain separate; no native workflow is activated.

The unique-symbol pair validator, merged in public PR8, checks raw source names, generated-name
exclusions and post-manual singleton groups for selected two-sided claims. See
UNIQUE_SYMBOL_PAIRS.md. One-sided symbol groups, body matching and completeness
remain separate; no matching producer or GUI workflow is activated.

The exact-body pair validator, merged in public PR9, checks explicit opt-in and selected
fingerprint buckets against the post-manual source snapshot, retaining symbol
precedence and duplicate blockers. See BODY_CANDIDATE_PAIRS.md. It does not
activate matching or prove body authenticity, identity or source completeness.

The duplicate-symbol group validator, merged in public PR10, checks actual source-name multiplicity,
required singleton-side selections and ambiguous labels after validated manual
pins. See DUPLICATE_SYMBOL_GROUPS.md. Singleton one-sided matching outcomes and
source completeness remain separate; native workflows are not activated.

The singleton one-sided symbol-row validator, merged in public PR11, checks added/removed claims
against post-manual source groups and deterministic body consumption. Missing
body metadata refuses only outcomes the option could change. See
ONE_SIDED_SYMBOL_ROWS.md. Omitted groups and unmatched/future bases remain separate.

The unmatched-row validator, merged in public PR12, binds side-specific added/removed claims to
admitted source IDs, unusable host names and unconsumed endpoints. See
UNMATCHED_ROWS.md. Omitted groups, future bases and completeness remain separate;
matching defaults and native workflows are unchanged.

The recorded matching-policy validator, merged in public PR13, checks canonical producer metadata
against validated manual pins and explicit body status, and rejects unsupported
basis names at this opt-in boundary. See MATCHING_POLICY.md. Generic decoding,
producer defaults, full-output reconstruction and native workflows remain separate.

The canonical manual-pair key validator, merged in public PR14, binds each manual row key to its
selected baseline/current IDs in producer order. See MANUAL_PAIR_KEYS.md. Earlier
APIs, matching defaults, complete-output reconstruction and native workflows retain
their existing scope.

The selected function-name validator, merged in public PR15, binds recorded labels to the selected
current finding, otherwise the selected baseline finding, using exact source text.
See SELECTED_FUNCTION_NAMES.md. Unselected group labels, complete output and native
workflow activation remain separate; names do not establish identity.

The unselected-symbol name validator, merged in public PR16, binds zero-endpoint ambiguity labels
to the exact admitted source-group name. See UNSELECTED_SYMBOL_NAMES.md. Its
AIRSApp build and 13 focused tests passed; independent review found no actionable
defect. Unselected offset-group labels and native activation remain separate.

The unselected-offset name validator, merged in public PR17, binds zero-endpoint exact-image
ambiguity labels to the producer's first recorded current member, otherwise its
first baseline member. See UNSELECTED_OFFSET_NAMES.md. Its AIRSApp build and 14
focused tests passed; independent review found no actionable defect. Source-order
authenticity, complete-output reconstruction and native activation remain separate.

The canonical row-order validator, merged in public PR18, checks strictly ascending raw UTF-8
complete keys after the existing declared-row proofs. See CANONICAL_ROW_ORDER.md.
Its AIRSApp build and 16 focused tests passed; independent review found no
actionable defect. Input is not reordered; complete-output reconstruction,
authenticity, identity and native activation remain separate.

The same-image row-coverage validator, merged in public PR19, detects omitted offset groups from
the union of two admitted saved reports. See SAME_IMAGE_ROW_COVERAGE.md. Its
AIRSApp build and 17 focused tests passed; independent review found no actionable
defect. Cross-image use refuses; original-binary coverage, remaining producer
fields, authenticity, identity and native activation remain separate.

The body-disabled cross-image coverage validator, merged in public PR20, detects omitted manual,
symbol and side-specific unmatched groups after validated pins. See
BODY_DISABLED_ROW_COVERAGE.md. Its AIRSApp build and 18 focused tests passed;
independent review found no actionable defect. Explicit false body status is
required; unknown/enabled status and same-image use refuse. Body-enabled
coverage, binary completeness, authenticity and native activation remain separate.

The body-enabled cross-image coverage validator, merged in public PR21, requires every projected
body pair plus all remaining groups after manual/body consumption. See
BODY_ENABLED_ROW_COVERAGE.md. Its AIRSApp build and 20 focused tests passed;
independent review found no actionable defect. Existing candidate precedence and
architecture/subtype gates are reused; unknown/false status and same-image use
refuse. Original-binary completeness, authenticity, remaining producer fields and
native activation remain separate.

The covered comparison decoder, merged in public PR22, provides one bounded native entry point
for the three saved-report coverage domains. See COVERED_COMPARISON_DECODE.md.
Its AIRSApp build and 16 focused tests passed; independent review found no
actionable defect. Generic decode remains broader; cross-image missing body
status refuses. Native workflow activation, remaining producer fields,
authenticity and identity remain separate.

The explicit body-status producer change, merged in public PR23, records false as well as true in
new comparison metadata. See EXPLICIT_BODY_STATUS.md. Eleven new tests and two
affected checks passed, including the CLI default path; independent review found
no actionable defect. Accepted native evidence is reused. Matching remains off
by default; historical absence stays unknown, and app activation remains separate.

The covered batch-runner policy, merged in public PR24, exposes saved-report coverage as explicit
acceptance opt-in. See COVERED_BATCH_COMPARISON.md. The real AIRSApp build passed;
ten async methods qualified through nine accepted results and one corrected
payload check. Independent review found no actionable production defect. Existing
no-argument initialization and GUI callers retain legacy acceptance; GUI activation,
authenticity and identity remain separate.

The comparison-schema alignment, merged in public PR25, admits current manual/body policies and
bases, plus optional typed body status and bounded exact manual-pair objects. See
COMPARISON_SCHEMA_ALIGNMENT.md. Fourteen development-validator tests passed with
zero skips; independent review found no actionable defect. Only baseline-diff was
regenerated. Structural validity does not establish semantic coverage, source
binding, authenticity or GUI activation; accepted runtime evidence is reused.

The owned producer/native coverage bridge, merged in public PR26, qualifies exact Python-produced
comparison bytes through covered decoding and strict batch acceptance. See
PRODUCER_COVERAGE_BRIDGE.md. Eight new controls and two mutation refusals passed;
independent review found no actionable defect. Production behavior and GUI callers
are unchanged; accepted app/runtime evidence is reused. Packaged transport,
authenticity, identity and GUI acceptance remain separate.

The local producer/native observation-parity qualification checks reason sorting
and multiplicity, relative addresses, checked-PC order and raw evidence text. See
PRODUCER_OBSERVATION_PARITY.md. Seven new controls and two consistent-accounting
label refusals passed; independent review found no actionable defect. Existing
coverage controls and production code remain unchanged; accepted app/runtime
evidence is reused. Binary equivalence, authenticity and GUI acceptance remain separate.

Next reuse sequence:

1. FunctionVersionMatcher adaptation for cross-build review candidates, beginning
   with separately qualified native preservation/activation or additional explicit
   evidence. Manual pairs, body production and exact-body candidate
   selection are merged. Historical reports lack fingerprints; CFG fingerprints
   and call-graph propagation are not implemented. Structural
   matches must never replace exact image identity or model/configuration checks.
2. Structured refusal facts where they remove duplicated diagnostic handling;
   retain AIRS unknown/discrepancy precedence instead of donor proof precedence.

## Next candidates, one bounded item at a time

1. Use the documented saved-report workflow to identify a concrete unresolved
   behavior worth improving; avoid adding filters without a specific review need.
2. Select a next semantic extension from an explicit owned example and independently
   derived recovery expectation. Reason frequency in supplied reports is prioritization
   input, not representative prevalence or automatic permission to widen support.
3. Complete clean-machine/minimum-OS acceptance when an appropriate environment is
   available. Development-Mac acceptance does not close these gates.

Reuse accepted results for unchanged inputs. Run only changed-boundary checks and
keep source tests, native GUI acceptance, packaging, signing/notarization, installation
and release publication distinct. Runtime evidence and user data stay outside source.


## Local workspace maintenance

Completed worktrees and merged feature branches can be pruned after preserving
unique source/evidence. Rebuildable caches and intermediate packaged app copies
need not remain alongside the active public checkout. See WORKSPACE_FOOTPRINT.md.
The saved native fingerprint-codec draft was completed and merged in PR39. Typed native
preservation and structural admission now have nine focused passing tests and a
successful real AIRSApp build. See NATIVE_BODY_FINGERPRINT_CODEC.md. Build products
are removed after retaining logs. Fingerprint production/matching activation and
GUI acceptance remain separate; no installed binary or release changes.

## Swift decompilation: synchronous error paths

The first bounded throwing-call return-edge model is implemented and qualified
against an owned optimized Swift image; see SWIFT_ERROR_FLOW.md. It recovers
local success/error successors without claiming complete source reconstruction.
Next extend explicit declaration coverage with owned examples, then bounded
handler-region recovery. Async continuation reconstruction remains separate.

The next bounded slice now adds opt-in local error-region intervals with raw
instructions and opaque call targets, qualified against the existing owned Swift
example and eleven new focused methods. Exclusive entry, catch type, reachable
join and source-like handler reconstruction remain unimplemented. The next
semantic step should establish incoming-edge constraints before widening region
layouts or presenting structured source.

Caller-local direct-entry validation is now implemented as an opt-in supplement,
with 17 focused passing controls and accepted owned-caller qualification. It
reports observed side entries or unresolved classification without claiming
exclusive entry. Next establish a separate structured-presentation eligibility
contract that consumes these statuses and preserves unresolved indirect/external
entry limits before presenting source-like handler structure.

Structured-presentation eligibility now consumes qualified region/direct-entry
facts and emits bounded labeled display plans only for eligible structural
candidates. Seventeen new focused controls and the accepted owned-example records
qualify the source contract. Source reconstruction remains disabled. Next add a
bounded renderer that preserves blocked/unresolved evidence, raw instructions,
opaque-call labels and all proof limits; native UI activation remains separate.

The bounded terminal renderer is implemented with thirteen focused passing
controls and renderer-only accepted-record qualification. It retains eligible,
blocked and unresolved outcomes, raw evidence and source denominators within
explicit row/byte caps. Next improve bounded signature/handler coverage from
owned Swift examples, or separately adapt this qualified presentation contract to
native UI. Full source reconstruction and native activation remain separate.

The v2 Swift edge model now admits exact ordinary Int-to-Void throwing free
functions, qualified by ten new controls and one owned compiler example. The
example recovers correct success/error edges but conservatively declines its
error block's jump past a distinct success entry into the epilogue. That concrete
layout is the next bounded region-recovery candidate; it requires separate join
and entry analysis rather than treating the success entry as the true join.

## Saved-report coverage GUI integration

The saved-batch pairing window now exposes strict coverage with a captured
per-invocation policy. Legacy programmatic behavior remains the default. The real
app build and a new refusal/export/policy-separation workspace test passed;
accepted core controls were reused. Interactive isolated-profile acceptance is
still required. See GUI_SAVED_REPORT_COVERAGE.md for delivered and held scope.
