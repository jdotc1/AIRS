# CBZ/CBNZ v49 bounded qualification

Baseline includes MOVK v48 commit f39211c and preserves the local work-budget
evidence commit ca1c6b7. No publication or installation is claimed.

## Fresh evidence

Eleven new Python state/CFG methods pass in composed runs. The initial decoder
case failed with the expected unsupported-control-flow error before production
changes. Cases cover exact widths/displacements, TBZ refusal, ZR, unchanged
flags/state, raw stack refusal, known skipped bad writes, possible-only mismatch,
unknown recovery precedence, preserved uncertainty, path budget, natural loop,
self-edge refusal, encoded refused-target evidence and shared teardown totals.

One expectation initially used a nonexistent possible-mismatch reason name; it
was corrected to the existing cfg_path_feasibility_unknown. A second witness used
a known original x0 identity instead of an unknown W projection; its input was
corrected. Only failing selectors were rerun. Seven initial passing methods and
three subsequently passing methods were reused. No production defect prompted
these test corrections.

Three emission methods pass on six first-run complete owned Mach-O images.
These exercise CBZ at both widths (CBNZ has unit coverage), retaining two function
entries, LC_FUNCTION_STARTS provenance and preferred BL PC 0x10000101c. Correct
recovery, definite missing-recovery discrepancy and uncertain branch reachability
remain distinct. Reports round-trip and are retained at exclusive paths under
local-evidence/compare_branch-v49. No accepted image was replayed or rehashed.
Six native fixtures copy those first emitted reports directly.

Forty-seven affected existing methods pass: 15 conditional-teardown, five
frame-effect and 27 loop methods. Two new synthetic Python methods qualify exact
v48/v49 architecture/boundary admission and future-label handling.

The real AIRSApp debug product built successfully in 3.86 seconds under the
exclusive shared native gate. Eight new native methods passed: four MOVK and four
CompareBranchReportTests. Other test bundles ran zero methods. Build/test logs
are retained in local-evidence/macscope-reuse-v49. No launch was required for
this analysis/model-registry change; compilation is not GUI acceptance.

Independent read-only semantic/fixture review found no actionable defect. It
checked exact controls, stack provenance, unknown precedence, FP effects, every
conditional-edge classification, registry identities and complete-image claims.
The reviewer performed no execution or writes.

## Reused and excluded scope

MOVK's eight new state/recovery and three emission method results are reused;
historical instruction/CFI/UI/distribution evidence is not replayed. Three new
arithmetic boundary methods adapted from owned MacScope boundary cases
pass without changing production arithmetic: MADD width wrapping, MNEG minimum
and overflowing products, and shifted CMN NZCV/less-than conditions.

MacScope remained read-only. Target instructions were interpreted as data, never
executed. No corpus, GUI, package, signing, notarization, release, install or user
store operation occurred. Clean-machine/minimum-OS/Intel/offline release gaps
remain open. START_HERE.md and docs/VERIFICATION.md referenced by historical
instructions are absent from this public checkout; current contracts, roadmap
and qualified results were used instead.
