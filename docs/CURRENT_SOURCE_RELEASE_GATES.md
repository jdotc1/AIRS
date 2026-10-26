# Current-source candidate gates

Packaging accepts explicit --version, --build and --source-commit values. For a
frozen candidate it generates AIRSBuildProvenance.json before signing, using the
exact clean source HEAD, bundle identifier and build. This is a builder-recorded
claim, not reproducible-build proof. Historical build 12 remains independent.

scripts/build_provenance.py creates claims exclusively. scripts/release_preflight.py
checks exact embedded source/repository/bundle/build binding, bounded regular
files, code seal, Gatekeeper and stapled ticket; it stops on the first failed
platform check. New receipts must be outside the protected app and cannot replace
existing files. Fifteen new synthetic controls passed, and independent review
found no blocking issue in that scope. Synthetic results do not qualify a binary.

--accepted-vendor-source takes an exact retained accepted source commit, compares
immutable Lumen tree identity and rejects tracked, untracked or ignored source
input changes. It reuses accepted source inspection rather than rescanning the
same vendor files. The caller must supply a genuinely accepted identity; choosing
an unchecked baseline is forbidden. Newly assembled owned binaries/resources
retain the separate content check. Three new malformed version/build/source
argument controls refused before any build.

Candidate work targets Apple silicon and includes the separately prepared private
Python runtime. Runtime preparation receipts, source freeze, toolchain/dependency
records, signing/notarization and archive facts remain local evidence until the
specific output has completed its publication checks. No installed application
replacement is part of candidate preparation.

Clean-machine acceptance requires an independently provisioned Apple silicon Mac
or VM. None is currently available. Local checks cannot close this gate or prove
minimum-macOS compatibility. No new public release may be described as fully
qualified while required environment/platform evidence remains unavailable.
