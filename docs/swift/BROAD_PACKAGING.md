# Complete broad Swift local handback

`scripts/package_swift_broad_handback.py` prepares one local ZIP only after the
parent has finished qualification, review, check accounting and source/export
boundary clearance. Preparing this script does not authorize executing it.
It does not compile, disassemble, hash source/captures, recheck signatures, run
qualification, upload, publish or provide cross-device delivery.

The accepted source baseline is `0b192429cbfb5583557c4c5f04017b1946141e4a`.
Reuse its retained acceptance. Inspect only the new/changed source and export
metadata boundary before executing the packager. The complete committed tracked
source tree is streamed from Git objects, including native targets, root build
files, licenses, all tests, schemas, documentation, reviews that are tracked,
and fixture formats such as `.macho`, `.bin` and `.png`. There is no extension
allowlist. The Git database, raw private history and loose working files are excluded;
a bounded sanitized commit-ID/subject inventory is supplied separately. Tracked caches,
credentials, unsafe names, links, submodules or special files cause refusal
rather than silent omission. The stream uses `ls-tree` and exact blob `git show` calls;
`export-ignore` and `export-subst` attributes cannot omit or rewrite files.
Archive member names must match the complete tracked file tree. An archive is not evidence
that every B1–B12 gate passed.

## Required inputs and identities

Commit the final source first. Supply two captured compiler directories explicitly;
there are no personal-path defaults. Each contains `compile-receipt.json`,
`compiler-index.json`, `source-manifest.json`, owned `.swift` source and one
`nm-MODE.txt` and `objdump-MODE.txt` per captured optimization mode. The full
qualification JSON must use `airs.swift-broad-qualification.v1`, contain all
26 named current harness gates with literal `true` values for completion, and
retain the original raw PC/word observations and gate
states. Supply two to eight whole-branch review records and the parent check
ledger as JSON. Review files must resolve to at least two distinct paths and
identify at least two reviewers. Every completion-counted record must have
`scope: whole_broad_branch`, `decision: passed`, an empty `unresolved_findings`
list, a `correction_history` list and `source_revision` equal to the qualified
engine revision. Duplicate review paths/identities or stale/partial reviews keep
the package incomplete. The check ledger is a **scoped readiness record**, not
a claim that packaging or delivery has already finished. Default staging requires:

```json
{
  "scope": "implementation_qualification_reviews_source_export",
  "state": "ready",
  "remaining_work": [],
  "task_remaining_work": [
    "Stage the complete portable local artifact",
    "Complete an explicitly authorized private cross-device delivery"
  ]
}
```

`remaining_work` describes only implementation/qualification/review/source-export
readiness; an empty list is required within that scope. Preserve packaging,
delivery and any other whole-task items separately in `task_remaining_work`.
Missing or contradictory readiness blocks default staging. A future ZIP cannot
require a fictitious already-complete whole-task ledger. The manifest records
`qualified_source_package_content_ready` and `NOT_ESTABLISHED_BY_PACKAGER` for
whole-task completion; the parent accounts for final artifact/delivery outcomes
after those separate operations.

The parent source-clearance JSON requires these exact fields:

```json
{
  "accepted_baseline": "0b192429cbfb5583557c4c5f04017b1946141e4a",
  "accepted_baseline_reused": true,
  "package_head": "EXACT_FINAL_COMMIT",
  "state": "passed",
  "scope": "complete_tracked_source_and_new_export_metadata",
  "additional_export_surfaces": [
    "baseline_to_head_patch",
    "sanitized_commit_inventory",
    "archive_root_handoff",
    "scoped_sha256_manifest"
  ]
}
```

Add the actual review evidence and unresolved scope details to that record.
The packager checks this supplied decision; it does not create or independently
prove the clearance. The final changed export views receive a narrow path check.
No original accepted capture or source is rehashed or reverified.

`qualification.source_revision` is recorded separately as
`engine_qualified_revision`; the exact packaged commit is `package_head`.
Post-qualification changes are restricted to documentation, tests, the packager,
README and CHANGELOG. A changed engine, native target, root build configuration,
qualification harness or other script refuses staging until qualification covers
that identity. A documentation-only final commit does not assert a new engine
qualification.

## Sanitized and relocated evidence

Original receipts, raw compile logs and local custody records stay private.
Included JSON is wrapped as `SANITIZED/RELOCATED`, with custody and filesystem
identity metadata removed. Source/image digests, compiler version, target,
optimization flags, command argument vectors, counts and raw instruction evidence
are preserved. These copied digests are retained evidence, not a new cryptographic
attestation. The current archive is not assigned a fabricated digest.

