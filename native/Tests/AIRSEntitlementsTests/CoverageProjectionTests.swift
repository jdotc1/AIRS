import Foundation
import XCTest
import AIRSCore
@testable import AIRSEntitlements

final class CoverageProjectionTests: XCTestCase {
    private func base() throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: CoverageInventoryTests().data("single")) as? [String: Any])
    }
    private func decode(_ object: [String: Any]) throws -> CoverageInventory { try CoverageInventory.decode(JSONSerialization.data(withJSONObject: object)) }

    func testCoverageProjectionBaseRetainsAbsentMetadataAndFullCounts() throws {
        let inventory = try decode(base())
        XCTAssertNil(inventory.selection)
        XCTAssertEqual(inventory.summary.function_count, 9)
        XCTAssertEqual(inventory.summary.unresolved_count, 4)
        XCTAssertEqual(inventory.reasons.count, 4)
        try inventory.validateSources([CoverageInventoryTests().data("source.audit")], options: CoverageOptions())
    }
    func testCoverageProjectionEachOptionalKeyAndComposedZeroLimit() throws {
        let original = try base(), reasons = try XCTUnwrap(original["reasons"] as? [[String: Any]])
        let codes = try reasons.map { try XCTUnwrap($0["reason"] as? String) }.sorted()
        var selection = original
        selection["reason_selection"] = ["requested": codes, "matched": codes, "unmatched": []]
        XCTAssertEqual(try decode(selection).selection?.reason_selection?.requested, codes)
        var frequency = original
        frequency["reason_frequency_selection"] = ["minimum_count": 1, "input_count": 4, "selected_count": 4, "omitted_count": 0]
        XCTAssertEqual(try decode(frequency).selection?.reason_frequency_selection?.minimum_count, 1)
        var order = original
        order["reason_order"] = "reason"
        order["reasons"] = reasons.sorted { ($0["reason"] as? String ?? "") < ($1["reason"] as? String ?? "") }
        XCTAssertEqual(try decode(order).selection?.reason_order, "reason")
        var limit = original
        limit["reasons"] = []
        limit["reason_limit"] = ["maximum": 0, "returned_count": 0, "omitted_count": 4, "selected_count": 4]
        XCTAssertEqual(try decode(limit).selection?.reason_limit?.maximum, 0)
        limit["reason_selection"] = selection["reason_selection"]
        limit["reason_frequency_selection"] = frequency["reason_frequency_selection"]
        limit["reason_order"] = "reason"
        let inventory = try decode(limit)
        XCTAssertEqual(inventory.summary.unresolved_count, 4)
        try inventory.validateSources([CoverageInventoryTests().data("source.audit")], options: CoverageOptions(reasons: codes, minimumCount: 1, order: .reason, limit: 0))
    }
    func testCoverageProjectionNoMatchesRemainValidWithoutChangingDenominator() throws {
        var value = try base()
        value["reasons"] = []
        value["reason_selection"] = ["requested": ["absent_reason"], "matched": [], "unmatched": ["absent_reason"]]
        let inventory = try decode(value)
        XCTAssertEqual(inventory.summary.function_count, 9)
        try inventory.validateSources([CoverageInventoryTests().data("source.audit")], options: CoverageOptions(reasons: ["absent_reason"]))
    }
    func testCoverageProjectionNullWrongTypeUnknownKeysAndImpossibleArithmeticRefuse() throws {
        for key in CoverageSelectionMetadata.keys {
            for malformed in [NSNull(), 1, [], "wrong"] as [Any] {
                var value = try base(); value[key] = malformed
                XCTAssertThrowsError(try decode(value), key)
            }
        }
        var value = try base()
        value["unexpected_projection"] = [:]
        XCTAssertThrowsError(try decode(value))
        value = try base()
        value["reason_frequency_selection"] = ["minimum_count": 1, "input_count": 4, "selected_count": 4, "omitted_count": 1]
        XCTAssertThrowsError(try decode(value))
        value["reason_frequency_selection"] = ["minimum_count": 2, "input_count": 4, "selected_count": 4, "omitted_count": 0]
        XCTAssertThrowsError(try decode(value))
        value = try base()
        value["reason_limit"] = ["maximum": 0, "returned_count": 4, "omitted_count": 0, "selected_count": 4]
        XCTAssertThrowsError(try decode(value))
    }
    func testCoverageProjectionInventedSelectionOrWrongSourceRefusesBinding() throws {
        var value = try base()
        value["reasons"] = []
        value["reason_frequency_selection"] = ["minimum_count": 1, "input_count": 4, "selected_count": 0, "omitted_count": 4]
        let inventory = try decode(value)
        XCTAssertThrowsError(try inventory.validateSources([CoverageInventoryTests().data("source.audit")], options: CoverageOptions(minimumCount: 1)))
        let original = try decode(base())
        XCTAssertThrowsError(try original.bindSource(CoverageInventoryTests().data("unicode-source.audit"), at: 0))
        XCTAssertThrowsError(try original.validateSources([CoverageInventoryTests().data("source.audit")], options: CoverageOptions(limit: 0)))
    }
    func testCoverageProjectionDuplicatesAndOverlappingReasonTotalsRemainFull() throws {
        let helper = CoverageInventoryTests(), source = try helper.data("source.audit")
        let duplicates = try CoverageInventory.decode(helper.data("duplicates"))
        try duplicates.validateSources([source, source], options: CoverageOptions())
        XCTAssertEqual(duplicates.summary.input_report_count, 2)
        XCTAssertEqual(duplicates.summary.function_count, 9)
        let overlap = try CoverageInventory.decode(helper.data("overlap"))
        XCTAssertGreaterThan(overlap.reasons.reduce(0) { $0 + $1.count }, overlap.summary.unresolved_count)
    }
    func testCoverageProjectionNativeSizeAndReasonRowLimitsAreNamed() throws {
        XCTAssertThrowsError(try CoverageInventory.decode(Data(repeating: 32, count: 32 * 1_048_576 + 1))) {
            XCTAssertTrue($0.localizedDescription.contains("32 MiB"))
        }
        var value = try base()
        let row = try XCTUnwrap((value["reasons"] as? [[String: Any]])?.first)
        value["reasons"] = Array(repeating: row, count: 4097)
        XCTAssertThrowsError(try decode(value)) { XCTAssertTrue($0.localizedDescription.contains("4,096")) }
    }
}

