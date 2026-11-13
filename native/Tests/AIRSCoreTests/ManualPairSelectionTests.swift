import Foundation
import XCTest
@testable import AIRSCore

/// Small owned saved-report fixtures; no inspected image or engine analysis.
enum ManualPairRequestFixtures {
    static func id(_ digit: String) -> String { "airsf-" + String(repeating: digit, count: 64) }

    static func source(current: Bool, digest: String? = nil, subtype: Int = 0) throws -> Data {
        let identifiers = current ? [id("c"), id("d")] : [id("a"), id("b")]
        let findings: [[String: Any]] = identifiers.enumerated().map { index, id in
            let start = 0x1000 + index * 0x20
            return ["id": id, "function": ["name": "\(current ? "after" : "before")\(index)",
                "address": "0x" + String(start, radix: 16), "end_address": "0x" + String(start + 16, radix: 16),
                "image_offset": "0x" + String(index * 0x20, radix: 16), "size": 16, "boundary_source": "lc_function_starts"],
                "verdict": "agreement", "coverage": "compact", "mode": "frame", "scope": "synchronous_call_sites",
                "encoding": "0x04000000", "checked_pcs": ["0x" + String(start + 8, radix: 16)], "instruction_count": 4,
                "reason_codes": ["supported_model_agreement"], "evidence": [], "limitations": []]
        }
        return try JSONSerialization.data(withJSONObject: [
            "schema_version": 1, "report_kind": "airs.audit",
            "generator": ["name": "AIRS", "version": "0.3.3", "analysis_model_version": AnalysisModels.current],
            "image": ["display_name": current ? "after" : "before", "architecture": "arm64", "file_type": "dylib",
                "preferred_base": "0x1000", "container_sha256": String(repeating: "0", count: 64),
                "slice_sha256": String(repeating: digest ?? (current ? "2" : "1"), count: 64),
                "cpu_subtype": subtype, "slice_offset": 0, "slice_size": 48],
            "summary": ["function_count": 2, "agreement_count": 2, "inconsistency_count": 0, "unresolved_count": 0,
                "metadata_entry_count": 2, "checked_pc_count": 2],
            "issues": [], "limitations": ["Synthetic saved-report review fixture."],
            "metadata_ranges": [
                ["start": "0x1000", "end": "0x1010", "encoding": "0x04000000", "mode": "frame"],
                ["start": "0x1020", "end": "0x1030", "encoding": "0x04000000", "mode": "frame"]],
            "findings": findings])
    }

    static func pairs(swapped: Bool = false) throws -> [ComparisonManualPair] {
        [try ComparisonManualPair(baselineID: id("a"), currentID: id(swapped ? "d" : "c")),
         try ComparisonManualPair(baselineID: id("b"), currentID: id(swapped ? "c" : "d"))]
    }

    static func selection(swapped: Bool = false) throws -> ManualPairSelection {
        try ManualPairSelection(pairs(swapped: swapped), baseline: AuditReport.decode(source(current: false)),
                                current: AuditReport.decode(source(current: true)))
    }

    static func comparison(swapped: Bool = false) throws -> Data {
        let before = try AuditReport.decode(source(current: false)), after = try AuditReport.decode(source(current: true))
        let pairs = try pairs(swapped: swapped)
        let rows: [[String: Any]] = pairs.map { pair in
            ["key": "manual:\(pair.baselineID):\(pair.currentID)", "match_basis": "manual_review",
             "function_name": pair.currentID == id("c") ? "after0" : "after1", "change": "unchanged",
             "baseline_id": pair.baselineID, "current_id": pair.currentID,
             "before_verdict": "agreement", "after_verdict": "agreement",
             "before_scope": "synchronous_call_sites", "after_scope": "synchronous_call_sites", "notes": []]
        }
        func image(_ source: AuditReport) -> [String: Any] {
            ["display_name": source.image.displayName, "slice_sha256": source.image.sliceSHA256, "architecture": "arm64"]
        }
        return try JSONSerialization.data(withJSONObject: [
            "schema_version": 1, "report_kind": "airs.diff",
            "comparison": ["baseline_image": image(before), "current_image": image(after), "same_image": false,
                "model_compatible": true, "matching_policy": "manual_then_unique_symbol", "exact_body_candidates": false,
                "analysis_configuration_changed": false,
                "manual_pairs": pairs.map { ["baseline_id": $0.baselineID, "current_id": $0.currentID] }],
            "summary": ["matched_count": 2, "changed_count": 0, "unchanged_count": 2, "added_count": 0, "removed_count": 0, "ambiguous_count": 0],
            "changes": rows, "limitations": ["User-selected review does not prove source-function identity."]])
    }
}

final class ManualPairSelectionTests: XCTestCase {
    func testManualPairEmptyRequestRefusesUnrequestedManualOutput() throws {
        XCTAssertThrowsError(try ManualPairSelection.empty.decodeComparison(ManualPairRequestFixtures.comparison(),
            baselineData: ManualPairRequestFixtures.source(current: false), currentData: ManualPairRequestFixtures.source(current: true))) {
            XCTAssertTrue($0.localizedDescription.contains("not submitted"))
        }
    }

