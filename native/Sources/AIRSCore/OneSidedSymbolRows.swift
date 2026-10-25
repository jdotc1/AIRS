import Foundation

public extension ComparisonReport {
    /// Verifies declared singleton symbol outcomes without assuming absent body status.
    /// Omitted groups, unmatched bases and source completeness remain separate.
    func validateOneSidedSymbolRows(baselineData: Data, currentData: Data) throws {
        try validateDuplicateSymbolGroups(baselineData: baselineData, currentData: currentData)
        guard !comparison.sameImage else { return }
        let rows = changes.filter { $0.matchBasis == "unique_symbol" }
        guard !rows.isEmpty else { return }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let oldPins = Set((comparison.manualPairs ?? []).map(\.baselineID))
        let newPins = Set((comparison.manualPairs ?? []).map(\.currentID))
        let oldGroups = admittedSymbolCandidateGroups(baseline.findings, excluding: oldPins)
        let newGroups = admittedSymbolCandidateGroups(current.findings, excluding: newPins)
        var possibleOld = Set<String>(), possibleNew = Set<String>()
        if comparison.exactBodyCandidates != false,
           baseline.image.architecture == current.image.architecture,
           baseline.image.cpuSubtype == current.image.cpuSubtype {
            let pairs = admittedBodyCandidatePairs(baseline: baseline.findings, current: current.findings,
                                                  baselinePins: oldPins, currentPins: newPins)
            for pair in pairs.values { possibleOld.insert(pair.baselineID); possibleNew.insert(pair.currentID) }
        }
        let prefixCount = "symbol:".utf8.count // Canonical usable source key already checked by composition.
        for row in rows {
            let name = Data(row.key.utf8.dropFirst(prefixCount))
            let before = oldGroups[name] ?? SymbolCandidateGroup()
            let after = newGroups[name] ?? SymbolCandidateGroup()
            if before.count > 1 || after.count > 1 { continue } // Composed multiplicity rules are authoritative.
            if before.count == 1 && after.count == 1 {
                guard row.baselineID == before.selectedID, row.currentID == after.selectedID else {
                    throw ReportError.invalidContents("Established symbol pair cannot hide an endpoint in a one-sided row.")
                }
                continue // Composed observation-label proof applies.
            }
            let couldConsume = before.selectedID.map(possibleOld.contains) == true
                || after.selectedID.map(possibleNew.contains) == true
            if couldConsume {
                guard comparison.exactBodyCandidates != nil else {
                    throw ReportError.invalidContents("Body-candidate status is unavailable for this singleton symbol outcome.")
                }
                throw ReportError.invalidContents("Body selection consumed the declared singleton symbol endpoint.")
            }
            let expected = before.count == 1 ? "removed" : "added"
            guard before.count == 1 || after.count == 1,
                  row.baselineID == before.selectedID, row.currentID == after.selectedID,
                  row.change == expected else {
                throw ReportError.invalidContents("Singleton symbol row contradicts its remaining source group or one-sided label.")
            }
        }
    }
}
