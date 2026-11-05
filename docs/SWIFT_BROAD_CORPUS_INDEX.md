> Historical component milestone. Final composed qualification and current limits are recorded in docs/swift/BROAD_QUALIFICATION.md; earlier corpus counts are not additive.

# Owned broad Swift corpus and independent compiler index

The generator owns 420 distinct source declarations: 80 free functions, 100
struct methods, 55 enum methods, 60 class methods, 45 static/type/extension
methods, 35 generic methods, 25 protocol requirements with concrete witnesses,
and 20 actor async methods. The category counts are disjoint. Of these, 340 are
nominal instance/type methods, including generic static methods. Protocol requirements and witnesses are represented by one owned case,
not double counted. Each declaration has two public, non-inlined source callers.

The manifest records case ID, owner, typed signature shape, dispatch, body
semantics, a feature vector independent of spelling, and each actual source
call expression and line. There are 100 concrete three-argument type combinations
using Int, Int32, UInt64, Double, Bool, String and [Int]. Bodies normalize their
real argument types, branch on the resulting value, throw an associated error,
and compute a result; they are not renamed empty functions. Thresholds,
predicates, arithmetic operations, receiver bias, throwing closures/rethrows,
typed throws, generic constraints and actor isolation supply additional source
features. Numeric thresholds are genuine semantic differences, but do not imply
that all cases have different emitted ABI lowerings. Emitted ABI diversity still
requires independent classification after compilation.

The tracked source and manifest are **source only and uncompiled**. They claim
zero emitted observations. Source signature diversity does not establish outcome
eligibility, actual instruction geometry, or any compiler lowering family.

Run stages explicitly, with a fresh compile directory and the shared storage
guard. These commands are recipes, not completed compilation evidence:

```sh
storage-guard run -- python3 scripts/swift_fixture_matrix.py generate \
  --source-dir NEW_SOURCE_DIRECTORY
storage-guard run -- python3 scripts/swift_fixture_matrix.py compile \
  --source-dir fixtures/swift-error-flow/broad --output-dir NEW_EVIDENCE_DIRECTORY
storage-guard run -- python3 scripts/swift_fixture_matrix.py index \
  --source-dir fixtures/swift-error-flow/broad --output-dir NEW_EVIDENCE_DIRECTORY
```

The compile stage requires Swift 6.x on macOS arm64. It captures the source once,
computes its SHA-256 once, and compiles the captured identity at Onone/O/Osize
using Swift language mode 6, macOS 14 arm64, and library evolution. The receipt
records exact command flags, compiler version, SDK path, source digest and each
emitted library digest. A partial run remains partial; an existing destination
is refused. There is no resume/retry or verification-bypass switch.

The 30-minute budget begins at compilation and is shared with indexing. The
512 MiB bound covers the evidence directory including source snapshot, libraries,
logs and disassembly. Compiler temporary files and module caches remain inside that bound. The
launcher monitors its active subprocess group, kills and drains the group on a
bound violation, and checks the final output size, preserving partial outputs. Library code is never loaded
or executed. Indexing reads the captured manifest and existing receipt; it does
not re-hash the source or emitted files.

The independent index uses LLVM objdump and nm, without importing an AIRS parser,
decoder, semantic engine or demangler. Each observed call records its actual PC,
raw instruction word, raw enclosing symbol, direct/indirect kind and target PC.
Direct branch destinations are decoded from the instruction word and matched
against nm addresses; disassembly annotations are diagnostic only. Caller symbols or their nm aliases
must contain the stable source caller token. Each mode deduplicates actual PCs
and reports per-declaration emission counts. Direct targets must contain the
corresponding owned declaration token to count toward the 1,500 minimum. Runtime
helper calls are retained but do not count. Unresolved indirect calls are retained
as requiring attribution and do not count. Cases without an owned call are
explicitly marked `optimized_away_or_no_owned_call_observed`; no synthetic
observation is substituted. Actual counts below 1,500 produce an incomplete index.

The source has 840 callers and a theoretical 2,520 opportunities across three
modes, but optimization, virtual dispatch, actor lowering and generic
specialization may reduce confirmed counts. Only the compiler index establishes
the actual count. A below-threshold result requires changed source and separately
scoped continuation; it does not authorize repeating unchanged compilation.

