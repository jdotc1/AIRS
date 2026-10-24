# Literal function-name selection for saved summaries

Use `summary --name-contains TEXT` to select finding details whose saved function
name contains the supplied literal substring. Matching is case-sensitive and
performs no Unicode normalization: composed and decomposed names remain distinct.
Missing or null names do not match. A nonblank query retains its literal spaces.

```sh
python3 -I airs_cli.py summary --report examples/mixed.audit.json --name-contains frame --sort verdict --limit 2 --format text
```

The query must be nonblank valid UTF-8 text, at most 256 encoded bytes, without
ASCII C0 controls or DEL. Invalid queries fail with `invalid_summary_name` before
saved-report I/O. There is no regular expression or glob interpretation.

The pipeline admits and summarizes the saved report, applies optional verdict and
reason selection, applies name selection, orders detail, then limits it. The pure
`select_summary_names` helper returns detached data. Its input must be unlimited
summary detail; the CLI supplies that stage. Without the option, the existing CLI
path and output shape are retained.

`finding_name_selection` records `contains`, `case_sensitive: true`,
`normalization: "none"`, and the immediate input, selected and omitted row counts.
Earlier `finding_selection` metadata describes the earlier verdict/reason stage;
its count can exceed the subsequent name-selected count. Limit metadata describes
the name-selected input. Full source denominators, verdict/reason counts, exact
saved identity, model, configuration, issues and caveats are unchanged, even when
no name matches. Text discloses selection and uses existing terminal escaping and
byte bounds. Output retains the protected writer's input-overwrite rejection.

This projection neither audits an image nor verifies saved identity against current
bytes. Selected agreements do not establish a whole-image pass. No native importer,
engine, GUI, installed app, settings or store behavior changes.

## Focused evidence

Eight new methods in `test_summary_name_filter.py` passed: composed CLI selection,
literal Unicode/case/missing names, detached full context, absent-option shape,
invalid-query rejection before I/O, terminal-safe text, no-match counts and
input-overwrite protection. After refining the text row label and its assertion,
only that changed method was rerun and passed; the other seven results were reused.
One literal isolated-bootstrap invocation of the command above passed. It retained
two of three name-selected details and reported the original nine-function count.
Existing summary, coverage, engine, native and runtime results were reused; no full
suite, image corpus, packaging or installed acceptance was repeated.
