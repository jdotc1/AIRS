# Broad Swift ABI admission foundation

`swift_abi_profiles.admit_swift_abi(image, declaration, qualification=None,
limits=ABILimits())` is a research admission layer separate from declaration
syntax and the historical narrow method profile. It returns `status`, `reason`,
`profile`, and an `evidence` object. `declaration` accepts the bounded parser's
`BroadDeclarationResult` or frozen `SwiftCallableIdentity`. An unsupported syntax
result retains its specific refusal reason, including async, typed throws,
witness/thunk, and unsupported generic families. No demangled display string is
used as ABI authority.

The immutable candidate capability is
`swift6-arm64-sync-untyped-research-v1`: ordinary ARM64, synchronous Swift in
language mode 6, ordinary untyped throwing error transport. Its `x21` capability
is emitted only after a matching lowering observation is admitted. It has no
async, typed-throws, witness dispatch, virtual dispatch, arm64e, or unproved
generic capability. A method body observation never qualifies arbitrary callers
or proves their dispatch targets; the flow layer must establish those separately.

## Nominal identity admission

The selected image's `__TEXT,__swift5_types` direct relative entries are read
with limits before access: section entries, parent depth, identifier bytes,
address overflow and cumulative bytes read. Tagged indirect and null pointers,
parent cycles, malformed ranges, unknown descriptor versions, unsupported parent
kinds and unknown flags on the matching chain return explicit unresolved reasons.
The defaults allow 1,024 entries, 16 parents, 256 bytes per identifier including
its terminator, 256 section mappings, and 32,768 bytes of total reader work.
Each access requires exactly one mapping, file-backed storage, and a file extent
inside both the selected slice and the retained image bytes.

Exact matching uses the module and the entire ordered `(name, kind)` parent
chain, with kinds 16/class, 17/struct, and 18/enum. Module parents must be null.
Uniqueness is checked across the complete bounded entry directory. References
to the same descriptor PC are deduplicated, while two distinct descriptors for
the same identity are ambiguous. A different version-zero nominal leaf can be
excluded using its common named prefix without interpreting its kind-specific
tail or generic context. A generic matching leaf or parent remains unresolved.
The recognized class-vtable flag establishes identity only; vtable contents and
virtual dispatch are not admitted.

Evidence retains the entry PC/raw relative pointer, every matching nominal PC,
flags and complete fixed descriptor prefix (44 bytes for class, 28 for struct or
enum), module PC/12-byte prefix, all identifier PCs/raw terminated bytes, selected
slice digest, slice offset/size and architecture. Existing image digests are
reused; admission does not hash or revalidate the source container.

The `binding` additionally retains all critical reads, including excluded leaf
names and every directory entry needed to establish uniqueness, together with
the complete bounded cached section mapping and selected-slice attributes.
`swift_abi_binding_matches(image, record)` checks those bytes and attributes
without hashing or repeating compiler/source verification. Changed excluded
leaves, new aliases, directory geometry, overlapping mappings or slice bounds
cannot reuse the binding. This is evidence custody checking, not authentication
of caller-invented receipts or proof of a new ABI capability. This layer uses no
cached function-entry map; callsite binding must separately establish function
and dispatch provenance.

## Independently inspected lowering tuples

`LOWERING_QUALIFICATIONS` is an immutable internal registry of frozen
`LoweringObservation` records. `qualification` may select an existing registry
ID; dictionaries or unknown IDs cannot certify themselves. With no ID, the same
registry is searched automatically. Admission requires the exact previously
recorded slice identity, symbol identity, callable kind, nominal parent identity,
argument/result type trees, non-generic ordinary-throws syntax, and bounded reads
matching retained instruction bytes. A copied registry ID cannot qualify a
different image or declaration. No caller-controlled register dictionary is
accepted.

These five initial tuples reuse the captured source/compile receipt and existing
objdump outputs in the owned `broad-swift-initial-v1` research corpus:

