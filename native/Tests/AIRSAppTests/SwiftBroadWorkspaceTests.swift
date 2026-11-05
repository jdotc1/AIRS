import XCTest
import AIRSCore
@testable import AIRSApp

final class SwiftBroadWorkspaceTests: XCTestCase {
    @MainActor func testExtendedHistoricalReopenAndCancellation() async throws {
        let original = try broad()
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: original) as? [String: Any])
        object["model_version"] = "swift-broad-error-flow-extended-v1"; object["profile"] = "broad-extended-v1"
        let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
            .appendingPathComponent("local-evidence/track-b-integration/extended-history-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let input = root.appendingPathComponent("report.json"); try data.write(to: input)
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in XCTFail("Historical import must not acquire input"); return Data() })
        workspace.importReport(input); await workspace.waitUntilSettled()
        XCTAssertTrue(workspace.isHistorical); XCTAssertEqual(workspace.profile,.broadExtended); XCTAssertNil(workspace.input)
        XCTAssertEqual(workspace.report?.sourceData,data)
        let cancelling = SwiftFlowWorkspace(execute: { _, _, _ in try await Task.sleep(for: .seconds(20)); return Data() })
        cancelling.profile = .broadExtended; cancelling.selectInput(URL(fileURLWithPath: "/owned/input")); cancelling.run(configuration: configuration)
        cancelling.cancel(); await cancelling.waitUntilSettled()
        XCTAssertNil(cancelling.report); XCTAssertTrue(cancelling.isHistorical); XCTAssertFalse(cancelling.isBusy)
    }
    @MainActor func testExtendedProfileRoutesAndRejectsMismatchedReply() async throws {
        let old = try broad()
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: old) as? [String: Any])
        object["model_version"] = "swift-broad-error-flow-extended-v1"; object["profile"] = "broad-extended-v1"
        let data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        let rejected = SwiftFlowWorkspace(execute: { _, _, _ in old })
        rejected.profile = .broadExtended; rejected.selectInput(URL(fileURLWithPath: "/owned/input")); rejected.run(configuration: configuration)
        await rejected.waitUntilSettled(); XCTAssertNil(rejected.report); XCTAssertNotNil(rejected.errorMessage)
        let accepted = SwiftFlowWorkspace(execute: { _, options, _ in XCTAssertEqual(options.profile, .broadExtended); return data })
        accepted.profile = .broadExtended; accepted.selectInput(URL(fileURLWithPath: "/owned/input")); accepted.run(configuration: configuration)
        await accepted.waitUntilSettled(); XCTAssertNil(accepted.errorMessage); XCTAssertFalse(accepted.isHistorical)
        XCTAssertEqual(accepted.report?.modelVersion, "swift-broad-error-flow-extended-v1")
    }
    @MainActor func testLargeProfileRejectsOtherProfileAndAcceptsItsOwnResult() async throws {
        let old = try broad()
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: old) as? [String: Any])
        object["model_version"] = "swift-broad-error-flow-large-v1"; object["profile"] = "broad-large-v1"
        let large = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        let mismatched = SwiftFlowWorkspace(execute: { _, _, _ in old })
        mismatched.profile = .broadLarge; mismatched.selectInput(URL(fileURLWithPath: "/owned/input")); mismatched.run(configuration: configuration)
        await mismatched.waitUntilSettled(); XCTAssertNil(mismatched.report); XCTAssertNotNil(mismatched.errorMessage)
        let accepted = SwiftFlowWorkspace(execute: { _, options, _ in XCTAssertEqual(options.profile, .broadLarge); return large })
        accepted.profile = .broadLarge; accepted.selectInput(URL(fileURLWithPath: "/owned/input")); accepted.run(configuration: configuration)
        await accepted.waitUntilSettled(); XCTAssertNil(accepted.errorMessage); XCTAssertFalse(accepted.isHistorical)
        XCTAssertEqual(accepted.report?.modelVersion, "swift-broad-error-flow-large-v1")
    }
    private var configuration: EngineConfiguration { .init(pythonExecutable: URL(fileURLWithPath: "/unused/python"), bootstrap: URL(fileURLWithPath: "/unused/bootstrap")) }
    private func broad(_ count: Int = 1, complete: Bool = true) throws -> Data {
        let rows: [[String: Any]] = (0..<count).map { i in
            ["caller_pc": "0x1000", "call_pc": "0x" + String(0x1004 + i * 4, radix: 16),
             "admission": ["status": "unresolved", "reason": "syntax_unqualified", "details_complete": true, "work_steps": 1, "call_return_proven": false],
             "candidate": NSNull(), "validation": NSNull()]
        }
        return try JSONSerialization.data(withJSONObject: ["model_version": "swift-broad-error-flow-v1", "profile": "broad-v1", "witness_model_version": "swift-outcome-witness-v2", "validation_model_version": "swift-outcome-validation-v2",
            "identity": ["architecture": "arm64", "cpu_subtype": 0, "uuid": NSNull(), "preferred_base": "0x1000", "slice_sha256": String(repeating: "a", count: 64), "container_sha256": String(repeating: "b", count: 64), "slice_index": 0, "container_slice_count": 1, "slice_offset": "0x0", "slice_size": "0x10000"],
            "word_scan_complete": complete, "call_details_complete": complete, "outcome_witnesses_complete": complete,
            "observed_call_instructions": count, "selected_call_candidates": count, "omitted_calls": 0, "scanned_words": 1024, "analysis_work": 999,
            "calls": rows, "status_counts": ["unresolved": count], "reason_counts": ["syntax_unqualified": count], "research_only": true, "call_return_proven": false, "runtime_reachability_proven": false, "limitations": ["structural_only"]], options: [.sortedKeys])
    }
    private func narrow() throws -> Data {
        try JSONSerialization.data(withJSONObject: ["schema_version": 1, "report_kind": "airs.swift_error_flow", "model_version": "swift-sync-error-edges-v37", "image": ["architecture": "arm64", "cpu_subtype": 0, "preferred_base": "0x0", "slice_sha256": String(repeating: "a", count: 64), "container_sha256": String(repeating: "b", count: 64), "slice_offset": 0, "slice_size": 128], "word_scan_complete": true, "call_details_complete": true, "limitations": ["Structural only"], "calls": [["caller_pc": "0x0", "call_pc": "0x4", "status": "recovered_candidate", "notes": String(repeating: "x", count: 20000)]]])
    }
    func testBroadArgumentsForcePrerequisitesAndExcludeNarrowMethods() {
        let args = SwiftFlowOptions(includeMethods: true, includeWitnesses: false, profile: .broad).arguments(input: URL(fileURLWithPath: "/owned/a ; app"), output: URL(fileURLWithPath: "/owned/out"))
        XCTAssertEqual(args.filter { $0 == "--include-outcome-witnesses" }.count, 1)
        XCTAssertTrue(args.contains("--swift-profile")); XCTAssertTrue(args.contains("broad-v1")); XCTAssertFalse(args.contains("--include-swift-methods"))
        for flag in ["--include-error-regions", "--validate-region-entries", "--include-structured-presentation"] { XCTAssertTrue(args.contains(flag)) }
        XCTAssertEqual(Array(args.suffix(2)), ["--", "/owned/a ; app"])
    }
    func testStandardArgumentsPreserveNarrowOptIns() {
        let args = SwiftFlowOptions(includeMethods: true, includeWitnesses: true).arguments(input: URL(fileURLWithPath: "/owned/a"), output: URL(fileURLWithPath: "/owned/out"))
        XCTAssertTrue(args.contains("--include-swift-methods")); XCTAssertTrue(args.contains("--include-outcome-witnesses")); XCTAssertFalse(args.contains("--swift-profile"))
    }
    @MainActor func testBroadRunForwardsProfileAndShowsPartialCoverage() async throws {
        let data = try broad(257, complete: false)
        let workspace = SwiftFlowWorkspace(execute: { _, options, _ in XCTAssertEqual(options.profile, .broad); return data })
        workspace.profile = .broad; workspace.selectInput(URL(fileURLWithPath: "/owned/input")); workspace.run(configuration: configuration)
        await workspace.waitUntilSettled()
        XCTAssertNil(workspace.errorMessage); XCTAssertFalse(workspace.isHistorical); XCTAssertTrue(workspace.status.contains("Partial"))
        XCTAssertEqual(workspace.report?.calls.count, 257); XCTAssertEqual(workspace.displayedCalls.count, 200); XCTAssertEqual(workspace.callPageCount, 2)
        workspace.moveCallPage(1); XCTAssertEqual(workspace.displayedCalls.count, 57); XCTAssertEqual(workspace.callPage, 1)
        workspace.moveCallPage(1); XCTAssertEqual(workspace.callPage, 1)
        workspace.profile = .standard; XCTAssertTrue(workspace.isHistorical)
    }
    @MainActor func testBroadCommandCannotPublishNarrowResponseAsCurrent() async throws {
        let data = try narrow(); let workspace = SwiftFlowWorkspace(execute: { _, _, _ in data })
        workspace.profile = .broad; workspace.selectInput(URL(fileURLWithPath: "/owned/input")); workspace.run(configuration: configuration)
        await workspace.waitUntilSettled(); XCTAssertNil(workspace.report); XCTAssertTrue(workspace.isHistorical); XCTAssertNotNil(workspace.errorMessage)
    }
    @MainActor func testProfileChangeDiscardsLateBroadCompletion() async throws {
        let data = try broad(); let workspace = SwiftFlowWorkspace(execute: { _, _, _ in try await Task.sleep(for: .milliseconds(30)); return data })
        workspace.profile = .broad; workspace.selectInput(URL(fileURLWithPath: "/owned/input")); workspace.run(configuration: configuration); workspace.profile = .standard
        await workspace.waitUntilSettled(); XCTAssertNil(workspace.report); XCTAssertTrue(workspace.isHistorical); XCTAssertFalse(workspace.isBusy)
    }
    @MainActor func testFullDetailPagesRetainPreviouslyHiddenEvidence() async throws {
        let data = try narrow(); let workspace = SwiftFlowWorkspace(execute: { _, _, _ in data })
        workspace.selectInput(URL(fileURLWithPath: "/owned/input")); workspace.run(configuration: configuration); await workspace.waitUntilSettled()
        XCTAssertEqual(workspace.detailPageCount, 2); XCTAssertLessThanOrEqual(workspace.detailText.count, 16000)
        workspace.moveDetailPage(1); XCTAssertFalse(workspace.detailText.isEmpty); XCTAssertEqual(workspace.detailPage, 1)
        XCTAssertEqual(workspace.report?.sourceData, data)
    }
    @MainActor func testHistoricalBroadImportAndExactExportHaveNoLiveAuthority() async throws {
        let repo = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let root = repo.appendingPathComponent("local-evidence/track-b-integration/owned-broad-workspace-" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let data = try broad(), source = root.appendingPathComponent("historical.json"), destination = root.appendingPathComponent("export.json")
        try data.write(to: source)
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in XCTFail("Import must not start an engine job"); return Data() })
        workspace.importReport(source); await workspace.waitUntilSettled()
        XCTAssertNil(workspace.errorMessage); XCTAssertTrue(workspace.isHistorical); XCTAssertNil(workspace.input)
        XCTAssertEqual(workspace.profile, .broad); XCTAssertEqual(workspace.report?.sourceData, data)
        try workspace.export(to: destination); XCTAssertEqual(try Data(contentsOf: destination), data)
        XCTAssertThrowsError(try workspace.export(to: source))
    }

    @MainActor func testBroadCancellationSettlesOwnedTaskBeforeControlsReset() async throws {
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in try await Task.sleep(for: .seconds(20)); return Data() })
        workspace.profile = .broad; workspace.selectInput(URL(fileURLWithPath: "/owned/input")); workspace.run(configuration: configuration)
        workspace.cancel(); XCTAssertTrue(workspace.isBusy)
        await workspace.waitUntilSettled(); XCTAssertFalse(workspace.isBusy); XCTAssertTrue(workspace.isHistorical); XCTAssertNil(workspace.report)
    }

    func testPublicDecodeRejectsDuplicateBroadToNarrowDispatchEnvelope() throws {
        let legacy = String(decoding: try narrow(), as: UTF8.self)
        let mixed = "{\"model_version\":\"swift-broad-error-flow-v1\",\"profile\":\"broad-v1\",\"profile\":\"standard\"," + legacy.dropFirst()
        XCTAssertThrowsError(try SwiftFlowReport.decode(Data(mixed.utf8)))
    }

}
