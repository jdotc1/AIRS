# Native optional body-fingerprint codec

Baseline: public main f017c37, exact-body candidates merged in PR37 using accepted
EXACT_BODY_CANDIDATES.md results. This bounded reuse increment adapts the
MacScope optional Codable fingerprint-facts convention to AIRS FunctionInfo.
The donor checkout is read-only. No matching or app activation is included here.

## Implemented contract

FunctionInfo exposes optional typed FunctionBodyFingerprint evidence. Missing body_fingerprint means
unavailable; explicit null is invalid. Present objects must have exactly kind,
sha256 and instruction_count. Known kind is arm64-exact-bytes-v1; digest is 64
lowercase hexadecimal characters and count is 3–16,384. Bounds are checked before
count-to-size conversion. Encoding an absent value omits the field; valid values
are preserved through a typed native round trip.

Fingerprint-specific context guards apply regardless of the advertised analysis
model: exact ordinary ARM64 subtype 0/1, independent LC_FUNCTION_STARTS, aligned
function start, size==count*4, matching finding instruction count and a supported
agreement/inconsistency. Existing extent/scope checks remain authoritative.
Imported fingerprints are structural review evidence, never authenticated bytes,
source-function identity or unwind proof. No hashing is added to native import.

Swift JSONDecoder may normalize integral JSON numeric forms such as 4.0 to Int 4;
Python admission requires an integer-valued Python object. The native codec explicitly qualifies this representation distinction while rejecting Boolean,
string and fractional counts. This is not a widening of size or count bounds.

## Qualification

Nine new BodyFingerprintCodecTests methods passed with zero failures. Their
synthetic report objects use placeholder digests, never bytes or real stores.
The first preimplementation unknown-kind test failed as intended because the old
codec ignored the field. After implementation, the complete new class passed.
Other test bundles selected zero methods; no unchanged suite was replayed.

Cases cover typed properties, typed encoding/decoding with retained scope/PCs,
absent-key omission, explicit null, missing/extra fields and wrong types,
digest/count bounds, future-model context guards, exact minimum/maximum extents,
and native normalization of integral JSON numbers. Imported values remain review
evidence, not authenticated digests or independently re-proven analysis.

The real AIRSApp debug product built successfully in 29.79 seconds under the
exclusive native gate. The clean preimplementation build and postimplementation
build exposed existing warnings in CodeUnitEntitlementReader.swift and
CoverageInventory.swift; neither file was changed. No diagnostic implicated the
new codec. Build success is not GUI/runtime acceptance.

Independent read-only source and test review found no actionable defect. It
checked exact optional/null/extra-key handling, bounded arithmetic, all-model
context guards, synthesized optional encoding and the numeric representation
limit. The reviewer ran no tests, builds, hashes, writes or target code.

Accepted Python producer, candidate-matching, analysis and distribution results
were reused. Logs are retained under local-evidence/native-body-fingerprint-resume.
The regenerated native/.build cache was removed after checks to keep the checkout
lean. No source image, accepted export or provenance hash was replayed.

Native compile/test is qualified for this source change. GUI activation, optional
producer arguments, comparison flags, defaults, signing and release are separate.
Original JSON round-trip fidelity for unrelated fields is not claimed by this
focused codec; only the typed optional fingerprint and existing typed finding
scope/identity fields are in scope. Installed app, settings and stores remain
unchanged. No MacScope source, accepted fixture or provenance hash is modified.
