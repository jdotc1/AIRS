# V42 refusal-fixture hardening

After W SDIV v42 and the triage guide merged through PR #17, a focused source
inspection found older regression tests using valid W SDIV `0x1ac10c00` as an
unsupported-word sentinel. This expectation became stale when v42 admitted that
form. The first affected decode-inventory method failed: five observed words now
correctly contained four admitted words and one refusal, rather than the fixture's
intended three admitted words and two refusals.

The hardening changes only test inputs and documentation. Unsupported sentinels
now use `0x3ac10c00`, a control-bit neighbor that the current explicit decoder
refuses. This is an AIRS admission boundary, not a general ISA-validity claim.
Actual positive W SDIV examples remain intact; W UDIV refusal remains intact.
No production code, analysis-model identity or native code changed.

Affected checks retain their original purposes:

- Decode inventory keeps admitted words separate, counts later refusals, preserves
  function and evidence caps, and protects the original input in CLI export.
- Isolated bootstrap still emits identity-bound decode-only JSON, without verdict
  or checked-PC claims.
- CLZ, RBIT and X division neighbor tests retain unsupported-family controls.
- Dead unsupported words and small work limits remain unresolved in X UDIV/SDIV
  recovery checks.

A new paired inventory method explicitly distinguishes valid W SDIV from its
refused control neighbor at separate original PCs. It checks current model
identity, exact refusal location/code, word-scan completeness and the absence of
semantic verdicts/checked-PC fields. Decoder admission does not establish that
symbolic effects or recovery are supported.

## Evidence and scope

Twelve focused methods passed in composed receipts: one new inventory pairing and
eleven affected existing methods. Eleven ran together; independent read-only
review found an additional uppercase W SDIV sentinel in the RBIT test, which was
corrected and checked separately. The first eleven passing results were reused.
The initial pre-correction failure is retained separately from the passing receipt.

The changed synthetic Mach-O inputs were first checked under their new identities;
no accepted unchanged source/image, signing or dependency identity was rehashed.
No full suite, random sweep, real-binary corpus, native build, GUI check or packaging
ran. Accepted W SDIV arithmetic/recovery, Python/native model admission, AIRSApp
build and distribution results were reused. The installed app, settings and stores
remain unchanged. This increment completes regression-fixture alignment; it does
not expand engine capability beyond v42 or close open release/environment gates.
