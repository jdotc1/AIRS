# Comparison schema vocabulary alignment

The v1 baseline-diff schema and its generator now describe all four supported
matching policies and all five matching bases emitted by the producer, including
manual review and exact-body candidates. Previously the schema rejected those
valid outputs despite support in the engine and native decoder.

Optional `exact_body_candidates` metadata must be Boolean when present. Optional
`manual_pairs` metadata must be an array of at most 50,000 exact two-field objects.
Each endpoint uses the host's 70-character lowercase AIRS ID shape; exact length
also rejects trailing newlines that some regular-expression engines allow before
an end anchor. Missing optional metadata remains valid for historical reports.

This is structural schema alignment. It does not establish endpoint bijection,
source membership, flag/policy consistency, group coverage, fingerprint authenticity
or function identity. Those remain explicit native validation boundaries. Other
schema contracts and bounds, matching defaults, model/schema versions and GUI
activation are unchanged. Only the changed baseline-diff contract is regenerated.

The focused development test uses `jsonschema` when already available and reports
an explicit skip otherwise. This adds no core/runtime dependency or dependency
manifest requirement. Actual qualification must distinguish executed validation
from skipped checks.

## Qualification

All 14 focused methods executed with the available Draft 2020-12 validator and
passed with zero skips, covering current producer variants, legacy absence,
malformed metadata/pairs, exact ID text, collection bounds and schema validity.
Independent review found no actionable defect. Only baseline-diff was regenerated;
accepted native/runtime evidence is reused for unchanged runtime inputs. No fresh
native build or GUI acceptance is claimed.