    func testManualPairRequestCanonicalizesAndDeduplicates() throws {
        let pairs = try ManualPairRequestFixtures.pairs()
        let before = try AuditReport.decode(ManualPairRequestFixtures.source(current: false))
        let after = try AuditReport.decode(ManualPairRequestFixtures.source(current: true))
        let request = try ManualPairSelection([pairs[1], pairs[0], pairs[1]], baseline: before, current: after)
        XCTAssertEqual(request.pairs, pairs)
        XCTAssertEqual(ManualPairSelection.empty.arguments, [])
    }

    func testManualPairRequestRejectsMalformedIDs() throws {
        let valid = ManualPairRequestFixtures.id("a")
        for bad in ["", "airsf-a", ManualPairRequestFixtures.id("A"), valid + "0", "x" + valid, valid + "\n"] {
            XCTAssertThrowsError(try ComparisonManualPair(baselineID: bad, currentID: valid))
            XCTAssertThrowsError(try ComparisonManualPair(baselineID: valid, currentID: bad))
        }
    }

    func testManualPairRequestNamesConflictingEndpointsAndRefusesUnknownIDs() throws {
        let pairs = try ManualPairRequestFixtures.pairs()
        let before = try AuditReport.decode(ManualPairRequestFixtures.source(current: false))
        let after = try AuditReport.decode(ManualPairRequestFixtures.source(current: true))
        let conflict = try ComparisonManualPair(baselineID: pairs[0].baselineID, currentID: pairs[1].currentID)
        for (entries, endpoint) in [([pairs[0], conflict], pairs[0].baselineID), ([pairs[1], conflict], pairs[1].currentID)] {
            XCTAssertThrowsError(try ManualPairSelection(entries, baseline: before, current: after)) {
                XCTAssertTrue($0.localizedDescription.contains(endpoint))
            }
        }
        let unknown = try ComparisonManualPair(baselineID: ManualPairRequestFixtures.id("e"), currentID: pairs[0].currentID)
        XCTAssertThrowsError(try ManualPairSelection([unknown], baseline: before, current: after))
    }

    func testManualPairRequestRefusesSameSliceAndArchitectureRegardlessOfSubtype() throws {
        let before = try AuditReport.decode(ManualPairRequestFixtures.source(current: false))
        let after = try AuditReport.decode(ManualPairRequestFixtures.source(current: true, digest: "1", subtype: 1))
        XCTAssertThrowsError(try ManualPairSelection(ManualPairRequestFixtures.pairs(), baseline: before, current: after))
        XCTAssertNoThrow(try ManualPairSelection([], baseline: before, current: after))
    }

    func testManualPairRequestCountsRawDuplicatesBeforeDeduplication() throws {
        let pair = try XCTUnwrap(ManualPairRequestFixtures.pairs().first)
        let before = try AuditReport.decode(ManualPairRequestFixtures.source(current: false))
        let after = try AuditReport.decode(ManualPairRequestFixtures.source(current: true))
        XCTAssertThrowsError(try ManualPairSelection(Array(repeating: pair, count: 50_001), baseline: before, current: after))
        XCTAssertEqual(try ManualPairSelection(Array(repeating: pair, count: 50_000), baseline: before, current: after).pairs, [pair])
    }

    func testManualPairArgumentBudgetCountsUTF8EnvironmentAndLauncherOverhead() throws {
        let args = try ManualPairRequestFixtures.selection().arguments + ["path with spaces/é"]
        let executable = "/owned/python", environment = ["LANG": "é"]
        let strings = [executable] + args + ["LANG=é"]
        let exactLimit = 16_384 + strings.reduce(0) { $0 + $1.utf8.count + 1 + MemoryLayout<UnsafeRawPointer>.size }
        XCTAssertNoThrow(try ReviewArgumentBudget.validate(executable: executable, arguments: args, environment: environment, limit: exactLimit))
        XCTAssertThrowsError(try ReviewArgumentBudget.validate(executable: executable, arguments: args, environment: environment, limit: exactLimit - 1)) {
            XCTAssertTrue($0.localizedDescription.contains("Remove pairs"))
        }
        XCTAssertThrowsError(try ReviewArgumentBudget.validate(executable: executable, arguments: [], environment: [:], limit: -1))
    }

    func testManualPairComposedAdmissionRejectsValidButDifferentReturnedSelection() throws {
        let before = try ManualPairRequestFixtures.source(current: false), after = try ManualPairRequestFixtures.source(current: true)
        let different = try ManualPairRequestFixtures.comparison(swapped: true)
        // Establish that this is valid source-bound output for a different request.
        let decoded = try ComparisonReport.decodeWithSavedReportCoverage(different, baselineData: before, currentData: after)
        XCTAssertEqual(decoded.comparison.manualPairs, try ManualPairRequestFixtures.pairs(swapped: true))
        XCTAssertThrowsError(try ManualPairRequestFixtures.selection().decodeComparison(different, baselineData: before, currentData: after)) {
            XCTAssertTrue($0.localizedDescription.contains("different review-pair selection"))
        }
    }

    func testManualPairComposedAdmissionAcceptsMatchingUnchangedRowsAndRefusesWrongSource() throws {
        let before = try ManualPairRequestFixtures.source(current: false), after = try ManualPairRequestFixtures.source(current: true)
        let request = try ManualPairRequestFixtures.selection(), data = try ManualPairRequestFixtures.comparison()
        let result = try request.decodeComparison(data, baselineData: before, currentData: after)
        XCTAssertEqual(result.changes.map(\.change), ["unchanged", "unchanged"])
        XCTAssertThrowsError(try request.decodeComparison(data, baselineData: after, currentData: before))
    }
}
