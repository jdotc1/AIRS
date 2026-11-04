import Foundation

public extension ComparisonReport {
    /// Verifies declared duplicate symbol groups, not singleton one-sided outcomes.
    /// Missing body-phase status remains unavailable; no source completeness claim.
    func validateDuplicateSymbolGroups(baselineData: Data, currentData: Data) throws {
        try validateBodyCandidatePairs(baselineData: baselineData, currentData: currentData)
        guard !comparison.sameImage else { return } // Composed exact-offset authority.
        let rows = changes.filter { $0.matchBasis == "unique_symbol" }
        guard !rows.isEmpty else { return }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let oldPins = Set((comparison.manualPairs ?? []).map(\.baselineID))
        let newPins = Set((comparison.manualPairs ?? []).map(\.currentID))
        let oldGroups = admittedSymbolCandidateGroups(baseline.findings, excluding: oldPins)
        let newGroups = admittedSymbolCandidateGroups(current.findings, excluding: newPins)
        let prefix = Data("symbol:".utf8)
        for row in rows {
            let bytes = Data(row.key.utf8)
            guard bytes.starts(with: prefix) else {
                throw ReportError.invalidContents("Symbol groups require exact source-name keys.")
            }
            let name = Data(bytes.dropFirst(prefix.count))
            guard usableComparisonSymbol(String(decoding: name, as: UTF8.self)) else {
                throw ReportError.invalidContents("Symbol groups require usable source names.")
            }
            let before = oldGroups[name] ?? SymbolCandidateGroup()
            let after = newGroups[name] ?? SymbolCandidateGroup()
            guard before.count > 0 || after.count > 0 else {
                throw ReportError.invalidContents("Symbol key has no remaining source-name group.")
            }
            if before.count > 1 || after.count > 1 {
                // Body selection never consumes these nonstandalone groups.
                guard row.change == "ambiguous", row.baselineID == before.selectedID,
                      row.currentID == after.selectedID else {
                    throw ReportError.invalidContents("Duplicate symbol group must remain ambiguous with only actual singleton sides selected.")
                }
            } else if row.change == "ambiguous", row.baselineID == nil || row.currentID == nil {
                throw ReportError.invalidContents("Unselected symbol ambiguity requires source-name multiplicity.")
            }
            // Fully selected pairs passed the composed symbol/observation proof.
            // Singleton one-sided matching outcomes remain a separate phase.
        }
    }
}
