# Development scope and retained evidence

Status note: this page records the state at 0.3.3 build 12 and the source development
that followed it. The ARM64/CFI model chain is carried through v50, the current source
model; after v47 the page records only that chain. It does not record releases after
build 12. The current release is 0.3.4 build 32 ([release
record](RELEASE_0_3_4_BUILD32.md)), and the current state and open items are in
[ROADMAP.md](ROADMAP.md).

The single active source repository is AIRS-app. Current source includes the v41
engine baseline and the accepted build 12 sidebar corrections. The current preview binary is 0.3.3/build 12, published from its accepted signed
candidate and retained results. See [release scope](RELEASE_0_3_3_BUILD12.md). See [sidebar acceptance](SIDEBAR_NAVIGATION.md).

The table below retains historical, boundary-specific qualification; later release
records and their named artifact scopes must be read separately. SOURCE_SNAPSHOT.json
records the final private-to-public migration. No private source history is required
for future development.

| Boundary | Retained evidence | Scope limit |
| --- | --- | --- |
| v36: X29-relative X stack accesses | Focused Python/native checks and a separate owned nonleaf witness | Bounded aligned X accesses and modeled recovery; no general memory support |
| v37: scalar X SDIV | Focused signed arithmetic, refusal and native admission checks | W forms and wider instruction families remain outside this increment |
| v38: W RBIT | Twelve focused new Python methods plus a four-function owned-image qualification | No W MOVZ or general W-instruction expansion |
| v39: equivalent compact rules | Sixteen new focused Python methods, native admission, and four retained two-function comparison cases | Exact contiguous equivalent rules; different encodings, gaps and overlap still refuse |
| v40: local FDE refusal | Nine new focused methods, three native admission methods and the corresponding app build | Two operand-free row-state opcodes only; opaque tails are not interpreted; no new real-image v40 qualification |
| Settled project companions | Original import/export checks and five affected integration selectors | Picker suppression and historical-panel GUI acceptance remains incomplete |
| Read-only project catalog | CLI build, six focused new methods, one literal CLI invocation | Metadata only; no evidence validation, history resolution or queue restoration |
| Lumen Settings | Accepted donor checks reused; actual AIRS candidate appearance reviewed before local installation | Appearance only; not complete interaction, normal delegate or release acceptance |

Counts describe their original bounded inputs. Separate fixtures/cases are not
combined into a larger corpus denominator. No source export reruns these checks.
Private execution logs, qualification/comparison receipts and local artifact
locations are intentionally excluded; synthetic code/report fixtures remain.

For v40, the triggering unsupported opcode consumes its instruction budget.
Opaque bytes reserve possible instructions and rows plus a pending/final row.
The entire refused FDE loses its supported prefix; shared framing, ranges and
overlap remain globally checked. Other unsupported opcodes remain globally
fatal. This adds no supported CFI instruction and no asynchronous claim.

Before a binary release: assign a release identity, reconcile package/source
version constants, qualify changed optimized integration within an explicitly
allocated scope, and complete the required distribution checks. Existing signing,
notarization, clean-Mac and OS receipts apply only to their named artifacts.
Publication and release remain separate from this development source update.

## Saved-report and project navigation increment

The development app and CLI built successfully. Ten focused native methods
passed for project search, catalog filtering/ordering and bounded store traversal.
Fifty-nine new Python methods passed in composed receipts: 49 earlier methods
were reused and the 10 remaining reason/limit/order methods passed on resume.
The portable-test repair retains its separate accepted 777-method Linux matrix;
that matrix was not replayed. New GUI workflows remain unexercised. No new
optimized binary, signing, notarization, installation or release is claimed.

## Current-baseline PR5 integration

Twenty-seven focused Python methods passed for literal CFI controls, whole-owned
Mach-O emission/admission and historical v40 admission. AIRSApp and native CLI
builds passed, along with24 native methods covering raw signature evidence,
portable documents, archive/lifecycle behavior and current/historical CFI models.
The v41 native fixture comes from the first checked emission without a repeated
audit. Two independent source reviews found no actionable defect. V40 direct
parser defaults, exact FDE selection, overlap and global opaque-work accounting
remain preserved. Existing vendor/runtime/dependency and original PR receipts
were reused; no full suite or corpus was rerun. New GUI acceptance, wheel/sdist,
optimized packaging, signing/notarization and installed updates remain separate.

## Post-build-12 source development: bounded coverage reason detail

The public roadmap now records the current baseline and next bounded candidates.
`coverage --limit N` limits ranked reason detail after optional reason selection,
while preserving full inventory counts, report records, duplicate/conflict context
and unmatched selections. JSON/text disclose explicit omissions; default output
retains its existing shape. Limited/selected projections remain CLI-only and are
not admitted by the unchanged complete-inventory native importer.

