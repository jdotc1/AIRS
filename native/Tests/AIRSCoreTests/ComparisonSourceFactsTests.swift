import Foundation
import XCTest
@testable import AIRSCore

final class ComparisonSourceFactsTests: XCTestCase {
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

    private func object(_ data: Data) throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    private func row(_ key: String = "symbol:pair", basis: String = "unique_symbol", label: String = "unchanged", old: String?, new: String?) -> [String: Any] {
        var value: [String: Any] = ["key": key, "match_basis": basis, "function_name": "Candidate", "change": label, "notes": []]
        if let old { value["baseline_id"] = old; value["before_verdict"] = "agreement"; value["before_scope"] = "synchronous_call_sites" }
        if let new { value["current_id"] = new; value["after_verdict"] = "agreement"; value["after_scope"] = "synchronous_call_sites" }
        return value
    }

    private func wire(_ rows: [[String: Any]], before: Data, after: Data) throws -> [String: Any] {
        let old = try object(before), new = try object(after)
        let oldImage = try XCTUnwrap(old["image"] as? [String: Any]), newImage = try XCTUnwrap(new["image"] as? [String: Any])
        let oldGenerator = try XCTUnwrap(old["generator"] as? [String: Any]), newGenerator = try XCTUnwrap(new["generator"] as? [String: Any])
        let context: [String: Any] = ["baseline_image": oldImage, "current_image": newImage,
            "same_image": (oldImage["slice_sha256"] as? String) == (newImage["slice_sha256"] as? String),
            "model_compatible": (oldGenerator["analysis_model_version"] as? String) == (newGenerator["analysis_model_version"] as? String),
            "matching_policy": "exact_digest_then_unique_symbol"]
        var summary = ["matched_count": rows.filter { $0["baseline_id"] is String && $0["current_id"] is String }.count]
        for label in ["changed", "unchanged", "added", "removed", "ambiguous"] {
            summary[label + "_count"] = rows.filter { ($0["change"] as? String) == label }.count
        }
        return ["schema_version": 1, "report_kind": "airs.diff", "comparison": context,
                "summary": summary, "changes": rows, "limitations": ["Synthetic selected facts only"]]
    }

    private func pair() throws -> (Data, Data) {
        (try source("before", id: oldID, digest: "1"), try source("after", id: newID, digest: "2"))
    }

