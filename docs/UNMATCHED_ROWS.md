# Declared unmatched-row validation

`ComparisonReport.validateUnmatchedRows(baselineData:currentData:)` is an explicit
native validation API for declared `unmatched` rows. It composes one-sided symbol,
duplicate-symbol, body-pair, unique-symbol, exact-offset, observation-label,
selected-source, accounting and manual-pair validation. Matching defaults,
comparison production and native workflows are unchanged.

## Side-specific source evidence

An unmatched row must select exactly one endpoint from its corresponding source:

- A baseline endpoint requires `unmatched:before:<baseline ID>` and `removed`.
- A current endpoint requires `unmatched:after:<current ID>` and `added`.

Keys retain their exact canonical bytes. The selected source finding must have
an unusable name under the existing host policy: empty, generic or generated
names provide no cross-image symbol evidence. Usable names cannot be relabelled
as unmatched merely because no symbol counterpart exists. Source admission is
unchanged; missing/null names are not newly admitted by this validator.

Validated manual-pair endpoints cannot appear as unmatched. Generated names do
not group together: even equal generated labels retain separate side-specific,
finding-specific unmatched keys. Added/removed means no accepted match in the
recorded phase, not a regression or fix.

## Body selection

The existing internal body-candidate projection is reused without changing its
selection policy. Sources and validated pins determine eligible pairs; imported
row omissions cannot restore consumed endpoints. Architecture and exact subtype
must permit the body phase. Model/configuration differences affect pair labels,
not whether body selection occurs.

Explicit false preserves unconsumed unmatched endpoints. Explicit true rejects
an endpoint consumed by an eligible body pair. Missing status remains unavailable:
when a possible eligible pair could consume the endpoint, validation refuses that
outcome. Otherwise the row is independent of that missing option and can be checked.
Fingerprint tuples remain unauthenticated imported review evidence.

## Scope and limits

Same-image rows retain exact-offset authority through composition. Empty or partial
comparisons do not establish source completeness. Other matching bases and display
prose remain outside this increment; existing validators retain their scope.
The API does not authenticate binary bytes, prove source-function identity,
change unwind findings or activate GUI matching. No packaging, installation,
GUI or release qualification follows from these report checks.


## Bounded qualification

The real AIRSApp target built successfully. Eighteen new focused native tests
passed with zero failures. Independent code, test and scope review found no
actionable defect. The shared body projection is unchanged; accepted prior
source/accounting/manual/symbol/body/offset/codec, Python, GUI and release results
are reused within their original scope. Detailed logs remain local.
