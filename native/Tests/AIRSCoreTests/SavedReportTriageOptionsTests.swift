import Foundation
import XCTest
@testable import AIRSCore

final class SavedReportTriageOptionsTests: XCTestCase {
    func testTriageAbsentOptionsEmitNoFlagsAndDefaultsRemainCountAndSource() throws {
        XCTAssertEqual(try CoverageOptions().arguments, [])
        XCTAssertEqual(try SummaryOptions().arguments, [])
        XCTAssertEqual(try CoverageOptions().order, .count)
        XCTAssertEqual(try SummaryOptions().order, .source)
    }
    func testTriageReasonsCanonicalizeAndRawEntryBudgetPrecedesDeduplication() throws {
        XCTAssertEqual(try CoverageOptions(reasons: ["z", "a", "z"]).reasons, ["a", "z"])
        XCTAssertThrowsError(try CoverageOptions(reasons: Array(repeating: "a", count: 33)))
        XCTAssertThrowsError(try SummaryOptions(reasons: Array(repeating: "a", count: 33)))
        for code in ["", "A", "é", "a-b", "a b", "a\n", "1a", String(repeating: "a", count: 129)] {
            XCTAssertThrowsError(try CoverageOptions(reasons: [code]))
        }
        XCTAssertNoThrow(try CoverageOptions(reasons: ["a" + String(repeating: "0_", count: 63) + "z"]))
        XCTAssertThrowsError(try CoverageOptions(reasons: []))
    }
    func testTriageMinimumAndBothDetailLimitBoundariesRefuseWithoutTruncation() throws {
        for count in [0, -1, Int.min] { XCTAssertThrowsError(try CoverageOptions(minimumCount: count)) }
        XCTAssertEqual(try CoverageOptions(minimumCount: Int.max).minimumCount, Int.max)
        for limit in [-1, 200_001, Int.max] {
            XCTAssertThrowsError(try CoverageOptions(limit: limit))
            XCTAssertThrowsError(try SummaryOptions(limit: limit))
        }
        for limit in [0, 200_000] {
            XCTAssertEqual(try CoverageOptions(limit: limit).arguments, ["--limit", String(limit)])
            XCTAssertEqual(try SummaryOptions(limit: limit).arguments, ["--limit", String(limit)])
        }
    }
    func testTriageSummaryLiteralUTF8AndVerdictCanonicalization() throws {
        let options = try SummaryOptions(verdicts: [.unresolved, .agreement, .unresolved], reasons: ["b", "a"],
            nameContains: "e\u{301} ' space", order: .verdict, limit: 0)
        XCTAssertEqual(options.arguments, ["--verdict", "agreement", "--verdict", "unresolved", "--reason", "a", "--reason", "b",
            "--name-contains=e\u{301} ' space", "--sort", "verdict", "--limit", "0"])
        XCTAssertThrowsError(try SummaryOptions(verdicts: []))
        for name in ["", "  ", "x\t", "x\u{7f}", String(repeating: "é", count: 129)] {
            XCTAssertThrowsError(try SummaryOptions(nameContains: name))
        }
        XCTAssertNoThrow(try SummaryOptions(nameContains: String(repeating: "é", count: 128)))
    }
    func testTriageNameQueryStartingWithDashStaysOneToken() throws {
        for name in ["-[NSObject", "--limit", "--output", "-1"] {
            XCTAssertEqual(try SummaryOptions(nameContains: name).arguments, ["--name-contains=" + name])
        }
    }
    func testTriageAggregateLimitsCountDuplicateInputsAndNameEachRefusal() throws {
        XCTAssertNoThrow(try SavedReportInputBudget.validateCounts(reportCount: 128, byteCount: 128 * 1_048_576, findingCount: 200_000))
        let cases: [(Int, Int, Int, String)] = [(129, 0, 0, "128"), (0, 0, 0, "128"), (1, 128 * 1_048_576 + 1, 0, "128 MiB"), (1, 0, 200_001, "200,000")]
        for (reports, bytes, findings, message) in cases {
            XCTAssertThrowsError(try SavedReportInputBudget.validateCounts(reportCount: reports, byteCount: bytes, findingCount: findings)) {
                XCTAssertTrue($0.localizedDescription.contains(message))
            }
        }
        let source = try ManualPairRequestFixtures.source(current: false)
        XCTAssertNoThrow(try SavedReportInputBudget.validate([source, source]))
        XCTAssertThrowsError(try SavedReportInputBudget.validate(Array(repeating: source, count: 129)))
        XCTAssertThrowsError(try SavedReportInputBudget.validate([Data(repeating: 32, count: 64 * 1_048_576 + 1)])) {
            XCTAssertTrue($0.localizedDescription.contains("64 MiB"))
        }
    }
}
