# Unselected exact-offset representative names

The opt-in `ComparisonReport.validateUnselectedOffsetNames(baselineData:currentData:)`
composes unselected-symbol and selected-name validation. For a declared
`exact_image_offset` row with neither endpoint selected, the representative is the
first current finding at that numeric offset, otherwise the first baseline
finding. Source array order is preserved exactly. The row name must equal that
representative's name byte for byte; unavailable names refuse validation.

The composed offset proof establishes same-image authority, canonical keys,
group membership, multiplicity and selected endpoints. This API does not infer
those facts from a label. Selected endpoint labels retain their earlier rule.

This checks consistency with recorded source order, not the authenticity of that
order or symbols, complete producer output, or source-function identity. It does
not change earlier APIs, matching defaults, report decoding or GUI workflows.

## Qualification

The real AIRSApp target built successfully. All 14 focused tests passed, covering
baseline-only, current-only and two-sided duplicates; source ordering and current
precedence; numeric source offsets; exact Unicode, empty and generated names;
unavailable names; inherited key/image failures; selected singleton ambiguity;
earlier API scope; and omitted groups. Independent review found no actionable
defect. This is source/unit qualification, not GUI acceptance.
