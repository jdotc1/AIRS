# Third-party notices

AIRS's original code is licensed under the [MIT License](LICENSE).
Third-party components and platform resources retain their existing copyrights
and license terms.

## Lumen

AIRS uses LumenTokens and LumenUI from the public [Lumen 1.3.0 release](https://github.com/jdotc1/Lumen/tree/v1.3.0),
licensed under its [MIT license](https://github.com/jdotc1/Lumen/blob/v1.3.0/LICENSE).
SwiftPM pins the public release revision in `native/Package.resolved`. The older
`native/Vendor/Lumen` snapshot is retained for historical provenance and is not linked.

## EntitlementDiff

The vendored EntitlementDiff code retains its [MIT license and attribution](native/Vendor/EntitlementDiff/LICENSE),
copyright 2026 EntitlementDiff contributors. Its origin and local changes are
recorded in [UPSTREAM.md](native/Vendor/EntitlementDiff/UPSTREAM.md).

## Python runtime

The separately prepared Python runtime and its bundled components retain their
upstream licenses. Standalone app packaging includes those notices in
`Contents/Resources/RuntimeNotices`; the compiled runtime is excluded from the
source snapshot. See [runtime preparation](docs/PRIVATE_PYTHON.md).

## Apple platform resources

AIRS uses Apple macOS frameworks. Some custom-symbol SVGs in Lumen's
`Sources/LumenUI/Resources/Symbols.xcassets` include Apple SF Symbols template
metadata and reference artwork. Apple-provided frameworks, symbols, templates
and reference material remain subject to their applicable Apple terms.
The AIRS and Lumen MIT licenses cover the owner's original contributions and
do not relicense that third-party material.

## EntitlementLens

- Source: <https://github.com/hideouts-io/EntitlementLens>
- Revision: `d7c6d58e08aa33ec950cd15bf852f277a44bef3c`
- License: MIT; copyright 2026 hideouts-io.
- Adapted area: bounded code-signature SuperBlob/index/slot parsing and checked byte ranges, from `Sources/EntitlementLens/Services/CodeSignatureParser.swift` and `MachOByteRange.swift`.
- Local changes: AIRS descriptor-bound reads, strict exact-slice identity, rejection of overlap across all indexed slots, tighter aggregate budgets, retained evidence validation, and no upstream URL wrapper, architecture-name dictionary join or XML semantic decoder.
- License and detailed provenance: `third_party/EntitlementLens/`.

## Gimli

- Source: <https://github.com/gimli-rs/gimli>
- Revision: `478f07ad90e91bb8b061ec33ef4bd3a8448839e1`
- License choice: MIT, from the upstream MIT OR Apache-2.0 offer.
- Adapted area: CFI fixed-width PC advance and saved-rule-state operations in `src/read/cfi.rs`, translated into AIRS's bounded Python evaluator.
- Local changes: existing AIRS positive/aligned/range constraints, FDE-only saved-rule stack, explicit operation/row/depth budgets and full-stream validation. No Rust code is built or dynamically loaded by AIRS.
- License, pinned source excerpts and detailed provenance: `third_party/gimli/`.

