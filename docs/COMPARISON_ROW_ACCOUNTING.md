# Native comparison row accounting

Baseline: public main dd0e771, manual-pair change verification merged in public PR3.
This bounded increment adapts the separation of matches, added/removed endpoints
and unresolved groups in MacScope FunctionVersionMatchResult to AIRS's existing
Python diff row/count contract. It imports no donor framework and makes no
MacScope changes. Schema 1, engine model v50 and matching behavior stay unchanged.

## Explicit API and row rules

ComparisonReport.validateRowAccounting() checks an already decoded comparison.
It is opt-in: ComparisonReport.decode and native app workflows are unchanged.
No source report, image, path, store or original binary is read or authenticated.

At most 100,000 rows are accepted, consistent with at most 50,000 findings in each
source report. Row keys must be nonempty and unique by exact UTF-8 bytes. Every
selected endpoint must have a lowercase AIRS finding ID. Each baseline endpoint
and each current endpoint can occur in at most one row. Uniqueness is side-local:
the same ID may occur once on both sides, as needed for exact-image comparisons.

A selected endpoint requires its typed verdict and nonempty scope facts. An absent
endpoint cannot carry typed verdict/scope facts. Existing optional decoding treats
missing and null values alike; this is a typed-presence check, not a claim about
literal JSON key presence or independent truth of those facts.

| Change category | Selected endpoints | Count contribution |
| --- | --- | --- |
| changed | Both | changed and matched |
| unchanged | Both | unchanged and matched |
| added | Current only | added |
| removed | Baseline only | removed |
| ambiguous | Zero, one or both | ambiguous; matched only if both |

One-to-one model/configuration-incompatible rows therefore remain matched pairs
classified ambiguous. Duplicate-symbol candidate groups with zero or one selected
endpoint do not invent a pair. Unknown change categories reject because they
cannot be counted. Unknown matching-basis strings remain preserved; accounting
does not establish that their matching procedure is valid.

All six declared summary counts must equal their observed counts. Computation
is bounded and never sums untrusted declared integer values, so very large counts
reject without overflow. Empty row lists require zero counts. Row/key/endpoint
passes use bounded linear lookup work; no comparison content is mutated.

## Deliberately narrow result

Success establishes internal row accounting only. IDs are not bound to source
findings by this API, missing source findings are not discovered, candidate-group
membership is not authenticated, match-basis semantics are not recomputed, and
changed/unchanged signatures are not verified. Nonnegative, well-accounted rows
can still contain false source facts or matches. Callers must retain the separate
source, compatibility and signature checks before making any stronger claim.

There is no readiness token, automatic import-policy change, matching activation,
GUI change, supported-instruction extension or binary correctness claim. The
existing source/signature helpers also do not silently invoke this new validator.

## Qualification

Thirteen new ComparisonRowAccountingTests methods passed with zero failures in
the initial class run. Two negative tests were then strengthened so their counts
were otherwise consistent and rejection isolated the category/fact rules. Only
those two changed methods ran again and passed; the other eleven were reused.
The first preimplementation compile reported the expected missing API and ran
no runtime test method.

Coverage includes empty/mixed categories, selected versus unselected ambiguity,
each summary field, Int.max declarations, invalid category shapes, duplicate and
malformed IDs, duplicate/empty/exact-Unicode keys, same-ID cross-side use,
missing/null/empty side facts, unknown match-basis preservation and the row cap.
The cap test uses an in-memory array of repeated synthetic rows and checks early
refusal; it is not a binary corpus or prevalence scan. All other inputs are small
synthetic comparison JSON with placeholder image digests.

The real AIRSApp debug product built successfully in 22.63 seconds under the
exclusive native gate. Independent read-only source/test review found no
additional actionable issue. Detailed logs are retained privately; generated
native build products are removed after qualification. Build success is not GUI
or installed-app acceptance.

Accepted manual change, compatibility, endpoint, codec, Python comparison, GUI
and distribution results are reused within their original scopes. No packaging,
signing, installation, publication or MacScope mutation is claimed by this local
increment. Installed app, settings and stores remain unchanged. Public integration
is a separate action.
