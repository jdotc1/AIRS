# Saved-report navigator export

`airs.facts_export` transforms a saved AIRS `broad-imports-v1` report with model
`swift-broad-error-flow-imports-v1` into AIRS Navigator Results v1 (`.airsnav`)
files for MacScope. It reads no selected binary, performs no new analysis, and
never executes input code. This exporter is AIRS code under the repository
licence. The repository carries no copy of the external navigator-engine contract.

```sh
PYTHONPATH=src python3 -B -m airs.facts_export report.json output --tool-version 1.0 --max-facts 4000
```

The output directory must not exist. There is no overwrite option. The exporter
prepares and checks all parts before writing, then writes `part-0001.airsnav`,
`part-0002.airsnav`, and so on, plus `manifest.json`, into a sibling staging
directory. It fsyncs every file and the staging directory and installs it with
one directory rename. A failure before that rename removes staging and leaves
the destination absent. Existing destinations are preserved. This is a local
filesystem transaction; it does not claim a concurrent-writer lock or parent
directory crash durability.

Exit status is 0 for a completed export operation (including a producer refusal
file), 2 for a named input refusal or I/O error, and 3 for `nothing_to_export`.
Diagnostics contain reason names rather than input text. A producer refusal is
valid transport data but causes the consumer to refuse import.

## Envelope and identity

Each part has exactly `kind: "airs.navigator_results"`, `formatVersion: 1`,
`identity`, `run`, and `results`. Identity contains the container and selected
slice SHA-256 strings, integer slice offset and size, CPU type 16777228, the raw
signed Int32 CPU subtype, lowercase canonical UUID or null, and canonical
UInt64 preferred-base address. Offset and size must fit Int64, size must be
positive, and their sum must fit Int64. Non-arm64 reports refuse. CPU subtype
bits are retained without masking or reinterpretation.

`run` contains `producerName: "AIRS"`, the supplied `producerVersion`,
`contractVersion: 1`, `completed`, `toolchain`, and exact `resultCount`,
`factCount`, `frontierCount`, and `refusalCount`. The version is nonempty and
at most 128 UTF-8 bytes. All fact and frontier toolchains equal
`airs-undetected/1`; AIRS does not implement a `toolchain-key/1` detector.

Transport objects have no arbitrary metadata, paths, timestamps, or filenames.
Numbers use Int64 integer syntax; floats and booleans used as integers refuse.
Keys are ASCII identifiers. Strings reject C0, DEL, C1, U+061C, U+200E/F,
U+202A–202E, and U+2066–2069. Limits count decoded UTF-8 bytes.

## Records and limits of the claims

Each result uses primitive `airs.imports-facts` and `primitiveVersion: "1"`.
The tool version appears only in `run.producerVersion` within imported files.
Subjects contain `kind` and `ref`; they omit the optional `image` member because
the enclosing file supplies image identity. Image subject refs retain the UUID
(or `nouuid`) and slice digest prefix.

Each admitted imported-callee row contributes an authoritative `callsTarget`
fact, whose subject is the call address and whose value is the stub address
string, plus an `unknownCalleeEffects` frontier item. The first occurrence of a
stub in a file also contributes an authoritative `hasName` fact with its raw
symbol string. Its provenance retains the three recorded stub instructions and
the two indirect-table entries and symbol-table entry. Loader refs retain the
recorded offset-based forms `stubIndirectEntry[0]@…`,
`pointerIndirectEntry[0]@…`, and `symtab[index]@…`.

The first evidence item carries rule attribution
`airs.swift-broad-error-flow-imports-v1` with version `"1"`; no separate
rule-only provenance item is added. IDs are recomputed from canonical UTF-8
JSON and the contract's subject/predicate/value/rule or subject/gap/detail
fields. The entire supplied subject participates in the ID. Fact revert handles
use the resulting ID.

Authoritative describes a producer-reported image reading, not independent
verification. There are no proven facts, proof certificates, `generation`,
`dependsOn`, derived facts, function-start claims, ABI admission, callee throw
or return claims, or dyld binding claims. Format acceptance establishes neither
image identity acceptance nor resolvable evidence nor store admission. In
particular, the offset-based loader references still need a consumer evidence
resolver; this exporter does not claim that later-stage acceptance.

## Selection, packing, and completion

`--max-facts` defaults to 4,000 and accepts 1 through 4,096. It limits the sum
of facts over the whole export. A stub name repeated in a later file consumes
another fact. Selection first takes the lowest-call-address row of each distinct
stub, sorted by call address, then all remaining rows sorted by call address.
The exporter stops at the first complete row unit that would exceed the budget.
It never splits a unit across results or files. Stub names are deduplicated
across results within each file and repeated when needed in another file.

