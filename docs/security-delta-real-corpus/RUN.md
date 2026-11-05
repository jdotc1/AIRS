# Reproducing Track A without granting historical authority

Use a macOS ARM64 host and the repository's accepted SwiftPM dependencies. Record
macOS, SDK, Swift and hardware identity before new qualification. A future replay
is a new explicitly authorized run; do not rerun existing sealed receipts merely
because this document provides commands. Ordinary CI does not download apps.

The committed case manifests are metadata, expected selected facts and hashes.
They contain no third-party application payloads. Review publisher licenses and
select an owned local Developer output root. Keep the entire cache private.
`security_delta_prepare.py` is a separate opt-in orchestrator so production
analysis and the common manifest validator have no network entry point.

## Owned checks

The new Python modules use only the standard library. Owned temporary fixtures
create their own ignored directory in a clean checkout and remove their temporary
contents. Focus selectors on changed boundaries; the execution index records
which checks were actually run for this implementation.

```sh
python3 -B -m unittest discover -s tests -p 'test_security_delta_*.py' -v
swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testDriverRequiresDistinctSidesAndBoundedCases
swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testHarnessNeverReplacesEvidenceAndBoundsReads
swift test --package-path native --filter SecurityDeltaRealArchiveAcceptanceTests.testSeventeenOwnedArchiveMutationsRefuse
```

The wildcard above describes the portable owned gate; this implementation reused
accepted individual receipts and did not indiscriminately replay that entire set.
Opt-in native methods raise XCTSkip when their explicit environment input is
absent. A skip is not an authentic case pass.

## First acquisition on a new approved root

```sh
python3 -B scripts/security_delta_corpus.py --check-manifests docs/security-delta-real-corpus/cases
python3 -B scripts/security_delta_prepare.py --manifests docs/security-delta-real-corpus/cases --output "$AIRS_OUTPUT_ROOT" --plan-only
```

`AIRS_OUTPUT_ROOT` must be an explicitly selected local root. On an installation
with the shared storage guard, run writing operations through its registered
entry adapter, for example:

```sh
storage-guard run --entry scripts/security_delta_prepare.py -- --manifests docs/security-delta-real-corpus/cases --output "$AIRS_OUTPUT_ROOT"
```

The acquisition command uses authenticated `gh` only for public publisher asset
metadata and bytes. It binds source IDs, canonical release URLs, size and expected
SHA; streams one first hash per archive; excludes external symlinks and unsafe ZIP
names; preserves legitimate internal symlinks; never executes apps or recursively
unpacks nested archives. It refuses unsupported architecture before network/output.
Version 1 qualification comparisons support arm64; other slices remain raw evidence.

The command creates `security-delta-real-corpus` beneath the selected root. Existing
corpora are preserved and refused. Do not delete or rehash a completed corpus just
to use this wrapper. Resume using its retained receipts and explicit host authority;
a saved receipt never becomes a live descriptor capability. Individual source
records survive a partial preparation; incomplete preparation is not a pass.

The original qualification used the same bounded APIs through an earlier explicit
batch adapter. This new wrapper's planning and owned mocked-network end-to-end
paths ran; authentic redownload through it was not run.

## Explicit native capture and historical replay

After separately authorizing the corpus run and reserving the shared build root:

```sh
export AIRS_REAL_CORPUS_DRIVER="$AIRS_OUTPUT_ROOT/security-delta-real-corpus/capture-driver-v1.json"
swift test --package-path native --filter SecurityDeltaRealWorkflowTests.testAuthorizedAuthenticCaptureAndPureReplay
unset AIRS_REAL_CORPUS_DRIVER
export AIRS_REAL_CORPUS_REPLAY="$AIRS_OUTPUT_ROOT/security-delta-real-corpus/capture-driver-v1.json"
swift test --package-path native --skip-build --filter SecurityDeltaRealWorkflowTests.testFreshInvocationHistoricalReplay
unset AIRS_REAL_CORPUS_REPLAY
```

The first method uses existing AIRS capture operations, explicitly selects at most
one recorded app component per side, and performs 100 pure retained-input replays
across five cases. It publishes fresh source archives, reports, inventories,
declarations and a ledger. The second method runs in a fresh invocation, checks
byte-identical historical output/evidence resolution and rejects live authority.
Those operations are not visible UI acceptance; inspect the native journey
separately. Independent recaptures produce new UUIDs and capture times.

Additional first helper-source qualification uses the explicit
`AIRS_REAL_CORPUS_HELPERS` driver and
`SecurityDeltaRealWorkflowTests.testFirstAuthenticHelperEntitlementCaptures`.
It selects four named cases/one previously unexamined helper each, recording
unavailable eligibility outcomes as separate immutable archives. It neither
fabricates empty dictionaries nor modifies the original reports. Do not repeat
it over an already captured revision without authorization.

A retained real archive can be selected through `AIRS_REAL_CORPUS_TAMPER` for
`SecurityDeltaRealArchiveAcceptanceTests.testOptInAuthenticArchiveTamperingRefuses`.
The method applies 17 owned mutations in memory; original evidence is preserved.

## Independent adjudication

```sh
storage-guard run --entry scripts/security_delta_case_evaluator.py -- \
  --manifests docs/security-delta-real-corpus/cases \
  --cache "$AIRS_OUTPUT_ROOT/security-delta-real-corpus" \
  --sources "$AIRS_OUTPUT_ROOT/security-delta-real-corpus/acquisitions.json" \
  --output "$AIRS_OUTPUT_ROOT" \
  --result-relative security-delta-real-corpus/adjudication.json
```

Use a fresh result filename for each changed checker/evidence revision. The checker
uses strict manifests, bounded no-follow JSON, capture/source-side association,
retained archive/inventory/reference reconciliation, independent source ownership,
raw declaration facts, rule triggers and recorded ancestry. It does not replace
Swift archive admission. Reuse the native codec receipt separately.

Raw oracle direct use is also explicit:
`security_delta_independent_oracle.py --bundle APP --output NEW_FILE --architecture arm64`.
`--apple-tools` adds bounded supplementary Apple display-tool output. Those
pathname reads are unbound to the descriptor observation and cannot become trust
or source-identity proof. Selected-range observations are separately timed,
non-atomic evidence; their prior container digest is not reverified.

## Interpretation and limits

Retained source bytes stay local. Committed selected Info facts and language
witnesses are independently inspectable locators/hashes; third-party restrictions
and source availability mean a public replay still requires legitimate reacquisition.
The full confusion/coverage denominators and environmental exclusions are in
RESULTS and CASE_MATRIX. Preserve unresolved cases in every host replay.
