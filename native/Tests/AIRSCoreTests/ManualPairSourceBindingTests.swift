import Foundation
import XCTest
@testable import AIRSCore

final class ManualPairSourceBindingTests: XCTestCase {
    private let oldID = "airsf-" + String(repeating: "a", count: 64)
    private let newID = "airsf-" + String(repeating: "b", count: 64)
    private let unknownID = "airsf-" + String(repeating: "c", count: 64)

    private func source(_ name: String, id: String, digest: String) throws -> Data {
        try JSONSerialization.data(withJSONObject: [
            "schema_version": 1, "report_kind": "airs.audit",
            "generator": ["name": "AIRS", "version": "0.3.3", "analysis_model_version": "arm64-bounded-test-bit-branch-v50"],
            "image": ["display_name": name, "architecture": "arm64", "file_type": "dylib", "preferred_base": "0x1000",
                      "container_sha256": String(repeating: "0", count: 64), "slice_sha256": String(repeating: digest, count: 64),
                      "cpu_subtype": 0, "slice_offset": 0, "slice_size": 16],
            "summary": ["function_count": 1, "agreement_count": 1, "inconsistency_count": 0, "unresolved_count": 0,
                        "metadata_entry_count": 1, "checked_pc_count": 1],
            "issues": [], "limitations": ["Synthetic binding test; identity is not authenticated"],
            "metadata_ranges": [["start": "0x1000", "end": "0x1010", "encoding": "0x04000000", "mode": "frame"]],
            "findings": [["id": id, "function": ["name": name, "address": "0x1000", "end_address": "0x1010",
                                                  "image_offset": "0x0", "size": 16, "boundary_source": "lc_function_starts"],
                          "verdict": "agreement", "coverage": "compact", "mode": "frame", "scope": "synchronous_call_sites",
                          "encoding": "0x04000000", "checked_pcs": ["0x1008"], "instruction_count": 4,
                          "reason_codes": ["supported_model_agreement"], "evidence": [], "limitations": []]]])
    }

    private func comparison(_ old: String? = nil, _ new: String? = nil) -> [String: Any] {
        let before = old ?? oldID, after = new ?? newID
        return ["schema_version": 1, "report_kind": "airs.diff",
                "comparison": ["baseline_image": image("before", "1"), "current_image": image("after", "2"),
                               "same_image": false, "model_compatible": true, "matching_policy": "manual_then_unique_symbol",
                               "manual_pairs": [["baseline_id": before, "current_id": after]]],
                "summary": ["matched_count": 1, "changed_count": 0, "unchanged_count": 1,
                            "added_count": 0, "removed_count": 0, "ambiguous_count": 0],
                "changes": [["key": "manual:pair", "match_basis": "manual_review", "function_name": "after",
                             "baseline_id": before, "current_id": after, "change": "unchanged",
                             "before_verdict": "agreement", "after_verdict": "agreement",
                             "before_scope": "synchronous_call_sites", "after_scope": "synchronous_call_sites",
                             "notes": ["User selection does not prove source identity"]]], "limitations": []]
    }

    private func image(_ name: String, _ digest: String) -> [String: Any] {
        ["display_name": name, "slice_sha256": String(repeating: digest, count: 64), "architecture": "arm64"]
    }

