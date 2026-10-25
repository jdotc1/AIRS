# Complete owned-image qualification for W SDIV

Public baseline: W UDIV v43 merged through PR #19 (`0e23db7`). This bounded
increment closes the real-parser emission gap for the earlier W SDIV family.
The engine remains `arm64-bounded-w-udiv-v43`, whose cumulative semantics include
W SDIV v42. No production code, model identity, UI or installed product changes.

## Three new complete inputs

The new `test_sdiv_w_emission.py` helper reuses the existing owned final-Mach-O
layout builder without changing it. Before adapting the bytes, it checks all
three instruction words at the declared locations. It then sets numerator to -7,
divisor to 3, and division to SDIV W19,W0,W1. The unknown-input variant instead
uses NOP in the numerator setup, preserving an original symbolic X0.

The unsigned builder intermediate exists only in memory; it is never parsed,
audited or hashed. Only the three distinct final signed input identities are
first qualified. LC_FUNCTION_STARTS, compact unwind entries, allocated stack,
FP/LR/X19 saves/restores and the separately declared sink remain unchanged.
The original declaration includes NOP padding through the first function's bound.
No inspected code is loaded or executed.

| New final input | First-function result | Checked PC / evidence |
| --- | --- | --- |
| Concrete -7/3 with correct X19 recovery | Agreement within synchronous-call scope | Preferred PC `0x10000101c` |
| Concrete -7/3 without X19 recovery | Supported inconsistency | Same PC; expected original X19, observed zero-extended `0xfffffffe` |
| Unknown numerator without X19 recovery | Unresolved | `unknown_recovery_value`; no supported checked PCs |

Every image has a two-function denominator. The declared sink agrees in all
three cases. Both supported outcomes retain LC_FUNCTION_STARTS provenance and
the original call-site address. Each emitted report round-trips through the Python
saved-report codec. These are deliberately owned bounded examples, not a claim
about representative binaries, all interruption points or real-world prevalence.

## Fresh and reused evidence

Three new Python methods passed in the first bounded run. They use real Mach-O
parsing and engine evaluation without parser mocks. Final source images and first
reports are retained locally. Exclusive source/output creation is checked before
an audit starts, so an existing receipt causes refusal before replay or overwrite.
This guard does not authorize repeating accepted checks under another directory.

First emitted reports supply three new native fixture files directly. The frozen
v42 typed fixture and v43 unsigned fixtures are preserved. Three new native
WSDIVOwnedImageReportTests methods check correct scope/PC retention, concrete signed
recovery evidence and unresolved-without-checked-PC behavior. All three passed with zero failures in the first bounded native run. Other
test bundles selected zero methods as intended. No new compiler warnings were
reported.

Independent read-only review found no actionable concern in the exact byte
adaptation, expected results, receipt guard or native test assertions. The review
performed no tests, builds, hashes, writes or target execution.

Existing W SDIV arithmetic/unknown/provenance and model-admission checks, W UDIV
qualification, app build, UI/lifecycle and distribution results were reused. The
native test target compiles the new test source; no repeated app build or GUI
qualification was needed for unchanged production sources. No full suite, original
library audit, random sweep, corpus, signing, packaging, installation or release
publication ran. The installed app, settings and stores remain unchanged.

The original v42 receipt used typed parser substitutes and retains that narrower
meaning. This increment adds real parser-to-engine-to-codec evidence under v43;
it does not retrospectively relabel the v42 result. Clean-machine/minimum-OS and
other open release gates remain open.
