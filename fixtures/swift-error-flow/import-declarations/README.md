# import-declarations fixture

Evidence for `airs.swift_import_declarations` (syntax model `swift-import-declaration-syntax-v1`), read by
`tests/test_swift_import_declarations.py`. Nothing here is executed.

## Files

- `source.swift`: owned Swift source for module `OracleLib` (309 declarations). Every declaration's effects
  (`throws`, `rethrows`, `async`, none) are fixed by construction, so the source is the truth for each symbol.
- `symbols.tsv`: the 494 exported Swift symbols of that module, one row each.
- `probes.tsv`: the 675 grammar probe strings for packets A to E (synthetic module `M`, plus compiled rows and the
  19 symbols of the `broad-imports` fixture).
- `old-parser.tsv`: the result of the unchanged `parse_broad_declaration` for every `symbols.tsv` row and the 19
  `broad-imports` symbols, recorded before the new entry point existed. It pins isolation (the old parser must not
  change).

All files are tab-separated UTF-8 with one header line and no quoting (read with `csv.QUOTE_NONE`).

## How symbols.tsv was produced

1. `source.swift` was compiled with Apple Swift 6.4.2 (swiftlang-6.4.2.1.9):
   `swiftc -O -target arm64-apple-macos13 -parse-as-library -module-name OracleLib -emit-library`.
2. The exported `$s` symbols were listed with `nm` (leading `_` removed) and demangled with
   `swift-demangle --compact`.
3. `entity_shape`, `source_truth_throws` (`yes`, `no` or `rethrows`) and `source_truth_async` (`yes`, `no`) come
   from the declaration in `source.swift` that the symbol belongs to, not from the mangled text.

Columns:

| column | meaning |
| --- | --- |
| `mangled` | the symbol as listed by `nm`, without the leading `_` |
| `demangled` | `swift-demangle --compact` output |
| `entity_shape` | what the symbol is (free_function, getter, init, metadata_accessor, ...) |
| `source_truth_throws`, `source_truth_async` | effects of the source declaration |
| `expected_decision` | `admit` or `decline` under the grammar |
| `expected_reason` | recommended decline reason (an existing `UnsupportedReason` value); empty for `admit` |
| `expected_throws` | `true` or `false` for `admit` rows; empty for `decline` rows |

The decision and `expected_throws` are binding. `expected_reason` is informative only: the grammar fixes the
verdict, while the reason a string gets is a recommendation.

## How the expected columns were computed

The expected columns of `symbols.tsv` and `probes.tsv` were computed from the written grammar (the productions
for packets A to E), not from the implementation under test. Two independent prototypes of that grammar, written
by different authors, were run over every row; they agree on every decision and on every `throws` value. Where
the two differed in reason only, the reason in the table is the one the grammar text recommends.

Result over `symbols.tsv`: 101 admitted with `throws == false`, 39 admitted with `throws == true`, 354 declined.
Every admitted non-throwing row has source truth `throws == no` and `async == no`, so the differential bar holds
with zero exceptions. Every admitted throwing row has source truth `throws == yes`.

`probes.tsv` holds 180 admitted non-throwing, 14 admitted throwing and 481 declined strings. Two compiled rows
(`$s1M4fakeyyF`, `$s1M5fakeAyyF`) come from functions given a plain-looking symbol with `@_silgen_name`; no
grammar over the mangled name can see their effects, so they are admitted and are wrong at source level. This
residual is documented, and the tests exclude these two rows from the source-level check by name.

`old-parser.tsv` was produced by calling `parse_broad_declaration(symbol)` on each string and recording
`supported`, the reason value, `offset`, `detail` and, for supported rows, the identity as compact JSON
(`json.dumps(asdict(identity), sort_keys=True, separators=(',', ':'))`).
