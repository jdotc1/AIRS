# Explicit-body-disabled cross-image row coverage

The opt-in `ComparisonReport.validateBodyDisabledRowCoverage(baselineData:currentData:)`
composes canonical declared-row validation and requires cross-image sources plus
explicit `exact_body_candidates: false`. Missing status remains unavailable;
unsuffixed policy text is not evidence that body matching was disabled. Enabled
body matching and same-image comparisons refuse, even for empty snapshots.

Expected raw UTF-8 keys comprise validated canonical manual pairs and all remaining
source groups after removing pinned endpoints independently per side. Usable host
names form symbol groups; generated/unusable names retain side-specific unmatched
keys. The existing host name guard is reused. Duplicate raw names collapse into
one symbol group, while equal generated labels on opposite sides remain distinct.

Existing proofs establish each declared row's selections, classification, name
and order. This boundary detects omissions without changing matching or inferring
body selections. Coverage means groups in the two admitted saved reports, not all
original-binary functions or every producer field. Names and imported fingerprints
remain unauthenticated; no identity or GUI acceptance is claimed. Earlier APIs,
decoding and defaults retain their scope. Body-enabled coverage remains separate.

## Qualification

The real AIRSApp target built successfully. All 18 focused tests passed, covering
omitted/shared/one-sided/duplicate groups, generated labels, Unicode-distinct
symbol names, manual endpoint removal, empty sources, strict domain/status guards,
inherited key/name failures and earlier partial-output scope. Imported body
evidence does not enable the option. Independent review found no actionable
defect. This is source/unit qualification, not native GUI acceptance.
