# Track A independent review — round 1

Scope: read-only adversarial source review of acquisition, strict manifests and
independent raw oracle. No reviewer tests, corpus scans, hashes, builds or app
execution. Baseline: Track A after `cd28aa3`; corrections are in subsequent Track
A commits. This review is distinct from the original delta feature reviews.

| Priority | Falsifying scenario | Correction | Execution evidence |
| --- | --- | --- | --- |
| High | Binary plist dictionary references a later out-of-range key object; raw indexing escapes as IndexError | Validate every offset before following references | Owned mutation 039; 40-case run passed |
| High | Invalid and valid duplicate LC_CODE_SIGNATURE commands overwrite unavailable with observed | Count every signature command independently of region validity | New duplicate-command RED/GREEN |
| High | Wrong XML blob magic, duplicate slot types or overlapping slots supply observed entitlements | Require XML magic, unique slot identities and disjoint bounded ranges | New slot-identity RED/GREEN |
| Medium | Stale or oversized reads consume bytes without charging work | Charge each chunk before freshness/result validation | Failed stale-read fixture passed |
| Medium | listdir materializes an unlimited population before checking count | Bounded scandir retains only the allowance plus sentinel | Owned mutation 040 stops at four consumed entries for allowance three |
| Medium | Bare facts/refusals or unsupported adjudicated claims pass manifest admission | Require source, side, archive digest, locator, typed value/state and adjudicator | Four owned RED cases; 40-case GREEN; structured positive GREEN |

Repair review found three further typed-fact admission gaps: non-string tags could
raise TypeError, real/date bits allowed nonfinite values, and data allowed
noncanonical base64. All received classified rejection and one new four-variant
RED/GREEN fixture. Empty strings remain valid typed values (positive RED/GREEN).
The DER slot constant is 7, per Apple's public XNU cs_blobs.h; DER semantics remain
unexamined. Raw plist integer facts disclose unspecified API representation.

A separate owned archive mutation exposed an unclassified BoundReviewError for a
Boolean schema version. The production delta boundary now translates that invalid
input to `invalid_review`, after preserving cancellation and precise existing
refusals. The independent reviewer accepted this narrow mapping on source review.
Seventeen owned archive mutations and seventeen authentic-archive mutations then
refused; the real case was Pearcleaner 5.4.0 → 5.4.1.

Apple display-tool reads are supplementary pathname observations. They are not
freshness-bound to the descriptor capture and do not establish source-bound
acceptance, trust, signature validity or runtime behavior. Original raw captures
remain preserved. The evaluator checks retained command/slot metadata before using
pre-repair signature facts; it does not re-read unchanged source bytes to do so.

Local receipt names: A3-review-signature-red/green, A7-owned-mutations-red/green,
A1-fact-positive-red/green, A1-fact-types-red/green, A3-failed-work-green,
A5-owned-tamper(-green), A5-authentic-tamper. No native UI acceptance follows from
this source review.

## Final unavailable-source correction

A new owned fixture demonstrated that a fresh naked helper with unavailable Info
was mislabeled `source_stale`. The capture operation now returns
`source_unavailable` when there are no usable captured Info bytes. Usable prior
bytes still receive pre/post comparison and a mismatch remains `source_stale`.
The independent reviewer accepted this narrow distinction; historical archives
and model/schema meanings are preserved. A reader trap proves the unavailable
path exits before entitlement reading. The new case and affected existing
changed-Info regression passed. Four previously unexamined authentic helper
sources received first explicit capture outcomes, all unavailable, in 1.424 s;
these are separate captures with new inventory identities, not modifications of
the 35 original reports or additional release pairs.

The optional reproduction orchestrator received source review. A valid but
unsupported x86_64 selection initially refused after acquisition; preflight now
refuses before network/output creation. A new owned RED/GREEN fixture asserts
both boundaries. The orchestrator's owned end-to-end fixture exercises actual
bounded extraction/raw capture with a mocked public network source. Authentic
redownload through this new wrapper was not run; the original 47 acquisition
receipts are reused.
