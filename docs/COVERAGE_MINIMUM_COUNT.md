# Minimum count for saved coverage reason detail

`coverage --minimum-count N` keeps reason detail rows whose recorded aggregate
count is at least N. N must be a positive integer; invalid numeric values fail
with `invalid_coverage_minimum_count` before report stat/read operations. Noninteger
CLI arguments are rejected by argument parsing. There is no arbitrary upper bound:
a threshold above every recorded count returns no reason details.

```sh
python3 -I airs_cli.py coverage --report examples/mixed.audit.json --minimum-count 2 --sort reason --limit 1 --format text
```

The pipeline aggregates/adopts reason-code selection using the existing inventory
builder, selects by inclusive count, orders reason detail, then applies a limit.
The `select_coverage_frequency` helper expects unlimited inventory detail at that
stage and returns detached data. It preserves existing row order. Without the
option the CLI skips the projection and preserves the previous output shape.

JSON `reason_frequency_selection` records the threshold (`minimum_count`) and
immediate `input_count`, `selected_count` and `omitted_count` of reason rows.
These are detail-row counts, not unresolved finding totals. Reason-code selection
metadata continues to describe code matching before this stage: a matched code may
subsequently be omitted by frequency. Limit metadata describes the filtered input.
Text explicitly discloses frequency selection without filtering denominators.

All full summary counts, models, report records, examples on retained rows,
duplicate/conflict context, unmatched code requests and limitations remain intact.
Duplicate handling is inherited from aggregation: supplying the same report twice
does not double its reason counts. Conflicting variants retain the existing
separate accounting. Counts may overlap for the same unresolved finding. They
represent supplied saved reports only, never real-world prevalence. No rows become
supported or resolved through omission. No saved identity is reverified.

The added projection metadata is CLI-only; it is not a new complete-inventory
native import format. The existing native admission contract is unchanged. No
engine, UI, installed app, settings or store behavior changes.

## Focused evidence

Six new methods in `test_coverage_minimum_count.py` passed on Python 3.13.16:
CLI composition, inclusive count boundary and detached context, absent/large
thresholds, invalid input rejection before I/O, explicit text omissions and full
denominators, and duplicate-input frequency accounting. One literal isolated
bootstrap command above passed, retaining zero reason rows while preserving the
nine-function source count and reporting four omitted reason rows.

Accepted reason selection/order/limit, full aggregation, protected writer,
terminal safety and engine/native/runtime receipts were reused. No full suite,
corpus, native build, GUI acceptance, packaging or installation was repeated.
