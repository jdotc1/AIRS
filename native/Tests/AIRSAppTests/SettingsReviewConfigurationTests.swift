import Foundation
import XCTest
@testable import AIRSApp

final class SettingsReviewConfigurationTests: XCTestCase {
    private func scratch() throws -> URL {
        let root = sidebarNavigationScratchRoot(environment: ProcessInfo.processInfo.environment)
            .resolvingSymlinksInPath()
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        return root
    }

    func testReviewParentUsesPassedEnvironmentOrPortableTemporaryDefault() throws {
        XCTAssertEqual(try SettingsReviewConfiguration.reviewParent(environment: [:]),
                       FileManager.default.temporaryDirectory.resolvingSymlinksInPath())
        let parent = try scratch()
        defer { try? FileManager.default.removeItem(at: parent) }
        XCTAssertEqual(try SettingsReviewConfiguration.reviewParent(environment: ["AIRS_REVIEW_PARENT": parent.path]), parent)
        XCTAssertThrowsError(try SettingsReviewConfiguration.reviewParent(environment: ["AIRS_REVIEW_PARENT": "relative"]))
        XCTAssertThrowsError(try SettingsReviewConfiguration.reviewParent(environment: ["AIRS_REVIEW_PARENT": ""]))
    }

    func testSettingsParentOverridePreservesIsolationAndFreshness() throws {
        let parent = try scratch()
        defer { try? FileManager.default.removeItem(at: parent) }
        let id = UUID().uuidString.lowercased()
        let root = parent.appendingPathComponent("AIRS-settings-visual-\(id)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        let identifier = "dev.airs.settings-review.\(id)"
        var environment = ["AIRS_REVIEW_PARENT": parent.path, "AIRS_SETTINGS_REVIEW": "1",
                           "AIRS_SETTINGS_REVIEW_ROOT": root.path, "AIRS_SETTINGS_REVIEW_SUITE": identifier + ".preferences"]
        XCTAssertEqual(try SettingsReviewConfiguration.parse(environment: environment, bundleIdentifier: identifier)?.root, root)
        XCTAssertThrowsError(try SettingsReviewConfiguration.parse(environment: environment, bundleIdentifier: "dev.airs.app"))
        environment.removeValue(forKey: "AIRS_REVIEW_PARENT")
        XCTAssertThrowsError(try SettingsReviewConfiguration.parse(environment: environment, bundleIdentifier: identifier))
        environment["AIRS_REVIEW_PARENT"] = parent.path
        try Data("used".utf8).write(to: root.appendingPathComponent("existing"))
        XCTAssertThrowsError(try SettingsReviewConfiguration.parse(environment: environment, bundleIdentifier: identifier))
    }

    func testReviewParentRejectsSymlinkOverride() throws {
        let parent = try scratch()
        defer { try? FileManager.default.removeItem(at: parent) }
        let alias = parent.appendingPathComponent("alias")
        try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: parent)
        XCTAssertThrowsError(try SettingsReviewConfiguration.reviewParent(environment: ["AIRS_REVIEW_PARENT": alias.path]))
    }

    func testAcceptanceUsesPassedParentAndKeepsFixtureContainment() throws {
        let parent = try scratch()
        defer { try? FileManager.default.removeItem(at: parent) }
        let root = parent.appendingPathComponent("AIRS-acceptance-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        let audit = parent.appendingPathComponent("audit.json")
        let comparison = parent.appendingPathComponent("comparison.json")
        try Data("{}".utf8).write(to: audit)
        try Data("{}".utf8).write(to: comparison)
        let arguments = ["AIRSApp", "--acceptance-profile", root.path,
                         "--acceptance-report", audit.path, "--acceptance-comparison", comparison.path]
        let environment = ["AIRS_REVIEW_PARENT": parent.path]
        XCTAssertEqual(try AcceptanceProfile.parse(arguments: arguments, environment: environment, bundleIdentifier: "dev.airs.app")?.root, root)
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: arguments, environment: [:], bundleIdentifier: "dev.airs.app"))
        var outside = arguments
        outside[4] = parent.deletingLastPathComponent().appendingPathComponent("outside.json").path
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: outside, environment: environment, bundleIdentifier: "dev.airs.app"))
        var relative = environment
        relative["AIRS_REVIEW_PARENT"] = "relative"
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: arguments, environment: relative, bundleIdentifier: "dev.airs.app"))
    }

    func testNavigationScratchUsesOutputOverrideThenTemporaryDirectory() {
        let configured = sidebarNavigationScratchRoot(environment: ["AIRS_TEST_OUTPUT_ROOT": "/synthetic/test-output"])
        XCTAssertEqual(configured.deletingLastPathComponent().path, "/synthetic/test-output")
        XCTAssertEqual(sidebarNavigationScratchRoot(environment: [:]).deletingLastPathComponent(), FileManager.default.temporaryDirectory)
        XCTAssertNotEqual(sidebarNavigationScratchRoot(environment: [:]), sidebarNavigationScratchRoot(environment: [:]))
    }
}
