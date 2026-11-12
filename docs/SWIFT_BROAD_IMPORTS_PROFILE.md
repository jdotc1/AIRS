# Imported Swift callee profile

`broad-imports-v1` is an explicitly selected profile for the broad structural Swift analysis. Its outer model is `swift-broad-error-flow-imports-v1`. It uses the `broad-extended-v1` resource limits and the same witness and validation models. Earlier profiles keep their selection, rows, counters and historical meaning unchanged.

## Why

Earlier broad profiles select a direct `BL` only when it targets an image function start whose symbol begins with `$s`. In a stripped app the local names are gone. Calls to imported Swift APIs also target `__TEXT,__stubs` entries, which are not function starts. As a result those profiles never selected direct calls to imported Swift functions, and in the build 32 real-input check every selected candidate was an indirect `BLR`/`BR`. This profile makes direct calls to imported Swift symbols visible. It records retained calls as attributed, unresolved rows. Admitted non-throwing imports are skipped.

## Stub attribution model

`arm64-import-stub-double-binding-v1` (`src/airs/macho_stubs.py`) reads the selected slice bytes itself. It requires the raw section headers to equal the parser-admitted sections. A stub entry is attributed only when all of the following hold:

1. The entry lies in a `__TEXT` `S_SYMBOL_STUBS` section with no section relocations. The section must have a stub size (`reserved2`) of 12, a nonzero size that is a multiple of 12 and lies inside the slice, a 4-byte-aligned address, and an indirect-table range inside `LC_DYSYMTAB`.
2. The entry's three words are exactly `ADRP x16`, `LDR x16, [x16, #imm12*8]` and `BR x16`. Other registers, `BRAA`/`BRAAZ`, a literal `LDR` and every other form are declined.
3. The 8-byte slot the entry loads (ADRP page plus scaled offset) lies at an 8-byte-aligned offset in exactly one lazy or non-lazy symbol-pointer section, and that section is itself well formed.
4. The stub's own indirect entry and the indirect entry for that slot name the same symbol-table index. Neither entry may be `INDIRECT_SYMBOL_LOCAL` or `INDIRECT_SYMBOL_ABS`.
5. The index lies in the `LC_DYSYMTAB` undefined-symbol range. The nlist is an undefined external: not a debugging entry, `N_UNDF`, `N_EXT`, section 0 and value 0. Its name is a bounded, NUL-terminated, nonempty ASCII string inside the string table.

Each failed check declines that entry with a stable reason, checked in the order above. A malformed section declines every entry in it. A call that lands in the middle of an entry is declined as `stub_entry_misaligned`. Each attributed stub records the virtual and file offsets of its three words, both indirect entries and the nlist record. The model decodes no chained fixups and no dyld binding information. The two-level library ordinal from `n_desc` is recorded as data and is not a proven runtime binding.

Limits are 4,096 load commands, 4,096 sections, 65,536 stubs, 1,048,576 indirect entries, 4,096 symbol-name bytes and 8,000,000 work steps. The stub count is checked before any entry is decoded. Exceeding a limit, a missing or out-of-slice symbol or indirect table, or a section-metadata mismatch makes the table incomplete. An incomplete table attributes nothing, and the report then records `import_stubs_complete: false` and `call_details_complete: false`.

## Selection and rows

For a direct `BL`, or a `B` that leaves its function, whose target is not a function start:

- A target outside every stub section is skipped, as in the earlier profiles.
- A declined entry is counted in `declined_stub_calls` and is not selected.
- A non-Swift symbol such as `_objc_msgSend` is counted in `non_swift_import_calls` and is not selected.
- A `$s` symbol that `parse_import_declaration` admits as non-throwing is counted in `non_throwing_swift_import_calls` and is not selected.
- Any other `$s` symbol is selected. That covers symbols admitted as throwing and symbols outside the parser's subset.

Selected import calls use the same omission rules as every other selected call: the aggregate work reservation, the per-function and total row caps, and the encoded-output budget. A retained row is `unresolved` with reason `imported_callee_abi_unqualified`. Its admission records:

