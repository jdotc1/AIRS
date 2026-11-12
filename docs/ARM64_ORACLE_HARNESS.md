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
- A full run over the real vectors is recorded below as its own evidence.

## First full run

Made on 2026-11-12 with the engine source at commit f5eefd5 and Python 3.15.2, over
all six vector files (34,863 rows, 34,761 distinct instruction words). All six input
pins matched and no row was malformed. The run used 0.6 seconds of CPU time.

| Class | CFG decoder | Linear decoder |
| --- | ---: | ---: |
| AGREE | 1,747 | 825 |
| AGREE-REJECT | 128 | 0 |
| BOTH-REJECT | 10,386 | 10,514 |
| SCOPE-DECLINE | 22,500 | 23,422 |
| Blocking rows | 0 | 0 |

The AGREE-REJECT reasons are `invalid_bitfield_encoding` (63),
`invalid_extract_encoding` (43), `invalid_logical_immediate` (15) and
`invalid_movk_shift` (7).

What the run leaves open:

- Six kinds the CFG decoder supports never reach AGREE in these vectors (`ret`,
  `smsubl`, `wldr`, `wlsl`, `wsdiv`, `wstr`), and one for the linear decoder (`ret`).
  Whether the vectors lack an accepted form of them or the script's kind table sends
  them to SCOPE-DECLINE has not been examined. Until it is, the result says nothing
  about those kinds.
- About 65% of the rows are SCOPE-DECLINE. The run checks the subset the decoders
  claim and nothing beyond it.
- 19 words differ in validity between oracle files. The summary reports them and
  they block nothing.

The vectors and the run's output are not stored in this repository.

## Generated vectors

The `oracle` CI job generates one seed for every source-derived decoder kind,
its 32 single-bit neighbours, and register-field substitutions 0, 1, 29, 30 and
31 at bit offsets 0, 5, 10 and 16. It adds 16,384 words from a 32-bit linear
congruential generator (initial state `0x41524d36`, multiplier 1664525,
increment 1013904223, modulo 2^32), then de-duplicates and sorts the words.
The explicit seed inventory refuses missing or unknown kinds. The output is
independent of Python's random module and version.

    python3 -I -B scripts/arm64-oracle-words.py --out build/words.s
    python3 -I -B scripts/arm64-oracle-generate.py --input build/words.s --out build/oracle
    python3 -I -B scripts/arm64-oracle-diff.py --generated build/oracle/generated.tsv --require-kind-coverage --out build/oracle/results

Create the parent output directory before running the words command. The generator
uses clang targeting `arm64-apple-macos` and llvm-objdump; it locates them with
`xcrun --find` on macOS and PATH elsewhere. `--clang` and `--objdump` override
those choices. It accepts only `.inst` rows, never executes the assembled object,
and refuses any unparsed disassembly line, address/word mismatch or missing row.
Unknown instructions remain rows. Both tools' version output is retained in
`tools.txt`. Existing generator outputs require `--overwrite`.

`--generated` and `--vectors-root` are mutually exclusive. Generated input has no
pin check; its summary identifies the mode and records SHA-256 and row count.
`--require-kind-coverage` makes any derived kind with no AGREE result a failure
(exit 1, with missing kinds on stderr), independently of blocking rows. Without
these options, the recorded-vector output format is unchanged.

CI asserts that there are no blocking comparisons and that every derived kind
agrees at least once for each decoder. It retains the summary, all disagreement
parts, generated vectors and tool versions, including when the comparison fails.
This uses the same disassembler family as the recorded vectors, so it is not a
second independent oracle. Coverage is of derived kinds, not of the instruction
set, all encodings of a kind, execution semantics or unwind recovery. A nonzero
blocking count must be investigated; generation does not establish decoder correctness.
