import Foundation
import XCTest
@testable import AIRSApp

final class AcceptanceProfileTests: XCTestCase {
    func testExplicitProfileRequiresFreshPhysicalRootAndOwnedRegularFixtures() throws {
        let parent = SettingsReviewConfiguration.reviewParent
        let root = parent.appendingPathComponent("AIRS-acceptance-\(UUID().uuidString)")
        let fixture = parent.appendingPathComponent("acceptance-test-\(UUID().uuidString).json")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        try Data("{}".utf8).write(to: fixture)
        defer { try? FileManager.default.removeItem(at: root); try? FileManager.default.removeItem(at: fixture) }
        let args = ["AIRSApp", "--acceptance-profile", root.path, "--acceptance-report", fixture.path,
                    "--acceptance-comparison", fixture.path]
        let profile = try XCTUnwrap(AcceptanceProfile.parse(arguments: args, environment: [:], bundleIdentifier: "dev.airs.app"))
        XCTAssertEqual(profile.root, root.standardizedFileURL)
        XCTAssertTrue(profile.suite.hasPrefix("dev.airs.acceptance."))
        XCTAssertNil(try AcceptanceProfile.parse(arguments: ["AIRSApp"], environment: [:], bundleIdentifier: "dev.airs.app"))
        for count in 2..<7 {
            XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: Array(args.prefix(count)), environment: [:], bundleIdentifier: "dev.airs.app"))
        }
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: args + ["--acceptance-profile", root.path], environment: [:], bundleIdentifier: "dev.airs.app"))
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: args, environment: ["AIRS_SETTINGS_REVIEW": "1"], bundleIdentifier: "dev.airs.app"))
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: args, environment: [:], bundleIdentifier: "dev.other"))
        var outside = args; outside[4] = "/Applications/AIRS.app/Contents/Info.plist"
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: outside, environment: [:], bundleIdentifier: "dev.airs.app"))
        try Data().write(to: root.appendingPathComponent("used"))
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: args, environment: [:], bundleIdentifier: "dev.airs.app"))
    }

    func testSymlinkFixtureAndProfileAreRejected() throws {
        let parent = SettingsReviewConfiguration.reviewParent
        let root = parent.appendingPathComponent("AIRS-acceptance-\(UUID().uuidString)")
        let target = parent.appendingPathComponent("acceptance-target-\(UUID().uuidString)")
        let link = parent.appendingPathComponent("acceptance-link-\(UUID().uuidString)")
        try FileManager.default.createDirectory(at: target, withIntermediateDirectories: true)
        try FileManager.default.createSymbolicLink(at: root, withDestinationURL: target)
        try Data("{}".utf8).write(to: target.appendingPathComponent("fixture.json"))
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: target.appendingPathComponent("fixture.json"))
        defer { for url in [root, link, target] { try? FileManager.default.removeItem(at: url) } }
        let args = ["AIRSApp", "--acceptance-profile", root.path, "--acceptance-report", link.path,
                    "--acceptance-comparison", link.path]
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: args, environment: [:], bundleIdentifier: "dev.airs.app"))
        try FileManager.default.removeItem(at: root)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: false)
        XCTAssertThrowsError(try AcceptanceProfile.parse(arguments: args, environment: [:], bundleIdentifier: "dev.airs.app"))
    }
}
