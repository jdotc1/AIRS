# Exact model-admission registry hardening

The Python and native report validators previously repeated the same historical
model identities in three membership lists each. Future additions could omit a
validation path and accidentally use generic import rules for a recognized model.
Each language now maintains one immutable explicit CFG identity set, with known
and evaluated-CFI sets derived by adding the exact historical linear identities.

The current CFG label count is asserted by the registry tests (49 at the imports admission change). The count below describes its historical checkpoint.

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


## Broad Swift model/profile pairs

Broad Swift admission uses a separate exact-pair registry:

| Model | Profile |
|---|---|
| `swift-broad-error-flow-v1` | `broad-v1` |
| `swift-broad-error-flow-large-v1` | `broad-large-v1` |
| `swift-broad-error-flow-extended-v1` | `broad-extended-v1` |
| `swift-broad-error-flow-imports-v1` | `broad-imports-v1` |

No prefix or version range grants admission. Mismatched known model/profile
pairs remain unsupported raw evidence. Imports require callsite model
`swift-broad-import-callsite-v1` and stub model
`arm64-import-stub-double-binding-v1`; import rows remain unresolved attribution
only. The recognized declaration syntax is `swift-import-declaration-syntax-v1`;
other syntax strings retain raw evidence without a throwing interpretation.
Unknown stub models in the exact imports pair refuse.

`tests/test_swift_broad_native_parity.py` pins the Python/native pairs and import
model/count literals. Native report and workspace tests cover admission,
refusals and requested-model pinning. These broad identities do not alter the
CFG identity registry or historical audit admission.
