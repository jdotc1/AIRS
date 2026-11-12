# Native broad-v1 integration qualification

Baseline: integrated Track A/Track B `3555d2b3bff79f983a9da5bdd1b42e30c98b2559`.
The accepted Python coordinator/validator and its 26-gate corpus are unchanged.

## Changed-boundary receipts

- 15 unique new adapter methods have composed passing receipts. Initial adapter
  RED failed for the missing adapter; initial eight-method GREEN passed in 0.227 s.
  Additional duplicate-key/model/ABI/cancellation and review regressions were
  observed failing before corrections. Latest review repair: four targeted methods,
  zero failures, 0.033 s. Unchanged complete suites were not replayed.
- Nine new workspace/profile methods passed, zero failures/skips, 0.134 s after
  the final public-dispatch change. They cover exclusive broad arguments, preserved
  standard opt-ins, partial coverage, 257-call paging, complete detail paging,
  profile/result mismatch, late completion, cancellation settlement, historical
  import/original-byte export and duplicate envelope refusal.
- The first workspace RED was blocked by the missing adapter and is not claimed
  as a workspace failure. The subsequent RED exposed missing profile/options APIs.
- Source-only independent review identified missing typed function-range binding,
  contradictory unchecked fact states, unbounded foreign fact summaries, dispatch
  preflight placement and hidden limitation entries. All five were closed after
  corrections. No remaining concrete blocker was identified. Duplicate dispatch
  was not reproduced on this host; pre-Foundation preflight is hardening with
  negative coverage, not a demonstrated RED failure.

The adapter withholds inconsistent recorded eligibility, preserves legitimate
unknown symbolic values and retains complete original JSON. Imported records are
historical claims, not fresh byte validation. The internal preflight optimization
is neither serialized nor accepted as filesystem authority. No inspected code is
executed. All admitted limitations and paged raw evidence remain inspectable.

Actual selectors: `swift test --package-path native --filter
SwiftBroadFlowReportTests` and the scoped new-method filters in retained adapter
receipts; `swift test --package-path native --filter SwiftBroadWorkspaceTests`.
Execution logs are retained privately as `broad-ui-adapter-*.log` and
`broad-ui-workspace-*.log`; accepted engine/compiler/corpus receipts are reused.

## Artifact qualification boundary

The real release target, package, signing, notarization and installation receive
separate new-artifact receipts. The new small owned probe source in
`fixtures/swift-error-flow/native-broad` supports first native command routing;
it supplies no additional credit to the accepted broad corpus. It is compiled
and inspected as data, never loaded or executed. Existing clean-machine,
minimum-OS, Intel and MacScope qualification limits remain unchanged.

## First native route correction

The first installed broad-v1 live route reached the accepted coordinator but the
CLI's file-output confirmation indexed legacy `report_kind` after writing the
broad report. The resulting `KeyError` prevented native publication. A narrow fix
uses the existing report kind when present and the broad model label otherwise;
it changes only stdout confirmation metadata, not serialized evidence or analysis.
One new mocked `--output` regression passed in 0.002 s and confirms unchanged
written evidence. Initial test invocations lacked PYTHONPATH and are retained as
harness failures, not semantic RED evidence; the actual native failure establishes
the defect. Independent source review approved this one-line correction. Native
binaries and accepted engine/corpus qualification are reused; only the changed
app resource/provenance seal receives new signing and notarization.


## Imported callee profile admission

The native adapter now recognizes the exact `swift-broad-error-flow-imports-v1` /
`broad-imports-v1` pair with the 8,192-call envelope. Import table counts,
completeness, declaration states, non-claims and repeated-stub bindings are
validated before presentation. Recorded ADRP/LDR/BR words must match the stub
model and derive the recorded pointer address with bounded arithmetic. This is
record consistency, not a fresh source-byte or section-containment check.

Import rows remain unresolved, without ABI admission, outcome witnesses,
validation or eligibility. The header includes import completeness and counters;
details show attribution, declaration syntax and its limitations. Unknown
declaration syntax models retain raw evidence without a throwing interpretation.
Earlier profiles retain their existing decoding and presentation. Workspace
model pinning and historical imports use the profile registry; Swift flow runs
have no analysis-reuse path.

Import call counters are accepted up to the profile's scan limit of 2,097,152
words; stub and section counts keep their own tighter caps. A recorded stub must
lie wholly inside the slice, and its three words must be consecutive in the file.

Results for this change, each run once on the final source: the native package
built; `SwiftBroadFlowReportTests` passed (36 tests), including the counter
limit, a stub ending exactly at the slice end and one byte past it, and
non-consecutive stub words; `SwiftBroadWorkspaceTests` passed (16 tests); and
`tests/test_swift_broad_native_parity.py` passed (4 tests), which compares the
native identity, reason and limit literals with the engine's. The admission and
refusal tests were written independently of the implementation. An independent
source review preceded the final run; the three boundary tests named above were
added in response to it and are not independently authored.

Not done for this change: app launch, real-input acceptance, packaging and any
distribution check. The consistency checks above read the report only; they do
not re-read the analysed file.
