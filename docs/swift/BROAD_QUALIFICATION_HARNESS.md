# Broad qualification harness

The executable `scripts/swift_broad_qualification.py` requires explicit primary
and second-toolchain capture directories. It has no machine-specific capture
paths or automatic evidence packaging. Keep it unrun until the complete pipeline
is ready and its one final qualification pass is authorized.

Run from the repository through the configured shared storage guard. Set these
variables to existing local capture/review records and a new private output
directory before execution:

```sh
: "${STORAGE_GUARD:?Set the configured storage-guard executable}"
: "${PRIMARY_CAPTURE:?Set the primary compiler capture directory}"
: "${SECOND_CAPTURE:?Set the second-toolchain capture directory}"
: "${QUALIFICATION_OUTPUT:?Set a new private qualification output directory}"
: "${REVIEW_ONE:?Set the first whole-branch review JSON}"
: "${REVIEW_TWO:?Set the second whole-branch review JSON}"
"$STORAGE_GUARD" run -- python3 scripts/swift_broad_qualification.py \
  --capture "$PRIMARY_CAPTURE" --second-capture "$SECOND_CAPTURE" \
  --output "$QUALIFICATION_OUTPUT" \
  --review "$REVIEW_ONE" --review "$REVIEW_TWO" --execute-final
```

Omitting `--execute-final` prints an UNRUN plan without opening compiler captures
or creating the output directory. Final execution requires committed source and
two review records bound to the current Git HEAD. After prerequisites, exclusive
creation of `FINAL-PASS-STARTED.json` prevents overwrite or accidental replay,
including after a crash. There is no resume, overwrite, or verification bypass.
A partially executed pass requires the parent to preserve evidence and resolve
new authorization before any further execution.

Review records must preserve actual review findings and corrections. Required
keys are `scope: "whole_broad_branch"`, `decision: "passed"`, `reviewer` (two
independent reviewer identifiers), `source_revision` (the exact final committed
HEAD), `unresolved_findings: []`, and `correction_history` (a list, empty only if
there were no corrections). The harness does not author favorable reviews.
Component reviews do not satisfy the whole-branch gate.

The harness reuses the fixed-v2 and official second-compiler compile receipts,
source manifests, LLVM/nm compiler indexes, and their existing digests. It loads
owned images through `load_owned_swift_image` custody admission, with no source
or image hashing, recompilation, disassembly, or index regeneration. Physical
sites are deduplicated by mode and actual call PC. Each indexed confirmed owned
call receives one bounded callsite/ABI/candidate/independent replay evaluation.
The ledger retains declines and incomplete gates. Source categories and source
challenge names remain separately identified; source label presence requires
an actual emitted indexed caller and never satisfies observed challenge coverage.
The positive geometry key uses only the independently checked selected post-call
trace and success/error/shared partitions. It contracts data operations, padding
and unconditional hops, then numbers the rooted condition/call/terminal graph
without addresses or register names. Caller-prefix instructions, stack-frame
spills, signature variation and lowering labels cannot add keys. Checked error
transport to a non-x21 selected test register remains a row diagnostic and does
not multiply the geometry count.
A missing or malformed selected graph receives an incomplete measuring
disposition and cannot add a geometry. ABI shapes use admitted storage contracts,
never case names, owner indices, addresses, constants, or a source shape count.

The required challenge inventory has twelve explicit keys: CBZ, CBNZ,
CMP/conditional test, direct propagation, independent success/error arms, shared
epilogue, multiple returns, nested handlers, local error conversion, nonreturning
terminator, tail call and optimized/inlined absence. Each record separates owned
source intent from retained raw PCs/words, image identity, checked CFG locator and
independent outcome disposition. Mixed diagnostic features and result lowerings
do not satisfy this inventory. Observed or explicitly refused relevant machine
forms may satisfy challenge observation; source-only, collapsed, missing and
unproven records cannot. An absent required form keeps the gate INCOMPLETE.

