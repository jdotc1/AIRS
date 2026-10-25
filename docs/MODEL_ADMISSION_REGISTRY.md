# Exact model-admission registry hardening

The Python and native report validators previously repeated the same historical
model identities in three membership lists each. Future additions could omit a
validation path and accidentally use generic import rules for a recognized model.
Each language now maintains one immutable explicit CFG identity set, with known
and evaluated-CFI sets derived by adding the exact historical linear identities.

No prefix, version range or current-engine label determines admission. All 46 CFG
labels, including the distinct historical CFI-control v36 alias, retain their
previous policies. Linear v1/v2 differences and unknown-label generic validation
remain unchanged. Guard order, error messages, schema and model v47 are preserved.

Fresh bounded validation:

- Three new Python methods passed in 0.027 seconds: exact policy relationships,
  every CFG label's subtype and evaluated-CFI boundaries, and native label parity.
- The real AIRSApp debug target built successfully in 10.69 seconds. The build
  emitted an existing unnecessary-await diagnostic in entitlement extraction.
- Focused native registry tests cover historical policy sets and each CFG label's
  valid admission followed by capability-subtype refusal; both passed with zero failures in 0.022 seconds.
- Independent source review found no admission widening or historical-policy drift.

Accepted CLS v47 and earlier semantic, owned-image, GUI and distribution results
are reused. No corpus pass, app launch, packaging, signing, installation or release
was performed. Installed app, settings and stores were left unchanged.
