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
