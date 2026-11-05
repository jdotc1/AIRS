# Component security change analysis

The Security Changes mode extends Component Review with a static, evidence-linked
explanation of previous → current component changes. It is not a malware
detector, trust verdict, compliance decision, runtime authorization result, or
security score. AIRS does not execute inspected code or resolve dynamic library
paths during analysis.

The existing inventory and matcher establish the recorded scope and component
relationships. Only accepted exact UTF-8 locations support direct before/after
declaration comparisons. Identifier-based relocation candidates and ambiguous
matches remain unresolved. Incomplete inventory, exclusions and failed reads
do not establish absence.

`ComponentSecurityDeltaAnalyzer` consumes the captured review and side-bound
supplemental evidence without opening a bundle. It derives inventory, Info
allowlist, loader, entitlement, privacy and available signature observations.
Presence and values are distinct: absent, unavailable and unexamined are not
empty dictionaries. Legacy entitlement integers may have unspecified original
representation; new opt-in captures retain the signed, unsigned and Boolean
types exposed by the source API.

Loader observations describe recorded commands and dependency declarations;
they do not show that a library was resolved, loaded or executed. An absent
privacy manifest is not a compliance finding. Signature observations describe
recorded byte ranges, slot data and digests; they do not establish signature
validity, certificate trust or notarization. Whole-container and slice digests
describe different scopes. Captures at different times do not form an atomic
application snapshot.

Rules can relate multiple changed categories in the same accepted component,
or changes in components whose recorded parent chains share an accepted
ancestor. Matched components require the relationship on both sides; accepted
additions and removals use their observed side and opposite-side scope evidence.
The finding includes every selected component or is omitted with an explicit
reference-limit count. Repeated-declaration findings require the same complete
typed transition. Unknown numeric representation and missing endpoints are
excluded from that exact-transition rule. Findings describe recorded
relationships without suggesting causation.

The native workflow derives an initial report from captured data and recorded
unexamined states. Individual component entitlement and signature captures are
explicit actions; prior acquired evidence is not silently overwritten. A new
review is currently required to recapture the same category for the same side
and component. Historical imports cannot authorize capture. A failed or stale
capture remains unavailable, and cancelled or superseded jobs are not published
as current.
When a strict capture is incomplete, a separately recorded legacy pair remains
usable with its historical numeric-fidelity limitations. A demonstrated
contradiction between a strict side and its legacy snapshot blocks the dependent
comparison and is shown as unresolved evidence.

The view provides category and exact-path filters, pages of findings and
observations, typed-value inspection, recorded evidence locators, source bytes,
and coverage details. Filters affect presentation only. The component review
archive and the separately exported security-delta document are distinct;
the latter contains supplemental evidence. See
`COMPONENT_SECURITY_DELTA_FORMAT.md` for wire and limit details and
`COMPONENT_SECURITY_DELTA_RESULTS.md` for qualification status.

## Opt-in real-release qualification

A separate read-only corpus harness exercises authentic releases without adding
network or filesystem authority to the analyzer. See
[the corpus protocol](security-delta-real-corpus/SPEC.md),
[reproduction instructions](security-delta-real-corpus/RUN.md), and
[qualified results and limitations](security-delta-real-corpus/RESULTS.md).
Ordinary application behavior and legacy export contracts are preserved.
