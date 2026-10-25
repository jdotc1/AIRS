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

## Implemented gates and usage

The standard-library-only publication tools now separate source, metadata and
artifact scope. They do not grant publication authority or replace signing,
notarization, functional acceptance or a human review of confidential context.

- `scripts/publication_gate.py` checks every newly outgoing commit (including
  intermediate states), approved author/committer identities, annotated tag chains,
  filenames, source content and nested ZIP contents. It also checks declared public
  text/assets. Known path/credential patterns and suspicious fixed home-root code
  reject without printing matching bytes.
- `scripts/configure-publication-gates.py` installs a local pre-push adapter only
  when it will not overwrite an unrelated hook. Supply an exact accepted baseline
  and a local evidence description. The adapter restricts the destination and
  stores its receipt in the Git common directory.
- `scripts/export-public-source.py` exports committed source only, after range
  inspection against an explicitly accepted baseline. It streams a bounded source
  archive and refuses loose local files, links and development payloads. This is
  a new export, not an assertion of byte identity with a historical source ZIP.
- `scripts/publish-public.py` preflights a private JSON plan. Its default performs
  no upload. `--execute` requires separate authority for that exact delivery. It
  verifies the account/destination, binds the actual remote PR head, requires a
  new release tag, rechecks file identities immediately before delivery and reads
  back the resulting destination metadata. Pushes share the hook receipt.

A plan declares `action` (`push`, `pull_request` or `release`), `repository`
(`jdotc1/AIRS`), `base`, `head`, explicit `text` and `assets` file lists, and
`public_metadata`. Push metadata has `destination_ref`; PR metadata has
`base_branch`, `head_branch` and `title`; release metadata has `tag` and `title`.
PR/release delivery uses one inspected body/notes file. Local plan paths belong
in ignored evidence, never tracked source. Attachments outside the declared
assets are not cleared. Existing releases are deliberately not edited by this
new-release wrapper; qualification supplements require a separately reviewed
update plan.

Example local preflight (substitute an authorized private plan/receipt):

```sh
python3 scripts/publish-public.py --plan local-evidence/publication-plan.json --receipt local-evidence/publication-receipt.json
```

ZIP inspection is bounded to 512 MiB per payload/expanded budget, 20,000 aggregate
entries, four nested archive levels and a 16 MiB central directory. ZIP64, multipart,
encrypted, malformed and unsupported archive formats fail closed for separate
qualification. Links must stay inside their top-level archive payload and name
an existing member. Nothing is extracted or executed. Source export has matching
aggregate size/entry bounds. A normal app ZIP may need a separately qualified
larger budget/format policy; the tool never silently bypasses those limits.

Accepted Git objects are reused by immutable object identity. Local file receipts
are bound to exact scanner-source bytes and file device/inode/size/modification/
change metadata, avoiding repeated hashes. They detect ordinary local changes;
they are private trusted receipts, not adversarial authentication. Policy drift
refuses stale receipts rather than silently rescanning sealed assets. An accepted
baseline must come from retained evidence; choosing an unchecked baseline would
omit it from the range and is prohibited.

## Qualification and remaining limits

Eighteen focused publication-tooling tests cover path classes, credentials,
identity/trailers, intermediate commits, nested/source archives, safe and unsafe
links, archive expansion/directory/ZIP64 bounds, exact receipt reuse, changed
assets, source export, hook integration, remote source binding and simulated
delivery/readback. No live publication or old release artifact scan was performed.
Independent review found binding and resource-bound gaps in the initial tools;
they were corrected and the affected boundary checks passed.

The fixed review-parent behavior has a successful real AIRSApp build and five
focused path-policy tests. Accepted navigation/GUI, app signing and distribution
results are reused within their original scope; changed profile roots have no
new GUI-launch claim. The release-history reconciliation supplement records
rewritten source identities and changed source ZIPs without altering original
qualification receipts.

Hooks apply to this configured checkout; fresh clones must install them. Hosted
services cannot make a local hook mandatory, and direct third-party uploads can
bypass local tooling. Contributors must use these gates for authorized delivery.
Pattern checks cannot prove the absence of arbitrary confidential prose, image
content or novel secret formats. Those require explicit scoped review; absence
of a pattern hit must never be reported as universal privacy clearance.