Seven new focused Python methods and one isolated-bootstrap CLI invocation passed;
unchanged aggregation, engine, native and runtime receipts were reused. No binary,
GUI, installation or release change is claimed. See COVERAGE_REASON_LIMIT.md and
ROADMAP.md for contract, evidence scope and remaining work.


## Post-build-12 source development: literal coverage reason ordering

`coverage --sort reason` orders selected saved-inventory reason rows by literal code
before an optional limit. JSON and text agree; default count ranking and complete
summary, duplicate/conflict and selection context remain intact. This is a CLI-only
projection, not a change to the native complete-inventory admission contract.

Seven new focused Python methods and one literal isolated-bootstrap invocation
passed. The merged reason-limit results and unchanged engine/native/runtime checks
were reused. No binary, GUI, installation or release changes were made. See
COVERAGE_REASON_ORDERING.md for scope and interpretation limits.


## Post-build-12 source development: literal summary function-name filtering

`summary --name-contains TEXT` narrows saved finding detail using a literal,
case-sensitive substring without Unicode normalization. It composes after existing
verdict/reason selection and before ordering/limiting. Selection metadata exposes
the stage counts while preserving full report denominators and evidence context.

Eight new focused methods passed, with only the affected text method repeated after
its row-label refinement. One isolated-bootstrap CLI invocation passed. Accepted
summary/coverage and unchanged engine/native/runtime results were reused. This is
source-only development; no GUI, binary, installation or release change is claimed.
See SUMMARY_FUNCTION_NAME_FILTER.md for the contract and evidence scope.


## Post-build-12 source development: minimum coverage reason count

`coverage --minimum-count N` selects reason detail by inclusive supplied-report
count before ordering and limiting. Explicit metadata and text expose omissions;
full denominators and duplicate/conflict context are preserved. This does not
measure representative prevalence or change any finding verdict.

Six new focused methods and one isolated-bootstrap CLI invocation passed. Accepted
aggregation, summary/coverage, protected output and unchanged native/runtime results
were reused. No installed-app, settings, stores or release operations were made.
See COVERAGE_MINIMUM_COUNT.md for the contract and evidence scope.


## Post-build-12 development: connected saved-report triage example

Minimum-count filtering is merged through PR #16. SAVED_REPORT_TRIAGE.md now
connects reason inventory to selected original findings, explains each projection's
counts and limitations, and records the boundary for proposing semantic work.
The companion scripts/saved-report-triage-example.py runs two bounded commands on
saved sample JSON into a fresh output directory, stops on failure and retains logs.

Its first composition check passed: nine full functions, four unresolved functions,
four inventory reasons and the original selected finding ID. Existing component
results were reused; no image audit, native build/GUI, packaging, installed-app or
release qualification was repeated. Settings and stores remain untouched.


## Post-build-12 semantic development: bounded W SDIV v42

Source inspection confirmed W signed division was refused in v41. The deliberately
owned W SDIV witness now uses shared X transfer and zero-extending W write under
arm64-bounded-w-sdiv-v42. Unknown and stack provenance, frame-body destinations,
required original-register recovery and possible-path uncertainty stay conservative.
Historical model identities remain distinct; W UDIV remains refused.

Eleven distinct new Python methods, seven affected existing selectors and three
new native admission methods passed in composed receipts. The real AIRSApp debug
target built. Independent read-only semantic review found no actionable defect;
its recommended divisor-truncation and unknown-precedence cases were added and
passed. The native fixture reuses the first new engine emission over typed owned
parser substitutes; no fresh whole-image parse or prevalence gain is claimed.

The test build reported an existing unused Bool warning at
FileOpenRoutingTests.swift:212. No GUI, installed app, settings, stores, packaging,
signing or release operations were performed. See SDIV_W.md and
SDIV_W_RESULTS.md for exact boundaries and fresh/reused evidence.


## Post-v42 hardening: align refusal fixtures

Triage guide and W SDIV v42 are merged through PR #17. Focused source inspection
found older refusal tests still using the newly admitted W SDIV word. These
fixtures now use a deliberately unmodeled control neighbor; one new inventory
method explicitly checks admitted W SDIV alongside the refusal. No engine/model,
native or installed-app behavior changed.

Twelve focused methods passed in composed receipts, including an additional RBIT
sentinel identified by independent read-only review. Accepted W SDIV, native build,
model admission and unrelated results were reused. No full suite, corpus, GUI,
packaging, installation or release operations were performed. See
V42_REFUSAL_FIXTURES.md for the initial failure, exact correction and evidence scope.


## Post-v42 semantic development: W UDIV v43

