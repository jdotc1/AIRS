import Foundation
import XCTest
@testable import AIRSCore

final class ManualPairCompatibilityTests: XCTestCase {
    private let oldID = "airsf-" + String(repeating: "a", count: 64)
    private let newID = "airsf-" + String(repeating: "b", count: 64)

    private func source(_ name: String, id: String, digest: String, config: Any? = nil, model: String = "arm64-bounded-test-bit-branch-v50") throws -> Data {
        var value: [String: Any] = [
            "schema_version": 1, "report_kind": "airs.audit",
            "generator": ["name": "AIRS", "version": "0.3.3", "analysis_model_version": model],
            "image": ["display_name": name, "architecture": "arm64", "file_type": "dylib", "preferred_base": "0x1000",
                      "container_sha256": String(repeating: "0", count: 64), "slice_sha256": String(repeating: digest, count: 64),
                      "cpu_subtype": 0, "slice_offset": 0, "slice_size": 16],
            "summary": ["function_count": 1, "agreement_count": 1, "inconsistency_count": 0, "unresolved_count": 0,
                        "metadata_entry_count": 1, "checked_pc_count": 1],
            "issues": [], "limitations": ["Synthetic compatibility test"],
            "metadata_ranges": [["start": "0x1000", "end": "0x1010", "encoding": "0x04000000", "mode": "frame"]],
            "findings": [["id": id, "function": ["name": name, "address": "0x1000", "end_address": "0x1010", "image_offset": "0x0",
                                                  "size": 16, "boundary_source": "lc_function_starts"],
                          "verdict": "agreement", "coverage": "compact", "mode": "frame", "scope": "synchronous_call_sites",
                          "encoding": "0x04000000", "checked_pcs": ["0x1008"], "instruction_count": 4,
                          "reason_codes": ["supported_model_agreement"], "evidence": [], "limitations": []]]]
        if let config { value["analysis_config"] = config }
        return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    }

