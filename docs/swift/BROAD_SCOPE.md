# Broad Swift research contract

Status: **qualified bounded research profile** at engine54284c8. All26 measured acceptance gates and both independent source reviews passed. The actual counts and remaining capability limits are in [BROAD_QUALIFICATION.md](BROAD_QUALIFICATION.md). Local packaging does not establish a release or cross-device delivery.

## Model boundary

Broad analysis is explicitly selected by `--swift-profile broad-v1`. Its identities
are `swift-broad-error-flow-v1`, `swift-outcome-witness-v2`, and
`swift-outcome-validation-v2`. These identify a separate research pipeline, not a
new interpretation of saved historical reports. The historical free-function
v37/v45 and method v38/v46 profiles, witness v1, and validation v1 retain their
original scope. Broad selection must include witnesses, regions, entry checks,
and structured presentation; it cannot be combined with `--include-swift-methods`.

The broad coordinator operates offline on parser-admitted immutable Mach-O bytes
for ordinary ARM64. It composes bounded raw-symbol declaration parsing, exact
callsite admission, qualified ABI evidence, a caller-local CFG, typed scalar and
stack value tracking, candidate construction, and a separately implemented byte
validator. Declaration recognition is distinct from ABI admission, dispatch
resolution, candidate construction, independent validation, and presentation.
No one stage confers the authority of a later stage.

Broad witness identity explicitly retains the container and selected-slice
digests, UUID (including explicit absence), architecture/full subtype, preferred
image base, selected FAT-directory index, slice count, slice offset/size, and
caller/callee boundaries. Parser custody binds those coordinates to the exact
immutable bytes and metadata. Historical narrow report serializers retain their
existing wire shape.

The candidate producer keeps `eligible: false`. Only the independent validator
may return `eligible_structural_only` after its bounded replay succeeds. Serialized
reports contain recorded outcomes; rendering them does not reread or authenticate
the inspected binary. Imported JSON cannot grant itself ABI qualification or
source custody. The validator's current implementation remains under review and
qualification; its existence is not proof that corpus gates have passed.

## Intended breadth and measured boundaries

The owned source contract requires at least 420 declarations and 340 nominal
methods: 80 free, 100 struct, 55 enum, 60 class, 45 static/extension, 35 generic,
25 protocol-related, and 20 actor/async cases. It includes typed throws, closures,
and rethrows as source challenges. The revised source records 23 result families,
12 parameter forms, and 12 caller source geometries. A source label or signature
combination does not establish a distinct emitted ABI shape, an observed geometry,
or an eligible witness.

The final contract also requires at least 80 emitted ABI shapes, 1,500 confirmed
physical owned-target call observations, 250 independently byte-validated positive
witnesses spanning seven callable families with at least 15 positives each, ten
positive geometries, twelve observed challenge patterns, eight qualified
lowerings, 300 negatives with zero false eligibility, and 100 deterministic
stratified repeat comparisons. Two independent whole-branch adversarial review
rounds and a complete portable ZIP are mandatory. See the ledger for evidence
and pending items rather than inferring achievement from this target list.

Positive geometries are normalized selected post-call/outcome graphs checked by
the independent validator; caller prefixes and incidental data/frame operations
do not create diversity. The twelve challenge requirements have individual
source-intent and emitted-evidence dispositions. A collapsed or unproven required
form remains incomplete, regardless of unrelated feature counts. Each positive
callable family also requires a negative control within the existing 300-case
budget. Source category minima and nonduplicate source feature vectors are
reconciled separately from emitted ABI and outcome evidence.

## Research assumptions and refusals

The initial ABI capability is the explicitly named
`swift6-arm64-sync-untyped-research-v1`. Exact retained observations and reviewed
rules determine what it admits. An x21 convention is usable only after applicable
qualification; mangled spelling, demangler output, a source declaration, or a
compiler-family guess cannot establish it. An arbitrary binary's compiler version
is not recovered from its symbol name. Nominal metadata admission establishes
identity, not dispatch or a class vtable target.

