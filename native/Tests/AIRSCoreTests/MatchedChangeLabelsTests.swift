import Foundation
import XCTest
@testable import AIRSCore

final class MatchedChangeLabelsTests: XCTestCase {
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
        try report.validateMatchedChangeLabels(baselineData: before, currentData: after)
    }

    func testEquivalentNonmanualPairCannotClaimChanged() throws {
        let (before, after) = try pair()
        XCTAssertNoThrow(try validate([row(old: oldID, new: newID)], before: before, after: after))
        XCTAssertThrowsError(try validate([row(label: "changed", old: oldID, new: newID)], before: before, after: after))
    }

    private func altered(_ data: Data, fields: [String: Any] = [:], top: [String: Any] = [:]) throws -> Data {
        var report = try object(data)
        for (key, value) in top { report[key] = value }
        var findings = try XCTUnwrap(report["findings"] as? [[String: Any]])
        for (key, value) in fields { findings[0][key] = value }
        report["findings"] = findings
        return try JSONSerialization.data(withJSONObject: report)
    }

    private func decode(_ value: [String: Any]) throws -> ComparisonReport {
        try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testChangedNonmanualObservationsCannotClaimUnchanged() throws {
        let (before, after) = try pair()
        let changed = try altered(after, fields: ["reason_codes": ["changed_observation"]])
        XCTAssertNoThrow(try validate([row(label: "changed", old: oldID, new: newID)], before: before, after: changed))
        XCTAssertThrowsError(try validate([row(old: oldID, new: newID)], before: before, after: changed))
    }

    func testPresentationChangesAreNotFindingSignatureChanges() throws {
        let (before, after) = try pair()
        let old = try altered(before, fields: ["evidence": [["code": "fact", "message": "Before display text", "expected": "caller"]]])
        let new = try altered(after, fields: ["evidence": [["code": "fact", "message": "After display text", "expected": "caller"]], "limitations": ["Other prose"]])
        XCTAssertNoThrow(try validate([row(old: oldID, new: newID)], before: old, after: new))
        XCTAssertThrowsError(try validate([row(label: "changed", old: oldID, new: newID)], before: old, after: new))
    }

    func testAllBasisStringsRetainHostObservationLabelChecks() throws {
        let (before, after) = try pair()
        for basis in ["unique_symbol", "exact_body_candidate", "future_matcher"] {
            XCTAssertNoThrow(try validate([row(basis: basis, old: oldID, new: newID)], before: before, after: after))
            XCTAssertThrowsError(try validate([row(basis: basis, label: "changed", old: oldID, new: newID)], before: before, after: after))
        }
    }

    func testConfigurationDifferencesRequireAmbiguousSelectedPairs() throws {
        let (before, after) = try pair()
        let configured = try altered(after, top: ["analysis_config": ["limits": ["work": 1]]])
        XCTAssertNoThrow(try validate([row(label: "ambiguous", old: oldID, new: newID)], before: before, after: configured))
        for label in ["unchanged", "changed"] {
            XCTAssertThrowsError(try validate([row(label: label, old: oldID, new: newID)], before: before, after: configured))
        }
        var value = try wire([row(label: "ambiguous", old: oldID, new: newID)], before: before, after: configured)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["analysis_configuration_changed"] = false; value["comparison"] = context
        XCTAssertThrowsError(try decode(value).validateMatchedChangeLabels(baselineData: before, currentData: configured))
    }

    func testModelDifferencesRequireAmbiguityButCompatiblePairsDoNot() throws {
        let (before, after) = try pair()
        var generator = try XCTUnwrap(object(after)["generator"] as? [String: Any]); generator["analysis_model_version"] = "future-model"
        let different = try altered(after, top: ["generator": generator])
        XCTAssertNoThrow(try validate([row(label: "ambiguous", old: oldID, new: newID)], before: before, after: different))
        XCTAssertThrowsError(try validate([row(old: oldID, new: newID)], before: before, after: different))
        XCTAssertThrowsError(try validate([row(label: "ambiguous", old: oldID, new: newID)], before: before, after: after))
    }

    func testUnselectedGroupsAndOneSidedRowsDoNotInventSignatures() throws {
        let (before, after) = try pair()
        let values = [row("added", basis: "unmatched", label: "added", old: nil, new: newID),
                      row("removed", basis: "unmatched", label: "removed", old: oldID, new: nil),
                      row("group", label: "ambiguous", old: nil, new: nil)]
        XCTAssertNoThrow(try validate(values, before: before, after: after))
        XCTAssertNoThrow(try validate([], before: before, after: after))
        let configured = try altered(after, top: ["analysis_config": ["limits": ["work": 1]]])
        XCTAssertNoThrow(try validate(values, before: before, after: configured))
    }

    func testSourceFactsAndAccountingRemainPrerequisites() throws {
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate([row(old: unknownID, new: newID)], before: before, after: after))
        var stale = row(old: oldID, new: newID); stale["before_scope"] = "modeled_leaf_body"
        XCTAssertThrowsError(try validate([stale], before: before, after: after))
        var wire = try self.wire([row(old: oldID, new: newID)], before: before, after: after)
        var summary = try XCTUnwrap(wire["summary"] as? [String: Int]); summary["matched_count"] = 99; wire["summary"] = summary
        XCTAssertThrowsError(try decode(wire).validateMatchedChangeLabels(baselineData: before, currentData: after))
    }

    private func additionalFinding(_ data: Data, id: String) throws -> Data {
        var report = try object(data), findings = try XCTUnwrap(object(data)["findings"] as? [[String: Any]])
        var finding = findings[0], function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        finding["id"] = id
        function["name"] = "second"; function["address"] = "0x1020"; function["end_address"] = "0x1030"; function["image_offset"] = "0x20"
        finding["function"] = function; finding["checked_pcs"] = ["0x1028"]; findings.append(finding); report["findings"] = findings
        var ranges = try XCTUnwrap(report["metadata_ranges"] as? [[String: Any]])
        ranges.append(["start": "0x1020", "end": "0x1030", "encoding": "0x04000000", "mode": "frame"]); report["metadata_ranges"] = ranges
        report["summary"] = ["function_count": 2, "agreement_count": 2, "inconsistency_count": 0, "unresolved_count": 0, "metadata_entry_count": 2, "checked_pc_count": 2]
        var image = try XCTUnwrap(report["image"] as? [String: Any]); image["slice_size"] = 64; report["image"] = image
        return try JSONSerialization.data(withJSONObject: report)
    }

    func testManualAndNonmanualRowsShareTheSameObservationRules() throws {
        let (before, after) = try pair()
        let otherNew = "airsf-" + String(repeating: "d", count: 64)
        let old = try additionalFinding(before, id: unknownID), new = try additionalFinding(after, id: otherNew)
        let manual = row("manual", basis: "manual_review", old: oldID, new: newID)
        let automatic = row("automatic", old: unknownID, new: otherNew)
        func withPairs(_ rows: [[String: Any]]) throws -> ComparisonReport {
            var value = try wire(rows, before: old, after: new), context = try XCTUnwrap(wire(rows, before: old, after: new)["comparison"] as? [String: Any])
            context["manual_pairs"] = [["baseline_id": oldID, "current_id": newID]]; value["comparison"] = context
            return try decode(value)
        }
        XCTAssertNoThrow(try withPairs([manual, automatic]).validateMatchedChangeLabels(baselineData: old, currentData: new))
        var falseManual = manual; falseManual["change"] = "changed"
        XCTAssertThrowsError(try withPairs([falseManual, automatic]).validateMatchedChangeLabels(baselineData: old, currentData: new))
        var falseAutomatic = automatic; falseAutomatic["change"] = "changed"
        XCTAssertThrowsError(try withPairs([manual, falseAutomatic]).validateMatchedChangeLabels(baselineData: old, currentData: new))
    }

    func testSharedSignatureRetainsUnicodeWireDistinctions() throws {
        let (before, after) = try pair()
        let old = try altered(before, fields: ["reason_codes": ["\u{e9}"]])
        let new = try altered(after, fields: ["reason_codes": ["e\u{301}"]])
        XCTAssertNoThrow(try validate([row(label: "changed", old: oldID, new: newID)], before: old, after: new))
        XCTAssertThrowsError(try validate([row(old: oldID, new: newID)], before: old, after: new))
    }

    func testConfigurationAdmissionCannotBeSkipped() throws {
        let (before, after) = try pair()
        let malformed = try altered(after, top: ["analysis_config": ["limits": ["work": true]]])
        XCTAssertThrowsError(try validate([row(label: "ambiguous", old: oldID, new: newID)], before: before, after: malformed))
    }
}
