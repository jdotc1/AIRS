# Native exact-image offset authority

Baseline: public main e287ee6, matched-change label verification merged in public
PR6. This bounded increment applies AIRS's existing Python exact-image precedence
and numeric-offset grouping contract. It reuses the unique-group/no-guess pattern
from MacScope FunctionVersionMatcher; the donor matcher does not supply AIRS's
exact-image phase or its precedence rule. No donor framework is imported and
MacScope remains read-only.

## Explicit API

ComparisonReport.validateExactImageOffsetRows(baselineData:currentData:) first
composes validateMatchedChangeLabels, retaining row accounting, source admission,
selected-source facts, manual-selection, compatibility and observation checks.
Existing immutable Data and 64 MiB per-source bounds remain authoritative.

For different declared source images, any exact_image_offset row rejects. Other
cross-image bases retain the composed checks but their matching semantics are
outside this API. For the same declared image, every row must use exact-image
offset authority; symbol, body or future bases cannot replace host precedence.
Same-image identity follows the existing admitted slice-digest/architecture facts,
not a new hash or authentication of original bytes. Context UUID facts retain
their existing source-binding rules.

Each same-image row requires canonical offset:0x<lowercase-hex> spelling without
redundant leading zeros. The helper groups each source's findings independently
by numeric image-relative offset, preserving the distinction from preferred VM
addresses. Alternate source offset spellings group numerically; row keys remain
canonical. The declared offset must exist on at least one source side.

A side selects its finding ID exactly when its group has one candidate. A group
with no candidates or multiple candidates must not select an ID. Thus a valid
source ID cannot be joined under another existing offset's key, and unique
candidates cannot be hidden as unselected ambiguity.

| Source group sizes | Selected endpoints | Required classification |
| --- | --- | --- |
| 1 baseline, 1 current | Both unique IDs | Composed observation/compatibility result |
| 1 baseline, 0 current | Baseline only | removed |
| 0 baseline, 1 current | Current only | added |
| Either side has multiple candidates | Only singleton sides select IDs | ambiguous |
| Neither side has a candidate | None | Reject nonexistent group |

This preserves one-sided selections in ambiguous groups without inventing a pair.
It also preserves ambiguity for unique pairs with differing models/configurations,
as determined by the existing composed validator. Row order is not used as
identity or grouping evidence.

## Limits of success

Only declared groups are checked. Omitted source groups and empty comparisons
remain permitted; this is not source completeness or a full matching result.
Cross-image symbol/body matching, source-function identity, imported digest truth
and original binary authenticity remain separate. Default report decoding and
native workflows do not automatically invoke this strict API.

Grouping and row passes are bounded linear work over the admitted source finding
and row limits. The composed validators use repeated bounded decoding passes;
this is not a single-pass parser. No path, target binary, runtime or user store is
read, executed, hashed or modified. Native targets remain macOS 14+, schema 1 and
engine model v50, with no dependency or supported-instruction expansion.

## Qualification

Twelve new ExactImageOffsetRowsTests methods passed with zero failures in 0.047
seconds. The real AIRSApp debug product built successfully in 22.42 seconds under
the exclusive native gate. The first preimplementation compile reported the
expected missing API and executed no runtime test method. Accepted unchanged
matched-label, source-fact, accounting, manual, codec, Python, GUI and distribution
results were reused rather than replayed.

Coverage includes valid unique groups, preferred-VM relocation, numeric source
offset normalization, canonical and malformed/overflow keys, wrong existing-group
joins, duplicate baseline/current/both-side groups, hidden unique endpoints,
added/removed one-sided groups, observation/configuration guards, architecture
identity, same-image precedence and explicit omission/cross-image scope limits.
Inputs are small synthetic report JSON with placeholder digests, not user reports
or a binary corpus. No target code is executed.

Independent read-only source/test review found no actionable defect and confirmed
host/donor attribution and conservative group handling. Detailed logs remain
private; generated native build products are removed after retaining receipts.
Build success is not GUI or installed-app acceptance.

No packaging, signing, installation, production settings/store change or MacScope
mutation is claimed by this qualification. Installed app, settings and stores
remain unchanged; public integration does not activate native workflows.