Packing is greedy in selection order, with these caps:

| Surface | Maximum |
| --- | ---: |
| Facts plus frontier per result | 128 |
| Facts plus frontier per file | 1,024 |
| Results per file | 128 |
| Provenance occurrences per file, before deduplication | 4,096 |
| Every nested array | 128 |
| Root-relative nesting edges | 32 |
| JSON values per file, excluding object keys | 65,536 |
| Members in a container | 4,096 |
| String / object key UTF-8 bytes | 4,096 / 64 |
| File bytes | 4,194,304 |
| Input report bytes / call rows | 16,777,216 / 8,192 |

A new result or file opens when the next whole unit would cross a cap. All
parts receive a final cap check before any output is written. No record is
silently dropped to meet a file-format bound.

Completion requires all four report completeness flags to be true,
`omitted_calls` to be zero, and no exporter budget omission. Every incomplete
file carries the applicable image-level disclosures in its first result.
Report omissions produce `budgetExceeded` with `omitted_calls=<N>`; false
completeness flags produce `producerIncomplete`. Exporter truncation adds
`budgetExceeded` with exactly
`exporter_fact_budget=<N>; exported_rows=<a>; omitted_rows=<b>` and
`missingEvidence: ["omitted_call_rows"]`. Disclosures consume the same caps
as other frontier items. Packing accounts for their final text and counts.
A budget too small for the first unit produces a disclosure-only `narrowed`
result. No imported rows with a complete stub table gives `nothing_to_export`.

An incomplete stub table with no imported rows produces one file with one
`refusal` result: `preconditionFailed`, `retryable: false`, zero facts,
`refusalCount: 1`, `completed: false`, and the applicable disclosures.

## Input refusals

The exporter retains strict required-field/type checks, duplicate-key detection,
profile/model checks, proof-claim refusals, input caps, address consistency,
stub provenance validation, and path-collision and symlink checks.

Contradictions and impossible records refuse as
`rows_with_incomplete_stub_table`, `stub_reason_with_complete_table`,
`unaligned_address`, `call_before_caller_start`, `overlapping_stubs`, or
`conflicting_symbol_entry`. Distinct stubs may share one symbol entry when
both index and nlist offset and symbol agree. The producer's symbol selection
is mirrored: `symbol.lstrip('_').startswith('$s')`, excluding declarations
for which `parsed.supported and not parsed.identity.throws`.
Unsupported symbols refuse as `unsupported_symbol`; semicolons and whitespace
refuse as `invalid_field_symbol`. Forbidden output text takes precedence as
`unsafe_text`, including oversized strings and oversized constructed details.

Identity errors include `unsupported_architecture`, `cpu_subtype_range`,
`slice_range`, `empty_slice`, `slice_extent_overflow`, and field-specific
`invalid_field_*` reasons for malformed digests, UUIDs, or hex addresses.
Other new transport reasons are `invalid_tool_version`, `invalid_max_facts`,
`format_budget_exceeded`, and `invalid_input_path`. Existing paths refuse as
`output_exists`; file operations report `io_error`.

## Manifest and contract pins

`manifest.json` is not imported. It contains exporter version 1, tool version,
input-report SHA-256, per-part name/SHA-256/results/facts/frontier/provenance
occurrences, selected imported-row totals (`total_rows`, `exported_rows`,
`omitted_rows`), completion, and the following pinned contract digests.
Other report row models are outside this projection and these row totals.
The manifest has sorted keys and contains no paths or timestamps beyond the
specified relative contract names and generated part names. Contract files are
not read at runtime. Identical report bytes and arguments yield identical part
and manifest bytes; rearranging report rows preserves part bytes but changes
the manifest's input-report digest.

| Contract file | SHA-256 |
| --- | --- |
| `README.md` | `91439002927ff03da742098be63215197e9f75bf411bfe8d9ab602dcd9f246cd` |
| `navigator-engine.schema.json` | `bbcf9e946a06a393cb458d604fb8c9d854322ffc6c54ef7c4ba1b129f60c0a6c` |
| `vocabulary.json` | `ad3e2b3b6c33d08b2f478255ade0da3e5e80eea8ae42b16c1143b79acd7bbf25` |
| `import/README.md` | `ca84729d95ad6566ffa44a5c833d931a5e893807226267e51d5b4d7b294f3cd0` |
| `import/expected-reports.json` | `3638bf933cc12bc6228b2b9afb9c731751142e53a84e6c67d8b89456e12a97c2` |

The standard-library test checker covers the image-free format stage. Optional
contract tests require `AIRS_NAVIGATOR_CONTRACT_DIR`; schema assertions also
require an already importable `jsonschema`. Neither dependency is installed by
the tests or required by the exporter.
