import Foundation
import XCTest
@testable import AIRSCore

final class ProducerObservationBridgeTests: XCTestCase {
    private struct Controls: Decodable {
        let formatVersion: Int
        let controls: [Control]
    }
    private struct Control: Decodable {
        let name: String
        let baselineJSON: String
        let currentJSON: String
        let comparisonJSON: String
        let expectedChange: String
    }
    private func control(_ name: String) throws -> Control {
        let url = try XCTUnwrap(Bundle.module.url(forResource: "producer-observation-controls-v1", withExtension: "json", subdirectory: "Fixtures"))
        let fixture = try JSONDecoder().decode(Controls.self, from: Data(contentsOf: url))
        XCTAssertEqual(fixture.formatVersion, 1); XCTAssertEqual(fixture.controls.count, 7)
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
        XCTAssertEqual(report.changes.count, 1)
        XCTAssertEqual(report.changes[0].matchBasis, "unique_symbol")
        XCTAssertEqual(report.changes[0].change, control.expectedChange)
        XCTAssertEqual(report.summary.changedCount, control.expectedChange == "changed" ? 1 : 0)
        XCTAssertEqual(report.summary.unchangedCount, control.expectedChange == "unchanged" ? 1 : 0)
        XCTAssertEqual(report.comparison.exactBodyCandidates, false)
        XCTAssertEqual(result.rows[0].comparisonData, Data(control.comparisonJSON.utf8))
    }
    func testProducerReasonReorderingRemainsUnchanged() async throws { try await accepted("reason-order") }
    func testProducerReasonMultiplicityIsChanged() async throws { try await accepted("reason-multiplicity") }
    func testProducerVMRelocationPreservesRelativeEvidence() async throws { try await accepted("vm-relocation") }
    func testProducerRelativeCheckedPCChangeIsChanged() async throws { try await accepted("checked-pc-offset") }
    func testProducerCheckedPCOrderChangeIsChanged() async throws { try await accepted("checked-pc-order") }
    func testProducerByteDistinctEvidenceIsChanged() async throws { try await accepted("evidence-bytes") }
    func testProducerEvidenceMessageOnlyRemainsUnchanged() async throws { try await accepted("message-only") }
    private func refusedLabel(_ name: String, forged: String) async throws {
        let control = try control(name)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(control.comparisonJSON.utf8)) as? [String: Any])
        var rows = try XCTUnwrap(object["changes"] as? [[String: Any]])
        rows[0]["change"] = forged; object["changes"] = rows
        var summary = try XCTUnwrap(object["summary"] as? [String: Any])
        summary["changed_count"] = forged == "changed" ? 1 : 0
        summary["unchanged_count"] = forged == "unchanged" ? 1 : 0; object["summary"] = summary
        let bytes = try JSONSerialization.data(withJSONObject: object)
        _ = try ComparisonReport.decode(bytes)
        let result = try await run(control, output: bytes)
        XCTAssertEqual(result.rows[0].state, "unavailable")
        XCTAssertNil(result.rows[0].comparison); XCTAssertNil(result.rows[0].comparisonData)
    }
    func testForgedUnchangedLabelRefusesWithConsistentCounts() async throws {
        try await refusedLabel("reason-multiplicity", forged: "unchanged")
    }
    func testForgedChangeLabelRefusesForRelocatedEquivalentEvidence() async throws {
        try await refusedLabel("vm-relocation", forged: "changed")
    }
}
