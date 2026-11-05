# Track A real-application qualification results

## Source and environment

Baseline: `0b192429cbfb5583557c4c5f04017b1946141e4a` (reviewed build 26 source).
Implementation branch: `codex/track-a-real-security-delta`. Milestone commits:
`03b8873` protocol, `9996ffd` acquisition/manifests, `cd28aa3` independent oracle,
`38e886d` capture/replay/adjudication and review repairs. The final scoped commit
is identified by the handback manifest; this file does not claim a self-referential
commit identity.

Qualification host: macOS 27.3 (26C5035r), MacBookPro18,2, Apple M1 Max, 64 GiB RAM,
ARM64. Apple Swift 6.4.2 (swiftlang-6.4.2.1.9 / clang-2100.4.1.1), SwiftPM tools
5.9, deployment target macOS 14. Owned Python test invocations used Python 3.13.16;
entry adapters also ran with Apple Python 3.9.6. This is one development host,
not macOS 14, clean-machine or installed-release acceptance.

The composed method ledger records **124 unique methods: 123 passed and one explicitly skipped**. Its 106 recorded invocations include RED/GREEN development, builds and reporting operations; this is not a claim that 106 suites passed. Accepted unchanged checks were reused, not replayed as a final broad suite.

## Corpus and denominators

| Gate | Requested / attempted population | Observed result |
| --- | --- | --- |
| Authentic pairs | At least 24; 35 attempted | 35 acquired/captured; 35 distinct changed primary image digests |
| Applications | At least 12 | 12 original publisher application bundles |
| Publishers | At least 3 | 10 publisher accounts |
| Releases | 47 distinct source releases | 47/47 ZIP acquisitions admitted |
| Raw image/candidate population | 300 records | 278 observed images; 22 unavailable candidates, never promoted to executables |
| Independent selected facts | 35 manifests | 210 source-qualified Info facts plus raw language witnesses |
| Certain observations | 3,361 of 3,837 total observations | 3,361 supported; 0 source disagreements; 476 explicitly unresolved/declined by AIRS |
| Certain findings | 948 of 1,424 total findings | 948 source/rule-supported; 0 unexplained certain false positives; 476 bounded coverage findings |
| Independent expected changes | 1,374 enumerated changes | 767 true positives; 607 unresolved; 0 false negatives in this enumerated scope |
| Historical exports | 35 qualifying original captures | 35/35 exported and reopened in a fresh invocation |
| Deterministic pure derivation | Five retained cases × 20 | 100/100 byte-identical report encodings |
| Archive corruption | 17 mutations × two contexts | 0/34 accepted; 17 owned and 17 on one authentic retained archive |
| Visible historical UI | Five selected cases | 5/5 opened with direction, scope and historical authority visible |
| Live UI workflow | One separately approved real pair | 1/1 selection→capture→inspection→export→historical reopen completed |

All 35 pairs have different retained primary-container digests, so none is counted
only because its ZIP metadata/compression changed. Independent recaptures are
separate observations with new UUIDs, not additional release pairs. Prereleases
keep their actual tags. OverSight is its authentic installer application, inspected
as data and never launched or installed.

Language evidence combines repository language byte counts with raw primary-image
Swift/Objective-C metadata section witnesses. Maccy and Ice corroborate the Swift
cohort; KeyCastr and KeepingYouAwake corroborate Objective-C/mixed. Other apps add
variety. This does not measure runtime language proportions.

### Strata

| Stratum | Minimum attempted cases | Actual attempted/observed cases |
| --- | ---: | --- |
| Primary executable | 6 | 35 |
| Framework/dylib | 6 | 24 |
| Service/extension/helper/login-item | 4 | 22 |
| Universal/multiple slices | 4 | 35 |
| Entitlement change or unavailable source | 6 | 35 primary attempts; 2 actual change cases plus 4 distinct first unavailable-helper cases = 6 |
| Privacy presence/absence/change | 4 | 35; no compliance inference |
| Loader/dependency | 4 | 35 examined; 18 actual change cases |
| Signature/source digest | 6 | 35 primary capture pairs with changed container digests |