    private func decode(_ value: [String: Any]) throws -> ComparisonReport {
        try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testPairMustExistInTheSelectedSourceReports() throws {
        let report = try decode(comparison(unknownID))
        XCTAssertThrowsError(try report.validateManualPairEndpoints(
            baselineData: source("before", id: oldID, digest: "1"),
            currentData: source("after", id: newID, digest: "2")))
    }

    private func bind(_ value: [String: Any], baseline: Data? = nil, current: Data? = nil) throws {
        let report = try decode(value)
        try report.validateManualPairEndpoints(
            baselineData: baseline ?? source("before", id: oldID, digest: "1"),
            currentData: current ?? source("after", id: newID, digest: "2"))
    }

    private func context(_ updates: [String: Any], in value: [String: Any]? = nil) throws -> [String: Any] {
        var wire = value ?? comparison()
        var changed = try XCTUnwrap(wire["comparison"] as? [String: Any])
        for (key, update) in updates { changed[key] = update }
        wire["comparison"] = changed
        return wire
    }

    private func rows(_ transform: (inout [[String: Any]]) -> Void) throws -> [String: Any] {
        var value = comparison()
        var changes = try XCTUnwrap(value["changes"] as? [[String: Any]])
        transform(&changes); value["changes"] = changes
        return value
    }

    func testValidPairBindsWithoutChangingReportsOrComparison() throws {
        let before = try source("before", id: oldID, digest: "1")
        let after = try source("after", id: newID, digest: "2")
        let report = try decode(comparison())
        let encoded = try JSONEncoder().encode(report)
        try report.validateManualPairEndpoints(baselineData: before, currentData: after)
        let second = try JSONDecoder().decode(ComparisonReport.self, from: JSONEncoder().encode(report))
        XCTAssertEqual(second.changes.first?.change, "unchanged")
        XCTAssertEqual(second.comparison.manualPairs, report.comparison.manualPairs)
        XCTAssertEqual(try JSONSerialization.jsonObject(with: encoded) as? NSDictionary,
                       try JSONSerialization.jsonObject(with: JSONEncoder().encode(report)) as? NSDictionary)
    }

    func testEndpointsCannotBeSwappedBetweenSourceSides() throws {
        XCTAssertThrowsError(try bind(comparison(newID, oldID)))
        XCTAssertThrowsError(try bind(comparison(oldID, unknownID)))
    }

    func testImageIdentityMustMatchWhileDisplayLabelsDoNotAuthorizeBinding() throws {
        for field in ["slice_sha256", "architecture", "uuid"] {
            var image = self.image("after", "2")
            image[field] = field == "slice_sha256" ? String(repeating: "f", count: 64)
                : field == "architecture" ? "arm64e" : "00000000-0000-0000-0000-000000000001"
            XCTAssertThrowsError(try bind(context(["current_image": image])))
        }
        XCTAssertNoThrow(try bind(context(["current_image": image("renamed display label", "2")])))
    }

    func testIdentityAndModelFlagsMustReflectTheSelectedSources() throws {
        XCTAssertThrowsError(try bind(context(["model_compatible": false])))
        var current = try XCTUnwrap(JSONSerialization.jsonObject(with: source("after", id: newID, digest: "2")) as? [String: Any])
        current["generator"] = ["name": "AIRS", "version": "0.3.3", "analysis_model_version": "future-model"]
        let data = try JSONSerialization.data(withJSONObject: current)
        XCTAssertThrowsError(try bind(comparison(), current: data))
        let ambiguous = try rows { $0[0]["change"] = "ambiguous" }
        XCTAssertNoThrow(try bind(context(["model_compatible": false], in: ambiguous), current: data))
        XCTAssertThrowsError(try bind(context(["current_image": image("after", "1")]),
                                     current: source("after", id: newID, digest: "1")))
    }

    func testRecordedPairsAndManualRowsMustCorrespondExactlyOnce() throws {
        XCTAssertThrowsError(try bind(rows { $0 = [] }))
        XCTAssertThrowsError(try bind(rows { $0.append($0[0]) }))
        XCTAssertThrowsError(try bind(rows { $0[0]["baseline_id"] = self.unknownID }))
        XCTAssertThrowsError(try bind(rows { $0[0].removeValue(forKey: "current_id") }))
        var noRecords = comparison()
        var context = try XCTUnwrap(noRecords["comparison"] as? [String: Any])
        context.removeValue(forKey: "manual_pairs"); noRecords["comparison"] = context
        XCTAssertThrowsError(try bind(noRecords))
    }

    func testRowVerdictsAndScopesMustComeFromSelectedFindings() throws {
        for field in ["before_verdict", "after_verdict", "before_scope", "after_scope"] {
            let changed = try rows { $0[0][field] = field.hasSuffix("verdict") ? "inconsistency" : "modeled_leaf_body" }
            XCTAssertThrowsError(try bind(changed), field)
        }
    }

    func testMalformedSourceReportsAreRejectedBeforeEndpointLookup() throws {
        XCTAssertThrowsError(try bind(comparison(), baseline: Data("not a report".utf8)))
        var source = try XCTUnwrap(JSONSerialization.jsonObject(with: self.source("after", id: newID, digest: "2")) as? [String: Any])
        source["summary"] = ["function_count": 9, "agreement_count": 1, "inconsistency_count": 0, "unresolved_count": 0,
                             "metadata_entry_count": 1, "checked_pc_count": 1]
        XCTAssertThrowsError(try bind(comparison(), current: JSONSerialization.data(withJSONObject: source)))
    }

    func testSourceByteLimitRejectsBeforeParsing() throws {
        let oversized = Data(count: ReportFiles.maximumBytes + 1)
        XCTAssertThrowsError(try bind(comparison(), baseline: oversized)) { error in
            guard case ReportError.tooLarge(let limit) = error else {
                return XCTFail("Expected bounded-data rejection before JSON decoding: \(error)")
            }
            XCTAssertEqual(limit, ReportFiles.maximumBytes)
        }
    }

    func testNoManualMetadataLeavesLegacyNonmanualRowsUnbound() throws {
        var value = comparison()
        var changed = try XCTUnwrap(value["comparison"] as? [String: Any])
        changed.removeValue(forKey: "manual_pairs"); value["comparison"] = changed
        var changes = try XCTUnwrap(value["changes"] as? [[String: Any]])
        changes[0]["match_basis"] = "unique_symbol"; value["changes"] = changes
        XCTAssertNoThrow(try bind(value))
    }

}
