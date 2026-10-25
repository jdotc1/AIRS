import Foundation
import XCTest
@testable import AIRSCore

final class REV32ReportTests: XCTestCase {
    private func data(_ name: String) throws -> Data {
        let url = try XCTUnwrap(Bundle.module.url(forResource: name, withExtension: "json", subdirectory: "Fixtures"))
        return try Data(contentsOf: url)
    }
    private func object() throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: data("rev32-v46-mismatch")) as? [String: Any])
    }
    private func decode(_ value: [String: Any]) throws -> AuditReport {
        try AuditReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testConcreteResultPreservesOriginalScopeAndPC() throws {
        let value = try AuditReport.decode(data("rev32-v46-mismatch"))
        XCTAssertEqual(value.generator.analysisModelVersion, "arm64-bounded-rev32-v46")
        XCTAssertEqual(value.summary.functionCount, 2)
        XCTAssertEqual(value.summary.inconsistencyCount, 1)
        let first = try XCTUnwrap(value.findings.first)
        XCTAssertEqual(first.verdict, .inconsistency)
        XCTAssertEqual(first.scope, "synchronous_call_sites")
        XCTAssertEqual(first.checkedPCs, ["0x10000101c"])
        XCTAssertEqual(first.function.boundarySource, "lc_function_starts")
        XCTAssertTrue(first.evidence.contains {
            $0.expected == .string("original x19") && $0.observed == .string("constant 0xffffffffcbedffff")
        })
    }

    func testCorrectAndUnknownRecoveryRemainDistinct() throws {
        let correct = try AuditReport.decode(data("rev32-v46-correct"))
        XCTAssertEqual(correct.summary.agreementCount, 2)
        XCTAssertEqual(correct.findings.first?.checkedPCs, ["0x10000101c"])
        let unknown = try AuditReport.decode(data("rev32-v46-unknown"))
        XCTAssertEqual(unknown.summary.functionCount, 2)
        XCTAssertEqual(unknown.summary.unresolvedCount, 1)
        XCTAssertEqual(unknown.summary.inconsistencyCount, 0)
        let first = try XCTUnwrap(unknown.findings.first)
        XCTAssertEqual(first.verdict, .unresolved)
        XCTAssertTrue(first.reasonCodes.contains("unknown_recovery_value"))
        XCTAssertEqual(first.checkedPCs, [])
    }

    func testKnownModelAdmissionAndFutureLabelControl() throws {
        for fault in ["subtype", "boundary", "scope", "encoding"] {
            var wire = try object()
            var image = try XCTUnwrap(wire["image"] as? [String: Any])
            var findings = try XCTUnwrap(wire["findings"] as? [[String: Any]])
            switch fault {
            case "subtype": image["cpu_subtype"] = 0x80000000
            case "boundary":
                var function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
                function["boundary_source"] = "compact_unwind"
                findings[0]["function"] = function
            case "scope": findings[0]["scope"] = "modeled_leaf_body"
            default: findings[0]["encoding"] = "0x04000100"
            }
            wire["image"] = image; wire["findings"] = findings
            XCTAssertThrowsError(try decode(wire), fault)
        }
        var wire = try object()
        var image = try XCTUnwrap(wire["image"] as? [String: Any])
        image["cpu_subtype"] = 0x80000000; wire["image"] = image
        for model in ["arm64-bounded-rev16-v45", "arm64-bounded-rev-v44", "arm64-bounded-w-udiv-v43", "arm64-bounded-w-sdiv-v42", "arm64-bounded-rev32-v46-future"] {
            var generator = try XCTUnwrap(wire["generator"] as? [String: Any])
            generator["analysis_model_version"] = model; wire["generator"] = generator
            if model.hasSuffix("-future") { XCTAssertNoThrow(try decode(wire)) }
            else { XCTAssertThrowsError(try decode(wire)) }
        }
    }

    func testDwarfAdmissionStillRequiresEvaluatedCoverageAndEncoding() throws {
        var wire = try object()
        var findings = try XCTUnwrap(wire["findings"] as? [[String: Any]])
        findings[0]["mode"] = "dwarf"; findings[0]["coverage"] = "dwarf_evaluated"
        findings[0]["scope"] = "synchronous_call_sites"; findings[0]["encoding"] = "0x03000004"
        wire["findings"] = findings
        XCTAssertNoThrow(try decode(wire))
        findings[0]["coverage"] = "dwarf_reference"; wire["findings"] = findings
        XCTAssertThrowsError(try decode(wire))
        findings[0]["coverage"] = "dwarf_evaluated"; findings[0]["encoding"] = "0x02000000"
        wire["findings"] = findings
        XCTAssertThrowsError(try decode(wire))
    }
}
