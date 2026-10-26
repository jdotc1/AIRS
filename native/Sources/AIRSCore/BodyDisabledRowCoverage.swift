import Foundation

public extension ComparisonReport {
    /// Requires all cross-image saved-report groups when body matching is explicitly disabled.
    /// Missing body status is unavailable, not an implicit disabled option.
    func validateBodyDisabledRowCoverage(baselineData: Data, currentData: Data) throws {
        try validateCanonicalRowOrder(baselineData: baselineData, currentData: currentData)
        guard !comparison.sameImage, comparison.exactBodyCandidates == false else {
            throw ReportError.invalidContents("Non-body group coverage requires cross-image sources and explicitly disabled body matching.")
        }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let pairs = comparison.manualPairs ?? []
        let oldPins = Set(pairs.map(\.baselineID)), newPins = Set(pairs.map(\.currentID))
        var expected = Set<Data>()
        for pair in pairs {
            expected.insert(Data("manual:\(pair.baselineID):\(pair.currentID)".utf8))
        }
        for (findings, pins, side) in [(baseline.findings, oldPins, "before"), (current.findings, newPins, "after")] {
            for finding in findings where !pins.contains(finding.id) {
                guard let name = finding.function.name else {
                    throw ReportError.invalidContents("Source finding has no admitted function name.")
                }
                let key = usableComparisonSymbol(name) ? "symbol:" + name : "unmatched:\(side):\(finding.id)"
                // Byte keys preserve distinct Unicode spellings and collapse only exact source groups.
                expected.insert(Data(key.utf8))
            }
        }
        guard Set(changes.map { Data($0.key.utf8) }) == expected else {
            throw ReportError.invalidContents("Comparison rows do not cover every body-disabled saved-report group.")
        }
    }
}
