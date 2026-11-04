# Canonical declared comparison-row order

The opt-in `ComparisonReport.validateCanonicalRowOrder(baselineData:currentData:)`
composes all existing declared-row and representative-name checks, then requires
strict ascending raw UTF-8 lexical order of adjacent complete row keys. For valid
Unicode strings this matches the producer's Unicode scalar sorting. The validator
does not sort, normalize, case-fold or interpret numeric substrings.

This preserves distinctions among canonical-equivalent spellings and follows key
order rather than numeric address, display-name, source-array or UI sort order.
Existing source admission, matching policy, endpoint and name proofs remain
prerequisites. Empty, singleton and ordered partial comparisons remain allowed.

Success establishes canonical order of declared rows, not complete producer
output, source identity, authenticated symbols or source-order authenticity.
Earlier validation APIs, decoding, matching defaults and GUI behavior retain their
existing scope. No new source decoding is added beyond the composed boundary.

## Qualification

The real AIRSApp target built successfully. All 16 focused tests passed, covering
empty/singleton/partial comparisons, source-order independence, reversed rows,
case/punctuation/prefixes, numeric-looking names and offsets, exact Unicode
spellings and supplementary scalars, inherited name/key failures, earlier API
scope, and mixed matching bases. Independent review found no actionable defect.
This establishes source/unit behavior, not GUI acceptance.
