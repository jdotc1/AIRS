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

## Reuse and lean runtime staging

--native-build-receipt names a trusted local airs-native-build-reuse-v1 receipt.
The helper requires matching accepted/current native source object identities,
clean compiler inputs, build-root containment, both executable records, exact
resource membership and matching file metadata. It rejects resource links, empty
new bundles and missing/changed products. Sixteen new synthetic methods passed.
It performs no source-content hashes or compiler invocations. Trusted local
receipt custody is required; this is not adversarial artifact authentication.

New staging omits CPython's unused test directory and ensurepip bootstrap payload
from the copied private framework. The application engine is standard-library-only
and never installs packages into its immutable runtime. The prepared framework
and its original receipt remain unchanged, and packaged omissions are recorded
in runtime-info.json. Malformed stdlib test archives therefore cannot accidentally
enter the distribution surface. Package changes require a new source claim,
seal and archive qualification; an earlier refused archive is not reused as clean.
