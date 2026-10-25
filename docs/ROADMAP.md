# AIRS bounded development roadmap

This public repository is the single development baseline. Plans describe intended
work; acceptance records establish completed scope. Build 12 remains the published
preview and is not replaced by source-only increments.

| Milestone | Current position | Remaining boundary |
| --- | --- | --- |
| Native evidence review and saved workflows | Build 12 includes accepted Settings, comparison and persistent sidebar corrections | Qualify each changed user interaction after pending work settles |
| Conservative ARM64/CFI model | Merged W SDIV/W UDIV and scalar reversals through v46 plus local CLS v47; historical identities and refusal accounting preserved | New instruction/rule families require distinct positive and refusal evidence and independent review |
| Saved-report coverage triage | Reason selection, terminal-safe output, bounded detail and literal code ordering implemented | Additional triage tools must preserve full denominators, overlap, duplicate/conflict and exact identity context |
| Public distribution | Single repository; build 12 signed/notarized/stapled release, public browser download and actual App Translocation accepted on the development Mac | Clean-machine, minimum-macOS, Intel-app and offline qualification remain incomplete |

## Current bounded increment

Coverage triage, W SDIV/W UDIV and owned-image qualification are merged through
PRs #13–20; scalar REV/REV16/REV32 through PRs #21–23. Accepted results are reused.
The current bounded semantic increment adds [scalar CLS W/X v47](CLS.md), sharing
CLZ state handling while excluding the sign bit from the count. Six new complete
images distinguish correct, missing and unknown recovery at both widths.
[Qualification](CLS_RESULTS.md) records fresh/reused scope and the corrected test
selector. Installation and release remain unchanged.

## Next candidates, one bounded item at a time

1. Use the documented saved-report workflow to identify a concrete unresolved
   behavior worth improving; avoid adding filters without a specific review need.
2. Select a next semantic extension from an explicit owned example and independently
   derived recovery expectation. Reason frequency in supplied reports is prioritization
   input, not representative prevalence or automatic permission to widen support.
3. Complete clean-machine/minimum-OS acceptance when an appropriate environment is
   available. Development-Mac acceptance does not close these gates.

Reuse accepted results for unchanged inputs. Run only changed-boundary checks and
keep source tests, native GUI acceptance, packaging, signing/notarization, installation
and release publication distinct. Runtime evidence and user data stay outside source.
