# Advanced Swift structural error flow

The optional method profile uses `swift-sync-error-edges-v38`,
`swift-return-choice-v46` and `swift-throwing-declarations-v1`. The existing
free-function default remains v37/v45. These profiles retain the existing
region v24, incoming v7, presentation v10, result v24, success-constant v17,
error-constant v19 and flag-entry v1 rules. Mixed or unknown model profiles
cannot produce trusted text summaries.

```
python3 -I -B airs_cli.py swift-error-flow Owned.dylib --include-swift-methods
python3 -I -B airs_cli.py swift-error-flow Owned.dylib --include-error-regions --validate-region-entries --include-structured-presentation --include-outcome-witnesses --format text
```

Witnesses require all three preceding analysis options. Missing prerequisites
are rejected before input reading. Methods and witnesses are independent opt-ins.
Exit 0 means complete scanning/detail processing, including semantic refusals;
exit 1 reports incomplete scanning, call retention or witness processing; exit 2
reports option/input/export errors. No status proves runtime execution.

The immutable declaration parser completely consumes a bounded ASCII mangling.
Method admission additionally requires selected-image symbol/entry attribution
and non-generic nominal context metadata. Unsupported generic, async, typed,
class, witness-dispatch and thunk forms decline. Syntax alone is insufficient.

## Witness contract

`swift-outcome-witness-v1` records source identity, caller/callee, raw words,
post-call test and successors, structural intervals, incoming checks, selected
value/return-choice evidence, graph provenance, accounting and limitations.
`swift-outcome-validation-v1` independently compares the relevant facts with
admitted bytes. Builder output alone is a candidate. The pure validator is the
validation interface; text rendering merely displays recorded validation and
never claims a fresh byte check.

Statuses are `eligible_structural_only`, `unresolved`, `blocked`, and `declined`.
Partial facts remain inspectable. An eligible witness does not prove that calls
return, branches execute, handlers are exclusive, catch types are known, or
source code is equivalent. Opaque calls retain unproven return behavior.

Historical reports retain their original model meaning. Optional fields are
absent by default. The generic unwind audit importer is not a Swift saved-report
validator. No native UI, upload, account, live debugger or remediation is added.

## Qualified subset and limits

Production method admission currently enables only the independently qualified
`Int -> Int` case. Candidate syntax for `Int -> Void` and `Void -> Int` is parsed
but those methods decline production admission pending separate callsite evidence.
See `swift/OWNED_ADVANCED_QUALIFICATION.md` for the compiler observations.
The initial witness validator independently admits a narrower shared-tail subset:
literal and preserved/copied result transfers, offset pair restores and stack
deallocation. Arithmetic and other return-tail forms remain unresolved.

Existing scan bounds remain 8 MiB input, 1024 functions, 4096 words/function,
16384 words total and 256 retained calls. Witness defaults cap 64 retained words,
16 graph nodes, 24 edges, graph/container depth8, 64 KiB serialized candidate,
4096 container items and2048 characters/string. Local replay is capped512 steps;
caller scanning4096 words and aggregate work262144 includes symbol/caller scans.
The coordinator caps aggregate serialized witnesses at8 MiB. Limits bound work
and retained storage; they do not assert a whole-process RSS ceiling.

The supplemental schema documents wire shape only. Semantic validation requires
the pure byte-backed validator. Unchanged saved evidence is never upgraded by
rendering it. The generic audit model registry is intentionally unchanged.
