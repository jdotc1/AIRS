# Contributor and agent guide

AIRS is a native macOS evidence-review workspace with a separately executable,
standard-library-only Python ARM64 Mach-O unwind analyzer. Selected binaries are input
data: never load or execute them. This is the single active development repository,
and work happens here on focused branches and pull requests (README.md,
CONTRIBUTING.md).

This guide gathers rules that are written down elsewhere in the repository and names
the file each one comes from. Where this guide and a named file disagree, the named
file governs and this guide should be corrected.

## Where to read

Every file named here exists in the repository.

- README.md: scope, build commands, the current release and its limits.
- CONTRIBUTING.md: contribution and evidence-handling rules.
- docs/PUBLICATION_POLICY.md: required before any public delivery.
- docs/ANALYSIS_CONTRACT.md: the analysis contract, required before changing analysis
  behavior. Its opening lines state the current source model.
- docs/DEVELOPMENT_STATUS.md: retained evidence by area. Its opening paragraph still
  names build 12; README.md names the current release.
- docs/ROADMAP.md: the current plan and the reasons for it. The dated checkpoints
  that preceded it are in docs/ROADMAP_HISTORY.md; headings there that begin
  "Current" or "Next" were true when written.
- docs/ARCHITECTURE.md: the engine and app split. Its opening status note predates the
  current model; take the current model from docs/ANALYSIS_CONTRACT.md.
- docs/CURRENT_SOURCE_RELEASE_GATES.md, docs/PRIVATE_PYTHON.md and RELEASE_NOTES.md:
  packaging, signing and release work only. README.md calls the first one prior
  release qualification.
- docs/WORKSPACE_FOOTPRINT.md: before removing worktrees, build products or caches.
- docs/MACOS_LIMITATIONS.md: known macOS window-capture geometry diagnostics.
- THIRD_PARTY_NOTICES.md and LICENSE: licenses and attribution, including the vendored
  Lumen and EntitlementDiff code under native/Vendor/.

Some documents, notably docs/ANALYSIS_CONTRACT.md and docs/ARCHITECTURE.md, link to
files that are not in this repository. Treat such a link as unresolved: do not infer
what the file said, and do not recreate it unless the task asks for that.

## Changing analysis behavior

Read docs/ANALYSIS_CONTRACT.md first, then:

- Preserve the analysis contract, its unresolved boundaries and exact image and slice
  identity. Keep unknown handling conservative: an uncertain or unsupported form stays
  unresolved or refused (CONTRIBUTING.md).
- Model identities are versioned and registered in src/airs/analysis_models.py.
  Historical identities remain distinct, and exact Python and native admission retains
  historical labels (README.md, docs/ANALYSIS_CONTRACT.md).
- A new instruction or rule family needs distinct positive and refusal evidence and
  independent review. Choose a semantic extension from an explicit owned example with an
  independently derived recovery expectation. Reason frequency in supplied reports is
  prioritization input, not representative prevalence or permission to widen support
  (docs/ROADMAP.md).
- Reuse the existing Lumen and owned component implementations where they meet the
  requirement (CONTRIBUTING.md).
- Commit synthetic fixtures and sanitized, scope-specific verification summaries. Do
  not include arbitrary real input binaries (CONTRIBUTING.md).

## Verification

### CI

.github/workflows/verify.yml ("Source verification") runs on pull requests, on pushes
to main and on manual dispatch, with read-only repository permission. The workflow file
is authoritative for versions, matrices and skip allowances; this summary can lag it.

- python job: Ubuntu 24.04, Python 3.11.17 and 3.15.0. It installs jsonschema 4.25.1 as
  the schema test dependency and runs
  `python -I -B scripts/verify-python.py --receipt build/verification/python.json`.
  It fails on any skipped test except one allowed case,
  test_private_python_reuse.RuntimeMetadataReuseTests.
  test_saved_observed_metadata_pair_without_runtime_access, and uploads the receipt.
- native job: macOS 15 arm64, Xcode 26.3, Python 3.15.0. It records the host and
  toolchain, builds the release AIRSApp and airs-entitlements products, runs
  `swift test --package-path native` with AIRS_PYTHON set, and writes native-scope.json
  with the raw skip lines plus a step summary. Two skips are anticipated:
  PrivatePythonTests.testActualPrivateChildUsesIsolatedNoSiteNoBytecodeAndCancellationSettles
  (the private runtime is not prepared in CI) and
  BundleDiscoveryTests.testInvalidNamesConsumeEntryBudgetAndRemainVisible (a host that
  rejects the file name). Review every skip line before accepting a run.
