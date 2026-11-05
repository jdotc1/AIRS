import Foundation
import XCTest
@testable import AIRSCore

final class SwiftFlowReportTests: XCTestCase {
    private func object() -> [String: Any] {
        ["schema_version": 1, "report_kind": "airs.swift_error_flow", "model_version": "swift-sync-error-edges-v37",
         "image": ["architecture": "arm64", "cpu_subtype": 0, "preferred_base": "0x0", "slice_sha256": String(repeating: "a", count: 64), "container_sha256": String(repeating: "b", count: 64), "slice_offset": 0, "slice_size": 128],
         "word_scan_complete": true, "call_details_complete": true, "limitations": ["Structural only"],
         "calls": [["caller_pc": "0x0", "call_pc": "0x4", "status": "recovered_candidate"]]]
    }
    private func decode(_ value: [String: Any]) throws -> SwiftFlowReport {
        try SwiftFlowReport.decode(JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]))
    }
    func testBoundedReportAndStableIdentity() throws {
        let report = try decode(object())
        XCTAssertTrue(report.supportsInterpretation)
        XCTAssertEqual(report.calls.first?.id, "0x0:0x4")
        XCTAssertTrue(report.calls.first?.detailJSON.contains("call_pc") == true)
        XCTAssertFalse(report.sourceData.isEmpty)
    }
    func testUnknownAndMixedModelsCannotInterpret() throws {
        var value = object(); value["model_version"] = "future"
        XCTAssertFalse(try decode(value).supportsInterpretation)
        value = object(); value["return_choice_model_version"] = "swift-return-choice-v46"
        XCTAssertFalse(try decode(value).supportsInterpretation)
    }
    func testUnknownProfileRetainsRawButSuppressesSemanticProjections() throws {
        var value = object(); value["model_version"] = "future"
        var rows = value["calls"] as? [[String: Any]] ?? []
        rows[0]["test_pc"] = "0x8"; rows[0]["success_pc"] = "0xc"; rows[0]["error_pc"] = "0x10"
        rows[0]["outcome_witness"] = ["status": "eligible_structural_only", "reason": "recorded", "validation": ["work_steps": 3, "checked_instruction_count": 2, "facts": ["call": "checked"]], "graph": ["edges": [["from": "call", "to": "test", "provenance_pc": "0x4"]]]]
        value["calls"] = rows
        let report = try decode(value); let call = try XCTUnwrap(report.calls.first)
        XCTAssertFalse(report.supportsInterpretation)
        XCTAssertNil(call.testPC); XCTAssertNil(call.successPC); XCTAssertNil(call.errorPC)
        XCTAssertNil(call.witnessStatus); XCTAssertNil(call.witnessReason)
        XCTAssertNil(call.witnessWorkSteps); XCTAssertNil(call.witnessCheckedInstructionCount)
        XCTAssertTrue(call.witnessFacts.isEmpty); XCTAssertTrue(call.witnessEdges.isEmpty)
        XCTAssertTrue(call.detailJSON.contains("success_pc")); XCTAssertFalse(report.sourceData.isEmpty)
    }

    func testDuplicateCallsAndMalformedIdentityRefuse() throws {
        var value = object(); let calls = value["calls"] as? [[String: Any]] ?? []
        value["calls"] = calls + calls
        XCTAssertThrowsError(try decode(value))
        value = object(); value["image"] = ["architecture": "arm64"]
        XCTAssertThrowsError(try decode(value))
        value = object(); value["schema_version"] = true
        XCTAssertThrowsError(try decode(value))
        value = object(); value["schema_version"] = 1.5
        XCTAssertThrowsError(try decode(value))
        value = object(); var image = value["image"] as? [String: Any] ?? [:]
        image["slice_offset"] = 0.5; value["image"] = image
        XCTAssertThrowsError(try decode(value))
    }
    func testOversizedAndDeepInputsRefuse() throws {
        XCTAssertThrowsError(try SwiftFlowReport.decode(Data(repeating: 32, count: SwiftFlowReport.maximumBytes + 1)))
        var nested: Any = "leaf"
        for _ in 0..<34 { nested = [nested] }
        var value = object(); value["nested"] = nested
        XCTAssertThrowsError(try decode(value))
    }
    func testContradictoryWitnessCannotDisplayEligibility() throws {
        var value = object()
        let models = ["error_region_model_version": "swift-sync-error-region-v24", "region_incoming_model_version": "swift-region-direct-entries-v7", "flag_entry_model_version": "swift-compare-flag-entries-v1", "structured_presentation_model_version": "swift-structural-presentation-v10", "success_result_model_version": "swift-success-result-v24", "success_constant_model_version": "swift-success-constant-v17", "error_constant_model_version": "swift-error-constant-v19", "return_choice_model_version": "swift-return-choice-v45", "outcome_witness_model_version": "swift-outcome-witness-v1", "outcome_validation_model_version": "swift-outcome-validation-v1"]
        for (key, model) in models { value[key] = model }
        value["outcome_witnesses_complete"] = true
        var rows = value["calls"] as? [[String: Any]] ?? []
        rows[0]["outcome_witness"] = ["model_version": "swift-outcome-witness-v1", "validation_model_version": "swift-outcome-validation-v1", "status": "eligible_structural_only", "runtime_branch_proven": true, "validation": ["model_version": "swift-outcome-validation-v1", "status": "eligible_structural_only"]]
        value["calls"] = rows
        XCTAssertEqual(try decode(value).calls.first?.witnessStatus, "unresolved")
        value["outcome_witnesses_complete"] = false
        XCTAssertEqual(try decode(value).calls.first?.witnessStatus, "unresolved")
    }

    func testSummaryRetainsOmissionsAndScanCounts() throws {
        var value = object()
        value["summary"] = ["scanned_word_count": 19, "observed_direct_call_count": 4, "omitted_call_count": 3]
        let report = try decode(value)
        XCTAssertTrue(report.summaryText.contains("3 omitted calls"))
        XCTAssertTrue(report.summaryText.contains("19 scanned words"))
    }

    func testOptionsAreExplicitArgumentsWithPrerequisites() {
        let args = SwiftFlowOptions(includeMethods: true, includeWitnesses: true).arguments(input: URL(fileURLWithPath: "/owned/--quoted input"), output: URL(fileURLWithPath: "/owned/report.json"))
        XCTAssertTrue(args.contains("--include-swift-methods")); XCTAssertTrue(args.contains("--include-outcome-witnesses"))
        XCTAssertTrue(args.contains("--include-structured-presentation")); XCTAssertEqual(Array(args.suffix(2)), ["--", "/owned/--quoted input"])
        XCTAssertFalse(SwiftFlowOptions().arguments(input: URL(fileURLWithPath: "/owned"), output: URL(fileURLWithPath: "/out")).contains("--include-swift-methods"))
    }
}
