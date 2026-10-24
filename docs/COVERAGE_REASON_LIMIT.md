# Bounded reason detail for saved-report coverage

`coverage --limit N` retains the first N ranked reason rows after optional literal
`--reason` selection and optional `--sort reason` ordering. The default ranking
remains descending count, then literal reason code for ties. Nondefault reason
ordering happens before limiting; see COVERAGE_REASON_ORDERING.md. N is an integer from 0 through 200000; invalid numeric bounds are
rejected before any report file I/O. Omitting the flag preserves the existing JSON
shape and terminal presentation without adding limit metadata or an extra projection.

```sh
python3 -I airs_cli.py coverage --report examples/mixed.audit.json --limit 2 --format text
python3 -I airs_cli.py coverage --report report.audit.json --reason unsupported_instruction --limit 0
```

The output adds `reason_limit` with `maximum`, `returned_count`, `omitted_count`
and `selected_count`. The selected count is the number of reason rows before the
limit, after reason selection; it is not a function count. A zero limit hides reason
detail but preserves all source counts and report records. An unmatched reason
selector remains explicit even if no detail rows are returned.

Full summary denominators, models, duplicate/conflict records, limitations and
reason-selection requested/matched/unmatched metadata remain unchanged. Reasons
can overlap within one unresolved function. Omitted detail never becomes supported,
resolved, or a whole-image pass. The helper detaches nested output and does not mutate
its input. It accepts a complete selected inventory, not an already limited projection.

Text output exposes limit metadata separately from full denominators. Its existing
32-reason-row and three-example-per-reason caps still apply after the explicit limit.
The existing `Reason rows omitted` line describes only the text renderer's additional
cap; `reason_limit.omitted_count` describes the explicit CLI limit. These distinct
omissions must not be conflated. JSON keeps every returned reason's existing bounded
example list; no new sampling or evidence inference is introduced.

This is a CLI presentation projection. The native coverage importer requires the
complete inventory contract and rejects additional selection/limit fields. Use
`coverage` without `--reason`, `--limit` or `--sort reason` to generate a native-importable inventory.
The native importer is unchanged; truncated inventories must not masquerade as full
coverage. Saved reports are read as data; no Mach-O is opened, executed or re-audited.
The existing protected output writer still rejects overwriting any supplied report.

## Focused validation

Seven new Python methods passed for CLI admission/full counts, detached ranked
projection, zero/default/upper/invalid limits, pre-I/O rejection, terminal omission
metadata, selector composition in JSON/text, and source-overwrite protection. The
last method's portable temporary-directory setup received its own final focused pass;
the other six results were reused. One literal isolated-bootstrap CLI invocation
passed with the saved example, limit 2 and text output. No engine, native, vendor,
runtime, full-suite, GUI or corpus checks were repeated. Existing coverage aggregation,
selection, protected-writer and engine receipts retain their original scope.

No binary was packaged, signed, installed or released. The installed app, settings
and stores were not operated or modified by this source increment.
