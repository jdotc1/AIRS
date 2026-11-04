# Unselected symbol-group names

`ComparisonReport.validateUnselectedSymbolNames(baselineData:currentData:)`
composes selected function-name validation and the existing declared-row checks.
For a `unique_symbol` row with neither endpoint selected, it requires the recorded
function name to equal the canonical symbol key suffix byte for byte. The composed
source-group proof establishes membership, usable names and multiplicity after
manual pins; the key alone does not establish those facts.

This preserves Unicode bytes, leading combining marks, punctuation and case.
It does not normalize names or manufacture selected endpoints. Selected rows keep
the current-source-first rule. Earlier APIs retain their existing scope.

Unselected exact-offset representative labels remain unverified. Names do not
establish identity or authenticate binary symbols. This opt-in API does not prove
complete producer output and does not activate a GUI workflow or change defaults.

## Qualification

The real AIRSApp target built successfully. All 13 focused tests passed, covering
baseline-only, current-only and two-sided duplicate groups, byte-exact Unicode,
punctuation, body-status independence, manual-pin effects, selected-name
composition, earlier-API scope and partial output. Independent review found no
actionable defect. These checks establish source/unit behavior, not GUI acceptance.
