# Real-release component-security-delta qualification

## Scope and separation

Track A qualifies the existing AIRS pure component-security-delta analyzer and
archive boundary. It does not add default capture behavior, a trust verdict,
malware classification, a compliance assertion or MacScope integration. Build 26
remains the current release. The acquisition/oracle/evaluator are opt-in test
facilities; third-party application code is never executed or modified.

Targets: at least 24 authentic successive release pairs from 12 applications and
three independent publishers, with at least two predominantly Swift and two
Objective-C/mixed applications where independently evidenced. Seek 30–40 pairs
if legitimate releases permit. Count versions by archive digests and publisher
release identity, never duplicate re-zips. Forty owned negative cases remain a
separate denominator. At least 100 pure-analysis repetitions on a recorded
stratified subset use the same admitted capture; independent recapture is a
separate event and may have different UUIDs.

| Stratum | Minimum attempted distinct cases |
|---|---:|
| simple primary Mach-O | 6 |
| frameworks/dylibs | 6 |
| XPC/extension/helper/login item | 4 |
| universal/multiple slices | 4 |
| entitlement changes/unavailable source | 6 |
| privacy manifests present/absent/changed | 4 |
| loader changes | 4 |
| signature/source digests | 6 |

## Manifest v1 and admission

The JSON Schema describes the wire shape. The standard-library-only validator
also enforces exact keys, duplicate-key rejection, strict UTF-8, HTTPS URLs with
no credentials/query/fragment, ordered release timestamps, distinct source
SHA-256 values, expected-to-side digest binding, and exact safe relative paths.
It does not normalize Unicode. License provenance is mandatory for each source.
Pending expectations are permitted during acquisition, but never count as
independently adjudicated acceptance. JSON Schema shape validation alone cannot
prove authenticity, source truth or semantic side correspondence.

Ceilings: 256 cases, 256 KiB per manifest, 24 nested levels, 8192 structural
nodes, 4096 bytes per general string, 192 bytes per case/publisher/application
identity, 1024 expected facts/refusals, and eight distinct coverage tags. File
admission opens each directory component without following symlinks and reads
only bounded regular manifest files. These test-harness ceilings cannot raise
any production AIRS ceiling.

## Acquisition and evidence custody

Use canonical publisher/project release URLs and legitimate public downloads.
Retain acquisition dates, publisher version/release identities, license URLs,
archive bytes/digests, exact app path, and redirect/source records locally.
Downloads and extracted third-party payloads remain outside tracked source.
Only manifests, hashes, independently expected facts, owned fixtures, harness
code and sanitized results may be public. Never embed local absolute roots,
credentials, user files or third-party binaries in a public handback.

Each acquisition and capture is separately recorded; it is not an atomic app
snapshot. Reuse accepted immutable byte identities and verification receipts.
Do not silently recapture stale evidence or infer absence from symlink exclusion,
failed reads, unexamined sources or output truncation. The case evaluator must
include every refused/unsupported case in its denominator.

## Four independently assessed boundaries

1. Authorized capture reuses AIRS discovery, inventory, declaration, entitlement
   and signature admission. The analyzer acquires no filesystem authority.
2. Pure derivation compares admitted immutable captures with explicit architecture,
   direction and existing hard limits.
3. The oracle separately parses raw plist/Mach-O/signature material, records typed
   values and locators/ranges/digests, and supplements sampled facts with Apple
   tools. It never calls the AIRS analyzer, matcher or canonical serializer.
4. Historical replay imports the exact retained archive in a fresh invocation,
   rederives the report and compares supported identities, coverage and bytes.
   Native presentation cannot regain live authority from historical import.

Every certain observation/finding needs independent source-backed adjudication.
Unavailable evidence produces unresolved adjudication, not an inferred empty or
absent dictionary. Signed/unsigned/Boolean/historical integer distinctions,
array order, duplicated loader records and raw slice identity remain explicit.
No signature trust, runtime library loading or privacy compliance is inferred.

## Acceptance reporting

Report per-case category TP/FP/FN/unresolved counts, certain-findings denominator,
evidence-reference resolution, omissions, refusals, archive outcomes and native
workflow status. Record both numerator and denominator for every target. A
missing input, license, platform facility or permission is blocked/skipped with
a concrete reason, never a pass. Report requested versus achieved strata and
language provenance rather than attributing implementation language by name.
AIRS acceptance does not establish MacScope integration acceptance.

## Qualified corpus and conservative oracle boundaries

The acquired set contains 47 original releases and 35 successive pairs from 12
applications/10 publisher accounts. Every pair has a different recorded primary
container digest, establishing that none is merely a duplicate re-zip. Prereleases
retain their actual publisher tags. OverSight is the publisher's installer app,
inspected as data; it was not run or installed.

Predominant language is supported by publisher repository language byte counts and
corroborating raw section metadata. Swift metadata is not a measurement of the
percentage of runtime instructions, nor does Objective-C metadata exclude Swift.
At least Maccy/Ice and KeyCastr/KeepingYouAwake satisfy the requested two language
cohorts with those explicit evidentiary limits. Exact section-header offsets, raw
slice identities and range digests are retained in manifests/local evidence.

Version-1 qualification comparisons are arm64-only; unsupported x86_64 selection
refuses before acquisition. Universal inputs retain both raw slice identities.
Existing production APIs retain their supported architecture contract.

The raw oracle uses property-list integer values with representation unspecified;
it cannot prove Foundation API signedness. Python datetime conversion also cannot
prove original binary-plist submicrosecond date bits. The independent checker
therefore declines exact DateBits comparison; production strict DateBits encoding
is unchanged. No certain date-bit claim occurs in the accepted real corpus.

Source coverage includes all 300 image/candidate records across the 47 raw bundle
walks: 278 observed images and 22 unavailable candidates, subsequently unexamined
by the recorded-range reader. Excluded links/special files remain separate records.
A complete oracle enumeration is not a claim of complete AIRS conventional scope
or runtime coverage. AIRS's legacy any-exclusion absence refusal remains unchanged.

Six distinct cases exercise actual entitlement changes or first explicit unavailable
helper outcomes. Four helper eligibility refusals are separate fresh captures, with
new inventory UUIDs and no fabricated pairwise empty values. Their prior unexamined
records are preserved. Attempted strata and positive outcomes are reported separately.
