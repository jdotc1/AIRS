import Foundation
import XCTest
@testable import AIRSCore

final class SelectedFunctionNamesTests: XCTestCase {
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
        try report.validateSelectedFunctionNames(baselineData: before, currentData: after)
    }

    func testUnrelatedLabelCannotBorrowSelectedManualPair() throws {
        let (old, new) = try pair()
        let key = "manual:" + oldID + ":" + newID
        var value = try wire([row(key, basis: "manual_review", old: oldID, new: newID)], before: old, after: new)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any])
        context["manual_pairs"] = [["baseline_id": oldID, "current_id": newID]]
        context["matching_policy"] = "manual_then_unique_symbol"; value["comparison"] = context
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        XCTAssertThrowsError(try report.validateSelectedFunctionNames(baselineData: old, currentData: new))
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
        try report.validateSelectedFunctionNames(baselineData: before, currentData: after)
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
    func testCurrentManualSourceNameTakesPrecedenceOverBaselineAndImageLabels() throws {
        let (old, new) = try pair()
        let before = try named(old, "oldFunction"), after = try named(new, "newFunction")
        XCTAssertNoThrow(try manualLabel("newFunction", before: before, after: after))
        for name in ["oldFunction", "before", "after", "0x1000", "Candidate"] {
            XCTAssertThrowsError(try manualLabel(name, before: before, after: after))
        }
    }
    func testBaselineOnlyAndCurrentOnlyRowsBindTheirOwnNames() throws {
        let (old, new) = try pair()
        let removed = labeled("symbol:before", label: "removed", old: oldID, new: nil, name: "before")
        let added = labeled("symbol:after", label: "added", old: nil, new: newID, name: "after")
        XCTAssertNoThrow(try check(configured([removed, added], before: old, after: new, policy: ordinary), before: old, after: new))
        let wrongRemoved = labeled("symbol:before", label: "removed", old: oldID, new: nil, name: "after")
        let wrongAdded = labeled("symbol:after", label: "added", old: nil, new: newID, name: "before")
        XCTAssertThrowsError(try check(configured([wrongRemoved], before: old, after: new, policy: ordinary), before: old, after: new))
        XCTAssertThrowsError(try check(configured([wrongAdded], before: old, after: new, policy: ordinary), before: old, after: new))
    }
    func testEmptySourceNameDoesNotBecomeAddressDisplayFallback() throws {
        let (old, new) = try pair()
        let before = try named(old, "_entry"), after = try named(new, "")
        XCTAssertNoThrow(try manualLabel("", before: before, after: after))
        XCTAssertThrowsError(try manualLabel("0x1000", before: before, after: after))
        XCTAssertThrowsError(try manualLabel("_entry", before: before, after: after))
    }
    func testGeneratedUnmatchedNameRemainsExactSourceText() throws {
        let (old, new) = try pair()
        let before = try named(old, "sub_Old"), after = try named(new, "sub_New")
        let key = "unmatched:after:" + newID
        let right = labeled(key, basis: "unmatched", label: "added", old: nil, new: newID, name: "sub_New")
        XCTAssertNoThrow(try check(configured([right], before: before, after: after, policy: ordinary), before: before, after: after))
        let wrong = labeled(key, basis: "unmatched", label: "added", old: nil, new: newID, name: "sub_new")
        XCTAssertThrowsError(try check(configured([wrong], before: before, after: after, policy: ordinary), before: before, after: after))
    }
    func testCanonicallyEquivalentUnicodeNamesAreNotCollapsed() throws {
        let (old, new) = try pair()
        let after = try named(new, "e\u{301}")
        XCTAssertNoThrow(try manualLabel("e\u{301}", before: old, after: after))
        XCTAssertThrowsError(try manualLabel("\u{e9}", before: old, after: after))
    }
    func testCaseAndWhitespaceAreNotNormalized() throws {
        let (old, new) = try pair()
        let after = try named(new, " Work ")
        XCTAssertNoThrow(try manualLabel(" Work ", before: old, after: after))
        for name in ["Work", " work ", " Work", "Work "] {
            XCTAssertThrowsError(try manualLabel(name, before: old, after: after))
        }
    }
    func testBodyPairUsesSelectedCurrentGeneratedName() throws {
        let (old, new) = try pair()
        let before = try named(old, "sub_old", fingerprint: true), after = try named(new, "sub_new", fingerprint: true)
        let key = "body:arm64-exact-bytes-v1:" + String(repeating: "f", count: 64) + ":4"
        let right = labeled(key, basis: "exact_body_candidate", old: oldID, new: newID, name: "sub_new")
        let wrong = labeled(key, basis: "exact_body_candidate", old: oldID, new: newID, name: "sub_old")
        XCTAssertNoThrow(try check(configured([right], before: before, after: after, status: true, policy: ordinary + bodySuffix), before: before, after: after))
        XCTAssertThrowsError(try check(configured([wrong], before: before, after: after, status: true, policy: ordinary + bodySuffix), before: before, after: after))
    }
    func testSameImageOffsetPairStillUsesCurrentSourceName() throws {
        let old = try named(source("before", id: oldID, digest: "1"), "oldFunction")
        let new = try named(source("after", id: newID, digest: "1"), "newFunction")
        let right = labeled("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID, name: "newFunction")
        let wrong = labeled("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID, name: "oldFunction")
        XCTAssertNoThrow(try check(configured([right], before: old, after: new, policy: ordinary), before: old, after: new))
        XCTAssertThrowsError(try check(configured([wrong], before: old, after: new, policy: ordinary), before: old, after: new))
    }
    func testOneSidedAmbiguityUsesItsSelectedSingleton() throws {
        let (old, new) = try pair()
        let before = try named(old, "work"), after = try named(new, "work")
        let oldDuplicate = try additional(before, id: unknownID, name: "work")
        let newDuplicate = try additional(after, id: otherNewID, name: "work")
        let current = labeled("symbol:work", label: "ambiguous", old: nil, new: newID, name: "work")
        let baseline = labeled("symbol:work", label: "ambiguous", old: oldID, new: nil, name: "work")
        XCTAssertNoThrow(try check(configured([current], before: oldDuplicate, after: after, policy: ordinary), before: oldDuplicate, after: after))
        XCTAssertNoThrow(try check(configured([baseline], before: before, after: newDuplicate, policy: ordinary), before: before, after: newDuplicate))
        let wrong = labeled("symbol:work", label: "ambiguous", old: oldID, new: nil, name: "after")
        XCTAssertThrowsError(try check(configured([wrong], before: before, after: newDuplicate, policy: ordinary), before: before, after: newDuplicate))
    }
    func testUnselectedGroupLabelsRemainExplicitlyUnverified() throws {
        let (old, new) = try pair()
        let before = try additional(named(old, "work"), id: unknownID, name: "work")
        let after = try additional(named(new, "work"), id: otherNewID, name: "work")
        let group = labeled("symbol:work", label: "ambiguous", old: nil, new: nil, name: "Unverified group label")
        XCTAssertNoThrow(try check(configured([group], before: before, after: after, policy: ordinary), before: before, after: after))
    }
    func testConfigurationAmbiguityDoesNotDisableSourceNameBinding() throws {
        let (old, new) = try pair()
        var value = try object(new); value["analysis_config"] = ["limits": ["work": 1]]
        let after = try JSONSerialization.data(withJSONObject: value)
        XCTAssertNoThrow(try manualLabel("after", before: old, after: after, label: "ambiguous"))
        XCTAssertThrowsError(try manualLabel("before", before: old, after: after, label: "ambiguous"))
        XCTAssertThrowsError(try manualLabel("after", before: old, after: after))
    }
    func testCorrectNameCannotRepairSourceOrManualKeyClaims() throws {
        let (old, new) = try pair()
        var stale = labeled(manualKey, basis: "manual_review", old: oldID, new: newID, name: "after")
        stale["after_scope"] = "metadata_only"
        XCTAssertThrowsError(try check(configured([stale], before: old, after: new, pins: pin, policy: manual), before: old, after: new))
        let wrongKey = labeled("manual:chosen", basis: "manual_review", old: oldID, new: newID, name: "after")
        XCTAssertThrowsError(try check(configured([wrongKey], before: old, after: new, pins: pin, policy: manual), before: old, after: new))
    }
    func testEarlierKeyApiKeepsItsNameLabelBoundary() throws {
        let (old, new) = try pair()
        let named = labeled(manualKey, basis: "manual_review", old: oldID, new: newID, name: "Legacy label")
        let report = try configured([named], before: old, after: new, pins: pin, policy: manual)
        XCTAssertNoThrow(try report.validateManualPairKeys(baselineData: old, currentData: new))
        XCTAssertThrowsError(try check(report, before: old, after: new))
        XCTAssertEqual(report.changes.first?.functionName, "Legacy label")
    }
    func testEmptyAndPartialComparisonsDoNotClaimCompleteness() throws {
        let (old, new) = try pair()
        let empty = try configured([], before: old, after: new, policy: ordinary)
        XCTAssertNoThrow(try check(empty, before: old, after: new))
        XCTAssertNil(empty.comparison.exactBodyCandidates)
        let one = labeled("symbol:before", label: "removed", old: oldID, new: nil, name: "before")
        XCTAssertNoThrow(try check(configured([one], before: old, after: new, policy: ordinary), before: old, after: new))
    }
    func testEqualIDsAcrossSourcesStillUseCurrentReportSide() throws {
        let before = try named(source("before", id: oldID, digest: "1"), "oldFunction")
        let after = try named(source("after", id: oldID, digest: "2"), "newFunction")
        let pins = [["baseline_id": oldID, "current_id": oldID]]
        let key = "manual:" + oldID + ":" + oldID
        let right = labeled(key, basis: "manual_review", old: oldID, new: oldID, name: "newFunction")
        let wrong = labeled(key, basis: "manual_review", old: oldID, new: oldID, name: "oldFunction")
        XCTAssertNoThrow(try check(configured([right], before: before, after: after, pins: pins, policy: manual), before: before, after: after))
        XCTAssertThrowsError(try check(configured([wrong], before: before, after: after, pins: pins, policy: manual), before: before, after: after))
    }
}
