# Imported Swift callee profile

`broad-imports-v1` is an explicitly selected profile for the broad structural Swift analysis. Its outer model is `swift-broad-error-flow-imports-v1`. It uses the `broad-extended-v1` resource limits and the same witness and validation models. Earlier profiles keep their selection, rows, counters and historical meaning unchanged.

## Why

Earlier broad profiles select a direct `BL` only when it targets an image function start whose symbol begins with `$s`. In a stripped app the local names are gone. Calls to imported Swift APIs also target `__TEXT,__stubs` entries, which are not function starts. As a result those profiles never selected direct calls to imported Swift functions, and in the build 32 real-input check every selected candidate was an indirect `BLR`/`BR`. This profile makes direct calls to imported Swift symbols visible. It records them as attributed, unresolved rows.

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
- A `$s` symbol that the bounded declaration parser admits as non-throwing is counted in `non_throwing_swift_import_calls` and is not selected.
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

The native app does not yet admit this model. Its importer accepts only the three earlier model/profile pairs, so it treats a `broad-imports-v1` report as unsupported.

## Evidence

The new synthetic tests are in `tests/test_swift_broad_imports.py`, 48 methods in total. 46 were written independently of the implementation, from the model description and from hand-built Mach-O bytes. The implementer added two more: one for the section-relocation refusal, and one, after review, for the section-metadata mismatch. They cover:

- attribution, including a FAT-slice container offset and a type-7 pointer section
- every per-entry and section-level decline reason, in check order
- every incomplete-table reason that a parser-admitted image can reach. Two cannot be reached, because the parser rejects those inputs first: `macho_header` and `indirect_symbol_table_extent`. `raw_section_metadata_mismatch` is reached by a section name with a non-ASCII byte, which the parser admits. The full flow refuses that image earlier, in metadata admission (`section_name_encoding`).
- profile isolation
- retention caps
- CLI JSON and text output

`tests/test_swift_broad_imports_fixture.py` checks an owned real-toolchain case. `fixtures/swift-error-flow/broad-imports/OwnedImports.swift` was compiled with Apple Swift 6.4.2 (`-O -target arm64-apple-macos13`, then `strip -x`). The binary has chained fixups and 29 stubs whose pointer slots are in `__DATA_CONST,__got`. The expected stubs and stub calls were derived with Apple tools only (`otool -Iv`, `objdump -d`, `swift-demangle`), independently of AIRS. All 29 stubs attribute to the `otool` symbol and slot.

The 54 calls to stubs split into 27 `$s` calls and 27 Swift-runtime calls. The 27 `$s` calls are exactly the selected rows, and the 27 runtime calls are counted as non-Swift. All 27 `$s` symbols in this binary fall outside the declaration parser's subset, so all 27 rows are `syntax_unresolved`. The 7 calls whose demangled name contains `throws` are among them. The binary is never executed. This is one owned case, not real-app or runtime qualification.
