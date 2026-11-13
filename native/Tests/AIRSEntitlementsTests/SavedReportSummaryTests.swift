import Foundation
import XCTest
import AIRSCore
@testable import AIRSEntitlements

/// Projects owned source fields only, with explicit expected counts asserted by tests.
private enum SummaryProjectionFixture {
    static func source() throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: CoverageInventoryTests().data("source.audit")) as? [String: Any])
    }
    static func bytes(_ value: [String: Any]) throws -> Data { try JSONSerialization.data(withJSONObject: value) }
    static func summary(_ source: [String: Any]) throws -> [String: Any] {
        let rows = try XCTUnwrap(source["findings"] as? [[String: Any]])
        let ranges = try XCTUnwrap(source["metadata_ranges"] as? [[String: Any]])
        let issues = try XCTUnwrap(source["issues"] as? [[String: Any]])
        func counts(_ values: [String]) -> [String: Int] { values.reduce(into: [:]) { $0[$1, default: 0] += 1 } }
        var identity = source.filter { ["schema_version", "report_kind", "generator", "image", "analysis_config"].contains($0.key) }
        identity["report_kind"] = "airs.audit"
        var reasons: [String: [String: Int]] = [:], verdicts: [String: Int] = [:]
        for verdict in ["agreement", "inconsistency", "unresolved"] {
            let selected = rows.filter { $0["verdict"] as? String == verdict }
            verdicts[verdict] = selected.count
            reasons[verdict] = counts(selected.flatMap { Array(Set($0["reason_codes"] as? [String] ?? [])) })
        }
        return ["schema_version": 1, "report_kind": "airs.report_summary", "source_report": identity,
            "summary": try XCTUnwrap(source["summary"]),
            "finding_counts": ["by_verdict": verdicts, "by_coverage": counts(rows.compactMap { $0["coverage"] as? String }),
                "by_mode": counts(rows.compactMap { $0["mode"] as? String }), "by_scope": counts(rows.compactMap { $0["scope"] as? String })],
            "reason_counts_by_verdict": reasons, "findings": rows.map { $0.filter { $0.key != "evidence" } },
            "metadata": ["entry_count": ranges.count, "entry_counts_by_mode": counts(ranges.compactMap { $0["mode"] as? String }), "issue_count": issues.count, "issues": issues],
            "source_limitations": try XCTUnwrap(source["limitations"]), "limitations": ["Owned saved summary fixture."]]
    }
}

