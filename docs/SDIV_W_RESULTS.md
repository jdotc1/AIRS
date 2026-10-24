# W SDIV v42 bounded qualification

This source-only increment uses model `arm64-bounded-w-sdiv-v42` on the public
baseline, following the locally committed saved-report triage guide. It is not a
new installed or published binary. The native deployment target remains macOS14.

## Fresh Python evidence

Eleven distinct new methods in `test_sdiv_w.py` passed in composed receipts:

- Exact encoding, fixed-control neighbors and retained W UDIV refusal.
- Independent fixed-step quotient oracle, signed edges, zero divisor, overflow,
  low32 projection of both operands and zero-extension.
- Aliased operands, ZR inputs and discarded destination.
- Raw stack-source refusal before projection, simplification or discard.
- Conservative original/unknown inputs with preserved flags, memory and SP.
- Owned leaf agreement and unsigned-neighbor unresolved boundary.
- Frame destination and unrestored preserved-register refusal.
- Correct/wrong/unknown call recovery with the original observation PC.
- Exact v42 model and strict import boundary with historical/future controls.
- Possible-only discrepancy and later-unknown unresolved precedence.
- Engine report emission and saved-codec round trip for the owned call witness.

The first nine methods passed. Independent review recommended adding high-bit
divisor truncation and INT_MIN/3 to the arithmetic method; only that changed method
was repeated, together with two newly added recovery/emission methods. The other
eight accepted results were reused. No random sweep or corpus ran.

Seven affected existing methods passed once: X SDIV arithmetic, aliases, raw-stack
refusal and unknown propagation through the shared transfer; the two X boundary
methods and one variable-shift neighbor method whose former W SDIV refusal
expectations changed. W UDIV and unrelated reserved-neighbor refusals remain.

## Review and fixture limits

Independent read-only review found no transfer or exact model-registration defect
and supplied the additional arithmetic and recovery cases above. It ran no tests,
builds, source hashes or target code and did not modify donor code.

The emitted native fixture is copied from the first new engine round trip. Its
image and unwind parser inputs are typed owned substitutes; identity fields are
explicit test placeholders, not digests of an independently parsed Mach-O. It
contains a deliberate X19 call-site mismatch and an owned leaf sink. It proves
emission/codec/model admission composition, not real-image parsing or prevalence.
The observed call-site X19 is zero-extended `0xfffffffe` at `0x101c`.

## Native and distribution scope

The real AIRSApp debug target built successfully in 38.53 seconds using the local
SwiftPM macOS package. The three new WSDIVReportTests methods qualify model/scope/
PC retention, strict architecture/boundary/scope/recovery admission and DWARF
coverage/encoding admission. All three passed with zero failures in the first bounded native run. Other
test bundles selected zero methods, as intended. Compilation reported an existing
unused Bool result warning in FileOpenRoutingTests.swift:212; it was not changed.

Accepted unrelated semantic, CFI-v41, aggregation, UI, lifecycle and distribution
receipts are reused. No full suite, original library audit, GUI launch, signing,
notarization, packaging, installation or release publication was performed. The
installed app, settings and stores were left unchanged. Clean-machine/minimum-OS
and other open release gates remain open.
