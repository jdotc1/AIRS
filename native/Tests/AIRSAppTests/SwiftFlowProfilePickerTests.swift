import XCTest
import AIRSCore
@testable import AIRSApp

final class SwiftFlowProfilePickerTests: XCTestCase {
    private func identity() -> [String: Any] {
        ["container_sha256": String(repeating: "a", count: 64), "slice_sha256": String(repeating: "b", count: 64),
         "architecture": "arm64", "cpu_subtype": 0, "uuid": NSNull(), "preferred_base": "0x1000", "slice_index": 0,
         "container_slice_count": 1, "slice_offset": "0x0", "slice_size": "0x1000"]
    }
    private func importCounts() -> [String: Any] {
        ["attributed_stubs": 0, "declined_stubs": 0, "invalid_stub_sections": 0, "selected_import_calls": 0,
         "non_throwing_swift_import_calls": 0, "non_swift_import_calls": 0, "declined_stub_calls": 0]
    }
    private func envelope(model: String, profile: String, row: [String: Any], status: String, reason: String,
                          limitations: [String]) -> [String: Any] {
        ["model_version": model, "profile": profile,
         "witness_model_version": "swift-outcome-witness-v2", "validation_model_version": "swift-outcome-validation-v2",
         "identity": identity(), "word_scan_complete": true, "call_details_complete": true,
         "outcome_witnesses_complete": true, "observed_call_instructions": 1, "selected_call_candidates": 1,
         "omitted_calls": 0, "scanned_words": 8, "analysis_work": 100, "research_only": true,
         "call_return_proven": false, "runtime_reachability_proven": false,
         "status_counts": [status: 1], "reason_counts": [reason: 1], "calls": [row], "limitations": limitations,
         "import_stub_model": "arm64-import-stub-double-binding-v1", "import_stubs_complete": true,
         "import_stub_reason": NSNull(), "import_stub_counts": importCounts()]
    }
    /// A saved broad-extended-v2 report: one imported-call row with a recorded caller-side error test.
    private func v2Report() -> [String: Any] {
        let fact: [String: Any] = [
            "model": "swift-caller-error-test-v1", "shape": "swifterror_idiom", "claims_callee_behaviour": false,
            "precall": ["status": "x21_zeroed", "zero_pc": "0x1000",
                        "window": [["pc": "0x1000", "word": "0xaa1f03f5", "kind": "mov"]]],
            "postcall": ["status": "recovered_candidate", "test_pc": "0x1008", "tested_register": "x21",
                         "success_pc": "0x100c", "error_pc": "0x1010",
                         "window": [["pc": "0x1008", "word": "0xb5000055", "kind": "xcbnz"]]]]
        let declaration: [String: Any] = ["status": "syntax_admitted", "reason": NSNull(),
            "identity": ["symbol": "$s5Owned4workyyKF", "throws": true, "syntax_model": "swift-import-declaration-syntax-v1"]]
        let admission: [String: Any] = ["model_version": "swift-broad-got-callsite-v1", "status": "unresolved",
            "reason": "imported_callee_abi_unqualified", "call_kind": "blr_got", "call_pc": 4100,
            "caller_start": 4096, "symbol": "$s5Owned4workyyKF", "declaration": declaration,
            "call_return_proven": false, "syntactic_call_target_admitted": false, "import_attribution_admitted": true]
        let row: [String: Any] = ["caller_pc": "0x1000", "call_pc": "0x1004", "admission": admission,
                                  "candidate": NSNull(), "validation": NSNull(), "caller_error_test": fact]
        var object = envelope(model: "swift-broad-error-flow-extended-v2", profile: "broad-extended-v2", row: row,
                              status: "unresolved", reason: "imported_callee_abi_unqualified",
                              limitations: ["structural_only", "imported_callees_attribution_only"])
        object["caller_error_test_counts"] = ["swifterror_idiom": 1]; object["caller_error_test_decline_counts"] = [:] as [String: Any]
        return object
    }
    /// A saved broad-extended-v3 report: one admitted value-witness site, declined as value_witness_abi_nonthrowing.
    private func v3Report() -> [String: Any] {
        let shape: [String: Any] = ["model": "swift-indirect-target-shape-v1", "site_pc": "0x100c", "site_kind": "blr",
            "class": "value_witness", "slot_offset": 8, "unknown_reason": NSNull(),
            "deciding_instructions": [["pc": "0x1000", "word": "0x94000005", "role": "metadata_call_result"],
                                      ["pc": "0x1004", "word": "0xf85f8008", "role": "table_load"],
                                      ["pc": "0x1008", "word": "0xf9400508", "role": "target_load"],
                                      ["pc": "0x100c", "word": "0xd63f0100", "role": "indirect_branch"]],
            "evidence": "table base loaded from [x0, #-8]", "class_before_join_refusal": NSNull(),
            "slot_address": NSNull(), "slot_section": NSNull(), "claims_callee_behaviour": false,
            "bounds": ["window_words": 256, "max_register_hops": 6, "max_function_words": 262144]]
        let witness: [String: Any] = ["model": "swift-value-witness-admission-v1", "admitted": true,
            "provenance_kind": "imported_metadata_accessor_call", "first_failing_condition": NSNull(),
            "reason": "meets_tier2_conditions", "site_pc": "0x100c", "site_kind": "blr", "slot_offset": 8,
            "metadata_register": "x0", "symbol": "_$sSS10FoundationE8EncodingVMa", "metadata_callee_pc": "0x1014",
            "claims_callee_behaviour": false, "abi_basis": "value_witness_function_slots_cannot_throw"]
        let admission: [String: Any] = ["model_version": "swift-broad-callsite-v1", "status": "declined",
            "reason": "value_witness_abi_nonthrowing", "call_pc": 4108, "details_complete": true]
        let row: [String: Any] = ["caller_pc": "0x1000", "call_pc": "0x100c", "admission": admission, "candidate": NSNull(),
                                  "validation": NSNull(), "indirect_target_shape": shape, "value_witness_admission": witness]
        var object = envelope(model: "swift-broad-error-flow-extended-v3", profile: "broad-extended-v3", row: row,
                              status: "declined", reason: "value_witness_abi_nonthrowing",
                              limitations: ["structural_only", "imported_callees_attribution_only",
                                            "indirect_target_shape_does_not_claim_callee_behaviour",
                                            "value_witness_admission_by_abi_with_recorded_provenance"])
        object["caller_error_test_counts"] = [:] as [String: Any]; object["caller_error_test_decline_counts"] = [:] as [String: Any]
        object["indirect_target_shape_model"] = "swift-indirect-target-shape-v1"
        object["value_witness_admission_model"] = "swift-value-witness-admission-v1"
        object["indirect_target_shape_counts"] = ["value_witness": 1]
        object["value_witness_admission_counts"] = ["admitted": 1, "refused": 0]
        object["value_witness_refusal_condition_counts"] = [:] as [String: Any]
        return object
    }
    private func data(_ object: [String: Any]) throws -> Data { try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys]) }
    /// A saved broad-extended-v1 report: one unresolved row with no caller-side or indirect-target records.
    private func v1Report() throws -> Data {
        let row: [String: Any] = ["caller_pc": "0x1000", "call_pc": "0x1004",
            "admission": ["status": "unresolved", "reason": "syntax_unqualified", "details_complete": true, "work_steps": 1, "call_return_proven": false],
            "candidate": NSNull(), "validation": NSNull()]
        return try data(["model_version": "swift-broad-error-flow-extended-v1", "profile": "broad-extended-v1",
            "witness_model_version": "swift-outcome-witness-v2", "validation_model_version": "swift-outcome-validation-v2",
            "identity": identity(), "word_scan_complete": true, "call_details_complete": true, "outcome_witnesses_complete": true,
            "observed_call_instructions": 1, "selected_call_candidates": 1, "omitted_calls": 0, "scanned_words": 1024, "analysis_work": 999,
            "calls": [row], "status_counts": ["unresolved": 1], "reason_counts": ["syntax_unqualified": 1], "research_only": true,
            "call_return_proven": false, "runtime_reachability_proven": false, "limitations": ["structural_only"]])
    }
    private var configuration: EngineConfiguration { .init(pythonExecutable: URL(fileURLWithPath: "/unused/python"), bootstrap: URL(fileURLWithPath: "/unused/bootstrap")) }
    private func saved(_ bytes: Data) throws -> URL {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("profile-picker-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let url = root.appendingPathComponent("report.json"); try bytes.write(to: url)
        addTeardownBlock { try? FileManager.default.removeItem(at: root) }
        return url
    }

    @MainActor func testSavedReportsReopenAsTheirOwnProfile() async throws {
        let v1 = try v1Report(), v2 = try data(v2Report()), v3 = try data(v3Report())
        for (bytes, expected, model) in [(v1, SwiftFlowProfile.broadExtended, "swift-broad-error-flow-extended-v1"),
                                         (v2, .broadExtendedV2, "swift-broad-error-flow-extended-v2"),
                                         (v3, .broadExtendedV3, "swift-broad-error-flow-extended-v3")] {
            let workspace = SwiftFlowWorkspace(execute: { _, _, _ in XCTFail("Historical import must not run the engine"); return Data() })
            workspace.importReport(try saved(bytes)); await workspace.waitUntilSettled()
            XCTAssertNil(workspace.errorMessage, model)
            XCTAssertEqual(workspace.report?.modelVersion, model)
            XCTAssertEqual(workspace.profile, expected, model)
            XCTAssertTrue(workspace.isHistorical); XCTAssertNil(workspace.input)
            XCTAssertEqual(workspace.report?.sourceData, bytes)
        }
    }

    @MainActor func testRunRoutesV2AndV3AndRejectsAnyOtherModel() async throws {
        let v1 = try v1Report(), v2 = try data(v2Report()), v3 = try data(v3Report())
        for (profile, matching, model) in [(SwiftFlowProfile.broadExtendedV2, v2, "swift-broad-error-flow-extended-v2"),
                                           (.broadExtendedV3, v3, "swift-broad-error-flow-extended-v3")] {
            let accepted = SwiftFlowWorkspace(execute: { _, options, _ in XCTAssertEqual(options.profile, profile); return matching })
            accepted.profile = profile; accepted.selectInput(URL(fileURLWithPath: "/owned/input")); accepted.run(configuration: configuration)
            await accepted.waitUntilSettled()
            XCTAssertNil(accepted.errorMessage, model); XCTAssertFalse(accepted.isHistorical)
            XCTAssertEqual(accepted.report?.modelVersion, model)
            for wrong in [v1, v2, v3] where wrong != matching {
                let rejected = SwiftFlowWorkspace(execute: { _, _, _ in wrong })
                rejected.profile = profile; rejected.selectInput(URL(fileURLWithPath: "/owned/input")); rejected.run(configuration: configuration)
                await rejected.waitUntilSettled()
                XCTAssertNil(rejected.report, model); XCTAssertNotNil(rejected.errorMessage, model); XCTAssertTrue(rejected.isHistorical)
            }
        }
    }

    @MainActor func testStandardAndOlderBroadRunsRejectV2AndV3Responses() async throws {
        let v2 = try data(v2Report()), v3 = try data(v3Report())
        for profile in [SwiftFlowProfile.standard, .broadExtended, .broadImports] {
            for wrong in [v2, v3] {
                let rejected = SwiftFlowWorkspace(execute: { _, _, _ in wrong })
                rejected.profile = profile; rejected.selectInput(URL(fileURLWithPath: "/owned/input")); rejected.run(configuration: configuration)
                await rejected.waitUntilSettled()
                XCTAssertNil(rejected.report, profile.rawValue); XCTAssertNotNil(rejected.errorMessage, profile.rawValue)
            }
        }
    }
}
