AIRS 0.4.0 Preview — build 33

**AIRS 0.4.0 requires macOS 27 or later on Apple silicon.** Build 32 (0.3.4) remains the last release for macOS 14 to 26.

Build 33 adds an explicitly selected **imported-callee** profile (`broad-imports-v1`, shown as "Broad Swift · imported callees (attribution only)") to the native Broad Swift Error Flow analysis, on top of everything in build 32.

- Calls that reach an imported Swift function through a verified import stub are attributed to the imported symbol. A stub is bound only when its three instruction words have the exact expected form and the stub's own indirect-table entry and the entry for the pointer slot it loads name the same undefined external symbol.
- An imported symbol is read with a closed mangling grammar. A symbol the grammar reads to the end with no throws marker is counted as a non-throwing import call and is not listed. Every other attributed call stays listed as unresolved, with its declaration state and the reason.
- Attributed rows are always shown as unresolved. They are never shown as supported or as agreement, and they carry no ABI admission, outcome witness or claim about which library is bound at run time.
- Earlier profiles keep their limits, their decoding and their historical interpretation. The default profile is unchanged.
- The unwind analysis model is `arm64-bounded-extract-class-v51`. Instruction words outside the extract class are no longer reported as an invalid extract encoding; they report as unsupported. No instruction support is added, and earlier reports keep their recorded model.
- An export is now refused when its destination lies inside the inspection store, a portable project or an inspected bundle, however the path to that folder is spelled. Before, a new destination below a symbolically linked folder could pass the check. A relative entitlement manifest in such a folder is no longer refused.
- Analysis reuse is pinned to the engine's current analysis model, and no longer declines a framework or engine folder that is reached through a path containing a symbolic link.
- A batch save no longer leaves an empty entry behind when another store briefly holds the inventory lock.
- The ARM64 decode oracle now runs in CI on vectors generated on the runner, and fails on any blocking disagreement or any supported instruction kind that never reaches agreement.
- The minimum system is macOS 27. The deployment target of the application and of the command-line tool is macOS 27, and the source is tested in CI on a hosted macOS 27 runner.

One real-input measurement was made on the engine source, not on this application bundle: Maccy 2.8.0, read as data and never run. Under `broad-imports-v1` the engine observed 55,863 call instructions, attributed 1,219 of 1,219 import stubs, skipped 3,145 stub calls to Swift imports that the grammar read as non-throwing, and selected 12,690 call candidates, of which the report retains 8,192 (its limit) and omits 4,498. Of the retained rows, 5,123 are attributed to an imported symbol and 3,069 remain indirect calls with no target. This measures attribution. It does not show that any attribution is correct beyond the stub binding rule, and one application is not a corpus.

Download **AIRS-0.4.0-build33-macOS-arm64.zip** for the Developer ID signed, Apple-notarized and stapled application with its included Python runtime. Exact source, a qualification summary and SHA-256 checksums are attached. Application source: `9a000f85ab9d47eaecd48fc06f59da9258f49e86`.

The source commit passed source verification and the publication gate in CI. The included Python runtime was prepared again from the same pinned Python 3.15.0 installer package as before; the build 32 signing and notarization receipts do not transfer to this build. Newly assembled publication files receive their own sanitation and first checksums.

Attribution does not prove that a callee throws, returns or is the function bound at run time; structural eligibility is not a runtime, trust or source-reconstruction verdict. The engine also contains a profile for calls made through the global offset table (`broad-imports-got-v1`); the application does not offer it. The application, its engine and the Python package now report one version, 0.4.0; reports stored by earlier builds keep the version that produced them. The in-app build record is builder-recorded, not reproducibly attested. Acceptance on a hosted macOS 27 runner is recorded separately once the published archive has been run there (`docs/RELEASE_ACCEPTANCE.md`); that run does not exercise the first-open dialog or any user action. This is not corpus, Intel or MacScope acceptance. The documented [macOS geometry limitation](https://github.com/jdotc1/AIRS/blob/main/docs/MACOS_LIMITATIONS.md) remains.
