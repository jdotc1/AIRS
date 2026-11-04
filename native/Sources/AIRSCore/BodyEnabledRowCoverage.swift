import Foundation

public extension ComparisonReport {
    /// Requires all cross-image saved-report groups under explicit body opt-in.
    /// Imported body evidence is not authenticated function identity.
    func validateBodyEnabledRowCoverage(baselineData: Data, currentData: Data) throws {
        try validateCanonicalRowOrder(baselineData: baselineData, currentData: currentData)
        guard !comparison.sameImage, comparison.exactBodyCandidates == true else {
            throw ReportError.invalidContents("Body-enabled group coverage requires cross-image sources and explicit body opt-in.")
        }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let pins = comparison.manualPairs ?? []
        let oldPins = Set(pins.map(\.baselineID)), newPins = Set(pins.map(\.currentID))
        var bodyPairs: [Data: AdmittedBodyCandidatePair] = [:]
        if baseline.image.architecture == current.image.architecture,
           baseline.image.cpuSubtype == current.image.cpuSubtype {
            bodyPairs = admittedBodyCandidatePairs(baseline: baseline.findings, current: current.findings,
                                                   baselinePins: oldPins, currentPins: newPins)
        }
        var oldConsumed = oldPins, newConsumed = newPins
        var expected = Set(bodyPairs.keys)
        for pin in pins { expected.insert(Data("manual:\(pin.baselineID):\(pin.currentID)".utf8)) }
        for pair in bodyPairs.values {
            oldConsumed.insert(pair.baselineID); newConsumed.insert(pair.currentID)
        }
        for (findings, consumed, side) in [(baseline.findings, oldConsumed, "before"), (current.findings, newConsumed, "after")] {
            for finding in findings where !consumed.contains(finding.id) {
                guard let name = finding.function.name else {
                    throw ReportError.invalidContents("Source finding has no admitted function name.")
                }
                let key = usableComparisonSymbol(name) ? "symbol:" + name : "unmatched:\(side):\(finding.id)"
                expected.insert(Data(key.utf8))
            }
        }
        guard Set(changes.map { Data($0.key.utf8) }) == expected else {
            throw ReportError.invalidContents("Comparison rows do not cover every body-enabled saved-report group.")
        }
    }
}
