# Native manual-row change evidence

Baseline: public main ad6babe, manual-pair compatibility merged in public PR2.
This bounded increment adapts MacScope UnwindAuditComparator.Signature's separation
of matching and audit observations, using AIRS's existing Python comparison
signature as the host contract. MacScope is read-only; no donor framework or
new dependency is imported. Schema 1 and engine model v50 remain unchanged.

## Explicit API

ComparisonReport.validateManualPairChanges(baselineData:currentData:) first reuses
source-endpoint and saved-configuration/model compatibility validation. Original
Data arguments retain the existing 64 MiB per-source limit. It then compares
selected source findings for manual_review rows only. No file or target image is
opened, executed, decoded or hashed. The report is not mutated or reclassified.

For compatible inputs, the declared row label must equal unchanged or changed
according to this signature:

| Finding fact | Comparison rule |
| --- | --- |
| Verdict, coverage, mode, scope | Exact admitted values |
| Optional encoding | Original string; no numeric normalization |
| Reason codes | Sorted wire strings, retaining duplicates |
| Checked PCs | Ordered offsets from each function start |
| Evidence | Ordered code, expected, observed and relative-address facts |

Evidence expected/observed values retain schema 1 string-or-null admission.
Missing and null values compare alike; an empty string is distinct. Free-form
strings compare their UTF-8 bytes so canonically equivalent but differently
encoded strings are not collapsed by native String equality. Evidence offsets
use signed magnitude across the full admitted UInt64 VM range, including addresses
before function start. No subtraction underflow or clamping is used.

Names, absolute relocation, evidence messages, limitations, body fingerprints,
instruction counts and other facts outside the existing host signature do not
create finding changes. Reason-code order is ignored, but checked-PC and evidence
order remain meaningful. This is a report-finding comparison, not code equivalence.

When source models or configurations differ, manual rows must be ambiguous.
Compatible rows cannot simply choose ambiguous to evade signature checking.
The reused endpoint helper and new exact model-label guard conservatively refuse
canonically equivalent but differently encoded unknown model labels. This edge
is fail-closed, not full Python acceptance parity for an ambiguous row.

## Deliberately incomplete admission scope

Success verifies manual labels and their prerequisites only. Nonmanual rows and
summary integrity remain outside this API, as demonstrated by a boundary test.
It does not authenticate image digests or report findings, recompute matching,
establish function identity or a regression/fix, issue a readiness token, or
activate native app/GUI workflows. Each of those remains a separate gate.

The source reports are admitted in a bounded constant number of parsing passes;
lookup and row passes remain linear apart from sorting reason codes. The API
preserves exact source bytes as inputs and does not cache or modify user data.

## Qualification

Fourteen new ManualPairChangeTests methods passed with zero failures in composed
receipts: twelve in the initial class run, then only two additional scope/order
methods. Earlier accepted tests were not replayed. The first preimplementation
compile reported the expected missing API and executed no runtime test method.

Cases cover positive unchanged/changed rows, each observation field, raw encoding
format, reason ordering and duplicate counts, checked-PC/evidence order, optional
null/empty distinctions, ignored presentation facts, Unicode wire differences,
large VM relocation, negative evidence offsets, incompatible ambiguity, exact
model labels, source-binding prerequisites, and the explicit nonmanual/summary
scope boundary. All inputs are small synthetic JSON with placeholder digests.
No user reports, binary corpus or target execution is involved.

The real AIRSApp debug product built successfully in 15.41 seconds under the
exclusive native gate. Independent read-only source/test review found no
actionable defect and confirmed the model-label refusal limitation. Detailed
logs are retained privately; generated build products are removed afterward.

Accepted compatibility, endpoint, codec, Python comparison, GUI and distribution
results are reused within their original scopes. No fresh GUI acceptance,
packaging, signing, installation, publication or MacScope mutation is claimed.
Installed app, settings and stores remain unchanged. The helper remains opt-in; public integration does not activate native workflows.
