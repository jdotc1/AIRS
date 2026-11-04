import Foundation
import XCTest
@testable import AIRSCore

final class UnselectedSymbolNamesTests: XCTestCase {
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
        try report.validateUnselectedSymbolNames(baselineData: before, currentData: after)
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
        try report.validateUnselectedSymbolNames(baselineData: before, currentData: after)
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
    func testUnselectedSymbolGroupCannotBorrowUnrelatedLabel() throws {
        let (old, new) = try pair()
        let before = try additional(named(old, "work"), id: unknownID, name: "work")
        let group = labeled("symbol:work", label: "ambiguous", old: nil, new: nil, name: "Unrelated")
        XCTAssertThrowsError(try check(configured([group], before: before, after: new, policy: ordinary), before: before, after: new))
    }
    private func group(_ name: String, oldCount: Int, newCount: Int, display: String? = nil,
                       status: Bool? = nil) throws {
        let (old, new) = try pair()
        var before = try named(old, oldCount == 0 ? "otherOld" : name)
        var after = try named(new, newCount == 0 ? "otherNew" : name)
        if oldCount == 2 { before = try additional(before, id: unknownID, name: name) }
        if newCount == 2 { after = try additional(after, id: otherNewID, name: name) }
        let value = labeled("symbol:" + name, label: "ambiguous", old: nil, new: nil, name: display ?? name)
        let policy = ordinary + (status == true ? bodySuffix : "")
        try check(configured([value], before: before, after: after, status: status, policy: policy), before: before, after: after)
    }
    func testBaselineOnlyDuplicateName() throws {
        try group("work", oldCount: 2, newCount: 0)
        XCTAssertThrowsError(try group("work", oldCount: 2, newCount: 0, display: "otherOld"))
    }
    func testCurrentOnlyDuplicateName() throws {
        try group("work", oldCount: 0, newCount: 2)
        XCTAssertThrowsError(try group("work", oldCount: 0, newCount: 2, display: "otherNew"))
    }
    func testBothDuplicateSides() throws {
        try group("work", oldCount: 2, newCount: 2)
        XCTAssertThrowsError(try group("work", oldCount: 2, newCount: 2, display: "0x1000"))
    }
    func testUnicodeBytesAreNotNormalized() throws {
        try group("caf\u{e9}", oldCount: 2, newCount: 2)
        XCTAssertThrowsError(try group("caf\u{e9}", oldCount: 2, newCount: 2, display: "cafe\u{301}"))
    }
    func testLeadingCombiningMarkUsesBytePrefix() throws {
        try group("\u{301}work", oldCount: 2, newCount: 0)
        XCTAssertThrowsError(try group("\u{301}work", oldCount: 2, newCount: 0, display: "work"))
    }
    func testPunctuationCaseAndSpacingAreExact() throws {
        try group(" Work:variant ", oldCount: 0, newCount: 2)
        XCTAssertThrowsError(try group(" Work:variant ", oldCount: 0, newCount: 2, display: "work:variant"))
    }
    func testBodyStatusDoesNotAlterDuplicateGroupNames() throws {
        for status: Bool? in [nil, false, true] {
            try group("work", oldCount: 2, newCount: 2, status: status)
            XCTAssertThrowsError(try group("work", oldCount: 2, newCount: 2, display: "unrelated", status: status))
        }
    }
    func testGeneratedNameCannotEstablishSymbolGroup() throws {
        for name in ["", "_entry", "sub_1000"] {
            XCTAssertThrowsError(try group(name, oldCount: 2, newCount: 0))
        }
    }
    func testEarlierSelectedNameBoundaryRetainsItsScope() throws {
        let (old, new) = try pair()
        let before = try additional(named(old, "work"), id: unknownID, name: "work")
        let value = labeled("symbol:work", label: "ambiguous", old: nil, new: nil, name: "unrelated")
        let report = try configured([value], before: before, after: new, policy: ordinary)
        try report.validateSelectedFunctionNames(baselineData: before, currentData: new)
        XCTAssertThrowsError(try check(report, before: before, after: new))
        XCTAssertEqual(report.changes[0].functionName, "unrelated")
    }
    func testSelectedCurrentNameStillTakesPrecedence() throws {
        let (old, new) = try pair()
        let before = try named(old, "work"), after = try named(new, "work")
        try validate([labeled("symbol:work", old: oldID, new: newID, name: "work")], before: before, after: after)
        XCTAssertThrowsError(try validate([labeled("symbol:work", old: oldID, new: newID, name: "wrong")], before: before, after: after))
    }
    func testManualPinCannotLeaveInventedDuplicateGroup() throws {
        let (old, new) = try pair()
        let before = try additional(named(old, "work"), id: unknownID, name: "work")
        let after = try additional(named(new, "work"), id: otherNewID, name: "work")
        let manualRow = labeled(manualKey, basis: "manual_review", old: oldID, new: newID, name: "work")
        let invented = labeled("symbol:work", label: "ambiguous", old: nil, new: nil, name: "work")
        XCTAssertThrowsError(try check(configured([manualRow, invented], before: before, after: after, pins: pin, policy: manual), before: before, after: after))
        let remaining = labeled("symbol:work", old: unknownID, new: otherNewID, name: "work")
        try check(configured([manualRow, remaining], before: before, after: after, pins: pin, policy: manual), before: before, after: after)
    }
    func testEmptyPartialOutputRemainsAllowed() throws {
        let (old, new) = try pair()
        try check(configured([], before: old, after: new, policy: ordinary), before: old, after: new)
    }
}
