import Foundation
import XCTest
@testable import AIRSCore

final class DuplicateSymbolGroupsTests: XCTestCase {
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
        try report.validateDuplicateSymbolGroups(baselineData: before, currentData: after)
    }

    private func named(_ data: Data, _ name: Any) throws -> Data {
        var report = try object(data), findings = try XCTUnwrap(object(data)["findings"] as? [[String: Any]])
        var info = try XCTUnwrap(findings[0]["function"] as? [String: Any]); info["name"] = name
        findings[0]["function"] = info; report["findings"] = findings
        return try JSONSerialization.data(withJSONObject: report)
    }

    private func namedPair(_ name: String = "work") throws -> (Data, Data) {
        let (before, after) = try pair()
        return (try named(before, name), try named(after, name))
    }

    private func symbolKey(_ name: String) -> String {
        var bytes = Data("symbol:".utf8); bytes.append(contentsOf: name.utf8)
        return String(decoding: bytes, as: UTF8.self)
    }

    private func additional(_ data: Data, id: String, name: String) throws -> Data {
        var report = try object(data), findings = try XCTUnwrap(object(data)["findings"] as? [[String: Any]])
        var extra = findings[0], info = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        extra["id"] = id; info["name"] = name; info["address"] = "0x1020"; info["end_address"] = "0x1030"; info["image_offset"] = "0x20"
        extra["function"] = info; extra["checked_pcs"] = ["0x1028"]; findings.append(extra); report["findings"] = findings
        var ranges = try XCTUnwrap(report["metadata_ranges"] as? [[String: Any]])
        ranges.append(["start": "0x1020", "end": "0x1030", "encoding": "0x04000000", "mode": "frame"]); report["metadata_ranges"] = ranges
        report["summary"] = ["function_count": 2, "agreement_count": 2, "inconsistency_count": 0, "unresolved_count": 0, "metadata_entry_count": 2, "checked_pc_count": 2]
        var image = try XCTUnwrap(report["image"] as? [String: Any]); image["slice_size"] = 64; report["image"] = image
        return try JSONSerialization.data(withJSONObject: report)
    }

    private func decoded(_ value: [String: Any]) throws -> ComparisonReport {
        try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testDuplicateBaselineCannotClaimRemovedSingleton() throws {
        let (before, after) = try pair()
        let old = try additional(named(before, "work"), id: unknownID, name: "work")
        XCTAssertThrowsError(try validate([row("symbol:work", label: "removed", old: oldID, new: nil)], before: old, after: after))
    }

    private let otherNewID = "airsf-" + String(repeating: "d", count: 64)
    private func validateWire(_ value: [String: Any], before: Data, after: Data) throws {
        try decoded(value).validateDuplicateSymbolGroups(baselineData: before, currentData: after)
    }
    private func duplicatePair(_ name: String = "work") throws -> (Data, Data) {
        let (old, new) = try namedPair(name)
        return (try additional(old, id: unknownID, name: name), try additional(new, id: otherNewID, name: name))
    }
    func testOneSidedDuplicateGroupsHaveNoSelectedEndpoint() throws {
        let (before, after) = try pair()
        let old = try additional(named(before, "work"), id: unknownID, name: "work")
        let new = try additional(named(after, "work"), id: otherNewID, name: "work")
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: nil, new: nil)], before: old, after: after))
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: nil, new: nil)], before: before, after: new))
    }
    func testMixedDuplicateGroupsRequireTheirActualSingleton() throws {
        let (old, new) = try namedPair()
        let duplicateOld = try additional(old, id: unknownID, name: "work")
        let duplicateNew = try additional(new, id: otherNewID, name: "work")
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: nil, new: newID)], before: duplicateOld, after: new))
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: oldID, new: nil)], before: old, after: duplicateNew))
        XCTAssertThrowsError(try validate([row("symbol:work", label: "ambiguous", old: nil, new: nil)], before: duplicateOld, after: new))
        XCTAssertThrowsError(try validate([row("symbol:work", label: "ambiguous", old: nil, new: nil)], before: old, after: duplicateNew))
    }
    func testTwoSidedDuplicatesDoNotSelectEitherSide() throws {
        let (old, new) = try duplicatePair()
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: nil, new: nil)], before: old, after: new))
        XCTAssertThrowsError(try validate([row("symbol:work", label: "ambiguous", old: oldID, new: nil)], before: old, after: new))
        XCTAssertThrowsError(try validate([row("symbol:work", label: "ambiguous", old: nil, new: newID)], before: old, after: new))
    }
    func testDuplicateCurrentCannotClaimAddedSingleton() throws {
        let (before, after) = try pair()
        let new = try additional(named(after, "work"), id: otherNewID, name: "work")
        XCTAssertThrowsError(try validate([row("symbol:work", label: "added", old: nil, new: newID)], before: before, after: new))
    }
    func testDuplicateGroupCannotHideBehindASelectedPair() throws {
        let (old, new) = try namedPair()
        let before = try additional(old, id: unknownID, name: "work")
        for label in ["unchanged", "ambiguous"] {
            XCTAssertThrowsError(try validate([row("symbol:work", label: label, old: oldID, new: newID)], before: before, after: new))
        }
    }
    func testForeignSingletonCannotSubstituteForGroupMember() throws {
        let (old, new) = try namedPair()
        let before = try additional(old, id: unknownID, name: "work")
        let after = try additional(new, id: otherNewID, name: "other")
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: nil, new: newID)], before: before, after: after))
        XCTAssertThrowsError(try validate([row("symbol:work", label: "ambiguous", old: nil, new: otherNewID)], before: before, after: after))
    }
    func testManualPinsCanResolveMultiplicityBeforeGrouping() throws {
        let (old, new) = try duplicatePair()
        let manual = row("manual:chosen", basis: "manual_review", old: unknownID, new: otherNewID)
        let symbol = row("symbol:work", old: oldID, new: newID)
        var value = try wire([manual, symbol], before: old, after: new)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["manual_pairs"] = [["baseline_id": unknownID, "current_id": otherNewID]]; value["comparison"] = context
        XCTAssertNoThrow(try validateWire(value, before: old, after: new))
        var hidden = try wire([symbol], before: old, after: new); hidden["comparison"] = context
        XCTAssertThrowsError(try validateWire(hidden, before: old, after: new))
    }
    func testOtherImportedRowsCannotConsumeDuplicateBlockers() throws {
        let (old, new) = try namedPair()
        let before = try additional(old, id: unknownID, name: "work"), after = try additional(new, id: otherNewID, name: "other")
        let other = row("future:pair", basis: "future_matcher", old: unknownID, new: otherNewID)
        XCTAssertThrowsError(try validate([row("symbol:work", label: "ambiguous", old: oldID, new: nil), other], before: before, after: after))
    }
    func testAbsentFalseAndTrueBodyStatusPreserveDuplicateGroupShape() throws {
        let (old, new) = try duplicatePair()
        for status: Bool? in [nil, false, true] {
            var value = try wire([row("symbol:work", label: "ambiguous", old: nil, new: nil)], before: old, after: new)
            var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["exact_body_candidates"] = status; value["comparison"] = context
            let report = try decoded(value)
            XCTAssertNoThrow(try report.validateDuplicateSymbolGroups(baselineData: old, currentData: new))
            XCTAssertEqual(report.comparison.exactBodyCandidates, status)
        }
    }
    func testSymbolKeysMustNameExistingUsableSourceGroups() throws {
        let (old, new) = try duplicatePair()
        for key in ["future:work", "Symbol:work", "symbol:missing", "symbol: work", "symbol:"] {
            XCTAssertThrowsError(try validate([row(key, label: "ambiguous", old: nil, new: nil)], before: old, after: new))
        }
        for name in ["sub_1", "_entry", "loc_0xAB", "sub_\u{301}real"] {
            let (before, after) = try duplicatePair(name)
            XCTAssertThrowsError(try validate([row(symbolKey(name), label: "ambiguous", old: nil, new: nil)], before: before, after: after))
        }
    }
    func testRawUnicodeWhitespaceAndCaseKeysRemainDistinct() throws {
        for name in ["e\u{301}", "work:variant", " work", "Work", "loc_\u{301}abc"] {
            let (old, new) = try duplicatePair(name)
            XCTAssertNoThrow(try validate([row(symbolKey(name), label: "ambiguous", old: nil, new: nil)], before: old, after: new))
        }
        let (old, new) = try duplicatePair("e\u{301}")
        XCTAssertThrowsError(try validate([row("symbol:\u{e9}", label: "ambiguous", old: nil, new: nil)], before: old, after: new))
    }
    func testUniqueGroupsCannotInventUnselectedAmbiguity() throws {
        let (old, new) = try namedPair()
        for endpoints: (String?, String?) in [(nil, nil), (oldID, nil), (nil, newID)] {
            XCTAssertThrowsError(try validate([row("symbol:work", label: "ambiguous", old: endpoints.0, new: endpoints.1)], before: old, after: new))
        }
        let after = try source("other", id: newID, digest: "2")
        XCTAssertThrowsError(try validate([row("symbol:work", label: "ambiguous", old: oldID, new: nil)], before: old, after: after))
    }
    func testIncompatibleSelectedUniquePairMayRemainAmbiguous() throws {
        let (old, new) = try namedPair()
        var changed = try object(new); changed["analysis_config"] = ["limits": ["work": 1]]
        let after = try JSONSerialization.data(withJSONObject: changed)
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: oldID, new: newID)], before: old, after: after))
        XCTAssertThrowsError(try validate([row("symbol:work", old: oldID, new: newID)], before: old, after: after))
        XCTAssertNoThrow(try validate([row("symbol:work", old: oldID, new: newID)], before: old, after: new))
    }
    func testSingletonOneSidedOutcomesAndCompletenessRemainSeparate() throws {
        let (old, new) = try pair()
        XCTAssertNoThrow(try validate([], before: old, after: new))
        XCTAssertNoThrow(try validate([row("symbol:before", label: "removed", old: oldID, new: nil)], before: old, after: new))
        XCTAssertNoThrow(try validate([row("symbol:after", label: "added", old: nil, new: newID)], before: old, after: new))
        XCTAssertNoThrow(try validate([row("future:pair", basis: "future_matcher", old: oldID, new: newID)], before: old, after: new))
    }
    func testSourceFactsAccountingAndExactImageAuthorityRemainPrerequisites() throws {
        let (old, new) = try duplicatePair()
        let one = row("symbol:work", label: "ambiguous", old: nil, new: nil)
        var wireValue = try wire([one], before: old, after: new), summary = try XCTUnwrap(wireValue["summary"] as? [String: Any])
        summary["ambiguous_count"] = 0; wireValue["summary"] = summary
        XCTAssertThrowsError(try validateWire(wireValue, before: old, after: new))
        let same = try source("after", id: newID, digest: "1")
        let before = try source("before", id: oldID, digest: "1")
        XCTAssertThrowsError(try validate([one], before: before, after: same))
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: same))
    }
}
