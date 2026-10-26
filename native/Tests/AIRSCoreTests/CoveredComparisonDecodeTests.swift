import Foundation
import XCTest
@testable import AIRSCore

final class CoveredComparisonDecodeTests: XCTestCase {
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
        _ = try decoded(report, before: before, after: after)
    }
    private func decoded(_ report: ComparisonReport, before: Data, after: Data) throws -> ComparisonReport {
        try ComparisonReport.decodeWithSavedReportCoverage(JSONEncoder().encode(report), baselineData: before, currentData: after)
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
    func testMissingCrossImageBodyStatusCannotConstructCoveredReport() throws {
        let (old, new) = try pair()
        let before = try named(old, "work"), after = try named(new, "work")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        XCTAssertThrowsError(try check(configured([value], before: before, after: after, policy: ordinary), before: before, after: after))
    }
    private func sameImageFixture(_ status: Bool?) throws -> (ComparisonReport, Data, Data) {
        let before = try source("before", id: oldID, digest: "1"), after = try source("after", id: newID, digest: "1")
        let value = labeled("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID, name: "after")
        return (try configured([value], before: before, after: after, status: status,
                               policy: ordinary + (status == true ? bodySuffix : "")), before, after)
    }
    private func assertSameImageStatus(_ status: Bool?) throws {
        let (report, before, after) = try sameImageFixture(status)
        let result = try decoded(report, before: before, after: after)
        XCTAssertTrue(result.comparison.sameImage)
        XCTAssertEqual(result.comparison.exactBodyCandidates, status)
        XCTAssertEqual(result.changes.map(\.key), ["offset:0x0"])
    }
    private func crossImageFixture() throws -> (ComparisonReport, Data, Data) {
        let (old, new) = try pair()
        let before = try named(old, "work"), after = try named(new, "work")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        return (try configured([value], before: before, after: after, status: false, policy: ordinary), before, after)
    }
    private func bodyFixture() throws -> (ComparisonReport, Data, Data) {
        let (old, new) = try pair()
        let before = try named(old, "_entry", fingerprint: true), after = try named(new, "_entry", fingerprint: true)
        let key = "body:arm64-exact-bytes-v1:" + String(repeating: "f", count: 64) + ":4"
        let value = labeled(key, basis: "exact_body_candidate", old: oldID, new: newID, name: "_entry")
        return (try configured([value], before: before, after: after, status: true, policy: ordinary + bodySuffix), before, after)
    }
    private func withContext(_ report: ComparisonReport, fields: [String: Any]) throws -> Data {
        var value = try object(JSONEncoder().encode(report)), context = try XCTUnwrap(value["comparison"] as? [String: Any])
        for (key, field) in fields { context[key] = field }; value["comparison"] = context
        return try JSONSerialization.data(withJSONObject: value)
    }
    func testSameImagePreservesMissingBodyStatus() throws { try assertSameImageStatus(nil) }
    func testSameImagePreservesDisabledBodyStatus() throws { try assertSameImageStatus(false) }
    func testSameImagePreservesEnabledBodyStatus() throws { try assertSameImageStatus(true) }
    func testExplicitFalseSelectsBodyDisabledCoverage() throws {
        let (report, before, after) = try crossImageFixture()
        let result = try decoded(report, before: before, after: after)
        XCTAssertFalse(result.comparison.sameImage)
        XCTAssertEqual(result.comparison.exactBodyCandidates, false)
        XCTAssertEqual(result.changes[0].matchBasis, "unique_symbol")
    }
    func testExplicitTrueSelectsBodyEnabledCoverage() throws {
        let (report, before, after) = try bodyFixture()
        let result = try decoded(report, before: before, after: after)
        XCTAssertEqual(result.comparison.exactBodyCandidates, true)
        XCTAssertEqual(result.changes[0].matchBasis, "exact_body_candidate")
    }
    func testSameImageDispatchRejectsOmittedGroup() throws {
        let (report, old, new) = try sameImageFixture(nil)
        let before = try additional(old, id: unknownID, name: "other"), after = try additional(new, id: otherNewID, name: "other")
        let partial = try configured([labeled("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID, name: "after")], before: before, after: after, policy: ordinary)
        XCTAssertThrowsError(try decoded(partial, before: before, after: after))
        XCTAssertNil(report.comparison.exactBodyCandidates)
    }
    func testBodyDisabledDispatchRejectsOmittedGroup() throws {
        let (old, new) = try pair()
        let before = try additional(named(old, "work"), id: unknownID, name: "other"), after = try named(new, "work")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        XCTAssertThrowsError(try check(configured([value], before: before, after: after, status: false, policy: ordinary), before: before, after: after))
    }
    func testBodyEnabledDispatchRejectsOmittedPair() throws {
        let (_, before, after) = try bodyFixture()
        XCTAssertThrowsError(try check(configured([], before: before, after: after, status: true, policy: ordinary + bodySuffix), before: before, after: after))
    }
    func testForgedSameImageFlagCannotWeakenCrossImageProof() throws {
        let (report, before, after) = try crossImageFixture()
        let bytes = try withContext(report, fields: ["same_image": true])
        XCTAssertThrowsError(try ComparisonReport.decodeWithSavedReportCoverage(bytes, baselineData: before, currentData: after))
    }
    func testForgedCrossImageFlagCannotWeakenSameImageProof() throws {
        let (report, before, after) = try sameImageFixture(false)
        let bytes = try withContext(report, fields: ["same_image": false])
        XCTAssertThrowsError(try ComparisonReport.decodeWithSavedReportCoverage(bytes, baselineData: before, currentData: after))
    }
    func testMalformedJSONDoesNotConstructCoveredReport() throws {
        let (_, before, after) = try crossImageFixture()
        for bytes in [Data("not JSON".utf8), Data("{}".utf8)] {
            XCTAssertThrowsError(try ComparisonReport.decodeWithSavedReportCoverage(bytes, baselineData: before, currentData: after))
        }
    }
    func testUnsupportedHeaderStillRefuses() throws {
        let (report, before, after) = try crossImageFixture()
        var value = try object(JSONEncoder().encode(report)); value["schema_version"] = 2
        let bytes = try JSONSerialization.data(withJSONObject: value)
        XCTAssertThrowsError(try ComparisonReport.decodeWithSavedReportCoverage(bytes, baselineData: before, currentData: after))
    }
    func testComparisonByteLimitPrecedesJSONDecoding() throws {
        let bytes = Data(count: ReportFiles.maximumBytes + 1)
        XCTAssertThrowsError(try ComparisonReport.decodeWithSavedReportCoverage(bytes, baselineData: Data(), currentData: Data())) { error in
            guard let failure = error as? ReportError, case .tooLarge(let limit) = failure else {
                XCTFail("Expected comparison byte-limit refusal before JSON decoding"); return
            }
            XCTAssertEqual(limit, ReportFiles.maximumBytes)
        }
    }
    func testSourceByteLimitPropagatesThroughSelectedBranch() throws {
        let (report, _, after) = try sameImageFixture(nil)
        let bytes = Data(count: ReportFiles.maximumBytes + 1)
        XCTAssertThrowsError(try decoded(report, before: bytes, after: after)) { error in
            guard let failure = error as? ReportError, case .tooLarge(let limit) = failure else {
                XCTFail("Expected composed source byte-limit refusal"); return
            }
            XCTAssertEqual(limit, ReportFiles.maximumBytes)
        }
    }
    func testDecodedFieldsAreNotNormalizedOrRewritten() throws {
        let (old, new) = try pair(), name = "cafe\u{301}"
        let before = try named(old, name), after = try named(new, name)
        var row = labeled("symbol:" + name, old: oldID, new: newID, name: name)
        row["notes"] = ["Review this recorded candidate."]
        var value = try wire([row], before: before, after: after), context = try XCTUnwrap(value["comparison"] as? [String: Any])
        context["exact_body_candidates"] = false; value["comparison"] = context
        value["limitations"] = ["Recorded source facts only."]
        let bytes = try JSONSerialization.data(withJSONObject: value)
        let result = try ComparisonReport.decodeWithSavedReportCoverage(bytes, baselineData: before, currentData: after)
        XCTAssertTrue(result.changes[0].functionName.utf8.elementsEqual(name.utf8))
        XCTAssertEqual(result.changes[0].notes, ["Review this recorded candidate."])
        XCTAssertEqual(result.limitations, ["Recorded source facts only."])
        XCTAssertEqual(result.comparison.exactBodyCandidates, false)
        let legacy = try ComparisonReport.decode(bytes)
        XCTAssertEqual(result.summary.matchedCount, legacy.summary.matchedCount)
    }
}
