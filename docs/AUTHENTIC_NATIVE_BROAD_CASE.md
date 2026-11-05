# Authentic native broad-v1 case: Maccy 2.8.0

One bounded, read-only case used the previously acquired authentic publisher
release [Maccy 2.8.0](https://github.com/p0deje/Maccy/releases/tag/2.8.0).
Acquisition/license/language and original archive/container digest receipts were
reused. No application was launched, modified or re-signed; only AIRS ran.

| Boundary | Observed outcome |
| --- | --- |
| Primary container | 5,027,200 bytes, within the8MiB broad image ceiling |
| Selected slice | ARM64 subtype0; FAT index1, container offset2,555,904, size2,471,296 |
| First installed native attempt | `symbol_address_extent` on canonical PIE `__mh_execute_header` |
| Targeted correction | Exact header metadata exclusion; no code/function attribution; see PIE_HEADER_SYMBOL_ADMISSION.md |
| Corrected installed attempt | `function_limit` at function-start entry8,193 |
| Independent function count | 8,617, exceeding the8,192 ceiling by425 |
| Independent metadata source reads | 23,227 bytes total; descriptor-relative/no-follow, stable metadata, no container rehash |
| New regression tests | Three owned methods passed, including six negative contexts; independent source review approved |
| Calls/findings | Unexamined: admission stopped before call analysis |
| Call adjudication/export/history | Blocked by the function ceiling; no report produced, Export correctly disabled |

The independent count decoded one bounded LC_FUNCTION_STARTS table (11,568 bytes),
reusing the prior header/load-command ranges. Entry8,193 begins at table byte
11,008, exactly matching the reported refusal offset. The initial header check
independently examined three symbol records and their declared section bounds.
No AIRS parser or validator supplied those independent interpretations.

The installed correction is AIRS0.3.4 build30, source
`e228302a17ccf5db965e572c67cd70fab4f0f853`, Developer ID signed, notarized Accepted
and stapled. Build29 is preserved for local rollback. The public GitHub preview
release remains build29; no new release assets were published for this case.
Unchanged native/runtime signatures and accepted qualification receipts were
reused. No broad corpus pass, full-suite repeat or ceiling increase occurred.

This case demonstrates a corrected real-input compatibility defect and a precise
remaining capacity boundary. It does **not** establish successful native broad
analysis of Maccy, zero findings, or whole-application acceptance. A larger-function
profile would require separate bounded design and qualification; the current
hard ceiling remains intact. No crash or hang was observed; known macOS geometry
diagnostics remain a separate documented limitation.
