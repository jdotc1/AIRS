# Native selected-source comparison facts

Baseline: public main a0b64fb, row accounting merged in public PR4. This bounded
increment extends the side-specific selected-endpoint lookup used by MacScope
UnwindAuditComparator to all selected AIRS comparison rows. The donor assumes
matcher-owned IDs; AIRS imports instead fail explicitly on missing or contradictory
selected facts, never silently dropping endpoints. No donor framework is imported
and MacScope remains read-only.

## Explicit API

ComparisonReport.validateSelectedSourceFacts(baselineData:currentData:) first runs
validateRowAccounting(), then the accepted validateManualPairEndpoints API. Thus
bounded row shape, counts, side uniqueness, declared source image/model facts,
source audit admission and recorded manual selections remain prerequisites.
The existing 64 MiB limit for each source is checked before decoding.

The helper then decodes the admitted audits and builds separate baseline and
current finding maps. Every selected baseline ID must exist in the baseline
source, with the recorded before verdict/scope equal to that finding. Every
selected current ID must independently exist in the current source and agree
with its after verdict/scope. A valid ID in the opposite source cannot substitute
for membership on the selected side.

Lookup applies regardless of match basis or change category: manual, symbol,
exact-image, unmatched and future basis strings all retain the same source-fact
requirement. Added/removed and one-sided ambiguous rows bind only their selected
sides. Ambiguity groups without selected endpoints remain permitted. The same ID
may occur once on each side; source lookup remains independent on both sides.

The API takes original immutable Data, not paths. No file, image, runtime or store
is opened, executed, hashed or modified. Source admission uses two bounded decoding
passes per report, followed by linear lookup/row passes; this is not a single-pass
claim. The native AIRSCore/AIRSApp target remains macOS 14+ with no new dependency.

## Deliberately narrow result

Success binds selected IDs and verdict/scope facts, not an entire comparison's
meaning. Empty comparisons can pass against nonempty sources: omitted findings
and unselected candidate-group membership are not discovered. Function display
names and notes are not source identity evidence and are not authenticated.

Nonmanual changed/unchanged labels are not recomputed, matching bases are not
validated, configuration identity is not checked, and declared report digests
are not authenticated against original binaries. A boundary test intentionally
permits an incorrect nonmanual changed label and a configuration difference when
selected facts still match. Those are separate validators and qualification gates.
Existing manual configuration/signature checks remain available but are not
silently invoked by this selected-fact API.

There is no readiness token, source-completeness proof, automatic import-policy
change, native matching activation, GUI change or new engine capability. Schema 1
and engine model v50 remain unchanged. Default report decoding is untouched.

## Qualification

The first preimplementation compile reported the expected missing API and ran no
runtime test method. The real AIRSApp debug product built successfully in 24.41
seconds under the exclusive native gate. Initial focused execution passed twelve
of thirteen new ComparisonSourceFactsTests methods; the remaining equality check
compared unordered JSON bytes. The test was made deterministic with sorted keys, and only that corrected method
ran again and passed. All thirteen unique methods therefore passed in composed
receipts; the other twelve were reused.

Cases cover valid nonmanual facts, foreign/current/swapped IDs, stale verdict/scope
facts on both sides, added/removed/ambiguous selections, future-basis lookup,
source-image and flag prerequisites, accounting/selection metadata, same-ID
cross-side lookup, malformed source admission, unchanged data, and explicit
completeness/signature/configuration limits. Inputs are small synthetic JSON
with placeholder digests, not user reports or a binary corpus.

Independent read-only review found no semantic defect and identified the JSON
ordering issue in the test. Detailed logs are retained privately; generated native
build products are removed after qualification. Accepted accounting, manual
changes, compatibility, endpoint, codec, Python, GUI and distribution results are
reused within their original scopes. Build success is not GUI acceptance.

This local increment performs no packaging, signing, installation, publication,
production settings/store change or MacScope mutation. Installed app and existing
settings/stores remain unchanged. Public integration remains separate.