final class SavedReportSummaryTests: XCTestCase {
    func testSavedSummaryBaseBindsOriginalIDsWithoutEvidenceAndKeepsCounts() throws {
        let source = try SummaryProjectionFixture.source(), bytes = try SummaryProjectionFixture.bytes(SummaryProjectionFixture.summary(source))
        let value = try SavedReportSummary.decode(bytes)
        let bound = try value.bind(SummaryProjectionFixture.bytes(source), projectionBytes: bytes, options: SummaryOptions())
        XCTAssertEqual(value.findings.map(\.id), bound.findings.map(\.id))
        XCTAssertEqual(value.summary.functionCount, 9)
        XCTAssertEqual(value.summary.unresolvedCount, 4)
        XCTAssertNil(value.finding_selection); XCTAssertNil(value.finding_name_selection); XCTAssertNil(value.finding_order); XCTAssertNil(value.finding_limit)
        XCTAssertFalse(bound.findings[0].evidence.isEmpty)
    }
    func testSavedSummaryORWithinFamiliesANDNameAndStableVerdictOrderBind() throws {
        let source = try SummaryProjectionFixture.source()
        var output = try SummaryProjectionFixture.summary(source)
        let rows = try XCTUnwrap(output["findings"] as? [[String: Any]])
        // Two unresolved alternatives plus a mismatched verdict must retain exactly two rows.
        let reasons = ["dwarf_fde_not_evaluated", "unsupported_control_flow"]
        let selected = rows.filter { ($0["reason_codes"] as? [String] ?? []).contains(where: reasons.contains) }
        XCTAssertEqual(selected.count, 2)
        output["finding_selection"] = ["requested": ["inconsistency", "unresolved"], "requested_reasons": reasons,
            "selected_count": 2, "omitted_count": 7, "original_count": 9]
        output["finding_name_selection"] = ["contains": "_", "case_sensitive": true, "normalization": "none", "input_count": 2, "selected_count": 2, "omitted_count": 0]
        output["finding_order"] = "verdict"; output["findings"] = selected
        let bytes = try SummaryProjectionFixture.bytes(output), value = try SavedReportSummary.decode(bytes)
        _ = try value.bind(SummaryProjectionFixture.bytes(source), projectionBytes: bytes,
            options: SummaryOptions(verdicts: [.inconsistency, .unresolved], reasons: reasons, nameContains: "_", order: .verdict))
        var swapped = output; swapped["findings"] = Array(selected.reversed())
        let swappedBytes = try SummaryProjectionFixture.bytes(swapped), swappedValue = try SavedReportSummary.decode(swappedBytes)
        XCTAssertThrowsError(try swappedValue.bind(SummaryProjectionFixture.bytes(source), projectionBytes: swappedBytes,
            options: SummaryOptions(verdicts: [.inconsistency, .unresolved], reasons: reasons, nameContains: "_", order: .verdict)))
    }
    func testSavedSummaryUnicodeLiteralQueryDoesNotNormalizeOrIgnoreCase() throws {
        var source = try SummaryProjectionFixture.source()
        var rows = try XCTUnwrap(source["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(rows[0]["function"] as? [String: Any]); function["name"] = "Cafe\u{301}"; rows[0]["function"] = function; source["findings"] = rows
        for (query, count) in [("Café", 0), ("cafe\u{301}", 0), ("Cafe\u{301}", 1)] {
            var output = try SummaryProjectionFixture.summary(source)
            let full = try XCTUnwrap(output["findings"] as? [[String: Any]])
            output["findings"] = count == 0 ? [] : [full[0]]
            output["finding_name_selection"] = ["contains": query, "case_sensitive": true, "normalization": "none", "input_count": 9, "selected_count": count, "omitted_count": 9 - count]
            let bytes = try SummaryProjectionFixture.bytes(output), value = try SavedReportSummary.decode(bytes)
            _ = try value.bind(SummaryProjectionFixture.bytes(source), projectionBytes: bytes, options: SummaryOptions(nameContains: query))
            XCTAssertEqual(value.findings.count, count)
        }
    }
    func testSavedSummaryZeroLimitKeepsFullCountsAndAbsentConfiguration() throws {
        var source = try SummaryProjectionFixture.source(); source.removeValue(forKey: "analysis_config")
        var output = try SummaryProjectionFixture.summary(source)
        output["findings"] = []; output["finding_limit"] = ["maximum": 0, "returned_count": 0, "omitted_count": 9, "selected_count": 9]
        let bytes = try SummaryProjectionFixture.bytes(output), value = try SavedReportSummary.decode(bytes)
        _ = try value.bind(SummaryProjectionFixture.bytes(source), projectionBytes: bytes, options: SummaryOptions(limit: 0))
        XCTAssertEqual(value.summary.functionCount, 9); XCTAssertEqual(value.finding_counts.by_verdict["unresolved"], 4)
        XCTAssertEqual(value.finding_limit?.maximum, 0)
    }
    func testSavedSummaryMalformedMetadataDuplicateIDsEvidenceAndWrongFactsRefuse() throws {
        let source = try SummaryProjectionFixture.source(), base = try SummaryProjectionFixture.summary(source)
        for key in ["finding_selection", "finding_name_selection", "finding_order", "finding_limit"] {
            for value in [NSNull(), false, [], 1] as [Any] {
                var bad = base; bad[key] = value
                XCTAssertThrowsError(try SavedReportSummary.decode(SummaryProjectionFixture.bytes(bad)))
            }
        }
        var bad = base, rows = try XCTUnwrap(base["findings"] as? [[String: Any]])
        rows[1]["id"] = rows[0]["id"]; bad["findings"] = rows
        XCTAssertThrowsError(try SavedReportSummary.decode(SummaryProjectionFixture.bytes(bad)))
        bad = base; rows = try XCTUnwrap(base["findings"] as? [[String: Any]])
        rows[0]["evidence"] = []; bad["findings"] = rows
        XCTAssertThrowsError(try SavedReportSummary.decode(SummaryProjectionFixture.bytes(bad)))
        bad = base; rows = try XCTUnwrap(base["findings"] as? [[String: Any]])
        rows[0]["id"] = "airsf-" + String(repeating: "f", count: 64); bad["findings"] = rows
        let bytes = try SummaryProjectionFixture.bytes(bad), value = try SavedReportSummary.decode(bytes)
        XCTAssertThrowsError(try value.bind(SummaryProjectionFixture.bytes(source), projectionBytes: bytes, options: SummaryOptions()))
        bad = base; bad["finding_limit"] = ["maximum": 0, "returned_count": 9, "omitted_count": 0, "selected_count": 9]
        XCTAssertThrowsError(try SavedReportSummary.decode(SummaryProjectionFixture.bytes(bad)))
        XCTAssertThrowsError(try SavedReportSummary.decode(Data("{}".utf8)))
    }
    func testSavedSummaryWrongSourceAndChangedFullCountsRefuse() throws {
        let source = try SummaryProjectionFixture.source(), output = try SummaryProjectionFixture.summary(source)
        let bytes = try SummaryProjectionFixture.bytes(output), value = try SavedReportSummary.decode(bytes)
        XCTAssertThrowsError(try value.bind(CoverageInventoryTests().data("unicode-source.audit"), projectionBytes: bytes, options: SummaryOptions()))
        var bad = output, counts = try XCTUnwrap(output["finding_counts"] as? [String: Any])
        counts["by_mode"] = ["unknown": 9]; bad["finding_counts"] = counts
        let badBytes = try SummaryProjectionFixture.bytes(bad), admitted = try SavedReportSummary.decode(badBytes)
        XCTAssertThrowsError(try admitted.bind(SummaryProjectionFixture.bytes(source), projectionBytes: badBytes, options: SummaryOptions()))
    }
    func testSavedSummaryNativeSizeLimitIsNamed() throws {
        XCTAssertThrowsError(try SavedReportSummary.decode(Data(repeating: 32, count: 32 * 1_048_576 + 1))) { XCTAssertTrue($0.localizedDescription.contains("32 MiB")) }
    }
}

extension SavedReportSummaryTests {
    func testSavedSummaryConfigurationAbsenceAndExplicitNullStayDistinct() throws {
        var source = try SummaryProjectionFixture.source()
        source.removeValue(forKey: "analysis_config")
        var output = try SummaryProjectionFixture.summary(source)
        let absentBytes = try SummaryProjectionFixture.bytes(output), absent = try SavedReportSummary.decode(absentBytes)
        XCTAssertFalse(absent.hasAnalysisConfiguration)
        source["analysis_config"] = NSNull()
        output = try SummaryProjectionFixture.summary(source)
        let nullBytes = try SummaryProjectionFixture.bytes(output), explicit = try SavedReportSummary.decode(nullBytes)
        XCTAssertTrue(explicit.hasAnalysisConfiguration)
        _ = try explicit.bind(SummaryProjectionFixture.bytes(source), projectionBytes: nullBytes, options: SummaryOptions())
        XCTAssertThrowsError(try absent.bind(SummaryProjectionFixture.bytes(source), projectionBytes: absentBytes, options: SummaryOptions()))
        XCTAssertThrowsError(try explicit.bind(SummaryProjectionFixture.bytes(source), projectionBytes: absentBytes, options: SummaryOptions()))
    }
}

extension SavedReportSummaryTests {
    func testSavedSummaryVerdictOrderGroupsAllRowsAndPreservesSourceTies() throws {
        let source = try SummaryProjectionFixture.source()
        var output = try SummaryProjectionFixture.summary(source)
        let rows = try XCTUnwrap(output["findings"] as? [[String: Any]])
        let indices = [3, 4, 5, 6, 7, 8, 0, 1, 2]
        output["findings"] = indices.map { rows[$0] }; output["finding_order"] = "verdict"
        let bytes = try SummaryProjectionFixture.bytes(output), value = try SavedReportSummary.decode(bytes)
        _ = try value.bind(SummaryProjectionFixture.bytes(source), projectionBytes: bytes, options: SummaryOptions(order: .verdict))
        XCTAssertEqual(value.findings.map(\.id), indices.compactMap { rows[$0]["id"] as? String })
        XCTAssertEqual(value.summary.functionCount, 9)
    }
}
