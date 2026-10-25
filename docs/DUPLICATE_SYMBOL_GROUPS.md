# Duplicate symbol-group validation

`ComparisonReport.validateDuplicateSymbolGroups(baselineData:currentData:)` is an
explicit native validation API for declared symbol groups with source-name
multiplicity. It composes exact-body candidate, unique-symbol pair, exact-image,
observation-label, selected-source, accounting and manual-pair validation. It does
not activate native workflows or change matching defaults.

## Source grouping

Only validated manual-pair endpoints are removed before grouping. Remaining
usable symbol names share exact UTF-8 groups under the existing host policy.
Generated names provide no symbol evidence. Every declared `unique_symbol` row
must use a `symbol:` key naming an existing usable source-name group. Unicode
normalization, case folding and whitespace trimming are not performed.

Whenever either side of that source group contains multiple findings:

- The row must be classified `ambiguous`, even if its imported label instead
  claims added or removed.
- A side with exactly one finding must select that finding's ID.
- A side with zero or multiple findings must select no ID.

This verifies declared 2:0, 0:2, 2:1, 1:2 and 2:2 group shapes without guessing a
pair. Omitted rows and imported body/future-match selections cannot hide source
multiplicity. Body matching never consumes ambiguous symbol groups, so absent,
false or true body-candidate status does not change their shape.

For groups without multiplicity, an ambiguous row missing either endpoint is
rejected. A fully selected one-to-one pair may remain ambiguous when its source
models or configurations differ, as required by the composed observation checks.

## Limits

Singleton one-sided matching outcomes remain unverified beyond composed source
facts and the declared key's source-group existence. Their final presence may
depend on body matching; absent body status is not interpreted as false. The API
does not verify source completeness, arbitrary other matching bases, displayed
names/notes, binary authenticity or source-function identity. Imported body
fingerprints remain unauthenticated review annotations. No engine finding,
comparison producer, decoding default or GUI behavior changes.

## Qualification scope

The real AIRSApp target built successfully, and sixteen new focused native tests
passed with zero failures. Independent source review found no actionable defect.
Synthetic cases exercise duplicate-group shapes, required singleton IDs,
hidden blockers, false classifications, validated manual pins, raw-name keys,
body-status independence and compatible/incompatible selected-pair boundaries.
Unchanged source/accounting/manual/symbol/body/offset/codec, Python, GUI and
release evidence is reused within its accepted scope. Detailed logs remain local.
No packaging, installation, GUI or release qualification is claimed here.
