# Scalar REV v44 bounded qualification

Public baseline: complete owned-image W SDIV qualification merged through PR #20
(`7cb3e70`). New source model: `arm64-bounded-rev-v44`. No installed or published
binary change is claimed. Native deployment remains macOS 14.

## Fresh checks

Fourteen distinct new Python methods passed: eleven in `test_rev.py`, plus three
in `test_rev_emission.py`. They cover exact W/X controls and excluded neighboring
families, independent byte-order expectations, width masking, negative/high-bit
inputs, aliases, double reversal, ZR/discard, raw stack provenance, unknown/original
values, flags and their consumers, SP/memory/unrelated state, frame/preserved
writes, correct/wrong/unknown call recovery, uncertain-path/later-unknown precedence,
work limits and exact current/historical/future model admission.

The three emission methods first qualify six new complete owned Mach-O identities:
correct, missing and unknown X19 recovery at each width. Real parser, engine and
Python codec results preserve two functions, independent LC_FUNCTION_STARTS
provenance and the original preferred call PC. Correct variants agree; incorrect
metadata retains the differing W/X concrete discrepancies; unknown variants have
no supported checked PCs. Each first report is retained. Exclusive paths are
checked before an audit begins to prevent accidental receipt replay/overwrite.
The builder intermediate is not parsed, audited or hashed.

Two affected existing RBIT neighbor methods passed after their old full-REV refusal
sentinels were replaced with an unmodeled W opcode3 control. Remaining REV16,
X REV32, CLS and other refusals remain intact. No passing method was repeated
unchanged, and no unrelated suite or corpus ran.

The real AIRSApp debug target built successfully in 3.42 seconds. Four new
REVReportTests native methods passed with zero failures. They preserve W/X evidence,
correct/unknown outcomes, original PC/scope, strict architecture/boundary/scope/
recovery admission, historical/future label handling and DWARF encoding/coverage
admission. Four native fixtures directly reuse first emitted reports. No new
compiler warnings were reported in the incremental build/test logs.

## Review, reuse and limits

Independent read-only semantic and fixture review found no actionable issue.
It verified the width-dependent controls, byte arithmetic expectations, provenance
and recovery guards, complete-image adaptation and native assertions. The reviewer
ran no tests, builds, hashes, target code or donor modifications.

Exact v44 is added to all three Python and native known-model admission lists.
Import admission is not verification that a producer actually performed the
claimed analysis. Historical fixtures remain frozen. Source, hashes and behavioral
receipts for unchanged inputs, other instruction families, CFI evaluation,
UI/lifecycle and distribution were reused. The prior source-only CFI test assertion
repair was not promoted to fresh runtime evidence.

No real-binary corpus, random sweep, old-library audit, GUI launch, packaging,
signing/notarization, installation or release publication occurred. Inspected
machine code is data and was never executed. Installed app, settings and stores
remain unchanged. Clean-machine/minimum-OS and other open release gates remain open.