V42 refusal-fixture hardening is merged through PR #18. The next bounded source
increment adds scalar W unsigned division under arm64-bounded-w-udiv-v43, reusing
X unsigned transfer and W writes. Raw stack sources, unknown inputs, frame-body
writes and uncertain/unknown recovery remain conservative. Python/native exact
admission retains v42 and earlier model identities.

Twelve distinct new Python methods and fourteen affected existing methods passed
in composed receipts. Two new complete owned Mach-O variants exercise real parsing
and engine emission with correct versus missing-X19 recovery metadata; their first
reports are retained, and the mismatch report seeds the native fixture directly.
The real AIRSApp debug target built, and three new native methods passed.
Independent semantic review found no actionable correctness issue.

Affected refusal tests were aligned with W UDIV admission. Historical v42 import
checks remain literal, while current-producer assertions and evidence destinations
track the current model. The historical CFI emission test's analogous assertion/
receipt-name repair was source-reviewed only; its accepted image workflow was not
replayed. Unrelated results were reused. No full suite, corpus, GUI, packaging,
signing, installation or release operations were performed. Installed settings and
stores remain untouched. See UDIV_W.md and UDIV_W_RESULTS.md for exact scope.


## Post-v43 qualification: signed division through complete owned images

W UDIV v43 is merged through PR #19. The next bounded qualification increment
adds three new complete owned Mach-O signed-division examples using the unchanged
owned layout builder and explicit checked instruction replacements. Real parsing
and engine emission distinguish correct recovery agreement, missing-X19 concrete
inconsistency and unknown recovery without supported checked PCs. All preserve
the two-function denominator and original call-site PC.

Three new Python methods and three new native codec methods passed once. First
reports directly seed the three new native codec fixtures. Independent read-only review found no actionable concern. Accepted
arithmetic, model-admission, app build and unrelated results are reused; no unchanged
image was re-audited or rehashed. No production code, model identity, GUI, installed
app, settings, stores or release operations changed. See W_SDIV_OWNED_IMAGES.md for
the native result and exact fresh/reused scope.


## Post-v43 semantic development: scalar REV v44

Complete owned-image W SDIV qualification is merged through PR #20. The next
bounded family adds full-width scalar byte REV W/X under arm64-bounded-rev-v44,
reusing owned MacScope decode mapping and AIRS state, W write, frame classification
and recovery helpers. Partial/vector reversals remain refused. Raw-stack, unknown,
preserved-register and uncertain-recovery behavior stays conservative.

Fourteen new Python methods, two affected RBIT neighbor methods and four new native
methods passed. Six new complete owned images qualify correct/missing/unknown
recovery at both widths without parser mocks; first reports supply native fixtures.
The real AIRSApp debug target built. Independent read-only semantic review found
no actionable issue. Unrelated accepted results were reused; no corpus, GUI,
packaging, installation or release operation occurred. Installed app, settings and
stores remain untouched. See REV.md and REV_RESULTS.md for exact scope.


## Post-v44 semantic development: scalar REV16 v45

REV v44 is merged through PR #21. The next bounded family adds scalar halfword
byte swaps under arm64-bounded-rev16-v45, reusing owned one-source mapping and the
existing REV state/guard/write path. Full-width REV retains its byte loop; X REV32
and vector forms remain refused. Known/unknown, provenance, frame and recovery
boundaries stay conservative.

Fourteen new Python methods, ten affected full-REV/RBIT methods and four new native
methods passed. Six new
complete owned images qualify correct/missing/unknown recovery for both widths,
and first reports supply native fixtures. The real AIRSApp debug target built.
Independent read-only review found no corrective issue. See REV16_RESULTS.md for
the native result and exact fresh/reused scope. No GUI, packaging, installation,
release or installed-app/settings/stores operations were performed.


## Post-v45 semantic development: scalar REV32 X v46

REV16 v45 is merged through PR #22. The next bounded family adds scalar byte
reversal within 32-bit words under arm64-bounded-rev32-v46. The shared REV path
retains full-REV and REV16 behavior; the sf=0 neighbor stays existing W REV.
Raw-stack, unknown, frame and uncertain-recovery behavior remain conservative.

Fourteen new Python methods, ten affected REV/REV16/RBIT methods and four new
native methods passed.
Three complete new owned images qualify correct/missing/unknown recovery through
real parsing and engine emission, and first reports seed native fixtures. The
real AIRSApp debug target built. Independent read-only semantic review found no
actionable issue. See REV32_RESULTS.md for native and fresh/reused scope. No GUI,
packaging, installation, release or installed-app/settings/stores operations occurred.


## Post-v46 semantic development: scalar CLS W/X v47

REV32 v46 is merged through PR #23. The next bounded family adds count-leading-
sign bits under arm64-bounded-cls-v47, reusing owned one-source mapping and CLZ
state handling. The sign bit is excluded; zero/all-ones differ from CLZ counts.
Raw-stack, unknown, frame and recovery boundaries remain conservative, and historical
CLZ behavior/error codes are retained.

