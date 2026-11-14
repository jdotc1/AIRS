import Foundation
import AppKit
import SwiftUI
import LumenUI
import XCTest
import AIRSCore
import AIRSEntitlements
@testable import AIRSApp

final class SettledSidebarNavigationTests: XCTestCase {
    @MainActor
    func testLiveShellRemembersDirectExternalRoute() async throws {
        let root = sidebarNavigationScratchRoot(environment: ProcessInfo.processInfo.environment)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let audit = AuditWorkspace(recents: SettingsReviewRecents(), supportRoot: root, preferences: .standard)
        let entitlements = EntitlementsWorkspace(library: EntitlementReportLibrary(root: root.appendingPathComponent("reports")),
            batchHistory: EntitlementBatchHistory(root: root.appendingPathComponent("history")),
            recovery: EntitlementBatchRecovery(root: root.appendingPathComponent("recovery")),
            inspectionLibrary: InspectionLibrary(root: root.appendingPathComponent("inspection")))
        let navigation = AIRSNavigation()
        let fileOpen = AIRSFileOpen(hasModal: { false }, projectStore: InspectionProjectStore(root: root.appendingPathComponent("projects")))
        let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1000, height: 700),
                              styleMask: [.titled, .closable], backing: .buffered, defer: false)
        window.contentView = NSHostingView(rootView: AIRSWindowView(audit: audit, entitlements: entitlements,
            navigation: navigation, fileOpen: fileOpen).lumenMetrics(.standard))
        window.orderFront(nil)
        defer { window.orderOut(nil); window.contentView = nil }
        navigation.showsSwiftFlow = true
        try await Task.sleep(nanoseconds: 150_000_000)
        navigation.showsSwiftFlow = false; navigation.showsEntitlements = true
        try await Task.sleep(nanoseconds: 150_000_000)
        navigation.selectWorkspace(.unwind, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), .swiftFlow)
    }
    @MainActor
    func testSavedReportTriageBlocksWorkspaceSwitchUntilClosed() throws {
        let root = sidebarNavigationScratchRoot(environment: ProcessInfo.processInfo.environment)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let audit = AuditWorkspace(recents: SettingsReviewRecents(), supportRoot: root, preferences: .standard)
        let entitlements = EntitlementsWorkspace(library: EntitlementReportLibrary(root: root.appendingPathComponent("reports")),
            batchHistory: EntitlementBatchHistory(root: root.appendingPathComponent("history")),
            recovery: EntitlementBatchRecovery(root: root.appendingPathComponent("recovery")),
            inspectionLibrary: InspectionLibrary(root: root.appendingPathComponent("inspection")))
        let navigation = AIRSNavigation()
        let fileOpen = AIRSFileOpen(hasModal: { false }, projectStore: InspectionProjectStore(root: root.appendingPathComponent("projects")))
        navigation.select(.swiftFlow, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        fileOpen.savedReportTriage = SavedReportTriageSession(sources: [], auditRevision: audit.reportRevision,
            entitlementRevision: entitlements.model.reportRevision)
        XCTAssertFalse(navigation.canSelectDestination(audit: audit, entitlements: entitlements, fileOpen: fileOpen))
        navigation.selectWorkspace(.entitlements, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), .swiftFlow)
        fileOpen.closeCoverage()
        navigation.selectWorkspace(.entitlements, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), .entitlements)
        navigation.selectWorkspace(.unwind, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), .swiftFlow)
    }
    @MainActor
    func testDirectRoutePreservesPreviouslySelectedWorkspaceDestination() throws {
        let root = sidebarNavigationScratchRoot(environment: ProcessInfo.processInfo.environment)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let audit = AuditWorkspace(recents: SettingsReviewRecents(), supportRoot: root, preferences: .standard)
        let entitlements = EntitlementsWorkspace(library: EntitlementReportLibrary(root: root.appendingPathComponent("reports")),
            batchHistory: EntitlementBatchHistory(root: root.appendingPathComponent("history")),
            recovery: EntitlementBatchRecovery(root: root.appendingPathComponent("recovery")),
            inspectionLibrary: InspectionLibrary(root: root.appendingPathComponent("inspection")))
        let navigation = AIRSNavigation()
        let fileOpen = AIRSFileOpen(hasModal: { false }, projectStore: InspectionProjectStore(root: root.appendingPathComponent("projects")))
        navigation.select(.swiftFlow, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        navigation.showsSwiftFlow = false; navigation.showsEntitlements = true
        navigation.selectWorkspace(.unwind, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), .swiftFlow)
    }
    @MainActor
    func testWorkspaceSwitcherRetainsEachDestinationAndRespectsBusyState() async throws {
        let root = sidebarNavigationScratchRoot(environment: ProcessInfo.processInfo.environment)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let audit = AuditWorkspace(recents: SettingsReviewRecents(), supportRoot: root, preferences: .standard)
        let entitlements = EntitlementsWorkspace(library: EntitlementReportLibrary(root: root.appendingPathComponent("reports")),
            batchHistory: EntitlementBatchHistory(root: root.appendingPathComponent("history")),
            recovery: EntitlementBatchRecovery(root: root.appendingPathComponent("recovery")),
            inspectionLibrary: InspectionLibrary(root: root.appendingPathComponent("inspection")))
        let navigation = AIRSNavigation()
        let fileOpen = AIRSFileOpen(hasModal: { false }, projectStore: InspectionProjectStore(root: root.appendingPathComponent("projects")))
        navigation.select(.swiftFlow, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        navigation.selectWorkspace(.entitlements, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), .entitlements)
        navigation.selectWorkspace(.unwind, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), .swiftFlow)
        _ = await fileOpen.finishBeforeQuit()
        navigation.selectWorkspace(.entitlements, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
        XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), .swiftFlow)
        XCTAssertEqual(AIRSWorkspace.unwind.rawValue, "unwind")
        XCTAssertEqual(AIRSWorkspace.entitlements.rawValue, "entitlements")
    }
    @MainActor
    func testEveryDestinationSurvivesPendingWorkSettlementAndRoundTrips() async throws {
        let root = sidebarNavigationScratchRoot(environment: ProcessInfo.processInfo.environment)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let suite = "dev.airs.navigation-test.\(UUID().uuidString)"
        let preferences = try XCTUnwrap(UserDefaults(suiteName: suite))
        defer { preferences.removePersistentDomain(forName: suite) }
        let audit = AuditWorkspace(recents: SettingsReviewRecents(), supportRoot: root, preferences: preferences)
        let entitlements = EntitlementsWorkspace(
            library: EntitlementReportLibrary(root: root.appendingPathComponent("reports")),
            batchHistory: EntitlementBatchHistory(root: root.appendingPathComponent("history")),
            recovery: EntitlementBatchRecovery(root: root.appendingPathComponent("recovery")),
            inspectionLibrary: InspectionLibrary(root: root.appendingPathComponent("inspection")))
        let navigation = AIRSNavigation()
        let fileOpen = AIRSFileOpen(hasModal: { false }, projectStore: InspectionProjectStore(root: root.appendingPathComponent("projects")))
        func settle() async throws {
            for _ in 0..<200 {
                if !audit.isBusy && !entitlements.isBusy && !fileOpen.blocksActions { break }
                try await Task.sleep(nanoseconds: 10_000_000)
            }
            XCTAssertFalse(audit.isBusy); XCTAssertFalse(entitlements.isBusy)
            // Give queued main-actor/view notifications an additional turn after worker completion.
            try await Task.sleep(nanoseconds: 30_000_000)
        }
        for source in AIRSDestination.allCases {
            for target in AIRSDestination.allCases {
                navigation.select(source, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
                try await settle()
                navigation.select(target, audit: audit, entitlements: entitlements, fileOpen: fileOpen)
                try await settle()
                XCTAssertEqual(navigation.destination(audit: audit, entitlements: entitlements), target, "\(source) → \(target) after settlement")
                XCTAssertFalse(audit.showingError); XCTAssertNil(entitlements.errorMessage)
                XCTAssertNil(audit.batchSnapshot, "Navigation must never start image analysis")
                XCTAssertNil(entitlements.batchResult, "Navigation must never start comparison")
            }
        }
    }
}

/// Shared by navigation checks and bounded path-policy tests.
func sidebarNavigationScratchRoot(environment: [String: String]) -> URL {
    let parent = environment["AIRS_TEST_OUTPUT_ROOT"].map { URL(fileURLWithPath: $0, isDirectory: true) }
        ?? FileManager.default.temporaryDirectory
    return parent.appendingPathComponent("AIRS-navigation-test-\(UUID().uuidString)", isDirectory: true)
}
