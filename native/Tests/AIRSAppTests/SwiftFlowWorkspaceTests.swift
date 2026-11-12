import XCTest
import AIRSCore
@testable import AIRSApp

final class SwiftFlowWorkspaceTests: XCTestCase {
    private func fixture() throws -> Data {
        try JSONSerialization.data(withJSONObject: ["schema_version": 1, "report_kind": "airs.swift_error_flow", "model_version": "swift-sync-error-edges-v37", "image": ["architecture": "arm64", "cpu_subtype": 0, "preferred_base": "0x0", "slice_sha256": String(repeating: "a", count: 64), "container_sha256": String(repeating: "b", count: 64), "slice_offset": 0, "slice_size": 128], "word_scan_complete": true, "call_details_complete": true, "limitations": ["Structural only"], "calls": [["caller_pc": "0x0", "call_pc": "0x4", "status": "recovered_candidate"]]])
    }
    private var configuration: EngineConfiguration {
        .init(pythonExecutable: URL(fileURLWithPath: "/unused/python"), bootstrap: URL(fileURLWithPath: "/unused/airs_cli.py"))
    }
    @MainActor func testFreshCompletionAndOptionsMarkHistorical() async throws {
        let data = try fixture()
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in data })
        workspace.selectInput(URL(fileURLWithPath: "/owned/input"))
        workspace.run(configuration: configuration)
        XCTAssertTrue(workspace.isBusy)
        await workspace.waitUntilSettled()
        XCTAssertFalse(workspace.isHistorical)
        XCTAssertEqual(workspace.selection, "0x0:0x4")
        workspace.includeMethods = true
        XCTAssertTrue(workspace.isHistorical)
        XCTAssertNotNil(workspace.report)
    }
    @MainActor func testCancellationRetainsBusyUntilSettlementAndQuit() async throws {
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in
            try await Task.sleep(for: .seconds(20))
            return Data()
        })
        workspace.selectInput(URL(fileURLWithPath: "/owned/input"))
        workspace.run(configuration: configuration); workspace.cancel()
        XCTAssertTrue(workspace.isBusy)
        let settled = await workspace.finishBeforeQuit()
        XCTAssertTrue(settled); XCTAssertFalse(workspace.isBusy); XCTAssertNil(workspace.report)
        XCTAssertTrue(workspace.isHistorical)
    }
    @MainActor func testImportedReportHistoricalAndProtectedExport() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let source = root.appendingPathComponent("source.json"), target = root.appendingPathComponent("export.json")
        let data = try fixture(); try data.write(to: source)
        let workspace = SwiftFlowWorkspace(); workspace.importReport(source)
        await workspace.waitUntilSettled()
        XCTAssertTrue(workspace.isHistorical); XCTAssertNil(workspace.input)
        XCTAssertThrowsError(try workspace.export(to: source))
        try workspace.export(to: target)
        XCTAssertEqual(try Data(contentsOf: target), data)
    }
    @MainActor func testBusyNavigationCannotHideSwiftJob() async throws {
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in try await Task.sleep(for: .seconds(20)); return Data() })
        let navigation = AIRSNavigation(swiftFlow: workspace)
        let audit = AuditWorkspace(), entitlements = EntitlementsWorkspace(), fileOpen = AIRSFileOpen(hasModal: { false })
        navigation.showsSwiftFlow = true
        // Navigation cannot hide an active owned job.
        XCTAssertTrue(navigation.swiftFlow.isHistorical)
        XCTAssertEqual(AIRSDestination.swiftFlow.title, "Swift Error Flow")
        workspace.selectInput(URL(fileURLWithPath: "/owned/input")); workspace.run(configuration: configuration)
        XCTAssertFalse(navigation.canSelectDestination(audit: audit, entitlements: entitlements, fileOpen: fileOpen))
        navigation.select(.audit, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertTrue(navigation.showsSwiftFlow)
        var ran = false; navigation.performAudit { ran = true }; XCTAssertFalse(ran)
        workspace.includeWitnesses = true
        _ = await workspace.finishBeforeQuit()
        XCTAssertTrue(workspace.isHistorical)
    }
    @MainActor func testChangedOptionsCannotPublishStaleCompletion() async throws {
        let data = try fixture()
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in data })
        workspace.selectInput(URL(fileURLWithPath: "/owned/input"))
        workspace.run(configuration: configuration)
        workspace.includeWitnesses = true
        await workspace.waitUntilSettled()
        XCTAssertNil(workspace.report)
        XCTAssertTrue(workspace.isHistorical)
        XCTAssertTrue(workspace.status.contains("superseded"))
    }
    @MainActor func testQuitResumeAndHardlinkExportProtection() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let source = root.appendingPathComponent("source.json"), alias = root.appendingPathComponent("alias.json")
        try fixture().write(to: source)
        try FileManager.default.linkItem(at: source, to: alias)
        let workspace = SwiftFlowWorkspace(); workspace.importReport(source); await workspace.waitUntilSettled()
        XCTAssertThrowsError(try workspace.export(to: alias))
        _ = await workspace.finishBeforeQuit()
        workspace.selectInput(alias); XCTAssertNil(workspace.input)
        workspace.resumeAfterCancelledQuit(); workspace.selectInput(alias)
        XCTAssertEqual(workspace.input, alias)
    }

    @MainActor func testCurrentInputStaysProtectedAcrossSelectionAndHistoricalImport() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let first = root.appendingPathComponent("first.macho"), second = root.appendingPathComponent("second.macho")
        let alias = root.appendingPathComponent("second-alias"), saved = root.appendingPathComponent("saved.json")
        try Data([1]).write(to: first); try Data([2]).write(to: second)
        try FileManager.default.linkItem(at: second, to: alias)
        let data = try fixture(); try data.write(to: saved)
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in data })
        workspace.selectInput(first); workspace.run(configuration: configuration); await workspace.waitUntilSettled()
        workspace.selectInput(second)
        XCTAssertThrowsError(try workspace.export(to: second))
        XCTAssertThrowsError(try workspace.export(to: alias))
        XCTAssertThrowsError(try workspace.export(to: first))
        workspace.importReport(saved); await workspace.waitUntilSettled()
        XCTAssertThrowsError(try workspace.export(to: second))
        XCTAssertThrowsError(try workspace.export(to: alias))
        XCTAssertThrowsError(try workspace.export(to: saved))
        let app = root.appendingPathComponent("Selected.app", isDirectory: true)
        try FileManager.default.createDirectory(at: app, withIntermediateDirectories: true)
        workspace.selectInput(app)
        XCTAssertThrowsError(try workspace.export(to: app.appendingPathComponent("report.json")))
        XCTAssertEqual(try Data(contentsOf: second), Data([2]))
    }

    @MainActor func testExportRefusesSelectedAppUnderAnotherSpellingOfItsFolder() async throws {
        let short = FileManager.default.temporaryDirectory.appendingPathComponent("airs-flow-alias-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: short, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: short) }
        let pointer = try XCTUnwrap(realpath(short.path, nil)); defer { free(pointer) }
        let long = URL(fileURLWithPath: String(cString: pointer), isDirectory: true)
        try XCTSkipIf(long.path == short.path, "temporary folder has no aliased ancestor here")
        let saved = short.appendingPathComponent("saved.json")
        let data = try fixture(); try data.write(to: saved)
        try FileManager.default.createDirectory(at: short.appendingPathComponent("Selected.app/Contents"), withIntermediateDirectories: true)
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in data })
        workspace.importReport(saved); await workspace.waitUntilSettled()
        for (base, alternate) in [(short, long), (long, short)] {
            workspace.selectInput(base.appendingPathComponent("Selected.app", isDirectory: true))
            let nested = alternate.appendingPathComponent("Selected.app/Contents/report.json")
            XCTAssertThrowsError(try workspace.export(to: nested))
            XCTAssertFalse(FileManager.default.fileExists(atPath: nested.path))
            let outside = alternate.appendingPathComponent("outside-\(UUID().uuidString).json")
            XCTAssertNoThrow(try workspace.export(to: outside))
            XCTAssertTrue(FileManager.default.fileExists(atPath: outside.path))
        }
    }
    @MainActor func testCentralAndDelegateFileOpeningRefuseDuringSwiftJob() async throws {
        let workspace = SwiftFlowWorkspace(execute: { _, _, _ in try await Task.sleep(for: .seconds(20)); return Data() })
        let navigation = AIRSNavigation(swiftFlow: workspace)
        let audit = AuditWorkspace(), entitlements = EntitlementsWorkspace(), fileOpen = AIRSFileOpen(hasModal: { false })
        let delegate = AIRSApplicationDelegate()
        delegate.configureFileOpening(audit: audit, entitlements: entitlements, navigation: navigation, fileOpen: fileOpen)
        navigation.showsSwiftFlow = true
        workspace.selectInput(URL(fileURLWithPath: "/owned/input")); workspace.run(configuration: configuration)
        XCTAssertNil(fileOpen.open([URL(fileURLWithPath: "/missing/New.app")], audit: audit, entitlements: entitlements, navigation: navigation))
        delegate.receiveOpenURLs([URL(fileURLWithPath: "/missing/report.json")])
        XCTAssertNil(fileOpen.intakeReview); XCTAssertNil(fileOpen.errorMessage)
        XCTAssertNil(audit.report); XCTAssertTrue(navigation.showsSwiftFlow)
        XCTAssertTrue(fileOpen.status.contains("Finish the current action"))
        _ = await workspace.finishBeforeQuit()
    }

}
