import XCTest
import Foundation
import Darwin
import AIRSCore
import AIRSEntitlements

final class SecurityDeltaRealResourceTests: XCTestCase {
    func testOwnedMaximumInventoryAndLoweredOutputCapsWithProcessMetrics() throws {
        let start = DispatchTime.now().uptimeNanoseconds
        func inventory(_ version: String, count: Int) -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: []),
                components: (0..<count).map { .init(relativePath: "Contents/Helpers/Owned\($0)", kind: "helper", declaredVersion: version, architectures: ["arm64"]) })
        }
        let previous = inventory("1", count: 64), current = inventory("2", count: 64)
        let review = try ComponentComparison.review(previous: previous, current: current, architecture: .arm64, entitlementResults: [])
        let options = try SecurityDeltaOptions(maximumObservations: 100, maximumFindings: 20)
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review, options: options)
        XCTAssertLessThanOrEqual(report.observations.count, 100)
        XCTAssertLessThanOrEqual(report.findings.count, 20)
        XCTAssertTrue(report.coverage.omissions.contains { $0.count > 0 })
        let tooMany = try ComponentComparison.review(previous: previous, current: inventory("2", count: 65), architecture: .arm64, entitlementResults: [])
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(review: tooMany)) { error in
            XCTAssertEqual((error as? SecurityDeltaRefusal)?.code, .componentLimit)
        }
        var usage = rusage(), allocator = malloc_statistics_t()
        XCTAssertEqual(getrusage(RUSAGE_SELF, &usage), 0)
        malloc_zone_statistics(nil, &allocator)
        let elapsed = Double(DispatchTime.now().uptimeNanoseconds - start) / 1_000_000_000
        let metrics: [String: Double] = ["elapsed_seconds": elapsed, "process_peak_rss_bytes": Double(usage.ru_maxrss),
            "allocator_size_in_use": Double(allocator.size_in_use), "allocator_zone_high_water_sum": Double(allocator.max_size_in_use),
            "allocator_reserved_bytes": Double(allocator.size_allocated), "retained_observations": Double(report.observations.count),
            "retained_findings": Double(report.findings.count)]
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys]
        print("TRACK_A_OWNED_RESOURCE " + String(decoding: try encoder.encode(metrics), as: UTF8.self))
        // Process lifetime/allocator-zone statistics include XCTest/runtime work.
        // They are empirical observations, not a process RSS or exact heap-peak guarantee.
    }
}