When the export-destination registry is full, reuse an existing registered output
root through `--output-dir EXISTING_REGISTERED_ROOT --run-name RUN_FILENAME` on
both compile and index commands. The same run name maps both stages to the same
child directory. The root must already exist, the run name must be one filename,
and symlinks escaping the root are refused. Compilation still refuses an existing
child. This reuses the registered destination; it does not change the registry or
bypass the storage guard. Tool discovery subprocesses use the same process-group,
time and storage limits, and index parsing checks the shared deadline.

## Source matrix v2: broader return and ownership shapes

`fixtures/swift-error-flow/broad-v2` is a separate source identity generated with
`generate --generation 2`. The original v1 fixture files and captured compiler
receipts remain unchanged. V1 produced 2,214 independently indexed confirmed
physical owned call instructions (Onone 630, O 800, Osize 784); this is reused
compiler-index evidence and does not establish the required ABI diversity.

V2 contains 420 cases with the same disjoint category minima and 340 methods.
Its 23 actual return families include Void, Bool, signed and unsigned 8/16/32/64-bit
integers, native Int/UInt, Float/Double, Optional Int, small and large structs,
payload and empty enums, a tuple, a reference, String and a Sendable existential.
These are real declared return types and corresponding return expressions.
Its 12 parameter forms include zero arguments, one signed argument, multiple
scalar arguments, inout, String/array, Float/Double, Optional, tuple, small and
large aggregates, a borrowing reference and a consuming aggregate. Generic
methods append a constrained argument; rethrows cases append a throwing closure.

Nominal contexts now include mutating and nonmutating struct methods, final and
nonfinal class methods, enum static methods, payload/empty enum instances, and
instance extension methods as well as static and class type methods. Actors and
protocol existential witnesses remain explicit cases. The 420 feature vectors
exclude thresholds and symbol spelling, and remain distinct by typed return,
parameter family, ownership/context, dispatch and body operation.

Each source caller records one of twelve source geometries: handled try, try?,
try!, propagation, multiple calls sharing a handler, early return, nested
handlers, local error conversion, a noreturn handler, tail return, an inline
absence challenge, and defer cleanup. These are source expectations; the compiler
may merge, inline, eliminate or otherwise lower them. No source geometry is
promoted to an observed emitted geometry by generation. Inline cases deliberately
challenge absent-call handling. Zero-argument cases may fold to constant outcomes.

The v2 manifest identifies `owned-swift-broad-v2`, and a new compilation receipt
binds that generator identity to its captured source and captured manifest. V2
has not been compiled by the generator worker. At least 80 actual emitted ABI
shapes, 1,500 confirmed calls and the downstream lowering/geometry gates still
require the separately authorized changed-source compilation and independent
classification. No v1 verification, hashing or disassembly was repeated to make
this change.

V2 defer callers accept a caller-owned `inout Int` cleanup slot and invoke the
owned `@inline(never)` cleanup helper from defer. The observable mutation escapes
to the source caller, rather than changing an unread local. Manifest sites mark
that external inout cleanup explicitly. An `inline_absence_challenge` site is
labelled only when its target actually carries `@inline(__always)`; each site
records the target attribute. Neither attribute guarantees a particular emitted
outcome, and all twelve observed-geometry gates remain pending compilation.

## V2 ownership correction after the first compiler failure

The first v2 Onone compilation failed with four ownership errors in shared-handler
callers 0231_1, 0232_0, 0243_1 and 0244_0: each consumed its `owned` argument twice.
The failed captured source and compile log remain preserved in the initial v2
evidence directory. No successful library resulted from that compiler stage.

The separate source fixture `broad-v2-fixed` identifies generator version
`owned-swift-broad-v2-fixed`. Each affected caller constructs `firstOwned` from
`owned.value` and `owned.other` before either consuming call, consumes that value
for the first call, and consumes the original argument only for the second call.
The source manifest marks this explicit field copy. The target declarations,
return/parameter families, dispatch contexts and control-flow geometries are
preserved. This correction has a focused source regression test; it has not been
compiled by the generator worker. A changed-source retry requires the parent's
specific verification authorization. The failed v2 capture and v1 evidence are
not overwritten or rechecked.
