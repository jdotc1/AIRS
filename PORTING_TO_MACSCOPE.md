# Porting component security change analysis to MacScope

This document describes the AIRS interface and the additional work a separate
MacScope project would need. It does not authorize or describe an implemented
MacScope integration. **AIRS acceptance does not establish MacScope integration
acceptance.**

## Portable boundary

The pure analysis entry points are in `AIRSEntitlements`:

```swift
try ComponentSecurityDeltaAnalyzer.analyze(review: review, options: options)
try ComponentSecurityDeltaAnalyzer.analyze(input: input, options: options)
```

`SecurityDeltaInput` holds a captured `ComponentReview` and optional side-bound
signature documents, strict entitlement documents, and signature refusals. The
analyzer accepts no URL, file descriptor, bookmark, discovery callback, or live
read capability. It checks cancellation and otherwise derives its output from
the admitted input, options, and model/rules versions. `SecurityDeltaOptions`
can lower the observation and finding ceilings, never raise their hard limits.
The analyzer and delta archive entry points expose `SecurityDeltaRefusal` for
classified rejections, with `resource_limit` for a legacy validator whose exact
budget is unavailable. Handle `CancellationError` separately. Direct evidence
adapters and legacy archive codecs can still return their own validation errors.

Portable model families include component and review identities, exact slice
descriptors, `SecurityDeltaValue`, source states, dispositions, evidence
references, observations, finding kinds, reasons, coverage, omissions and the
versioned report. The current implementation also depends on AIRSCore's
inventory, discovery record and matching models, EntitlementDiff's declaration
types, Foundation and CryptoKit. These dependencies need explicit vendoring,
replacement or adapters in the receiving project; this is not a standalone
binary framework or an assumed MacScope private API.

## Evidence and identity adapters

The host must establish previous/current direction, stable per-capture inventory
and component UUIDs, exact UTF-8 relative paths, recorded parent relationships,
and bounded scope/exclusion records. It must supply admitted declaration and
entitlement snapshots with side, inventory, component, source and architecture
bindings. Matching must reconstruct the AIRS exact-location relation; an
identifier, filename or suggested relocation is not accepted as identity.

An architecture label alone does not qualify a signature-slice join. Preserve
raw CPU type, full subtype/capability bits, header magic, source index, offset,
size and recorded digest. Slice offsets and indexes may differ between builds.
Unsupported mappings and mismatched raw identities must remain unresolved.
Exclusion of a symlink or special file is not proof of absence.

Newly acquired strict entitlement evidence must come from the opt-in exposed
numeric decoder and retain Boolean, signed and unsigned tags. The captured API
representation does not prove source-language signedness. Legacy schema-1
snapshots are treated as normalized historical values: equal numeric values do
not establish their original representation. Never reconstruct a lost tag.

The host owns explicit acquisition, descriptor-relative no-follow traversal,
source freshness checks before and after reads, secure capability lifetime,
size budgets and cancellation. Imported documents are historical and cannot
acquire live authority. Never execute a selected executable, resolve dynamic
dependencies as a side effect of analysis, or infer signature trust from raw
structural evidence.

## Serialization and presentation

`ComponentSecurityDeltaArchive` is a separate
`airs.component.security-delta` schema-1 document. Its model and rules versions
are `component-security-delta-v1` and `component-security-delta-rules-v1`.
It retains source review bytes, bound supplemental evidence, options and the
derived report. Import admits source documents and recomputes the supported
report; imported explanations, identifiers, counts and references do not
constitute a validation receipt. Unsupported versions and invalid bindings are
refused. The legacy component-review archive stays a separate format.

Stable IDs and export bytes are guaranteed only for identical admitted source
bytes, direction, options and version identifiers. Independent recaptures can
produce different inventory/component UUIDs. Exact byte strings, typed numeric
tags and ordered arrays must not be normalized by an adapter. Preserve unknown
legacy attachments in their original enclosing source bytes.

A host UI needs explicit direction and architecture confirmation, bounded
finding and observation pages, component/category filters, full retained-value
and source-locator inspection, coverage and omission details, and a clear
historical/live distinction. Each acquired revision needs a new evidence basis;
cancelled, stale, or superseded work must not be published as current. Captures
are sequential observations, not an atomic application snapshot.

## Refusal and qualification boundaries

Keep candidate moves, ambiguous matches, incomplete/excluded scope, missing
category captures, failed reads, stale capabilities, unexamined slices and
malformed references distinct. Never turn them into a missing declaration or
agreement. Report output caps and omitted detail counts; do not infer runtime
library loading, effective authorization, privacy compliance, notarization,
trust, maliciousness or a security score.

Before claiming MacScope acceptance, independently repeat synthetic fixtures
covering exact versus candidate matching, partial inventory, Unicode-distinct
paths, Boolean versus integer and signed versus unsigned values, unavailable
versus absent/empty evidence, duplicate loader rows and order, exact raw slice
identity, conflicting evidence, malformed/dangling archive references,
deterministic ordering and output, resource caps, cancellation, historical
reopening and stale-result rejection. Then perform a host-specific UI and
lifecycle qualification using explicitly authorized owned bundles. A passing
AIRS fixture or native AIRS session is not a substitute for those checks.


## Separate Swift outcome-witness contract

Advanced Swift error-flow adaptation is specified in
`docs/PORTING_SWIFT_OUTCOMES_TO_MACSCOPE.md`. It has separate model, byte-admission
and qualification requirements; the component-security contract above is preserved.

## Separate imported-callee attribution note

Stub attribution, imported declaration syntax and GOT-loaded call attribution are
described in `docs/PORTING_SWIFT_IMPORTS_TO_MACSCOPE.md`. It is attribution only and has
its own model identities, limits and refusal reasons.

## Real-release qualification replay

The independent corpus protocol, source manifests, owned mutations and host replay
gates are documented in
[the real-release portability acceptance contract](docs/security-delta-real-corpus/PORTING_ACCEPTANCE.md).
AIRS acceptance does not establish MacScope integration acceptance.
