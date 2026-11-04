# Scalar REV32 v46 bounded qualification

Public baseline: REV16 v45 merged through PR #22 (`f104b2a`). Source model:
`arm64-bounded-rev32-v46`. Native deployment remains macOS 14. No installed or
published binary update is claimed.

## Fresh checks

Fourteen new Python methods passed: eleven in `test_rev32.py`, plus three in
`test_rev32_emission.py`. They cover exact X-only controls and positive W/full-REV
neighbors, lane order with an independent serialization oracle, masking above 64,
negative/high-bit values, aliases, concrete versus symbolic double reversal,
ZR/discard, raw stack sources, unknown inputs, flags/conditions, SP/memory and
unrelated state, frame/preserved writes, correct/wrong/unknown recovery,
uncertain-path/later-unknown precedence, work limits and exact model admission.

The three emission methods first qualify new correct, missing and unknown X19
recovery images through real Mach-O parsing and engine evaluation. Each retains
two functions, LC_FUNCTION_STARTS provenance, the independent sink and original
preferred call PC. The discrepancy preserves `constant 0xffffffffcbedffff`;
unknown recovery has no supported checked PCs. First reports round-trip through
the Python codec and remain retained behind exclusive pre-audit output guards.
No accepted input or layout-builder intermediate was audited or rehashed.

Ten affected existing methods passed: six REV16 arithmetic/provenance/unknown/
call/decode/leaf methods, three full-REV decode/leaf/arithmetic methods and one
RBIT neighbor refusal method. Obsolete REV32 refusal sentinels now use unmodeled
control neighbors. Existing W REV remains positively admitted at the sf=0 neighbor.
Unchanged passing checks were not replayed, and no full suite or corpus ran.

The real AIRSApp debug target built in 2.47 seconds. Four new REV32ReportTests
native methods check concrete evidence, correct versus unknown outcomes, exact
model/scope/PC retention, strict subtype/boundary/scope/recovery and DWARF admission,
and historical/future labels. All four passed with zero failures in the first bounded native run. Other test
bundles selected zero methods as intended. No new compiler warnings were reported.
Three native fixtures reuse the first emitted reports without re-auditing images.

## Review and reuse

Independent read-only semantic and fixture/native review found no actionable issue.
It checked the two-stage lane transformation, exact W/X distinction, unchanged
REV/REV16 paths, independent expected values, image layout and codec assertions.
The reviewer ran no tests, builds, hashes, writes or target code.

Exact v46 is registered across all three Python/native known-model lists. Admission
does not verify that a producer actually performed its claims. Frozen historical
fixtures, other arithmetic families, CFI evaluation, UI/lifecycle and distribution
results are reused. The earlier CFI current-producer assertion maintenance remains
source-only and is not promoted to fresh runtime evidence.

No random sweep, old-library audit, GUI, packaging, signing/notarization,
installation or release publication occurred. Target machine code is data and was
never executed. Installed app, settings and stores remain unchanged; clean-machine,
minimum-OS and other open release gates remain open.
