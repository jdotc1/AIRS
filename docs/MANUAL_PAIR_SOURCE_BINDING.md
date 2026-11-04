# Native manual-pair endpoint binding

Baseline: public main 1428611, comparison-context codec merged in PR40 using its
accepted NATIVE_COMPARISON_CONTEXT.md results. This bounded helper adapts MacScope
FunctionVersionMatcher.validatedPins and side-specific known-endpoint lookup to
AIRS source reports. MacScope is read-only and no donor framework is imported.

## Explicit API

ComparisonReport.validateManualPairEndpoints(baselineData:currentData:) accepts
original audit-report Data, capped at the existing 64 MiB limit for each source.
It validates each report through AuditReport.decode before resolving endpoints.
No file is opened, binary decoded, source digest recomputed or store modified.
The API is opt-in and is not called automatically by the native app.

Declared selected-slice SHA-256, architecture and optional UUID must agree with
the respective selected report. Display labels and paths do not authorize a
binding. Declared same-image and model-compatibility flags must reflect the
selected reports. Nonempty manual pairs cannot override actual exact-image
identity. These checks compare declared report facts, not original binary bytes.

Each recorded baseline/current endpoint must exist in the corresponding source.
Every recorded pair needs exactly one manual_review row with the same two IDs;
unrecorded, repeated, missing, swapped or unknown manual endpoints reject. Row
before/after verdicts and scopes must equal their selected source findings.
Source IDs are already unique and bounded by report admission; lookups and row
checks use a bounded linear pass without force unwraps or guessed identities.

## Deliberately narrow result

Success is endpoint/row-fact binding only, not full comparison qualification.
The helper does not authenticate reports or images, validate configuration
identity, recompute change signatures, reclassify rows or bind nonmanual match
bases. A supplied changed/unchanged/ambiguous label is not independently verified
by this API. Callers must retain those separate checks before relying on a full
comparison. No readiness/authorization token, native matching or GUI activation
is introduced. Model v50, schema 1 and all default workflows remain unchanged.

## Qualification

Ten new ManualPairSourceBindingTests methods passed with zero failures. The first
preimplementation compile reported the missing API, as expected; no runtime test
method executed in that check. After implementation the entire new class passed.
Other test bundles selected zero methods and accepted unchanged suites were not
replayed.

Coverage includes a valid pair with preserved comparison data, side-specific
unknown/swapped IDs, image/UUID/architecture mismatches, labels excluded from
identity, actual same-image/model flag consistency, exact pair/row correspondence,
source verdict/scope facts, malformed source reports, the byte limit before parse,
and legacy nonmanual rows remaining outside this binding scope. Tests use small
synthetic JSON with placeholder digests; the size test uses an in-memory zero
buffer, not a binary corpus or user report.

The real AIRSApp debug product built successfully in 13.06 seconds under the
exclusive gate. Existing entitlement-reader/inventory warnings remain outside
this change; no diagnostic implicated the new helper. Independent read-only
source/test review found no actionable defect and confirmed the narrow result.
The reviewer ran no tests, builds, hashes or writes.

Accepted comparison-codec, fingerprint, Python analysis/matching and distribution
results were reused. Logs are retained at local-evidence/manual-pair-source-binding.
The regenerated native/.build cache was removed after retaining receipts. Build
success is not GUI or installed-app acceptance. Installed app, settings and stores
are unchanged. No launch, packaging, installation, release or MacScope mutation
is included.
