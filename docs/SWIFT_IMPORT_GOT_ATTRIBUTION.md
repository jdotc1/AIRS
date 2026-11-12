# GOT-loaded BLR attribution profile

`broad-imports-got-v1` is an explicitly selected profile for the broad structural Swift analysis. Its outer model is `swift-broad-error-flow-imports-got-v1`. It is a strict superset of `broad-imports-v1` (see `docs/SWIFT_BROAD_IMPORTS_PROFILE.md`): it uses the same resource limits, witness and validation models, and adds the keys described below. Every existing profile, `broad-imports-v1` included, keeps its selection, rows, counters and meaning unchanged. The new profile is a sibling, not a change to `broad-imports-v1`.

## Why

An indirect call through a register loaded from a non-lazy symbol pointer slot (`__got`) is invisible to the stub model, which only follows direct calls into `__TEXT,__stubs`. A typical shape is:

```
adrp x16, <page>
ldr  x16, [x16, #off]
blr  x16
```

This profile attributes such a `BLR` to the undefined external symbol bound to that slot. It does so only when two independent binding sources name the same import. Attribution is all it does.

## Model identities

| identity | value |
| --- | --- |
| profile | `broad-imports-got-v1` |
| report model | `swift-broad-error-flow-imports-got-v1` |
| binding model | `arm64-got-blr-two-source-binding-v1` (`src/airs/macho_got.py`) |
| chained-fixups decoder | `macho-chained-fixups-64-bind-v1` |
| call-site window | `adrp-ldr-blr-straight-line-window-v1` |
| row model | `swift-broad-got-callsite-v1` |

Select it with `--swift-profile broad-imports-got-v1` on `swift-error-flow`, with the same prerequisite flags as the other broad profiles.

## Two binding sources

For each 8-byte slot of every `S_NON_LAZY_SYMBOL_POINTERS` section, both sources are decoded and compared, unless the chained fixups fail for the whole image (see below). A slot is attributed only if both decode and agree.

