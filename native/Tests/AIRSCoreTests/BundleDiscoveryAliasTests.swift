import Darwin
import Foundation
import XCTest
@testable import AIRSCore

final class BundleDiscoveryAliasTests: XCTestCase {
    func testBothDiscoverySpellingsValidateEitherInputAndRejectChangedBytes() throws {
        let short = FileManager.default.temporaryDirectory.appendingPathComponent("airs-alias-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: short, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: short) }
        let pointer = try XCTUnwrap(realpath(short.path, nil)); defer { free(pointer) }
        let long = URL(fileURLWithPath: String(cString: pointer), isDirectory: true)
        try XCTSkipIf(long.path == short.path, "temporary folder has no aliased ancestor here")
        let app = short.appendingPathComponent("Owned.app")
        let alternateApp = long.appendingPathComponent("Owned.app")
        let directory = app.appendingPathComponent("Contents/MacOS")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        let plist = try PropertyListSerialization.data(fromPropertyList: ["CFBundleExecutable": "Main"], format: .xml, options: 0)
        try plist.write(to: app.appendingPathComponent("Contents/Info.plist"))
        let checkout = URL(fileURLWithPath: #filePath).deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let fixture = checkout.appendingPathComponent("fixtures/generated/before.macho")
        let image = directory.appendingPathComponent("Main")
        try FileManager.default.copyItem(at: fixture, to: image)
        let first = try BundleDiscovery().discover(app)
        let second = try BundleDiscovery().discover(alternateApp)
        XCTAssertEqual(first.entries.filter(\.selectable).count, 1)
        XCTAssertEqual(second.entries.filter(\.selectable).count, 1)
        let firstProvenance = try XCTUnwrap(first.entries.first(where: \.selectable)?.provenance)
        let secondProvenance = try XCTUnwrap(second.entries.first(where: \.selectable)?.provenance)
        let inputs = [image, alternateApp.appendingPathComponent("Contents/MacOS/Main")]
        for provenance in [firstProvenance, secondProvenance] {
            for input in inputs {
                XCTAssertNoThrow(try BundleDiscovery.validate(provenance, input: input))
            }
        }
        try Data("Changed image bytes".utf8).write(to: image)
        for provenance in [firstProvenance, secondProvenance] {
            for input in inputs {
                XCTAssertThrowsError(try BundleDiscovery.validate(provenance, input: input))
            }
        }
    }
}
