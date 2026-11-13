# AIRS 0.4.0 Preview — build 33

Current preview: https://github.com/jdotc1/AIRS/releases/tag/v0.4.0-build33

Application/source tag: `v0.4.0-build33`, exact application source
`9a000f85ab9d47eaecd48fc06f59da9258f49e86`. This includes everything in build 32 plus the
explicitly selected `broad-imports-v1` Swift error-flow profile
([profile details](SWIFT_BROAD_IMPORTS_PROFILE.md)). The minimum system is macOS 27 on
Apple silicon; build 32 remains the last release for macOS 14 to 26.

The release provides the signed, Apple-notarized, stapled ARM64 app ZIP (34,214,253
bytes, SHA-256 `db9ec3829ad7923645429106ed5892ada4e1b0e0dc3b224d4cba26d36e0cf52a`), the
exact source ZIP, a public qualification JSON and SHA-256 checksums.

This is a new build. Every packaged binary and bundle was signed with the Developer ID
identity, including the private Python runtime, and the application was notarized and
stapled for this build; no signing or notarization receipt of build 32 was transferred.
After stapling, the release preflight passed: the recorded source commit, bundle
identifier, build and the requested version 0.4.0 matched, the code seal verified,
Gatekeeper accepted the application and the stapled ticket validated. The application
archive passed the publication archive gate. The source commit passed source
verification (run 43323530863) and the publication gate (run 43323530979) on main,
including the native build and tests on a hosted macOS 27 runner and the ARM64 decode
oracle.

Before signing, the bundled engine of the candidate reported `AIRS 0.4.0` and wrote both
import-profile reports on the owned fixture, byte-identical to the earlier candidate's.
The application window was not opened on this candidate and no user interaction was
tested on it. The Maccy 2.8.0 measurement in the release notes was made on the engine
source, not on this bundle.

Release acceptance run 43374401949 on 2026-11-13 checked the published archive on the
hosted macOS 27 image (macOS 27.0.1), with every step passing
([what the run checks](RELEASE_ACCEPTANCE.md)). That run is the evidence for the macOS 27
minimum: the host was at the declared minimum major version. It does not exercise the
first-open dialog of a quarantined download, any window content or any user action.

Preview status is retained. Attribution does not prove that a callee throws, returns or
is the function bound at run time; structural eligibility does not prove runtime
execution, trust or source reconstruction. The in-app build record is
builder-recorded, not reproducibly attested. Intel, corpus and MacScope acceptance are
not established.
