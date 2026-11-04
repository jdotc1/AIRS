# Explicit comparison body-option metadata

New producer reports always serialize the validated `exact_body_candidates`
Boolean, including false when the caller uses the existing default. This is an
additive metadata/wire-shape change. It records the option that governed comparison,
not fingerprint availability or whether the body phase found any pair.

True still appends the existing policy suffix and body limitations. False retains
the plain policy, disabled matching and existing limits. Same-image offset and
manual precedence remain unchanged. Non-Boolean arguments still refuse.

Explicit false allows new default cross-image reports to meet the covered native
decoder's option-presence prerequisite without inventing metadata. Historical
reports are not rewritten; missing status remains unavailable at strict cross-image
coverage. Generic decoding, schema/model versions, matching defaults and native
GUI paths retain their scope. This change does not activate covered decoding in
the app or establish binary authenticity, identity or runtime acceptance.

## Qualification

Eleven new metadata tests and two affected existing checks passed, including the
CLI default JSON path: 13 tests, zero failures. Independent review found no
actionable defect. Accepted native decoder/build evidence is reused for unchanged
native code. No new native runtime, packaged-engine or GUI acceptance is claimed.
