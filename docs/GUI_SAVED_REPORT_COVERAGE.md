# Saved-batch comparison coverage choice

The pairing window now exposes “Require complete saved-report row coverage”.
It starts enabled and is disabled while a job is busy. Confirmation passes the
choice to a fresh immutable BatchComparisonRunner for that invocation. The
programmatic compareSavedBatches default remains false for legacy callers.
Core matching and strict decoding are unchanged.

Strict comparison must pass the existing saved-report coverage decoder. Refusal
leaves the pair unavailable with no comparison object or bytes; it does not fall
back to legacy decoding. The result view retains unavailable/unpaired rows and
only offers drill-down when both the comparison and its bytes exist. Existing
cancellation and task settlement remain owned by the workspace.

The option's disclosure explains row coverage and refusal without claiming binary
authentication. Changing the choice does not alter saved reports or old batch
histories. This increment does not add requested-policy metadata to exported
batch documents; that separate source change is not included here.

## Qualification and limits

Independent review found no blocking lifecycle, policy capture or stale-output
issue. The real AIRSApp target built for the existing macOS 14 deployment target.
One new focused workspace method passed: strict coverage refuses the legacy
cross-image example, its export has no comparison payload, and a subsequent
invocation using the legacy default accepts the exact comparison bytes. Temporary
history/library stores are owned test fixtures and removed after the check.

Accepted strict-success, refusal, later-pair continuation and core export controls
were reused; unchanged suites were not repeated. Existing cancellation wiring was
reviewed rather than described as newly exercised. Subsequent isolated native
UI observations confirmed explicit pairing, the
strict default and refusal without drill-down, legacy opt-out, busy-state choice
locking, and cancellation with no stale comparison. Export bytes are covered by
the new workspace test; unchanged native save/export behavior reuses its accepted
prior scope. A standalone XCTest Save panel did not become observable, so that
attempt is not claimed as new save-panel acceptance. A successful app build and
workspace test do not establish GUI, installed-app or release acceptance.
The subsequent exact-source candidate was signed and notarized as documented in
CURRENT_SOURCE_RELEASE_GATES.md. Build 13 is published as a preview, with
clean-machine and minimum-macOS acceptance pending. No app installation was
performed during qualification or publication.

## Follow-up boundaries

The coverage-choice workflow has composed native build, workspace-test and
isolated interaction evidence. Candidate signing, archive, browser-download and
local App Translocation results are recorded in CURRENT_SOURCE_RELEASE_GATES.md.
Independent clean-machine and minimum-macOS acceptance remain open. Integrations
into other applications require their own host qualification.
