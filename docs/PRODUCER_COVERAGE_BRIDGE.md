# Owned producer-to-native coverage controls

This bounded integration qualification connects the existing Python comparison
producer to the covered native decoder through the opt-in strict batch runner.
Eight new owned controls cover default disabled matching, body matching, manual
matching, manual-plus-body matching, both same-image option states, Unicode-distinct
symbols and duplicate body blockers.

The fixture stores the exact serialized baseline/current/comparison JSON strings
created from synthetic saved reports by the existing producer. Expected row counts,
bases and Boolean status are independently specified. The runner returns and retains
the stored output bytes directly; no second serialization is used as a byte oracle.
All digest/fingerprint values are synthetic placeholders, not authenticated evidence.

Two mutation controls preserve structural validity while omitting an eligible body
row or substituting a well-formed foreign manual endpoint. The omitted-row summary
is internally consistent, and the foreign pair's recorded key/endpoint fields agree.
Refusal therefore exercises group coverage or source binding, with no accepted
payload retained.

No target binary is read or executed. Existing synthetic report helpers and matching
code are reused; production matching, native acceptance policies, GUI activation and
installed data are unchanged. Qualification of these saved-report controls does not
prove analysis truth, original-binary completeness, identity, fingerprint authenticity,
packaged-engine transport or GUI acceptance.

## Qualification

All ten new native methods passed: eight producer-output controls plus two
structurally consistent mutation refusals. Independent review found no actionable
defect. The controls were generated once and no accepted fixture or unchanged
suite was replayed. The fresh evidence is test-target producer/covered-decoder/
strict-runner integration; accepted production-app/runtime evidence is reused.
No fresh production-app build, packaged transport or GUI acceptance is claimed.
