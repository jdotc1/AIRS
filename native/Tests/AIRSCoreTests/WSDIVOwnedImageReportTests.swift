import Foundation
import XCTest
@testable import AIRSCore

final class WSDIVOwnedImageReportTests: XCTestCase {
    private func report(_ variant: String) throws -> AuditReport {
        let url = try XCTUnwrap(Bundle.module.url(
            forResource: "w-sdiv-owned-v43-\(variant)", withExtension: "json", subdirectory: "Fixtures"))
        return try AuditReport.decode(Data(contentsOf: url))
    }

    func testCorrectRecoveryRetainsExactScopeAndOriginalPC() throws {
        let value = try report("correct")
        XCTAssertEqual(value.generator.analysisModelVersion, "arm64-bounded-w-udiv-v43")
        XCTAssertEqual(value.summary.functionCount, 2)
        XCTAssertEqual(value.summary.agreementCount, 2)
        let first = try XCTUnwrap(value.findings.first)
        XCTAssertEqual(first.function.boundarySource, "lc_function_starts")
        XCTAssertEqual(first.verdict, .agreement)
        XCTAssertEqual(first.scope, "synchronous_call_sites")
        XCTAssertEqual(first.checkedPCs, ["0x10000101c"])
    }

    func testMismatchKeepsZeroExtendedSignedEvidence() throws {
        let value = try report("mismatch")
        XCTAssertEqual(value.summary.functionCount, 2)
        XCTAssertEqual(value.summary.inconsistencyCount, 1)
        let first = try XCTUnwrap(value.findings.first)
        XCTAssertEqual(first.verdict, .inconsistency)
        XCTAssertEqual(first.checkedPCs, ["0x10000101c"])
        XCTAssertTrue(first.evidence.contains {
            $0.expected == .string("original x19") && $0.observed == .string("constant 0xfffffffe")
        })
    }

    func testUnknownRecoveryDoesNotAcquireSupportedCheckedPCs() throws {
        let value = try report("unknown")
        XCTAssertEqual(value.summary.functionCount, 2)
        XCTAssertEqual(value.summary.unresolvedCount, 1)
        XCTAssertEqual(value.summary.inconsistencyCount, 0)
        let first = try XCTUnwrap(value.findings.first)
        XCTAssertEqual(first.verdict, .unresolved)
        XCTAssertTrue(first.reasonCodes.contains("unknown_recovery_value"))
        XCTAssertEqual(first.checkedPCs, [])
        XCTAssertEqual(value.findings.last?.verdict, .agreement)
    }
}