Nested-handler intent requires a second independently admitted throwing call and
its independently checked error-alias test/corridors inside one exclusive outer
outcome arm. The inner tails may join outer shared code. This bounded reconciliation
uses already-computed records and charges work/retention; it performs no extra
image analysis. An unrelated conversion/overflow condition cannot establish the
link. Without it, the observed source challenge stays collapsed or unproven.
Shared-epilogue coverage requires a shared checked RET, not a shared BRK alone.
Conversion intent requires checked distinct scalar
output and cleared x21 at the error return. Direct propagation intent requires
the checked raw selected-call x21 origin at every error return. None recovers a
catch type or source handler. BRK records an exception transfer without proving
Swift noreturn or external resumption. Tail syntax records an escaping B/BR,
without proving the target's source semantics. Optimized/inlined absence requires
both the index's zero-call record and complete matching caller byte scans with
zero call instructions; the cause of that absence remains unproven.

The negative plan reserves one declaration-kind control for each of the seven
primary callable families inside its 280 retained mutations. It fills the
remaining slots with globally distinct field paths stratified by claim domain,
and reseals only JSON representation size before evaluation. A family control
is distinguished by its family and physical call site; no same-site/path pair
is repeated. Missing family controls keep a separate mandatory gate incomplete.
Eleven separate limits and one stale-custody attack add twelve cases. Eight small
synthetic byte attacks parse distinct fresh Mach-O inputs with coordinated
identity/raw facts, so their rejection is not merely old parser custody. The
synthetic registry observation binds only their unchanged authored RET callee;
it never upgrades a changed real ABI or compiler receipt. Attack kinds must cover
identity, custody, raw call, post-test, polarity, CFG, entry, nominal, ABI, value
attachment, truncation, work limits, dispatch and proof scope. An ignored deleted field that
remains eligible causes the zero-false-eligible gate to fail and is reported.
No negative outcome drives adaptive retry or extra checking.

Source reconciliation separately enforces every 80/100/55/60/45/35/25/20
category minimum, unique case IDs and complete nonduplicate feature vectors,
and at least 80 source signature shapes. These are saved manifest facts, not
new AST/compiler evidence or the separate 80-emitted-ABI-shape gate.

The repeat plan selects exactly 100 distinct eligible physical sites, stratified
by compiler capture, optimization, family, geometry and result lowering. Each is
repeated once through admission, construction and validation and compared using
canonical public JSON, including accounting. Fewer than 100 sites is incomplete.
No third run or whole-image repeated scan occurs.

The machine ledger includes all quantitative gates and an `INCOMPLETE` state if
any gate fails. The harness writes only local JSON records and a README, including
review records and its start/failure markers. These private records may contain
unrelocated paths and custody metadata. Their packaging state remains explicitly
**pending**; the harness creates no archive and makes no complete-handback claim.

The gate inventory now contains 26 mandatory gates and is reconciled with the
packager. The additional gates cover source category minima, source diversity,
seven-family negative controls and measured latency/RSS.

During the already authorized pass, `perf_counter` records total elapsed time
from invocation to the measurement snapshot and bounded count/total/min/max
summaries around image admission, sessions, independent ledgers, physical-call
analysis, negative units/groups and repeat comparisons. The per-unit timings
cover the named operation; total timing also includes preparation between units.
Final report serialization and packaging occur after that snapshot. Failed units
retain their count/time when the clock is available. Failure records preserve
available measurements; no measurement starts a second qualification run.

`getrusage(RUSAGE_SELF).ru_maxrss` records the Python process's lifetime high-water
RSS, including startup before the measured interval. On Darwin its raw unit is
bytes; on Linux it is KiB, converted explicitly to bytes. It is not an exact
interval peak and excludes compiler/native/Git helper child processes and the
storage-guard parent. An unavailable API, unsupported platform unit or invalid
clock/RSS result is explicit and fails the measurement gate. Algorithmic work,
encoded retained-record and streamed JSON limits do not impose a process RSS
ceiling or wall-time ceiling. The metrics do not claim such a ceiling.

