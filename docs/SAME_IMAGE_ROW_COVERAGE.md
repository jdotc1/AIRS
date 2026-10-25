# Same-image saved-report group coverage

The opt-in `ComparisonReport.validateSameImageRowCoverage(baselineData:currentData:)`
composes canonical declared-row validation, then explicitly requires same-image
comparison authority. It requires one row for every numeric offset group in the
union of the two admitted saved reports. Duplicate candidates and alternate hex
spellings contribute one group per numeric offset, not one row per finding.

Earlier checks establish each row's key, selected endpoints, multiplicity, change
classification, name and canonical order. This boundary adds omission detection;
it does not infer source admission or matching truth from the expected key set.
Both empty same-image snapshots can have empty output. Cross-image comparisons
refuse this domain-specific API, including empty comparisons.

Coverage refers only to the supplied saved-report groups. It does not establish
all original-binary functions, binary authenticity, symbol identity, exact notes
or complete producer output across other fields/domains. Earlier APIs continue
to accept validated partial output; decoding, matching defaults and native GUI
workflows retain their existing scope. Sources remain bounded to 50,000 findings
per side, producing at most 100,000 expected offset groups.

## Qualification

The real AIRSApp target built successfully. All 17 focused tests passed, covering
omitted/shared/one-sided/disjoint groups, duplicate candidates, alternate numeric
spellings, empty snapshots, cross-image refusal, inherited semantic failures,
equal-count wrong-key cases, lexical order and earlier partial-output scope.
Independent review found no actionable defect. This is source/unit qualification,
not native GUI acceptance or original-binary completeness.
