# AIRS roadmap

This file says where AIRS is going and why. It is rewritten when the plan changes.
The dated checkpoints that used to follow it are in
[ROADMAP_HISTORY.md](ROADMAP_HISTORY.md), unchanged. Plans describe intended work;
acceptance records establish completed scope. Source-only increments do not replace
installed apps.

Written 2026-11-12 against main at commit f5eefd5.

## 1. Where things stand

**Released.** AIRS 0.3.4, build 32 (tag v0.3.4-build32, application source db7347b),
signed, notarized and stapled for Apple silicon. It includes Security Changes in
Component Review and native Standard and Broad Swift analysis with the explicitly
selected extended scan profile. See [RELEASE_0_3_4_BUILD32.md](RELEASE_0_3_4_BUILD32.md)
and [RELEASE_NOTES.md](../RELEASE_NOTES.md).

**Merged and not released.** Twenty-one pull requests have merged since build 32. None
is in a released build.

- Swift: the `broad-imports-v1` profile
  ([SWIFT_BROAD_IMPORTS_PROFILE.md](SWIFT_BROAD_IMPORTS_PROFILE.md)), a declaration
  grammar for imported callees
  ([SWIFT_IMPORT_DECLARATIONS.md](SWIFT_IMPORT_DECLARATIONS.md)), native admission of
  the imports profile ([NATIVE_BROAD_RESULTS.md](NATIVE_BROAD_RESULTS.md)), and the
  engine-only `broad-imports-got-v1` profile
  ([SWIFT_IMPORT_GOT_ATTRIBUTION.md](SWIFT_IMPORT_GOT_ATTRIBUTION.md)).
- ARM64/CFI: `arm64-bounded-extract-class-v51` ([EXTRACT_CLASS.md](EXTRACT_CLASS.md))
  and a decode-oracle differential harness
  ([ARM64_ORACLE_HARNESS.md](ARM64_ORACLE_HARNESS.md)).
- Native application: a fix for a save race in the batch history store, analysis reuse
  pinned to the engine's current model with a symlink containment fix, and path
  comparison that no longer depends on how a path is spelled
  ([PATH_ALIASES.md](PATH_ALIASES.md)).
- Process: the Source verification workflow on every pull request and on main, the
  publication gate in CI, and slow type-check reporting in the local build.

**Verification.** `.github/workflows/verify.yml` runs the Python tests on Python 3.11
and 3.15 and the Swift build and tests on a hosted Apple silicon runner. Hosted results
are on the repository's Actions page. Publication gates are described in
[PUBLICATION_POLICY.md](PUBLICATION_POLICY.md).

## 2. What the first real-input measurements showed

Until 2026-11-12 the work after build 32 was chosen and checked on owned fixtures of a
few dozen symbols. Two measurements made that day are the reason this plan changed.

### Swift profiles on one real application

Maccy 2.8.0 (the release archive recorded in
[the real-application corpus](security-delta-real-corpus/CASE_MATRIX.md); ARM64 slice,
393,880 instruction words, 55,863 call instructions), engine source at f5eefd5. The
binary was read as data and never executed.

| Profile | Candidates | Retained | Omitted by the 8,192-row limit | Rows still unresolved |
| --- | ---: | ---: | ---: | ---: |
| `broad-extended-v1` | 5,263 | 5,263 | 0 | 5,263 |
| `broad-imports-v1` | 12,690 | 8,192 | 4,498 | 8,192 |
| `broad-imports-got-v1` | 11,241 | 8,192 | 3,049 | 8,192 |

- The imports profile attributed all 1,219 stubs, set aside 23,615 calls to non-Swift
  imports, and skipped 3,145 calls to Swift imports whose declaration it could prove
  non-throwing. That part works.
- Of the 5,123 retained rows for imported Swift callees, the declaration grammar
  admitted 4. The declines are generic requirements (1,742), substitutions the grammar
  does not know (1,679), unsupported productions (1,129), protocol contexts (438) and
  four smaller classes (131).
- The GOT profile attributed 1,449 of 3,200 candidates, all non-Swift. Of its 1,751
  declines, 1,746 have one reason, `got_base_not_adrp`.
- With either imports profile the row limit is exceeded and thousands of rows are
  omitted.
- Every row a reader sees is still marked unresolved.

The profiles are sound on their fixtures, and on this application they barely change
what a reader of the report learns. The grammar was grown from a fixture whose symbols
are simpler than the symbols of a real application, where substitutions and generic
requirements are the normal case.

### The decode oracle

The first full run of the oracle harness compared the two ARM64 decoders with 34,761
distinct instruction words of independent disassembler output. It found no blocking
disagreement, and it took less than one second of CPU time. The decoders claim about
5% of those words (1,875 for the CFG decoder) and decline the rest by scope. Six
instruction kinds the CFG decoder supports never reach agreement in the vectors, so
the run says nothing about them yet. See
[ARM64_ORACLE_HARNESS.md](ARM64_ORACLE_HARNESS.md).

### What was already known and not acted on

