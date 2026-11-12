import Foundation
import XCTest
@testable import AIRSCore

final class AnalysisModelRegistryTests: XCTestCase {
    func testExactHistoricalPolicySets() {
        XCTAssertEqual(AnalysisModels.cfg.count, 50)
        XCTAssertEqual(AnalysisModels.known.subtracting(AnalysisModels.cfg), ["arm64-linear-v1", "arm64-linear-dwarf-v2"])
        XCTAssertEqual(AnalysisModels.evaluatedCFI.subtracting(AnalysisModels.cfg), ["arm64-linear-dwarf-v2"])
        let unknownLabels: [String] = [
            "arm64-bounded-extract-class-v51-future",
            "arm64-bounded-test-bit-branch-v50-future",
            "arm64-bounded-test-bit-branch-v51",
            "ARM64-bounded-test-bit-branch-v50",
        ]
        for label in unknownLabels {
            XCTAssertFalse(AnalysisModels.known.contains(label))
        }
    }

    func testEveryCFGLabelRejectsCapabilitySubtypeAfterValidAdmission() throws {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "cls-v47-32-mismatch", withExtension: "json", subdirectory: "Fixtures"))
        let original = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: url)) as? [String: Any])
        for label in AnalysisModels.cfg {
            var wire = original
            var generator = try XCTUnwrap(wire["generator"] as? [String: Any])
            generator["analysis_model_version"] = label
            wire["generator"] = generator
            XCTAssertNoThrow(try AuditReport.decode(JSONSerialization.data(withJSONObject: wire)), label)
            var image = try XCTUnwrap(wire["image"] as? [String: Any])
            image["cpu_subtype"] = 0x80000000
            wire["image"] = image
            XCTAssertThrowsError(try AuditReport.decode(JSONSerialization.data(withJSONObject: wire)), label)
        }
    }
}
