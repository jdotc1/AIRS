import Foundation

public extension ComparisonReport {
    /// Verifies declared side-specific unmatched outcomes, not source completeness.
    /// Imported body evidence remains unauthenticated; absent status stays unknown.
    func validateUnmatchedRows(baselineData: Data, currentData: Data) throws {
        try validateOneSidedSymbolRows(baselineData: baselineData, currentData: currentData)
        guard !comparison.sameImage else { return } // Composed exact-offset authority.
        let rows = changes.filter { $0.matchBasis == "unmatched" }
        guard !rows.isEmpty else { return }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let oldPins = Set((comparison.manualPairs ?? []).map(\.baselineID))
        let newPins = Set((comparison.manualPairs ?? []).map(\.currentID))
        var oldByID: [String: Finding] = [:], newByID: [String: Finding] = [:]
        for finding in baseline.findings { oldByID[finding.id] = finding }
        for finding in current.findings { newByID[finding.id] = finding }
        var possibleOld = Set<String>(), possibleNew = Set<String>()
        if comparison.exactBodyCandidates != false,
           baseline.image.architecture == current.image.architecture,
           baseline.image.cpuSubtype == current.image.cpuSubtype {
            let pairs = admittedBodyCandidatePairs(baseline: baseline.findings, current: current.findings,
                                                  baselinePins: oldPins, currentPins: newPins)
            for pair in pairs.values { possibleOld.insert(pair.baselineID); possibleNew.insert(pair.currentID) }
        }
        for row in rows {
            let id: String, side: String, expected: String, finding: Finding?, pinned: Bool, couldConsume: Bool
            if let selected = row.baselineID, row.currentID == nil {
                id = selected; side = "before"; expected = "removed"; finding = oldByID[selected]
                pinned = oldPins.contains(selected); couldConsume = possibleOld.contains(selected)
            } else if let selected = row.currentID, row.baselineID == nil {
                id = selected; side = "after"; expected = "added"; finding = newByID[selected]
                pinned = newPins.contains(selected); couldConsume = possibleNew.contains(selected)
            } else {
                throw ReportError.invalidContents("Unmatched row requires exactly one side-specific source endpoint.")
            }
            let key = "unmatched:\(side):\(id)"
            guard row.change == expected, Data(row.key.utf8) == Data(key.utf8), !pinned,
                  let finding, let name = finding.function.name, !usableComparisonSymbol(name) else {
                throw ReportError.invalidContents("Unmatched row contradicts its source name, manual selection, canonical key or one-sided label.")
            }
            if couldConsume {
                guard comparison.exactBodyCandidates != nil else {
                    throw ReportError.invalidContents("Body-candidate status is unavailable for this unmatched outcome.")
                }
                throw ReportError.invalidContents("Body selection consumed the declared unmatched endpoint.")
            }
        }
    }
}
