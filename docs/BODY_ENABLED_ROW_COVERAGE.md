# Explicit-body-enabled cross-image row coverage

The opt-in `ComparisonReport.validateBodyEnabledRowCoverage(baselineData:currentData:)`
composes canonical declared-row validation and requires cross-image sources with
explicit true body status. Missing/false status and same-image use refuse, even
when empty. No policy text or fingerprint presence backfills the option.

The validator reuses the existing admitted body-candidate projection after manual
pins, gated by equal source architecture and exact CPU subtype. Expected raw keys
include every validated manual pair and projected body pair. Consumed endpoints
are removed independently per side before rebuilding remaining usable-name symbol
and side-specific unmatched groups. Established symbols and duplicate blockers
retain the existing projection's precedence. Model/configuration incompatibility
does not suppress candidate coverage; composed change-label checks retain ambiguity.

This detects omitted groups in the supplied saved-report snapshots, including body
pairs absent from declared rows. It does not authenticate imported fingerprints,
prove source-function identity, establish original-binary completeness or reconstruct
all producer fields. Earlier APIs retain partial-output scope; source decoding,
matching defaults and GUI workflows retain their behavior.

## Qualification

The real AIRSApp target built successfully. All 20 focused tests passed, covering
omitted/multiple body pairs, named/generated consumption, established symbols,
duplicate blockers, manual effects, model/configuration ambiguity, subtype
boundaries, Unicode-distinct remaining groups, empty sources, strict option/domain
refusals, inherited name proof and earlier partial-output scope. Independent review
found no actionable defect. This is source/unit qualification, not GUI acceptance.
