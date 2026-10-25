# Opt-in exact-body review candidates

Baseline: public main bf1e3c8, fingerprint producer merged in PR36 with accepted
FUNCTION_BODY_FINGERPRINTS.md results reused. This bounded phase adapts MacScope
FunctionVersionMatcher.applyUniqueKeyPhase: count one snapshot of unmatched keys,
accept only one candidate on each side, and never guess ties. MacScope is read-only.
AIRS uses its own saved-report contracts and exact-byte fingerprint kind.

## Use

```sh
python3 airs_cli.py diff --baseline baseline.audit.json --current current.audit.json \
  --match-exact-bodies --format text
```

Python: compare_reports(baseline, current, match_exact_bodies=True). The option
requires a boolean and defaults to False. It reads only saved reports and never
recomputes digests or audits source images. Reports without eligible fingerprints
continue through existing symbol/manual matching. Fingerprints require the separate
producer opt-in; historical reports do not gain invented body evidence.

## Selection and evidence

Exact-image offsets retain authority, even with this flag. For different images,
manual pairs and established unique-symbol pairs are reserved first. Ambiguous
symbol groups are not resolved by this increment. Candidate eligibility requires
a standalone unmatched finding on each side with the same admitted kind, SHA-256
and instruction count, and equal architecture/CPU subtype. All remaining body keys
are counted, including members of blocked ambiguous-symbol groups: blocked members
must not make an otherwise repeated fingerprint falsely appear unique.

Each eligible key must occur once on both remaining sides. Duplicate body evidence
selects no pair and adds a nonunique-body note while preserving original row/count
accounting. Accepted endpoints are consumed once. Output and pair selection are
deterministic and source reports are unchanged. One bounded snapshot phase is used;
there is no iterative fixpoint, call-graph propagation, CFG matching or automatic
resolution of duplicate-symbol ambiguity. Work is linear in findings plus the
existing output sort, within report-admission size/count limits.

Selected rows use match_basis exact_body_candidate, retain both finding IDs and
explicitly say the imported digest is unauthenticated review evidence. It does not
prove source-function identity or a regression/fix; relocation may change encoded
bytes. Existing model/configuration differences still yield ambiguous paired
outcomes. Body equality never overrides the finding signature or checked-PC changes.

When enabled, comparison.exact_body_candidates is True and matching_policy appends
_then_exact_body_candidate to its existing policy. matched_count includes these
review candidates, consistent with existing symbol/manual semantics. Off preserves
the previous wire shape and behavior. Schema remains 1 and analysis model remains
arm64-bounded-test-bit-branch-v50. No unwind findings, scope or checked PCs change.

## Qualification

Fourteen new API methods pass in composed runs: unique stripped/renamed pairing,
default off/missing/changed evidence, nonunique refusal, manual/symbol precedence,
exact-image authority, model/configuration ambiguity, CPU subtype mismatch,
retained duplicate-symbol ambiguity, option/type/admission boundaries, deterministic
order/input preservation, blocked-group duplicate accounting, instruction-count
mismatch and unchanged body evidence with changed checked-PC signature. The first
preimplementation case failed because the API keyword did not yet exist.

Four new real isolated CLI methods pass on fresh synthetic reports: JSON basis/IDs,
text review limitations, default-off output and manual precedence. The initial CLI
case failed with the intended unrecognized --match-exact-bodies error. Inputs are
preserved and temporary files are removed under local-evidence/exact-body-cli.

One first-run pipeline method qualifies two new complete owned Mach-O identities:
new instruction bytes and distinct UUIDs produce different slice IDs but equal
eligible body fingerprints. Each image is audited once. The result contains one
exact-body review candidate and leaves the two-word sink as added/removed. Original
preferred call PC 0x10000101c, function IDs and the two-function denominator remain
intact. Source reports and comparison are retained under exclusive
local-evidence/exact-body-candidates paths. No accepted image is re-audited,
rehashed or replayed. Target instructions are never executed.

Twenty-five affected manual API/CLI, generated-symbol and comparison-boundary
methods pass after shared comparison/CLI changes. Other accepted producer,
analysis/native/distribution results are reused. Independent read-only source and
CLI/pipeline review found no actionable defect and confirmed the added false-
uniqueness test. The reviewer ran no tests, builds, hashes, writes or target code.

## Remaining boundaries

This is Python API/CLI matching. Native-app activation, annotation preservation,
GUI controls and GUI acceptance remain separate work. Native compilation is
unchanged, so no build/launch was required. MacScope remained read-only. Installed
app, settings and stores are unchanged. No package, release, installation or corpus
work is included. Imported digest admission is structural, never authentication.
