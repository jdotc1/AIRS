# Coverage text escaped-value preflight

Coverage text previously fed saved values to JSONEncoder.iterencode, then checked
the emitted chunk against its byte budget. A string is escaped into one complete
chunk before the encoder yields it. Control characters can expand sixfold and
non-BMP characters twelvefold, so refusal could follow a large allocation even
when the caller requested a small output limit.

Coverage now reuses the existing summary renderer's escaped-size preflight with
the remaining output budget. Oversized nested strings and dictionary keys are
refused before JSON encoding. The existing coverage-specific size error remains.
ASCII JSON escaping, deterministic ordering, full counts, report/conflict records,
selection metadata, example limits and final newline retain their meanings.
No semantic support, report admission or source hashing changes. This bounds the
escaped value allocation against the output budget; it is not a total-process
memory cap, because the source inventory and output buffers coexist.

Fresh bounded evidence:

- A new synthetic regression failed on the old implementation when a saved string
  reached the encoder before its expansion was budgeted.
- Three new methods cover that regression, oversized dictionary keys, nested
  control/DEL/non-BMP/surrogate escaping and exact output-byte boundaries.
- Those three methods and five affected existing coverage-text methods passed.
  One new test initially used a nonexistent exception.message attribute; it was
  corrected to str(exception), and only that method was rerun. The seven already
  passing methods were reused.

Independent read-only review found no actionable issue for the admitted inventory
schema and confirmed output compatibility and the bounded-allocation claim.

Tests use tiny synthetic inventory objects. They do not read or re-audit real
images, recompute hashes, or replay accepted CLI/GUI/distribution workflows.
Existing summary-helper checks, registry/model results and native build receipts
are reused. Native source is unchanged, so no native build or launch is added.
Installed app, settings and stores were not accessed; no packaging or release.
