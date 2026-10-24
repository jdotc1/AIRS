import Foundation
import XCTest
import AIRSCore
import AIRSEntitlements
@testable import AIRSApp

final class SettledSidebarNavigationTests: XCTestCase {
    @MainActor
    func testEveryDestinationSurvivesPendingWorkSettlementAndRoundTrips() async throws {
        let root = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent("AIRS-navigation-test-\(UUID().uuidString)")
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
