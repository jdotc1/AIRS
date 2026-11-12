import Foundation
import XCTest
@testable import AIRSCore

final class GeneratorVersionAdmissionTests: XCTestCase {
    func testEarlierAndCurrentGeneratorVersionsRemainAdmissible() throws {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "cls-v47-32-mismatch",
                                                  withExtension: "json", subdirectory: "Fixtures"))
        let stored = try String(contentsOf: url, encoding: .utf8)
        let earlier = try AuditReport.decode(Data(stored.utf8))
        XCTAssertEqual(earlier.generator.version, "0.3.3")
        let updated = stored.replacingOccurrences(of: "\"version\": \"0.3.3\"",
                                                  with: "\"version\": \"0.4.0\"")
        let current = try AuditReport.decode(Data(updated.utf8))
        XCTAssertEqual(current.generator.version, "0.4.0")
        XCTAssertEqual(current.generator.analysisModelVersion, earlier.generator.analysisModelVersion)
        XCTAssertEqual(current.summary.functionCount, earlier.summary.functionCount)
    }
}
