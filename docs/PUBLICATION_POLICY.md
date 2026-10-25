# Public publication policy

Sanitization is a prerequisite for every authorized public delivery. This policy
does not authorize a push, release, destructive history rewrite or repository
recreation. Existing verification and release gates remain in force.

## Scope before publication

Identify the exact repository, outgoing refs/commits, public text and assets.
Record the expected source identity and any valid accepted sanitization receipts.
A clean current tree is not evidence that earlier outgoing commits are clean.
A signed executable is not evidence that its source archive or release notes
are suitable for publication.

Review these distinct surfaces when new or changed:

- Tracked source, tests, documentation, fixtures, manifests, generated files and
  vendored content; include filenames, symlink targets and textual metadata.
- Every newly outgoing commit and tag: contents, messages, author and committer
  identities, tagger identities and trailers. Use approved public identities.
- Pull-request and issue titles, bodies, comments, attachments, workflow summaries
  and release text. Avoid inserting private details and editing them away later;
  earlier revisions may remain visible.
- Source archives and release assets, including embedded file metadata, paths,
  debug strings, qualification records, receipts and checksums. Each artifact
  needs its own applicable evidence; source clearance alone is insufficient.

Exclude credentials, private contact information, host/user identifiers, personal
absolute paths, private working-directory conventions, temporary session paths,
private repository references and internal coordination/provenance text.
Do not print matching credential bytes in reports. Use repository-relative names,
neutral fixture paths or generic wording in public material. Preserve required
licenses and legitimate third-party attribution.

## Preserve local functionality

Machine-specific locations belong in ignored local configuration or the execution
environment, with documented portable defaults where appropriate. Do not store
local paths in GitHub repository variables or public CI definitions. Runner-local
configuration may supply them. Redacting a path must not leave an empty operand,
invalid containment check, broken command or misleading receipt.

Qualify changed configuration behavior with the smallest relevant checks. Retain
accepted build/runtime results only where inputs and behavior remain unchanged;
explicitly identify repaired-but-unqualified paths. Sanitization must preserve
installed apps, settings, stores and unrelated checkouts unless changes are
separately authorized.

## Evidence and release decision

Keep private findings and detailed local logs outside tracked source. A local
receipt records exact outgoing identities, covered surfaces, accepted results
reused, changed-boundary checks and unresolved gaps. Never describe a component
scan as a whole-publication clearance. Do not rerun sealed checks on unchanged
inputs; inspect new/changed surfaces or obtain permission when a repeat is needed.

Review the final rendered public text before submission. After publication,
confirm the actual destination refs, identities, text and asset metadata against
the approved delivery, without replaying unchanged analysis or signing checks.
A failed or incomplete surface blocks that surface's publication.

If exposure is discovered, stop further publication, preserve private evidence
and identify affected surfaces. Repository deletion/recreation and force-pushes
require explicit authority and a recovery plan covering issues, PRs, releases,
protection, runners and other metadata. Do not claim deletion removes all cached
or historical copies.

## Required implementation before the next delivery

This document establishes the required review scope; it is not an automated gate
or a claim that all existing publication tooling implements it. The existing
release-content checker covers selected application payloads and vendored source,
not the full publication surface above.

Before the next public delivery, add and qualify outgoing-commit path/identity
checks, public-text checks, unpacked-asset checks and export-filter pattern tests.
Review source-path rewrites semantically and reconcile rewritten source identities
with qualification records. A regenerated source archive is a changed artifact;
unchanged app qualification does not establish its original byte identity.
