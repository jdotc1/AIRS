import Foundation
import XCTest
@testable import AIRSCore

final class ModelAdmissionBoundaryTests: XCTestCase {
    private func wire(_ model: String, subtype: UInt32 = 0) throws -> [String: Any] {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "cls-v47-32-mismatch", withExtension: "json", subdirectory: "Fixtures"))
        var value = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        var generator = try XCTUnwrap(value["generator"] as? [String: Any])
        generator["analysis_model_version"] = model
        value["generator"] = generator
        var image = try XCTUnwrap(value["image"] as? [String: Any])
        image["cpu_subtype"] = subtype
        value["image"] = image
        return value
    }
    private func decode(_ value: [String: Any]) throws -> AuditReport {
        try AuditReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    func testHistoricalCompactSubtypePolicy() throws {
        for model in ["arm64-linear-v1", "arm64-linear-dwarf-v2"] {
            for subtype: UInt32 in [0x80000000, 0x80000001] {
                XCTAssertNoThrow(try decode(wire(model, subtype: subtype)), model)
            }
            XCTAssertThrowsError(try decode(wire(model, subtype: 0x80000002)), model)
        }
    }

    func testHistoricalEvaluatedCFIPolicy() throws {
        for model in ["arm64-linear-v1", "arm64-linear-dwarf-v2"] {
            for subtype: UInt32 in [0, 0x80000000] {
                var value = try wire(model, subtype: subtype)
                var findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
                findings[0]["mode"] = "dwarf"
                findings[0]["coverage"] = "dwarf_evaluated"
                findings[0]["scope"] = "synchronous_call_sites"
                findings[0]["encoding"] = "0x03000004"
                value["findings"] = findings
                if model == "arm64-linear-dwarf-v2" && subtype == 0 {
                    XCTAssertNoThrow(try decode(value))
                } else {
                    XCTAssertThrowsError(try decode(value), model)
                }
            }
        }
    }

    func testUnknownLabelsRetainGenericAdmissionAndStructuralChecks() throws {
        for model in ["arm64-bounded-cls-v48", "arm64-bounded-cls-v47-future", "ARM64-bounded-cls-v47"] {
            var value = try wire(model, subtype: 0x80000000)
            XCTAssertNoThrow(try decode(value), model)
            var findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
            findings[0]["checked_pcs"] = ["0xfffffffffffffff0"]
            value["findings"] = findings
            XCTAssertThrowsError(try decode(value), model)
        }
    }
}