    private func comparison(changed: Bool? = nil, classification: String = "unchanged", compatible: Bool = true) throws -> ComparisonReport {
        var context: [String: Any] = [
            "baseline_image": ["display_name": "before", "slice_sha256": String(repeating: "1", count: 64), "architecture": "arm64"],
            "current_image": ["display_name": "after", "slice_sha256": String(repeating: "2", count: 64), "architecture": "arm64"],
            "same_image": false, "model_compatible": compatible, "matching_policy": "manual_then_unique_symbol",
            "manual_pairs": [["baseline_id": oldID, "current_id": newID]]]
        if let changed { context["analysis_configuration_changed"] = changed }
        let value: [String: Any] = ["schema_version": 1, "report_kind": "airs.diff", "comparison": context,
            "summary": ["matched_count": 1, "changed_count": classification == "changed" ? 1 : 0,
                        "unchanged_count": classification == "unchanged" ? 1 : 0, "ambiguous_count": classification == "ambiguous" ? 1 : 0,
                        "added_count": 0, "removed_count": 0],
            "changes": [["key": "manual:pair", "match_basis": "manual_review", "function_name": "after",
                         "baseline_id": oldID, "current_id": newID, "change": classification,
                         "before_verdict": "agreement", "after_verdict": "agreement",
                         "before_scope": "synchronous_call_sites", "after_scope": "synchronous_call_sites", "notes": ["Review candidate"]]],
            "limitations": []]
        return try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testDifferentLimitsRequireAmbiguousManualRows() throws {
        let value = try comparison(changed: true)
        XCTAssertThrowsError(try value.validateManualPairCompatibility(
            baselineData: source("before", id: oldID, digest: "1", config: ["limits": ["max_cfg_steps_per_function": 512]]),
            currentData: source("after", id: newID, digest: "2", config: ["limits": ["max_cfg_steps_per_function": 4096]])))
    }

    private func validate(_ report: ComparisonReport, before: Any? = nil, after: Any? = nil) throws {
        try report.validateManualPairCompatibility(
            baselineData: source("before", id: oldID, digest: "1", config: before),
            currentData: source("after", id: newID, digest: "2", config: after))
    }

    func testEqualConfigurationsKeepTheExistingClassification() throws {
        let report = try comparison(changed: false)
        let config: [String: Any] = ["limits": ["work": 512, "paths": 64], "policy": "owned"]
        XCTAssertNoThrow(try validate(report, before: config, after: config))
        XCTAssertEqual(report.changes.first?.change, "unchanged")
        XCTAssertEqual(report.comparison.analysisConfigurationChanged, false)
    }

    func testDifferentConfigurationsPermitAmbiguousRowsOnly() throws {
        let before = ["limits": ["work": 1]], after = ["limits": ["work": 2]]
        XCTAssertNoThrow(try validate(comparison(changed: true, classification: "ambiguous"), before: before, after: after))
        for classification in ["changed", "unchanged", "future-label"] {
            XCTAssertThrowsError(try validate(comparison(changed: true, classification: classification), before: before, after: after))
        }
    }

    func testReportedFlagMustReflectTheActualSavedConfigurations() throws {
        let before = ["limits": ["work": 1]], after = ["limits": ["work": 2]]
        XCTAssertThrowsError(try validate(comparison(changed: true), before: before, after: before))
        XCTAssertThrowsError(try validate(comparison(changed: false, classification: "ambiguous"), before: before, after: after))
    }

    func testLegacyAbsenceAndMissingStatusDoNotInventDefaults() throws {
        XCTAssertNoThrow(try validate(comparison(changed: false)))
        let config = ["limits": ["work": 1]]
        XCTAssertNoThrow(try validate(comparison(changed: true, classification: "ambiguous"), after: config))
        let unrecorded = try comparison(classification: "ambiguous")
        XCTAssertNoThrow(try validate(unrecorded, after: config))
        XCTAssertNil(unrecorded.comparison.analysisConfigurationChanged)
        XCTAssertThrowsError(try validate(comparison(), after: config))
    }

    func testExtraConfigurationFactsParticipateInEquality() throws {
        let before: [String: Any] = ["limits": ["work": 1], "options": ["mode": "strict"]]
        let after: [String: Any] = ["options": ["mode": "different"], "limits": ["work": 1]]
        XCTAssertNoThrow(try validate(comparison(changed: true, classification: "ambiguous"), before: before, after: after))
        XCTAssertThrowsError(try validate(comparison(changed: false), before: before, after: after))
    }

    func testMalformedConfigurationAndLimitsReject() throws {
        let malformed: [Any] = [NSNull(), "config", [Any](), [String: Any](), ["limits": NSNull()], ["limits": [Any]()],
                                ["limits": ["work": true]], ["limits": ["work": -1]],
                                ["limits": ["work": 1.5]], ["limits": ["work": "1"]]]
        for config in malformed {
            XCTAssertThrowsError(try validate(comparison(changed: true, classification: "ambiguous"), after: config))
        }
        XCTAssertNoThrow(try validate(comparison(changed: false), before: ["limits": [:]], after: ["limits": [:]]))
    }

    func testIntegralFloatingWireDoesNotBecomeAnIntegerLimit() throws {
        let key = "max_cfg_steps_per_function"
        let before = try source("before", id: oldID, digest: "1", config: ["limits": [key: 1]])
        let after = try source("after", id: newID, digest: "2", config: ["limits": [key: 1]])
        let text = try XCTUnwrap(String(data: after, encoding: .utf8))
        let floating = text.replacingOccurrences(of: "\"max_cfg_steps_per_function\":1", with: "\"max_cfg_steps_per_function\":1.0")
        XCTAssertNotEqual(floating, text)
        XCTAssertThrowsError(try comparison(changed: false).validateManualPairCompatibility(
            baselineData: before, currentData: Data(floating.utf8)))
    }

    func testModelMismatchAlsoRequiresAmbiguousManualRows() throws {
        let before = try source("before", id: oldID, digest: "1")
        let after = try source("after", id: newID, digest: "2", model: "future-model")
        XCTAssertThrowsError(try comparison(changed: false, compatible: false).validateManualPairCompatibility(
            baselineData: before, currentData: after))
        XCTAssertNoThrow(try comparison(changed: false, classification: "ambiguous", compatible: false).validateManualPairCompatibility(
            baselineData: before, currentData: after))
    }

    func testEndpointAndImageGuardsRemainPrerequisites() throws {
        let report = try comparison(changed: false)
        XCTAssertThrowsError(try report.validateManualPairCompatibility(
            baselineData: source("before", id: "airsf-" + String(repeating: "c", count: 64), digest: "1"),
            currentData: source("after", id: newID, digest: "2")))
        XCTAssertThrowsError(try report.validateManualPairCompatibility(
            baselineData: source("before", id: oldID, digest: "1"), currentData: source("after", id: newID, digest: "f")))
    }

    func testCompatibilityDoesNotRecomputeCompatibleChangeLabels() throws {
        let report = try comparison(changed: false, classification: "changed")
        let data = try JSONEncoder().encode(report)
        XCTAssertNoThrow(try validate(report))
        let second = try ComparisonReport.decode(JSONEncoder().encode(report))
        XCTAssertEqual(second.changes.first?.change, "changed")
        XCTAssertEqual(try JSONSerialization.jsonObject(with: data) as? NSDictionary,
                       try JSONSerialization.jsonObject(with: JSONEncoder().encode(report)) as? NSDictionary)
    }

}
