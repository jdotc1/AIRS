# Scalar CLS v47 bounded qualification

Public baseline: REV32 v46 merged through PR #23 (`4ac87c5`). New source identity:
`arm64-bounded-cls-v47`. Native deployment remains macOS 14. No installed or
published binary update is claimed.

## Fresh checks

Fourteen new Python methods passed: eleven in `test_cls.py`, plus three in
`test_cls_emission.py`. They cover exact controls and the CLZ neighbor, sign-bit
exclusion, independent bit-scanning expectations, zero/all-ones, sign transitions,
negative/high-bit inputs, W projection, aliases, ZR/discard, raw stack provenance,
unknown/original values, flags/conditions, SP/memory/unrelated state, frame/preserved
writes, definite/possible/unknown recovery, work limits and exact model admission.

The three emission methods first qualify six new complete Mach-O identities:
correct, missing and unknown X19 recovery at both widths. Real parsing and engine
emission retain two functions, LC_FUNCTION_STARTS provenance and original preferred
call PC. Concrete discrepancies preserve counts 18/50; unknown variants have no
supported checked PCs. First reports round-trip through the Python codec and are
retained behind exclusive pre-audit paths. Builder intermediates and accepted
images were not audited or rehashed.

Thirteen affected existing methods passed in composed receipts: all eight bounded
CLZ methods over the changed shared transfer, two X RBIT refusal/dead-word methods,
one W RBIT neighbor method and REV16/REV32 decoder-neighbor methods. Old CLS
refusal sentinels now use unmodeled control neighbors. CLZ counts, stack error code,
unknown propagation, state and recovery behavior remain intact.

One requested X RBIT method initially named the wrong test class, producing a
loader AttributeError without executing that method. Only the selector was
corrected; that method then passed. The other fifteen passing methods in the
emission/affected command were reused, not replayed. This selection error is kept
separate from implementation results; no production failure was observed.

The real AIRSApp debug target built successfully in 4.14 seconds. Four new
CLSReportTests native methods cover differing W/X counts, correct versus unknown
recovery, exact model/scope/PC retention, strict subtype/boundary/scope/recovery/
DWARF admission and historical/future labels. All four passed with zero failures in the first bounded native run. Other
test bundles selected zero methods as intended. No new compiler warnings were
reported. Four fixtures reuse first emitted reports directly.

## Review and reused scope

Independent read-only semantic and fixture/native review found no actionable issue.
It checked sign-bit exclusion, normalization, independent expected values, exact
controls, provenance/write/frame guards, complete-image layout and codec assertions.
The reviewer ran no tests, builds, hashes, writes or target code. Historical fixtures
remain frozen. Exact v47 is registered across all three Python/native known-model
lists; admission does not verify that a producer actually performed its claims.

Other instruction families, CFI evaluation, UI/lifecycle and distribution results
are reused. Earlier source-only CFI assertion maintenance is not promoted to fresh
runtime evidence. No random sweep, corpus, old-library audit, GUI, packaging,
signing/notarization, installation or release publication occurred. Target code
was never executed. Installed app, settings and stores remain unchanged;
clean-machine/minimum-OS and other open release gates remain open.