extension CoverageProjectionTests {
    func testCoverageProjectionRejectsFractionalIntegerMetadataAndNamesJSONNodeBudget() throws {
        var value = try base()
        value["reason_frequency_selection"] = ["minimum_count": 1, "input_count": 4, "selected_count": 4, "omitted_count": 0]
        let bytes = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        let text = String(decoding: bytes, as: UTF8.self).replacingOccurrences(of: "\"minimum_count\":1", with: "\"minimum_count\":1.0")
        XCTAssertThrowsError(try CoverageInventory.decode(Data(text.utf8)))
        let nodes = Data(("[" + Array(repeating: "0", count: 100_001).joined(separator: ",") + "]").utf8)
        XCTAssertThrowsError(try CoverageJSONIdentity.parse(nodes, detailedLimits: true)) { XCTAssertTrue($0.localizedDescription.contains("100,000")) }
    }
}

extension CoverageProjectionTests {
    func testCoverageProjectionFrequencyNoMatchAndJSONDepthAndStringLimits() throws {
        var value = try base(); value["reasons"] = []
        value["reason_frequency_selection"] = ["minimum_count": 2, "input_count": 4, "selected_count": 0, "omitted_count": 4]
        let inventory = try decode(value)
        try inventory.validateSources([CoverageInventoryTests().data("source.audit")], options: CoverageOptions(minimumCount: 2))
        XCTAssertEqual(inventory.summary.unresolved_count, 4)
        let nested = Data((String(repeating: "[", count: 98) + "0" + String(repeating: "]", count: 98)).utf8)
        XCTAssertThrowsError(try CoverageJSONIdentity.parse(nested, detailedLimits: true)) { XCTAssertTrue($0.localizedDescription.contains("96")) }
        let string = Data(("\"" + String(repeating: "a", count: 1_048_577) + "\"").utf8)
        XCTAssertThrowsError(try CoverageJSONIdentity.parse(string, detailedLimits: true)) { XCTAssertTrue($0.localizedDescription.contains("1 MiB")) }
    }
}
