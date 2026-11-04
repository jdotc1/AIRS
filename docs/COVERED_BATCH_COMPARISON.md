# Opt-in covered batch comparison acceptance

The `BatchComparisonRunner(requireSavedReportCoverage: true)` policy
uses covered saved-report decoding at the runner's existing acceptance point.
The policy is immutable for that runner. The original no-argument initializer
continues to select legacy identity-only acceptance, preserving existing GUI
callers and initializer references.

Strict decoding occurs after the existing output-budget and cancellation checks,
before accepted output consumes budget or populates the row's comparison fields.
The existing image-identity guard remains after decoding. Refused output follows
the existing unavailable-row path with no accepted payload; later pairs continue.
Progress, cancellation, pairing, retained source reports and export behavior retain
their established contracts.

This is an explicit native runner policy, not GUI activation or a global decoder
change. Covered acceptance establishes saved-report group coverage and composed
field checks. It does not authenticate fingerprints/binary bytes, prove function
identity or establish GUI acceptance. Historical absent cross-image body metadata
refuses strict mode while remaining available to the unchanged legacy path.

## Qualification

The real AIRSApp target built successfully. Ten focused async methods qualified
through nine accepted results and one corrected exact-payload check, covering
strict success branches, default initializer compatibility, missing status,
omitted groups, forged names, continuation/progress, cross-run stale-state
prevention and refusal export. Independent review found no actionable production
defect and accepted the corrected payload assertion. No unchanged suite was
repeated. This is source/unit integration; the GUI remains on legacy acceptance.