Capture roots, captured compiler-bin roots and SDK roots become relative
`captures/`, `toolchains/` and `sdks/` locations. Explicit additional
`--relocate-prefix ABSOLUTE=relative` mappings cover qualification/review roots
and other known private prefixes. Residual recognized machine paths cause refusal
without printing their bytes. Mapping a path does not clear confidential prose;
the parent must review the new export surface and include filenames/metadata.

Each capture includes a `REPRODUCE.sh` with shell-quoted captured argument vectors
and preserved target/flags. Install the exact recorded compiler and SDK, map them
to the relative locations, create module caches and run from `AIRS/evidence`.
After relocation, every compiler path operand must be relative, including
attached `-I`, `-F`, `-L`, SDK/module options, prefix maps and linker operands.
Unmapped absolute paths under any root (including `/opt`, `/usr/local` and
`/scratch`) are refused. Public HTTP(S) URLs and ordinary flags are preserved. Unknown joined options
containing slash/backslash are refused; explicitly supported relative Clang
include forms remain portable. Relocation occurs once per object key, with a
bounded per-object key set refusing collisions created by redaction.
These commands reproduce owned fixtures; they do not recreate historical custody
or independently establish old qualification. The complete source tree includes
qualification tools, tests, schemas and their usage documentation. Read the
retained work/check ledgers for the commands actually run and their limits.

Owned capture `.dylib` files are deliberately omitted because portable binary
clearance has not been established. The manifest states that omission. Owned
source, original image digests, compiler-index/raw PC and instruction words,
compiler identity and sanitized captured nm/objdump views remain available.
The package must not claim to contain executable capture artifacts.

## Patch, commit inventory, handoff and SHA-256 scope

The archive additionally contains `HANDOFF.md` at its root,
`AIRS/changes/BASELINE-TO-HEAD.patch`, `AIRS/changes/COMMITS.json`, and
`AIRS/evidence/SHA256-MANIFEST.json`. These four surfaces count toward the same
evidence allocation, expanded-size and aggregate entry bounds.

The patch covers the exact accepted baseline through the package head and uses
Git's full-index binary-patch representation, including binary fixture changes.
It disables external diffs, text conversion, rename shortcuts, relative path
configuration and expanded submodule history. It has a 64 MiB byte bound. Patch
bytes are preserved rather than redacted, because edits would invalidate the
complete reviewed change record. Parent clearance must cover removed as well as
added text, file names and binary patch metadata. A generic private-path pattern
check is not applied to this exact patch: neutral path-pattern regression
fixtures can legitimately contain those strings. This is explicit reliance on
the parent's exact-head export review, not a claim of automated patch clearance.

The reverse-topological baseline-to-head commit inventory retains only commit
IDs and sanitized subjects, not authors, committer identities, emails, dates,
bodies, intermediate file snapshots or `.git`. Known path prefixes are relocated
and email-shaped subject text is redacted. Its Git output is bounded to 1 MiB
and its record count to 4,096. Human review of confidential subject wording is
still part of the separate new export-surface clearance.

The root handoff gives relative navigation, the accepted baseline, exact package
head, engine-qualified revision, scoped readiness, false/missing gates and the
parent's exact separate remaining-work lists. Local staging remains distinct
from whole-task completion and cross-device delivery.

The SHA-256 manifest copies **existing** owned source and emitted-image digests
from the retained capture receipts. Its explicit coverage is the original
captured bytes only. Relocated source/evidence views, the source snapshot,
patch, inventory and handoff have no member digest coverage. Captured image
artifacts remain omitted. No missing digest is generated and no unchanged
source or capture is hashed. The final ZIP is labelled `UNSEALED_BY_PACKAGER`;
a separate authorized first seal may identify that newly created artifact in an
adjacent sidecar. There is no invented whole-member manifest and a ZIP cannot
contain its own final hash.

## One final local operation

Run under the shared storage guard only when the parent authorizes the final
local export and all required inputs exist. This is the unrun command template;
substitute the explicit input/output paths in the task's Developer directory:

