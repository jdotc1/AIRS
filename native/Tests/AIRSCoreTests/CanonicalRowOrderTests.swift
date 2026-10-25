import Foundation
import XCTest
@testable import AIRSCore

final class CanonicalRowOrderTests: XCTestCase {
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

    private func validate(_ rows: [[String: Any]], before: Data, after: Data, status: Bool? = false) throws {
        var value = try wire(rows, before: before, after: after)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["exact_body_candidates"] = status; value["comparison"] = context
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        try report.validateCanonicalRowOrder(baselineData: before, currentData: after)
    }

    private let ordinary = "exact_digest_then_unique_symbol"
    private let manual = "manual_then_unique_symbol"
    private let bodySuffix = "_then_exact_body_candidate"
    private var pin: [[String: String]] { [["baseline_id": oldID, "current_id": newID]] }
    private func configured(_ rows: [[String: Any]], before: Data, after: Data, status: Bool? = nil,
                            pins: [[String: String]]? = nil, policy: String) throws -> ComparisonReport {
        var value = try wire(rows, before: before, after: after)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any])
        context["matching_policy"] = policy; context["exact_body_candidates"] = status; context["manual_pairs"] = pins
        value["comparison"] = context
        return try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }
    private func check(_ report: ComparisonReport, before: Data, after: Data) throws {
        try report.validateCanonicalRowOrder(baselineData: before, currentData: after)
    }
    private func named(_ data: Data, _ name: String, fingerprint: Bool = false) throws -> Data {
        var value = try object(data), findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(findings[0]["function"] as? [String: Any]); function["name"] = name
        if fingerprint { function["body_fingerprint"] = ["kind": "arm64-exact-bytes-v1", "sha256": String(repeating: "f", count: 64), "instruction_count": 4] }
        findings[0]["function"] = function; value["findings"] = findings
        return try JSONSerialization.data(withJSONObject: value)
    }
    private func additional(_ data: Data, id: String, name: String = "_entry", digest: String = "f") throws -> Data {
        var report = try object(data), findings = try XCTUnwrap(object(data)["findings"] as? [[String: Any]])
        let start = 0x1000 + findings.count * 0x20
        var extra = findings[0], function = try XCTUnwrap(extra["function"] as? [String: Any])
        extra["id"] = id; function["name"] = name
        function["address"] = "0x" + String(start, radix: 16); function["end_address"] = "0x" + String(start + 16, radix: 16)
        function["image_offset"] = "0x" + String(start - 0x1000, radix: 16); function["size"] = 16
        function["body_fingerprint"] = ["kind": "arm64-exact-bytes-v1", "sha256": String(repeating: digest, count: 64), "instruction_count": 4]
        extra["function"] = function; extra["instruction_count"] = 4; extra["checked_pcs"] = ["0x" + String(start + 8, radix: 16)]
        findings.append(extra); report["findings"] = findings
        var ranges = try XCTUnwrap(report["metadata_ranges"] as? [[String: Any]])
        ranges.append(["start": function["address"]!, "end": function["end_address"]!, "encoding": "0x04000000", "mode": "frame"]); report["metadata_ranges"] = ranges
        let n = findings.count
        report["summary"] = ["function_count": n, "agreement_count": n, "inconsistency_count": 0, "unresolved_count": 0, "metadata_entry_count": n, "checked_pc_count": n]
        var image = try XCTUnwrap(report["image"] as? [String: Any]); image["slice_size"] = start + 16 - 0x1000; report["image"] = image
        return try JSONSerialization.data(withJSONObject: report)
    }
    private let otherNewID = "airsf-" + String(repeating: "d", count: 64)
    private var manualKey: String { "manual:" + oldID + ":" + newID }
    private func labeled(_ key: String, basis: String = "unique_symbol", label: String = "unchanged",
                         old: String?, new: String?, name: String) -> [String: Any] {
        var value = row(key, basis: basis, label: label, old: old, new: new); value["function_name"] = name; return value
    }
    private func manualLabel(_ name: String, before: Data, after: Data, label: String = "unchanged") throws {
        let value = labeled(manualKey, basis: "manual_review", label: label, old: oldID, new: newID, name: name)
        try check(configured([value], before: before, after: after, pins: pin, policy: manual), before: before, after: after)
    }
    private func fixture(_ names: [String]) throws -> (Data, Data, [[String: Any]]) {
        let (old, new) = try pair()
        var before = try named(old, names[0]), after = try named(new, names[0])
        var rows = [labeled("symbol:" + names[0], old: oldID, new: newID, name: names[0])]
        for index in names.indices.dropFirst() {
            let old = "airsf-" + String(format: "%064x", index + 16)
            let new = "airsf-" + String(format: "%064x", index + 32)
            before = try additional(before, id: old, name: names[index])
            after = try additional(after, id: new, name: names[index])
            rows.append(labeled("symbol:" + names[index], old: old, new: new, name: names[index]))
        }
        return (before, after, rows)
    }
    func testReversedValidRowsCannotClaimCanonicalOrder() throws {
        let (old, new, rows) = try fixture(["zeta", "alpha"])
        XCTAssertThrowsError(try validate(rows, before: old, after: new))
    }
    func testSortedKeysDoNotDependOnSourceOrder() throws {
        let (old, new, rows) = try fixture(["zeta", "alpha"])
        try validate(Array(rows.reversed()), before: old, after: new)
    }
    func testEmptyComparisonRetainsPartialScope() throws {
        let (old, new) = try pair()
        try validate([], before: old, after: new)
    }
    func testSingletonNeedsNoOrderingInference() throws {
        let (old, new, rows) = try fixture(["work"])
        try validate(rows, before: old, after: new)
    }
    func testOrderedPartialRowsDoNotRequireOmittedGroups() throws {
        let (old, new, rows) = try fixture(["alpha", "middle", "zeta"])
        try validate([rows[0], rows[2]], before: old, after: new)
    }
    func testCasePunctuationAndPrefixAreNotFolded() throws {
        let (old, new, rows) = try fixture([" Work", "Work", "Work!", "Work:variant", "work"])
        try validate(rows, before: old, after: new)
        XCTAssertThrowsError(try validate(Array(rows.reversed()), before: old, after: new))
    }
    func testNumericLookingNamesUseLexicalOrder() throws {
        let (old, new, rows) = try fixture(["work10", "work2"])
        try validate(rows, before: old, after: new)
        XCTAssertThrowsError(try validate(Array(rows.reversed()), before: old, after: new))
    }
    func testCanonicalEquivalentSpellingsRemainDistinctOrderedKeys() throws {
        let (old, new, rows) = try fixture(["cafe\u{301}", "caf\u{e9}"])
        try validate(rows, before: old, after: new)
        XCTAssertThrowsError(try validate(Array(rows.reversed()), before: old, after: new))
    }
    func testSupplementaryScalarsFollowCodePointRatherThanUTF16Order() throws {
        let (old, new, rows) = try fixture(["\u{e000}", "\u{10000}"])
        try validate(rows, before: old, after: new)
        XCTAssertThrowsError(try validate(Array(rows.reversed()), before: old, after: new))
    }
    func testLeadingCombiningMarkDoesNotJoinPrefixGrapheme() throws {
        let (old, new, rows) = try fixture(["a", "\u{301}work"])
        try validate(rows, before: old, after: new)
        XCTAssertThrowsError(try validate(Array(rows.reversed()), before: old, after: new))
    }
    func testCorrectOrderCannotBypassSelectedNameProof() throws {
        let (old, new, rows) = try fixture(["alpha", "zeta"])
        var wrong = rows; wrong[0]["function_name"] = "unrelated"
        XCTAssertThrowsError(try validate(wrong, before: old, after: new))
    }
    func testDuplicateKeysRemainInvalid() throws {
        let (old, new, rows) = try fixture(["alpha", "zeta"])
        var wrong = rows; wrong[1]["key"] = wrong[0]["key"]
        XCTAssertThrowsError(try validate(wrong, before: old, after: new))
    }
    func testEarlierAPIKeepsUnorderedRowsWithoutMutation() throws {
        let (old, new, rows) = try fixture(["zeta", "alpha"])
        let report = try configured(rows, before: old, after: new, status: false, policy: ordinary)
        try report.validateUnselectedOffsetNames(baselineData: old, currentData: new)
        XCTAssertThrowsError(try check(report, before: old, after: new))
        XCTAssertEqual(report.changes.map(\.key), ["symbol:zeta", "symbol:alpha"])
    }
    private func relocated(_ data: Data, offsets: [UInt64]) throws -> Data {
        var value = try object(data), findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
        var ranges: [[String: Any]] = []
        let hex: (UInt64) -> String = { "0x" + String($0, radix: 16) }
        for index in findings.indices {
            let start = 0x1000 + offsets[index]
            var function = try XCTUnwrap(findings[index]["function"] as? [String: Any])
            function["address"] = hex(start); function["end_address"] = hex(start + 16); function["image_offset"] = hex(offsets[index])
            findings[index]["function"] = function; findings[index]["checked_pcs"] = [hex(start + 8)]
            ranges.append(["start": hex(start), "end": hex(start + 16), "encoding": "0x04000000", "mode": "frame"])
        }
        value["findings"] = findings; value["metadata_ranges"] = ranges
        var image = try XCTUnwrap(value["image"] as? [String: Any]); image["slice_sha256"] = String(repeating: "1", count: 64)
        image["slice_size"] = (offsets.max() ?? 0) + 16; value["image"] = image
        return try JSONSerialization.data(withJSONObject: value)
    }
    func testOffsetsUseLexicalRatherThanNumericOrder() throws {
        let (before, after, sourceRows) = try fixture(["workLow", "workHigh"])
        let old = try relocated(before, offsets: [0x20, 0x100]), new = try relocated(after, offsets: [0x20, 0x100])
        var low = sourceRows[0], high = sourceRows[1]
        low["key"] = "offset:0x20"; high["key"] = "offset:0x100"
        low["match_basis"] = "exact_image_offset"; high["match_basis"] = "exact_image_offset"
        try validate([high, low], before: old, after: new)
        XCTAssertThrowsError(try validate([low, high], before: old, after: new))
    }
    func testManualSymbolAndUnmatchedPrefixesShareOneOrder() throws {
        let (old, new, rows) = try fixture(["pinned", "work", "_entry"])
        let oldExtra = "airsf-" + String(format: "%064x", 18), newExtra = "airsf-" + String(format: "%064x", 34)
        let manualRow = labeled(manualKey, basis: "manual_review", old: oldID, new: newID, name: "pinned")
        let added = labeled("unmatched:after:" + newExtra, basis: "unmatched", label: "added", old: nil, new: newExtra, name: "_entry")
        let removed = labeled("unmatched:before:" + oldExtra, basis: "unmatched", label: "removed", old: oldExtra, new: nil, name: "_entry")
        let ordered = [manualRow, rows[1], added, removed]
        try check(configured(ordered, before: old, after: new, status: false, pins: pin, policy: manual), before: old, after: new)
        XCTAssertThrowsError(try check(configured([rows[1], manualRow, added, removed], before: old, after: new, status: false, pins: pin, policy: manual), before: old, after: new))
    }
    func testBodyPrefixPrecedesManualPrefixDespiteSelectionPrecedence() throws {
        let (old, new, _) = try fixture(["pinned", "_entry"])
        let oldExtra = "airsf-" + String(format: "%064x", 17), newExtra = "airsf-" + String(format: "%064x", 33)
        let key = "body:arm64-exact-bytes-v1:" + String(repeating: "f", count: 64) + ":4"
        let body = labeled(key, basis: "exact_body_candidate", old: oldExtra, new: newExtra, name: "_entry")
        let selected = labeled(manualKey, basis: "manual_review", old: oldID, new: newID, name: "pinned")
        try check(configured([body, selected], before: old, after: new, status: true, pins: pin, policy: manual + bodySuffix), before: old, after: new)
        XCTAssertThrowsError(try check(configured([selected, body], before: old, after: new, status: true, pins: pin, policy: manual + bodySuffix), before: old, after: new))
    }
}
