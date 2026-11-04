# Preferred VM targets in refused direct-edge evidence

Existing CFG validation refuses direct branches outside the modeled body/shared
teardown and calls lacking an independently known function entry. The retained
finding describes the reason and branch PC, but omits the encoded target needed
to investigate which boundary was crossed. This increment adds that diagnostic
without widening branch or callee support.

For cfg_edge_not_modeled, the existing decoder must recognize B or B.cond; for
cfg_call_target_not_modeled it must recognize BL. The current refusal annotation
uses the existing signed displacement plus the original instruction preferred VM
PC, retaining an observed string such as:

`ARM64 instruction word 0x94000080; preferred VM target 0x120c`

The target is an encoded arithmetic destination, not an image-relative offset,
confirmed function entry, reached state or recovery observation. No target bytes
are read, no callee is analyzed, and no path feasibility is inferred. Existing
alignment, mapping, in-function source bounds, exact ordinary subtype, matching
reason, retained evidence and empty-observed guards remain. A mismatched or
undecodable instruction leaves the original evidence intact. Historical auditors,
reason codes/messages, verdicts, scope, checked PCs, schema and v47 are unchanged.

Fresh bounded qualification:

- Four new synthetic methods and three affected refusal-instruction methods passed
  together in 0.015 seconds, with no failures.
- New cases cover B/B.cond forward-outside and backward targets, BL to an unknown
  entry, signed BL displacement, no target read, mismatched/undecodable edge kinds,
  preservation of existing observations and zero retained-evidence budget.
- Initial branch regressions failed on the missing observed target. The call test
  initially used the helper's frameless default and hit its earlier nonleaf refusal;
  its corrected explicit frame fixture forces current CFG dispatch and failed on
  the missing target before implementation. No passing checks were replayed then.

Independent read-only review found no actionable issue in signed target handling,
attribution gates, evidence budgets or preservation of supported outcomes.

These are tiny typed input tests, not complete image qualification. Accepted
semantic, native-build, GUI and distribution evidence is reused. Native source is
unchanged. No image execution, hashing, corpus pass, app packaging, installation,
release, settings or store operations were performed.
