# Swift synchronous throwing-call recovery

The independent `swift-sync-error-edges-v1` model identifies bounded structural
success/error return edges in ordinary ARM64 Mach-O images. This is the first
Swift decompilation slice: it does not reconstruct complete `do/catch` source.
The existing unwind audit and its model identity remain unchanged.

```
python3 -I -B airs_cli.py swift-error-flow Example.dylib --output flow.json
```

## Admission and evidence

A direct BL must target an exact LC_FUNCTION_STARTS entry with one public,
file-backed executable-section symbol. Section-end labels, aliases, private,
resolver and alternate entries do not supply declarations. The complete supported
mangling is two length-prefixed ASCII identifiers followed by `yS2iKF`: an
ordinary synchronous, untyped throwing free function taking one unlabeled
Swift.Int and returning Swift.Int. Other declarations remain declined, including
async, typed throws, generic functions, methods and thunks. Symbol declarations
are structural evidence, not authenticated runtime targets.

An eight-word post-call window tracks x21 and live 64-bit MOV copies, respecting
overwrites and the zero register. NOP is allowed. A forward 64-bit CBZ/CBNZ of a
live error-result alias must have two distinct aligned successors inside the same
caller. Zero means success; nonzero means error. Unknown instructions, other
branches/calls, narrow tests and clobbered aliases stop recovery. Existing data,
relocation and symbol-only boundary exclusions remain effective.

The report retains raw instruction words, preferred VM addresses, relative call
and callee offsets, selected-slice identity, declaration evidence and declined
reasons. Default limits reuse decode inventory bounds: 8 MiB input, 1,024
functions, 4,096 words per function, 16,384 total words, 32 call details per
function and 256 total. Omitted details and incomplete scans are explicit.
Exit status is 0 for complete scanning/detail retention, 1 for partial coverage,
and 2 for input errors; status 0 does not mean all calls were recovered.

## Reuse and limits

The implementation reuses AIRS Mach-O admission, ARM64 instruction decoding,
input resolution and protected atomic exports. The x21 convention follows the
same ordinary-throws distinction used by MacScope. No MacScope source is changed
and no runtime dependency or external demangler is introduced. Primary references:

- https://github.com/swiftlang/swift/blob/main/docs/ABI/CallingConventionSummary.rst
- https://github.com/swiftlang/swift/blob/main/docs/ABIStabilityManifesto.md#error-register
- https://github.com/swiftlang/swift/blob/main/docs/ABI/Mangling.rst

Candidates may occur in unreachable instruction words. This pass proves neither
reachability nor dominance, catch types, handler meaning, source equivalence,
unwind correctness, async behavior or compatibility beyond the admitted subset.
Selected code is parsed as data and never executed.

## Qualification

Twenty-two focused methods cover positive recovery, polarity, aliases and kills,
width, intervening instructions, successor bounds, complete declaration grammar,
symbol attribution, entry exclusions, scan budgets and protected CLI exports.
Accepted cases were reused; only the three CLI methods were repeated after their
temporary-directory setup changed. Independent semantic review found and prompted
a section-end attribution regression test and fix, then found no remaining
correctness issue in the reviewed boundaries.

An owned optimized Swift dylib compiled from
`fixtures/swift-error-flow/OwnedThrows.swift` was independently disassembled and
then analyzed once. Of 14 direct-call candidates in 173 scanned words, one was
recovered and 13 declined; no call details were omitted. The call at 0x934 targets
`AIRSErrorFlow.parse` at 0x890. The x21 test at 0x938 has success successor 0x948
and error successor 0x93c, matching the independent disassembly. This is owned
compiler-output qualification, not a corpus, native app or GUI acceptance claim.
Generated images and detailed execution receipts remain outside tracked source.

Next: qualify additional explicit Swift signatures and recover bounded handler
regions before presenting source-like `do/catch` output. Every extension needs a
positive owned example and an independently reviewed refusal boundary.
