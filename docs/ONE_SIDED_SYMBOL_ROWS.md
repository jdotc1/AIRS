# Singleton one-sided symbol rows

`ComparisonReport.validateOneSidedSymbolRows(baselineData:currentData:)` is an
explicit native validation API for declared added/removed symbol rows. It composes
duplicate-symbol, body-pair, unique-symbol, exact-offset, observation-label,
selected-source, accounting and manual-pair checks. It does not activate matching
or change native workflows.

## Declared source groups

Usable symbol names retain exact UTF-8 grouping after validated manual pins.
Duplicate groups retain the composed ambiguous-group rules. An established
one-baseline/one-current symbol group must retain both selected singleton IDs;
it cannot be represented as a one-sided added or removed row.

A singleton group with only a baseline finding requires that exact baseline ID,
no current endpoint and a removed label. A singleton current-only group requires
that exact current ID, no baseline endpoint and an added label. These labels mean
no accepted match in the recorded comparison phase, not regression or fix.

## Body selection and unavailable metadata

The shared internal body-candidate projection reconstructs the existing host
snapshot from admitted source reports: validated manual pins precede established
symbol pairs; all remaining fingerprint blockers count; selected bucket endpoints
must be unique and standalone. Imported rows do not determine consumption, and
omitted body rows cannot make consumed symbol endpoints available again.

- Explicit false preserves the pre-body singleton groups.
- Explicit true consumes eligible body candidates when source architecture and
  exact CPU subtype permit the body phase.
- Missing status stays unavailable. If an eligible body pair could consume a
  declared singleton symbol endpoint, validation refuses that row. When the body
  option cannot affect that endpoint, its one-sided presence can still be checked.

Model/configuration differences do not prevent body selection; they govern the
resulting pair's observation label through composed checks. Imported fingerprints
remain structurally admitted annotations, never authenticated byte evidence.

## Boundaries

The shared projection is internal and requires already admitted sources and
validated manual pins. Callers retain authority for body-phase status, cross-image
identity and architecture/subtype conditions. The body-pair validator uses the
same projection without changing its accepted selection policy.

Omitted groups remain allowed. This API does not establish comparison completeness,
verify unmatched/future matching bases or display prose, authenticate binaries,
prove source-function identity, or widen engine semantics. Prior source and GUI
results remain distinct from changed-boundary qualification.


## Bounded qualification

The real AIRSApp target built successfully. Eighteen new focused native tests and
fourteen directly affected body-pair tests passed with zero failures after the
shared projection refactor. Independent code and scope review found no actionable
defect. Unchanged source/accounting/manual/symbol/offset/codec, Python, GUI and
release evidence is reused within its original scope. Detailed logs remain local;
no packaging, installation, GUI or release qualification is claimed.