- `call_kind`
- the call and stub addresses
- the symbol and library ordinal
- the declaration-syntax result (`syntax_admitted` with the parsed identity, or `syntax_unresolved` with the parser's reason)
- the stub provenance

Its `candidate` and `validation` are empty. The report adds `import_stub_model`, `import_stubs_complete`, `import_stub_reason` and `import_stub_counts`, and appends the limitation `imported_callees_attribution_only`.

## What the rows do not mean

An imported row is attribution plus declaration syntax only. It carries no Swift ABI admission and no outcome witness. It does not claim that the callee throws or returns at runtime, or that dyld binds the symbol to a particular library. A `$s` symbol outside the declaration parser's subset is selected because its throwing status is unknown, not because it is known to throw. Calls that load a GOT slot and branch through `BLR` stay unresolved, as before.

The native app admits the exact `swift-broad-error-flow-imports-v1` / `broad-imports-v1` pair, validates its recorded import envelope and stub arithmetic, and presents import rows as unresolved attribution only. Mismatched pairs remain unsupported raw evidence. The importer never rereads source bytes; section bounds are not recorded, so native section containment cannot be checked.

## Evidence

The new synthetic tests are in `tests/test_swift_broad_imports.py`, 48 methods in total. 46 were written independently of the implementation, from the model description and from hand-built Mach-O bytes. The implementer added two more: one for the section-relocation refusal, and one, after review, for the section-metadata mismatch. They cover:

- attribution, including a FAT-slice container offset and a type-7 pointer section
- every per-entry and section-level decline reason, in check order
- every incomplete-table reason that a parser-admitted image can reach. Two cannot be reached, because the parser rejects those inputs first: `macho_header` and `indirect_symbol_table_extent`. `raw_section_metadata_mismatch` is reached by a section name with a non-ASCII byte, which the parser admits. The full flow refuses that image earlier, in metadata admission (`section_name_encoding`).
- profile isolation
- retention caps
- CLI JSON and text output

`tests/test_swift_broad_imports_fixture.py` checks an owned real-toolchain case. `fixtures/swift-error-flow/broad-imports/OwnedImports.swift` was compiled with Apple Swift 6.4.2 (`-O -target arm64-apple-macos13`, then `strip -x`). The binary has chained fixups and 29 stubs whose pointer slots are in `__DATA_CONST,__got`. The expected stubs and stub calls were derived with Apple tools only (`otool -Iv`, `objdump -d`, `swift-demangle`), independently of AIRS. All 29 stubs attribute to the `otool` symbol and slot.

The 54 calls to stubs split into 27 `$s` calls and 27 Swift-runtime calls. The 27 runtime calls are counted as non-Swift. The 19 distinct `$s` symbols split into 10 admitted non-throwing, 1 admitted throwing and 8 declined. Their 27 call sites produce 12 selected rows and 15 skipped non-throwing calls, replacing the previous 27 rows and 0 skipped calls. All 7 calls whose demangled name contains `throws` remain rows. The Data initializer row is `syntax_admitted` with `throws: true`; declined declarations are `syntax_unresolved`. The binary is never executed. This is one owned case, not real-app or runtime qualification.

See [Imported Swift declaration syntax](SWIFT_IMPORT_DECLARATIONS.md) for the closed grammar, decline reasons, evidence and residual symbol-override hazard. The syntax model is `swift-import-declaration-syntax-v1`. The outer profile and model identities were retained while the declaration grammar settled before native admission; subsequent semantic changes require a new identity.

## Real-input measurement

One third-party application was measured on 2026-11-12 with the engine source at commit f5eefd5 and Python 3.15.2: Maccy 2.8.0, from the release archive whose SHA-256 is recorded in `docs/security-delta-real-corpus/cases/p0deje.maccy.2.7.1-to-2.8.0.json`. The ARM64 slice has 393,880 instruction words and 55,863 call instructions. The binary was read as data and never executed. This is a measurement of attribution on one input. It is not a correctness claim and not prevalence.

| | `broad-extended-v1` | `broad-imports-v1` | `broad-imports-got-v1` |
| --- | ---: | ---: | ---: |
| Candidates | 5,263 | 12,690 | 11,241 |
| Retained rows (limit 8,192) | 5,263 | 8,192 | 8,192 |
| Omitted by the limit | 0 | 4,498 | 3,049 |
| Retained `imported_callee_abi_unqualified` | 0 | 5,123 | 5,809 |
| Retained `indirect_target_unresolved` | 5,263 | 3,069 | 2,383 |

The extended-profile figures equal the ones recorded for build 32. With the imports profile, all 1,219 stubs were attributed and none declined. Calls through stubs split into 23,615 to non-Swift symbols, 3,145 to Swift symbols admitted as non-throwing (skipped) and 7,427 selected as rows. With the GOT profile, 2,140 GOT slots were read (1,893 agreeing, 247 declined) and 1,449 of 3,200 GOT candidates were attributed, all to non-Swift symbols; 1,746 of the 1,751 declines are `got_base_not_adrp`.

Because rows were omitted, both imports runs report incomplete call details and exit with status 1, as designed.

Declaration syntax of the retained imported-callee rows (imports profile / GOT profile): admitted 4 / 4; unresolved 5,119 / 5,805. The unresolved reasons are generic requirements 1,742 / 1,984, unknown substitution 1,679 / 1,971, unsupported production 1,129 / 1,240, protocol context 438 / 471, unconsumed suffix 71 / 71, invalid grammar 27 / 31, thunk or specialization 17 / 17 and closure type 16 / 20.

What this shows: stub attribution and the non-throwing skip work on a real application. The declaration grammar admits almost none of the symbols that remain, the retention limit is exceeded, and every retained row is still unresolved. [ROADMAP.md](ROADMAP.md) section 4.3 is the plan that follows from it.
