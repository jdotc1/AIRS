import Foundation
import XCTest
@testable import AIRSCore

final class ProducerCoverageBridgeTests: XCTestCase {
    private struct Controls: Decodable {
        let formatVersion: Int
        let controls: [Control]
    }
    private struct Control: Decodable {
        let name: String
        let baselineJSON: String
        let currentJSON: String
        let comparisonJSON: String
        let expectedBases: [String]
        let expectedRows: Int
        let expectedBodyStatus: Bool
    }
    private func control(_ name: String) throws -> Control {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "producer-coverage-controls-v1", withExtension: "json", subdirectory: "Fixtures"))
        let fixture = try JSONDecoder().decode(Controls.self, from: Data(contentsOf: url))
        XCTAssertEqual(fixture.formatVersion, 1); XCTAssertEqual(fixture.controls.count, 8)
        return try XCTUnwrap(fixture.controls.first { $0.name == name })
    }
    private func run(_ control: Control, output: Data? = nil) async throws -> BatchComparisonResult {
        let before = Data(control.baselineJSON.utf8), after = Data(control.currentJSON.utf8)
        let payload = output ?? Data(control.comparisonJSON.utf8)
        let baseline = RetainedReport(data: before, report: try AuditReport.decode(before), provenance: LibraryProvenance(sourceLabel: "Owned synthetic control"))
        let current = RetainedReport(data: after, report: try AuditReport.decode(after), provenance: LibraryProvenance(sourceLabel: "Owned synthetic control"))
        func item(_ name: String, _ report: RetainedReport) -> ImageBatchItem {
            ImageBatchItem(id: UUID(), input: URL(fileURLWithPath: "/owned/" + name), status: .completed,
                message: "Synthetic saved report", retainedReportID: UUID(), image: report.report.image,
                summary: report.report.summary, model: report.report.generator.analysisModelVersion)
        }
        let old = item("baseline", baseline), new = item("current", current)
        let plan = try BatchComparisonPlan(baseline: ImageBatchSnapshot(id: UUID(), items: [old], settled: true),
                                           current: ImageBatchSnapshot(id: UUID(), items: [new], settled: true))
        return try await BatchComparisonRunner(requireSavedReportCoverage: true).run(plan: plan,
            pairs: [BatchImagePair(baselineID: old.id, currentID: new.id)],
            load: { id in id == old.retainedReportID ? baseline : current }, compare: { _, _ in payload })
    }
    private func accepted(_ name: String) async throws {
        let control = try control(name), result = try await run(control)
        XCTAssertTrue(result.settled); XCTAssertFalse(result.cancelled)
        XCTAssertEqual(result.rows[0].state, "compared")
        let report = try XCTUnwrap(result.rows[0].comparison)
        XCTAssertEqual(report.changes.count, control.expectedRows)
        XCTAssertEqual(Set(report.changes.map(\.matchBasis)), Set(control.expectedBases))
        XCTAssertEqual(report.comparison.exactBodyCandidates, control.expectedBodyStatus)
        XCTAssertEqual(result.rows[0].comparisonData, Data(control.comparisonJSON.utf8))
    }
    func testProducerDefaultOutputIsCovered() async throws { try await accepted("default-disabled") }
    func testProducerBodyOutputIsCovered() async throws { try await accepted("body-enabled") }
    func testProducerManualOutputIsCovered() async throws { try await accepted("manual-disabled") }
    func testProducerManualAndBodyOutputIsCovered() async throws { try await accepted("manual-body-enabled") }
    func testProducerSameImageDisabledOutputIsCovered() async throws { try await accepted("same-image-disabled") }
    func testProducerSameImageEnabledOutputIsCovered() async throws { try await accepted("same-image-enabled") }
    func testProducerUnicodeGroupsRemainDistinct() async throws { try await accepted("unicode-symbols") }
    func testProducerDuplicateBodyBlockersRemainUnmatched() async throws { try await accepted("duplicate-body-blockers") }
    func testOmittedBodyRowRefusesDespiteConsistentSummary() async throws {
        let control = try control("body-enabled")
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(control.comparisonJSON.utf8)) as? [String: Any])
        object["changes"] = []
        object["summary"] = ["matched_count": 0, "changed_count": 0, "unchanged_count": 0, "added_count": 0, "removed_count": 0, "ambiguous_count": 0]
        let bytes = try JSONSerialization.data(withJSONObject: object)
        _ = try ComparisonReport.decode(bytes)
        let result = try await run(control, output: bytes)
        XCTAssertEqual(result.rows[0].state, "unavailable")
        XCTAssertNil(result.rows[0].comparison); XCTAssertNil(result.rows[0].comparisonData)
    }
    func testWellFormedForeignManualSourceRefuses() async throws {
        let control = try control("manual-disabled"), foreign = "airsf-" + String(repeating: "f", count: 64)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(control.comparisonJSON.utf8)) as? [String: Any])
        var context = try XCTUnwrap(object["comparison"] as? [String: Any])
        var pairs = try XCTUnwrap(context["manual_pairs"] as? [[String: String]])
        let currentID = try XCTUnwrap(pairs[0]["current_id"])
        pairs[0]["baseline_id"] = foreign; context["manual_pairs"] = pairs; object["comparison"] = context
        var rows = try XCTUnwrap(object["changes"] as? [[String: Any]])
        rows[0]["baseline_id"] = foreign; rows[0]["key"] = "manual:" + foreign + ":" + currentID; object["changes"] = rows
        let bytes = try JSONSerialization.data(withJSONObject: object)
        _ = try ComparisonReport.decode(bytes)
        let result = try await run(control, output: bytes)
        XCTAssertEqual(result.rows[0].state, "unavailable")
        XCTAssertNil(result.rows[0].comparison); XCTAssertNil(result.rows[0].comparisonData)
    }
}
