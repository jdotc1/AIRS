# Canonical manual-pair keys

`ComparisonReport.validateManualPairKeys(baselineData:currentData:)` is an explicit
native validator for the recorded key of each `manual_review` row. It composes
matching-policy and all prior declared-row checks. The host producer uses exactly
`manual:<baseline ID>:<current ID>`, with the two selected source IDs in that order.

Both endpoints must exist, and the key must match the full canonical UTF-8 bytes.
A user label, swapped endpoint order, unrelated pair's key, alternate prefix,
whitespace or partial identifier cannot claim this key proof. Typed AIRS finding
IDs have no delimiter ambiguity. No further source decoding or candidate projection
is added by this increment.

Validated pins, one-to-one row accounting, side-specific source facts,
configuration/model compatibility and observation labels remain prerequisites.
The same key spelling applies when explicit body opt-in is recorded or source
configuration/model differences require an ambiguous row label. Manual selection
cannot override same-image offset authority.

## Scope and compatibility

Earlier validation APIs continue to accept arbitrary manual keys within their
original documented scope. Generic decoding and comparison production are unchanged;
callers choose this stricter boundary explicitly. It does not turn a key into
source-function identity, byte authenticity, regression/fix evidence or complete
producer-output reconstruction. Omitted groups and presentation fields retain
their existing boundaries. Native GUI matching and distribution gates are unchanged.


## Bounded qualification

The real AIRSApp target built successfully, and thirteen new focused native tests
passed with zero failures. Independent code/test/scope review found no actionable
defect. All composed validators are unchanged; their accepted source/accounting/
manual/symbol/body/unmatched/policy/offset/codec results are reused alongside
unchanged Python, GUI and distribution evidence within original scope. Detailed
logs remain local. No packaging, installation, GUI or new release qualification
is claimed.