- CI is source verification only. It does not qualify packaging, signing,
  notarization, a clean Mac or distribution, and it is not a distribution approval
  (README.md).

- .github/workflows/publication-gate.yml ("Publication gate") runs
  scripts/publication_gate.py in range mode over the commits a pull request or a push
  to main adds, using the gate script from the trusted base revision. A green run is a
  backstop, not a publication clearance. A workflow-skip token in a head commit
  message stops both workflows from starting, so do not use one on a change that
  touches source or lands on main (CONTRIBUTING.md).

### Local commands documented in the repository

```
make test
python3 -I -B scripts/verify-python.py --receipt build/verification/python.json
PYTHONPATH=src python3 -m unittest discover -s tests -p test_<module>.py
swift build --package-path native --configuration release --product AIRSApp
swift build --package-path native --configuration release --product airs-entitlements
swift test --package-path native
swift test --package-path native --filter <TestClass>
```

- `make test` runs `PYTHONPATH=src python3 -m unittest discover -s tests -v`
  (Makefile). The receipt form is what CI runs; add `--fail-on-skip` to turn any skip
  into a failure. build/ is untracked. A single module is selected with `-p`
  (docs/swift/BROAD_DECLARATIONS.md), and `-k` narrows to a class or test
  (docs/swift/BROAD_PACKAGING.md).
- Native requirements: macOS 14 or newer on Apple silicon, Swift 6.1 or newer, and
  Python 3.11 or newer for the engine (README.md). Set AIRS_PYTHON to the absolute path
  of a Python 3.11+ executable before `swift test`, as CI and scripts/verify-macos.sh
  do. A filtered run is described in docs/NATIVE_BROAD_RESULTS.md.
- scripts/verify-macos.sh (`AIRS_PYTHON=/absolute/path/to/python3
  scripts/verify-macos.sh`) compiles and tests the native package, runs the Python suite
  and assembles a temporary developer app package to inspect its layout. No app or
  inspected binary is launched, and the package is removed on exit.
  docs/PRIVATE_PYTHON.md calls it the historical gate that uses the developer variant;
  apply the reuse rule below before running it.
- AIRS_TEST_OUTPUT_ROOT selects an explicit output root for tests that write files;
  otherwise they use portable temporary defaults (README.md).
- `make schemas` runs scripts/generate-schemas.py, `make fixtures` runs
  fixtures/generate.py, and scripts/generate-examples.py regenerates the reviewable
  examples.

### Expectations

- Validate changed behavior with the smallest relevant checks and retain existing valid
  receipts for unchanged inputs. Accepted checks are reused for unchanged boundaries:
  do not repeat engine suites, corpora, dependency checks or signing, and do not rerun
  unchanged gates merely to package another copy (README.md,
  docs/PRIVATE_PYTHON.md). When a repeat seems necessary, obtain permission first
  (docs/PUBLICATION_POLICY.md).
- Native UI fixes require stable interaction acceptance after pending work settles;
  compile-only or immediate-selection evidence is insufficient. Source checks, GUI
  acceptance, signing and notarization, and release publication are distinct gates.
  Do not represent a skipped workflow as a passed one (CONTRIBUTING.md).
- Ordinary development does not authorize a binary release. Public binary releases
  require their own reviewed artifact identity and acceptance, and version constants in
  the source and developer packaging are not a new release identity (CONTRIBUTING.md,
  README.md).
- Release tooling named in the repository: scripts/package-app.sh (README.md,
  docs/PRIVATE_PYTHON.md), scripts/prepare-private-python.py (docs/PRIVATE_PYTHON.md),
  scripts/build_provenance.py and scripts/release_preflight.py
  (docs/CURRENT_SOURCE_RELEASE_GATES.md). Read a script's own header before running it.

## Publication

Before any public push, pull request, tag, release, source export or asset upload, read
and apply docs/PUBLICATION_POLICY.md. Sanitization is a prerequisite for every
authorized public delivery. The policy does not authorize a push, release, destructive
history rewrite or repository recreation, and existing verification and release gates
remain in force. Its rules:

- Scope the delivery first: the exact repository, outgoing refs and commits, public
  text and assets, the expected source identity and any valid accepted sanitization
  receipts. A clean current tree is not evidence that earlier outgoing commits are
  clean. A signed executable is not evidence that its source archive or release notes
  are suitable. An application-content check is not repository, history or metadata
  clearance. Reuse accepted evidence only for the exact content and surfaces it
  covered. Keep unresolved publication surfaces explicit and do not publish them as
  clean.
