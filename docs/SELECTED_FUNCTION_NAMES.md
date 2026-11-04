# Selected function-name binding

`ComparisonReport.validateSelectedFunctionNames(baselineData:currentData:)` is an
explicit native validation API for recorded `function_name` presentation facts on
rows with selected endpoints. It composes canonical manual keys and all earlier
declared-row checks. Comparison production, generic decoding and UI behavior are
unchanged.

## Source representative

The host producer uses the selected current finding when one exists, otherwise
the selected baseline finding. A selected current ID therefore has precedence
even for renamed manual/body pairs, incompatible observations or same-image rows.
A baseline-only ambiguity row uses its selected baseline singleton rather than an
unselected member of the current multi-candidate group.

The recorded label must match the admitted source finding's name by exact UTF-8
bytes. Empty and generated names remain exact source facts. Case folding,
whitespace trimming, Unicode normalization, image display names, row keys and
address/display-name fallbacks cannot substitute for the source value. Missing
lookups or names fail closed; native source admission remains unchanged.

## Limits

Rows with neither endpoint selected retain an explicitly unverified label. The
producer chooses a group representative in that case; reconstructing that choice
is outside this increment. Empty or partial comparisons still do not establish
source completeness, and notes/other presentation fields keep their existing scope.

A source-name match is presentation consistency with the selected saved report,
not authenticated binary-symbol evidence, cross-build identity, regression/fix
proof or widened analysis coverage. Earlier validation APIs keep their documented
name-label boundary. No GUI matching, packaging, installation or release acceptance
is implied.


## Bounded qualification

The real AIRSApp target built successfully, and sixteen new focused native tests
passed with zero failures. Independent test/scope and production-code review found
no actionable defect. Cases include side-specific lookup when IDs are equal across
sources, renamed manual/body pairs, one-sided ambiguity and exact wire-name facts.
All composed validators are unchanged; accepted source/accounting/manual/symbol/
body/unmatched/policy/key/offset/codec, Python, GUI and distribution results are
reused within their original scope. Detailed logs remain local. No packaging,
installation, GUI or new release qualification is claimed.
