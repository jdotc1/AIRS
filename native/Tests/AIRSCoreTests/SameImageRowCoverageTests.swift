import Foundation
import XCTest
@testable import AIRSCore

final class SameImageRowCoverageTests: XCTestCase {
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
            "same_image": (oldImage["slice_sha256"] as? String) == (newImage["slice_sha256"] as? String) && (oldImage["architecture"] as? String) == (newImage["architecture"] as? String),
            "model_compatible": (oldGenerator["analysis_model_version"] as? String) == (newGenerator["analysis_model_version"] as? String) && (oldImage["architecture"] as? String) == (newImage["architecture"] as? String),
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
        try report.validateSameImageRowCoverage(baselineData: before, currentData: after)
    }

    private func sameImagePair() throws -> (Data, Data) {
        (try source("before", id: oldID, digest: "1"), try source("after", id: newID, digest: "1"))
    }

    private func changed(_ data: Data, top: [String: Any] = [:], fields: [String: Any] = [:], function: [String: Any] = [:]) throws -> Data {
        var report = try object(data)
        for (key, value) in top { report[key] = value }
        var findings = try XCTUnwrap(report["findings"] as? [[String: Any]])
        for (key, value) in fields { findings[0][key] = value }
        var info = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        for (key, value) in function { info[key] = value }
        findings[0]["function"] = info; report["findings"] = findings
        return try JSONSerialization.data(withJSONObject: report)
    }

    private func moved(_ data: Data, offset: UInt64, base: UInt64 = 0x1000) throws -> Data {
        let hex: (UInt64) -> String = { "0x" + String($0, radix: 16) }
        var image = try XCTUnwrap(object(data)["image"] as? [String: Any]); image["preferred_base"] = hex(base); image["slice_size"] = offset + 16
        return try changed(data,
            top: ["image": image, "metadata_ranges": [["start": hex(base + offset), "end": hex(base + offset + 16), "encoding": "0x04000000", "mode": "frame"]]],
            fields: ["checked_pcs": [hex(base + offset + 8)]],
            function: ["address": hex(base + offset), "end_address": hex(base + offset + 16), "image_offset": hex(offset)])
    }

    private func additional(_ data: Data, id: String, offset: UInt64) throws -> Data {
        var report = try object(data), findings = try XCTUnwrap(object(data)["findings"] as? [[String: Any]])
        let addition = try moved(data, offset: offset)
        var extra = try XCTUnwrap(object(addition)["findings"] as? [[String: Any]])[0]; extra["id"] = id; findings.append(extra); report["findings"] = findings
        var ranges = try XCTUnwrap(report["metadata_ranges"] as? [[String: Any]])
        if offset != 0 { ranges += try XCTUnwrap(object(addition)["metadata_ranges"] as? [[String: Any]]) }
        report["metadata_ranges"] = ranges
        report["summary"] = ["function_count": 2, "agreement_count": 2, "inconsistency_count": 0, "unresolved_count": 0, "metadata_entry_count": ranges.count, "checked_pc_count": 2]
        var image = try XCTUnwrap(report["image"] as? [String: Any]); image["slice_size"] = max(16, offset + 16); report["image"] = image
        return try JSONSerialization.data(withJSONObject: report)
    }

    private func labeled(_ name: String) -> [String: Any] {
        var value = row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: nil, new: nil)
        value["function_name"] = name; return value
    }
    private let otherNewID = "airsf-" + String(repeating: "d", count: 64)
    private func selected(_ key: String, old: String?, new: String?, name: String, label: String = "unchanged") -> [String: Any] {
        var value = row(key, basis: "exact_image_offset", label: label, old: old, new: new)
        value["function_name"] = name; return value
    }
    private func twoGroups() throws -> (Data, Data) {
        let (before, after) = try sameImagePair()
        return (try additional(before, id: unknownID, offset: 0x20), try additional(after, id: otherNewID, offset: 0x20))
    }
    private var firstRow: [String: Any] { selected("offset:0x0", old: oldID, new: newID, name: "after") }
    private var secondRow: [String: Any] { selected("offset:0x20", old: unknownID, new: otherNewID, name: "after") }
    func testOmittedSameImageGroupCannotClaimCoverage() throws {
        let (before, after) = try twoGroups()
        XCTAssertThrowsError(try validate([firstRow], before: before, after: after))
    }
    private func empty(_ data: Data) throws -> Data {
        var value = try object(data)
        value["findings"] = []; value["metadata_ranges"] = []
        value["summary"] = ["function_count": 0, "agreement_count": 0, "inconsistency_count": 0,
                            "unresolved_count": 0, "metadata_entry_count": 0, "checked_pc_count": 0]
        return try JSONSerialization.data(withJSONObject: value)
    }
    func testAllSharedGroupsAreCovered() throws {
        let (before, after) = try twoGroups()
        try validate([firstRow, secondRow], before: before, after: after)
    }
    func testBaselineOnlyGroupIsRequired() throws {
        let (before, after) = try sameImagePair()
        let old = try additional(before, id: unknownID, offset: 0x20)
        let removed = selected("offset:0x20", old: unknownID, new: nil, name: "before", label: "removed")
        try validate([firstRow, removed], before: old, after: after)
        XCTAssertThrowsError(try validate([firstRow], before: old, after: after))
    }
    func testCurrentOnlyGroupIsRequired() throws {
        let (before, after) = try sameImagePair()
        let new = try additional(after, id: otherNewID, offset: 0x20)
        let added = selected("offset:0x20", old: nil, new: otherNewID, name: "after", label: "added")
        try validate([firstRow, added], before: before, after: new)
        XCTAssertThrowsError(try validate([firstRow], before: before, after: new))
    }
    func testDisjointSourceGroupsRequireUnion() throws {
        let (before, after) = try sameImagePair()
        let new = try moved(after, offset: 0x20)
        let removed = selected("offset:0x0", old: oldID, new: nil, name: "before", label: "removed")
        let added = selected("offset:0x20", old: nil, new: newID, name: "after", label: "added")
        try validate([removed, added], before: before, after: new)
        XCTAssertThrowsError(try validate([removed], before: before, after: new))
        XCTAssertThrowsError(try validate([added], before: before, after: new))
    }
    func testBothDuplicateGroupsRequireOneRowRatherThanFindingCount() throws {
        let (before, after) = try sameImagePair()
        let old = try additional(before, id: unknownID, offset: 0), new = try additional(after, id: otherNewID, offset: 0)
        try validate([labeled("after")], before: old, after: new)
    }
    func testDuplicateBaselineAndSingletonCurrentStillHaveOneGroup() throws {
        let (before, after) = try sameImagePair()
        let old = try additional(before, id: unknownID, offset: 0)
        let value = selected("offset:0x0", old: nil, new: newID, name: "after", label: "ambiguous")
        try validate([value], before: old, after: after)
    }
    func testAlternateSourceHexSpellingsCollapseNumerically() throws {
        let (before, after) = try sameImagePair()
        let old = try changed(additional(before, id: unknownID, offset: 0), function: ["image_offset": "0x0000"])
        let new = try changed(after, function: ["image_offset": "0x00"])
        let value = selected("offset:0x0", old: nil, new: newID, name: "after", label: "ambiguous")
        try validate([value], before: old, after: new)
    }
    func testBothEmptySameImageSnapshotsHaveEmptyCoverage() throws {
        let (before, after) = try sameImagePair()
        try validate([], before: empty(before), after: empty(after))
    }
    func testEmptyBaselineRequiresCurrentGroups() throws {
        let (before, after) = try sameImagePair()
        let old = try empty(before)
        let value = selected("offset:0x0", old: nil, new: newID, name: "after", label: "added")
        try validate([value], before: old, after: after)
        XCTAssertThrowsError(try validate([], before: old, after: after))
    }
    func testEmptyCurrentRequiresBaselineGroups() throws {
        let (before, after) = try sameImagePair()
        let new = try empty(after)
        let value = selected("offset:0x0", old: oldID, new: nil, name: "before", label: "removed")
        try validate([value], before: before, after: new)
        XCTAssertThrowsError(try validate([], before: before, after: new))
    }
    func testCrossImageRefusesEvenWhenBothSnapshotsAreEmpty() throws {
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate([], before: empty(before), after: empty(after)))
    }
    func testEarlierBoundaryRetainsOrderedPartialOutput() throws {
        let (before, after) = try twoGroups()
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: wire([firstRow], before: before, after: after)))
        try report.validateCanonicalRowOrder(baselineData: before, currentData: after)
        XCTAssertThrowsError(try report.validateSameImageRowCoverage(baselineData: before, currentData: after))
        XCTAssertEqual(report.changes.map(\.key), ["offset:0x0"])
    }
    func testCompleteKeysCannotBypassNameOrClassificationProof() throws {
        let (before, after) = try twoGroups()
        var wrong = firstRow; wrong["function_name"] = "unrelated"
        XCTAssertThrowsError(try validate([wrong, secondRow], before: before, after: after))
        wrong = firstRow; wrong["change"] = "changed"
        XCTAssertThrowsError(try validate([wrong, secondRow], before: before, after: after))
    }
    func testEqualRowCountCannotReplaceMissingSourceGroup() throws {
        let (before, after) = try twoGroups()
        var wrong = secondRow; wrong["key"] = "offset:0x40"
        XCTAssertThrowsError(try validate([firstRow, wrong], before: before, after: after))
    }
    func testCompleteCoverageStillUsesLexicalKeyOrder() throws {
        let (before, after) = try sameImagePair()
        let old = try additional(moved(before, offset: 0x20), id: unknownID, offset: 0x100)
        let new = try additional(moved(after, offset: 0x20), id: otherNewID, offset: 0x100)
        let low = selected("offset:0x20", old: oldID, new: newID, name: "after")
        let high = selected("offset:0x100", old: unknownID, new: otherNewID, name: "after")
        try validate([high, low], before: old, after: new)
        XCTAssertThrowsError(try validate([low, high], before: old, after: new))
    }
    func testNonemptySourceGroupsCannotAllBeOmitted() throws {
        let (before, after) = try sameImagePair()
        XCTAssertThrowsError(try validate([], before: before, after: after))
    }
}
