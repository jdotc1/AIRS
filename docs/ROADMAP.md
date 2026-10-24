# AIRS bounded development roadmap

This public repository is the single development baseline. Plans describe intended
work; acceptance records establish completed scope. Build 12 remains the published
preview and is not replaced by source-only increments.

| Milestone | Current position | Remaining boundary |
| --- | --- | --- |
| Native evidence review and saved workflows | Build 12 includes accepted Settings, comparison and persistent sidebar corrections | Qualify each changed user interaction after pending work settles |
| Conservative ARM64/CFI model | Integrated v41 bounded model; historical model identities and refusal accounting preserved | New instruction/rule families require distinct positive and refusal evidence and independent review |
| Saved-report coverage triage | Reason selection, terminal-safe output and bounded reason detail implemented | Additional triage tools must preserve full denominators, overlap, duplicate/conflict and exact identity context |
| Public distribution | Single repository; build 12 signed/notarized/stapled release, public browser download and actual App Translocation accepted on the development Mac | Clean-machine, minimum-macOS, Intel-app and offline qualification remain incomplete |

## Current bounded increment

Add `coverage --limit N` as a presentation bound on ranked saved-report reason rows.
Reuse the existing aggregation, reason selection, summary-limit pattern and protected
writer. Preserve full counts and show omissions explicitly. No engine semantics,
native UI or installation changes. See [contract and focused checks](COVERAGE_REASON_LIMIT.md).

## Next candidates, one bounded item at a time

1. Add another saved-report triage affordance only when it answers a concrete review
   question; retain original counts and uncertainty rather than re-auditing images.
2. Select a next semantic extension from an explicit owned example and independently
   derived recovery expectation. Reason frequency in supplied reports is prioritization
   input, not representative prevalence or automatic permission to widen support.
3. Complete clean-machine/minimum-OS acceptance when an appropriate environment is
   available. Development-Mac acceptance does not close these gates.

Reuse accepted results for unchanged inputs. Run only changed-boundary checks and
keep source tests, native GUI acceptance, packaging, signing/notarization, installation
and release publication distinct. Runtime evidence and user data stay outside source.
