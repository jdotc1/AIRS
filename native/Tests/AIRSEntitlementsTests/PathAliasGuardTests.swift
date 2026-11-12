import Darwin
import Foundation
import XCTest
import AIRSCore
import EntitlementDiffCore
@testable import AIRSEntitlements

final class PathAliasGuardTests: XCTestCase {
    private func aliases() throws -> (URL, URL) {
        let short = FileManager.default.temporaryDirectory.appendingPathComponent("airs-alias-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: short, withIntermediateDirectories: true)
        addTeardownBlock { try? FileManager.default.removeItem(at: short) }
        let pointer = try XCTUnwrap(realpath(short.path, nil)); defer { free(pointer) }
        let long = URL(fileURLWithPath: String(cString: pointer), isDirectory: true)
        try XCTSkipIf(long.path == short.path, "temporary folder has no aliased ancestor here")
        return (short, long)
    }

    func testManifestAcceptsAllBaseAndAppSpellingsAndPreservesCallerPaths() throws {
        let (short, long) = try aliases()
        for base in [short, long] {
            for apps in [short, long] {
                let previous = apps.appendingPathComponent("Previous.app", isDirectory: true)
                let current = apps.appendingPathComponent("nested/Current.app", isDirectory: true)
                let pair = EntitlementBatchPair(previous: previous, current: current, architecture: .arm64)
                let manifest = try EntitlementBatchManifest(pairs: [pair], relativeTo: base)
                XCTAssertEqual(manifest.version, 2)
                XCTAssertEqual(manifest.pairs[0].previousPath, "Previous.app")
                XCTAssertEqual(manifest.pairs[0].currentPath, "nested/Current.app")
                let original = try XCTUnwrap(manifest.makePairs().first)
                XCTAssertEqual(Array(original.previous.path.utf8), Array(previous.path.utf8))
                XCTAssertEqual(Array(original.current.path.utf8), Array(current.path.utf8))
                let parsed = try EntitlementBatchManifest.parse(manifest.data(), relativeTo: apps)
                let restored = try XCTUnwrap(parsed.makePairs().first)
                XCTAssertEqual(Array(restored.previous.path.utf8), Array(previous.path.utf8))
                XCTAssertEqual(Array(restored.current.path.utf8), Array(current.path.utf8))
                let baseParsed = try EntitlementBatchManifest.parse(manifest.data(), relativeTo: base)
                let basePair = try XCTUnwrap(baseParsed.makePairs().first)
                XCTAssertEqual(basePair.previous.path, base.appendingPathComponent("Previous.app").path)
                XCTAssertEqual(basePair.current.path, base.appendingPathComponent("nested/Current.app").path)
                XCTAssertFalse(FileManager.default.fileExists(atPath: previous.path))
                XCTAssertFalse(FileManager.default.fileExists(atPath: current.path))
            }
        }
    }

    func testManifestWritesThroughEitherBaseAliasAndRejectsUnrelatedBase() throws {
        let (short, long) = try aliases()
        for (base, destinationBase) in [(short, long), (long, short)] {
            let pair = EntitlementBatchPair(previous: base.appendingPathComponent("Previous.app"),
                current: base.appendingPathComponent("Current.app"), architecture: .arm64)
            let manifest = try EntitlementBatchManifest(pairs: [pair], relativeTo: base)
            let destination = destinationBase.appendingPathComponent("plan-\(UUID().uuidString).json")
            try manifest.write(to: destination, excluding: [])
            let restored = try EntitlementBatchManifest.read(destination)
            XCTAssertEqual(try restored.data(), try manifest.data())
            let restoredPair = try XCTUnwrap(restored.makePairs().first)
            let expectedPrevious = destinationBase.appendingPathComponent("Previous.app")
            let expectedCurrent = destinationBase.appendingPathComponent("Current.app")
            XCTAssertEqual(Array(restoredPair.previous.path.utf8), Array(expectedPrevious.path.utf8))
            XCTAssertEqual(Array(restoredPair.current.path.utf8), Array(expectedCurrent.path.utf8))
            let unrelated = base.appendingPathComponent("elsewhere")
            XCTAssertThrowsError(try EntitlementBatchManifest(pairs: [pair], relativeTo: unrelated)) { error in
                guard case EntitlementBatchManifestError.base = error else {
                    return XCTFail("Expected base, got \(error)")
                }
            }
            let wrongDestination = unrelated.appendingPathComponent("plan.json")
            XCTAssertThrowsError(try manifest.write(to: wrongDestination, excluding: [])) { error in
                guard case EntitlementBatchManifestError.base = error else {
                    return XCTFail("Expected base, got \(error)")
                }
            }
        }
    }

    func testStoreExportRefusesNestedAliasAndAcceptsSiblingInBothDirections() async throws {
        let (short, long) = try aliases()
        for (base, alternate) in [(short, long), (long, short)] {
            let name = "store-" + UUID().uuidString
            let store = InspectionProjectStore(root: base.appendingPathComponent(name))
            let project = try await store.create(name: "Alias export")
            let nested = alternate.appendingPathComponent(name).appendingPathComponent("nested.airsproject")
            do {
                try await store.exportPortableProject(project.id, to: nested)
                XCTFail("Nested export must be refused")
            } catch {
                let refused = try XCTUnwrap(error as? AIRSCore.ReportError, "Expected a report error, got \(error)")
                guard case .invalidContents(let message) = refused else {
                    XCTFail("Expected invalidContents, got \(error)"); continue
                }
                XCTAssertEqual(message, "Export outside the source project store.")
            }
            XCTAssertFalse(FileManager.default.fileExists(atPath: nested.path))
            let outside = alternate.appendingPathComponent("export-\(UUID().uuidString).airsproject")
            try await store.exportPortableProject(project.id, to: outside)
            XCTAssertEqual(try PortableProjectReader.prepare(at: outside).project.id, project.id)
        }
    }

    func testPortableReaderRefusesNestedAliasAndAcceptsSiblingInBothDirections() async throws {
        let (short, long) = try aliases()
        for (base, alternate) in [(short, long), (long, short)] {
            let name = "package-" + UUID().uuidString
            let package = base.appendingPathComponent(name)
            let project = InspectionProject(name: "Alias reconstruction")
            try PortableProjectWriter.write(project: project, metadata: project.data(), evidence: [:], to: package)
            let admitted = try PortableProjectReader.prepare(at: package)
            let nested = alternate.appendingPathComponent(name).appendingPathComponent("recipient")
            do {
                _ = try await PortableProjectReader.reconstruct(admitted, to: nested)
                XCTFail("Nested reconstruction must be refused")
            } catch {
                XCTAssertEqual(error as? InspectionArchiveError, .invalid)
            }
            XCTAssertFalse(FileManager.default.fileExists(atPath: nested.path))
            let outside = alternate.appendingPathComponent("recipient-" + UUID().uuidString)
            let store = try await PortableProjectReader.reconstruct(admitted, to: outside)
            let restored = try await store.load(project.id)
            XCTAssertEqual(restored.id, project.id)
        }
    }
}