- Source A is the indirect symbol table (`LC_DYSYMTAB`) plus the nlist record. The entry must be neither local nor absolute, must lie in the undefined-symbol range, and the nlist must be an undefined external with a bounded, NUL-terminated, nonempty ASCII name. Source A yields a name, a two-level library ordinal and a weak-reference flag.
- Source B is the `LC_DYLD_CHAINED_FIXUPS` chain member at that slot plus its imports-table entry. The member is reached by walking the page chain from the page start; reading the raw qword at the slot without reaching it by the walk is never used as evidence. Only the plain import format (no addends) with uncompressed symbols is accepted, and only pointer formats 2 and 6 (`DYLD_CHAINED_PTR_64` and `DYLD_CHAINED_PTR_64_OFFSET`). The decoder follows the SDK header meaning of `segment_offset` (offset in memory to the start of the segment, that is the segment's address minus the image base) and declines on mismatch.

Recorded provenance uses slice file offsets throughout, including `name_offset`, which is the offset of the symbol name and not the imports-table field. `chain_step` counts chain members from 0 in walk order within the page.

Agreement is checked in this order: identical name bytes (no normalisation, no underscore stripping); no special library ordinals (self, dynamic lookup, executable, flat or weak lookup); both ordinals within the dylib count; equal ordinals; equal weak flags; a valid library path. There is no single-source fallback and no tie-break. Classic opcode-based binding is not decoded: an image without chained fixups declines every slot.

Both tables normally come from the same linker, so agreement is internal consistency, not independent proof of run-time binding.

## Call-site window

For a plain `BLR Xn` (not `BLRAA`/`BLRAB` forms, not `BR`), the model walks backwards inside the function. The load must be `LDR Xn, [Xb, #imm]` (64-bit, unsigned offset) and the base must be set by an `ADRP`. Between them, and between the load and the call, at most three instructions per gap are allowed, from a closed list: `NOP`, register `MOV`, `MOVZ`/`MOVN`/`MOVK` and non-flag-setting `ADD`/`SUB` immediate. Each must not write the tracked register. Any other word, or a write to the register, ends the window.

An entry screen then requires that no direct branch destination, function start or defined-symbol value lies after the `ADRP` up to and including the `BLR`, that the window sits in one executable section, and that no word of it is data-in-code. The slot address is computed from the `ADRP` page and the load offset and must fall in a valid `S_NON_LAZY_SYMBOL_POINTERS` section.

The conditional-branch screen uses `w & 0xff000000 == 0x54000000`, matching both `B.cond` and `BC.cond`.

The entry screen is syntactic. It does not see computed branches (`BR`/`BLR` to a register, jump tables), exception landing pads or run-time patching (limitation `got_window_entry_screen_syntactic`).

## Refusal reasons

Unknown never becomes agreement. Every failure is a stable reason, at one of four levels.

- Table-level (the table is incomplete, nothing is attributed, and the report sets `call_details_complete: false`): `macho_header`, `load_command_limit`, `section_limit`, `raw_section_metadata_mismatch`, `indirect_symbol_table_missing`, `indirect_symbol_limit`, `indirect_symbol_table_extent`, `got_slot_limit`, `got_entry_screen_limit`, `got_data_in_code_limit`, `got_work_limit`. An executable section that cannot be screened (zero-fill type or file range outside the slice) is reported as `macho_header`.
- Image-level (the table is complete, every slot declines with the same reason): `chained_fixups_absent`, `chained_fixups_duplicate`, `chained_fixups_extent`, `binding_encoding_ambiguous` (classic bind opcodes alongside chained fixups), `binding_namespace_flat`, `chained_fixups_version`, `chained_header_layout`, `chained_imports_format_unsupported`, `chained_symbols_compressed`, `chained_imports_limit`, `chained_starts_layout`, `binding_library_table_limit`.
- Slot-level, source A: `indirect_symbol_local_or_absolute`, `indirect_symbol_index_range`, `indirect_symbol_not_undefined_range`, `imported_symbol_not_undefined_external`, `imported_symbol_name`.
- Slot-level, source B: `chained_slot_not_covered`, `chained_segment_record_extent`, `chained_page_size_unsupported`, `chained_pointer_format_unsupported`, `chained_segment_offset_mismatch`, `chained_page_start_multi`, `chained_chain_malformed`, `chained_pointer_reserved_bits`, `chained_import_ordinal_range`, `chained_slot_not_member`, `chained_slot_rebase`, `chained_bind_addend_nonzero`, `chained_import_name`. A malformed page chain declines every slot on that page.
- Slot-level, agreement and mapping: `binding_name_mismatch`, `binding_library_ordinal_special`, `binding_library_ordinal_range`, `binding_library_mismatch`, `binding_weak_mismatch`, `binding_library_name`, `got_slot_unmapped`.
- Call-level window: `got_base_not_adrp`, `got_window_gap_limit`, `got_window_outside_function`, `got_window_incoming_edge`, `got_window_symbol_entry`, `got_window_data_in_code`, `got_slot_unmapped`, `got_slot_section_kind`, `got_slot_section_invalid`.

The GOT path ignores a site only when the first word before the `BLR` that is not skipped as an allowlisted gap instruction is not a 64-bit `LDR Xn, [Xb, #imm]`; such a site is left to the existing path. Any site that does have that load is a candidate. A load whose base register is not set by an `ADRP` declines `got_base_not_adrp`. A declined site is counted, and its row is exactly the row `broad-imports-v1` produces.

Most reasons have synthetic coverage in `tests/test_macho_got.py`, with positive controls and single-field patches where parser admission permits them. The reachable non-ASCII segment-name cause of `macho_header` is tested: `parse_macho` replaces non-ASCII bytes, whereas the GOT decoder requires ASCII. Its other causes (header and command extents, sizes, duplicates, final command cursor, and unbacked executable sections) are refused first by `parse_macho`. Both `indirect_symbol_table_extent` raise sites are unreachable: `parse_macho` and its `payload_extent` helper validate the indirect, nlist and string-table extents. The call-level `got_window_data_in_code` reason is untested and unreachable through admitted functions: `parse_macho` accepts embedded data but marks every function in the affected section, and the GOT window excludes those functions; this is not parser byte rejection.

The section-edge cause of `got_window_outside_function` is tested where section and function starts coincide; a section edge strictly inside a function is prevented by `parse_macho` function construction. The function-start cause of `got_window_symbol_entry` is untested because `parse_macho` ends each function at the next start, so a window cannot cross it. Slot-level `got_slot_unmapped` is untested because `parse_macho` requires section containment and `_check_nonoverlap` rejects overlapping segment VM ranges. The command-size cause of `chained_fixups_extent` is untested because `parse_macho` requires a 16-byte link-edit command. The `chained_starts_layout` cause with a nonzero `__TEXT` file offset is tested with a shifted `__TEXT` mapping and a zero-offset positive control; absent or duplicate `__TEXT` segments are parser-refused. These specific coverage gaps are not claimed as tested.

## Selection and rows

For an attributed GOT call:

- A symbol that does not begin with `$s` (after removing leading underscores) is a non-Swift call. It leaves `calls[]` and is counted in `non_swift_got_calls`.
- A `$s` symbol is parsed with the same declaration entry point used for stub symbols, `parse_import_declaration` (syntax model `swift-import-declaration-syntax-v1`; see [Imported Swift declaration syntax](SWIFT_IMPORT_DECLARATIONS.md)). If the declaration is supported and does not throw, the call leaves `calls[]` and is counted in `non_throwing_swift_got_calls`.
- Any other `$s` call is selected (`selected_got_calls`, and `selected_call_candidates`) and follows the same omission rules as every other selected call. A retained row is `unresolved` with reason `imported_callee_abi_unqualified` and `call_kind` `blr_got`. Its admission records the register, the `ADRP` and `LDR` addresses, the slot address and section, the symbol, library ordinal and path, weak flag, import ordinal, the declaration-syntax result, and provenance (every word of the window, with slice and container file offsets, plus the offsets of both binding sources and the chain walk). `call_return_proven` and `syntactic_call_target_admitted` are false, and `import_attribution_admitted` is true.

Report additions (this profile only): `got_binding_model`, `chained_fixups_model`, `got_window_model`, `got_bindings_complete`, `got_binding_reason`, `chained_fixups_status` (`decoded`, an image-level reason, or `not_decoded` when the table is incomplete, including when chained fixups were never read), `got_counts` (`got_slots`, `agreeing_got_slots`, `declined_got_slots`, `blr_instructions`, `got_candidates`, `attributed_got_calls`, `declined_got_calls`, `selected_got_calls`, `non_throwing_swift_got_calls`, `non_swift_got_calls`), `got_decline_counts` and `got_slot_decline_counts`. The limitations list gains `got_callees_attribution_only` and `got_window_entry_screen_syntactic`. An incomplete table also sets `call_details_complete: false`. `not_decoded` is a fixed incomplete-table sentinel, including work-limit stops after chained work has begun; it does not assert that no bytes were read. The text renderer shows the same counters under this profile only.

## Limits

Defaults: 4,096 load commands, 4,096 sections, 1,048,576 indirect entries, 4,096 symbol-name bytes, 1,048,576 GOT slots, 1,048,576 chained imports, 4,000,000 chain members, 4,000,000 screened words, 65,536 data-in-code entries, a gap of 3 allowlisted instructions on each side of the load, and 16,000,000 work steps. Slot and word counts are checked before decoding. Exceeding a table-level limit makes the table incomplete.

An image-level chained failure declines every valid GOT slot with that reason and skips source A.
Executable sections that are zero-fill or outside the slice make the GOT table incomplete with `macho_header`, although parser admission rejects those bytes first.
`got.work` is added to `analysis_work`, so the aggregate-work omission threshold can be reached earlier than in `broad-imports-v1`.
Each retained GOT row has `work_steps = 16 + len(symbol) + number of window words`.

## Fixture outcome

`fixtures/swift-error-flow/broad-imports/OwnedImports.macho` is an owned binary with chained fixups. Its expectation is in `fixtures/swift-error-flow/broad-imports/expected-got.json`. It is derived only from Apple developer tool output (`otool`, `dyld_info`, `objdump`), with the exact commands recorded in its `derivation` field; no AIRS output and no execution of the binary was involved.

- 35 `__got` slots, all 35 agree between the two sources, none declined.
- 7 `BLR` instructions, all 7 GOT candidates. Three are attributed to the non-Swift symbol `___chkstk_darwin`: they leave `calls[]` and are counted in `non_swift_got_calls`. Four value-witness calls (the base register comes from runtime metadata, not an `ADRP`) decline `got_base_not_adrp`, and their rows are unchanged. The `BR x2` witness tail call is not a `BLR` and is untouched.
- `selected_got_calls` and `non_throwing_swift_got_calls` are 0. `calls[]` equals the `broad-imports-v1` `calls[]` minus exactly the three attributed rows.

The `$s` row path has no real-compiler case in this fixture. It is covered by tests that build Mach-O bytes by hand.

## Isolation

Every new branch is gated on the GOT profile. A 16-report comparison (4 owned binaries by the 4 earlier profiles) between the tree immediately before this change and the tree with it was run once and found no difference in any report. Within `broad-imports-got-v1`, every row at a pc that is not an attributed GOT call is identical to the `broad-imports-v1` row; a test checks this in-process. `src/airs/macho_stubs.py` is unchanged. The new module reads only the selected slice bytes, uses only the standard library and `airs.types`, and never executes or maps the analysed binary.

## What this does not claim

- Attribution only. It does not claim that any callee throws or returns, and no Swift ABI admission or outcome witness is made.
- It does not claim which library dyld binds a symbol to at run time. Interposition, missing weak imports, flat lookup and run-time patching are out of scope, and the library ordinal is recorded as data.
- Only `BLR` is considered, only chained fixups are decoded, and only pointer formats 2 and 6 are accepted. Every other case declines or is left to the existing path.
- The entry screen is syntactic, as described above.
- Unresolved items stay in the denominators; unknown never becomes agreement.
- The profile is engine-only. The native app does not admit this model/profile pair yet, so it does not present these reports.
