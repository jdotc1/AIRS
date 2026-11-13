<p align="center">
  <img src="resources/AIRS-icon.png" alt="AIRS app icon" width="144">
</p>

# AIRS

AIRS is a macOS application for reviewing what a compiled program contains without
running it. You select an application, a framework or a single ARM64 Mach-O file, and
AIRS reads it as data and shows what it found, what it could not decide, and why.

It has two parts:

- a native macOS application (SwiftUI and AppKit) for selecting inputs, reviewing
  results and saving them, and
- an analysis engine written in Python with no dependency outside the standard
  library, which also runs on its own from the command line.

## What it does

- **Unwind audit.** For each function in an ARM64 image, AIRS compares the recorded
  unwind information with what a bounded reading of the instructions supports. Each
  function gets a verdict and, when the verdict is not agreement, a reason.
- **Component review.** AIRS lists the code units inside an application bundle with
  their signatures and entitlements. For a previous and a current version of the same
  application it reports what changed in the declared permissions and components
  ([Security Changes](docs/COMPONENT_SECURITY_DELTA.md)).
- **Swift error flow.** For selected images, AIRS finds calls to throwing Swift
  functions and the paths their success and error returns take, within stated limits
  ([Swift error flow](docs/SWIFT_ERROR_FLOW.md)).
- **Saved reports.** Results are saved as files that can be reopened, summarised and
  compared across builds ([examples](docs/SAVED_REPORT_COMMAND_EXAMPLES.md)).

## What it never does

- It never loads or executes the program it is inspecting. A selected binary is
  input data.
- It watches nothing and fetches nothing. A person selects each input.
- It does not count an undecided result as agreement. Functions and changes it could
  not decide stay in every total, each with a reason.

## What its results do not establish

A result describes the structure of the bytes that were read. It is not a statement
that a program is safe, trusted or correct, that a code path runs, or what the
original source looked like. Signature and entitlement evidence is a record of what
the file declares; it does not authenticate the signer. Every analysis has a named
model with documented limits, and anything outside those limits is reported as
unsupported or unresolved. The limits are listed in the
[analysis contract](docs/ANALYSIS_CONTRACT.md) and the page for each model.

## Install

Download the current release from the
[releases page](https://github.com/jdotc1/AIRS/releases). Each release provides the
signed and notarized application archive, the exact source, a qualification summary
and SHA-256 checksums.

The current release is the
[AIRS 0.4.0 build 33 preview](https://github.com/jdotc1/AIRS/releases/tag/v0.4.0-build33).
It requires macOS 27 on Apple silicon and adds the imported-callee Swift error-flow
profile ([release record](docs/RELEASE_0_4_0_BUILD33.md)).

## Requirements

- AIRS 0.4.0 and later: macOS 27 or later on Apple silicon.
- AIRS 0.3.4 build 32 is the last release for macOS 14 to 26. It declares macOS 14 as
  its minimum and was never tested on it.
- Intel Macs are not supported.

The application includes its own Python runtime. Nothing else needs to be installed.

## Build from source

Building requires macOS 27, Xcode 27 or later, and Python 3.11 or later.

```
swift build --package-path native --configuration release --product AIRSApp
swift build --package-path native --configuration release --product airs-entitlements
python3 -I -B airs_cli.py --version
```

A developer bundle that uses the system Python is assembled with
`bash scripts/package-app.sh --release --external-python`. A standalone bundle needs a
prepared private Python runtime ([PRIVATE_PYTHON.md](docs/PRIVATE_PYTHON.md)).

The product has one version. The literal `__version__` in `src/airs/__init__.py`
defines it; the package metadata and a Swift constant are copies that a test checks.

Continuous integration runs the Python tests on two Python versions, builds and tests
the native package on a hosted macOS 27 runner, checks the ARM64 decoders against an
independent disassembler, and scans every pull request for text that must not be
published. [CONTRIBUTING.md](CONTRIBUTING.md) describes the workflow.

## Where to read more

- [Roadmap](docs/ROADMAP.md): what is planned, what is not, and why.
- [Architecture](docs/ARCHITECTURE.md) and the
  [analysis contract](docs/ANALYSIS_CONTRACT.md).
- [Model registry](docs/MODEL_ADMISSION_REGISTRY.md): every analysis model and what it
  admits.
- [Release acceptance](docs/RELEASE_ACCEPTANCE.md): how a published archive is checked
  on a clean machine, and what that check does not cover.
- Release documents: [0.4.0 build 33](docs/RELEASE_0_4_0_BUILD33.md),
  [0.3.4 build 32](docs/RELEASE_0_3_4_BUILD32.md),
  [0.3.4 build 29](docs/RELEASE_0_3_4_BUILD29.md),
  [0.3.3 build 12](docs/RELEASE_0_3_3_BUILD12.md),
  [0.3.3 build 10](docs/RELEASE_0_3_3_BUILD10.md),
  [0.3.3 build 9](docs/RELEASE_0_3_3_BUILD9.md) and the
  [release history](docs/RELEASE_HISTORY_RECONCILIATION.md).
- [Known macOS limitation](docs/MACOS_LIMITATIONS.md) in window-geometry diagnostics.

## Source scope and licensing

This is the only active AIRS repository. The source excludes private history,
maintainer records, logs, screenshots, corpus locations and compiled applications.
Owned regression fixtures and public schemas are included. `SOURCE_FILES.txt`,
`SOURCE_EXPORT_SCOPE.json` and `SOURCE_SNAPSHOT.json` describe the original 0.3.3
source import and are kept as records of it.

AIRS and the bundled design-system snapshot are licensed under the
[MIT License](LICENSE). EntitlementDiff keeps its MIT license, and Python's licenses
accompany the packaged runtime. See [third-party notices](THIRD_PARTY_NOTICES.md).