```sh
storage-guard run -- python3 scripts/package_swift_broad_handback.py \
  --root "$AIRS_ROOT" --head "$PACKAGE_HEAD" \
  --primary-capture "$PRIMARY_CAPTURE" \
  --second-capture "$SECOND_CAPTURE" \
  --qualification "$QUALIFICATION_JSON" \
  --ledger "$CHECK_LEDGER_JSON" \
  --source-clearance "$SOURCE_CLEARANCE_JSON" \
  --review "$REVIEW_ONE" --review "$REVIEW_TWO" \
  --relocate-prefix "$QUALIFICATION_ROOT=evidence-origin/qualification" \
  --output-dir "$EXISTING_REGISTERED_EXPORT_ROOT" \
  --archive-name "$SAFE_ARCHIVE_BASENAME" \
  --marker "$EXISTING_REGISTERED_EXPORT_ROOT/$SAFE_MARKER_BASENAME" \
  --execute-final-local
```

`--output-dir` names the actual existing export root and is recognized by the
shared storage guard. Reuse a currently registered root; this mode does not
create, register or rename an export directory. `--archive-name` must be an
explicit nonblank single basename without separators, absolute/drive-qualified
forms, control characters or any `..` substring. The directory itself must
exist and must not be a symlink. The output filename cannot be a symlink.
The marker must be a direct child of that same directory and have a safe
basename. Output paths are derived before capture/qualification metadata reads.

Legacy `--output FILE` remains available as a mutually exclusive mode; it
refuses `--archive-name` and retains its original marker-path semantics. Neither
mode grants storage admission or permits replacing an existing artifact. Use
the real `--output-dir` root rather than an unrecognized flag or file-path
alias to avoid introducing another export root. The storage registry and its
thresholds remain authoritative and are not changed by this tool.

The source budget is 256 MiB; the ZIP and aggregate expanded budget are 512 MiB,
with 20,000 aggregate entries. Raw evidence input files and retained serialized evidence each have their own
unchanged 256 MiB aggregate cap. A separate 16 GiB processing-charge allowance
accounts for repeated decoding/parsing, relocation and serialization operations.
Those conservative cumulative charges are work units, not output bytes, a peak
RSS measurement or a RAM guarantee. Repeated conversions no longer consume the
serialized-output cap. JSON depth remains 64 and token count is capped at
16 million per input; each input remains bounded at 128 MiB. Escaping uses
4,096-character chunks before growing a serialized buffer, and payload retention
checks the remaining shared 256 MiB cap. No member is omitted or truncated to fit. JSON output
streams bounded tokens rather than materializing a full sanitized JSON copy.
Each capture has at most eight owned Swift source files, there are at most eight
review files and 32 explicit prefix mappings. File/count limits are checked
before evidence reads. The `ls-tree` input streams bounded NUL rows (8 KiB per
row, 16 MiB listing bytes) and stops as soon as entry or source-byte limits fail.
No complete unchecked tree listing is buffered. JSON with duplicate keys or
nonfinite numbers is rejected, including overflowing exponents.
The start marker is created exclusively immediately before the first ZIP/source
stream operation, survives failure and forbids unattended resumption. An existing
output or marker refuses replacement. A stopped partial is preserved and is not a
completed artifact. Do not delete a marker or change output names to repeat a
failed operation without explicit authorization for that run.

Default staging refuses incomplete qualification gates or the scoped readiness
record. Whole-task packaging/delivery items remain explicitly pending. The parent may explicitly add `--allow-incomplete` solely to preserve
unfinished work in a local package. Its manifest remains `INCOMPLETE`; archive
existence cannot complete the task. A successful local operation is
`STAGED_LOCAL_ONLY`. Cross-device delivery, signing, upload and release require
their separate authority and completed supported destination operation.

## Focused tests

`tests/test_swift_broad_handback_packager.py` uses newly authored synthetic tar,
JSON and text only. It covers complete format inclusion, member/path safety,
source bounds, omitted members, custody removal, retained original digests and
instruction evidence, unknown path refusal, clearance binding, engine-change
refusal and the execution switch. It exports no real AIRS source and reads no
captured receipts. Reuse the recorded result for unchanged test inputs.

The corrective review boundary has 17 additional tests in
`PackagerReviewBoundaryTests`, covering cumulative reservations, file/review
counts, bounded streamed tree enumeration, arbitrary command path roots and
attached operands, mandatory gates and distinct current passed reviews, and
strict JSON. The first 11 passed in their initial focused run; six additional
preallocation/control-output/joined-path/key-collision/response-file tests each passed once in
separate narrow runs.
Other Git identity/diff/status query output is capped at 1 MiB before decoding.
The original 15 synthetic tests
were not rerun for this correction. Reuse both recorded scopes; the correction
command was:

