# Imported callee effect admission profile (`broad-extended-v4`)

`broad-extended-v4` is an explicitly selected profile for the broad structural Swift analysis. It is the second-generation broad profile. It adds three things to the report of `broad-extended-v3`: the licence that a decided declaration gives an imported callee at a call site, a complete accounting of every candidate and observed call, and a header that states the profile's premises, claims and limits. Every earlier profile keeps its selection, rows, counters and output bytes unchanged. The native application admits this profile: its registry pair is registered with `native_admitted` true.

## Identity

| Item | Value |
| --- | --- |
| profile | `broad-extended-v4` |
| report `model_version` | `swift-broad-error-flow-extended-v4` |
| new fact model | `swift-import-effect-admission-v1` |
| declaration grammar, unchanged | `swift-declaration-syntax-v2`, pinned to swift-6.4.2-RELEASE |
| caller fact, unchanged | `swift-caller-error-test-v1` |
| also unchanged | stub and GOT attribution models, `swift-indirect-target-shape-v1`, `swift-value-witness-admission-v1`, the witness and validation models |

The accounting fields (omission causes, scan, unselected partition, import call table) belong to the report model and have no model of their own. The profile uses the resource limits of `broad-extended-v1`. The retention limit of 8,192 rows is not raised, and no limit is added. The profile name is selected with `--swift-profile broad-extended-v4`, with the same prerequisite flags as the other broad profiles.

## What an imported callee is

An import call is a call whose target stub or GOT slot the existing attribution already tied to a symbol. This profile does not change attribution. A symbol is Swift when it begins `$s` after any leading underscores. Any other symbol is `not_swift`, is never parsed, and stays outside every Swift count.

For each distinct Swift symbol the engine parses the declaration once and keeps the result for the run. The stub path, the GOT path and the value-witness metadata-accessor check of v3 share that one result, so a second parse of the same symbol is a defect. The parse is charged once per distinct symbol to `analysis_work`.

A symbol the value-witness check admits must agree with the import table when the table lists it. A Swift metadata accessor is listed `non_throwing`. One of the fixed C runtime metadata functions of `swift-value-witness-admission-v1`, such as `swift_checkMetadataState`, is not a Swift declaration and is listed `not_swift`. A disagreement fails the report.

## Premises

The licence rests on five premises, carried once in `capabilities.premises` and never repeated per row:

- `symbol_name_carries_effects`: a mangled Swift name encodes the effects of the declaration it was produced from.
- `no_silgen_name_override`: the declared effect is the effect of the definition bound to the name. The residual hazard is recorded, not discharged.
- `name_only_attribution`: stub and GOT attribution is by symbol name only.
- `binding_not_proven`: interposition, flat namespace, weak or missing imports and the library ordinal are not proven.
- `grammar_pinned`: the parse is by `swift-declaration-syntax-v2`, pinned to swift-6.4.2-RELEASE.

## Not claimed

`capabilities.not_claimed` lists what no row of this profile asserts: `callee_returns`, `dyld_binding`, `runtime_callee`, `arguments_and_results` and `error_value_at_runtime`.

## Licence table

The licence class is a function of the grammar decision and the recorded effects.

| Grammar decision | Recorded effects | Licence class | Claim made | Claim not made |
| --- | --- | --- | --- | --- |
| `non_throwing` | none | `no_error_exit` | the definition bound to this name has no error exit through x21 | that the call returns, the actual callee, the binding, results |
| `throwing` | not async, untyped | `declared_error_exit` | the definition may exit with an error in x21 under the untyped Swift 6 convention (this includes `rethrows`) | that an error occurs, that a nonzero x21 after the call is an error, which error |
| `throwing` | async, or typed throws | `refused_unsupported_effect` | nothing; the effect is outside the ABI profile | any x21 claim |
| `async` | any | `refused_unsupported_effect` | nothing | any return-point claim |
| `undecided` | any reason, including `accessor`, `typed_throws`, `thunk_or_specialization` | `none` | nothing | that the callee is non-throwing |

`none` and `refused_unsupported_effect` never become agreement. The grammar is not changed: an accessor and `throws(Never)` stay undecided because the grammar decides them so.

## Caller relation

The caller fact of `swift-caller-error-test-v1` is computed at every attributed Swift site, as in v3, and is not changed. Its shapes are `swifterror_idiom`, `postcall_test_only`, `precall_zero_only` and `none`. A tail branch has no post-call window. The relation of the licence to the caller fact is one of `conflict`, `corroborated`, `no_signal` and `not_applicable`.

| Licence class | Caller shape | Call kind | Relation | Treatment |
| --- | --- | --- | --- | --- |
| `no_error_exit` | `swifterror_idiom` | `bl` | `conflict` | row kept, reason `declaration_caller_disagreement` |
| `no_error_exit` | `swifterror_idiom` | tail `b` | `not_applicable` | skipped |
| `no_error_exit` | any other shape | any | `no_signal` | skipped |
| `declared_error_exit` | `swifterror_idiom` | `bl` | `corroborated` | row retained |
| `declared_error_exit` | any other shape | `bl` | `no_signal` | row retained |
| `declared_error_exit` | any | tail `b` | `not_applicable` | row retained |
| `refused_unsupported_effect`, `none` | any | any | `not_applicable` | row retained |

A `corroborated` relation says that instructions near the call agree with the declared effect. It does not say that the call fails or succeeds.

## Rows

Every retained import row has status `unresolved`, so it stays in the denominator. The reason is the one the licence gives:

| Licence class and relation | status | reason |
| --- | --- | --- |
| `no_error_exit`, `conflict` | `unresolved` | `declaration_caller_disagreement` |
| `declared_error_exit` | `unresolved` | `imported_callee_outcome_unmodeled` |
| `refused_unsupported_effect` | `unresolved` | `imported_callee_effect_unsupported` |
| `none` | `unresolved` | `imported_callee_abi_unqualified` |

