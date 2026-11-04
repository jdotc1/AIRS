import Foundation
import XCTest
@testable import AIRSCore

final class MatchingPolicyTests: XCTestCase {
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
        try report.validateMatchingPolicy(baselineData: before, currentData: after)
    }

    func testUnknownPolicyCannotClaimVerifiedProducerMetadata() throws {
        let (old, new) = try pair()
        var value = try wire([], before: old, after: new)
        var context = try XCTUnwrap(value["comparison"] as? [String: Any]); context["matching_policy"] = "future_policy"; value["comparison"] = context
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        XCTAssertThrowsError(try report.validateMatchingPolicy(baselineData: old, currentData: new))
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
        try report.validateMatchingPolicy(baselineData: before, currentData: after)
    }
    private func named(_ data: Data, _ name: String, fingerprint: Bool = false) throws -> Data {
        var value = try object(data), findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(findings[0]["function"] as? [String: Any]); function["name"] = name
        if fingerprint { function["body_fingerprint"] = ["kind": "arm64-exact-bytes-v1", "sha256": String(repeating: "f", count: 64), "instruction_count": 4] }
        findings[0]["function"] = function; value["findings"] = findings
        return try JSONSerialization.data(withJSONObject: value)
    }
    private func manualRow(label: String = "unchanged") -> [String: Any] {
        row("manual:chosen", basis: "manual_review", label: label, old: oldID, new: newID)
    }
    func testMissingAndFalseBodyStatusRetainOrdinaryPolicyWithoutMutation() throws {
        let (old, new) = try pair()
        for status: Bool? in [nil, false] {
            let report = try configured([], before: old, after: new, status: status, policy: ordinary)
            XCTAssertNoThrow(try check(report, before: old, after: new))
            XCTAssertEqual(report.comparison.exactBodyCandidates, status)
            XCTAssertNil(report.comparison.manualPairs)
        }
    }
    func testTrueStatusRequiresSuffixEvenForEmptyComparison() throws {
        let (old, new) = try pair()
        XCTAssertNoThrow(try check(configured([], before: old, after: new, status: true, policy: ordinary + bodySuffix), before: old, after: new))
        XCTAssertThrowsError(try check(configured([], before: old, after: new, status: true, policy: ordinary), before: old, after: new))
    }
    func testSuffixCannotSupplyUnavailableOrDisabledBodyStatus() throws {
        let (old, new) = try pair()
        for status: Bool? in [nil, false] {
            XCTAssertThrowsError(try check(configured([], before: old, after: new, status: status, policy: ordinary + bodySuffix), before: old, after: new))
        }
    }
    func testEmptyPinsDoNotClaimManualSelection() throws {
        let (old, new) = try pair()
        let empty = try configured([], before: old, after: new, pins: [], policy: ordinary)
        XCTAssertNoThrow(try check(empty, before: old, after: new))
        XCTAssertEqual(empty.comparison.manualPairs?.count, 0)
        XCTAssertThrowsError(try check(configured([], before: old, after: new, pins: [], policy: manual), before: old, after: new))
        XCTAssertThrowsError(try check(configured([], before: old, after: new, policy: manual), before: old, after: new))
    }
    func testValidatedNonemptyPinsRequireManualPolicy() throws {
        let (old, new) = try pair()
        XCTAssertNoThrow(try check(configured([manualRow()], before: old, after: new, pins: pin, policy: manual), before: old, after: new))
        XCTAssertThrowsError(try check(configured([manualRow()], before: old, after: new, pins: pin, policy: ordinary), before: old, after: new))
        XCTAssertThrowsError(try check(configured([manualRow()], before: old, after: new, policy: manual), before: old, after: new))
    }
    func testManualAndBodyOptInHaveIndependentCanonicalMetadata() throws {
        let (old, new) = try pair()
        for status: Bool? in [nil, false, true] {
            let policy = manual + (status == true ? bodySuffix : "")
            let report = try configured([manualRow()], before: old, after: new, status: status, pins: pin, policy: policy)
            XCTAssertNoThrow(try check(report, before: old, after: new))
            XCTAssertEqual(report.comparison.exactBodyCandidates, status)
        }
        XCTAssertThrowsError(try check(configured([manualRow()], before: old, after: new, status: true, pins: pin, policy: manual), before: old, after: new))
    }
    func testBodyOptInRemainsRecordedUnderSameImageAuthority() throws {
        let old = try source("old", id: oldID, digest: "1"), new = try source("new", id: newID, digest: "1")
        let offset = row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)
        XCTAssertNoThrow(try check(configured([offset], before: old, after: new, status: true, policy: ordinary + bodySuffix), before: old, after: new))
        XCTAssertThrowsError(try check(configured([offset], before: old, after: new, status: true, policy: ordinary), before: old, after: new))
    }
    func testSubtypeGatingDoesNotEraseRecordedBodyOptIn() throws {
        let (old, new) = try pair()
        let before = try named(old, "oldWork", fingerprint: true), current = try named(new, "newWork", fingerprint: true)
        var value = try object(current), image = try XCTUnwrap(value["image"] as? [String: Any]); image["cpu_subtype"] = 1; value["image"] = image
        let after = try JSONSerialization.data(withJSONObject: value)
        let removed = row("symbol:oldWork", label: "removed", old: oldID, new: nil)
        XCTAssertNoThrow(try check(configured([removed], before: before, after: after, status: true, policy: ordinary + bodySuffix), before: before, after: after))
    }
    func testSupportedSymbolUnmatchedAndBodyBasesRetainTheirEvidenceChecks() throws {
        let (old, new) = try pair()
        let symbolOld = try named(old, "work"), symbolNew = try named(new, "work")
        XCTAssertNoThrow(try check(configured([row("symbol:work", old: oldID, new: newID)], before: symbolOld, after: symbolNew, policy: ordinary), before: symbolOld, after: symbolNew))
        let unnamedOld = try named(old, "_entry", fingerprint: true), unnamedNew = try named(new, "_entry", fingerprint: true)
        let unmatched = row("unmatched:before:" + oldID, basis: "unmatched", label: "removed", old: oldID, new: nil)
        XCTAssertNoThrow(try check(configured([unmatched], before: unnamedOld, after: unnamedNew, status: false, policy: ordinary), before: unnamedOld, after: unnamedNew))
        let key = "body:arm64-exact-bytes-v1:" + String(repeating: "f", count: 64) + ":4"
        XCTAssertNoThrow(try check(configured([row(key, basis: "exact_body_candidate", old: oldID, new: newID)], before: unnamedOld, after: unnamedNew, status: true, policy: ordinary + bodySuffix), before: unnamedOld, after: unnamedNew))
    }
    func testUnsupportedBasisCannotBorrowKnownPolicyAssurance() throws {
        let (old, new) = try pair()
        for basis in ["future_matcher", "", "Unique_symbol", "unmatched "] {
            let unknown = row("future:pair", basis: basis, old: oldID, new: newID)
            XCTAssertThrowsError(try check(configured([unknown], before: old, after: new, policy: ordinary), before: old, after: new))
        }
    }
    func testCanonicalPolicySpellingIsNotNormalizedOrExtended() throws {
        let (old, new) = try pair()
        for policy in [" " + ordinary, ordinary + " ", ordinary.uppercased(), ordinary + "_future", ordinary + bodySuffix + bodySuffix,
                       "exact_digest_then_unique_symbo\u{301}l", "exact_digest_then_unique_symbol\u{200b}"] {
            XCTAssertThrowsError(try check(configured([], before: old, after: new, policy: policy), before: old, after: new))
        }
    }
    func testBaseSpellingCannotInventFalseBodyStatusForConsumableRows() throws {
        let (old, new) = try pair()
        let before = try named(old, "_entry", fingerprint: true), after = try named(new, "_entry", fingerprint: true)
        let unmatched = row("unmatched:before:" + oldID, basis: "unmatched", label: "removed", old: oldID, new: nil)
        XCTAssertThrowsError(try check(configured([unmatched], before: before, after: after, policy: ordinary), before: before, after: after))
        XCTAssertNoThrow(try check(configured([unmatched], before: before, after: after, status: false, policy: ordinary), before: before, after: after))
    }
    func testIncompatibleSelectedPairRetainsAmbiguousObservationLabel() throws {
        let (old, new) = try pair()
        let before = try named(old, "work"), current = try named(new, "work")
        var value = try object(current); value["analysis_config"] = ["limits": ["work": 1]]
        let after = try JSONSerialization.data(withJSONObject: value)
        XCTAssertNoThrow(try check(configured([row("symbol:work", label: "ambiguous", old: oldID, new: newID)], before: before, after: after, policy: ordinary), before: before, after: after))
        XCTAssertThrowsError(try check(configured([row("symbol:work", old: oldID, new: newID)], before: before, after: after, policy: ordinary), before: before, after: after))
    }
    func testCanonicalMetadataDoesNotRepairSourceOrAccountingClaims() throws {
        let (old, new) = try pair()
        let unknown = row("unmatched:before:" + unknownID, basis: "unmatched", label: "removed", old: unknownID, new: nil)
        XCTAssertThrowsError(try check(configured([unknown], before: old, after: new, policy: ordinary), before: old, after: new))
        var value = try wire([], before: old, after: new), summary = try XCTUnwrap(value["summary"] as? [String: Any]); summary["matched_count"] = 1; value["summary"] = summary
        let invalid = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        XCTAssertThrowsError(try check(invalid, before: old, after: new))
    }
    func testGenericDecodingAndOmittedGroupsKeepTheirPriorBoundaries() throws {
        let (old, new) = try pair()
        let report = try configured([row("future:pair", basis: "future_matcher", old: oldID, new: newID)], before: old, after: new, policy: "future_policy")
        XCTAssertEqual(report.comparison.matchingPolicy, "future_policy")
        XCTAssertNoThrow(try report.validateUnmatchedRows(baselineData: old, currentData: new))
        XCTAssertThrowsError(try check(report, before: old, after: new))
        XCTAssertNoThrow(try check(configured([], before: old, after: new, policy: ordinary), before: old, after: new))
    }
}
