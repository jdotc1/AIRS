# Literal reason-code ordering for saved coverage

`coverage --sort reason` orders unresolved-reason detail by literal reason code.
This makes codes easier to locate and align across supplied saved inventories.
`--sort count` is the default: descending count, then literal reason code for ties.
Omitting the flag preserves the accepted default JSON shape and terminal output.

```sh
python3 -I airs_cli.py coverage --report examples/mixed.audit.json --sort reason --limit 2 --format text
```

The pipeline is saved-report admission and aggregation, optional literal reason
selection, optional reason-code ordering, then optional reason-row limiting. Thus
`--sort reason --limit 2` returns the first two selected codes alphabetically, not
the two highest counts. Both JSON and text use the requested order. Text's existing
32-row and three-example caps remain additional presentation bounds.

Explicit reason-code ordering adds `reason_order: "reason"`; text discloses it as
`Reason order`. All summary denominators, report records, model/configuration
context, conflicts, duplicate markers, selected/unmatched codes, reason counts,
examples and limitations retain their meanings. Only row order changes. The helper
returns detached nested data and expects a complete selected count-ranked inventory,
not an already limited or reordered projection. Default count mode leaves that
canonical input shape and order intact.

Reason frequency in supplied reports is not representative prevalence or automatic
permission to expand engine support. Alphabetical ordering does not imply cause,
severity or priority. No image is read or re-audited, no target code executes, and
no provenance hash is recomputed. The unchanged protected writer remains in use.

Like selected/limited inventories, reason-ordered JSON is a CLI projection. The
unchanged native coverage importer rejects additional projection fields. Generate
native-importable complete inventories without `--reason`, `--limit` or the
nondefault `--sort reason`; explicit `--sort count` retains the default contract.

## Focused evidence

Seven new Python methods passed: JSON/text CLI order before limiting; literal order,
full context and nested detachment; unchanged default count shape/rank; empty/tied
reason rows; invalid ordering rejected before report I/O; explicit count text order;
and composition with unmatched selection and zero limit. One literal isolated-
bootstrap CLI invocation with reason ordering, limit 2 and text output passed.

Accepted reason-limit, aggregation, protected-writer, engine, native and runtime
results were reused. No full suite, GUI workflow, corpus, signing, packaging,
installation or release work occurred. The installed app, settings and stores were
not operated or changed. This is a source-only increment after build 12.
