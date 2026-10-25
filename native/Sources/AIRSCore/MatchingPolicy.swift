import Foundation

public extension ComparisonReport {
    /// Checks recorded host policy and known basis vocabulary after declared-row proof.
    /// This explicit boundary does not establish complete producer output or identity.
    func validateMatchingPolicy(baselineData: Data, currentData: Data) throws {
        try validateUnmatchedRows(baselineData: baselineData, currentData: currentData)
        let supported: Set<String> = ["exact_image_offset", "manual_review", "unique_symbol",
                                      "exact_body_candidate", "unmatched"]
        guard changes.allSatisfy({ supported.contains($0.matchBasis) }) else {
            throw ReportError.invalidContents("Unsupported matching basis cannot claim host policy validation.")
        }
        let hasManualPairs = comparison.manualPairs?.isEmpty == false
        var expected = hasManualPairs ? "manual_then_unique_symbol" : "exact_digest_then_unique_symbol"
        if comparison.exactBodyCandidates == true { expected += "_then_exact_body_candidate" }
        // Missing body status stays unavailable; composed row proofs retain that
        // uncertainty. The policy string never backfills the optional status.
        guard Data(comparison.matchingPolicy.utf8) == Data(expected.utf8) else {
            throw ReportError.invalidContents("Recorded matching policy contradicts validated selections or explicit body status.")
        }
    }
}