The security-change comparison is the only lane with a real corpus behind it: 35
release pairs of 12 applications. On that corpus it reported 767 of 1,374 independently
enumerated changes with no false negative in the enumerated scope, and left 607
unresolved ([RESULTS.md](security-delta-real-corpus/RESULTS.md)). It is also the feature
a user of the released application sees first. It received no work after build 32.

## 3. What changes

1. **Real inputs set the order of work.** The 12 applications of the real-application
   corpus are the measurement panel for every lane. A change to an analysis model
   reports its panel counters before and after. Counts rank the work; they are still
   not prevalence, and an extension still needs an owned example with an independently
   derived expectation before it is admitted.
2. **Component review comes first.** It is the released feature with measured value
   and a measured gap.
3. **Merged work is released.** Twenty-one merged pull requests with no release is a
   queue, not progress. The next release carries all of them, and later releases
   follow milestones instead of accumulating.
4. **One system floor.** The minimum system is macOS 27 from the next release (a
   maintainer decision of 2026-11-12). The declared target was macOS 14, which no test
   ever ran on. With one floor, the development host, the hosted runner and the
   declared minimum are the same major system, and the minimum-system gate can be
   closed with evidence.
5. **A machine makes the check where a machine can.** Release acceptance on a freshly
   provisioned hosted runner replaces the wait for a spare Mac. The decode oracle runs
   in CI. Registries kept by hand in two languages are generated from one source.
6. **Profiles stop multiplying.** There are five named broad Swift profiles, each a
   superset of another, and a reader has to choose among them. New semantics still
   get a new model identity. They do not get a new profile name.
7. **A lane that does not move the panel stops growing.** Section 4.3 and section 4.4
   each carry a stop rule.

## 4. Plan

Order within a section is the order of work. Sections 4.1 and 4.2 come before the
others.

### 4.1 Release 0.4.0

The next release is 0.4.0: the first with the macOS 27 minimum, carrying everything
merged since build 32.

1. Done: the deployment target in the package manifest and the bundle is macOS 27,
   and the native CI job runs on the hosted macOS 27 image with Xcode 27.2 (the
   label is `xcode-27`, marked preview on 2026-11-12; if it is renamed the job
   moves with it). The Python jobs are unchanged.
2. Add a release-acceptance workflow, started by hand for a release tag. On a fresh
   hosted macOS 27 runner it downloads the published archive, checks it against the
   published checksums, checks the signature, the notarization ticket and the
   Gatekeeper assessment, runs the bundled interpreter and engine on the owned
   fixtures, and compares the counters with the expected files. Its record is the
   clean-machine and minimum-system evidence for that release, with its limits
   stated: no person, no browser download, no network isolation.
3. Freeze the source, package, and probe the bundled engine.
4. Maintainer: sign, notarize, staple, tag and publish.
5. Run the acceptance workflow on the published archive and record the result in the
   release document.

Exit: a published 0.4.0 whose release document cites a green main run on the exact
commit and a green acceptance run on the published archive.

After 0.4.0, each milestone below that changes what a user sees ends in a release.

### 4.2 Component review and security changes

1. Break the 607 unresolved expected changes of the corpus down by reason, and take
   the largest class that has an owned example. Exit for each class: its corpus count
   moves, with no new false positive and no false negative in the enumerated scope.
   State: the per-change records of the recorded run were not kept, so the split
   cannot be read from what exists. The evaluator now records the ground for each
   unresolved row and totals them per case and per run. One of the four grounds is
   "the report has no observation for that component and category", which may hide
   misses; the first thing the split has to show is how many of the 607 it accounts
   for. The recorded run that produces the split has not been made.
2. Activate in the application the manual finding pairs and the coverage triage that
   the engine and the native validators already support.
3. Cross-build review candidates beyond exact-body matching (CFG fingerprints,
   call-graph propagation) stay research until item 1 has run out of cheaper classes.
   Structural matches never replace exact image identity or model checks.

### 4.3 Swift error flow

1. **Panel measurement.** A workflow started by hand that fetches each panel input
   from its publisher by recorded digest, never executes it, runs the profiles and
   publishes the counters. Exit: a table like the one in section 2 for all 12
   applications.
2. **No silent truncation.** Rows beyond the retention limit are summarized by reason
   in the report. Exit: the Maccy measurement has no omitted row without a reason
   count.
3. **A complete declaration grammar.** Parse every function-entity mangling,
   including substitutions and generic requirements, instead of adding productions one
   at a time. Check it differentially against the toolchain's demangler over every
   imported Swift symbol name in the panel. Exit: no symbol the grammar admits as
   non-throwing that the demangler shows as throwing or async, and the admitted share
   reported (today 4 of 5,123 on Maccy).
4. **GOT candidate screen.** Explain `got_base_not_adrp`. In the owned fixture the
   four declines with this reason are value-witness calls. If the same holds on the
   panel, which nobody has checked, these are table calls and not GOT loads, and they
   leave the GOT candidate count.
