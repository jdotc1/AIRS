import Foundation
import XCTest
@testable import AIRSCore

final class CoveredBatchComparisonTests: XCTestCase {
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
    private func batchItem(_ name: String, data: Data) throws -> ImageBatchItem {
        let report = try AuditReport.decode(data)
        return ImageBatchItem(id: UUID(), input: URL(fileURLWithPath: "/owned/" + name), status: .completed,
            message: "Owned saved report", retainedReportID: UUID(), image: report.image,
            summary: report.summary, model: report.generator.analysisModelVersion)
    }
    private func batchPlan(_ old: [ImageBatchItem], _ new: [ImageBatchItem]) throws -> BatchComparisonPlan {
        try BatchComparisonPlan(baseline: ImageBatchSnapshot(id: UUID(), items: old, settled: true),
                                current: ImageBatchSnapshot(id: UUID(), items: new, settled: true))
    }
    private func retained(_ data: Data) throws -> RetainedReport {
        RetainedReport(data: data, report: try AuditReport.decode(data), provenance: LibraryProvenance(sourceLabel: "Owned saved report"))
    }
    private func execute(_ report: ComparisonReport, before: Data, after: Data, runner: BatchComparisonRunner) async throws -> BatchComparisonResult {
        let old = try batchItem("baseline", data: before), new = try batchItem("current", data: after)
        let baseline = try retained(before), current = try retained(after), output = try JSONEncoder().encode(report)
        return try await runner.run(plan: batchPlan([old], [new]), pairs: [BatchImagePair(baselineID: old.id, currentID: new.id)],
            load: { id in id == old.retainedReportID ? baseline : current }, compare: { left, right in
                XCTAssertEqual(left, before); XCTAssertEqual(right, after); return output
            })
    }
    func testStrictMissingBodyStatusRemainsUnavailableWithoutPayload() async throws {
        let (old, new) = try pair(), before = try named(old, "work"), after = try named(new, "work")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        let report = try configured([value], before: before, after: after, policy: ordinary)
        let result = try await execute(report, before: before, after: after, runner: BatchComparisonRunner(requireSavedReportCoverage: true))
        XCTAssertEqual(result.rows[0].state, "unavailable")
        XCTAssertNil(result.rows[0].comparison); XCTAssertNil(result.rows[0].comparisonData)
    }
    private func workFixture(_ status: Bool? = false) throws -> (ComparisonReport, Data, Data) {
        let (old, new) = try pair(), before = try named(old, "work"), after = try named(new, "work")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        return (try configured([value], before: before, after: after, status: status, policy: ordinary), before, after)
    }
    func testDefaultInitializerReferenceRetainsLegacyPartialAcceptance() async throws {
        let factory: () -> BatchComparisonRunner = BatchComparisonRunner.init
        let (_, old, after) = try workFixture(nil)
        let before = try additional(old, id: unknownID, name: "other")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        let report = try configured([value], before: before, after: after, policy: ordinary)
        let result = try await execute(report, before: before, after: after, runner: factory())
        XCTAssertEqual(result.rows[0].state, "compared")
        XCTAssertNotNil(result.rows[0].comparisonData)
        XCTAssertNil(result.rows[0].comparison?.comparison.exactBodyCandidates)
    }
    func testStrictBodyDisabledSuccessPreservesAcceptedBytes() async throws {
        let (report, before, after) = try workFixture()
        let output = try JSONEncoder().encode(report)
        let old = try batchItem("baseline", data: before), new = try batchItem("current", data: after)
        let baseline = try retained(before), current = try retained(after)
        let result = try await BatchComparisonRunner(requireSavedReportCoverage: true).run(
            plan: batchPlan([old], [new]), pairs: [BatchImagePair(baselineID: old.id, currentID: new.id)],
            load: { id in id == old.retainedReportID ? baseline : current }, compare: { _, _ in output })
        XCTAssertEqual(result.rows[0].state, "compared")
        XCTAssertEqual(result.rows[0].comparisonData, output)
        XCTAssertEqual(result.rows[0].comparison?.comparison.exactBodyCandidates, false)
    }
    func testStrictBodyEnabledSuccessUsesCoveredBranch() async throws {
        let (old, new) = try pair()
        let before = try named(old, "_entry", fingerprint: true), after = try named(new, "_entry", fingerprint: true)
        let key = "body:arm64-exact-bytes-v1:" + String(repeating: "f", count: 64) + ":4"
        let value = labeled(key, basis: "exact_body_candidate", old: oldID, new: newID, name: "_entry")
        let report = try configured([value], before: before, after: after, status: true, policy: ordinary + bodySuffix)
        let result = try await execute(report, before: before, after: after, runner: BatchComparisonRunner(requireSavedReportCoverage: true))
        XCTAssertEqual(result.rows[0].state, "compared")
        XCTAssertEqual(result.rows[0].comparison?.changes[0].matchBasis, "exact_body_candidate")
    }
    func testStrictSameImageSuccessPreservesMissingBodyMetadata() async throws {
        let before = try source("before", id: oldID, digest: "1"), after = try source("after", id: newID, digest: "1")
        let value = labeled("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID, name: "after")
        let report = try configured([value], before: before, after: after, policy: ordinary)
        let result = try await execute(report, before: before, after: after, runner: BatchComparisonRunner(requireSavedReportCoverage: true))
        XCTAssertEqual(result.rows[0].state, "compared")
        XCTAssertNil(result.rows[0].comparison?.comparison.exactBodyCandidates)
    }
    func testStrictOmittedGroupHasNoAcceptedPayload() async throws {
        let (_, old, after) = try workFixture()
        let before = try additional(old, id: unknownID, name: "other")
        let value = labeled("symbol:work", old: oldID, new: newID, name: "work")
        let report = try configured([value], before: before, after: after, status: false, policy: ordinary)
        let result = try await execute(report, before: before, after: after, runner: BatchComparisonRunner(requireSavedReportCoverage: true))
        XCTAssertEqual(result.rows[0].state, "unavailable")
        XCTAssertNil(result.rows[0].comparison); XCTAssertNil(result.rows[0].comparisonData)
    }
    func testStrictForgedNameHasNoAcceptedPayload() async throws {
        let (_, before, after) = try workFixture()
        let value = labeled("symbol:work", old: oldID, new: newID, name: "unrelated")
        let report = try configured([value], before: before, after: after, status: false, policy: ordinary)
        let result = try await execute(report, before: before, after: after, runner: BatchComparisonRunner(requireSavedReportCoverage: true))
        XCTAssertEqual(result.rows[0].state, "unavailable")
        XCTAssertNil(result.rows[0].comparison); XCTAssertNil(result.rows[0].comparisonData)
    }
    func testStrictFailureContinuesLaterPairAndProgressNeverAcceptsBadOutput() async throws {
        let (valid, before, after) = try workFixture()
        let (invalid, _, _) = try workFixture(nil)
        let validBytes = try JSONEncoder().encode(valid), invalidBytes = try JSONEncoder().encode(invalid)
        let olds = try [batchItem("old1", data: before), batchItem("old2", data: before)]
        let news = try [batchItem("new1", data: after), batchItem("new2", data: after)]
        let baseline = try retained(before), current = try retained(after), probe = CoveredBatchProbe()
        let result = try await BatchComparisonRunner(requireSavedReportCoverage: true).run(plan: batchPlan(olds, news),
            pairs: zip(olds, news).map { BatchImagePair(baselineID: $0.id, currentID: $1.id) },
            load: { id in olds.contains { $0.retainedReportID == id } ? baseline : current },
            compare: { _, _ in await probe.next() == 1 ? invalidBytes : validBytes },
            progress: { snapshot in await probe.record(snapshot) })
        XCTAssertEqual(result.rows.map(\.state), ["unavailable", "compared"])
        XCTAssertNil(result.rows[0].comparison); XCTAssertNil(result.rows[0].comparisonData)
        XCTAssertEqual(result.rows[1].comparisonData, validBytes)
        XCTAssertTrue(result.settled); XCTAssertFalse(result.cancelled)
        let states = await probe.snapshots()
        XCTAssertTrue(states.contains(["unavailable", "pending"]))
        XCTAssertFalse(states.contains { $0.first == "compared" })
    }
    func testSameStrictRunnerDoesNotReusePreviousSuccessfulPayload() async throws {
        let runner = BatchComparisonRunner(requireSavedReportCoverage: true)
        let (valid, before, after) = try workFixture()
        let first = try await execute(valid, before: before, after: after, runner: runner)
        XCTAssertEqual(first.rows[0].state, "compared")
        let (invalid, _, _) = try workFixture(nil)
        let second = try await execute(invalid, before: before, after: after, runner: runner)
        XCTAssertEqual(second.rows[0].state, "unavailable")
        XCTAssertNil(second.rows[0].comparison); XCTAssertNil(second.rows[0].comparisonData)
        XCTAssertNotNil(first.rows[0].comparisonData)
    }
    func testStrictRefusalExportContainsNoComparisonPayload() async throws {
        let (report, before, after) = try workFixture(nil)
        let result = try await execute(report, before: before, after: after, runner: BatchComparisonRunner(requireSavedReportCoverage: true))
        let value = try object(result.exportData()), rows = try XCTUnwrap(value["rows"] as? [[String: Any]])
        XCTAssertEqual(rows[0]["state"] as? String, "unavailable")
        XCTAssertNil(rows[0]["comparison"])
        XCTAssertEqual(value["settled"] as? Bool, true)
    }
}

private actor CoveredBatchProbe {
    private var count = 0
    private var states: [[String]] = []
    func next() -> Int { count += 1; return count }
    func record(_ result: BatchComparisonResult) { states.append(result.rows.map(\.state)) }
    func snapshots() -> [[String]] { states }
}