    private func validate(_ rows: [[String: Any]], before: Data, after: Data) throws {
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: wire(rows, before: before, after: after)))
        try report.validateSelectedSourceFacts(baselineData: before, currentData: after)
    }

    func testForeignNonmanualEndpointCannotPassSelectedSourceBinding() throws {
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate([row(old: unknownID, new: newID)], before: before, after: after))
    }

    private func decode(_ value: [String: Any]) throws -> ComparisonReport {
        try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testValidNonmanualFactsBindWithoutMutatingSavedData() throws {
        let (before, after) = try pair()
        let report = try decode(wire([row(old: oldID, new: newID)], before: before, after: after))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        let original = try encoder.encode(report)
        XCTAssertNoThrow(try report.validateSelectedSourceFacts(baselineData: before, currentData: after))
        XCTAssertEqual(try encoder.encode(report), original)
        XCTAssertEqual(try AuditReport.decode(before).findings.first?.id, oldID)
        XCTAssertEqual(try AuditReport.decode(after).findings.first?.id, newID)
    }

    func testCurrentAndSwappedIDsCannotBorrowTheOtherSourceSide() throws {
        let (before, after) = try pair()
        for value in [row(old: oldID, new: unknownID), row(old: newID, new: oldID),
                      row(old: newID, new: newID), row(old: oldID, new: oldID)] {
            XCTAssertThrowsError(try validate([value], before: before, after: after))
        }
    }

    func testEverySelectedVerdictAndScopeMustMatchItsSource() throws {
        let (before, after) = try pair()
        for (key, falseFact) in [("before_verdict", "inconsistency"), ("after_verdict", "unresolved"),
                                 ("before_scope", "modeled_leaf_body"), ("after_scope", "metadata_only")] {
            var value = row(old: oldID, new: newID); value[key] = falseFact
            XCTAssertThrowsError(try validate([value], before: before, after: after))
        }
    }

    func testAddedAndRemovedRowsBindOnlyTheirSelectedSides() throws {
        let (before, after) = try pair()
        let values = [row("added", basis: "unmatched", label: "added", old: nil, new: newID),
                      row("removed", basis: "unmatched", label: "removed", old: oldID, new: nil)]
        XCTAssertNoThrow(try validate(values, before: before, after: after))
        XCTAssertThrowsError(try validate([row("added", basis: "unmatched", label: "added", old: nil, new: unknownID)], before: before, after: after))
        XCTAssertThrowsError(try validate([row("removed", basis: "unmatched", label: "removed", old: unknownID, new: nil)], before: before, after: after))
    }

    func testAmbiguousGroupsBindSelectionsWithoutInventingMembers() throws {
        let (before, after) = try pair()
        let values = [row("old", label: "ambiguous", old: oldID, new: nil),
                      row("new", label: "ambiguous", old: nil, new: newID),
                      row("group", label: "ambiguous", old: nil, new: nil)]
        XCTAssertNoThrow(try validate(values, before: before, after: after))
        XCTAssertThrowsError(try validate([row("bad", label: "ambiguous", old: unknownID, new: nil)], before: before, after: after))
    }

    func testFutureMatchBasesCannotBypassSelectedEndpointLookup() throws {
        let (before, after) = try pair()
        XCTAssertNoThrow(try validate([row(basis: "future_matcher", old: oldID, new: newID)], before: before, after: after))
        XCTAssertThrowsError(try validate([row(basis: "future_matcher", old: unknownID, new: newID)], before: before, after: after))
    }

    func testImageAndDeclaredFlagsRemainPrerequisites() throws {
        let (before, after) = try pair()
        let original = try wire([row(old: oldID, new: newID)], before: before, after: after)
        let report = try decode(original)
        let foreign = try source("before", id: oldID, digest: "3")
        XCTAssertThrowsError(try report.validateSelectedSourceFacts(baselineData: foreign, currentData: after))
        for field in ["same_image", "model_compatible"] {
            var value = original, context = try XCTUnwrap(original["comparison"] as? [String: Any])
            context[field] = !(try XCTUnwrap(context[field] as? Bool)); value["comparison"] = context
            XCTAssertThrowsError(try decode(value).validateSelectedSourceFacts(baselineData: before, currentData: after))
        }
    }

    func testAccountingRejectsRepeatedSelectionsAndContradictorySummary() throws {
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate([row("one", old: oldID, new: newID), row("two", old: oldID, new: newID)], before: before, after: after))
        var value = try wire([row(old: oldID, new: newID)], before: before, after: after)
        var summary = try XCTUnwrap(value["summary"] as? [String: Int]); summary["matched_count"] = 99; value["summary"] = summary
        XCTAssertThrowsError(try decode(value).validateSelectedSourceFacts(baselineData: before, currentData: after))
    }

    func testManualSelectionMetadataStillCannotBeSkipped() throws {
        let (before, after) = try pair()
        var value = try wire([row("manual:pair", basis: "manual_review", old: oldID, new: newID)], before: before, after: after)
        XCTAssertThrowsError(try decode(value).validateSelectedSourceFacts(baselineData: before, currentData: after))
        var context = try XCTUnwrap(value["comparison"] as? [String: Any])
        context["manual_pairs"] = [["baseline_id": oldID, "current_id": newID]]; value["comparison"] = context
        XCTAssertNoThrow(try decode(value).validateSelectedSourceFacts(baselineData: before, currentData: after))
    }

    func testSameIDAcrossSidesUsesIndependentSourceLookups() throws {
        let before = try source("before", id: oldID, digest: "1")
        let after = try source("after", id: oldID, digest: "1")
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: oldID)], before: before, after: after))
    }

    func testSourceCompletenessAndNonmanualSignaturesAreNotClaimed() throws {
        let (before, after) = try pair()
        XCTAssertNoThrow(try validate([], before: before, after: after))
        // The two admitted findings have equivalent signatures. This API binds
        // selected verdict/scope facts, not this nonmanual changed label.
        XCTAssertNoThrow(try validate([row(label: "changed", old: oldID, new: newID)], before: before, after: after))
        var current = try object(after); current["analysis_config"] = ["limits": ["work": 7]]
        let differentConfiguration = try JSONSerialization.data(withJSONObject: current)
        XCTAssertNoThrow(try validate([row(old: oldID, new: newID)], before: before, after: differentConfiguration))
    }

    func testMalformedSourceAuditCannotBecomeSelectedEvidence() throws {
        let (before, after) = try pair()
        let report = try decode(wire([row(old: oldID, new: newID)], before: before, after: after))
        XCTAssertThrowsError(try report.validateSelectedSourceFacts(baselineData: Data("{}".utf8), currentData: after))
    }
}
