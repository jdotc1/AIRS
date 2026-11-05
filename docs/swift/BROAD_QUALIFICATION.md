# Broad Swift qualification ledger

Status: **QUALIFIED** at engine revision `54284c8b3c7f3f44ff716de88b8301d5c4c4a6e0`. All 26 measured gates passed.
This is local research qualification; it does not establish runtime execution,
source reconstruction, ownership safety, installed-app acceptance or a release.

| Gate | Required | Recorded |
| --- | ---: | ---: |
| Primary source declarations / methods | 420 / 340 | 420 / 340 |
| Distinct source feature vectors | 420 | 420 |
| Source signature shapes | 80 | 362 |
| Confirmed primary physical calls | 1,500 | 2,191 |
| Emitted ABI shapes | 80 | 175 |
| Independent primary structural witnesses | 250 | 370 |
| Positive outcome geometries | 10 | 42 |
| Required compiler challenge forms | 12 | 12 |
| Qualified result lowerings | 8 | 21 |
| Differentiated negatives / false eligibility | 300 / 0 | 300 / 0 |
| Distinct deterministic comparisons / equal | 100 / 100 | 100 / 100 |

| Primary family | Eligible sites | Minimum |
| --- | ---: | ---: |
| free | 96 | 15 |
| struct | 127 | 15 |
| enum | 37 | 15 |
| direct_final_class | 38 | 15 |
| static | 27 | 15 |
| extension | 20 | 15 |
| concrete_generic | 25 | 15 |

Each required family has a separate negative control. Primary eligible witnesses
are 210 at O and 160 at Onone. Osize was compiled and indexed, but has zero
eligible witnesses under the current strict caller-local CFG/entry contract.
That limitation is preserved rather than converted into positive coverage.

The second Swift 6.3.3 compiler's 64-case representative capture has 284 confirmed
physical calls and 46 independent eligible witnesses (28 O,18 Onone). It is not
a second full 1,500-call corpus. The primary compiler is Apple Swift 6.4.2;
the retained compiler/SDK/target/LLVM argument and version receipts are reused.

A separately authorized six-function Swift supplement was first compiled in
three modes under a combined 60-second/16-MiB ceiling. Its 11 indexed calls were
independently checked once. The observed nested second-call/error corridor and
literal local-conversion evidence supplies only those two required challenge
entries. It adds no primary-positive, family, source-count or second-compiler
credit. The other ten challenge entries come from the primary capture.

The measured second qualification took 40.4706755 seconds before final report
serialization. RUSAGE_SELF process-lifetime peak RSS was 279,609,344 bytes;
this is not an interval peak and excludes compiler/native/Git-helper children
and the storage-guard parent. Work was 129,911,969 charged steps and retained
encoded evidence was 67,381,822 bytes; those are not RSS ceilings.

The first final pass at 02c58aa remains preserved as INCOMPLETE: 202 positives,
static6/extension8 and four challenge omissions. It was not overwritten. Jeff
authorized one repaired-source pass; that pass produced these final results.
All original compiler images, indexes and source digests were reused without
recompilation, redisassembly or rehashing. The new supplement received only its
first seals and first observations, separately authorized by Jeff.

The historical baseline records 2,241 tests with one skip in30.231s. Component
checks and their new repair regressions are retained individually in the check
ledger; they are not a fresh whole-branch full-suite total. Original default
golden equality and historical model receipts are reused. Missing historical
command details remain explicitly unavailable instead of being invented.

Both independent whole-branch source reviews passed the exact qualified engine
revision. The final package can add documentation, tests and packager-only
changes; its manifest distinguishes package_head from engine_qualified_revision.
See BROAD_REVIEW_ROUND_1.md, BROAD_REVIEW_ROUND_2.md and BROAD_PORTING.md.

General virtual/witness targets, closures, async and typed throws retain explicit
partial/refused capabilities. String/existential result conventions remain
unqualified. No unsupported dispatch or ABI becomes eligible by source spelling.
The full machine ledger retains all selected sites, refusal reasons and source
case mappings. Positive result types span Void, Bool, signed/unsigned widths,
Float/Double, Optional<Int>, tuples, small/large structs, enums and references.

The disclosed earlier CFG worker repeated-check incident remains recorded in the
check ledger; those executions are not relabeled as authorized new verification.
Cross-device delivery is USER_DEFERRED by Jeff. The archive is STAGED_LOCAL_ONLY.
