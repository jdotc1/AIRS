# ARM64 decode oracle harness
`scripts/arm64-oracle-diff.py` compares the two AIRS ARM64 decoders (linear and
CFG) with recorded disassembler output. It never runs a disassembler or uses
the network; it reads the vector files as data.

## Rule under test

AIRS may refuse any word it does not model. Every word it admits must match the
oracle's instruction and SP/FP effects, and AIRS must never call a word invalid
when the oracle decodes it. An oracle `<unknown>` is never agreement; an
unparseable row is listed, never skipped.

## Input layout

`--vectors-root` holds any of these tab-separated files (absent files are
refused unless `--allow-unpinned`; `#` lines are comments; each file is limited to 64 MiB):
- `arm64-coverage-vectors/vectors.tsv`, `arm64-reserved-vectors/vectors.tsv`: group, address, word, objdump
- `arm64-feature-vectors/vectors.tsv`: group, address, word, mnemonic, operands, source
- `arm64-feature-vectors/boundary.tsv`: address, word, mnemonic, operands
- `arm64-shipping-vectors/vectors.tsv`: group, word, mnemonic, operands, source
- `arm64-shipping-vectors/boundary.tsv`: word, mnemonic, operands

Words are eight hex digits. Rows without an address treat branch targets as wildcards.

## Running it
    python3 -I -B scripts/arm64-oracle-diff.py --vectors-root DIR --out OUT
`--out` is required; inside the repository it must sit under a directory the
root `.gitignore` names. Existing outputs need `--overwrite`. `--limit N`
decodes the first N distinct rows per file. `--full` adds `rows.tsv.gz`.
Inputs are checked against recorded pins (path, git blob id, size, row counts):
a missing or differing file refuses the run. `--allow-unpinned` switches that
check off; only the synthetic unit tests use it.

Outputs: `summary.json` (byte-stable: manifest with SHA-256 values, counts per
decoder, refusals by code, agreements by kind), `disagreements.tsv` (every
blocking row, in complete numbered parts above 2000 rows) and `run-info.json`
(timing). Exit: 0 clean, 1 blocking rows, 2 usage error, refusal, failed kind-table
derivation or an unexpected error (one-line message on stderr, for example an
`--out` that is an existing file), 3 input missing or not matching its pin.

## Outcomes
- AGREE: admitted; mnemonic, operands and SP/FP effects match.
- AGREE-REJECT: AIRS says invalid; the oracle rejects it too.
- BOTH-REJECT: AIRS declines as out of scope; the oracle rejects it.
- SCOPE-DECLINE: AIRS declines as out of scope; the oracle decodes it.

Blocking:
- OVER-ADMIT: admitted; the oracle rejects it.
- WRONG-ADMIT: admitted; the mnemonic (F), operands (O) or SP/FP effects (P) differ.
- FALSE-INVALID: AIRS says invalid; the oracle decodes it.
- DECODER-EXCEPTION: a decoder crashed or returned something unclassified.
- UNPARSEABLE: a malformed row or oracle text.
- ORACLE-CONFLICT: one word and address has two different oracle answers.

Only `invalid_*` error codes are validity claims. A gap in the script's kind table stops the run.

## What it does not claim

- It is not ISA-complete: it checks only the words in the vectors.
- Refusals are allowed, so SCOPE-DECLINE is not a defect.
- It does not validate the oracle; validity depends on the oracle's extensions.
- No vector file or disassembler output is vendored here.
- A full run over the real vectors is recorded separately as its own evidence.
