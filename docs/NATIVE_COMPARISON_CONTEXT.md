# Native comparison-context preservation

Baseline: public main 83353b3, native fingerprint codec merged in PR39 using its
accepted NATIVE_BODY_FINGERPRINT_CODEC.md results. This bounded data-model step
adapts MacScope's Codable matching-result/manual-pin preservation principle to
AIRS comparison records. The MacScope checkout remains read-only; no framework,
matching implementation or app lifecycle is imported.

## Known metadata

Native ComparisonContext now retains optional analysis_configuration_changed,
exact_body_candidates and manual_pairs fields. Missing metadata remains nil and
is omitted on encoding. Explicit false and empty lists remain present. Explicit
null and wrong types reject. ComparisonReport and its typed children are Codable,
so the known context, IDs, notes, summary and classification fields can round-trip.
Unknown matching-policy and row-basis strings remain generic review data.

Each ComparisonManualPair retains baseline_id/current_id in supplied order.
Pair objects require exactly those two fields and lowercase AIRS finding IDs.
The decoder checks the 50,000-entry bound before typed materialization when the
array count is available, and maintains an incremental guard for other decoders.
Duplicate or conflicting endpoints reject without silent normalization. A declared
same-image comparison cannot contain nonempty manual pairs; an explicit empty
list remains representable.

This is structural metadata admission and known-field preservation. It does not
resolve IDs against unavailable source audit reports, authenticate identities,
recompute matching or reclassify rows. Existing schema/header/nonnegative-count
checks remain in place. No byte-for-byte or unknown-extension JSON preservation
is claimed. Missing configuration status is not silently converted to unchanged.

## Qualification

Eleven new ComparisonContextCodecTests methods passed in composed runs. The
preimplementation explicit-null case failed as intended because the old decoder
ignored the field. Ten methods then passed after implementation. The cap assertion
was strengthened to require the specific limit error, and a true-configuration-
change case was added; only those two selectors were run afterward, both passing.
The other nine accepted methods were reused without replay.

Coverage includes typed metadata/pair round trips, legacy omission, false/empty
retention, null/type/key/ID rejection, duplicates/conflicts, declared same-image
constraints, future policy/basis values, the raw list bound and preservation of
ambiguous classification/counts/notes. Tests use synthetic JSON with placeholder
IDs and digests, not user reports or stores. No binary or provenance hash is read.

The real AIRSApp debug product built successfully in 25.44 seconds under the
exclusive shared gate. Existing entitlement-reader/inventory warnings were
present before production edits and remain outside this change. No diagnostic
implicated the new comparison codec. Independent read-only source and test review
found no actionable defect; the reviewer ran no tests, builds, hashes or writes.

Logs are retained under local-evidence/native-comparison-context. The generated
native/.build cache was removed after checks. Python matching/producer, native
fingerprint and distribution results are reused; no unchanged suite or sealed
input verification was replayed. Build success is not native GUI acceptance.

## Boundaries

Native production/matching flags, defaults, GUI controls and release behavior do
not change. Analysis model remains arm64-bounded-test-bit-branch-v50 and schema
remains 1. Further use of recorded selections requires explicit source-report
binding and workflow qualification. Installed app, settings and stores remain
unchanged. No launch, packaging, installation, release or MacScope mutation is
included. This step retains facts for future native review without promoting
imported metadata into authority.
