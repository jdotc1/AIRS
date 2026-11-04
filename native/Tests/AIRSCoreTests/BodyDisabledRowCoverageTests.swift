import Foundation
import XCTest
@testable import AIRSCore

final class BodyDisabledRowCoverageTests: XCTestCase {
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
        try report.validateBodyDisabledRowCoverage(baselineData: before, currentData: after)
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
        try report.validateBodyDisabledRowCoverage(baselineData: before, currentData: after)
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
    func testOmittedCrossImageGroupCannotClaimCoverage() throws {
        let (old, new) = try pair()
        let before = try additional(named(old, "work"), id: unknownID, name: "other")
        let after = try named(new, "work")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        XCTAssertThrowsError(try validate([value], before: before, after: after))
    }
    private func empty(_ data: Data) throws -> Data {
        var value = try object(data)
        value["findings"] = []; value["metadata_ranges"] = []
        value["summary"] = ["function_count": 0, "agreement_count": 0, "inconsistency_count": 0,
                            "unresolved_count": 0, "metadata_entry_count": 0, "checked_pc_count": 0]
        return try JSONSerialization.data(withJSONObject: value)
    }
    private func workPair() throws -> (Data, Data) {
        let (old, new) = try pair(); return (try named(old, "work"), try named(new, "work"))
    }
    private var workRow: [String: Any] { labeled("symbol:work", old: oldID, new: newID, name: "work") }
    private func duplicateGroup(oldCount: Int, newCount: Int) throws {
        let (old, new) = try workPair()
        let before = try oldCount == 0 ? empty(old) : additional(old, id: unknownID, name: "work")
        let after = try newCount == 0 ? empty(new) : additional(new, id: otherNewID, name: "work")
        let value = labeled("symbol:work", label: "ambiguous", old: nil, new: nil, name: "work")
        try validate([value], before: before, after: after)
        XCTAssertThrowsError(try validate([], before: before, after: after))
    }
    func testSharedAndOneSidedSymbolGroupsAreCovered() throws {
        let (old, new) = try workPair()
        let before = try additional(old, id: unknownID, name: "other")
        let removed = labeled("symbol:other", label: "removed", old: unknownID, new: nil, name: "other")
        try validate([removed, workRow], before: before, after: new)
    }
    func testBaselineOnlyDuplicateGroupHasOneRow() throws { try duplicateGroup(oldCount: 2, newCount: 0) }
    func testCurrentOnlyDuplicateGroupHasOneRow() throws { try duplicateGroup(oldCount: 0, newCount: 2) }
    func testTwoSidedDuplicateGroupHasOneRow() throws { try duplicateGroup(oldCount: 2, newCount: 2) }
    private func unmatched(_ before: Data, _ after: Data, name: String) throws {
        let added = labeled("unmatched:after:" + newID, basis: "unmatched", label: "added", old: nil, new: newID, name: name)
        let removed = labeled("unmatched:before:" + oldID, basis: "unmatched", label: "removed", old: oldID, new: nil, name: name)
        try validate([added, removed], before: before, after: after)
        XCTAssertThrowsError(try validate([added], before: before, after: after))
    }
    func testEqualGeneratedNamesRemainTwoSideSpecificGroups() throws {
        let (old, new) = try pair()
        for name in ["", "_entry", "__text", "sub_1000", "loc_0xA"] {
            try unmatched(named(old, name), named(new, name), name: name)
        }
    }
    func testUnicodeDistinctSymbolSpellingsRemainSeparateGroups() throws {
        let (old, new) = try pair()
        let decomposed = "cafe\u{301}", composed = "caf\u{e9}"
        let before = try additional(named(old, decomposed), id: unknownID, name: composed)
        let after = try additional(named(new, decomposed), id: otherNewID, name: composed)
        let first = labeled("symbol:" + decomposed, old: oldID, new: newID, name: decomposed)
        let second = labeled("symbol:" + composed, old: unknownID, new: otherNewID, name: composed)
        try validate([first, second], before: before, after: after)
        XCTAssertThrowsError(try validate([first], before: before, after: after))
    }
    func testManualPinsAreRemovedBeforeDuplicateNameGrouping() throws {
        let (old, new) = try workPair()
        let before = try additional(old, id: unknownID, name: "work"), after = try additional(new, id: otherNewID, name: "work")
        let selected = labeled(manualKey, basis: "manual_review", old: oldID, new: newID, name: "work")
        let remaining = labeled("symbol:work", old: unknownID, new: otherNewID, name: "work")
        try check(configured([selected, remaining], before: before, after: after, status: false, pins: pin, policy: manual), before: before, after: after)
        XCTAssertThrowsError(try check(configured([selected], before: before, after: after, status: false, pins: pin, policy: manual), before: before, after: after))
    }
    func testAllPinnedSourcesRequireOnlyManualGroup() throws {
        let (old, new) = try workPair()
        let value = labeled(manualKey, basis: "manual_review", old: oldID, new: newID, name: "work")
        try check(configured([value], before: old, after: new, status: false, pins: pin, policy: manual), before: old, after: new)
    }
    func testEarlierBoundaryStillAcceptsOrderedPartialRows() throws {
        let (old, new) = try workPair()
        let before = try additional(old, id: unknownID, name: "other")
        let report = try configured([workRow], before: before, after: new, status: false, policy: ordinary)
        try report.validateCanonicalRowOrder(baselineData: before, currentData: new)
        XCTAssertThrowsError(try check(report, before: before, after: new))
        XCTAssertEqual(report.changes.map(\.key), ["symbol:work"])
    }
    func testEmptyCrossImageSnapshotsWithExplicitFalseHaveEmptyCoverage() throws {
        let (old, new) = try pair()
        try validate([], before: empty(old), after: empty(new))
    }
    func testMissingBodyStatusRefusesEvenEmptyCoverage() throws {
        let (old, new) = try pair(), before = try empty(old), after = try empty(new)
        XCTAssertThrowsError(try check(configured([], before: before, after: after, policy: ordinary), before: before, after: after))
    }
    func testEnabledBodyMatchingRefusesEvenEmptyCoverage() throws {
        let (old, new) = try pair(), before = try empty(old), after = try empty(new)
        XCTAssertThrowsError(try check(configured([], before: before, after: after, status: true, policy: ordinary + bodySuffix), before: before, after: after))
    }
    func testSameImageRefusesEvenEmptyCoverage() throws {
        let old = try empty(source("before", id: oldID, digest: "1"))
        let new = try empty(source("after", id: newID, digest: "1"))
        XCTAssertThrowsError(try validate([], before: old, after: new))
    }
    func testUnsuffixedPolicyDoesNotBackfillMissingBodyStatus() throws {
        let (old, new) = try workPair()
        let report = try configured([workRow], before: old, after: new, policy: ordinary)
        try report.validateCanonicalRowOrder(baselineData: old, currentData: new)
        XCTAssertThrowsError(try check(report, before: old, after: new))
        XCTAssertNil(report.comparison.exactBodyCandidates)
    }
    func testEqualRowCountCannotSubstituteForeignKey() throws {
        let (old, new) = try workPair()
        var wrong = workRow; wrong["key"] = "symbol:foreign"
        XCTAssertThrowsError(try validate([wrong], before: old, after: new))
    }
    func testCoveredKeysCannotBypassSelectedNameProof() throws {
        let (old, new) = try workPair()
        var wrong = workRow; wrong["function_name"] = "unrelated"
        XCTAssertThrowsError(try validate([wrong], before: old, after: new))
    }
    func testImportedBodyEvidenceDoesNotEnableMatching() throws {
        let (old, new) = try pair()
        try unmatched(named(old, "_entry", fingerprint: true), named(new, "_entry", fingerprint: true), name: "_entry")
    }
}
