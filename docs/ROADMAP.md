# AIRS bounded development roadmap

This public repository is the single development baseline. Plans describe intended
work; acceptance records establish completed scope. Build 12 remains the published
preview and is not replaced by source-only increments.

| Milestone | Current position | Remaining boundary |
| --- | --- | --- |
| Native evidence review and saved workflows | Build 12 includes accepted Settings, comparison and persistent sidebar corrections | Qualify each changed user interaction after pending work settles |
| Conservative ARM64/CFI model | Merged through CLS v47; MOVK v48 and CBZ/CBNZ v49 merged in PR32; TBZ/TBNZ v50 merged in PR33 with bounded source/native qualification; historical identities remain distinct | New instruction/rule families require distinct positive and refusal evidence and independent review |
| Saved-report coverage triage | Reason selection, terminal-safe output, bounded detail and literal code ordering implemented | Additional triage tools must preserve full denominators, overlap, duplicate/conflict and exact identity context |
| Public distribution | Single repository; build 12 signed/notarized/stapled release, public browser download and actual App Translocation accepted on the development Mac | Clean-machine, minimum-macOS, Intel-app and offline qualification remain incomplete |

## Current bounded increment

Coverage triage, W SDIV/W UDIV and owned-image qualification are merged through
PRs #13–20; scalar REV/REV16/REV32 through PRs #21–23. Accepted results are reused.
Scalar [CLS W/X v47](CLS.md) is merged in PR #24 with accepted
[qualification results](CLS_RESULTS.md) reused.

Exact model-admission registry hardening is merged in PR #25; its accepted
[qualification](MODEL_ADMISSION_REGISTRY.md) is reused.

Historical/unknown-model decoder boundary tests are merged in PR #26; their
[accepted results](MODEL_ADMISSION_BOUNDARIES.md) are reused.

Coverage-text escaped-allocation preflight is merged in PR #27 with
[accepted results](COVERAGE_TEXT_PREFLIGHT.md) reused.

Exact refusal-instruction evidence is merged in PR #28 with
[accepted results](REFUSAL_INSTRUCTION_EVIDENCE.md) reused.

Refused direct-edge target diagnostics are merged in PR #29 with
[accepted results](REFUSED_BRANCH_TARGETS.md) reused.

Unknown CFG recovery evidence is merged in PR #30 with
[accepted results](CFG_UNKNOWN_RECOVERY_EVIDENCE.md) reused.

Possible-path discrepancy evidence is merged in PR #31 with
[accepted results](CFG_POSSIBLE_DISCREPANCY_EVIDENCE.md) reused.

The preceding local analysis improvement retains configured and completed CFG
state-visit counts in the existing work-budget exhaustion evidence row. Limits
still stop exploration immediately and retain unresolved status without checked
PCs; no supported subset or model change is added.
See [work-budget qualification](CFG_WORK_BUDGET_EVIDENCE.md).
Installation and release remain unchanged.

## MacScope reuse implementation

MOVK W/X v48 and CBZ/CBNZ W/X v49 are merged in PR32 with independent review,
owned-image qualification and native admission. See MOVK_RESULTS.md and
COMPARE_BRANCH_RESULTS.md. MacScope is read-only; no new binary is installed.
Recent multiply/CMN literal boundary cases are adapted as three passing regression
methods; existing AIRS arithmetic needed no change. Function matching and proof
fact recording remain subsequent work, not claimed implemented by this increment.

TBZ/TBNZ v50 is merged in PR33, with separate owned positive/refusal
evidence. See TEST_BIT_BRANCH.md and TEST_BIT_BRANCH_RESULTS.md. Binary release
and installation remain separate.

The first function-matching reuse increment, merged in PR34, adapts MacScope's generated-name
guard to saved-report comparison. Generic entry/section and address-shaped donor
labels no longer create cross-build symbol joins. Exact-image matching and model/
configuration checks remain authoritative. See GENERATED_SYMBOL_MATCHING.md for
behavior and eight new plus three affected passing methods. No fingerprint
matcher or new analysis model is claimed.

Manual finding pairs, merged in PR35, add validated explicit selections to the
saved-report API and CLI. MacScope's one-to-one pin precedence is adapted without
copying its framework or adding fingerprints. See MANUAL_FUNCTION_PAIRS.md for
nine new API, five isolated CLI and eleven affected passing methods. Manual pairs
remain review candidates and cannot override exact-image or compatibility guards.

The producer, merged in PR36, emits optional exact-byte body fingerprints through
an audit API/CLI opt-in, using only already-supported substantial functions.
See FUNCTION_BODY_FINGERPRINTS.md for bounds and twelve new plus fourteen affected
passing methods. Default/native-app output is unchanged. Fingerprints do not
perform matching or change unwind findings.

The next local increment adds explicit API/CLI opt-in exact-body candidate
matching after manual/unique-symbol matches. Duplicate evidence and ambiguous
symbol groups are not guessed; compatibility guards remain authoritative.
See EXACT_BODY_CANDIDATES.md for fourteen new API, four isolated CLI, one fresh
pipeline and twenty-five affected passing methods. Default/native-app matching
is unchanged; no identity proof or new analysis semantics is claimed.

Next reuse sequence:

1. FunctionVersionMatcher adaptation for cross-build review candidates, beginning
   with separately qualified native preservation/activation or additional explicit
   evidence. Manual pairs and body production are merged; exact-body candidate
   selection is local. Historical reports lack fingerprints; CFG fingerprints
   and call-graph propagation are not implemented. Structural
   matches must never replace exact image identity or model/configuration checks.
2. Structured refusal facts where they remove duplicated diagnostic handling;
   retain AIRS unknown/discrepancy precedence instead of donor proof precedence.

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
