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

## Opt-in bounded error-region intervals

```
python3 -I -B airs_cli.py swift-error-flow Example.dylib --include-error-regions --output flow.json
```

The optional `swift-sync-error-region-v1` supplement describes local structural
intervals for recovered calls. Default reports retain the original edge-only
shape and model. A region decline does not invalidate or promote an edge result.
The report adds `error_region_model_version`, per-call `error_region`, and
recovered/declined region counts in the summary. These counts cover retained
recovered edges only; omitted calls and declined edge candidates remain visible
in the original scan/detail counters. Existing exit status describes scan/detail
completeness, not successful region recovery.

The first admitted layout requires the error successor to be the instruction
immediately after the test, before a forward success successor in the same
caller. The success entry is the proposed exclusive-end join boundary. At most
16 words may lie in the interval, and every word must be in the already scanned
caller prefix. Supported words are NOP, 64-bit MOV/MOVZ/MOVN, opaque direct BL,
and a final unconditional B exactly to the proposed join. Other instructions,
reverse layouts, early or differently targeted branches and truncated scan
prefixes decline with explicit reasons. No additional instruction family is
added to the existing decoder or unwind model.

Each admitted word retains its PC, raw encoding and kind. BL retains its target
and `opaque_call` label without claiming a callee identity or behavior. Both
`call_return_proven` and `join_reachability_proven` are false. There is no proof
that calls return, that the join executes, that the interval has no other incoming
edges, or that it is exclusively entered on error. The join is not a proven
postdominator. This is neither catch-type recovery nor source-level handler
reconstruction.

Eleven new focused methods passed, covering the owned shape, default preservation,
CLI opt-in, opaque calls, permitted final join branch, rejected control flow,
reverse layouts, the exact 16-word bound and scan-prefix refusal. Independent
semantic review found no blocking correctness issue. Accepted edge and CLI
qualification was reused rather than replayed.

The same accepted owned compiler image and independent disassembly supplied the
new region qualification. Only the new helper analyzed the accepted caller bytes;
compilation, disassembly, image hashing/admission and edge analysis were not
repeated. It recorded MOV at 0x93c, an opaque BL at 0x940 to 0xaec, and MOVN at
0x944, with proposed join 0x948. Disassembly labels the call as an error-release
stub, but the report deliberately assigns no runtime meaning to that target.
This is source-engine qualification; native presentation, installation and
release acceptance remain separate.

## Opt-in caller-local direct-entry validation

```
python3 -I -B airs_cli.py swift-error-flow Example.dylib --include-error-regions --validate-region-entries --output flow.json
```

`--validate-region-entries` requires `--include-error-regions`. It adds the
`swift-region-direct-entries-v1` model marker and an `incoming_validation`
supplement to retained structural region candidates. Declined regions have no
validation claim; default edge and region reports remain unchanged.

The validator classifies the already bounded caller prefix once per caller using
the existing decoder. It checks direct B, BL, B.cond, CBZ/CBNZ and TBZ/TBNZ targets.
A source outside the half-open candidate interval targeting its start or interior
is an unexpected direct entry. Sources inside the interval are not side entries;
the proposed join is outside the interval. The expected adjacent error-test
fallthrough remains allowed by the region layout. The pass does not execute
code or assume a direct branch is reachable.

Results have three statuses:

- `unexpected_direct_entries`: at least one conflicting direct edge is observed,
  even when scan coverage is partial or other words are unclassified.
- `unresolved`: no conflict is observed, but caller coverage is incomplete or
  at least one word cannot be classified, including unsupported indirect control
  transfers or invalid direct-target arithmetic.
- `no_unexpected_direct_entries`: the full caller is scanned, every word is
  classified, and no conflicting direct target is observed within this scope.

The supplement retains source/target PCs, raw encodings and branch kinds, caller
scan completeness and word counts. Conflict and unclassified-word details are
capped separately at 16 entries while retaining exact totals and detail
completeness fields. Classification shares the existing function/word budgets;
region inspection does not extend the admitted caller prefix. Existing CLI exit
status still reports scan/detail completeness rather than semantic approval.

`exclusive_entry_proven` is always false. This check covers caller-local direct
edges only. It does not exclude indirect or external entries, prove reachability,
prove that calls return, establish a postdominator or recover catch semantics.
An observed side entry supplements the candidate; it does not erase the original
structural region or alter the unwind result. Consumers must inspect validation
status before using an interval as a structured presentation candidate.

Seventeen new focused methods passed across positive, boundary and review controls.
They cover all supported direct families, start/interior/join boundaries,
internal opaque calls, unknown/indirect words, invalid target arithmetic, partial
scans, conflict precedence, evidence caps, default preservation and API/CLI option
requirements. Independent semantic review found no blocking correctness issue.
Accepted edge/region qualification was reused.

Only the new classifier and entry validator analyzed the accepted owned caller
bytes at 0x920 through 0x958. All 14 words were classified, with zero unexpected
caller-local direct entries to the accepted interval [0x93c, 0x948). The output
retains `exclusive_entry_proven: false`. Compiler, disassembly, identity, edge and
region results were reused without replay. This is source-engine qualification,
not native UI, installation, distribution or release acceptance.
