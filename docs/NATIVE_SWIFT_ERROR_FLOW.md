# Native Swift Error Flow workspace

The Swift Error Flow workspace presents the bounded synchronous Swift analysis
through the existing owned engine subprocess. Method recognition and outcome
witnesses are separate opt-ins, initially off. Witness analysis explicitly supplies
the structured presentation, error-region and caller-entry prerequisites.

The Standard Swift profile retains the qualified ordinary, non-generic, synchronous
untyped-throws struct instance methods with Int-to-Int signatures, direct calls and
exact admitted symbols/function entries. Broad Swift selects the separately qualified
`broad-v1` profile, including its required witnesses, region/entry and structured
presentation flags. Its qualified free, struct, enum, direct final-class, static,
extension and concrete-generic families retain their exact ABI/callsite admission
boundaries; unsupported forms remain refused or unresolved. Standard opt-ins are
preserved when changing profiles and are never passed to broad-v1.
AIRS does not execute selected binaries.

An eligible witness describes independently checked bounded structural facts.
It does not prove runtime reachability, call return, exclusive handler entry,
catch types or reconstructed source. Unknown instructions, incomplete scans,
resource exhaustion and omitted details remain visible.

Saved JSON reports preserve original bytes for export and are historical recorded
evidence. Native decoding checks shape, bounds, identity fields and supported model
profiles; it does not reread or authenticate the source image. Recorded validator
eligibility must never be presented as a new byte check at import time.

Changing input/options invalidates current-result authority. A pending job owns its
cancellation lifecycle until completion; stale completions cannot replace newer
workspace state. Export uses protected atomic writes and must preserve an existing
destination on refusal or failure. Imported reports restore no live read authority.

This native integration changes neither the Python analysis models nor existing
component-security semantics. Engine/compiler qualification receipts are reused;
new native build, tests and runtime observations are recorded separately.


## Broad native workflow

Select **Broad Swift · broad-v1** in the analysis-profile picker, select an owned
binary or app, then choose Analyze. Selection alone starts no read. The existing
single owned subprocess executes the accepted broad coordinator; the native
adapter never reruns byte validation or upgrades a producer candidate.

Broad reports retain their distinct identity envelope, model registry and
candidate/independent-validator records. The view shows admitted declaration/ABI
states, independent fact statuses, refusal reasons, exact slice coordinates,
work/completeness/omission counts and original per-call evidence. Calls page in
sets of 200 across all 4,096 retained rows; evidence pages expose every retained
JSON character in 16,000-character segments. Export retains the original report
bytes. Pagination is presentation only, not output truncation.

The analysis-profile picker offers these profiles, each mapped to one engine argument and
report model:

| Picker entry | Engine argument | Report model |
| --- | --- | --- |
| Standard Swift · v37/v38 | none | `swift-sync-error-edges-v37`/`v38` |
| Broad Swift · broad-v1 | `broad-v1` | `swift-broad-error-flow-v1` |
| Broad Swift · larger function inventory | `broad-large-v1` | `swift-broad-error-flow-large-v1` |
| Broad Swift · extended scan | `broad-extended-v1` | `swift-broad-error-flow-extended-v1` |
| Broad Swift · extended + caller error tests (v2) | `broad-extended-v2` | `swift-broad-error-flow-extended-v2` |
| Broad Swift · v2 + indirect targets and value witnesses (v3) | `broad-extended-v3` | `swift-broad-error-flow-extended-v3` |
| Broad Swift · imported callees (attribution only) | `broad-imports-v1` | `swift-broad-error-flow-imports-v1` |

The v2 and v3 entries use the extended limits (9,216 functions, 2,097,152 scanned words, 8,192
retained calls). v2 records, for each retained imported-call row, what the caller did around the
call; that is a fact about the caller and says nothing about whether the callee throws. v3 adds
indirect-target shape and value-witness admission records; an admitted value-witness call stays
declined as `value_witness_abi_nonthrowing`, with no claim about callee behavior. See
[the imported-callee profile](SWIFT_BROAD_IMPORTS_PROFILE.md). A run whose engine response names a
different model than the selected profile is refused, and a saved report reopens under the entry
that matches its model.

The engine's existing 8 MiB image, 16 MiB report and other work ceilings remain
unchanged. Native shape admission also bounds depth, nodes, strings, row payloads,
model combinations, duplicate keys and exact identity links. Saved validator
outcomes are recorded assertions, never new source-byte checks or runtime proof.
Malformed bindings refuse; unknown model combinations retain bounded raw evidence
without semantic interpretation. Resource refusals and incomplete scans remain
visible. Changing profiles invalidates current-result authority; cancelled or
superseded jobs cannot publish a current report. Historical imports select the
report's profile for inspection and do not select or reopen a source image.
