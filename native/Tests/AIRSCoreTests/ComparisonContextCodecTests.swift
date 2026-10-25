import Foundation
import XCTest
@testable import AIRSCore

final class ComparisonContextCodecTests: XCTestCase {
    private let oldID = "airsf-" + String(repeating: "a", count: 64)
    private let newID = "airsf-" + String(repeating: "b", count: 64)

    private func object() -> [String: Any] {
        ["schema_version": 1, "report_kind": "airs.diff",
         "comparison": ["baseline_image": image("before", digest: "1"), "current_image": image("after", digest: "2"),
                        "same_image": false, "model_compatible": true, "matching_policy": "exact_digest_then_unique_symbol"],
         "summary": ["matched_count": 0, "changed_count": 0, "unchanged_count": 0,
                     "added_count": 0, "removed_count": 0, "ambiguous_count": 0],
         "changes": [], "limitations": ["Synthetic context admission; no source identity established"]]
    }

    private func image(_ name: String, digest: String) -> [String: Any] {
        ["display_name": name, "slice_sha256": String(repeating: digest, count: 64), "architecture": "arm64"]
    }

    private func wire(_ updates: [String: Any]) throws -> [String: Any] {
        var value = object()
        var context = try XCTUnwrap(value["comparison"] as? [String: Any])
        for (key, update) in updates { context[key] = update }
        value["comparison"] = context
        return value
    }