5. **What turns a row into a result.** Two designs to examine, in this order, each
   needing a contract, an owned example and an independent expectation. (a) Evidence
   at the call site itself: what the caller does with the error register after the
   call, reported as a fact about the caller and with no claim about the callee. The
   first step is to read what the existing edge model already records at such sites.
   (b) ABI admission for imported callees from a complete declaration parse.
6. **Indirect calls.** A census of how the 5,263 unresolved indirect targets on Maccy
   are loaded (value witness, protocol witness, class table, closure context) before
   any design.

Items 2 to 5 land in one second-generation broad profile whose report lists its
capabilities and limits. The five existing profile names stay admitted and
byte-identical.

Stop rule: if items 3 and 5 are done and nearly every panel row is still unresolved,
no further Swift profile work is scheduled, and the lane is maintained as it is.

Still separate and not scheduled: Swift-frontend emission and runtime qualification
for the CMP-based layouts, wider success arithmetic, async continuation
reconstruction.

### 4.4 ARM64 unwind

1. **The oracle in CI.** Generate the vectors on the runner with its own LLVM tools
   from a deterministic word list, so no third-party vector file is stored. Until
   then the harness is run locally before any decoder change.
2. **Close what the first run left open.** Explain the six kinds that never reach
   agreement. Correct the refusal reason for valid FEAT_PAuth_LR words, which are
   declined as invalid encodings where unsupported-instruction is accurate. No path is
   wrongly accepted today.
3. **Panel audit.** Run the unwind audit over the panel and rank refusal reasons by
   the number of functions each one blocks.

Stop rule: an instruction family is added only when item 3 shows it blocks functions
in the panel. The families added in versions 42 to 50 were chosen without such a
ranking. Until the ranking exists the chain is treated as complete.

### 4.5 Native application

1. Swift 6 language mode for the core module. The batch-history save race was a real
   concurrency defect that CI found by chance on an unrelated change; the compiler's
   data-race checking is the systematic version of that.
2. Replace the vendored design-system snapshot, which dates from the macOS 14 floor
   and carries 11 local workaround rows (`native/LUMEN-GAPS.md`), with a current
   upstream release, and delete the workarounds it makes unnecessary. Record the
   upstream commit and its licence.
3. Keep the engine at most one capability ahead of the application. The GOT profile
   is engine-only today; its successor in section 4.3 is admitted natively before
   another engine-only capability is added.
4. Generate the Python and Swift model registries from one file, so that parity is a
   build fact and not a test that has to be amended by hand.
5. Qualify changed user interactions: picker suppression and historical-panel GUI
   acceptance for settled project companions remain incomplete.

### 4.6 Interchange

A facts exporter for the MacScope navigator contract is written and reviewed and is
not published. It will pin the contract by content digest and will not carry a copy
of it. Publication waits on a maintainer decision about the licence of the contract
files. Porting notes continue with each released model
([PORTING_SWIFT_IMPORTS_TO_MACSCOPE.md](PORTING_SWIFT_IMPORTS_TO_MACSCOPE.md)).

### 4.7 Documentation and identity

1. Rewrite README.md as an introduction: what AIRS does, what it never does, how to
   install it, what it requires and what its results do not establish. Its build
   history moves to the release documents.
2. One version identity. The application is 0.3.4 and the Python package and engine
   report 0.3.3. First read whether any validator pins the generator version; the
   preferred result is one version source read by the package, the engine and the
   application.
3. [DEVELOPMENT_STATUS.md](DEVELOPMENT_STATUS.md) opens on build 12 and
   [ARCHITECTURE.md](ARCHITECTURE.md) on an earlier model. Each gets a current
   opening or a pointer here.
4. ANALYSIS_CONTRACT.md cites 79 pages that were never in this repository. Both it
   and ARCHITECTURE.md say so in an opening note. This is closed by disclosure, and no
   page will be restored.

## 5. Not planned

- Systems older than macOS 27, and qualification on a macOS 14 virtual machine.
- Intel-host qualification of the application, which is built for Apple silicon only.
- Executing, loading or instrumenting an inspected binary. This is a property of the
  tool, not a deferral.
- Full source reconstruction and general decompilation.
- New named Swift profiles, and instruction families without panel evidence (section
  3, items 6 and 7).

## 6. Rules that do not change

- Unknown never becomes agreement. Unresolved items stay in the denominator.
- New semantics need a new model identity, separate positive and refusal evidence,
  review by someone who did not write the change, and exact admission in the Python
  and native validators. Historical identities stay distinct.
- Choose a semantic extension from an explicit owned example with an independently
  derived recovery expectation. Reason frequency in supplied reports is prioritization
  input, not representative prevalence or permission to widen support.
- No release is described as fully qualified while a release gate in
  [CURRENT_SOURCE_RELEASE_GATES.md](CURRENT_SOURCE_RELEASE_GATES.md) is open.

## 7. What only the maintainer does

Signing, notarization, tagging, publication and installation of a release; repository
settings such as branch protection and required checks; deleting branches; and
decisions about publishing material derived from other repositories.