| Qualification ID | Compiler mode | Callable | Qualified storage |
| --- | --- | --- | --- |
| `owned-initial-v1-O-transform-int` | `-O` | free `broad_transform(Int) throws -> Int` | argument/result `x0`; ordinary error `x21` |
| `owned-initial-v1-Onone-transform-int` | `-Onone` | same free function | argument/result `x0`; ordinary error `x21` |
| `owned-initial-v1-O-struct0080` | `-O` | struct primary method `(Int32, Bool, Double) throws -> Int` | `w0`, `x1`, `d0`; indirect receiver `x20`; result `x0`; ordinary error `x21` |
| `owned-initial-v1-O-enum0180` | `-O` | enum primary method `(Int32, Bool, Double) throws -> Int` | `w0`, `x1`, `d0`; indirect receiver `x20`; result `x0`; ordinary error `x21` |
| `owned-initial-v1-O-class0249` | `-O` | class primary method `(Int32, Int, Int) throws -> Int` | `w0`, `x1`, `x2`; reference receiver `x20`; result `x0`; ordinary error `x21` |

The recorded toolchain is Apple Swift 6.4.2
`swiftlang-6.4.2.1.9 clang-2100.4.1.1`, language mode 6,
`arm64-apple-macosx14.0`, with library evolution enabled. Each record retains
source and slice digests from the prior receipt, capture locations, exact PCs,
and raw little-endian instructions independently inspected for argument,
receiver, result and error storage. The three primary records additionally
retain a caller's `x21` clear, direct call, and conditional test. Existing source,
manifest and compiler evidence were inspected; no recompilation, redisassembly,
rehashing, corpus pass, or repeated provenance verification was performed.

The local receipt `local-evidence/swift-broad/b4-v1-abi-observations.json` records
first admission of the three selected real primary methods and retained nominal
records. A bounded Mach-O section-directory read constructed the selected image
using the existing compiler-receipt digest. This receipt covers those three
observations only; reuse it while inputs and admission code are unchanged.
It predates the binding follow-up, so it is historical observation evidence and
does not claim fresh binding validation against later implementation changes.

## Remaining qualification work

This foundation does not meet a broad corpus acceptance target. Exact captured
fixtures are initial observations, not a universal allowlist endpoint. General
Swift stable-ABI rules require an explicitly selected profile assumption plus
bounded independent corroboration of actual error transport, argument/result
lowering and dispatch at the callsite. An arbitrary binary's compiler version
cannot be recovered from a mangled symbol or assumed from this corpus.

Built-in integer widths, Bool, Float/Double and Void can gain storage capabilities
only through reviewed source/toolchain observations and public ABI rules. The
initial records above cover only their listed tuples when no selected callsite
qualification is supplied. The generalized profile below supplies separate
rules and evidence for additional shapes. Existential, String-result, closure,
async, typed-throwing and other unqualified productions remain explicit gaps;
no register is guessed from an arbitrary nominal type name.

## Generalized selected stable-ABI research profile

`ABICallsiteQualification(profile_id, call_pc, caller_start, target_pc,
callsite_capability=None)` is a frozen work request for
`swift6-arm64-sync-untyped-stable-research-v2`. It is not a caller-issued
certificate. B4 independently requires the raw direct BL, exact function entry,
unique qualifying nlist symbol, canonical declaration identity, nominal parent
records, actual callee `x21` transport instructions or exact straight-line leaf
preservation effects, and result-storage
corroboration. An arbitrary dictionary cannot supply this authority.

The result explicitly reports `compiler_verified: false`, selected convention
preconditions, `error_state_proven: false`, and `call_return_proven: false`.
The profile assumes well-formed synchronous untyped Swift stable ARM64 calls;
it does not recover a compiler version from an arbitrary binary or prove
post-call values. Reference compiler/source facts describe the independently
inspected owned evidence, not verification of every input's toolchain.

`STABLE_STORAGE_CAPABILITIES` and `STABLE_LOWERING_OBSERVATIONS` are immutable
capability and retained-PC/raw-byte records. Built-in integer widths/sign,
Bool, Void, Float, Double, `Optional<Int>` and `(Int, Bool)` have explicit
storage contracts. FP instruction masks preserve direction and precision.
Owned resilient `BroadSmall`, `BroadLarge`, `BroadPayload`, `BroadTag`, and
`BroadReference` layouts require frozen captured-source lineage. Six exact
primary/second-compiler capture slices currently have that lineage; an arbitrary
same-named type cannot gain their capabilities.
Result categories preserve integer width/sign, FP register bank, multi-register
payload/tag or tuple fields, indirect result storage and known owned layout
size. Unsupported result-buffer aliases and unqualified shapes decline.
Argument storage explicitly preserves `inout` pointer locations, independent
integer/FP allocation, supported tuple fields, and qualified owned resilient
arguments. The location contract does not establish a register's current value
or prove initialization of an unused receiver.

