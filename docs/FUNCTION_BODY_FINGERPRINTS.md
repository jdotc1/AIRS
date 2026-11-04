# Optional exact-body fingerprints

Baseline: public main fe67170, manual finding pairs merged in PR35 with accepted
MANUAL_FUNCTION_PAIRS.md results reused. This bounded producer adapts MacScope's
stable digest approach and substantial-body floor of three instructions from
FunctionVersionFingerprinting.stableDigest and FunctionVersionMatcher. MacScope
is read-only. AIRS retains encoded bytes and immediates instead of importing the
decompiler's normalized-text fingerprints or claiming donor qualification.

## Use and representation

Opt in through audit_path(..., include_function_fingerprints=True), or:

```sh
python3 airs_cli.py audit new-input.macho --include-function-fingerprints --output audit.json
```

The default is off, including native-app analysis calls. Eligible findings gain
function.body_fingerprint with exactly kind, sha256 and instruction_count. Kind
is arm64-exact-bytes-v1. The lowercase SHA-256 covers the domain bytes
`AIRS arm64 exact-body v1` followed by a zero byte and the exact function bytes
in original encoded order. It includes all encoded operands/immediates; it does
not include the symbol or preferred VM address. Relocated PC-relative operands
may change bytes and therefore the digest. This kind must not be treated as a
normalized/relocation-insensitive fingerprint.

An annotation is optional review evidence, not source-function identity,
authentication or unwind proof. It is bound to the existing finding range and
selected-image report context. No automatic joining, new verdict, checked PC,
identity, function boundary or comparison signature is introduced. Empty/missing
fingerprints provide no matching evidence. Manual pairs remain explicit review
selection. Analysis model stays v50 and report schema stays 1 with an additive
optional field documented in audit-report-v1.schema.json.

## Bounded production and admission

Production requires ordinary ARM64 subtype 0/1, independent LC_FUNCTION_STARTS
boundaries, aligned executable file-backed bytes, a size of 3–16,384 instructions,
a supported agreement/inconsistency and a complete matching auditor instruction
count. Unsupported/unresolved results, shorter functions, partial counts and
unmapped data receive no annotation. Production trusts the existing auditor's
supported outcome; it does not independently re-decode or re-prove the body.

Only already-budgeted supported functions can receive fingerprints: no extra
functions are analyzed and no instruction/path budget is widened. Hashing is
bounded by those existing per-function/global analysis limits and the explicit
16,384-word fingerprint cap. Python admission checks the exact shape, kind,
digest syntax, count/size/alignment and architecture/provenance/verdict context.
Admission never verifies the imported digest against external bytes.

This increment is a Python API/CLI producer. The native FunctionInfo DTO does
not expose this optional field, and native preservation/export or GUI handling
is not claimed. Native callers keep the option disabled. Automatic cross-build
fingerprint matching and any native adoption need separate implementation and
qualification.

## Qualification

Five new producer methods pass: exact shape, immediate/order sensitivity,
address/name exclusion, short/partial/unresolved/boundary/cap refusal, and
architecture/mapping/executable/zero-fill boundaries. The preimplementation case
failed because the producer module did not yet exist.

Four new synthetic admission methods pass: round-trip, malformed fields,
count/context contradictions and unchanged comparison semantics/input objects.
These digest-shaped fields are explicit placeholders, not provenance hashes.

Three emission methods first qualify three distinct new complete Mach-O inputs.
They use different finalized instruction bytes from accepted images and refuse
existing source/output paths before audit. Default output omits fingerprints;
real isolated CLI opt-in emits one supported body while withholding the two-word
sink; unknown recovery remains unresolved without a fingerprint or checked PCs.
The original supported BL PC stays 0x10000101c, two-function denominator and
agreement scope remain intact. Reports round-trip through Python admission.
Source/report evidence is retained under local-evidence/body-fingerprint-v1.
No accepted source was re-audited or rehashed for these checks.

Fourteen affected manual API/CLI methods pass after the shared codec and CLI
changes. Other accepted analysis, native and release results are reused.
Independent read-only source review found no actionable semantic defect and
confirmed the distinction between auditor-derived evidence and independent
re-proof. The reviewer ran no tests, builds, hashes, writes or target code.

Native compilation is unchanged; no build/GUI run was required. No installed app,
settings or stores were changed. No package, release, installation, corpus or
MacScope mutation is included. Target instructions were never executed.
