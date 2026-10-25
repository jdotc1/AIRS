import Foundation
import XCTest
@testable import AIRSCore

final class UniqueSymbolPairsTests: XCTestCase {
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
        try report.validateUniqueSymbolPairs(baselineData: before, currentData: after)
    }

    func testDifferentSourceNamesCannotClaimAUniqueSymbolPair() throws {
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate([row("symbol:before", old: oldID, new: newID)], before: before, after: after))
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

    func testUniqueExactNamePairPassesAsAReviewCandidate() throws {
        let (before, after) = try namedPair()
        XCTAssertNoThrow(try validate([row("symbol:work", old: oldID, new: newID)], before: before, after: after))
    }

    func testHiddenDuplicateBlockersCannotBecomeUniqueByOmission() throws {
        let (before, after) = try namedPair()
        let old = try additional(before, id: unknownID, name: "work")
        let otherNew = "airsf-" + String(repeating: "d", count: 64)
        let new = try additional(after, id: otherNew, name: "work")
        XCTAssertThrowsError(try validate([row("symbol:work", old: oldID, new: newID)], before: old, after: after))
        XCTAssertThrowsError(try validate([row("symbol:work", old: oldID, new: newID)], before: before, after: new))
        XCTAssertThrowsError(try validate([row("symbol:work", old: oldID, new: newID)], before: old, after: new))
    }

    func testValidatedManualPinsPrecedeSourceNameGrouping() throws {
        let (before, after) = try namedPair()
        let otherNew = "airsf-" + String(repeating: "d", count: 64)
        let old = try additional(before, id: unknownID, name: "work"), new = try additional(after, id: otherNew, name: "other")
        let manual = row("manual:chosen", basis: "manual_review", old: unknownID, new: otherNew)
        let symbol = row("symbol:work", old: oldID, new: newID)
        var value = try wire([manual, symbol], before: old, after: new)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any])
        context["manual_pairs"] = [["baseline_id": unknownID, "current_id": otherNew]]; value["comparison"] = context
        XCTAssertNoThrow(try decoded(value).validateUniqueSymbolPairs(baselineData: old, currentData: new))
        var hiddenPin = try wire([symbol], before: old, after: new); hiddenPin["comparison"] = context
        XCTAssertThrowsError(try decoded(hiddenPin).validateUniqueSymbolPairs(baselineData: old, currentData: new))
    }

    func testOtherImportedMatchesCannotConsumeSymbolBlockers() throws {
        let (before, after) = try namedPair()
        let otherNew = "airsf-" + String(repeating: "d", count: 64)
        let old = try additional(before, id: unknownID, name: "work"), new = try additional(after, id: otherNew, name: "other")
        let values = [row("symbol:work", old: oldID, new: newID),
                      row("body:candidate", basis: "exact_body_candidate", old: unknownID, new: otherNew)]
        XCTAssertThrowsError(try validate(values, before: old, after: new))
    }

    func testGeneratedAndGenericNamesWithholdSymbolEvidence() throws {
        for name in ["", "_entry", "__text", "sub_real", "sub_0x1", "<anonymous>", "0xnothex", "0X1", "loc_0xAB", "unk_1", "off_a", "nullsub_F", "sub_\u{301}real", "0x\u{301}nothex"] {
            let (before, after) = try namedPair(name)
            XCTAssertThrowsError(try validate([row(symbolKey(name), old: oldID, new: newID)], before: before, after: after))
        }
    }

    func testNonhexAndEmptyDonorSuffixesRetainHostPolicy() throws {
        for name in ["loc_work", "loc_", "loc_0x", "Loc_1", "_entrypoint", "__textual", "loc_\u{301}abc", " work"] {
            let (before, after) = try namedPair(name)
            XCTAssertNoThrow(try validate([row(symbolKey(name), old: oldID, new: newID)], before: before, after: after))
        }
    }

    func testCaseWhitespaceAndUnicodeNamesAreNotNormalizedTogether() throws {
        let pairs = [("Work", "work"), (" work", "work"), ("work ", "work"), ("\u{e9}", "e\u{301}")]
        for (oldName, newName) in pairs {
            let (before, after) = try pair()
            let old = try named(before, oldName), new = try named(after, newName)
            XCTAssertThrowsError(try validate([row(symbolKey(oldName), old: oldID, new: newID)], before: old, after: new))
        }
    }

    func testSymbolKeyMustRetainExactSourceWireName() throws {
        let (before, after) = try namedPair()
        for key in ["symbol:other", "Symbol:work", "symbol: work"] {
            XCTAssertThrowsError(try validate([row(key, old: oldID, new: newID)], before: before, after: after))
        }
        let name = "e\u{301}"
        let (old, new) = try namedPair(name)
        XCTAssertNoThrow(try validate([row(symbolKey(name), old: oldID, new: newID)], before: old, after: new))
        XCTAssertThrowsError(try validate([row("symbol:\u{e9}", old: oldID, new: newID)], before: old, after: new))
        let (colonOld, colonNew) = try namedPair("work:variant")
        XCTAssertNoThrow(try validate([row("symbol:work:variant", old: oldID, new: newID)], before: colonOld, after: colonNew))
    }

    func testBodyCandidateStatusDoesNotChangeEstablishedSymbolPairs() throws {
        let (before, after) = try namedPair()
        let statuses: [Bool?] = [nil, false, true]
        for status in statuses {
            var value = try wire([row("symbol:work", old: oldID, new: newID)], before: before, after: after)
            var context = try XCTUnwrap(value["comparison"] as? [String: Any])
            if let status { context["exact_body_candidates"] = status }
            value["comparison"] = context
            let report = try decoded(value)
            XCTAssertNoThrow(try report.validateUniqueSymbolPairs(baselineData: before, currentData: after))
            XCTAssertEqual(report.comparison.exactBodyCandidates, status)
        }
    }

    func testObservationCompatibilityAndSourceFactsRemainRequired() throws {
        let (before, after) = try namedPair()
        var configured = try object(after); configured["analysis_config"] = ["limits": ["work": 1]]
        let different = try JSONSerialization.data(withJSONObject: configured)
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: oldID, new: newID)], before: before, after: different))
        XCTAssertThrowsError(try validate([row("symbol:work", old: oldID, new: newID)], before: before, after: different))
        XCTAssertThrowsError(try validate([row("symbol:work", old: unknownID, new: newID)], before: before, after: after))
        var stale = row("symbol:work", old: oldID, new: newID); stale["before_scope"] = "metadata_only"
        XCTAssertThrowsError(try validate([stale], before: before, after: after))
    }

    func testSameImageStillRequiresOffsetAuthority() throws {
        let before = try named(source("before", id: oldID, digest: "1"), "work")
        let after = try named(source("after", id: newID, digest: "1"), "work")
        XCTAssertThrowsError(try validate([row("symbol:work", old: oldID, new: newID)], before: before, after: after))
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: after))
    }

    func testMissingSourceNamesDoNotBecomeAddressBasedSymbols() throws {
        let (before, after) = try pair()
        let old = try named(before, NSNull()), new = try named(after, NSNull())
        XCTAssertThrowsError(try validate([row("symbol:work", old: oldID, new: newID)], before: old, after: new))
    }

    func testOneSidedGroupsOtherBasesAndCompletenessRemainSeparate() throws {
        let (before, after) = try namedPair()
        XCTAssertNoThrow(try validate([], before: before, after: after))
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: oldID, new: nil)], before: before, after: after))
        let (otherOld, otherNew) = try pair() // Different source names deliberately remain unverified for this other basis.
        XCTAssertNoThrow(try validate([row("future:pair", basis: "future_matcher", old: oldID, new: newID)], before: otherOld, after: otherNew))
    }
}
