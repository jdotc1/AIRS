# Component security-delta document

The separate JSON document kind is `airs.component.security-delta`, schema 1,
model `component-security-delta-v1`, rules `component-security-delta-rules-v1`.
The legacy component-review archive format is unchanged. The delta envelope
retains the exact source review archive as fixed-size base64 chunks, optional
side-bound signature documents, strict entitlement documents and signature
refusals, effective output options, and a derived report.

Import uses bounded JSON parsing, exact interpreted key sets, document-version
checks, source-document admission, side/inventory/component/path and requested
architecture binding, duplicate checks and report rederivation. It compares the
claimed canonical report bytes against the newly derived result; imported
explanations, IDs or validation claims cannot grant trust or live authority.
Unknown attachments inside the legacy source archive remain byte-for-byte
retained and uninterpreted. Unsupported schema/model/rules versions refuse.

IDs use domain-separated SHA-256 over canonical length-delimited evidence and
version-bound fields. The basis sorts semantically unordered inventory and
scope records by exact UTF-8 bytes, retains ordered declaration arrays, and
includes direction, selected architecture, supplemental document bytes and
options. No fresh export timestamp, random export UUID or localized explanation
enters derived IDs. Identical admitted input and options yield identical report
IDs and export bytes; independent captures can have different inventory and
component UUIDs. The legacy source archive may itself contain attachment UUIDs.

Typed values explicitly distinguish Boolean, signed integer, unsigned integer,
legacy-normalized integer, finite real/date bit patterns, UTF-8 string, data,
ordered array and sorted exact-key dictionary. Signed and unsigned integers use
separate tags and canonical decimal strings. A normalized historical integer
does not establish its original signed/unsigned representation. Captured source
bytes are not equivalent to authenticated original executable bytes.

Version-1 ceilings include 128 combined review components, 384 declaration
records per side, 65,536 bytes per declaration source, 32 typed-value levels,
10,000 nodes per declaration, 100,000 aggregate typed nodes, 16 MiB aggregate
decoded typed payload, 32 MiB retained evidence, 8,192 observations, 2,048
findings, 32 references per finding, 256 source records, 16 MiB per signature
document, and 32 MiB for the encoded delta file. Output options may lower the
observation/finding ceilings. The signature reader also enforces its existing
streaming, header, signature-byte and slot ceilings. Rendered lists and typed
collections are paged; full retained strings and bytes can be inspected in
bounded pages.

An input that cannot be safely admitted is refused. A report with capped output
identifies omitted records, whether the count is exact or a lower bound, and
whether omission details are complete. A finding requiring more than the
reference ceiling is omitted as a whole, rather than silently losing supporting
references. A related-component finding requiring more than 32 distinct
limitations is likewise omitted and counted under `limitation_limit`.
Final export can refuse independently when the encoded envelope
would exceed its cap; a valid report and captured evidence remain in the session.
These are allocation/work limits, not a process resident-memory guarantee.

The analyzer and delta archive entry points expose `SecurityDeltaRefusal.code`
for classified failures. Specific cases include `component_limit`,
`duplicate_component_identity`, `duplicate_observation_identity`,
`evidence_binding_mismatch`, `component_correspondence_unaccepted`,
`typed_depth_limit`, `typed_node_limit`, `decoded_byte_limit`,
`retained_byte_limit`, `document_size_limit`, `export_size_limit`, and the
unsupported-version codes. A legacy validator that exposes only an unspecified
limit becomes `resource_limit`; it is not assigned a falsely precise budget.
`invalid_review` covers malformed records and disagreement with rederivation.
Structured task cancellation remains `CancellationError`. Direct legacy review
codecs retain their existing error contract; individual evidence adapters can
also expose their underlying legacy validation errors.
