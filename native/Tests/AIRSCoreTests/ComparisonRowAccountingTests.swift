import Foundation
import XCTest
@testable import AIRSCore

final class ComparisonRowAccountingTests: XCTestCase {
    private func id(_ digit: String) -> String { "airsf-" + String(repeating: digit, count: 64) }

    private func row(_ key: String, label: String, old: String? = nil, new: String? = nil) -> [String: Any] {
        var value: [String: Any] = ["key": key, "match_basis": "unique_symbol", "function_name": "Review candidate", "change": label, "notes": []]
        if let old { value["baseline_id"] = old; value["before_verdict"] = "agreement"; value["before_scope"] = "synchronous_call_sites" }
        if let new { value["current_id"] = new; value["after_verdict"] = "agreement"; value["after_scope"] = "synchronous_call_sites" }
        return value
    }

    private func report(_ rows: [[String: Any]], counts: [String: Int]) throws -> ComparisonReport {
        var summary = ["matched_count": 0, "changed_count": 0, "unchanged_count": 0, "added_count": 0, "removed_count": 0, "ambiguous_count": 0]
        for (key, value) in counts { summary[key] = value }
        let value: [String: Any] = ["schema_version": 1, "report_kind": "airs.diff",
            "comparison": ["baseline_image": ["display_name": "Before", "slice_sha256": String(repeating: "1", count: 64), "architecture": "arm64"],
                "current_image": ["display_name": "After", "slice_sha256": String(repeating: "2", count: 64), "architecture": "arm64"],
                "same_image": false, "model_compatible": true, "matching_policy": "exact_digest_then_unique_symbol"],
            "summary": summary, "changes": rows, "limitations": ["Synthetic row accounting; source facts are not authenticated"]]
        return try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testContradictorySummaryCannotPassRowAccounting() throws {
        let value = try report([row("one", label: "unchanged", old: id("a"), new: id("b"))], counts: ["matched_count": 99, "unchanged_count": 1])
        XCTAssertThrowsError(try value.validateRowAccounting())
    }

    func testEmptyRowsRequireZeroSummary() throws {
        XCTAssertNoThrow(try report([], counts: [:]).validateRowAccounting())
        XCTAssertThrowsError(try report([], counts: ["added_count": 1]).validateRowAccounting())
    }

    private func mixedRows() -> [[String: Any]] {
        [row("changed", label: "changed", old: id("a"), new: id("b")),
         row("added", label: "added", new: id("c")),
         row("removed", label: "removed", old: id("d")),
         row("pair-ambiguous", label: "ambiguous", old: id("e"), new: id("f")),
         row("group-ambiguous", label: "ambiguous")]
    }

    private var mixedCounts: [String: Int] {
        ["matched_count": 2, "changed_count": 1, "added_count": 1, "removed_count": 1, "ambiguous_count": 2]
    }

    func testMixedCategoriesAndAmbiguousPairsAreAccountedSeparately() throws {
        XCTAssertNoThrow(try report(mixedRows(), counts: mixedCounts).validateRowAccounting())
        let unchanged = row("unchanged", label: "unchanged", old: id("1"), new: id("2"))
        XCTAssertNoThrow(try report([unchanged], counts: ["matched_count": 1, "unchanged_count": 1]).validateRowAccounting())
    }

    func testEachDeclaredCountMustEqualObservedRowsWithoutOverflow() throws {
        for key in ["matched_count", "changed_count", "unchanged_count", "added_count", "removed_count", "ambiguous_count"] {
            var counts = mixedCounts; counts[key] = (counts[key] ?? 0) + 1
            XCTAssertThrowsError(try report(mixedRows(), counts: counts).validateRowAccounting())
            counts[key] = Int.max
            XCTAssertThrowsError(try report(mixedRows(), counts: counts).validateRowAccounting())
        }
    }

    func testCategoryEndpointShapesCannotInventAddedOrMatchedRows() throws {
        let malformed: [([String: Any], [String: Int])] = [
            (row("a", label: "changed", old: id("a")), ["changed_count": 1]),
            (row("b", label: "unchanged", new: id("b")), ["unchanged_count": 1]),
            (row("c", label: "added", old: id("a"), new: id("b")), ["added_count": 1, "matched_count": 1]),
            (row("d", label: "added"), ["added_count": 1]),
            (row("e", label: "removed", new: id("b")), ["removed_count": 1]),
            (row("f", label: "removed", old: id("a"), new: id("b")), ["removed_count": 1, "matched_count": 1]),
            (row("g", label: "future_change"), [:])]
        for (value, counts) in malformed {
            XCTAssertThrowsError(try report([value], counts: counts).validateRowAccounting())
        }
    }

    func testOneSidedAndUnselectedAmbiguityDoNotInventPairs() throws {
        let values = [row("old-group", label: "ambiguous", old: id("a")),
                      row("new-group", label: "ambiguous", new: id("b")),
                      row("neither-group", label: "ambiguous")]
        XCTAssertNoThrow(try report(values, counts: ["ambiguous_count": 3]).validateRowAccounting())
        XCTAssertThrowsError(try report(values, counts: ["ambiguous_count": 3, "matched_count": 1]).validateRowAccounting())
    }

    func testDuplicateKeysAndEndpointsAreRejected() throws {
        let first = row("one", label: "changed", old: id("a"), new: id("b"))
        let sameKey = row("one", label: "changed", old: id("c"), new: id("d"))
        XCTAssertThrowsError(try report([first, sameKey], counts: ["matched_count": 2, "changed_count": 2]).validateRowAccounting())
        let repeatedOld = row("two", label: "removed", old: id("a"))
        XCTAssertThrowsError(try report([first, repeatedOld], counts: ["matched_count": 1, "changed_count": 1, "removed_count": 1]).validateRowAccounting())
        let repeatedNew = row("two", label: "added", new: id("b"))
        XCTAssertThrowsError(try report([first, repeatedNew], counts: ["matched_count": 1, "changed_count": 1, "added_count": 1]).validateRowAccounting())
        XCTAssertThrowsError(try report([row("", label: "ambiguous")], counts: ["ambiguous_count": 1]).validateRowAccounting())
    }

    func testTheSameIDMayAppearOnceOnEachSide() throws {
        let value = row("same-image", label: "unchanged", old: id("a"), new: id("a"))
        XCTAssertNoThrow(try report([value], counts: ["matched_count": 1, "unchanged_count": 1]).validateRowAccounting())
    }

    func testWireDistinctUnicodeKeysAreNotCollapsed() throws {
        let values = [row("\u{e9}", label: "added", new: id("a")), row("e\u{301}", label: "added", new: id("b"))]
        XCTAssertNoThrow(try report(values, counts: ["added_count": 2]).validateRowAccounting())
    }

    func testMalformedEndpointIdentifiersCannotBeCounted() throws {
        for malformed in ["other-" + String(repeating: "a", count: 64), "airsf-a", id("A"), id("g")] {
            XCTAssertThrowsError(try report([row("one", label: "added", new: malformed)], counts: ["added_count": 1]).validateRowAccounting())
        }
    }

    func testFactsMustFollowTypedEndpointPresence() throws {
        let valid = row("one", label: "changed", old: id("a"), new: id("b"))
        for field in ["before_verdict", "before_scope", "after_verdict", "after_scope"] {
            var value = valid; value.removeValue(forKey: field)
            XCTAssertThrowsError(try report([value], counts: ["matched_count": 1, "changed_count": 1]).validateRowAccounting())
            value = valid; value[field] = NSNull()
            XCTAssertThrowsError(try report([value], counts: ["matched_count": 1, "changed_count": 1]).validateRowAccounting())
        }
        for field in ["before_scope", "after_scope"] {
            var value = valid; value[field] = ""
            XCTAssertThrowsError(try report([value], counts: ["matched_count": 1, "changed_count": 1]).validateRowAccounting())
        }
        var noEndpoint = row("empty", label: "ambiguous")
        noEndpoint["before_scope"] = "metadata_only"
        XCTAssertThrowsError(try report([noEndpoint], counts: ["ambiguous_count": 1]).validateRowAccounting())
        var explicitNull = row("null", label: "ambiguous")
        for field in ["baseline_id", "current_id", "before_verdict", "before_scope", "after_verdict", "after_scope"] { explicitNull[field] = NSNull() }
        XCTAssertNoThrow(try report([explicitNull], counts: ["ambiguous_count": 1]).validateRowAccounting())
    }

    func testUnknownMatchBasisDoesNotBecomeMatchingTruth() throws {
        var value = row("future", label: "changed", old: id("a"), new: id("b"))
        value["match_basis"] = "future_matcher"
        let decoded = try report([value], counts: ["matched_count": 1, "changed_count": 1])
        XCTAssertNoThrow(try decoded.validateRowAccounting())
        XCTAssertEqual(decoded.changes[0].matchBasis, "future_matcher")
    }

    func testRowLimitRejectsBeforeDuplicateOrDeclaredCountProcessing() throws {
        let decoded = try report([row("one", label: "ambiguous")], counts: ["ambiguous_count": 1])
        let oversized = ComparisonReport(schemaVersion: decoded.schemaVersion, reportKind: decoded.reportKind,
            comparison: decoded.comparison, summary: decoded.summary,
            changes: Array(repeating: decoded.changes[0], count: 100_001), limitations: [])
        XCTAssertThrowsError(try oversized.validateRowAccounting()) { error in
            XCTAssertTrue(error.localizedDescription.contains("row limit"))
        }
    }
}