    private func decode(_ value: [String: Any]) throws -> ComparisonReport {
        try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testExplicitNullContextFlagIsRejected() throws {
        XCTAssertThrowsError(try decode(wire(["exact_body_candidates": NSNull()])))
    }

    private func pair(_ old: String? = nil, _ new: String? = nil) -> [String: Any] {
        ["baseline_id": old ?? oldID, "current_id": new ?? newID]
    }

    private func encodedContext(_ report: ComparisonReport) throws -> [String: Any] {
        let value = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(report)) as? [String: Any])
        return try XCTUnwrap(value["comparison"] as? [String: Any])
    }

    func testTypedMetadataAndPairsSurviveRoundTrip() throws {
        var value = try wire(["analysis_configuration_changed": false, "exact_body_candidates": true,
                              "manual_pairs": [pair()], "matching_policy": "manual_then_unique_symbol_then_exact_body_candidate"])
        value["summary"] = ["matched_count": 1, "changed_count": 0, "unchanged_count": 1,
                            "added_count": 0, "removed_count": 0, "ambiguous_count": 0]
        value["changes"] = [["key": "manual:pair", "match_basis": "manual_review", "function_name": "sub_1000",
                            "baseline_id": oldID, "current_id": newID, "change": "unchanged",
                            "before_verdict": "agreement", "after_verdict": "agreement",
                            "before_scope": "synchronous_call_sites", "after_scope": "synchronous_call_sites",
                            "notes": ["User-selected review candidate; no source identity proof"]]]
        let report = try decode(value)
        XCTAssertEqual(report.comparison.analysisConfigurationChanged, false)
        XCTAssertEqual(report.comparison.exactBodyCandidates, true)
        XCTAssertEqual(report.comparison.manualPairs?.first?.baselineID, oldID)
        XCTAssertEqual(report.comparison.manualPairs?.first?.currentID, newID)
        let second = try ComparisonReport.decode(JSONEncoder().encode(report))
        XCTAssertEqual(second.comparison.manualPairs, report.comparison.manualPairs)
        XCTAssertEqual(second.comparison.exactBodyCandidates, true)
        XCTAssertEqual(second.changes.first?.notes, report.changes.first?.notes)
        XCTAssertEqual(second.changes.first?.matchBasis, "manual_review")
        XCTAssertEqual(second.summary.matchedCount, 1)
    }

    func testLegacyMetadataRemainsUnavailableAndOmitted() throws {
        let report = try decode(object())
        XCTAssertNil(report.comparison.analysisConfigurationChanged)
        XCTAssertNil(report.comparison.exactBodyCandidates)
        XCTAssertNil(report.comparison.manualPairs)
        let context = try encodedContext(report)
        for key in ["analysis_configuration_changed", "exact_body_candidates", "manual_pairs"] {
            XCTAssertNil(context[key], key)
        }
    }

    func testFalseAndEmptyValuesRemainPresent() throws {
        let report = try decode(wire(["analysis_configuration_changed": false, "exact_body_candidates": false, "manual_pairs": []]))
        XCTAssertEqual(report.comparison.exactBodyCandidates, false)
        XCTAssertEqual(report.comparison.manualPairs?.count, 0)
        let context = try encodedContext(report)
        XCTAssertEqual(context["analysis_configuration_changed"] as? Bool, false)
        XCTAssertEqual(context["exact_body_candidates"] as? Bool, false)
        XCTAssertEqual((context["manual_pairs"] as? [Any])?.count, 0)
    }

    func testNullAndWrongMetadataTypesReject() throws {
        let badFlags: [Any] = [NSNull(), 0, 1, "false", [Any](), [String: Any]()]
        for key in ["analysis_configuration_changed", "exact_body_candidates"] {
            for bad in badFlags { XCTAssertThrowsError(try decode(wire([key: bad])), key) }
        }
        let badPairs: [Any] = [NSNull(), "pairs", [String: Any](), [1]]
        for bad in badPairs { XCTAssertThrowsError(try decode(wire(["manual_pairs": bad]))) }
    }

    func testMalformedPairFieldsAndIdentifiersReject() throws {
        let wrongIDs = ["airsf-" + String(repeating: "A", count: 64), "airsf-abc", "other-" + String(repeating: "a", count: 64)]
        for id in wrongIDs { XCTAssertThrowsError(try decode(wire(["manual_pairs": [pair(id)]]))) }
        for key in ["baseline_id", "current_id"] {
            var missing = pair(); missing.removeValue(forKey: key)
            XCTAssertThrowsError(try decode(wire(["manual_pairs": [missing]])))
            var wrong = pair(); wrong[key] = true
            XCTAssertThrowsError(try decode(wire(["manual_pairs": [wrong]])))
        }
        var extra = pair(); extra["unbound"] = "value"
        XCTAssertThrowsError(try decode(wire(["manual_pairs": [extra]])))
    }

    func testDuplicateAndConflictingEndpointsReject() throws {
        let another = "airsf-" + String(repeating: "c", count: 64)
        for pairs in [[pair(), pair()], [pair(), pair(oldID, another)], [pair(), pair(another, newID)]] {
            XCTAssertThrowsError(try decode(wire(["manual_pairs": pairs])))
        }
    }

    func testDeclaredSameImageRejectsNonemptyPairsButAllowsEmptyRecords() throws {
        XCTAssertThrowsError(try decode(wire(["same_image": true, "manual_pairs": [pair()]])))
        XCTAssertNoThrow(try decode(wire(["same_image": true, "manual_pairs": []])))
    }

    func testUnknownPolicyAndBasisRemainGenericReviewData() throws {
        var value = try wire(["matching_policy": "future-review-policy", "exact_body_candidates": false])
        value["summary"] = ["matched_count": 0, "changed_count": 0, "unchanged_count": 0,
                            "added_count": 1, "removed_count": 0, "ambiguous_count": 0]
        value["changes"] = [["key": "future", "match_basis": "future_candidate", "function_name": "review",
                            "change": "added", "notes": ["Future producer review data"]]]
        let report = try decode(value)
        let second = try ComparisonReport.decode(JSONEncoder().encode(report))
        XCTAssertEqual(second.comparison.matchingPolicy, "future-review-policy")
        XCTAssertEqual(second.changes.first?.matchBasis, "future_candidate")
        XCTAssertEqual(second.summary.addedCount, 1)
    }

    func testRawPairLimitRejectsBeforeDecodingEveryEntry() throws {
        let oversized = Array(repeating: pair(), count: 50_001)
        XCTAssertThrowsError(try decode(wire(["manual_pairs": oversized]))) { error in
            XCTAssertTrue(error.localizedDescription.contains("50,000"), "Expected the count bound, not duplicate rejection")
        }
    }


    func testConfigurationChangePreservesAmbiguousClassification() throws {
        var value = try wire(["analysis_configuration_changed": true])
        value["summary"] = ["matched_count": 1, "changed_count": 0, "unchanged_count": 0,
                            "added_count": 0, "removed_count": 0, "ambiguous_count": 1]
        value["changes"] = [["key": "symbol:_work", "match_basis": "unique_symbol", "function_name": "_work",
                            "baseline_id": oldID, "current_id": newID, "change": "ambiguous",
                            "notes": ["Analysis configuration differs; review only"]]]
        let report = try decode(value)
        let second = try ComparisonReport.decode(JSONEncoder().encode(report))
        XCTAssertEqual(second.comparison.analysisConfigurationChanged, true)
        XCTAssertEqual(second.summary.ambiguousCount, 1)
        XCTAssertEqual(second.summary.changedCount, 0)
        XCTAssertEqual(second.summary.unchangedCount, 0)
        XCTAssertEqual(second.changes.first?.change, "ambiguous")
        XCTAssertEqual(second.changes.first?.notes, report.changes.first?.notes)
    }

}
