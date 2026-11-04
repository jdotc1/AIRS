import Foundation
import XCTest
@testable import AIRSCore

final class BodyEnabledRowCoverageTests: XCTestCase {
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

    private func validate(_ rows: [[String: Any]], before: Data, after: Data, status: Bool? = true) throws {
        try check(configured(rows, before: before, after: after, status: status,
                             policy: ordinary + (status == true ? bodySuffix : "")), before: before, after: after)
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
        try report.validateBodyEnabledRowCoverage(baselineData: before, currentData: after)
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
    func testOmittedEligibleBodyPairCannotClaimCoverage() throws {
        let (old, new) = try pair()
        XCTAssertThrowsError(try validate([], before: named(old, "_entry", fingerprint: true), after: named(new, "_entry", fingerprint: true)))
    }
    private func bodyKey(_ digest: String = "f") -> String {
        "body:arm64-exact-bytes-v1:" + String(repeating: digest, count: 64) + ":4"
    }
    private func bodyRow(_ digest: String = "f", old: String? = nil, new: String? = nil,
                         name: String = "_entry", label: String = "unchanged") -> [String: Any] {
        labeled(bodyKey(digest), basis: "exact_body_candidate", label: label,
                old: old ?? oldID, new: new ?? newID, name: name)
    }
    private func bodySources(_ oldName: String = "_entry", _ newName: String = "_entry") throws -> (Data, Data) {
        let (old, new) = try pair()
        return (try named(old, oldName, fingerprint: true), try named(new, newName, fingerprint: true))
    }
    private func empty(_ data: Data) throws -> Data {
        var value = try object(data)
        value["findings"] = []; value["metadata_ranges"] = []
        value["summary"] = ["function_count": 0, "agreement_count": 0, "inconsistency_count": 0,
                            "unresolved_count": 0, "metadata_entry_count": 0, "checked_pc_count": 0]
        return try JSONSerialization.data(withJSONObject: value)
    }
    private func unmatched(_ id: String, side: String, name: String = "_entry") -> [String: Any] {
        labeled("unmatched:" + side + ":" + id, basis: "unmatched", label: side == "after" ? "added" : "removed",
                old: side == "before" ? id : nil, new: side == "after" ? id : nil, name: name)
    }
    private func subtype(_ data: Data, _ subtype: Int) throws -> Data {
        var value = try object(data), image = try XCTUnwrap(value["image"] as? [String: Any])
        image["cpu_subtype"] = subtype; value["image"] = image
        return try JSONSerialization.data(withJSONObject: value)
    }
    func testGeneratedSingletonsAreConsumedByBodyGroup() throws {
        let (old, new) = try bodySources()
        try validate([bodyRow()], before: old, after: new)
    }
    func testRenamedNamedSingletonGroupsAreFullyConsumed() throws {
        let (old, new) = try bodySources("oldWork", "newWork")
        try validate([bodyRow(name: "newWork")], before: old, after: new)
    }
    func testEveryProjectedBodyBucketIsRequired() throws {
        let (old, new) = try bodySources()
        let before = try additional(old, id: unknownID, name: "_entry", digest: "e")
        let after = try additional(new, id: otherNewID, name: "_entry", digest: "e")
        let second = bodyRow("e", old: unknownID, new: otherNewID)
        try validate([second, bodyRow()], before: before, after: after)
        XCTAssertThrowsError(try validate([bodyRow()], before: before, after: after))
    }
    func testEstablishedSymbolPairKeepsPrecedenceOverBodyEvidence() throws {
        let (old, new) = try bodySources("work", "work")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        try validate([value], before: old, after: new)
        XCTAssertThrowsError(try validate([], before: old, after: new))
    }
    func testDuplicateFingerprintsRemainSeparateUnmatchedGroups() throws {
        let (old, new) = try bodySources()
        let before = try additional(old, id: unknownID, name: "_entry")
        let rows = [unmatched(newID, side: "after"), unmatched(oldID, side: "before"), unmatched(unknownID, side: "before")]
        try validate(rows, before: before, after: new)
        XCTAssertThrowsError(try validate(Array(rows.dropLast()), before: before, after: new))
    }
    func testDuplicateSymbolsContinueToBlockBodySelection() throws {
        let (old, new) = try bodySources("work", "_entry")
        let before = try additional(old, id: unknownID, name: "work")
        let symbol = labeled("symbol:work", label: "ambiguous", old: nil, new: nil, name: "work")
        try validate([symbol, unmatched(newID, side: "after")], before: before, after: new)
        XCTAssertThrowsError(try validate([symbol], before: before, after: new))
    }
    func testManualConsumptionCanRemoveBodyDuplicateBlockers() throws {
        let (old, new) = try bodySources()
        let before = try additional(old, id: unknownID, name: "_entry"), after = try additional(new, id: otherNewID, name: "_entry")
        let selected = labeled(manualKey, basis: "manual_review", old: oldID, new: newID, name: "_entry")
        let body = bodyRow(old: unknownID, new: otherNewID)
        try check(configured([body, selected], before: before, after: after, status: true, pins: pin, policy: manual + bodySuffix), before: before, after: after)
        XCTAssertThrowsError(try check(configured([selected], before: before, after: after, status: true, pins: pin, policy: manual + bodySuffix), before: before, after: after))
    }
    func testIncompatibleModelRetainsBodyCoverageAndAmbiguousLabel() throws {
        let (old, new) = try bodySources()
        var value = try object(new), generator = try XCTUnwrap(value["generator"] as? [String: Any])
        generator["analysis_model_version"] = "arm64-bounded-compare-branch-v49"; value["generator"] = generator
        let after = try JSONSerialization.data(withJSONObject: value)
        try validate([bodyRow(label: "ambiguous")], before: old, after: after)
        XCTAssertThrowsError(try validate([], before: old, after: after))
    }
    func testChangedConfigurationRetainsBodyCoverageAndAmbiguousLabel() throws {
        let (old, new) = try bodySources()
        var before = try object(old), after = try object(new)
        before["analysis_config"] = ["limits": ["work": 1]]; after["analysis_config"] = ["limits": ["work": 2]]
        let oldData = try JSONSerialization.data(withJSONObject: before), newData = try JSONSerialization.data(withJSONObject: after)
        try validate([bodyRow(label: "ambiguous")], before: oldData, after: newData)
        XCTAssertThrowsError(try validate([], before: oldData, after: newData))
    }
    func testSubtypeMismatchKeepsOriginalGroups() throws {
        let (old, new) = try bodySources()
        let after = try subtype(new, 1)
        let rows = [unmatched(newID, side: "after"), unmatched(oldID, side: "before")]
        try validate(rows, before: old, after: after)
        XCTAssertThrowsError(try validate([], before: old, after: after))
    }
    func testEqualNonzeroSubtypeAllowsBodySelection() throws {
        let (old, new) = try bodySources()
        try validate([bodyRow()], before: subtype(old, 1), after: subtype(new, 1))
    }
    func testUnicodeDistinctRemainingSymbolsRetainSeparateKeys() throws {
        let (old, new) = try pair()
        let decomposed = "cafe\u{301}", composed = "caf\u{e9}"
        let before = try additional(named(old, decomposed), id: unknownID, name: composed)
        let after = try additional(named(new, decomposed), id: otherNewID, name: composed)
        let first = labeled("symbol:" + decomposed, old: oldID, new: newID, name: decomposed)
        let second = labeled("symbol:" + composed, old: unknownID, new: otherNewID, name: composed)
        try validate([first, second], before: before, after: after)
        XCTAssertThrowsError(try validate([first], before: before, after: after))
    }
    func testEmptyCrossImageSourcesWithExplicitTrueHaveEmptyCoverage() throws {
        let (old, new) = try pair()
        try validate([], before: empty(old), after: empty(new))
    }
    func testMissingStatusRefusesEvenEmptyCoverage() throws {
        let (old, new) = try pair()
        XCTAssertThrowsError(try validate([], before: empty(old), after: empty(new), status: nil))
    }
    func testDisabledStatusRefusesEvenEmptyCoverage() throws {
        let (old, new) = try pair()
        XCTAssertThrowsError(try validate([], before: empty(old), after: empty(new), status: false))
    }
    func testSameImageRefusesEvenEmptyCoverage() throws {
        let old = try empty(source("before", id: oldID, digest: "1"))
        let new = try empty(source("after", id: newID, digest: "1"))
        XCTAssertThrowsError(try validate([], before: old, after: new))
    }
    func testEarlierBoundaryRetainsOmittedBodyRowScope() throws {
        let (old, new) = try bodySources()
        let report = try configured([], before: old, after: new, status: true, policy: ordinary + bodySuffix)
        try report.validateCanonicalRowOrder(baselineData: old, currentData: new)
        XCTAssertThrowsError(try check(report, before: old, after: new))
        XCTAssertTrue(report.changes.isEmpty)
    }
    func testUnconsumedGroupIsRequiredAlongsideBodyPair() throws {
        let (old, new) = try bodySources()
        let before = try additional(old, id: unknownID, name: "_entry", digest: "e")
        let removed = unmatched(unknownID, side: "before")
        try validate([bodyRow(), removed], before: before, after: new)
        XCTAssertThrowsError(try validate([bodyRow()], before: before, after: new))
    }
    func testCoveredBodyKeyCannotBypassSelectedNameProof() throws {
        let (old, new) = try bodySources()
        XCTAssertThrowsError(try validate([bodyRow(name: "unrelated")], before: old, after: new))
    }
}