The four helper eligibility outcomes are `source_unavailable`, not empty or absent
entitlements. They refused before the reader because no usable captured Info
baseline existed. Earlier unexamined records remain preserved. Complete per-case
versions, source SHA-256 values, licenses, paths, selected facts, counts and tags
are in the case manifests and CASE_MATRIX.

The false-negative denominator covers independent exact-location paired Info keys,
present privacy keys, recorded loader groups and raw digest/signature observations.
Unsupported/missing sources remain unresolved. It does not enumerate every possible
application behavior, dependency resolution or unsupported DER/date interpretation.
Finding qualification checks constituent source facts, required references,
category/disposition triggers, exact component grouping, recorded physical ancestry
and strict repeated transitions. It establishes no causation or runtime behavior.

## Executed focused checks and receipts

The composed method ledger and actual command index are `METHOD_RECEIPTS.json` and
`EXECUTION_INDEX.md`. They distinguish fresh checks, development RED failures,
corrections, skips and exact outer job status where recovered. Runner times are
not substituted for process wall times. The ledger has one physical invalid-UTF8
fixture skip because APFS refuses constructing it; the injected invalid-name case
passed. Forty newly named owned mutations are distinct from authentic cases.

Representative actual invocations:

```sh
python3 -m unittest discover -s tests -p test_security_delta_corpus_manifest.py -v
python3 -m unittest discover -s tests -p test_security_delta_corpus_acquisition.py -v
python3 -m unittest discover -s tests -p test_security_delta_owned_mutations.py -v
swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testAuthorizedAuthenticCaptureAndPureReplay
swift test --package-path native --skip-build --filter SecurityDeltaRealWorkflowTests.testFreshInvocationHistoricalReplay
swift test --package-path native --filter SecurityDeltaRealArchiveAcceptanceTests.testSeventeenOwnedArchiveMutationsRefuse
swift test --package-path native --skip-build --filter SecurityDeltaRealArchiveAcceptanceTests.testOptInAuthenticArchiveTamperingRefuses
swift test --package-path native --filter SecurityDeltaRealResourceTests.testOwnedMaximumInventoryAndLoweredOutputCapsWithProcessMetrics
swift build --package-path native --product AIRSApp
```

The original authentic capture method passed in 19.966 s; fresh historical replay
in 4.814 s; authentic tampering in 1.551 s. Outer capture/replay command wall times
were 22.63/7.59 s. Four first helper captures passed in 1.424 s. The unavailable
helper guard and affected existing changed-Info regression passed; a later reader
trap made reader bypass explicit. The original-disappearance owned fixture passed
in 0.037 s. The real AIRSApp product built after the layout correction in 6.32 s
and after the refusal correction in 0.46 s, reusing compiled changed modules.

No broad `verify-macos.sh`, Python engine suite, accepted unchanged signing/source
hash gate, or duplicate corpus download was run for handoff. Existing legacy value,
archive, matching, cancellation, resource and native job-state receipts are reused
at their unchanged boundaries. ADVERSARIAL_MATRIX identifies those selectors.
The public reproduction wrapper has three planning checks, an owned mocked-network
end-to-end check, and an unsupported-architecture-before-network check. Authentic
redownload through that new wrapper was not run; original acquisition receipts
remain authoritative.

## Resource and latency observations

- ZIP acquisition: 290,903,043 bytes; expansion: 684,656,550 bytes. Original sources
  remain local, unmodified, unexecuted and unredistributed.
- Initial independent raw oracle: 47/47 captures, 6.53 summed per-source seconds,
  process peak RSS 521,994,240 bytes. This includes transient source buffers and
  runtime allocation, not just retained fact bytes.
- Later explicitly approved recorded-range capture: 1,593,648 read bytes, 0.7942
  summed seconds, 278 observed images/22 previously unavailable candidates left
  unexamined. No original archive/container digest was recomputed. Raw ranges,
  first range digests, header/fat/CPU/UUID checks and separate capture time remain
  local. They are non-atomic later observations.
