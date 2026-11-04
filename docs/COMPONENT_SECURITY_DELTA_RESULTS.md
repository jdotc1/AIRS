# Component security delta qualification

Focused synthetic tests cover exact and ambiguous component correspondence,
inventory coverage and exclusions, typed values, entitlement and loader
declarations, privacy manifests, signature evidence, correlation, historical
archives, resource limits, cancellation, and native workflow state. The native
AIRSApp target built and an unsigned debug build completed a synthetic review,
signature capture, evidence inspection, export and historical reopening.

These results do not establish signature trust, runtime behavior of inspected
components, real-application acceptance, notarization, or MacScope integration.
The native debug run logged AppKit invalid-view-geometry diagnostics whose cause
was not established. An end-to-end oversized export and actual blocking inside
Security.framework were not exercised; bounded preflight and task-settlement
paths were tested with synthetic inputs.

Independent technical review findings and corrections are documented in
`COMPONENT_SECURITY_DELTA_REVIEW_ROUND_1.md` and
`COMPONENT_SECURITY_DELTA_REVIEW_ROUND_2.md`.