- Review each surface that is new or changed: tracked files (names, symlink targets and
  textual metadata included); every newly outgoing commit and tag (contents, messages,
  author, committer and tagger identities, trailers); pull-request and issue titles,
  bodies, comments and attachments, workflow summaries and release text; source
  archives and release assets, including embedded file metadata, paths, debug strings,
  qualification records, receipts and checksums. Each artifact needs its own
  applicable evidence, and source clearance alone is insufficient. Documentation
  comments, preview and sample labels and vendor provenance count as source.
- Write public text correctly the first time. A private detail that is inserted and
  later edited away may remain visible in earlier revisions.
- Exclude from tracked files, commits, pull-request and issue text, workflow
  definitions and release assets: credentials, private contact information, host or
  user identifiers, personal absolute paths, private working-directory conventions,
  temporary session paths, private repository references and internal coordination or
  provenance text. Use repository-relative names, neutral fixture paths or generic
  wording, and do not print matching credential bytes in reports. Keep required
  licenses and legitimate third-party attribution.
- Keep machine-specific locations in ignored local configuration or the execution
  environment, with documented portable defaults. Do not store local paths in GitHub
  repository variables or public CI definitions. A redaction must not leave an empty
  operand, an invalid containment check, a broken command or a misleading receipt.
- Commit, tag and tagger addresses must be approved public identities (the allowlist is
  in scripts/publication_gate.py). The gate rejects any co-author trailer, including
  one added automatically by a tool, so do not add co-author trailers.
- Keep private findings and detailed logs outside tracked source, in local-evidence/. A
  local receipt records exact outgoing identities, covered surfaces, accepted results
  reused, changed-boundary checks and unresolved gaps. Never describe a component scan as
  a whole-publication clearance. Inspect new or changed surfaces instead of rerunning
  sealed checks on unchanged inputs.
- Review the final rendered public text before submission. After publication, confirm
  the actual destination refs, identities, text and asset metadata against the approved
  delivery, without replaying unchanged analysis or signing checks. A failed or
  incomplete surface blocks that surface's publication.
- If exposure is discovered, stop further publication, preserve private evidence and
  identify the affected surfaces. Repository deletion or recreation and force-pushes
  require explicit authority and a recovery plan covering issues, pull requests,
  releases, protection, runners and other metadata. Do not claim that deletion removes
  all cached or historical copies.

The publication tools are standard-library only. They do not grant publication
authority or replace signing, notarization, functional acceptance or human review of
confidential context.

- scripts/publication_gate.py checks every newly outgoing commit (including
  intermediate states), approved identities, annotated tag chains, file names, source
  content and nested ZIP contents, plus declared public text and assets.
- scripts/configure-publication-gates.py installs a local pre-push adapter
  (scripts/publication-pre-push.py) when it will not overwrite an unrelated hook. It
  needs an exact accepted baseline from retained evidence and a local evidence
  description; an unchecked baseline is prohibited. Hooks apply to the configured
  checkout and a fresh clone must install them.
- scripts/export-public-source.py exports committed source only, after range inspection
  against an accepted baseline.
- scripts/publish-public.py preflights a private JSON plan kept in ignored local
  evidence and uploads nothing unless `--execute` is given with separate authority for
  that exact delivery. Attachments outside the declared assets are not cleared.
- Hosted services cannot make a local hook mandatory, so contributors must use these
  gates for authorized delivery. Pattern checks cannot prove the absence of confidential
  prose, image content or novel secret formats; those need explicit scoped review, and
  the absence of a pattern hit must never be reported as universal privacy clearance.

## Working tree

- Preserve unrelated work and existing analysis, verification and release gates.
- Use this repository as the active checkout. Completed feature work does not need a
  permanent worktree or another packaged application copy (docs/WORKSPACE_FOOTPRINT.md).
- .gitignore excludes local-evidence/, build/, dist/, native/.build/, .env files and
  signing keys (*.p12, *.p8). Not every ignored file is disposable: local evidence and
  credentials are ignored on purpose, and installed apps, user settings and stores are
  outside any cleanup.
- Keep committed source, unmerged changes, accepted receipts and the owned inputs needed
  for later evidence reuse. Derived caches such as native/.build, obsolete packaged
  copies, completed worktrees and merged feature branches may be removed after work
  settles, once ownership, uncommitted data and branch reachability are checked. Do not
  replay sealed checks, rehash inputs or rebuild merely to confirm a cleanup
  (docs/WORKSPACE_FOOTPRINT.md).
