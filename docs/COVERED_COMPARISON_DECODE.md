# Covered saved-report comparison decoding

The opt-in `ComparisonReport.decodeWithSavedReportCoverage(_:baselineData:currentData:)`
provides one native constructor for bounded comparison decoding plus the existing
saved-report group coverage proofs. It applies `ReportFiles.maximumBytes` before
JSON decoding and retains the existing generic schema/count admission checks.

Same-image reports select same-image coverage, preserving missing/false/true body
metadata. Cross-image reports select body-disabled or body-enabled coverage only
from explicit false or true metadata. Missing cross-image status refuses; policy
text and fingerprint presence do not supply a default. The selected validator
checks source context, so a forged dispatch flag cannot weaken the proof.

The constructor returns the decoded report without changing its modeled fields.
It does not add extra source decoding outside the selected coverage branch.
Generic decoding remains available with its earlier broader scope. This API does
not activate a GUI workflow or change matching defaults.

Success means saved-report group coverage plus the composed field checks. It does
not authenticate binary bytes or fingerprints, establish function identity,
reconstruct every producer field, or claim GUI acceptance. Legacy cross-image
reports without body status require explicit separate handling rather than an
invented setting.

## Qualification

The real AIRSApp target built successfully. All 16 focused tests passed, covering
the three coverage branches, same-image option preservation, unavailable status,
forged dispatch flags, omitted groups, malformed JSON/schema, comparison/source
byte bounds and unchanged modeled fields. Independent review found no actionable
defect. This is source/unit qualification, not GUI activation or acceptance.
