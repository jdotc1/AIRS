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

## Staged-runtime publication surface

The full archive gate also covers the private runtime. A dependency-integrity
receipt is not a publication-content clearance. New staging removes unused
runtime developer documentation/build directories and normalizes build-home
prefixes in generated sysconfig data. The literal dictionary/JSON transforms
preserve nonpath values and types and refuse executable configuration. Fixed
strip operations remove native debug/local-symbol metadata before signing;
no arbitrary Mach-O byte replacement is performed.

The sanitizer accepts only a fresh .airs-package.* staging copy, rejects unsafe
paths, uses a one-shot marker and retains a relative-path staging report in
RuntimeNotices. The prepared runtime and previously signed candidates are not
modified. Seventeen new synthetic controls passed. Actual staged runtime startup
and the new signed archive still require their separate qualification.

The archive gate now supports bounded standard framework link chains, including
Versions/Current and implicit ZIP directories. It still refuses escapes, cycles,
dangling links, malformed archives and private markers. Twenty new focused
controls passed; no previous archive acceptance was silently transferred to the
changed policy. Resolution is bounded by link, component, namespace and byte
limits, without extraction or execution.

## Residual native source-path literals

Some upstream build paths are C source-file/build-directory literals rather than
removable debug symbols. Fresh staging now supports a narrowly qualified
fixed-width normalization of those complete ASCII literals in readable,
non-writable __TEXT,__cstring sections. It preserves literal terminators, file
length, offsets and every byte outside the selected home-prefix spans; it does
not touch sections marked as instructions. Unclassified markers or contradictory
Mach-O mappings refuse the stage. This is a trusted pinned-runtime packaging
transform, not an input-binary patching feature or a general semantic-equivalence
claim.

Twenty-one new focused controls passed for thin/universal containers, preserved
bytes/width, section/protection/instruction boundaries, string subsets and parser
budgets. Two additional staging-composition methods passed. Independent review
found no blocking issue. Original preparation and older candidates remain intact.
Stripping precedes normalization, so a refused stage may be partially processed;
it must be discarded/held, not retried. Actual modified-runtime behavior and
artifact acceptance remain mandatory separate checks before delivery.