Fourteen new Python methods, thirteen affected CLZ/RBIT/decoder methods and four
new native methods passed
in composed receipts. One loader selector named the wrong class; only that selector
was corrected and executed, without replaying passed methods. Six new complete
owned images qualify correct/missing/unknown recovery, and first reports supply
native fixtures. The real AIRSApp debug target built. Independent read-only review
found no actionable issue. See CLS_RESULTS.md for native and exact fresh/reused
scope. No GUI, packaging, installation, release or installed-app/settings/stores
operations occurred.

## Post-v47 semantic development: MOVK W/X v48

CLS v47 is merged. The next bounded family adds exact MOVK W/X under
`arm64-bounded-movk-v48`, adapting the owned MacScope move-wide field mapping. The
operation reads its old destination, replaces the selected 16-bit lane and masks to the
destination width. W shifts 32 and 48 are rejected, register 31 is the zero register,
and NZCV and memory are unchanged. Retained original or unknown bits stay unknown, and
raw stack addresses refuse before W projection.

Eight new state and recovery methods passed, and three emission methods passed on six
first-run complete owned Mach-O images that keep correct, missing-recovery and
unknown-recovery cases distinct. Six emitted reports supply native fixtures, and four
new native admission methods passed. Independent semantic and fixture review found no
actionable defect. See MOVK.md and MOVK_RESULTS.md. No accepted image was re-audited or
rehashed, and target instructions were never executed. Installed app, settings and
stores are unchanged and no release action is claimed.

## Post-v48 semantic development: CBZ/CBNZ W/X v49

`arm64-bounded-compare-branch-v49` adds exact CBZ/CBNZ W/X using the owned MacScope
compare-and-branch field mapping. Register 31 is the zero register. A concrete value
selects one edge after width masking; unknown or original sources fork both edges
without restoring certainty. A raw stack address refuses before W projection or zero
inference. No register, NZCV, SP or memory is modified. The shared conditional-edge
classification carries the family through dispatch, natural-loop handling, shared
teardown recognition and target validation. TBZ/TBNZ, indirect branches and unsupported
loop shapes stayed outside this model.

Eleven new Python state and CFG methods passed in composed runs. Two tests were
corrected, one expectation and one witness input, without a production defect, and only
failing selectors were rerun. Three
emission methods passed on six first-run complete owned Mach-O images, which exercise
CBZ at both widths; CBNZ has unit coverage only. Forty-seven affected existing methods
passed, and two new synthetic methods qualify exact v48/v49 admission and future-label
handling. The real AIRSApp debug product built and eight new native methods passed: four
for MOVK and four for compare-and-branch. Three arithmetic boundary methods adapted from
owned MacScope cases passed without a production change. Independent read-only review
found no actionable defect. v48 and v49 are merged in PR32. See COMPARE_BRANCH.md and
COMPARE_BRANCH_RESULTS.md. No corpus, GUI, packaging, signing, notarization, release or
installation operation occurred.

## Post-v49 semantic development: TBZ/TBNZ v50

`arm64-bounded-test-bit-branch-v50` adds exact TBZ/TBNZ using the owned MacScope
test-and-branch mapping. Low-bit forms test W bits 0 to 31 and high-bit forms test X
bits 32 to 63; register 31 is the zero register. Only a concrete source chooses one
successor. Original and unknown sources keep both edges, and derived stack addresses
refuse before projection. The instructions write no register, memory, SP, FP or NZCV.
Bit-tested teardown evidence has its own code. Indirect branches, unsupported loop
shapes and asynchronous or all-PC recovery are not added.

Ten new state and CFG methods passed in composed receipts, with unit coverage of all 64
bit indices. One new budget test named a nonexistent field; it was corrected and only
that method was rerun. Three emission methods passed on 12 first-run owned Mach-O
images: TBZ and TBNZ at bits 0 and 63, each with correct recovery, concrete missing
recovery and unknown-predicate reachability. Complete images cover bits 0 and 63 only.
Two new synthetic admission methods and eleven affected CBZ/CBNZ methods passed. Twelve
native fixtures copy the first emitted reports, the real AIRSApp debug product built,
and four new native admission methods passed. Independent read-only review found no
actionable defect. v50 is merged in PR33. See TEST_BIT_BRANCH.md and
TEST_BIT_BRANCH_RESULTS.md. No GUI, corpus, packaging, signing, notarization, release or
installation action is included, and the clean-machine, minimum-macOS, Intel-app and
offline release gaps stay open.

v50 is the current source model. Later source work is recorded in
[ROADMAP.md](ROADMAP.md).
