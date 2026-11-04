# Recorded matching-policy validation

`ComparisonReport.validateMatchingPolicy(baselineData:currentData:)` is an explicit
native check of recorded producer-policy metadata and supported matching-basis
names. It composes unmatched-row and all prior declared-row validation. It does
not change generic decoding, matching production, engine semantics or GUI behavior.

## Canonical policy metadata

The host producer records policy from validated manual selections and explicit
body-matching opt-in:

| Validated manual pairs | Explicit body status | Required policy |
| --- | --- | --- |
| Missing or empty | Missing or false | `exact_digest_then_unique_symbol` |
| Nonempty | Missing or false | `manual_then_unique_symbol` |
| Missing or empty | True | `exact_digest_then_unique_symbol_then_exact_body_candidate` |
| Nonempty | True | `manual_then_unique_symbol_then_exact_body_candidate` |

The policy uses exact UTF-8 spelling. Key presence alone cannot imply manual
selection: an explicitly empty pair list retains the ordinary policy. Likewise,
a manual-looking row cannot supply missing validated selection metadata.

Missing body status remains unavailable. The unsuffixed spelling does not invent
false status; composed row checks still refuse outcomes whose presence depends
on that unavailable option. A body suffix cannot replace missing explicit status.
Explicit true records opt-in even when same-image authority or CPU-subtype gating
prevents the body phase from selecting any pair.

## Supported basis vocabulary

This API accepts only `exact_image_offset`, `manual_review`, `unique_symbol`,
`exact_body_candidate` and `unmatched` row bases. Unknown, empty or differently
spelled bases reject rather than borrowing the assurance of composed checks that
were not written for them. Existing generic decoding remains forward-compatible;
this stricter boundary is an explicit caller choice.

## Limits

Success establishes recorded-policy consistency and the evidence covered by the
composed validators. It does not reconstruct complete producer output or verify
every producer field, display label, note or manual-key spelling. Empty/partial
comparisons can remain valid; omitted groups do not establish source completeness.
Imported fingerprints remain unauthenticated review evidence, and no matching
basis proves source-function identity or a regression/fix.

Accepted source and runtime results keep their original scope. New native checks
and the real AIRSApp build qualify this boundary separately from GUI activation,
packaging, installation and release acceptance.


## Bounded qualification

The real AIRSApp target built successfully, and sixteen new focused native tests
passed with zero failures. Independent code/test/scope review found no actionable
defect. All composed validators are unchanged; accepted source/accounting/manual/
symbol/body/unmatched/offset/codec, Python, GUI and distribution results are reused
within their original scope. Detailed logs remain local. No packaging, installation,
GUI or new release qualification is claimed.
