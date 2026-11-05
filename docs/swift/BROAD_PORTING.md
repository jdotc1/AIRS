# Broad Swift porting and evidence reuse

Status: the bounded research profile passed its26 qualification gates at engine54284c8. Package and engine revisions remain distinct; cross-device delivery is user-deferred. Read
[BROAD_SCOPE.md](BROAD_SCOPE.md) and [BROAD_QUALIFICATION.md](BROAD_QUALIFICATION.md)
before interpreting results.

## Package-root workflow

Use a package-root shell with a supported Python environment and the dependencies
declared by the repository. Discover entry points and fixture tools from included
source rather than hard-coding the author's installation paths:

```sh
python -m airs --help
python -m airs swift-error-flow --help
rg --files scripts fixtures docs schemas tests | rg 'swift|broad'
```

These are usage examples, not receipts that the commands were executed for this
documentation update. A new, authorized offline analysis can explicitly select
the separate broad profile:

```sh
python -m airs swift-error-flow ./input/owned-image --arch arm64 \
  --swift-profile broad-v1 --include-outcome-witnesses \
  --include-error-regions --validate-region-entries \
  --include-structured-presentation --format json \
  --output ./output/broad-report.json
```

Create the chosen bounded output directory first. Replace the example input with
an explicitly owned final Mach-O image or supported input. Do not mix the broad
profile with `--include-swift-methods`. A refusal caused by options, architecture,
metadata, missing evidence, or budgets is a result to retain. Do not remove checks
to make a port appear successful.

Find saved receipts by relative names under the supplied evidence directory, for
example `rg --files ./evidence | rg 'compile|index|qualification|review|manifest'`.
Preserve the receipt-to-image and receipt-to-source identity relationships during
relocation. A package may retain existing digest values without recomputing them.
If a required capture or receipt was not included, report it as missing rather
than substituting an author's private path or inventing a portable location.

## Architecture and ABI adaptation

Ordinary ARM64 and the explicitly selected synchronous untyped Swift research
profile are the present foundation. arm64e, pointer authentication, async calling
conventions, typed throws, runtime dispatch, or a different platform/toolchain
require their own reviewed evidence and admission rules. Do not infer compiler
identity from Swift symbols or copy a register map from another architecture.

A lowering observation binds more than a type spelling: selected slice identity,
raw callable and nominal identity, actual argument/result storage, receiver,
ordinary error transport, and retained instruction bytes. Porting needs new
evidence when those inputs change. Preserving a qualification ID while changing
the binary cannot certify the new binary. Public ABI documentation supplies
context; independent emitted evidence and byte checks supply the scoped claim.

Keep limits explicit for file size, function and instruction counts, metadata
reads, CFG edges, paths, scalar expressions, stack slots, aggregate work, and
serialized output. Truncation and omitted rows must remain visible. Preserve the
separation between raw parser admission, declaration syntax, callsite and nominal
custody, ABI qualification, candidate production, independent validation, and
display. The independent validator must not accept a producer's success assertion
in place of reading the selected bytes and replaying its own bounded rules.

Use separate invocation-owned metadata state for call admission and independent
validation. `create_callsite_session` and its private capability can accelerate
ABI admission; `create_independent_swift_image_ledger` must parse its own raw
directory and never consume that producer capability. Charge each factory once
and all selected-byte work per witness. Serialized JSON and copied objects cannot
substitute for either private exact-image custody object.

Keep reference lowering evidence distinct from selected source lineage. The
owned slice/source map contains the three primary captures and three secondary
representative captures. Primary observation PCs apply only to their matching
primary image; they must not be replayed at unrelated secondary-image addresses.
A fresh compilation is a new image identity and needs independent qualification,
not an edited digest in a saved report. The package deliberately omits capture
executables unless separately cleared; retained digests, source, raw instruction
and metadata records, and relocated nm/objdump views describe historical evidence.
Reproduction does not assert byte identity with those historical executables.

Preserve explicit UUID absence, preferred base, selected FAT index/count, offset,
size and full subtype. A BRK node is an external exception transfer, not a source
return or proof that a handler cannot resume. Unknown scalar values and
conditional ABI outcome roles must survive serialization and display unchanged.

## Validation and handback discipline

Reuse existing unchanged-input receipts. Do not rerun a saved suite, corpus
capture, signing/dependency check, or sealed provenance hash solely because the
package moved or a reviewer changed. Changed implementation needs focused checks
for its affected behavior; any additional unchanged-input or corpus-scale run
requires the task owner's specific authorization. The final authorized
qualification and deterministic comparisons must be recorded once with exact
inputs and outcomes, then reused.

The final portable ZIP must include its own inventory, source and fixture
locations, schemas, relevant tests, qualification ledger, both review records,
recorded evidence, commands relative to its root, and explicit limitations. Raw
private logs, absolute private paths, credentials, and machine-only openers do
not belong in the public contract. A ZIP's existence does not prove delivery:
cross-device delivery requires a supported attachment or an authorized durable
authenticated HTTPS destination, with destination access checked separately.
No publication, upload, release, or installed-app acceptance is authorized by
these examples.