Caller clear/test instruction PCs are optional geometry observations.
Direct propagation can legitimately have neither an explicit clear nor a test.
A clear's presence never proves it survives a branch or opaque call. The
independent caller-state/CFG validator must prove those facts; B4 does not seed
a fabricated zero state. This separation admits ABI storage for propagating
callers while preserving semantic uncertainty.

Concrete generic specialization additionally requires exact owned v2 lineage,
supported concrete `Int` bindings, reviewed specialization attributes, and an
entry-prefix check that every substituted formal GPR input is read/transferred
before its original location is clobbered or control transfers. Raw
`DroppedArgument` ordinals are retained, never translated into source parameter
indices or used to erase formal arguments. Hidden generic metadata/context
argument locations are not claimed. The independent validator must reproduce
this corroboration instead of trusting a profile ID.

Family labels distinguish free, struct, enum, static/type, extension, direct
final-class, and concrete generic specialization. Extension/final source
attributes have no unique mangling bit. Their classification therefore requires
the exact owned source/slice lineage plus the admitted actual direct target;
names alone cannot qualify these facts in another image. Virtual class,
protocol, closure, actor/async and typed-throws families retain their separate
challenge boundaries. A family label is not a dynamic dispatch proof.

The optional private B5 callsite capability is minted from an immutable
selected-image session. B4 checks custody and all request fields; supplying its
detached record dictionary is refused. Reuse avoids reparsing invariant
metadata. `work_steps` includes new capability-validation work and ABI reader
work, excluding capability construction already charged by the caller. Without
a capability, B4 includes its full B5 work. B5 has a separate 2,000,000-step
budget; the ABI reader retains its 32,768-byte bound. The parent charges session
construction once and enforces its aggregate work ledger. Session-bound
`swift_abi_binding_matches` needs the matching private capability; a serialized
record alone cannot recreate process-local custody.

## Scoped v2 observed breadth

The first scoped diagnostic examined 20 selected v2 callforms. Four specifically
authorized new replacement representatives and two former generic visibility
refusals on changed B5/ABI code followed. The first 20 successful observations
were not repeated. Captures were loaded through `load_owned_swift_image` using
existing v2 receipt custody/digests; no hashing, compilation, disassembly,
re-indexing or whole-corpus admission was run.

The saved observation union contains **15 ABI-pattern admissions across all
seven required families** and **12 distinct result-storage contracts**:

| Family | Saved admitted observations |
| --- | ---: |
| Free | 7 |
| Struct | 1 |
| Enum | 1 |
| Static/type | 2 |
| Extension | 1 |
| Direct final-class | 1 |
| Concrete generic specialization | 2 |

Contracts include Void, narrow/64-bit integer, Boolean, Float/Double, optional
payload/tag, tuple fields, an indirect resilient struct, an indirect enum tag,
and a class reference. Distinct widths/sign and known layout sizes remain
explicit. These are saved observations with their original implementation
boundaries, not a fresh current whole-corpus result. They establish neither
15 positives per family nor 250 semantic witnesses. Eight result-lowering
categories are supported by these concrete observations; the 23 source return
families and 80 emitted ABI-shape gate are not automatically qualified.

Ignored scoped receipts are `local-evidence/swift-broad/b4-v2-scoped-first.json`,
`b4-v2-replacements-first.json`, `b4-v2-generic-changed-visibility.json`, and
`b4-v2-observation-breadth.json` in that directory. They preserve individual
call/target PCs, storage evidence, private byte bindings and work accounting.
Reuse them within their stated boundaries. Generalized current-source review,
the authorized final qualification, and integration remain distinct gates.

## Public ABI references

