# Native observation labels for selected comparison pairs

Baseline: public main 5bc78fa, selected-source fact binding merged in public PR5.
This bounded increment extends the MacScope UnwindAuditComparator-style separation
of matching from audit observations to all selected AIRS pairs. It reuses the
existing host finding signature instead of implementing a second comparator.
MacScope remains read-only and no donor framework/dependency is imported.

## Explicit API

ComparisonReport.validateMatchedChangeLabels(baselineData:currentData:) first
composes validateSelectedSourceFacts and validateManualPairChanges. Thus row
accounting, selected endpoint membership/facts, source context, recorded manual
selection, admitted configurations and exact model-label guards precede further
classification checks. Manual rows retain their existing verification path.

For every other row with both selected endpoints, the helper uses the same
FindingObservationSignature as manual verification. With equal admitted models
and configurations, equal signatures require unchanged and different signatures
require changed. Model/configuration differences require ambiguous. Compatible
selected pairs cannot choose ambiguous to evade observation checks.

The internal signature refactor changes naming/visibility only, keeping its fields
private. Verdict, coverage, mode, scope, raw optional encoding, sorted reasons
with duplicates, ordered relative checked PCs and ordered evidence facts retain
their accepted semantics. Free-form strings preserve exact UTF-8 distinctions;
relative evidence addresses retain sign and the full admitted VM range. Display
names/prose and facts outside the host signature do not create finding changes.

An internal configuration-difference wrapper delegates to the existing original
Data comparison. Its inputs must already pass configuration admission. Missing
legacy configurations follow the existing policy; no default is invented.
Malformed limits and contradictory recorded configuration status still reject.
The inherited canonical-Unicode unknown-model edge remains fail-closed rather
than claiming full Python acceptance parity for an ambiguous row.

One-sided added/removed rows and ambiguity groups without a selected pair remain
outside signature comparison. They still pass the accounting and source-fact
prerequisites. Unknown matching-basis strings cannot bypass the host's observation
label checks; a future producer with different label conventions may be refused
by this strict opt-in API. Default decoding remains unchanged.

## Limits of success

This verifies recorded observation labels, not whether functions should have been
paired. Symbol, exact-image, body-candidate and future matching-basis semantics
are not recomputed. Body equality, source-function identity, matching completeness,
source completeness and original binary authenticity remain separate questions.
An internally consistent comparison may still have unselected findings or a false
match. Empty selected comparisons do not imply complete source coverage.

The API uses original bounded Data only, with the existing 64 MiB cap per source.
It performs several bounded decoding passes while composing accepted validators;
it is not a single-pass parser. Endpoint maps and selected-row passes are linear
apart from the signature's existing reason sorting. Nothing is read from a file,
executed, hashed, mutated, reclassified or written to a store.

There is no automatic import-policy change, native matching activation, readiness
token, GUI change, new instruction support or new engine model. Native targets
remain macOS 14+, schema 1 and model v50.

## Qualification

Eleven new MatchedChangeLabelsTests methods passed with zero failures in 0.032
seconds. The real AIRSApp debug product built successfully in 16.19 seconds under
the exclusive native gate. Accepted unchanged manual, source-fact, accounting,
compatibility, codec, Python, GUI and distribution results were reused. No
unchanged test suite, source artifact or signing check was repeated.
The first preimplementation compile reported the expected missing API and ran
no runtime test method. Independent read-only implementation review found no
actionable defect and confirmed the behavior-preserving shared-helper refactor.

New small synthetic cases cover equal/different nonmanual observations, ignored
presentation text, all basis strings, model/configuration ambiguity, contradictory
configuration status, source/accounting prerequisites, mixed manual/nonmanual
rows, exact wire strings, malformed configuration and deliberately unselected
groups. Detailed logs remain private; generated build products are removed after
retaining receipts. Build success is not GUI or installed-app acceptance. No user
report or binary corpus is used.

No packaging, signing, installation, production settings/store change or MacScope
mutation is claimed by this qualification. Installed app, settings and stores
remain unchanged; public integration does not activate native workflows.
