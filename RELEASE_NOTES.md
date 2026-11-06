# AIRS 0.3.4 Preview — build 32

Build 32 adds an explicitly selected **Extended Swift scan** resource profile (`broad-extended-v1`) to the native Broad Swift Error Flow analysis, on top of everything in build 29.

- Choose the extended profile to scan more of a large image: up to 9,216 recorded functions or symbols, 2,097,152 words overall (262,144 per function) and 8,192 retained call records. Image and report ceilings remain 8 MiB and 16 MiB. Earlier profiles keep their original limits and historical interpretation.
- A function that exceeds the per-function limit is partially scanned; later functions stay eligible while overall budget remains. Omitted-candidate counts and separate completeness states are retained, displayed and preserved in the raw export.
- Installed real-input check on the previously acquired Maccy 2.8.0 ARM64 slice: the scan completed after 393,880 words (the prior profile stopped partial at 262,144), observed 55,863 call instructions and retained all 5,263 selected candidate records with zero omissions; all remained unresolved indirect targets. The report exported and reopened as historical evidence with the extended-profile label.

Download **AIRS-0.3.4-build32-macOS-arm64.zip** for the Developer ID signed, Apple-notarized and stapled application with its included Python runtime. Exact source, a qualification summary and SHA-256 checksums are attached. Application source: `db7347b1c06b60ba08f71d496f1c9690fe46e437`.

Completed verification, signing and notarization receipts were reused. Accepted Track A and Track B evidence from build 29 was preserved; unchanged suites, corpus passes and source/dependency hashes were not repeated for publication. Newly assembled publication files receive their own sanitation and first checksums.

Complete scan accounting does not prove that indirect targets, execution or source behavior were established; structural eligibility is not a runtime, trust or source-reconstruction verdict. The in-app build record is builder-recorded, not reproducibly attested. This is one real-input workflow check, not corpus, clean-machine, minimum-OS, Intel or MacScope acceptance. The documented [macOS geometry limitation](https://github.com/jdotc1/AIRS/blob/main/docs/MACOS_LIMITATIONS.md) remains; the application stayed responsive in the scoped check.
