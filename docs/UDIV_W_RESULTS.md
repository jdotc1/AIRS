# W UDIV v43 bounded qualification

Public baseline: merged v42 refusal-fixture hardening, PR #18 (`8b9f6de`).
The new source identity is `arm64-bounded-w-udiv-v43`; it is not a published or
installed binary update. Native deployment remains macOS 14.

## Fresh Python evidence

Twelve distinct new methods passed in composed receipts: eleven arithmetic,
provenance, decode, state/recovery and exact-import methods in `test_udiv_w.py`,
plus one real parser/engine emission method in `test_udiv_w_emission.py`. The
historical-import method was then decoupled from a current-model constant assertion;
only that changed method was repeated. Other accepted new results were reused.

The bounded edge cases cover low32 masking of both sources, unsigned high-bit
values, zero divisor, zero-extension, aliases, ZR/discard, raw stack-source refusal,
unknown/original inputs, NZCV consumers, memory/SP and unrelated registers,
frame/unrestored preserved destinations, correct/wrong/unknown call recovery,
possible-only mismatch and later-unknown precedence. The independent arithmetic
oracle uses 32 fixed long-division steps; no random sweep ran.

The emission method first qualifies two new complete owned Mach-O variants with
real parsers and the engine, without mocks. Both preserve a two-function denominator
and the declared LC_FUNCTION_STARTS boundaries. Correct metadata agrees; missing
X19 recovery is inconsistent at preferred PC `0x10000101c`, observing
`constant 0x7fffffff`. The independently declared sink agrees. Each emitted report
round-trips through the saved codec. The first mismatch report is reused directly
for native admission; no unchanged input was re-audited to create that fixture.

Fourteen affected existing methods passed: seven X UDIV arithmetic/alias/stack/
unknown/flags/neighbor/leaf methods through the changed shared transfer, two X SDIV
neighbor/leaf methods, one variable-shift neighbor method, and four W SDIV decode/
leaf/historical-admission/current-emission methods. Refusal controls now use
unmodeled neighbors. Current W SDIV producer output uses a model-specific local
root and current model assertion; frozen historical artifacts are not overwritten.

## Source review and reused boundaries

Independent read-only semantic review found no actionable correctness issue in
the transfer, exact registration, edge cases or independent complete-image builder.
It supplied high-bit divisor/zero cases and identified affected neighbor/current-
identity tests. It ran no tests, builds, hashes, target code or donor modifications.

The historical CFI emission test's current-producer identity assertion and receipt
name were corrected in source. That changed method was syntax-checked and source-reviewed, not
executed: its accepted CFI image workflow was not replayed or rehashed. Prior CFI
behavioral results are reused, not claimed as execution of the changed assertion.
Other unrelated semantics, diagnostics, UI/lifecycle and distribution evidence
remain reused.

## Native and release scope

The real AIRSApp debug target built successfully in 3.40 seconds. Three new native
WUDIVReportTests cover exact model/scope/PC retention, strict subtype/boundary/scope/
recovery and historical/future admission, and DWARF coverage/encoding admission.
All three methods passed with zero failures in the first bounded native run.
Other test bundles selected zero methods as intended. No new compiler warning was
reported in the incremental build/test logs.

No full suite, real-binary corpus, GUI, packaging, signing/notarization, installation
or release publication was performed. The installed app, settings and stores
remain unchanged. Clean-machine/minimum-OS and other open release gates remain open.
