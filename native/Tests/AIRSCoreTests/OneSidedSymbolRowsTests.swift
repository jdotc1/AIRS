import Foundation
import XCTest
@testable import AIRSCore

final class OneSidedSymbolRowsTests: XCTestCase {
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
        try report.validateOneSidedSymbolRows(baselineData: before, currentData: after)
    }

    func testForeignSourceNameCannotBeRemoved() throws {
        let (old, new) = try pair()
        XCTAssertThrowsError(try validate([row("symbol:after", basis: "unique_symbol", label: "removed", old: oldID, new: nil)], before: old, after: new))
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
        try report.validateOneSidedSymbolRows(baselineData: before, currentData: after)
    }
    private func namedBodies() throws -> (Data, Data) {
        let (old, new) = try bodies()
        return (try annotated(old, name: "oldWork"), try annotated(new, name: "newWork"))
    }
    private func removed(_ name: String = "oldWork", id: String? = nil) -> [String: Any] {
        row("symbol:" + name, label: "removed", old: id ?? oldID, new: nil)
    }
    private func added(_ name: String = "newWork", id: String? = nil) -> [String: Any] {
        row("symbol:" + name, label: "added", old: nil, new: id ?? newID)
    }
    func testOrdinaryAddedAndRemovedSourceSingletonsPass() throws {
        let (old, new) = try pair()
        for status: Bool? in [nil, false, true] {
            XCTAssertNoThrow(try validate([removed("before"), added("after")], before: old, after: new, status: status))
        }
    }
    func testExactSingletonIDsAndSideAreRequired() throws {
        let (old, new) = try pair()
        let before = try additional(old, id: unknownID, name: "other")
        XCTAssertThrowsError(try validate([removed("before", id: unknownID)], before: before, after: new))
        XCTAssertNoThrow(try validate([removed("other", id: unknownID)], before: before, after: new))
        XCTAssertThrowsError(try validate([added("before")], before: before, after: new))
    }
    func testExplicitFalsePreservesEligibleBodyEndpointsAsSymbolRows() throws {
        let (old, new) = try namedBodies()
        XCTAssertNoThrow(try validate([removed(), added()], before: old, after: new, status: false))
    }
    func testExplicitTrueConsumesEndpointsEvenWhenBodyRowsAreOmitted() throws {
        let (old, new) = try namedBodies()
        XCTAssertThrowsError(try validate([removed()], before: old, after: new, status: true))
        XCTAssertThrowsError(try validate([added()], before: old, after: new, status: true))
        XCTAssertNoThrow(try validate([bodyRow()], before: old, after: new, status: true))
        XCTAssertNoThrow(try validate([], before: old, after: new, status: true)) // No completeness claim.
    }
    func testMissingStatusRefusesOnlyOutcomesThatCouldBeConsumed() throws {
        let (old, new) = try namedBodies()
        XCTAssertThrowsError(try validate([removed()], before: old, after: new, status: nil))
        XCTAssertThrowsError(try validate([added()], before: old, after: new, status: nil))
        let distinct = try annotated(new, name: "newWork", digest: "e")
        var value = try wire([removed(), added()], before: old, after: distinct)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context.removeValue(forKey: "exact_body_candidates"); value["comparison"] = context
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        XCTAssertNil(report.comparison.exactBodyCandidates)
        XCTAssertNoThrow(try report.validateOneSidedSymbolRows(baselineData: old, currentData: distinct))
        XCTAssertNil(report.comparison.exactBodyCandidates)
    }
    func testAbsentFingerprintCannotBecomeBodyConsumption() throws {
        let (old, new) = try pair()
        let before = try annotated(old, name: "before")
        for status: Bool? in [nil, true] {
            XCTAssertNoThrow(try validate([removed("before"), added("after")], before: before, after: new, status: status))
        }
    }
    func testDuplicateBodyBucketsWithholdConsumption() throws {
        let (old, new) = try namedBodies()
        let after = try additional(new, id: otherNewID, name: "other")
        for status: Bool? in [nil, true] {
            XCTAssertNoThrow(try validate([removed(), added()], before: old, after: after, status: status))
        }
    }
    func testBlockedSymbolMembersStillCountAgainstBodyUniqueness() throws {
        let (old, new) = try namedBodies()
        let after = try additional(additional(new, id: otherNewID, name: "work"), id: extraID, name: "work", digest: "e")
        XCTAssertNoThrow(try validate([removed(), added()], before: old, after: after, status: true))
        XCTAssertNoThrow(try validate([removed()], before: old, after: after, status: nil))
    }
    func testEstablishedSymbolPairsAreExcludedFromBodyBuckets() throws {
        let (old, new) = try namedBodies()
        let before = try additional(old, id: unknownID, name: "stable"), after = try additional(new, id: otherNewID, name: "stable")
        XCTAssertThrowsError(try validate([removed()], before: before, after: after, status: true))
        XCTAssertThrowsError(try validate([removed()], before: before, after: after, status: nil))
        XCTAssertNoThrow(try validate([bodyRow()], before: before, after: after, status: true))
    }
    func testExactSubtypeMismatchDisablesBodyPhaseWithoutChangingStatus() throws {
        let (old, new) = try namedBodies()
        var value = try object(new), image = try XCTUnwrap(value["image"] as? [String: Any]); image["cpu_subtype"] = 1; value["image"] = image
        let after = try JSONSerialization.data(withJSONObject: value)
        for status: Bool? in [nil, true] {
            XCTAssertNoThrow(try validate([removed(), added()], before: old, after: after, status: status))
        }
    }
    func testIncompatibleObservationsDoNotDisableBodySelection() throws {
        let (old, new) = try namedBodies()
        var value = try object(new); value["analysis_config"] = ["limits": ["work": 1]]
        let after = try JSONSerialization.data(withJSONObject: value)
        XCTAssertThrowsError(try validate([removed()], before: old, after: after, status: true))
        XCTAssertThrowsError(try validate([added()], before: old, after: after, status: nil))
        XCTAssertNoThrow(try validate([bodyRow(label: "ambiguous")], before: old, after: after, status: true))
        XCTAssertNoThrow(try validate([removed(), added()], before: old, after: after, status: false))
    }
    func testManualPinsPrecedeBodyConsumption() throws {
        let (old, new) = try namedBodies()
        let before = try additional(old, id: unknownID), after = try additional(new, id: otherNewID)
        XCTAssertNoThrow(try validate([removed()], before: before, after: after, status: true)) // Unconsumed duplicate bucket.
        let manual = row("manual:chosen", basis: "manual_review", old: unknownID, new: otherNewID)
        var value = try wire([manual, removed()], before: before, after: after)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["manual_pairs"] = [["baseline_id": unknownID, "current_id": otherNewID]]; value["comparison"] = context
        XCTAssertThrowsError(try validateWire(value, before: before, after: after))
        var accepted = try wire([manual, bodyRow()], before: before, after: after); accepted["comparison"] = context
        XCTAssertNoThrow(try validateWire(accepted, before: before, after: after))
    }
    func testEstablishedUniquePairCannotHideAnEndpoint() throws {
        let (old, new) = try pair()
        let before = try annotated(old, name: "work"), after = try annotated(new, name: "work")
        for status: Bool? in [nil, false, true] {
            XCTAssertThrowsError(try validate([removed("work")], before: before, after: after, status: status))
            XCTAssertThrowsError(try validate([added("work")], before: before, after: after, status: status))
            XCTAssertNoThrow(try validate([row("symbol:work", old: oldID, new: newID)], before: before, after: after, status: status))
        }
    }
    func testSelectedUniqueAmbiguityAndDuplicateGroupsRetainPriorRules() throws {
        let (old, new) = try pair()
        let before = try annotated(old, name: "work"), after = try annotated(new, name: "work")
        var value = try object(after); value["analysis_config"] = ["limits": ["work": 1]]
        let other = try JSONSerialization.data(withJSONObject: value)
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: oldID, new: newID)], before: before, after: other))
        let duplicate = try additional(before, id: unknownID, name: "work")
        XCTAssertNoThrow(try validate([row("symbol:work", label: "ambiguous", old: nil, new: newID)], before: duplicate, after: after, status: true))
    }
    func testExactWireNamesAreNotNormalizedForSingletons() throws {
        let (old, new) = try pair()
        let before = try annotated(old, name: "e\u{301}"), after = try annotated(new, name: "other", digest: "e")
        XCTAssertNoThrow(try validate([removed("e\u{301}")], before: before, after: after))
        XCTAssertThrowsError(try validate([removed("\u{e9}")], before: before, after: after))
    }
    func testManualConsumedAndUnknownEndpointsRemainUnavailable() throws {
        let (old, new) = try namedBodies()
        let manual = row("manual:chosen", basis: "manual_review", old: oldID, new: newID)
        var value = try wire([manual, removed()], before: old, after: new)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["manual_pairs"] = [["baseline_id": oldID, "current_id": newID]]; value["comparison"] = context
        XCTAssertThrowsError(try validateWire(value, before: old, after: new))
        XCTAssertThrowsError(try validate([removed(id: unknownID)], before: old, after: new))
    }
    func testExactImageAuthorityAndOtherBasesRemainSeparate() throws {
        let before = try source("old", id: oldID, digest: "1"), after = try source("new", id: newID, digest: "1")
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: after))
        XCTAssertThrowsError(try validate([removed("old")], before: before, after: after))
        let (old, new) = try pair()
        XCTAssertNoThrow(try validate([row("future:pair", basis: "future_matcher", old: oldID, new: newID)], before: old, after: new, status: nil))
    }
}
