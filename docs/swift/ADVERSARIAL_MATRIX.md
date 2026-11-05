# Assignment acceptance matrix

The entries map required cases to focused methods or reused historical controls.
No synthetic check establishes broad compiler coverage. No unchanged historical
suite was rerun for this matrix.

| Cases | Evidence |
|---|---|
|1–6 exact/unsupported/length/size/substitution/suffix|test_swift_methods parser tests; retained legacy grammar controls|
|7–10 aliases/visibility/executable/entry/thunk|test_swift_methods and reused test_swift_error_flow attribution/boundary controls|
|11 valid direct call/test|test_swift_outcome_witness.test_positive|
|12–16 polarity/call/branch/callee/slice|test_mutation_matrix; test_interval_and_graph; source-backed record checks|
|17–18 interval PC/word|test_interval_and_graph; retained-proof/target regressions|
|19–21 incomplete scan/direct side entry/unknown entry|test_incomplete_unknown_and_side_entry; test_interval_and_graph|
|22 conflicting values|test_value_and_choice_coordinated_mutation|
|23 shared epilogue|test_interval_and_graph; test_coordinated_skipping_arm_fallthrough_is_refused|
|24 return-choice mismatch|test_value_and_choice_coordinated_mutation; test_interval_and_graph|
|25 unproven call return|positive witness retains call_return_proven:false; retained-proof regression rejects promotion|
|26 truncated retained details|test_interval_and_graph; malformed nested/empty interval regression|
|27 work/storage exhaustion|test_budgets_and_malformed; coordinator aggregate budget test|
|28 deterministic output|test_deterministic_and_immutable; bounded sorted serialization|
|29 default equivalence|test_swift_witness_integration default field equality;27 affected CLI/text checks|
|30 historical compatibility|unchanged v37/v45 assertions in affected checks; existing audit registry reused|

Two independent reviews additionally exercised source-level coordinated-evidence
attacks and prompted focused regression corrections. Unsupported arithmetic and
nonqualified tails return unresolved rather than gaining eligibility.
