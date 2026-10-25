# Selected exact-body candidate validation

`ComparisonReport.validateBodyCandidatePairs(baselineData:currentData:)` is an
explicit native validation API for selected exact-body review pairs. It composes
unique-symbol, exact-image, observation-label, selected-source, accounting and
manual-pair validation. It does not activate a GUI workflow or change decoding,
matching defaults, engine semantics, findings or source data.

## Source snapshot and precedence

For a claimed `exact_body_candidate` row, the comparison must explicitly record
`exact_body_candidates: true`. Missing status remains unavailable. Sources must
be different images with equal architecture and exact CPU subtype. Both selected
IDs must have structurally admitted fingerprints with equal kind, SHA-256 text
and instruction count. The row key must be the canonical
`body:arm64-exact-bytes-v1:<lowercase digest>:<decimal count>`.

The validator reconstructs the host matcher phase from admitted source findings:

1. Remove only validated manual-pair endpoints.
2. Group remaining usable symbol names by exact UTF-8 bytes. Unusable or missing
   names represent separate side-specific, finding-specific unmatched groups.
3. Exclude established one-baseline/one-current symbol groups, even when their
   symbol rows are omitted from the imported comparison.
4. Count every remaining fingerprint in a kind/digest/count bucket, including
   fingerprints belonging to blocked ambiguous symbol groups.
5. Require exactly one member on each side of the selected bucket. Both selected
   members must also come from original post-pin groups containing only one
   finding total. Imported body or future-match rows cannot consume blockers.

This is one snapshot phase, with no iterative tie-breaking. Shared usable-name
helpers preserve the existing host generated-name policy and raw UTF-8 grouping;
no donor policy replaces AIRS rules. Prior bounded validators may decode sources
again; this API does not claim a single-pass parser.

## Meaning and limits

Body equality is review evidence, not source-function identity, regression/fix
proof, binary authenticity or byte verification. Imported digests are not rehashed.
Model/configuration differences still require ambiguous observation labels, while
comparable sources require the existing changed/unchanged signature result.

All declared body rows require two selected endpoints; malformed one-sided or
unselected body claims reject. Omitted candidates and groups remain unverified.
The API does not establish source completeness, recompute the whole comparison,
verify arbitrary future matching bases, or change historical reports lacking
fingerprints. Default native workflows and distribution gates remain separate.

## Bounded qualification

The real AIRSApp target built successfully. Fourteen new focused native tests
passed with zero failures using synthetic source reports. Independent source
review found no actionable defect. These checks cover selected body evidence, canonical keys, explicit opt-in, fingerprint
presence/full tuples, duplicate and ambiguous-symbol blockers, manual precedence,
omitted established symbols, subtype compatibility and observation-label authority.
Accepted unchanged source/accounting/manual/symbol/offset/codec, Python, GUI and
distribution results are reused within their original scope. Detailed logs remain
local; this increment has no GUI, packaging, install or release qualification.
