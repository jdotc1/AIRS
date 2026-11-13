import Foundation
import XCTest
@testable import AIRSCore

final class SwiftFlowProfileTests: XCTestCase {
    private func arguments(_ options: SwiftFlowOptions) -> [String] {
        options.arguments(input: URL(fileURLWithPath: "/owned/input"), output: URL(fileURLWithPath: "/owned/out"))
    }

    func testPickerOffersEveryAdmittedExtendedProfileInOrder() {
        XCTAssertEqual(SwiftFlowProfile.allCases,
                       [.standard, .broad, .broadLarge, .broadExtended, .broadExtendedV2, .broadExtendedV3, .broadImports])
    }

    func testTitlesAreNonEmptyAndDistinct() {
        let titles = SwiftFlowProfile.allCases.map(\.title)
        XCTAssertTrue(titles.allSatisfy { !$0.isEmpty })
        XCTAssertEqual(Set(titles).count, titles.count)
        XCTAssertTrue(SwiftFlowProfile.broadExtendedV2.title.contains("caller error tests"))
        XCTAssertTrue(SwiftFlowProfile.broadExtendedV3.title.contains("indirect targets"))
    }

    func testModelsAndArgumentsAreDistinctAndMatchTheEngineIdentities() {
        XCTAssertEqual(SwiftFlowProfile.broadExtendedV2.broadModel, "swift-broad-error-flow-extended-v2")
        XCTAssertEqual(SwiftFlowProfile.broadExtendedV2.broadArgument, "broad-extended-v2")
        XCTAssertEqual(SwiftFlowProfile.broadExtendedV3.broadModel, "swift-broad-error-flow-extended-v3")
        XCTAssertEqual(SwiftFlowProfile.broadExtendedV3.broadArgument, "broad-extended-v3")
        XCTAssertEqual(SwiftFlowProfile.broadExtended.broadModel, "swift-broad-error-flow-extended-v1")
        XCTAssertEqual(SwiftFlowProfile.broadExtended.broadArgument, "broad-extended-v1")
        let broad = SwiftFlowProfile.allCases.filter { $0 != .standard }
        XCTAssertEqual(Set(broad.compactMap(\.broadModel)).count, broad.count)
        XCTAssertEqual(Set(broad.compactMap(\.broadArgument)).count, broad.count)
        XCTAssertNil(SwiftFlowProfile.standard.broadModel)
        XCTAssertNil(SwiftFlowProfile.standard.broadArgument)
    }

    func testExtendedV2AndV3CommandsCarryTheBroadPrerequisites() throws {
        for (profile, argument) in [(SwiftFlowProfile.broadExtendedV2, "broad-extended-v2"),
                                    (SwiftFlowProfile.broadExtendedV3, "broad-extended-v3")] {
            let args = arguments(SwiftFlowOptions(includeMethods: true, includeWitnesses: false, profile: profile))
            let flag = try XCTUnwrap(args.firstIndex(of: "--swift-profile"), argument)
            XCTAssertEqual(args[flag + 1], argument)
            XCTAssertEqual(args.filter { $0 == "--include-outcome-witnesses" }.count, 1, argument)
            for required in ["--include-error-regions", "--validate-region-entries", "--include-structured-presentation"] {
                XCTAssertTrue(args.contains(required), "\(argument) \(required)")
            }
            XCTAssertFalse(args.contains("--include-swift-methods"), argument)
            XCTAssertEqual(Array(args.suffix(2)), ["--", "/owned/input"])
        }
    }
}
