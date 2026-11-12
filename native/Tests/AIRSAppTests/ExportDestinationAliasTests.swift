import Darwin
import Foundation
import XCTest
import AIRSCore
@testable import AIRSApp

@MainActor private final class ExportAliasRecents: WorkspaceRecentsRecording {
    var recentDocumentURLs: [URL] = []
    func noteRecentDocument(_ url: URL) {}
    func clearRecentDocuments() {}
}

final class ExportDestinationAliasTests: XCTestCase {
    @MainActor
    func testProtectedAppRejectsNestedAliasAndAcceptsAdjacentJSONInBothDirections() throws {
        let short = FileManager.default.temporaryDirectory.appendingPathComponent("airs-alias-\(UUID().uuidString)", isDirectory: true)
        try FileManager.default.createDirectory(at: short, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: short) }
        let pointer = try XCTUnwrap(realpath(short.path, nil)); defer { free(pointer) }
        let long = URL(fileURLWithPath: String(cString: pointer), isDirectory: true)
        try XCTSkipIf(long.path == short.path, "temporary folder has no aliased ancestor here")
        try FileManager.default.createDirectory(at: short.appendingPathComponent("Owned.app/Contents"), withIntermediateDirectories: true)
        let library = ReportLibrary(root: short.appendingPathComponent("library"))
        let history = BatchHistory(root: short.appendingPathComponent("history"))
        let workspace = AuditWorkspace(library: library, recents: ExportAliasRecents(),
            batchAudit: { _ in throw CocoaError(.fileReadUnknown) }, batchHistory: history)
        for (base, alternate) in [(short, long), (long, short)] {
            let app = base.appendingPathComponent("Owned.app")
            let nested = alternate.appendingPathComponent("Owned.app/Contents/export.json")
            XCTAssertThrowsError(try workspace.validateExportDestination(nested, protectedInputs: [app])) { error in
                guard case ReportError.invalidContents(let message) = error else {
                    return XCTFail("Expected invalidContents, got \(error)")
                }
                XCTAssertEqual(message, "Choose a JSON destination outside the inspected images and attached debug artifacts.")
            }
            let outside = alternate.appendingPathComponent("export.json")
            XCTAssertNoThrow(try workspace.validateExportDestination(outside, protectedInputs: [app]))
            XCTAssertFalse(FileManager.default.fileExists(atPath: nested.path))
        }
    }
}
