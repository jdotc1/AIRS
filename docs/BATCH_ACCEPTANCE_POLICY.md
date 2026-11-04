# Batch acceptance policy provenance

The immutable `BatchComparisonResult.acceptancePolicy` records the policy
requested for that runner result. Strict results export
`comparison_acceptance_policy: saved_report_group_coverage`; legacy results omit
this new field to preserve their existing wire shape. Existing four-label result
construction defaults to legacy identity-only acceptance, and runner constructors
retain their behavior.

The runner sets policy before its first progress snapshot. It remains present
through successful, refused, cancelled and unpaired outcomes. The exported policy
is not a certificate that every row succeeded: row state and accepted payload
presence remain authoritative, including a strict batch where every row refuses.
Export serializes the recorded policy without replaying source validation.

This metadata is not portable proof or authentication, including for manually
constructed results. It does not establish original-binary completeness, function
identity or GUI acceptance. The GUI remains on its existing legacy policy;
matching, source admission, cancellation and installed data are unchanged.

## Qualification

The real AIRSApp target built successfully. All six focused methods passed,
covering strict success, legacy omission, all-refused output, cancellation,
unpaired initial/final progress and existing four-label construction. Independent
review found no actionable defect. Accepted matching/coverage and GUI evidence
is reused within its original scope; no GUI activation or revalidation on export
is introduced.