Async, typed throws, protocol/witness dispatch, virtual dispatch, closures,
generics/specializations, aggregates, optionals, and indirect calls must retain
their actual supported/unresolved/refused state at every layer. Parsing a case
does not qualify its lowering. A constant-target indirect-call proof does not
resolve arbitrary runtime dispatch. Tail calls do not supply post-call evidence.
Unknown instructions, conflicting entries, ambiguous mappings, unsupported
lowerings, changed custody, and exhausted budgets must not become success.

All admitted outcomes are caller-local structural facts conditional on the named
research ABI assumptions and inspected entry. They do not prove execution,
runtime reachability, call return, exclusive runtime entry, source-level `try`,
catch/handler semantics, source expressions, or reconstructed source code. No
clinical, installed-app, release, or production acceptance follows from them.

Selected stable-profile success/error roles are explicitly conditional on its
calling-convention preconditions, including the required incoming x21 state.
The incoming state remains `unproven_profile_precondition`; a visible lexical
clear does not establish dominance. A known contradictory incoming state blocks
the witness. Raw post-call register provenance is kept separate from that
conditional semantic role. Explicit unknown return values may accompany checked
structural geometry; they do not become exact returned-value claims.

BRK has an explicit external-exception transfer with no ordinary local
fallthrough. Its raw instruction is checked, while external handling and
resumption remain unmodeled and unproved. An exception observation is distinct
from a return observation and does not prove language-level nonreturn behavior.

## Resource ceilings

The broad CLI image scan admits at most 8 MiB, 8,192 function entries, 4,096 words
per function, 262,144 total scanned words, 256 retained calls per function, and
4,096 retained call records. Its public JSON ceiling is 16 MiB including the
indented envelope; the terminal view is bounded to 1 MiB and 256 displayed rows.
Omissions clear the applicable processing-completeness fields.

A witness defaults to 512 instructions, 512 blocks, 2,048 edges, depth 32,
64 state entries, 512 provenance nodes, 65,536 charged local work steps,
256 KiB of encoded candidate data, and a 16-instruction post-call window. Python
configuration has explicit hard ceilings; increasing a local limit cannot erase
aggregate accounting or authorize an unsupported fact.

B5 parses its immutable metadata session once per image under a 2,000,000-step
limit. The independent validator builds a separate raw-directory ledger under
262,144 steps, without consuming B5 or producer facts. Their initial work is
charged once and each witness still independently checks its selected bytes,
symbol/context/ABI facts, CFG and values. These are invocation-owned ledgers;
serialized records and copied objects do not convey custody, and no global
image cache or repeated source hash is needed.

The qualification harness separately enforces a 512,000,000-step ledger,
bounded input parsing, 96 MiB of retained records, and 128 MiB of streamed local
JSON. Its larger evidence envelope is distinct from a CLI report. These are
algorithmic, retained-data and encoded-output bounds, not a whole-process RSS
claim. See [BROAD_QUALIFICATION_HARNESS.md](BROAD_QUALIFICATION_HARNESS.md).

The final pass separately measures elapsed time and Python process-lifetime
high-water RSS, with explicit platform units and child-process exclusions.
Those observations do not impose a wall-time or RSS ceiling and do not turn the
algorithmic limits into a process-memory guarantee.

## Completeness and delivery

Reports must expose incomplete scans, omitted calls, unresolved reasons, and
resource limits. `word_scan_complete`, `call_details_complete`, and
`outcome_witnesses_complete` describe different coverage boundaries. A bounded
text view may omit additional rows while JSON retains the recorded detail.

The portable handback must contain the implementation, owned fixture sources,
schemas, tests, contracts, review dispositions, and qualification evidence needed
to assess its stated scope. Commands and navigation must be relative to the
package root. Private machine paths and raw private logs are excluded. Packaging
does not change a pending gate to complete; the delivered ledger must say exactly
which gates passed, remain incomplete, or are concretely blocked.
