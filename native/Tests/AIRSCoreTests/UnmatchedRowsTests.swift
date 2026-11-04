import Foundation
import XCTest
@testable import AIRSCore

final class UnmatchedRowsTests: XCTestCase {
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
            "exact_body_candidates": true, "matching_policy": "exact_digest_then_unique_symbol_then_exact_body_candidate"]
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
        try report.validateUnmatchedRows(baselineData: before, currentData: after)
    }

    func testUsableSymbolCannotClaimUnmatchedBasis() throws {
        let (old, new) = try pair()
        XCTAssertThrowsError(try validate([row("unmatched:before:" + oldID, basis: "unmatched", label: "removed", old: oldID, new: nil)], before: old, after: new))
    }
    private let otherNewID = "airsf-" + String(repeating: "d", count: 64)
    private let extraID = "airsf-" + String(repeating: "e", count: 64)
    private var bodyKey: String { "body:arm64-exact-bytes-v1:" + String(repeating: "f", count: 64) + ":4" }
    private func bodyRow(label: String = "unchanged") -> [String: Any] {
        row(bodyKey, basis: "exact_body_candidate", label: label, old: oldID, new: newID)
    }
    private func annotated(_ data: Data, name: String = "_entry", digest: String = "f", count: Int = 4) throws -> Data {
        var report = try object(data), findings = try XCTUnwrap(object(data)["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        function["name"] = name; function["size"] = count * 4
        function["end_address"] = "0x" + String(0x1000 + count * 4, radix: 16)
        function["body_fingerprint"] = ["kind": "arm64-exact-bytes-v1", "sha256": String(repeating: digest, count: 64), "instruction_count": count]
        findings[0]["function"] = function; findings[0]["instruction_count"] = count; report["findings"] = findings
        report["metadata_ranges"] = [["start": "0x1000", "end": function["end_address"]!, "encoding": "0x04000000", "mode": "frame"]]
        var image = try XCTUnwrap(report["image"] as? [String: Any]); image["slice_size"] = count * 4; report["image"] = image
        return try JSONSerialization.data(withJSONObject: report)
    }
    private func bodies() throws -> (Data, Data) {
        let (old, new) = try pair(); return (try annotated(old), try annotated(new))
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
    private func validateWire(_ value: [String: Any], before: Data, after: Data) throws {
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        try report.validateUnmatchedRows(baselineData: before, currentData: after)
    }
    private func renamed(_ data: Data, _ name: Any) throws -> Data {
        var value = try object(data), findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
        var info = try XCTUnwrap(findings[0]["function"] as? [String: Any]); info["name"] = name
        findings[0]["function"] = info; value["findings"] = findings
        return try JSONSerialization.data(withJSONObject: value)
    }
    private func plainUnmatched(_ name: String = "_entry") throws -> (Data, Data) {
        let (old, new) = try pair(); return (try renamed(old, name), try renamed(new, name))
    }
    private func unmatchedOld(_ id: String? = nil, label: String = "removed") -> [String: Any] {
        let selected = id ?? oldID
        return row("unmatched:before:" + selected, basis: "unmatched", label: label, old: selected, new: nil)
    }
    private func unmatchedNew(_ id: String? = nil, label: String = "added") -> [String: Any] {
        let selected = id ?? newID
        return row("unmatched:after:" + selected, basis: "unmatched", label: label, old: nil, new: selected)
    }
    func testGenericGeneratedAndEmptyNamesRetainSideSpecificRows() throws {
        for name in ["", "_entry", "__text", "sub_real", "sub_0x1", "<anonymous>", "0xnothex", "0X1", "loc_0xAB", "unk_1", "off_a", "nullsub_F", "sub_\u{301}real"] {
            let (old, new) = try plainUnmatched(name)
            XCTAssertNoThrow(try validate([unmatchedOld(), unmatchedNew()], before: old, after: new, status: nil))
        }
    }
    func testUsableBoundaryNamesCannotBecomeUnmatched() throws {
        for name in ["loc_work", "loc_", "loc_0x", "Loc_1", "_entrypoint", "__textual", "loc_\u{301}abc", " work"] {
            let (old, new) = try plainUnmatched(name)
            XCTAssertThrowsError(try validate([unmatchedOld()], before: old, after: new))
        }
    }
    func testKeysRequireExactSidePrefixAndSelectedID() throws {
        let (old, new) = try plainUnmatched()
        for key in ["unmatched:after:" + oldID, "unmatched:before:" + newID, "unmatched:Before:" + oldID,
                    "Unmatched:before:" + oldID, "unmatched:before:" + oldID + " ", "unmatched:before:", "future:before:" + oldID] {
            XCTAssertThrowsError(try validate([row(key, basis: "unmatched", label: "removed", old: oldID, new: nil)], before: old, after: new))
        }
        XCTAssertThrowsError(try validate([row("unmatched:before:" + newID, basis: "unmatched", label: "added", old: nil, new: newID)], before: old, after: new))
        XCTAssertNoThrow(try validate([unmatchedOld(), unmatchedNew()], before: old, after: new))
    }
    func testUnmatchedCannotSelectBothOrNeitherEndpoint() throws {
        let (old, new) = try plainUnmatched()
        XCTAssertThrowsError(try validate([row("unmatched:before:" + oldID, basis: "unmatched", old: oldID, new: newID)], before: old, after: new))
        XCTAssertThrowsError(try validate([row("unmatched:before:" + oldID, basis: "unmatched", label: "ambiguous", old: nil, new: nil)], before: old, after: new))
        XCTAssertThrowsError(try validate([unmatchedOld(label: "ambiguous")], before: old, after: new))
        XCTAssertThrowsError(try validate([unmatchedNew(label: "ambiguous")], before: old, after: new))
    }
    func testExplicitFalsePreservesEligibleUnmatchedEndpoints() throws {
        let (old, new) = try bodies()
        XCTAssertNoThrow(try validate([unmatchedOld(), unmatchedNew()], before: old, after: new, status: false))
    }
    func testExplicitTrueConsumesEndpointsDespiteOmittedBodyRows() throws {
        let (old, new) = try bodies()
        XCTAssertThrowsError(try validate([unmatchedOld()], before: old, after: new, status: true))
        XCTAssertThrowsError(try validate([unmatchedNew()], before: old, after: new, status: true))
        XCTAssertNoThrow(try validate([bodyRow()], before: old, after: new, status: true))
        XCTAssertNoThrow(try validate([], before: old, after: new, status: true))
    }
    func testMissingStatusRemainsUnavailableForConsumableEndpoints() throws {
        let (old, new) = try bodies()
        XCTAssertThrowsError(try validate([unmatchedOld()], before: old, after: new, status: nil))
        XCTAssertThrowsError(try validate([unmatchedNew()], before: old, after: new, status: nil))
        let distinct = try annotated(new, digest: "e")
        var value = try wire([unmatchedOld(), unmatchedNew()], before: old, after: distinct)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context.removeValue(forKey: "exact_body_candidates"); value["comparison"] = context
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        XCTAssertNil(report.comparison.exactBodyCandidates)
        XCTAssertNoThrow(try report.validateUnmatchedRows(baselineData: old, currentData: distinct))
        XCTAssertNil(report.comparison.exactBodyCandidates)
    }
    func testAbsentFingerprintCannotConsumeAnUnmatchedEndpoint() throws {
        let (old, new) = try plainUnmatched()
        let before = try annotated(old)
        for status: Bool? in [nil, true] {
            XCTAssertNoThrow(try validate([unmatchedOld(), unmatchedNew()], before: before, after: new, status: status))
        }
    }
    func testDuplicateBodiesKeepIndependentGeneratedNameRows() throws {
        let (old, new) = try bodies()
        let before = try additional(old, id: unknownID)
        for status: Bool? in [nil, true] {
            XCTAssertNoThrow(try validate([unmatchedOld(), unmatchedOld(unknownID), unmatchedNew()], before: before, after: new, status: status))
        }
    }
    func testBlockedAmbiguousSymbolsCountAgainstUnmatchedBodySelection() throws {
        let (old, new) = try bodies()
        let after = try additional(additional(new, id: otherNewID, name: "work"), id: extraID, name: "work", digest: "e")
        for status: Bool? in [nil, true] {
            XCTAssertNoThrow(try validate([unmatchedOld(), unmatchedNew()], before: old, after: after, status: status))
        }
    }
    func testSubtypeMismatchDisablesBodyConsumption() throws {
        let (old, new) = try bodies()
        var value = try object(new), image = try XCTUnwrap(value["image"] as? [String: Any]); image["cpu_subtype"] = 1; value["image"] = image
        let after = try JSONSerialization.data(withJSONObject: value)
        for status: Bool? in [nil, true] {
            XCTAssertNoThrow(try validate([unmatchedOld(), unmatchedNew()], before: old, after: after, status: status))
        }
    }
    func testIncompatibleObservationsDoNotDisableBodyConsumption() throws {
        let (old, new) = try bodies()
        var value = try object(new); value["analysis_config"] = ["limits": ["work": 1]]
        let after = try JSONSerialization.data(withJSONObject: value)
        XCTAssertThrowsError(try validate([unmatchedOld()], before: old, after: after, status: true))
        XCTAssertThrowsError(try validate([unmatchedNew()], before: old, after: after, status: nil))
        XCTAssertNoThrow(try validate([bodyRow(label: "ambiguous")], before: old, after: after, status: true))
        XCTAssertNoThrow(try validate([unmatchedOld(), unmatchedNew()], before: old, after: after, status: false))
    }
    func testValidatedManualPinsPrecedeBodyProjection() throws {
        let (old, new) = try bodies()
        let before = try additional(old, id: unknownID), after = try additional(new, id: otherNewID)
        XCTAssertNoThrow(try validate([unmatchedOld()], before: before, after: after, status: true))
        let manual = row("manual:chosen", basis: "manual_review", old: unknownID, new: otherNewID)
        var value = try wire([manual, unmatchedOld()], before: before, after: after)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["manual_pairs"] = [["baseline_id": unknownID, "current_id": otherNewID]]; value["comparison"] = context
        XCTAssertThrowsError(try validateWire(value, before: before, after: after))
        var accepted = try wire([manual, bodyRow()], before: before, after: after); accepted["comparison"] = context
        XCTAssertNoThrow(try validateWire(accepted, before: before, after: after))
    }
    func testPinnedAndUnknownEndpointsCannotReappearAsUnmatched() throws {
        let (old, new) = try plainUnmatched()
        let manual = row("manual:chosen", basis: "manual_review", old: oldID, new: newID)
        var value = try wire([manual], before: old, after: new)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["manual_pairs"] = [["baseline_id": oldID, "current_id": newID]]; value["comparison"] = context
        XCTAssertNoThrow(try validateWire(value, before: old, after: new))
        var reused = try wire([manual, unmatchedOld()], before: old, after: new); reused["comparison"] = context
        XCTAssertThrowsError(try validateWire(reused, before: old, after: new))
        XCTAssertThrowsError(try validate([unmatchedOld(unknownID)], before: old, after: new))
    }
    func testMissingOrNullSourceNamesAreNotNewlyAdmitted() throws {
        let (old, new) = try plainUnmatched()
        XCTAssertThrowsError(try validate([unmatchedOld()], before: renamed(old, NSNull()), after: new))
        var value = try object(old), findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(findings[0]["function"] as? [String: Any]); function.removeValue(forKey: "name")
        findings[0]["function"] = function; value["findings"] = findings
        XCTAssertThrowsError(try validate([unmatchedOld()], before: JSONSerialization.data(withJSONObject: value), after: new))
    }
    func testComposedSourceFactsAndSameImageAuthorityRemainRequired() throws {
        let (old, new) = try plainUnmatched()
        var stale = unmatchedOld(); stale["before_scope"] = "metadata_only"
        XCTAssertThrowsError(try validate([stale], before: old, after: new))
        let same = try renamed(source("same", id: newID, digest: "1"), "_entry")
        XCTAssertThrowsError(try validate([unmatchedOld()], before: old, after: same))
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: old, after: same))
    }
    func testOmissionsAndFutureBasesRemainSeparate() throws {
        let (old, new) = try plainUnmatched()
        XCTAssertNoThrow(try validate([], before: old, after: new, status: nil))
        XCTAssertNoThrow(try validate([unmatchedOld()], before: old, after: new, status: nil))
        XCTAssertNoThrow(try validate([row("future:pair", basis: "future_matcher", old: oldID, new: newID)], before: old, after: new, status: nil))
    }
}
