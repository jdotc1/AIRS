import Foundation
import XCTest
@testable import AIRSCore

final class BodyCandidatePairsTests: XCTestCase {
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

    private func validate(_ rows: [[String: Any]], before: Data, after: Data) throws {
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: wire(rows, before: before, after: after)))
        try report.validateBodyCandidatePairs(baselineData: before, currentData: after)
    }

    func testMissingFingerprintsCannotSupportBodyPair() throws {
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate([row("body:arm64-exact-bytes-v1:" + String(repeating: "f", count: 64) + ":4", basis: "exact_body_candidate", old: oldID, new: newID)], before: before, after: after))
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
        try report.validateBodyCandidatePairs(baselineData: before, currentData: after)
    }
    func testUniqueStandaloneBodyPairPasses() throws {
        let (old, new) = try bodies()
        XCTAssertNoThrow(try validate([bodyRow()], before: old, after: new))
        let namedOld = try annotated(old, name: "oldName"), namedNew = try annotated(new, name: "newName")
        XCTAssertNoThrow(try validate([bodyRow()], before: namedOld, after: namedNew))
    }
    func testExplicitOptInIsRequired() throws {
        let (old, new) = try bodies()
        for status: Bool? in [nil, false, true] {
            var value = try wire([bodyRow()], before: old, after: new)
            var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["exact_body_candidates"] = status; value["comparison"] = context
            if status == true { XCTAssertNoThrow(try validateWire(value, before: old, after: new)) }
            else { XCTAssertThrowsError(try validateWire(value, before: old, after: new)) }
        }
    }
    func testBothFingerprintsAndFullTupleAreRequired() throws {
        let (old, new) = try bodies(), (bareOld, bareNew) = try pair()
        XCTAssertThrowsError(try validate([bodyRow()], before: bareOld, after: new))
        XCTAssertThrowsError(try validate([bodyRow()], before: old, after: bareNew))
        XCTAssertThrowsError(try validate([bodyRow()], before: old, after: annotated(new, digest: "e")))
        let longer = try annotated(new, count: 5)
        XCTAssertNoThrow(try AuditReport.decode(longer))
        XCTAssertThrowsError(try validate([bodyRow()], before: old, after: longer))
    }
    func testCanonicalKeyAndTwoEndpointsAreRequired() throws {
        let (old, new) = try bodies()
        for key in [bodyKey + "0", bodyKey.replacingOccurrences(of: ":4", with: ":04"), bodyKey.uppercased(), "body:other"] {
            XCTAssertThrowsError(try validate([row(key, basis: "exact_body_candidate", old: oldID, new: newID)], before: old, after: new))
        }
        XCTAssertThrowsError(try validate([row(bodyKey, basis: "exact_body_candidate", label: "removed", old: oldID, new: nil)], before: old, after: new))
        XCTAssertThrowsError(try validate([row(bodyKey, basis: "exact_body_candidate", label: "added", old: nil, new: newID)], before: old, after: new))
        XCTAssertThrowsError(try validate([row(bodyKey, basis: "exact_body_candidate", label: "ambiguous", old: nil, new: nil)], before: old, after: new))
    }
    func testOmittedDuplicateBodiesStillBlockSelection() throws {
        let (old, new) = try bodies()
        XCTAssertThrowsError(try validate([bodyRow()], before: additional(old, id: unknownID), after: new))
        XCTAssertThrowsError(try validate([bodyRow()], before: old, after: additional(new, id: otherNewID)))
    }
    func testEstablishedSymbolPairsCannotBeStolen() throws {
        let (old, new) = try bodies()
        XCTAssertThrowsError(try validate([bodyRow()], before: annotated(old, name: "stable"), after: annotated(new, name: "stable")))
    }
    func testEstablishedSymbolsAreExcludedEvenWhenTheirRowsAreOmitted() throws {
        let (old, new) = try bodies()
        let before = try additional(old, id: unknownID, name: "stable"), after = try additional(new, id: otherNewID, name: "stable")
        XCTAssertNoThrow(try validate([bodyRow()], before: before, after: after))
    }
    func testSoleBucketMembersFromAmbiguousSymbolsAreIneligible() throws {
        let (old, new) = try bodies()
        let before = try additional(annotated(old, name: "work"), id: unknownID, name: "work", digest: "e")
        XCTAssertThrowsError(try validate([bodyRow()], before: before, after: annotated(new, name: "work")))
    }
    func testBlockedSymbolMembersCountAgainstOtherCandidates() throws {
        let (old, new) = try bodies()
        let before = try additional(additional(old, id: unknownID, name: "work"), id: extraID, name: "work", digest: "e")
        let after = try additional(new, id: otherNewID, name: "work", digest: "d")
        XCTAssertThrowsError(try validate([bodyRow()], before: before, after: after))
    }
    func testValidatedManualPinsPrecedeBodySnapshot() throws {
        let (old, new) = try bodies()
        let before = try additional(old, id: unknownID), after = try additional(new, id: otherNewID)
        let manual = row("manual:chosen", basis: "manual_review", old: unknownID, new: otherNewID)
        var value = try wire([manual, bodyRow()], before: before, after: after)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["manual_pairs"] = [["baseline_id": unknownID, "current_id": otherNewID]]; value["comparison"] = context
        XCTAssertNoThrow(try validateWire(value, before: before, after: after))
        var hidden = try wire([bodyRow()], before: before, after: after); hidden["comparison"] = context
        XCTAssertThrowsError(try validateWire(hidden, before: before, after: after))
    }
    func testExactCPUSubtypeIsRequired() throws {
        let (old, new) = try bodies()
        var value = try object(new), image = try XCTUnwrap(value["image"] as? [String: Any]); image["cpu_subtype"] = 1; value["image"] = image
        let other = try JSONSerialization.data(withJSONObject: value)
        XCTAssertNoThrow(try AuditReport.decode(other))
        XCTAssertThrowsError(try validate([bodyRow()], before: old, after: other))
    }
    func testBodyEvidenceDoesNotOverrideObservationLabels() throws {
        let (old, new) = try bodies()
        var configured = try object(new); configured["analysis_config"] = ["limits": ["work": 1]]
        let other = try JSONSerialization.data(withJSONObject: configured)
        XCTAssertNoThrow(try validate([bodyRow(label: "ambiguous")], before: old, after: other))
        XCTAssertThrowsError(try validate([bodyRow()], before: old, after: other))
        var changed = try object(new), findings = try XCTUnwrap(changed["findings"] as? [[String: Any]])
        findings[0]["reason_codes"] = ["different_observation"]; changed["findings"] = findings
        let altered = try JSONSerialization.data(withJSONObject: changed)
        XCTAssertNoThrow(try validate([bodyRow(label: "changed")], before: old, after: altered))
        XCTAssertThrowsError(try validate([bodyRow()], before: old, after: altered))
    }
    func testSameImageStillRequiresOffsetAuthorityAndOmissionsStaySeparate() throws {
        let (old, new) = try bodies()
        let same = try annotated(source("after", id: newID, digest: "1"))
        XCTAssertThrowsError(try validate([bodyRow()], before: old, after: same))
        XCTAssertNoThrow(try validate([], before: old, after: new))
        XCTAssertNoThrow(try validate([row("future:pair", basis: "future_matcher", old: oldID, new: newID)], before: old, after: new))
    }
}
