# Contributing to AIRS

This public repository is the single source of truth for AIRS development. Submit
changes as focused branches and pull requests here. No private repository, private
Git history or source-export step is required to contribute or build.

Keep raw machine-specific execution records, user settings and stores, signing
credentials and local build artifacts outside tracked source. Use local-evidence/
for untracked local records when needed. Commit synthetic fixtures and sanitized,
scope-specific verification summaries. Do not include arbitrary real input binaries.

Preserve the analysis contract, unresolved boundaries and exact image/slice identity.
Treat selected binaries as data, never as code to load or execute. Reuse the existing
Lumen and owned component implementations where they meet the requirement.

Validate changed behavior and retain existing valid receipts for unchanged inputs.
Native UI fixes require stable interaction acceptance after pending work settles;
compile-only or immediate selection evidence is insufficient. Source checks, GUI
acceptance, signing/notarization and release publication remain distinct gates.
Do not represent a skipped workflow as a passed workflow. See docs/ANALYSIS_CONTRACT.md
and docs/RELEASE_VERIFICATION.md for the retained product and distribution contracts.

The build scripts and the CI release builds report any Swift expression or function body
that takes 300 ms or more to type-check as a warning; the CI compiler (Xcode 26.3) is older
than the usual local one, so local timings are a proxy for CI.

Ordinary development does not authorize a binary release. Public binary releases
require their own reviewed artifact identity and acceptance. Keep account and
signing credentials out of source and workflow output.
