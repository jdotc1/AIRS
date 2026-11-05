> Historical component milestone. Final composed qualification and current limits are recorded in docs/swift/BROAD_QUALIFICATION.md; earlier corpus counts are not additive.

# Broad Swift profile scope

## B1 model version firewall

The default CLI profile remains absent (`None`). Its historical edge model
`swift-sync-error-edges-v37` and return choice `swift-return-choice-v45` retain
their existing meaning. `--include-swift-methods` remains the separate historical
v38/v46 opt-in. Both retain outcome witness v1 and validation v1.

`--swift-profile broad-v1` selects an independent dispatcher and registers
`swift-broad-error-flow-v1`, `swift-outcome-witness-v2`, and
`swift-outcome-validation-v2`. Registration does not establish implementation
or qualification. No broad return-choice model is assigned by the firewall.

The broad profile requires `--include-outcome-witnesses`,
`--include-error-regions`, `--validate-region-entries`, and
`--include-structured-presentation`. It rejects `--include-swift-methods`.
Malformed combinations fail before input resolution or reading. Broad text
rendering currently refuses explicitly before input resolution. The independent
pipeline currently returns a structured `swift_broad_pipeline_pending` error;
it must not relabel a historical recognizer report as broad evidence.

The frozen original input and JSON/text captures in
`fixtures/swift-error-flow/broad-goldens` establish the historical behavior.
Reuse their existing manifest as provenance; do not regenerate or rehash it.
Focused B1 tests compare historical output bytes and exercise profile isolation.
The existing full Python baseline receipt remains
`local-evidence/swift-broad/baseline-python.log`; B1 does not repeat that suite.

B1 is only the model boundary. Broad pipeline, renderer, witness validator,
family coverage, corpus gates, and final qualification remain outstanding.
