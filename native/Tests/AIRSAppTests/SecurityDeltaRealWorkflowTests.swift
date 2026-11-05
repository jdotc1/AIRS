import XCTest
import Foundation
import AIRSCore
import AIRSEntitlements
@testable import AIRSApp

/// Explicitly opt-in. Paths and third-party payloads are never package resources.
final class SecurityDeltaRealWorkflowTests: XCTestCase {
    func testDriverRequiresDistinctSidesAndBoundedCases() throws {
        XCTAssertThrowsError(try RealCorpusDriver.validate([]))
        let same = RealCorpusCase(caseID: "owned.same", previous: "/owned/A.app", current: "/owned/A.app")
        XCTAssertThrowsError(try RealCorpusDriver.validate([same]))
        let pair = RealCorpusCase(caseID: "owned.pair", previous: "/owned/A.app", current: "/owned/B.app")
        XCTAssertNoThrow(try RealCorpusDriver.validate([pair]))
        XCTAssertThrowsError(try RealCorpusDriver.validate([pair, pair]))
    }

    func testHarnessNeverReplacesEvidenceAndBoundsReads() throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent(".build/track-a-owned-io/" + UUID().uuidString)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let destination = root.appendingPathComponent("evidence.json"), original = Data("original".utf8)
        try RealCorpusDriver.publish(original, to: destination)
        XCTAssertThrowsError(try RealCorpusDriver.publish(Data("replacement".utf8), to: destination))
        XCTAssertEqual(try RealCorpusDriver.readBounded(destination, maximum: 8), original)
        XCTAssertThrowsError(try RealCorpusDriver.readBounded(destination, maximum: 7))
        let link = root.appendingPathComponent("link")
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: destination)
        XCTAssertThrowsError(try RealCorpusDriver.readBounded(link, maximum: 8))
    }

    func testAuthorizedAuthenticCaptureAndPureReplay() async throws {
        guard let path = ProcessInfo.processInfo.environment["AIRS_REAL_CORPUS_DRIVER"] else {
            throw XCTSkip("Opt-in authentic corpus absent; no third-party application is acquired or inspected by ordinary CI.")
        }
        let driver = try RealCorpusDriver.load(URL(fileURLWithPath: path))
        try await driver.capture()
    }

    func testFreshInvocationHistoricalReplay() throws {
        guard let path = ProcessInfo.processInfo.environment["AIRS_REAL_CORPUS_REPLAY"] else {
            throw XCTSkip("Requires a prior explicitly authorized retained corpus capture.")
        }
        try RealCorpusDriver.load(URL(fileURLWithPath: path)).replay()
    }
}
