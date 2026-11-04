import XCTest
import Foundation
import AIRSCore
import EntitlementDiffCore
@testable import AIRSEntitlements

final class SecurityDeltaValueTests: XCTestCase {
    func testStrictTagsAndLegacyNormalization() throws {
        let signed = try SecurityDeltaValue.from(.integer(1), normalizedIntegers: false)
        let unsigned = try SecurityDeltaValue.from(.unsignedInteger(1), normalizedIntegers: false)
        let historical = try SecurityDeltaValue.from(.integer(1), normalizedIntegers: true)
        XCTAssertEqual(try signed.compare(to: unsigned), .different)
        XCTAssertEqual(try signed.compare(to: historical), .representationUnresolved)
        XCTAssertEqual(try historical.compare(to: .normalizedInteger("2")), .different)
        XCTAssertEqual(try SecurityDeltaValue.boolean(true).compare(to: signed), .different)
    }

    func testExactKeysAndNestedOrder() throws {
        let a = SecurityDeltaValue.dictionary([.init(key: "é", value: .array([.signed(1), .signed(2)]))])
        let b = SecurityDeltaValue.dictionary([.init(key: "e\u{301}", value: .array([.signed(1), .signed(2)]))])
        let c = SecurityDeltaValue.dictionary([.init(key: "é", value: .array([.signed(2), .signed(1)]))])
        try a.validate(); try b.validate(); try c.validate()
        XCTAssertEqual(try a.compare(to: b), .different)
        XCTAssertEqual(try a.compare(to: c), .different)
    }

    func testValidationAndRoundTripRetainTypes() throws {
        let original = SecurityDeltaValue.array([.signed(1), .unsigned(1), .normalizedInteger("1"), .boolean(true)])
        let decoded = try JSONDecoder().decode(SecurityDeltaValue.self, from: JSONEncoder().encode(original))
        try decoded.validate()
        guard case .array(let values) = decoded, case .signed(1) = values[0], case .unsigned(1) = values[1],
              case .normalizedInteger("1") = values[2], case .boolean(true) = values[3] else { return XCTFail("Tags changed") }
        XCTAssertThrowsError(try SecurityDeltaValue.normalizedInteger("01").validate())
        XCTAssertThrowsError(try SecurityDeltaValue.realBits(Double.nan.bitPattern).validate())
        XCTAssertThrowsError(try SecurityDeltaValue.array([.array([.boolean(true)])]).validate(maxDepth: 1))
        XCTAssertThrowsError(try SecurityDeltaValue.dictionary([.init(key: "a", value: .boolean(true)), .init(key: "a", value: .boolean(false))]).validate())
        XCTAssertThrowsError(try SecurityDeltaValue.from(.array([.array([.boolean(true)])]), normalizedIntegers: false, maxDepth: 1))
        XCTAssertThrowsError(try SecurityDeltaValue.from(.string("long"), normalizedIntegers: false, maxBytes: 3))
        let text = String(decoding: try JSONEncoder().encode(SecurityDeltaValue.unsigned(UInt64.max)), as: UTF8.self)
        XCTAssertTrue(text.contains("18446744073709551615"))
        XCTAssertThrowsError(try JSONDecoder().decode(SecurityDeltaValue.self, from: Data(#"{"type":"signed","value":"01"}"#.utf8)))
        XCTAssertThrowsError(try SecurityDeltaValue.realBits(Double.nan.bitPattern).compare(to: .realBits(Double.nan.bitPattern)))
    }

    func testValueResourceRefusalCodesIdentifyTheReachedLimit() throws {
        let nested = SecurityDeltaValue.array([.array([.boolean(true)])])
        XCTAssertThrowsError(try nested.validate(maxDepth: 1)) { XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .typedDepthLimit) }
        XCTAssertThrowsError(try nested.validate(maxNodes: 2)) { XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .typedNodeLimit) }
        XCTAssertThrowsError(try SecurityDeltaValue.string("long").validate(maxBytes: 3)) { XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .decodedByteLimit) }
        XCTAssertNoThrow(try nested.validate(maxDepth: 2, maxNodes: 3, maxBytes: 1))
    }

    func testLegacyErrorsTranslateAtDeltaBoundaryWithoutMaskingCancellation() {
        func check(_ error: Error, _ expected: SecurityDeltaRefusalCode) {
            XCTAssertThrowsError(try securityDeltaBoundary { throw error } as Void) {
                XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, expected)
            }
        }
        check(SavedReportError.limit, .resourceLimit)
        check(EntitlementDataError.nonFiniteNumber, .invalidReview)
        check(EntitlementDataError.limitExceeded("depth"), .resourceLimit)
        check(EntitlementDiffCore.ReportError.architectureMismatch, .invalidReview)
        check(CodeSignatureEvidenceError.unavailable, .sourceUnavailable)
        XCTAssertThrowsError(try securityDeltaBoundary { throw CancellationError() } as Void) { XCTAssertTrue($0 is CancellationError) }
    }
}
