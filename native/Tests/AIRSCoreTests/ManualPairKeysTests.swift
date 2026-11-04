import Foundation
import XCTest
@testable import AIRSCore

final class ManualPairKeysTests: XCTestCase {
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
        try report.validateManualPairKeys(baselineData: before, currentData: after)
    }

    func testArbitraryManualKeyCannotClaimCanonicalPairEvidence() throws {
        let (old, new) = try pair()
        var value = try wire([row("manual:chosen", basis: "manual_review", old: oldID, new: newID)], before: old, after: new)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any])
        context["manual_pairs"] = [["baseline_id": oldID, "current_id": newID]]
        context["matching_policy"] = "manual_then_unique_symbol"; value["comparison"] = context
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        XCTAssertThrowsError(try report.validateManualPairKeys(baselineData: old, currentData: new))
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
        try report.validateManualPairKeys(baselineData: before, currentData: after)
    }
    private func named(_ data: Data, _ name: String, fingerprint: Bool = false) throws -> Data {
        var value = try object(data), findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(findings[0]["function"] as? [String: Any]); function["name"] = name
        if fingerprint { function["body_fingerprint"] = ["kind": "arm64-exact-bytes-v1", "sha256": String(repeating: "f", count: 64), "instruction_count": 4] }
        findings[0]["function"] = function; value["findings"] = findings
        return try JSONSerialization.data(withJSONObject: value)
    }
    private func manualRow(label: String = "unchanged") -> [String: Any] {
        row("manual:" + oldID + ":" + newID, basis: "manual_review", label: label, old: oldID, new: newID)
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
    private let otherNewID = "airsf-" + String(repeating: "d", count: 64)
    private var canonical: String { "manual:" + oldID + ":" + newID }
    private func validateKey(_ key: String, before: Data, after: Data, status: Bool? = nil, label: String = "unchanged") throws {
        let report = try configured([row(key, basis: "manual_review", label: label, old: oldID, new: newID)], before: before, after: after,
                                    status: status, pins: pin, policy: manual + (status == true ? bodySuffix : ""))
        try check(report, before: before, after: after)
    }
    func testCanonicalPairKeyPassesForAllBodyStatusStates() throws {
        let (old, new) = try pair()
        for status: Bool? in [nil, false, true] {
            let report = try configured([manualRow()], before: old, after: new, status: status, pins: pin,
                                        policy: manual + (status == true ? bodySuffix : ""))
            XCTAssertNoThrow(try check(report, before: old, after: new))
            XCTAssertEqual(report.comparison.exactBodyCandidates, status)
        }
    }
    func testReversedAndForeignKeyComponentsCannotBorrowSelectedPair() throws {
        let (old, new) = try pair()
        for key in ["manual:" + newID + ":" + oldID, "manual:" + unknownID + ":" + newID,
                    "manual:" + oldID + ":" + unknownID, "manual:" + oldID + ":" + oldID] {
            XCTAssertThrowsError(try validateKey(key, before: old, after: new))
        }
    }
    func testPartialAlternateAndExtraDelimitersReject() throws {
        let (old, new) = try pair()
        for key in ["manual:", "manual:" + oldID, "manual:" + oldID + ":", canonical + ":extra",
                    "manual::" + oldID + ":" + newID, canonical.replacingOccurrences(of: "manual:", with: "review:")] {
            XCTAssertThrowsError(try validateKey(key, before: old, after: new))
        }
    }
    func testCaseWhitespaceAndUnicodeVariantsAreNotNormalized() throws {
        let (old, new) = try pair()
        for key in [canonical.uppercased(), " " + canonical, canonical + " ", canonical + "\n",
                    canonical + "\u{200b}", canonical.replacingOccurrences(of: "manual:", with: "manual\u{301}:"),
                    canonical.replacingOccurrences(of: ":", with: "：")] {
            XCTAssertThrowsError(try validateKey(key, before: old, after: new))
        }
    }
    func testConfigurationAmbiguityDoesNotChangeCanonicalKey() throws {
        let (old, new) = try pair()
        var value = try object(new); value["analysis_config"] = ["limits": ["work": 1]]
        let after = try JSONSerialization.data(withJSONObject: value)
        XCTAssertNoThrow(try validateKey(canonical, before: old, after: after, label: "ambiguous"))
        XCTAssertThrowsError(try validateKey(canonical, before: old, after: after))
        XCTAssertThrowsError(try validateKey("manual:chosen", before: old, after: after, label: "ambiguous"))
    }
    func testBothEndpointsAndValidatedPinMetadataRemainRequired() throws {
        let (old, new) = try pair()
        XCTAssertThrowsError(try check(configured([manualRow()], before: old, after: new, policy: manual), before: old, after: new))
        XCTAssertThrowsError(try check(configured([manualRow()], before: old, after: new, pins: [], policy: ordinary), before: old, after: new))
        let oneSided = row(canonical, basis: "manual_review", label: "removed", old: oldID, new: nil)
        XCTAssertThrowsError(try check(configured([oneSided], before: old, after: new, pins: pin, policy: manual), before: old, after: new))
        let unknown = row("manual:" + unknownID + ":" + newID, basis: "manual_review", old: unknownID, new: newID)
        let missing = [["baseline_id": unknownID, "current_id": newID]]
        XCTAssertThrowsError(try check(configured([unknown], before: old, after: new, pins: missing, policy: manual), before: old, after: new))
    }
    func testMultiplePairsUseTheirOwnKeysIndependentOfMetadataOrder() throws {
        let (old, new) = try pair()
        let before = try additional(old, id: unknownID, name: "otherOld"), after = try additional(new, id: otherNewID, name: "otherNew")
        let otherKey = "manual:" + unknownID + ":" + otherNewID
        let other = row(otherKey, basis: "manual_review", old: unknownID, new: otherNewID)
        let pins = [["baseline_id": unknownID, "current_id": otherNewID]] + pin
        XCTAssertNoThrow(try check(configured([manualRow(), other], before: before, after: after, pins: pins, policy: manual), before: before, after: after))
        let swapped = [row(otherKey, basis: "manual_review", old: oldID, new: newID),
                       row(canonical, basis: "manual_review", old: unknownID, new: otherNewID)]
        XCTAssertThrowsError(try check(configured(swapped, before: before, after: after, pins: pins, policy: manual), before: before, after: after))
    }
    func testCanonicalKeyDoesNotRepairSourceFactsOrPolicy() throws {
        let (old, new) = try pair()
        var stale = manualRow(); stale["before_scope"] = "metadata_only"
        XCTAssertThrowsError(try check(configured([stale], before: old, after: new, pins: pin, policy: manual), before: old, after: new))
        XCTAssertThrowsError(try check(configured([manualRow()], before: old, after: new, pins: pin, policy: ordinary), before: old, after: new))
        XCTAssertThrowsError(try check(configured([manualRow()], before: old, after: new, status: true, pins: pin, policy: manual), before: old, after: new))
    }
    func testEarlierPolicyApiKeepsItsArbitraryManualKeyBoundary() throws {
        let (old, new) = try pair()
        let record = try configured([row("review:legacy", basis: "manual_review", old: oldID, new: newID)], before: old, after: new, pins: pin, policy: manual)
        XCTAssertNoThrow(try record.validateMatchingPolicy(baselineData: old, currentData: new))
        XCTAssertThrowsError(try check(record, before: old, after: new))
        XCTAssertEqual(record.changes.first?.key, "review:legacy")
    }
    func testCanonicalManualPairDoesNotInventBodyStatusForOtherRows() throws {
        let (old, new) = try bodies()
        let before = try additional(old, id: unknownID), after = try additional(new, id: otherNewID)
        let unmatched = row("unmatched:before:" + unknownID, basis: "unmatched", label: "removed", old: unknownID, new: nil)
        XCTAssertThrowsError(try check(configured([manualRow(), unmatched], before: before, after: after, pins: pin, policy: manual), before: before, after: after))
        XCTAssertNoThrow(try check(configured([manualRow(), unmatched], before: before, after: after, status: false, pins: pin, policy: manual), before: before, after: after))
        let bodyKey = "body:arm64-exact-bytes-v1:" + String(repeating: "f", count: 64) + ":4"
        let body = row(bodyKey, basis: "exact_body_candidate", old: unknownID, new: otherNewID)
        XCTAssertNoThrow(try check(configured([manualRow(), body], before: before, after: after, status: true, pins: pin, policy: manual + bodySuffix), before: before, after: after))
    }
    func testSameImageOffsetAuthorityCannotBeOverriddenByManualKey() throws {
        let old = try source("old", id: oldID, digest: "1"), new = try source("new", id: newID, digest: "1")
        XCTAssertThrowsError(try validateKey(canonical, before: old, after: new))
        let offset = row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)
        XCTAssertNoThrow(try check(configured([offset], before: old, after: new, policy: ordinary), before: old, after: new))
    }
    func testEmptyAndPartialNonmanualComparisonsKeepTheirPriorScope() throws {
        let (old, new) = try pair()
        XCTAssertNoThrow(try check(configured([], before: old, after: new, policy: ordinary), before: old, after: new))
        let empty = try configured([], before: old, after: new, pins: [], policy: ordinary)
        XCTAssertNoThrow(try check(empty, before: old, after: new))
        XCTAssertEqual(empty.comparison.manualPairs?.count, 0)
        let one = row("symbol:before", label: "removed", old: oldID, new: nil)
        XCTAssertNoThrow(try check(configured([one], before: old, after: new, policy: ordinary), before: old, after: new))
    }
}
