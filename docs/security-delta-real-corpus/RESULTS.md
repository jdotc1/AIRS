# Track A execution ledger

Baseline: `0b192429cbfb5583557c4c5f04017b1946141e4a`; macOS 27.3 build
26C5035r; Apple Swift 6.4.2 (swiftlang-6.4.2.1.9, clang-2100.4.1.1);
ARM64 host, package deployment macOS 14. Historical START_HERE.md and
VERIFICATION.md are absent from the active checkout; current delta contracts
were read instead. Existing component-delta tests and build 26 qualification
remain accepted within their original scope, without blanket reruns.

## A1 protocol progress

- RED: new manifest test module failed import because the harness did not exist.
- GREEN: initial nine schema/semantic cases passed (0.006 seconds).
- RED: precise invalid raw UTF-8 code and ancestor-symlink escape tests failed.
- GREEN: all 11 manifest methods passed (0.006 seconds; exit 0), after separating
  UTF-8/depth refusal codes and adding descriptor-relative directory traversal.
- Command: `python3 -B -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -v`.
  Runs were supervised by the shared storage guard. Changed inputs were only the
  new corpus protocol/tests. The final full run covered both changed shared
  admission functions; accepted unchanged AIRS tests were not repeated.
- Native baseline checks: pending shared build-root availability; the native Swift
  UI owner currently reserves it. No native test is claimed by these Python runs.

## Current denominators

Authentic pairs acquired/adjudicated: 0/24 requested; applications: 0/12;
publishers: 0/3. These are pending work, not acceptance or source blockers.
No real bundle analysis, oracle, archive replay, native corpus workflow, stress
qualification, or independent Track A adversarial round has run yet.

## A2 acquisition and owned guards

Acquired and admitted 47/47 original official release ZIPs, yielding 35 distinct
chronological pairs from 12 applications and 10 publisher accounts. Downloaded
290,903,043 bytes; extracted 684,656,550 bytes. No source digest was duplicated
within a pair. Payloads are local-only; 35 manifests contain actual URLs, hashes,
license provenance and exact app paths. Oracle expectations remain pending.
Applications: Maccy, Ice, SwiftBar, KeyCastr, xbar, KeepingYouAwake, KnockKnock,
QLMarkdown, AltTab, Pearcleaner, OverSight and TaskExplorer. OverSight's selected
bundle is the publisher's installer app; it is inspected as data and never run.
Pearcleaner records Apache-2.0 with Commons Clause; its payload is not redistributed.

Owned archive tests: initial nine methods passed, then a Unicode-directory
collision test failed on APFS (two exact names silently merged). Inode-to-exact-
path tracking corrected the extraction layer; all ten affected methods passed
(0.013 s, exit 0). Two new transfer methods passed (0.003 s), proving one streamed
hash, no destination replacement, size/digest refusal and pre-transfer cancellation.
A new pre-network budget test failed and passed after moving size validation before
process creation (0.001 s). Only relevant changed/new checks ran.
Commands use `python3 -B -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py`
with focused `-k` selectors for later independent helper changes. All are owned
fixtures; none counts as authentic-pair analysis acceptance.

## A3 oracle progress

Eight owned raw-byte methods passed after a missing-module RED run (0.001 s,
exit 0): typed Boolean/integer/order, raw integer representation uncertainty,
empty/malformed privacy data, duplicate loader sequence, raw subtype bits, fat
slice/UUID provenance, malformed signature versus absence, and truncated input.
Command: `python3 -B -m unittest discover -s tests -p test_security_delta_independent_oracle.py -v`.
No real application binary has been decoded by this oracle yet.

A3 continued: bounded independent bundle traversal, explicit privacy presence,
Unicode failure classification, byte-work accounting and retained-output refusal
were added. The affected oracle run passed 12 methods and skipped one physical
invalid-UTF8 filename fixture because APFS refused constructing it (EILSEQ);
an injected invalid-name case passed separately. New Apple-tool agreement and
mismatch preservation passed (1 method); atomic no-overwrite evidence publication
passed after a missing-helper RED (1 method). These tests do not use AIRS parsing.
Evidence logs: A3-bounded-oracle-green, A3-work-green, A3-tools-green,
A3-atomic-red/green in the private task evidence directory.

Jeff approved one bounded 47-release/35-pair qualification pass plus 100 pure
retained-input replays. Raw oracle capture started; capture results will be
reported separately from adjudication. No third-party application is executed.

## Capture, replay and repair receipts

First authorized pass: 47/47 independent raw captures, 35/35 AIRS captured pairs,
35/35 retained delta archives, 100/100 pure deterministic replays on five distinct
retained cases, and 35/35 fresh-invocation historical replays. Native capture test:
19.966 s; historical replay test: 4.814 s. Outer command wall times: 22.63 s and
7.59 s. Outer Swift-driver RSS was ~77 MB; this does not measure combined child
process peak. Oracle peak RSS was 521,994,240 bytes; summed per-source time 6.53 s.
No inspected app was launched.

New selectors:
`SecurityDeltaRealWorkflowTests.testDriverRequiresDistinctSidesAndBoundedCases`
(1 passed after missing-driver RED),
`SecurityDeltaRealWorkflowTests.testAuthorizedAuthenticCaptureAndPureReplay`
(1 passed, 35 cases/100 replays),
`SecurityDeltaRealWorkflowTests.testFreshInvocationHistoricalReplay`
(1 passed, 35 archives),
`SecurityDeltaRealWorkflowTests.testHarnessNeverReplacesEvidenceAndBoundsReads`
(1 passed, 0.006 s),
`SecurityDeltaRealArchiveAcceptanceTests.testSeventeenOwnedArchiveMutationsRefuse`
(1 passed after classified-error RED), and
`SecurityDeltaRealArchiveAcceptanceTests.testOptInAuthenticArchiveTamperingRefuses`
(1 passed, 17/17 refusals, 1.551 s).
These use focused `swift test --package-path native --filter ...`; already-built
corpus/replay/tamper invocations use `--skip-build`. Missing opt-in artifacts raise
XCTSkip in ordinary CI and do not count as authentic passes.

Forty newly named owned mutation methods passed (0.007 s), after four manifest
admission failures. Additional targeted regression methods cover review repairs.
Two independent adversarial source reviews and repair records are separate files.
The real AIRSApp product was compiled by the native test builds. No release build,
installation, signing, notarization, download or MacScope operation occurred.

Checker v4: 35 cases; 2,459/3,837 source observations supported, 1,378 unresolved,
0 disagreements in the supported subset. Finding constituent support: 846/1,424;
578 unresolved. Independently enumerated expected changes: 761/1,368 true positives,
607 unresolved, 0 false negatives in that enumerated scope. These are provisional
until the remaining requested raw fields and final review closure are recorded.
Earlier v1 dependency disagreements were checker count-versus-array mistakes;
a new owned regression corrected the checker, without changing AIRS semantics.

Visible native observation so far: one authentic historical Pearcleaner comparison
opened via Open Report, Components and Security Changes switched, previous→current
arm64 direction and partial scope visible, correlated Info version/digest finding
selected, previous String 5.4.0 inspected. This is one visible historical case,
not five live pair-selection/capture workflows. No screenshot containing local
file-picker paths is included publicly. Remaining native gates are still open.
