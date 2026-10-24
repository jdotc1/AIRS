# Review unresolved reasons in saved reports

This workflow connects coverage inventory to individual saved findings. Use Python
3.11 or newer from the AIRS checkout. The commands below use the repository's
`examples/mixed.audit.json`; they read saved JSON only. They do not re-audit an
image, execute it, recompute provenance hashes or establish that current bytes
match the saved identity. These CLI additions are source development after build
12; the installed build 12 is not claimed to contain them.

## 1. Inventory reasons before narrowing the review

```sh
python3 -I airs_cli.py coverage --report examples/mixed.audit.json --minimum-count 1 --sort reason --limit 4 --output triage-coverage.json
```

For this sample the full counts remain nine functions and four unresolved
functions. Four reason rows survive the inclusive threshold of one; the limit
omits none. The row `unsupported_control_flow` has count one.

For your own reports, repeat `--report` to combine saved inputs. To focus on
recurring reasons use `--minimum-count 2` or another positive threshold. This
sample has no recurring unresolved reason, so a threshold of two would return
no reason detail. That means the detail filter selected nothing; it does not
mean unresolved work disappeared or the image passed.

Use `--sort count` (the default) to prioritize by recorded frequency or
`--sort reason` for literal code ordering. `--limit` caps detail only. Inspect
`reason_frequency_selection` and `reason_limit` alongside the full `summary`;
reason-code selection, if supplied, occurs before frequency selection. The
inventory retains every supplied report record, including duplicate/conflict
accounting. Duplicate reports count once; conflicting variants count separately.
Reason counts can overlap and describe supplied reports, not real-world prevalence.

## 2. Follow a chosen reason to saved functions

```sh
python3 -I airs_cli.py summary --report examples/mixed.audit.json --verdict unresolved --reason unsupported_control_flow --name-contains conditional --sort verdict --limit 1 --output triage-summary.json
```

The sample selects `_conditional_flow`. The selected detail retains its original
finding ID, function address and saved evidence. The full counts still report
nine functions and four unresolved functions. Look up that finding ID in the
original report to review the complete evidence and limitations.

Repeat `--reason` for alternative reason codes and `--verdict` for alternative
verdicts. Reasons combine with OR, verdicts combine with OR, and the two selector
families combine with AND. The optional name query is another AND stage: a
literal, case-sensitive substring without Unicode normalization. Unnamed
functions do not match. Omit `--name-contains` to inspect every function for a
reason. Text output may clip examples; JSON preserves details up to your explicit
limit. Stage metadata distinguishes verdict/reason selection, name selection and
final limiting, so their selected counts can differ.

Coverage inventories describe unresolved reasons. Use summary directly to inspect
inconsistencies, for example with `--verdict inconsistency`; absence from the
unresolved inventory is not evidence that an inconsistency is absent.

## 3. Retain outputs and decide what evidence is missing

Use fresh output filenames and `--output` to retain each completed result through
the protected writer. Shell redirection does not provide its source-overwrite
protection. The input to `summary --report` must remain the original audit report,
not the coverage or summary projection. Selected CLI projections are not new
complete-inventory native import formats.

An unresolved reason is a review starting point, not permission to widen the
engine's support. Before proposing a semantic extension, identify a specific
owned input and an independently derived recovery expectation. Require a positive
case and a refusal/unknown boundary with independent semantic review. Filtering
an unresolved finding away does not make it supported. Agreement applies only
to recorded checked PCs and scope, never a whole-image pass.

## Executable sample and evidence scope

The companion script runs the two new composed CLI commands against saved sample
JSON, writes outputs/logs and a receipt into a new directory, and checks the
full denominators, chosen reason and original finding ID:

```sh
python3 scripts/saved-report-triage-example.py --output-dir local-evidence/triage-example
```

An existing destination is refused. Preserve its receipt and reuse it; creating a
fresh directory does not authorize repeating an unchanged accepted check. On a
failed command, logs are retained and the script stops without retrying.

The first bounded run passed both composed commands: full function count nine,
full unresolved count four, four inventory reason rows, one selected original
finding. Accepted component tests, byte bounds, terminal safety, duplicate/conflict
handling and protected-writer receipts were reused. This new composition result
is not a repeated full suite, native acceptance, image audit, signing or release
qualification. No installed app, settings or stores were accessed.

See [command reference](SAVED_REPORT_COMMAND_EXAMPLES.md),
[function-name matching](SUMMARY_FUNCTION_NAME_FILTER.md),
[minimum count](COVERAGE_MINIMUM_COUNT.md), and
[development roadmap](ROADMAP.md) for individual contracts and remaining gates.
