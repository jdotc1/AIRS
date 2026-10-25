# TBZ/TBNZ v50 bounded qualification

Baseline: public main c80bc8f, merged PR32. MOVK/CBZ/CBNZ and prior work-budget
results are reused from MOVK_RESULTS.md and COMPARE_BRANCH_RESULTS.md; none was
replayed for publication. The merge used skip-ci commits to reuse accepted results.
The new source increment adds the bounded test-bit branch family.

## Fresh checks

Ten new state/CFG methods pass in composed receipts. Before implementation the
new decoder test produced the intended unsupported_control_flow failure.
Coverage includes all 64 bit indices, both predicates, signed14 displacement
extremes, exact controls, ZR, concrete width masking, unchanged state/NZCV,
original/unknown values, stack-provenance refusal, skipped bad writes, possible
mismatch and later unknown precedence, persistent uncertainty, natural-loop and
self-edge handling, target diagnostics, shared teardown and path/work budgets.

One new budget test initially named a nonexistent Limits field. It was corrected
to max_cfg_steps_per_function and only the failing method was rerun. Nine accepted
methods were reused. No production defect was observed in that correction.

Three new emission methods pass on 12 finalized, first-run owned Mach-O images:
TBZ and TBNZ at bits 0/63, each with correct recovery, concrete missing recovery
and unknown-predicate reachability. Each image retains two function entries and
LC_FUNCTION_STARTS provenance. The original BL PC remains 0x10000101c. Possible-only
discrepancies remain unresolved without supported checked PCs. All64 bit positions
have unit coverage; complete images cover bits 0/63 only. Inputs/reports are
retained under exclusive local-evidence/test-bit-branch-v50 paths; no accepted
image is re-audited, overwritten or rehashed. Target code is never executed.

Two new synthetic Python admission methods pass for exact v50 subtype/boundary/
scope controls and future-label generic import. Eleven affected CBZ/CBNZ methods
pass after the shared predicate changes. The old TBZ refusal sentinel now uses a
reserved B.cond control; historical v49 fixtures remain frozen. Other CFG effects
and historical fixtures reuse accepted results rather than repeat broad suites.

Twelve native fixtures copy the first emitted reports directly. The real AIRSApp
debug product built successfully in 4.04 seconds after acquiring the exclusive
shared gate. Four new TestBitBranchReportTests native admission methods passed
with zero failures; other test bundles ran zero methods. Logs are retained under
local-evidence/test-bit-branch-v50. Native admission covers both operations at
bits 0/63, correct/unknown/discrepant recovery, exact known-model restrictions,
historical/future labels and existing evaluated-DWARF requirements. Build and
admission are source qualification, not GUI or distribution acceptance.

Independent read-only semantic and fixture review found no actionable defect.
It checked split-bit decoding, displacements, all shared-edge classifications,
provenance, uncertainty/unknown precedence and final image/native assertions.
The reviewer performed no tests, builds, hashes or writes.

## Boundaries

MacScope is read-only. Installed app, settings and stores are unchanged. No GUI,
corpus, packaging, signing, notarization, release or install action is included.
Development-Mac source/native qualification does not close clean-machine,
minimum-macOS, Intel-app or offline release gaps. Public binary remains build12.
