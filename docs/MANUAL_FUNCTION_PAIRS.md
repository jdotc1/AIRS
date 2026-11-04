# Manual finding pairs for saved-report comparison

Baseline: public main cffb0a6, generated-symbol guard merged in PR34 using the
accepted GENERATED_SYMBOL_MATCHING.md results. This bounded increment adapts
MacScope FunctionVersionMatcher.validatedPins and its one-to-one manual-pin
precedence. The donor is read-only. No framework, native lifecycle or automatic
fingerprint matching is imported.

## Use

The Python API adds an optional keyword argument:

```python
compare_reports(baseline, current, manual_pairs=[(baseline_id, current_id)])
```

The isolated CLI adds a repeatable flag:

```sh
python3 airs_cli.py diff --baseline before.audit.json --current after.audit.json \
  --pair "$BASELINE_FINDING_ID=$CURRENT_FINDING_ID" --format text
```

Set the two variables to actual complete finding IDs from the respective saved
reports. The command reads saved reports and does not analyze a binary. JSON is
the default output; text output retains IDs, manual basis and review limitations.
Existing output protection prevents replacing input reports.

## Contract

Inputs must pass existing report validation first. Every pair identifies an
existing baseline finding and an existing current finding. At most 50,000 raw
pair entries are accepted. Identical pairs deduplicate; endpoint conflicts and
malformed/unknown pairs fail with invalid_manual_pair. Canonical pairs sort by
baseline/current ID. Neither report is modified.

Manual pairs precede automatic symbol grouping and consume each endpoint once.
Remaining findings retain unique eligible-symbol matching and duplicate ambiguity.
Exact-image offset authority cannot be overridden: nonempty pairs for the same
selected-slice digest and architecture are rejected. Same-image comparisons must
use automatic offsets. Empty pairs preserve the previous output shape/policy.

For nonempty pairs, comparison.manual_pairs records the canonical selected IDs,
matching_policy is manual_then_unique_symbol and paired rows have match_basis
manual_review. Their notes explicitly say user selection does not prove source
function identity or a regression/fix. Existing selected-image context and row
IDs bind the result to the supplied saved reports, without authenticating them.
Architecture, analysis-model or configuration differences still yield ambiguous
paired outcomes. No pin can turn incompatible evidence into a supported change.

Schema stays 1; these are additive comparison fields/string values, not a new
analysis model. Engine remains arm64-bounded-test-bit-branch-v50. No GUI pin editor,
body/CFG fingerprint producer, structural matching or call-graph propagation is
included. The current native decoder accepts string match bases; native/GUI
acceptance of this workflow is not claimed by the CLI qualification.

## Qualification

Nine new synthetic API methods pass: explicit stripped/renamed pairing, canonical
deduplication, unknown/conflicting endpoints, malformed shapes/types, raw cap,
exact-image authority, model/architecture/configuration ambiguity, manual-before-
symbol precedence, report preservation and empty-pair compatibility. The first
preimplementation case failed because manual_pairs was not yet accepted.

Five new real isolated-bootstrap methods pass on fresh synthetic report files:
JSON pair recording, text basis/IDs/review limitation, structured malformed and
unknown-ID errors with no partial report, and repeated identical flags. The
preimplementation CLI case failed with the intended unrecognized --pair error.
Temporary inputs live under local-evidence/manual-pair-cli and are removed by
each test. Original synthetic reports remain unchanged; no target is analyzed.

Eleven affected generated-symbol and comparison-boundary methods pass after the
shared comparison change. Other accepted results are reused; no sealed source,
image, export or provenance hash is reverified. Independent read-only API and
CLI reviews found no actionable defect and ran no tests/builds/hashes/writes.

Native compilation/UI are unaffected and no new native build/launch was required.
Installed app, settings and stores are unchanged. No package, signing,
notarization, release, installation, corpus or donor modification is included.