The implementation was checked against public Swift source documentation:
[Calling convention summary](https://github.com/swiftlang/swift/blob/main/docs/ABI/CallingConventionSummary.rst),
[calling convention design](https://github.com/swiftlang/swift/blob/main/docs/ABI/CallingConvention.rst),
[metadata descriptors](https://github.com/swiftlang/swift/blob/main/include/swift/ABI/Metadata.h),
and [metadata flags and kinds](https://github.com/swiftlang/swift/blob/main/include/swift/ABI/MetadataValues.h).
The summary identifies ARM64 error-return and async-context register roles;
those roles are applicable only within a qualified convention. The metadata
headers define descriptor kind values, relative parent/name fields, genericity,
uniqueness and kind-specific flags. Private source or binary bytes were not
submitted to documentation tools.

## Second-compiler captured-source lineage

`OWNED_SOURCE_BY_SLICE` is an immutable internal mapping from the three primary
capture slices and three Swift 6.3.3 representative slices to their actual
captured source identities. Entries were taken from the existing v2 compile
receipts. The representative source copies the same generated common type
and selected function definitions; it has its own distinct source digest.
No caller-supplied digest dictionary or registration mechanism grants lineage.

Primary lowering references remain separate: `_V2_SLICES` contains only the
three primary reference images, and `_V2_SOURCE` identifies only their source.
`evidence.lowering.source_sha256`, `reference_slice_sha256`, and the reference
compiler fields retain that reference provenance. New `selected_source_sha256`
and `selected_slice_sha256` fields identify the actual selected capture.
`family_evidence.source_sha256` uses the actual selected source, including for
the representative compiler. An unregistered selected slice has no owned source
lineage; it cannot borrow the primary source identity.

Four previously unadmitted second-compiler callforms received their first scoped
ABI-pattern checks using receipt custody reuse:

| Capture mode/case | Family | Observed result contract |
| --- | --- | --- |
| `Onone / 0019` | Free | `(Int, Bool)` in `x0`, `w1` |
| `O / 0085` | Mutating struct | Resilient `BroadLarge` through `x8` |
| `O / 0081` | Mutating struct | Float in `s0` |
| `O / 0340` | Concrete generic specialization | Resilient enum tag through `x8` |

All four admitted the conditional stable ABI patterns and retained the second
capture's actual source identity. The private receipt is
`local-evidence/swift-broad/b4-second-6-3-3-four-first.json`. These four scoped
observations do not establish cross-version corpus acceptance or semantic
witness eligibility. No primary check, hash, compiler, version command,
disassembler, indexer or whole-corpus pass was repeated.

## Repair 2: exact leaf preservation

A throwing Swift signature can compile to a leaf implementation that never
changes the incoming error register. Requiring an object-copy instruction in
that body would reject a valid storage convention. The ABI corroborator now has
two explicit modes: `distinct_nonzero_gpr_copy`, retaining the previous bounded
instruction-presence rule, and `preserved_x21_leaf`.

The leaf mode requires at most 256 words with exactly one final `RET x30`, no
other control transfer or opaque call, and no unknown instruction effect. GPR
destination allocation is checked before operand interpretation, and other
instructions use exact checked descriptors. A load, paired load, arithmetic
write, conversion into GPR x21, or writeback affecting x21 refuses preservation.
Even a self-write to x21 is conservatively refused. SIMD register 21 is a
separate bank; storing x21 does not change it. No outlined-helper instruction
pooling or result-buffer alias inference is introduced.

`callee_error_observation` retains the mode, body entry, word count, final-return
PC for a leaf, and the conditional preservation scope. Leaf preservation says
only that the incoming x21 value is unchanged **if this straight-line body
returns normally**. It does not prove that the input is zero, that a value is an
error object, that execution reaches the return, or that a call returns.
Existing `error_state_proven`, `call_return_proven`, and error-object type flags
remain false. The independent validator reproduces the effect check.

Repair 2 was motivated by receipt-only inspection of the incomplete first final
qualification. That receipt already contained 257 ABI-admitted `Osize` rows;
its zero eligible-witness count therefore has substantial downstream causes.
The new leaf mode addresses a specific ABI refusal rather than relaxing unknown
critical value or custody requirements. Only new authored synthetic regressions
were executed for this repair; real compiler units and the final corpus were
not reevaluated.