```sh
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k PackagerReviewBoundaryTests
```

The two subsequent narrow commands were:

```sh
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k test_relocated_json_escape_budget_is_reserved_before_encoder
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k test_git_control_queries_stop_at_fixed_output_bound
```

The final two residual-boundary commands were:

```sh
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k test_unenumerated_attached_paths_refuse_and_known_relative_clang_forms_survive
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k test_relocated_dictionary_key_collisions_refuse_without_second_relocation
```

Response-file and plugin-server operands have one additional narrow check:

```sh
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k test_response_files_and_plugin_server_operands_require_relative_paths
```

The repeated response-prefix correction unwraps iteratively and rejects an empty
operand. Its one new 2,000-prefix case passed in this single targeted run:

```sh
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k test_two_thousand_response_prefixes_are_iterative_and_empty_refuses
```

## R1-04 repair evidence

Seven new methods in `RoundOnePackagerRepairTests` passed in the first focused
run (7/7, 0.004 seconds). They use mocked Git streams and small synthetic
metadata only, covering patch bytes/bounds, sanitized commit inventory, exact
extra-member inventory/root handoff, reused SHA coverage, supplemental clearance,
scoped pre-packaging readiness and incomplete remaining-work preservation:

```sh
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k RoundOnePackagerRepairTests
```

No real Git source export, capture preflight, ZIP staging or hash occurred. No
previous test method was rerun. The earlier completeness fixture was updated to
the new scoped-readiness contract without running its old methods. The separate
worker's existing 26-gate synchronization result is reused; it was not repeated.

## Recognized output-directory CLI evidence

Seven new `OutputDirectoryCliTests` methods passed in their first focused run
(7/7, 0.005 seconds): parser mode exclusivity, exact existing-root path derivation
without metadata reads, basename refusal, existing-directory/symlink checks,
legacy compatibility, marker containment/archive symlink refusal, and preserved
exclusive output/marker/sidecar behavior using only newly authored tiny fixtures.
No earlier packager method was rerun; no actual metadata, export, hash or ZIP
staging was performed.

```sh
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k OutputDirectoryCliTests
```

The authorized outcome is local staging. Cross-device delivery is USER_DEFERRED
until a destination is supplied; this CLI change grants no upload authority.

## Large evidence and optional challenge supplement

A legitimate approximately 49 MiB qualification JSON can have conservative
processing charges above 256 MiB while its complete serialized evidence fits
that cap. Processing, raw input and retained output accounting are therefore
separate. Source remains capped at 256 MiB, the ZIP/expanded total at 512 MiB,
and aggregate entries at 20,000. These local accounting changes do not change
shared storage-guard thresholds or establish observed RSS.

Optional `--supplemental-capture DIRECTORY` adds at most one third input, under
`captures/supplemental/`, solely for challenge evidence. Primary and independent
second-compiler roles/counts remain unchanged. Its source, compile.v2/index,
manifest, nm/objdump and reproduction views use the same custody removal and
relative relocation rules. Existing digests are copied, never regenerated.
The original source filename comes from `source_file` for the supplemental
receipt rather than the main capture's legacy filename.

If the qualification uses the supplemental capture it must declare:

```json
{
  "supplemental_capture_evidence": {
    "used": true,
    "role": "supplemental_challenge_only",
    "source_sha256": "EXISTING_SOURCE_SHA256",
    "images": {"Onone": "EXISTING_IMAGE_SHA256", "O": "EXISTING_IMAGE_SHA256", "Osize": "EXISTING_IMAGE_SHA256"}
  }
}
```

The input is required when `used` is true. Source identity and the complete
mode-to-image map must match the supplied original receipt metadata, and that
receipt's role must be `supplemental_challenge_only`. Absent/false declaration
requires no third input; an unreferenced third input is refused. This is lineage
reconciliation only, not a repeated compile/index/hash or a new attestation.

Five NEW `LargeEvidenceSupplementTests` methods passed in their first focused
run (5/5, 0.007 seconds). They simulate the 49 MiB processing ratio using counters
without allocating/reading a real report; check unchanged output/input caps,
chunked escaping, exact optional lineage, and tiny synthetic supplemental views.
No old method, real report/capture preflight, hash, export or ZIP operation ran.

```sh
python3 -m unittest discover -s tests -p test_swift_broad_handback_packager.py -k LargeEvidenceSupplementTests
```