A separate delivery step must export complete tracked source, retain required
licenses and root files, create a sanitized relocated evidence view, preserve
original private receipts, and obtain the applicable publication evidence. That
step also owns the complete portable ZIP and authorized cross-device delivery.
Final B12 completion requires evidence from that separate packaging operation.

The final pass charges a 512,000,000 actual algorithmic-step aggregate budget.
A private invocation-owned `CallsiteSession` is created once per image, with its
initial raw metadata/index work charged once. Calls and repeat comparisons share
that exact-image session; B4 consumes a private minted callsite capability rather
than parsing raw symbols a second time. The independent validator receives neither
session nor capability. The harness reserves 5,000,000 steps before each full
call/repeat unit, 65,536 before each changed-candidate negative, and a separately
bounded synthetic group. Insufficient reserve omits the next unit, retains its
reason, and makes the completeness gate fail. It never silently drops a family.


Capture inputs are bounded before JSON decoding: reviews and compile receipts
at 1 MiB each, source manifests at 4 MiB, and compiler indexes at 32 MiB. A lexical
preflight bounds nesting, tokens, scalar length and string length before the JSON
parser allocates containers. Parsed counts are checked before case/site scans:
at most 1,000 source cases, eight sites per case, three modes and 10,000 indexed
calls per mode. Relevant untracked source/import files also refuse final-source
identity admission.

The second compiler gate requires different canonical capture directories,
different captured compiler executable paths and different captured Swift version
identities. Each receipt's compiler command must bind its declared executable.
A copied primary capture cannot satisfy this gate merely by receiving a second
label. Existing compiler-version receipts are reused without invoking compilers.

Retained call records plus their private candidate context have a 96 MiB encoded
aggregate budget. A refused record is represented by a bounded omission summary
and makes the retention-completeness gate fail. The report writer streams with a
128 MiB cap; an overflow preserves its bounded partial and writes an explicit
incomplete summary without repeating analysis, negatives or comparisons. False
optional proof-scope flags are attacked by asserting them true, rather than
mistaking harmless omission of a false claim for invalid evidence.

Observed compiler challenges also include explicitly unsupported forms. The
confirmed-owned-target physical count stays separate from selected source
indirect-call candidates. Indexed source BLR sites receive normal bounded B5
admission and explicit dispositions; their targets are never guessed, and their
refusals are separate from the 300 mutation checks.

During the authorized final pass, each selected source caller is inspected once
from its admitted image bytes, including callers with no indexed owned call.
The bounded raw scan retains instruction PCs/words for BLR, BR, BRK, direct B
outside the function, x21 zero tests/copies/clear, and calls with a lexically later RET
without a later local x21 test. These are syntax observations and do not prove source
propagation, a handler, virtual dispatch or runtime reachability. An exact index
case with zero actual calls and zero confirmed owned targets is recorded as
unconfirmed call absence; it never proves optimization or inlining. The required
unsupported-challenge gate explicitly requires observed indirect BLR, direct
branch escape, BRK, lexical call/later-RET without an error test, and indexed owned
call absence. Missing observations remain incomplete. These gates are separate
from the ten positive replay geometry requirement.

Raw caller observations are yielded individually into aggregate retention before
the next function is inspected. The lexical call/later-RET observation explicitly
makes no reachability or propagation claim, even when an intervening branch loops.
Raw classification uses one forward pass and one reverse suffix pass; both word
passes are charged, without a call-by-return cross-product search.

The compiler-index lexical token limit is 2,000,000 within its 32 MiB byte cap;
other ordinary capture JSON uses 500,000 tokens, and reviews/compile receipts use
20,000 tokens within 1 MiB. Preload inspection is linear in these bounded input
bytes/tokens. These input limits are independent of the verification-unit work
ledger and do not initiate image analysis or regenerate compiler evidence.


