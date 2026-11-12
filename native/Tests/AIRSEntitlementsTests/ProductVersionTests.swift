import Foundation
import XCTest
import AIRSCore
@testable import AIRSEntitlements

final class ProductVersionTests: XCTestCase {
    private func captured() throws -> CodeSignatureEvidenceDocument {
        func word(_ value: UInt32, little: Bool = true) -> Data {
            Data((0..<4).map { UInt8(truncatingIfNeeded: value >> ((little ? $0 : 3 - $0) * 8)) })
        }
        var raw = Data()
        for value: UInt32 in [0xfade0cc0, 31, 1, 5, 20, 0xfade7171, 11] { raw += word(value, little: false) }
        raw += Data([0xff, 0, 0x61])
        var source = Data([0xcf, 0xfa, 0xed, 0xfe])
        for value: UInt32 in [0x0100000c, 0x80000002, 2, 1, 16, 0, 0, 0x1d, 16, 128, 31] { source += word(value) }
        source += Data(repeating: 0, count: 128 - source.count); source += raw
        let base = ProcessInfo.processInfo.environment["AIRS_TEST_OUTPUT_ROOT"].map { URL(fileURLWithPath: $0, isDirectory: true) } ?? FileManager.default.temporaryDirectory
        let root = base.appendingPathComponent("AIRS-signature-document-\(UUID())/Owned.app")
        defer { try? FileManager.default.removeItem(at: root.deletingLastPathComponent()) }
        let image = root.appendingPathComponent("Contents/MacOS/Main")
        try FileManager.default.createDirectory(at: image.deletingLastPathComponent(), withIntermediateDirectories: true)
        try source.write(to: image)
        try PropertyListSerialization.data(fromPropertyList: ["CFBundleExecutable": "Main"], format: .xml, options: 0)
            .write(to: root.appendingPathComponent("Contents/Info.plist"))
        let unit = try XCTUnwrap(BundleDiscovery().discover(root).entries.first { $0.relativePath == "Contents/MacOS/Main" }?.provenance)
        return try CodeSignatureEvidenceDocument.capture(unit: unit, componentID: UUID())
    }

    func testSignatureCaptureDefaultsToProductVersion() throws {
        XCTAssertEqual(try captured().producerVersion, AIRSProductVersion.current)
    }
}
