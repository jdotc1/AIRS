import XCTest
import Foundation
@testable import EntitlementDiffCore

final class SecurityDeltaNumericRepresentationTests: XCTestCase {
    func testLegacyNormalizationAndBooleanRemainUnchanged() throws {
        let input: NSDictionary = ["one": NSNumber(value: UInt64(1)), "flag": NSNumber(value: true),
                                   "large": NSNumber(value: UInt64.max)]
        let values = try FoundationEntitlementDecoder().decode(input)
        guard case .integer(1)? = values["one"], case .boolean(true)? = values["flag"],
              case .unsignedInteger(UInt64.max)? = values["large"] else {
            return XCTFail("Legacy numeric normalization or Boolean identity changed")
        }
    }

    func testOptInPreservesExposedNSNumberTypeAndBoolean() throws {
        let number = NSNumber(value: UInt64.max)
        let values = try FoundationEntitlementDecoder(numericRepresentation: .exposed)
            .decode(["number": number, "flag": NSNumber(value: true)] as NSDictionary)
        guard case .unsignedInteger(UInt64.max)? = values["number"],
              case .boolean(true)? = values["flag"] else {
            return XCTFail("Exposed representation or Boolean identity was lost")
        }
    }

    func testSmallExposedUnsignedDiffersFromLegacyNormalization() throws {
        let exposed = FoundationEntitlementDecoder(numericRepresentation: .exposed)
        let legacy = FoundationEntitlementDecoder()
        guard case .unsignedInteger(1) = try exposed.integer(decimal: "1", type: "Q"),
              case .integer(1) = try legacy.integer(decimal: "1", type: "Q"),
              case .integer(-1) = try exposed.integer(decimal: "-1", type: "q") else {
            return XCTFail("Integer representation was not preserved")
        }
        XCTAssertThrowsError(try exposed.integer(decimal: "-1", type: "Q"))
        XCTAssertThrowsError(try exposed.integer(decimal: "18446744073709551616", type: "Q"))
        XCTAssertThrowsError(try exposed.integer(decimal: "1", type: "?"))
        XCTAssertThrowsError(try exposed.integer(decimal: "9223372036854775808", type: "q"))
        for type in ["C", "S", "I", "L", "Q"] {
            guard case .unsignedInteger(1) = try exposed.integer(decimal: "1", type: type) else { return XCTFail(type) }
        }
        for type in ["c", "s", "i", "l", "q"] {
            guard case .integer(1) = try exposed.integer(decimal: "1", type: type) else { return XCTFail(type) }
        }
    }
}
