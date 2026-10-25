# Generated-symbol matching guard

Baseline: public main 44d5953, TBZ/TBNZ merged in PR33 using accepted
TEST_BIT_BRANCH_RESULTS.md receipts. This source-only comparison increment adapts
the owned MacScope FunctionVersionFingerprinting.isGeneratedName guard from
Services/VersionMatching/FunctionVersionFingerprint.swift. MacScope remains
read-only; no donor framework, lifecycle or fingerprint serialization is copied.

## Behavior

Cross-build unique-symbol matching now withholds evidence for generic `_entry`
and `__text` labels, and `loc_`, `unk_`, `off_`, `nullsub_` names with a nonempty
ASCII hexadecimal suffix, optionally introduced by 0x/0X. AIRS's broader existing
sub_, angle-placeholder and lowercase hexadecimal-address exclusions remain;
uppercase 0X address labels are excluded too. Nonhexadecimal prefix names such as
loc_handler remain eligible. Programmer-authored names shaped like generated
labels may become unmatched: this is conservative loss of matching evidence.

Exact image-digest/architecture matching still uses image offsets first, regardless
of names. Unique symbols remain review candidates, not proven source identity.
Duplicate real symbols remain ambiguous. Model/configuration incompatibility
continues to prevent supported changed/unchanged interpretations. Unmatched rows
retain separate added/removed accounting and never imply a fix or regression.
A comparison limitation explains why generated labels provide no evidence.

No report field, schema, matching-policy label or analysis-model identity changes;
current analysis remains arm64-bounded-test-bit-branch-v50. No body/CFG fingerprint,
manual pin, structural pairing or call-graph propagation is implemented yet.

## Qualification

Eight new synthetic-report test methods pass in composed runs. The initial
preimplementation test demonstrated nine generated-name false joins. Tests cover
new exclusions, retained historical exclusions, nonhex real symbols, exact-image
precedence, model/configuration mismatch, deterministic output/input preservation,
duplicate symbols and malformed name types. The objects use explicit placeholder
digests; no binary analysis or provenance hashing occurs.

Three affected DiffBoundaryRegressionTests methods pass after the comparison
change. Accepted TBZ/MOVK/CBZ source/native/image results are reused without
replaying them. The independent read-only comparison review found no actionable
defect, confirmed exact-image precedence, conservative pattern exclusions and
existing duplicate/admission boundaries, and ran no tests/builds/hashes/writes.

Native compilation and GUI are unaffected; no new native build or launch was
needed. Installed app, settings and stores remain unchanged. No package, release,
installation, corpus or donor modification is included.
