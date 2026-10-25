# Native manual-pair compatibility prerequisites

Endpoint baseline: rewritten public main 7c2c474. The historical endpoint-binding
qualification is reused; repository recreation invalidated the old PR-history links. This increment continues the bounded host adaptation of manual
pair review. It reuses AIRS structural NSDictionary configuration comparison
from its existing batch/reuse code; no donor configuration DTO is assumed.
MacScope remains read-only.

## Explicit API and limits

ComparisonReport.validateManualPairCompatibility(baselineData:currentData:) first
runs the accepted endpoint validator, including source admission, byte caps,
image/model flag consistency, side-specific endpoint membership and row facts.
It then reads analysis_config from the original saved Data, rather than a typed
round trip that omits that field. No file or original binary is opened.

A present configuration must be an object with a limits object. Limits must be
nonnegative native-representable integers (UInt64 range); Boolean, string,
fractional and integral floating JSON values reject. Extra configuration facts
participate in structural equality. Two missing legacy configurations compare
equal under the existing saved-report comparison policy; one missing and one
present configuration differ. Absence does not invent defaults or qualify a
report for the separately stricter analysis reuse cache.

If analysisConfigurationChanged is supplied, it must reflect actual selected
source configurations. An absent status stays absent. Whether or not status is
recorded, different configurations or incompatible models require every manual
review row to have ambiguous classification.

Success establishes these prerequisites only. Compatible changed/unchanged labels
are not recomputed or independently verified. The method does not authenticate
images/reports, validate nonmanual matching, produce a readiness token or activate
app comparison workflows. Schema 1, model v50 and analysis semantics stay unchanged.

## Qualification

Eleven new ManualPairCompatibilityTests methods passed with zero failures in
0.016 seconds. Coverage includes equal/different limits, explicit status
contradictions, absent legacy fields, extra configuration facts, malformed values
and integral floating wire values, model mismatch, endpoint/image prerequisites,
and the explicit boundary that compatible change signatures are not recomputed.
All inputs are small synthetic JSON with placeholder digests.

The first preimplementation compile reported the expected missing API; no runtime
test executed in that check. After implementation, the real AIRSApp debug product
built successfully in 22.29 seconds under the exclusive native gate. Existing
entitlement-reader/inventory warnings remain outside this change. Other selected
test bundles ran zero methods; accepted unchanged suites were not replayed.

Independent read-only source/test review found no actionable defect and confirmed
the compatibility-only boundary. The reviewer performed no checks or writes.

Detailed qualification logs are retained privately. Accepted endpoint,
codec, Python matching/analysis and distribution results are reused. Native build
products are removed after retaining logs. Build success is not GUI acceptance.
No launch, packaging, release, installation, store/settings change or MacScope
mutation is included.