- Outer native Swift-driver RSS was approximately 77 MB; it is not the test-child
  memory peak. A separate fresh owned 128-component ceiling case measured the
  test process directly: peak RSS 25,886,720 bytes; elapsed 0.031357084 s;
  allocator in-use 933,808 bytes; reserved 46,137,344 bytes. The allocator's
  high-water counter returned 0 and is **unavailable as a peak measurement**, not
  evidence of zero allocations. Process/runtime overhead is included.
- That owned case retained 100/100 allowed observations and 20/20 allowed findings,
  disclosed omissions and refused 129 combined components with `component_limit`.
  Hard component/tree/value/reference/export limits remain unchanged. Paging is
  200 rows; KeyCastr's 224 observations visibly used two pages.

Work/retention limits are not a process RSS guarantee. Exact peak heap allocations
and long-duration leak profiling were not established by the available counter;
this record does not substitute an unapproved repeat instrumentation pass.

## Native observations

A local unsigned development wrapper ran the built AIRS executable. Five authentic
historical comparisons were inspected: Pearcleaner, TaskExplorer, QLMarkdown,
KeyCastr and Maccy. Observed controls included previous→current arm64 direction,
complete/partial scope, exact component/category filters, Findings/All observations,
Components/Security Changes navigation, typed String 5.4.0, source UUID/key locator,
retained source-byte paging, non-atomic capture wording and the second observation
page. The first inspection exposed a squeezed inspector; bounded list/detail widths
corrected it and the new view was visibly readable.

A separately approved Pearcleaner 5.4.0→5.4.1 live run confirmed direction before
reads, explicitly captured previous/current entitlements and signatures, showed
absent→absent entitlement presence, exported the full report despite presentation
filters, and reopened it as historical evidence: 40 findings/149 observations,
partial coverage, no live authority. The owned development host responded to Quit.
A bounded own-process error/fault log query completed with no matching records.

The subsequent helper-refusal correction was qualified by fresh focused native
checks and the real-target build. The unchanged visible-view receipt is reused;
no installed final-source acceptance or new signed/notarized build is claimed.
No inspected application was launched. No accessibility, OS permission, security
setting, source bundle or installed release was modified.

## Reviews, corrections and remaining gates

Both independent adversarial rounds and repairs are documented separately. They
found malformed plist references, signature ambiguity/magic, uncharged read work,
unbounded enumeration, weak fact admission, provenance/rule-trigger gaps, privacy
owner/denominator errors, late architecture refusal and overwriting evidence.
Targeted regressions corrected these. A narrow production delta error translation,
a capture refusal distinction and the inspector width fix are the only production
behavior/layout changes. No analyzer semantic rewrite or legacy format change was
introduced. Earlier checker disagreement counts were checker errors and are
preserved as development evidence, not relabeled engine failures.

Open environmental/authorization gates:

- **BLOCKED:** no approved read-only external app volume was available. Internal
  Time Machine snapshots are not treated as an authorized external application
  volume. Next step: provide an authorized read-only external test source/run.
- **NOT RUN:** clean-machine, macOS 14 runtime, Intel host and installed-release
  acceptance. Next step: separately provision/authorize those environments.
- **NOT RUN:** actual OS permission-revocation race, real blocking inside
  Security.framework and a real >limit app export. Owned injected failure,
  cancellation/settlement and export-limit receipts remain separate coverage.
- **NOT RUN:** precise heap-peak/leak profiling; the allocator counter did not
  provide a useful peak. A repeated instrumented run requires specific approval.
- **DEFERRED:** MacScope integration/acceptance. No MacScope code was changed.
- **DELIVERY:** the complete source handback ZIP is kept local; no third-party
  upload or public application release is implied.

These gates are not passes. The achieved bounded corpus acceptance does not claim
that entire applications are unchanged, safe, compliant, trusted or behaviorally
characterized. The original release remains unchanged. Packaging identity, ZIP
SHA-256 and final source commit are supplied in the handback manifest.