Decided non-throwing calls without a `conflict` are skipped and counted, per symbol and in the unselected partition. An import row never carries `abi`, a candidate or a validation. It carries its declaration as a fixed-key compact record (`syntax_model`, `decision`, `reason`, `entity`, `throws`, `is_async`, `typed_throws`, `identity_sha256`) in place of the full grammar identity, and an `effect_admission` record (`model`, `licence_class`, `caller_relation`). Rows other than import rows carry neither.

## Declined scope of item 5b: no witness

This profile gives no import a witness. An imported callee has no body, no callee control-flow graph and no lowering observation to validate against, so claiming more than the licence would be a new semantic without evidence. The only ways an import leaves the unresolved set are being skipped as decided non-throwing, or being a row that is counted and labelled. A decided `throwing` import stays `unresolved` by design. ABI admission for imported callees, `async` return points, typed throws and accessors are outside this profile.

## Report fields

All fields below are present only under this profile, and the profile requires all of them.

- `capabilities`: `report_model`, `effect_admission_model`, `declaration_syntax_model`, `grammar_pin`, `caller_error_test_model`, `premises`, `not_claimed`.
- `limits`: `max_total_evidence`, `max_observations_per_function`, `max_instructions_per_function`, `max_total_instructions`, `analysis_work_ceiling`, `output_budget_bytes`, `import_table_entries`, `import_table_byte_reserve`. The values come from the constants the engine uses. `output_budget_bytes` is the effective row budget after the 65,536-byte slack and the table reserve.
- `omission_causes`: `analysis_work_budget`, `per_function_limit`, `total_row_limit`, `output_budget`. Every selected candidate that does not become a row has exactly one cause, the first limit the engine reaches in that order. `omitted_calls` is their sum.
- `omitted_by_kind`: `import_stub`, `import_got`, `local_swift_direct`, `indirect`. The kind is known before any limit is tested, so it says what was lost. Its values sum to `omitted_calls`.
- `unselected_call_counts`: `skipped_non_throwing`, `non_swift_import`, `declined_stub`, `direct_target_not_swift_function`, `direct_target_unattributed`, and `other`. Every observed call is either a selected candidate or in one named bucket, and `other` must be 0.
- `scan`: the words of every function classed once as decoded, not decoded for the per-function ceiling, not decoded because the total ceiling ran out, or in a function excluded for its boundary. `candidates_in_unscanned_words` is the integer 0 when every unscanned count is 0 and otherwise null with the reason `words_not_decoded`.
- `import_calls`: one entry per attributed imported symbol, Swift or not, with its call counts taken at attribution time and so independent of the row limit; `decision_by_shape` (four decisions by four caller shapes, all 16 cells present); `decision_summary` (names by decision, and undecided names and calls by grammar reason).
- `reason_counts` no longer contains the internal scan marker `excluded_boundary`.

## Limits and bounds

- The import table holds at most 4,096 entries and a reserved size of 2 MiB (512 bytes per entry plus the symbol length). Entries are admitted first-seen in address order. A symbol that does not fit adds only to `residual`. `complete` is true exactly when `residual.symbols` is 0 and the word scan is complete, so a count over a partly scanned image is never marked complete.
- The reserve leaves the encoded-output budget before any row is costed, so the table cannot turn a successful analysis into the final size failure.
- The retention limit stays 8,192 rows. The engine reports the limits it ran with, and the invariant checker pins `limits.max_total_evidence` to 8,192 for this profile.
- Candidates inside words that were not decoded are unknown, not zero.
- The engine runs the report invariant checker (`airs.swift_broad_accounting.check_broad_v4_report`) before it returns a v4 report and fails closed with a message that begins with the rule id.
- No older profile calls the checker.

## Native status

The registry pair is registered with `native_admitted` true, and the native application offers the profile as the last entry of the analysis-profile picker ("Broad Swift · v3 + declaration licences and full accounting (v4)"). The native decoder is a second, independent implementation of the report rules. Before it accepts a v4 report it refuses, with a message that begins with the rule id, any report that breaks a rule it can check from the report alone:

- Report shape (E1, E2): the nine v4 groups are all present and no key is unknown; the header strings and the limits keys are fixed; the v4 identity and groups appear only together.
- Integer discipline: every count is a non-negative integer (never a boolean or a fraction), and every sum is checked for overflow.
- Accounting (A1 to A6, B1 to B3, C1 to C7): the row, omission, scan and import-table arithmetic of this page.
- Import rows (D1 to D4): the compact declaration record is internally consistent and the licence class is recomputed from it by the table above (the grammar itself is not run); the caller relation, the row status and the row reason follow from the licence, the caller-test shape and the call kind; no import row carries an ABI, a candidate or a validation.

Older profiles are admitted exactly as before. The native view shows the recorded licence class and caller relation of each imported-call row beside the other evidence; both are recorded evidence, and the call stays unresolved. The command line tool and the engine accept the profile as before.

## Related

- [Declaration grammar contract](swift/DECLARATION_GRAMMAR_CONTRACT.md) and [declaration grammar v2](swift/DECLARATION_GRAMMAR_V2.md): the grammar whose decisions this profile reads.
- [Import effect admission library](../src/airs/swift_import_effect_admission.py): the resolver that turns a decision into a licence (the contract of item 5a).
- [Broad imports profile](SWIFT_BROAD_IMPORTS_PROFILE.md): the profile whose import rows this one extends.
- [Panel measurement](SWIFT_BROAD_V4_PANEL.md): what this profile reports on the 12 corpus applications, and the stop-rule outcome.
