# Porting Swift structural outcome witnesses to MacScope

This contract concerns the advanced Swift AIRS engine only. AIRS acceptance does
not establish MacScope compatibility. Do not modify MacScope as part of this
assignment. The Function Fact Sheet and Bounded Call Graph projects are separate.

## Required adapters

Supply an immutable admitted ARM64 Mach-O slice with architecture/subtype,
UUID, selected-slice and container identities, slice offset/size and preferred
base; file-backed executable section mapping; exact function starts and ends;
all symbol aliases and visibility/alternate-entry metadata. Preserve VM,
image-relative, slice-relative and container-relative distinctions.

The decoder must return raw 32-bit word, PC, instruction kind, operand registers,
width, signed branch displacement, immediate and addressing mode. Unknown words
must remain unknown. Required forms are AIRS's bounded direct BL/B, CBZ/CBNZ,
CMP-zero/B.cond, MOV/wide-move, scalar result arithmetic and qualified return-tail
forms. Do not equate an accepted instruction descriptor with runtime execution.

The declaration adapter must reproduce the complete bounded mangling grammar and
non-generic struct-context admission; include exact descriptor raw fields and
source addresses. Generic, async, typed-throws, class and witness dispatch stay
unsupported. Transfer owned source fixtures and disassembly observations; compile
and independently qualify each supported compiler/optimization combination.

## Pure interfaces and negotiation

Port `parse_throwing_declaration(symbol, allow_methods=False)`,
`build_outcome_witness(image, function, call, limits=..., model_profile=...)` and
`validate_outcome_witness(image, function, witness, limits=...)`. Builder evidence
cannot validate itself. The validator rereads admitted bytes, recomputes mapping,
call/test targets, polarity, intervals and bounded value/choice correlation.

Negotiate exact profiles: legacy edge v37/choice v45 or method edge v38/choice
v46 plus declaration v1; witness v1 and validation v1 are supplemental. Preserve
historical version meanings. Unknown profiles decline interpretation.

Preserve statuses eligible_structural_only, unresolved, blocked and declined,
reason codes, per-fact results, detail completeness and accounting. All runtime,
exclusive-entry, source-reconstruction, catch-type and call-return proofs remain
absent. No speculative indirect edges or global dominance claims are permitted.

## Budgets and acceptance risks

Transfer enforced limits and charging semantics with the model, including input,
function/caller scan, declaration/metadata, graph depth/nodes/edges, instruction
records, references, diagnostics, validation steps and serialized bytes. Resource
exhaustion cannot yield eligibility. Cache only validator-owned admitted-image
caller ledgers within a single invocation; never trust imported producer ledgers.

Required acceptance includes the 30-case adversarial matrix, coordinated word and
identity mutations, swapped call/arm attachments, generic enclosing contexts,
shared tails, truncation and exact legacy default equivalence. No general Swift
compiler coverage follows from synthetic success.

AIRS-specific dependencies are its Mach-O admission and function boundary model,
Python instruction descriptors, bounded scan contracts, protected atomic exports
and JSON/text serializers. A native adapter must independently establish these
boundaries. No reusable private MacScope framework or GUI URL scheme is assumed.
