# Track A independent review — round 2

A second independent reviewer examined the amended evaluator, native test harness,
archive tampering and admission boundaries. The reviewer performed source review
only, with no tests, builds, hashes, network requests or corpus scan.

| Priority | Concrete issue | Correction / disposition |
| --- | --- | --- |
| High | Relabeling a component while retaining another component's evidence paths could receive support | Validate source ownership using independent Info executable declarations and exact component paths; bind reference UUIDs/sides to retained inventories and archive contents; validate acquisition receipt and capture-driver sides against strict manifests |
| High | Root Contents/Resources privacy changes were omitted from expected changes | Explicit root/nested/framework source-layout mapping; both executable owners checked before use; three-layout owned regression RED/GREEN |
| Medium | Protocol accepted x86_64 but harness/checker selected arm64 | Qualification version 1 explicitly refuses non-arm64 evaluation; driver refuses an explicit unsupported architecture; original run was entirely arm64 |
| Medium | Failed XCTAssertFalse did not prevent evidence replacement | Throw before encoding/writing; publish through a fresh owned temporary file and no-overwrite hard link; owned destination-preservation fixture passed |
| Medium | Unbounded JSON reads bypassed manifest/structural admission | Strict manifest loader, bounded no-follow reads, pre-parse nesting bound, duplicate keys/identities, bounded collections and classified malformed-input refusal; owned input-boundary fixture passed |

The checker compares flat report data with the retained historical report body,
checks side inventories against embedded source attachments, and resolves component
references before source adjudication. Internal archive consistency and authentic
release provenance remain separate: acquisition receipts/driver path bindings and
independent raw facts support the latter. A serialized admission flag does not
confer trust or live authority. Native archive admission/rederivation receipts are
reused separately; the Python checker does not replace that codec.

Counts produced before these repairs are provisional historical evidence. The
post-repair ledger supersedes their interpretation without deleting them. Finding
support denotes constituent source-fact support; correlation ancestry and wording
have a separate review/qualification boundary.

The review explicitly rejected treating state-model tests as visible native UI
acceptance. Visible historical review has been inspected separately; remaining
native interactions and environment-specific gates are recorded in RESULTS.md.
No release, signing, installed-source acceptance, clean-machine, minimum-OS or
MacScope acceptance is established by this review.

## Closure and later field coverage

Repair closure found three additional counterexamples: a default finding-kind
branch could promote unchanged source facts; privacy enumeration needed exact
before/after executable-owner agreement; and null declaration component IDs could
skip binding checks. Each received a new owned RED/GREEN fixture and correction.
Unknown/conflict kinds remain unresolved. Shared ancestor bridges now require the
exact path to exist in both inventories. The second reviewer closed these three
items on source inspection and found no further blocking issue in those repairs.

The added minimum-OS/section parser and separately approved range observations
preserve raw CPU/subtype, fat-table location, header and UUID correspondence. They
retain raw command ranges and first range digests without rehashing old containers.
They remain later non-atomic evidence. A valid XML plist without an XML declaration
exposed a format-autodetection limitation; an owned RED/GREEN regression fixed it,
and four previously unavailable xbar Info observations were first successfully
retained. Earlier failed records remain historical evidence.

The reviewer also accepted the proportionate layout-only correction: findings and
observation lists have bounded widths and the inspector retains readable width.
The real AIRSApp target built, and five historical native cases plus one separately
authorized live selection/capture/export/reopen workflow were inspected. Those
execution receipts belong to the implementing run, not the source reviewer.
