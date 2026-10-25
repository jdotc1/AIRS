# MOVK W/X v48

Model `arm64-bounded-movk-v48` adds exact MOVK W/X only, adapting the owned
MacScope `decodeMoveWide` mapping. The operation reads its
old destination, replaces the selected 16-bit lane and masks to destination
width. W writes zero-extend. W shifts 32/48 are reserved and rejected. Rd31
is ZR/discard, never SP. NZCV and memory are unchanged.

Original/unknown retained bits remain unknown, including after repeated writes;
no symbolic identity is reconstructed. Raw stack addresses refuse before W
projection. Body FP writes and unrestored preserved registers retain their
existing guards. Recovery remains scoped to existing leaf-body or synchronous
call observations. No memory, CFI, loop or asynchronous scope is added.

Donor encoding examples and read-modify-write classification are reused as
construction references. AIRS uses its own Python state model and native exact
model registry; no donor lifecycle, framework or dependency is introduced.
