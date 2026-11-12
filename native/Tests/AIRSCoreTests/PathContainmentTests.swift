import Darwin
import Foundation
import XCTest
import AIRSCore

final class PathContainmentTests: XCTestCase {
    private func aliases() throws -> (URL, URL) {
        let short = FileManager.default.temporaryDirectory.appendingPathComponent("airs-alias-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: short, withIntermediateDirectories: true)
        addTeardownBlock { try? FileManager.default.removeItem(at: short) }
        let pointer = try XCTUnwrap(realpath(short.path, nil)); defer { free(pointer) }
        let long = URL(fileURLWithPath: String(cString: pointer), isDirectory: true)
        try XCTSkipIf(long.path == short.path, "temporary folder has no aliased ancestor here")
        return (short, long)
    }

    func testExistingAndMissingLeavesAcrossBothAliasDirections() throws {
        let (short, long) = try aliases()
        let root = short.appendingPathComponent("store", isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let otherRoot = long.appendingPathComponent("store", isDirectory: true)
        XCTAssertTrue(PathContainment.sameLocation(root, otherRoot))
        XCTAssertFalse(PathContainment.isInside(root, otherRoot))
        XCTAssertTrue(PathContainment.isSameOrInside(root, otherRoot))
        for (base, alternate) in [(short, long), (long, short)] {
            let protected = base.appendingPathComponent("store")
            let missing = alternate.appendingPathComponent("store/new.json")
            XCTAssertTrue(PathContainment.isInside(missing, protected))
            XCTAssertTrue(PathContainment.isSameOrInside(missing, protected))
            XCTAssertFalse(FileManager.default.fileExists(atPath: missing.path))
            let existing = alternate.appendingPathComponent("store/existing")
            try Data("owned".utf8).write(to: existing)
            XCTAssertTrue(PathContainment.isInside(existing, protected))
            XCTAssertFalse(PathContainment.sameLocation(missing, existing))
            let sibling = alternate.appendingPathComponent("store2/x")
            XCTAssertFalse(PathContainment.isInside(sibling, protected))
            XCTAssertFalse(PathContainment.isSameOrInside(sibling, protected))
        }
    }

    func testSymbolicParentResolvesIntoRoot() throws {
        let (short, long) = try aliases()
        let root = short.appendingPathComponent("store")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        let link = short.appendingPathComponent("link")
        try FileManager.default.createSymbolicLink(at: link, withDestinationURL: root)
        let candidate = long.appendingPathComponent("link/new.json")
        XCTAssertTrue(PathContainment.isInside(candidate, root))
        XCTAssertEqual(PathContainment.comparisonKey(candidate),
                       PathContainment.comparisonKey(root.appendingPathComponent("new.json")))
    }

    func testMissingRootAndParentComponentsUseComparisonKeys() throws {
        let (short, long) = try aliases()
        let root = short.appendingPathComponent("absent")
        let alternate = long.appendingPathComponent("absent")
        XCTAssertFalse(FileManager.default.fileExists(atPath: root.path))
        XCTAssertTrue(PathContainment.sameLocation(root, alternate))
        XCTAssertTrue(PathContainment.isInside(alternate.appendingPathComponent("child"), root))
        XCTAssertFalse(PathContainment.isInside(long.appendingPathComponent("absent2/child"), root))
        let a = short.appendingPathComponent("a")
        try FileManager.default.createDirectory(at: a, withIntermediateDirectories: true)
        let tail = long.appendingPathComponent("a/missing/../b")
        XCTAssertEqual(PathContainment.comparisonKey(tail),
                       PathContainment.comparisonKey(a.appendingPathComponent("b")))
        let physicalParent = long.appendingPathComponent("a/../b")
        XCTAssertEqual(PathContainment.comparisonKey(physicalParent),
                       PathContainment.comparisonKey(short.appendingPathComponent("b")))
    }

    func testNonFileURLsHaveNoKeyOrContainment() throws {
        let short = FileManager.default.temporaryDirectory
        let remote = try XCTUnwrap(URL(string: "https://example.invalid/store/child"))
        XCTAssertNil(PathContainment.comparisonKey(remote))
        XCTAssertFalse(PathContainment.sameLocation(remote, remote))
        XCTAssertFalse(PathContainment.sameLocation(remote, short))
        XCTAssertFalse(PathContainment.isInside(remote, short))
        XCTAssertFalse(PathContainment.isInside(short, remote))
        XCTAssertFalse(PathContainment.isSameOrInside(remote, short))
        XCTAssertFalse(PathContainment.isSameOrInside(short, remote))
    }
}