Each image also receives one separate validator-owned independent raw directory
ledger, with up to 262,144 initial work steps charged once. It is created directly
from the admitted image, never from the B5 session or producer capability. Physical
calls, changed-candidate negatives and deterministic repeats share that exact
validator ledger. Standalone tiny synthetic inputs charge their own ledger work
through `accounting.image_work_charged_here`, separately from per-witness work.
The synthetic group reserves 8,000,000 steps including these initial costs.
Exception-resumption proof flags are attacked by asserting forbidden true claims;
optional descriptive unmodeled-exception text is excluded from deletion attacks.
An exception terminal may distinguish a positive geometry only after independent
validation; raw BRK observation alone remains a separate compiler challenge.


Capture metadata prerequisites are validated before the exclusive final-pass
marker. The full primary requires `indexed`, at least 420 cases and at least
1,500 distinct confirmed physical calls. The separately authorized second
compiler accepts `indexed_representative` with exactly 64 source cases, nonempty
Onone/O/Osize indexes and at least one confirmed physical call. Its representative
scope never inherits the primary's 1,500-call requirement. Both still require a
complete trusted v2 compile receipt and distinct captured compiler evidence.
The report preserves each role's admitted metadata scope and count prerequisite.


A compare/conditional challenge may occur inside a selected post-call outcome
arm even when the primary x21 zero test is CBZ/CBNZ. Measurement requires adjacent
allocated CMP (SUBS with Rd=ZR) and ordinary B.cond instructions in the same
independently checked selected arm, and records that this is distinct from the
error zero test. Prefix comparisons, reserved encodings, non-ZR SUBS and
unselected blocks cannot qualify it; no flags or branch truth is inferred.

The owned inlining-absence challenge uses exact selected-image source-callee
symbol/entry mappings plus a complete caller control-transfer inventory. Every
remaining direct call must join the independent saved index by PC, word and
target, and must not target the mapped source callee. Unrelated runtime calls
are permitted; unknown indirect/control transfers, escaping branches, incomplete
mappings or missing index matches keep absence unproven. Case-wide zero-call
counts alone no longer qualify this challenge. This reports only observed direct
source-callee call absence under owned inline intent, never its optimization cause.
The full transfer inventory adds a third linear word pass to raw caller work.

Optional `--supplemental-study` reuses an explicitly trusted private first-study
receipt (`airs.swift-broad-supplemental-study.v1`), bound to the exact frozen
current Git HEAD. The receipt is limited to 4 MiB, 200,000 lexical tokens,
48 nesting levels and eighteen distinct physical observations. It retains
refused/unresolved observations honestly. Only independently eligible rows with
complete checked identity/call/ABI/CFG/post-call/region facts may contribute
observed `nested_handlers` or `local_error_conversion` entries. Candidate
eligibility flags never grant credit. Selected image SHA metadata, call PCs,
retained words and challenge locators must agree; no hashes or byte replay occur
while reading the receipt. Rewriting trusted local receipts is outside this local
custody boundary, as with compile-v2 receipts. Core validator APIs never accept
these study receipts as proof input.

The first-study writer uses `capture='supplemental'`, retains each row's complete
`image_identity`, and computes its two-entry inventory with
`challenge_inventory(rows, [], [], capture_role='supplemental',
challenges=SUPPLEMENTAL_CHALLENGES)` after genuine nested reconciliation. Store
`observation_count=len(rows)`, source revision, the complete three-mode existing
image digest map and the actual source digest. State is `observed` only when both
inventory entries are observed, otherwise `INCOMPLETE`. The final harness rejects
inventory/count/order inconsistencies and stale revisions before its start marker.

Only these two challenge entries can merge into the required challenge inventory.
The final report explicitly labels historical first-study reuse and preserves
supplemental capture evidence for packaging. Supplemental observations never
increase primary declaration/witness/family/ABI/geometry/lowering counts or
second-toolchain counts. They are not rerun during final qualification.
