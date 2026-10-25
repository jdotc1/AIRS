# Scalar REV16 v45 bounded qualification

Public baseline: REV v44 merged through PR #21 (`0de2403`). New source identity:
`arm64-bounded-rev16-v45`. Native deployment remains macOS 14. No installed or
published binary update is claimed.

## Fresh checks

Fourteen new Python methods passed: eleven in `test_rev16.py`, three in
`test_rev16_emission.py`. They cover exact fixed controls and scalar widths,
lane-local byte ordering with an independent serialization oracle, high/negative
inputs, W masking/zero-extension, aliases, concrete versus symbolic double reversal,
ZR/discard, raw stack provenance, unknown values, flags/conditions, SP/memory and
unrelated registers, frame/preserved writes, definite/possible/unknown recovery,
work limits and current/historical/future import admission.

The three emission methods first qualify six distinct new complete Mach-O inputs:
correct, missing and unknown X19 recovery at both widths. Real parsing and engine
emission preserve two functions, independent LC_FUNCTION_STARTS boundaries and
the original preferred call PC. Correct metadata agrees; missing metadata preserves
the width-dependent concrete discrepancy; unknown variants stay unresolved with
no supported checked PCs. First reports round-trip through the Python codec and
are retained under exclusive pre-audit paths. No accepted unsigned/full-REV image
or builder intermediate was parsed, audited or rehashed.

Ten affected existing methods passed: eight full-REV state/decode/recovery methods
cover the shared path, plus two RBIT neighbor methods whose old REV16 refusal
sentinels changed. The full-REV byte loop is retained. The new controls remain
unmodeled; X REV32, unmodeled W opcode3, CLS and vector refusals remain intact.
No passing method was repeated unchanged and no full suite or corpus ran.

The real AIRSApp debug target built successfully in 2.51 seconds. Four new native
REV16ReportTests methods cover width-specific evidence, correct versus unknown
recovery, exact model/scope/PC retention and strict subtype/boundary/scope/recovery/
DWARF admission with historical/future controls. All four passed with zero failures in the first bounded native run. Other
test bundles selected zero methods as intended. No new compiler warnings were
reported. Four native fixtures directly reuse first emitted reports.

## Review and reused scope

Independent read-only semantic review found no corrective issue in the exact
controls, lane masks, state guards, oracle and expected recovery values. It ran
no tests, builds, hashes, writes or target code. Historical fixtures remain frozen.
Exact v45 is added to all three Python/native known-model admission lists; import
admission still does not establish that the producer actually ran its claims.

Other instruction families, CFI evaluation, UI/lifecycle and distribution results
are reused. The earlier CFI current-producer test maintenance remains source-only
qualification and is not promoted to fresh runtime evidence. No random sweep,
old-library audit, GUI, packaging, signing/notarization, installation or release
publication occurred. Target bytes were never executed. Installed app, settings
and stores remain unchanged; clean-machine/minimum-OS and other open release gates
remain open.
