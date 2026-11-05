import XCTest
import Foundation
import AIRSCore
import AIRSEntitlements
import EntitlementDiffCore
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

    func testUnavailableHelperInfoDoesNotInventStaleness() async throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent(".build/track-a-helper-boundary/" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        func app(_ name: String) throws -> URL {
            let bundle = root.appendingPathComponent(name + ".app"), contents = bundle.appendingPathComponent("Contents")
            try FileManager.default.createDirectory(at: contents.appendingPathComponent("MacOS"), withIntermediateDirectories: true)
            try FileManager.default.createDirectory(at: contents.appendingPathComponent("Helpers"), withIntermediateDirectories: true)
            var image = Data([0xcf, 0xfa, 0xed, 0xfe])
            for word: UInt32 in [0x0100000c, 0, 2, 1, 24, 0, 0, 0x32, 24, 1, 0x000e0000, 0, 0] {
                image.append(contentsOf: (0..<4).map { UInt8(truncatingIfNeeded: word >> ($0 * 8)) })
            }
            try image.write(to: contents.appendingPathComponent("MacOS/Main"))
            try image.write(to: contents.appendingPathComponent("Helpers/Owned"))
            try PropertyListSerialization.data(fromPropertyList: ["CFBundleExecutable": "Main", "CFBundleIdentifier": "owned", "CFBundleShortVersionString": "1"], format: .xml, options: 0).write(to: contents.appendingPathComponent("Info.plist"))
            return bundle
        }
        let session = try ComponentReviewOperations.build(app("Previous"), app("Current"), .arm64)
        let helper = try XCTUnwrap(session.review.current.components.first { $0.relativePath == "Contents/Helpers/Owned" })
        struct ReaderTrap: CodeUnitSnapshotReading {
            func read(unit: BundleImageProvenance, architecture: Architecture) async throws -> EntitlementSnapshot {
                XCTFail("Unavailable Info must refuse before invoking the entitlement reader")
                throw SecurityDeltaRefusal(.invalidReview)
            }
        }
        let result = try await ComponentSecurityDeltaOperations.captureEntitlements(session, side: .current, componentID: helper.id, reader: ReaderTrap())
        XCTAssertEqual(result.state, .unavailable)
        XCTAssertEqual(result.reason, "source_unavailable")
        XCTAssertNil(result.values)
    }

    func testChangedInfoWithEqualImageDigestSurvivesOriginalBundleDisappearance() async throws {
        let root = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent(".build/track-a-historical-disappearance/" + UUID().uuidString)
        defer { try? FileManager.default.removeItem(at: root) }
        func app(_ name: String, version: String) throws -> URL {
            let bundle = root.appendingPathComponent(name + ".app"), contents = bundle.appendingPathComponent("Contents")
            try FileManager.default.createDirectory(at: contents.appendingPathComponent("MacOS"), withIntermediateDirectories: true)
            var image = Data([0xcf, 0xfa, 0xed, 0xfe])
            for word: UInt32 in [0x0100000c, 0, 2, 1, 24, 0, 0, 0x32, 24, 1, 0x000e0000, 0, 0] {
                image.append(contentsOf: (0..<4).map { UInt8(truncatingIfNeeded: word >> ($0 * 8)) })
            }
            try image.write(to: contents.appendingPathComponent("MacOS/Main"))
            try PropertyListSerialization.data(fromPropertyList: ["CFBundleExecutable": "Main", "CFBundleIdentifier": "owned", "CFBundleShortVersionString": version], format: .xml, options: 0).write(to: contents.appendingPathComponent("Info.plist"))
            return bundle
        }
        let previous = try app("Previous", version: "1"), current = try app("Current", version: "2")
        var session = try ComponentReviewOperations.build(previous, current, .arm64)
        for side in [SecurityDeltaSide.previous, .current] {
            let inventory = side == .previous ? session.review.previous : session.review.current
            let id = try XCTUnwrap(inventory.components.first { $0.kind == "app" }?.id)
            session = try ComponentSecurityDeltaOperations.capturingSignature(session, side: side, componentID: id)
        }
        let report = try XCTUnwrap(session.securityDeltaReport)
        XCTAssertEqual(report.observations.first { $0.category == .informationPropertyList && $0.subject == "key:CFBundleShortVersionString" }?.disposition, .observedChange)
        XCTAssertEqual(report.observations.first { $0.category == .signatureEvidence && $0.subject == "containerSHA256" }?.disposition, .unchanged)
        let bytes = try XCTUnwrap(session.securityDeltaArchiveBytes)
        try FileManager.default.removeItem(at: previous)
        try FileManager.default.removeItem(at: current)
        XCTAssertFalse(FileManager.default.fileExists(atPath: previous.path))
        XCTAssertFalse(FileManager.default.fileExists(atPath: current.path))
        let restored = try ComponentSecurityDeltaArchive.decode(bytes)
        let historical = try ComponentReviewSession(review: restored.admittedReview.review, archiveBytes: restored.sourceReviewArchive, sourceURLs: [], live: nil,
            securityDeltaReport: restored.report, entitlementEvidence: restored.entitlementEvidence, signatureEvidence: restored.signatureEvidence,
            signatureRefusals: restored.signatureRefusals, admittedReview: restored.admittedReview)
        XCTAssertNil(historical.live)
        let component = try XCTUnwrap(historical.review.current.components.first?.id)
        XCTAssertThrowsError(try ComponentSecurityDeltaOperations.capturingSignature(historical, side: .current, componentID: component))
        do {
            _ = try await ComponentSecurityDeltaOperations.captureEntitlements(historical, side: .current, componentID: component)
            XCTFail("Historical reopening must not recreate source authority")
        } catch { XCTAssertNotNil(error as? AIRSCore.ReportError) }
        for finding in restored.report.findings {
            for reference in finding.evidence { _ = try ComponentSecurityDeltaOperations.resolveEvidence(reference, in: historical) }
        }
    }

    func testFirstAuthenticHelperEntitlementCaptures() async throws {
        guard let path = ProcessInfo.processInfo.environment["AIRS_REAL_CORPUS_HELPERS"] else { throw XCTSkip("Opt-in first helper-source capture absent") }
        let driver = try RealCorpusDriver.load(URL(fileURLWithPath: path))
        let wanted: Set<String> = ["alienator88.pearcleaner.5.4.0-to-5.4.1", "p0deje.maccy.2.6.1-to-2.7.0", "keycastr.keycastr.v0.10.4-to-v0.10.5", "swiftbar.swiftbar.v2.1.2-beta-2-to-v2.1.2-beta-3"]
        var results: [[String: String]] = []
        for item in driver.cases where wanted.contains(item.caseID) {
            let session = try ComponentReviewOperations.build(URL(fileURLWithPath: item.previous), URL(fileURLWithPath: item.current), .arm64)
            let helper = try XCTUnwrap(session.review.current.components.first { record in
                session.review.currentDeclarations.contains { $0.componentID == record.id && $0.category == .info && $0.state == .unavailable }
            })
            let captured = try await ComponentSecurityDeltaOperations.capturingEntitlements(session, side: .current, componentID: helper.id)
            let evidence = try XCTUnwrap(captured.entitlementEvidence.first { $0.side == .current && $0.componentID == helper.id })
            XCTAssertEqual(evidence.state, .unavailable)
            XCTAssertEqual(evidence.reason, "source_unavailable")
            let output = URL(fileURLWithPath: driver.output).appendingPathComponent(item.caseID).appendingPathComponent("first-helper-capture.json")
            let retained = try XCTUnwrap(captured.securityDeltaArchiveBytes)
            try RealCorpusDriver.publish(retained, to: output)
            results.append(["case_id": item.caseID, "path": helper.relativePath, "state": evidence.state.rawValue, "reason": evidence.reason ?? "", "basis": "Separate first capture for a previously unexamined helper; fresh inventory identities"])
        }
        XCTAssertEqual(results.count, 4)
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        try RealCorpusDriver.publish(encoder.encode(results), to: URL(fileURLWithPath: driver.output).appendingPathComponent("first-helper-capture-ledger.json"))
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
