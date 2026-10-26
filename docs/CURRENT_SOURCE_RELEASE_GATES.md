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

## Current local candidate qualification

The frozen Apple silicon candidate is version 0.3.4, build 13, source
2944e4626a6e3b600bac0a8793c0accecb51b363. The source claim was embedded before
signing. The retained release native build was reused only while its native
source identities and product metadata matched. Subsequent scanner/documentation
changes do not retroactively change this candidate's source identity.

The final staged private Python 3.15 runtime passed one changed-boundary probe of
its seven normalized extension modules, sysconfig, one owned child process and
engine bootstrap. The exact candidate launched with isolated stores using native
audit/comparison fixtures; native control observed the report overview, opened
and dismissed the comparison sheet, and closed the acceptance window. An earlier
attempt supplied the wrong report kind and exited before displaying a window;
it is not counted as successful acceptance. These checks do not establish a
clean installation, offline operation, minimum-OS compatibility or arbitrary
runtime-module correctness.

Apple notarization accepted the signed candidate. Stapling and the post-staple
source/build binding, code seal, Gatekeeper and ticket checks passed. The final
stapled distribution ZIP passed the bounded archive privacy/link gate. Its size
is 33,207,916 bytes and SHA-256 is
be30a2a95fdcb17dc924f18d766c6f94159f93407f712ec9954d7c354ee8e51d.
Detailed receipts and credential-profile information remain private.

The archive scanner permits two exact quoted generic upstream library lookup
constants for its home-shorthand rule only. It keeps all other marker checks on
original bytes. Four new focused methods cover exact literals, suffixes, other
paths, escaped/mismatched quotes, case variants and adjacent private markers.
Independent review recommended the same bounded policy. No signed artifact was
modified to resolve these generic scanner matches.

R1A–R1C and local distribution preparation are complete. The new archive also
passed one isolated GUI launch from an actual App Translocation location after
fresh extraction and synthetic quarantine. Both the launch API and application
profile recorded the translocated executable. Native control observed the report
overview, opened and dismissed the comparison sheet, then closed the window; the
test process exited. This is local archive/translocation acceptance, not a browser
download. R1D remains open for download delivery; historical build-12 results
cannot qualify it. R2 remains blocked because no independently provisioned
compatible Apple silicon environment is available. There is no new download link
or public release, and the installed app and production stores are unchanged.
