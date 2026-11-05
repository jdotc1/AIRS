> Historical component milestone. Final composed qualification and current limits are recorded in docs/swift/BROAD_QUALIFICATION.md; earlier corpus counts are not additive.

# Broad Swift structural region candidates

The v2 producer remains candidate-only: every result has `eligible: false` and
requires independent byte, ABI, value and region validation. None of the region
labels establish runtime execution, dominance, termination or source structure.

The post-call window accepts a qualified 64-bit x21 error origin, exact register
copies and modeled stack spills/reloads, an X CBZ/CBNZ, or `CMP Xn,#0` followed
immediately by EQ/NE. The latter records `test_kind: cmp_zero_bcond`, the
comparison PC/word and branch condition. Other comparisons, narrowing, intervening
instructions after CMP, unsupported effects and unqualified stack addresses
remain unresolved. Direct unconditional hops follow exact branch targets inside
the admitted function; a repeated PC is an explicit `post_call_cycle` refusal.

Stack identity starts with an empty post-call stack and the entry-relative SP
offset recovered from an exact linear prefix. Prefix branches and unsupported
effects discard frame qualification. Address materialization may discard a
register's prior frame alias while preserving SP. No previous stack content or
pre-call error seed survives merely because a call returned structurally.

For each accepted error test, bounded graph traversal computes the instruction
PC sets reachable from each successor, following the CFG's call-continuation
candidates. `regions.partition` contains sorted `success_only_pcs`,
`error_only_pcs`, `shared_pcs` and `unreachable_pcs`. The last set means unreachable
from these two successor entries, including the pre-test prefix; it does not mean
unreachable from function entry. Every lexical return has a corresponding
`success`, `error`, `shared` or `unreachable` tail label. Shared epilogues,
multiple return tails, additional branches and loops therefore retain structural
facts without inventing one outcome for a shared return.

The unchanged model limits still bound retained words, graph edges, the post-call
window, value provenance, work and encoded output. Limit exhaustion leaves an
incomplete candidate. These additions do not broaden historical legacy models.

Synthetic tests cover EQ/NE polarity, adjacent flag use, exact hops, cycle
refusal, stack aliases, shared tails and multiple returns. Compiler nm/objdump
files are source evidence for designing these cases, not compiler qualification
or independently eligible corpus counts.

## Local breakpoint exception transfers

The structural CFG describes exact BRK encodings as `exception_transfer` edges
with a null target. The `exception_transfers` list retains each instruction's
raw PC, word, slice/container offsets and `kind: brk`, together with
`exception: breakpoint` and `resume_proven: false`. Such a transfer has no normal
fallthrough edge. Any following lexical word starts a separate block and still
must be classified, including otherwise disconnected code after the BRK.

`external_exception_handling_unmodeled: true` and
`exception_resume_proven: false` state the boundary explicitly. An external
exception handler might later resume execution; local bytes establish neither
resumption nor non-resumption. A complete local structural graph containing a
BRK therefore establishes no runtime termination or never-return property.
Unknown instructions after a BRK and resource exhaustion continue to prevent
structural completeness. Exception transfers consume ordinary edge, block and
work budgets.
