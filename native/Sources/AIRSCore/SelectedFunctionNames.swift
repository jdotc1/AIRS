import Foundation

public extension ComparisonReport {
    /// Binds selected row labels to admitted source names, not authenticated symbols.
    /// Rows without selected endpoints retain an unverified representative label.
    func validateSelectedFunctionNames(baselineData: Data, currentData: Data) throws {
        try validateManualPairKeys(baselineData: baselineData, currentData: currentData)
        let rows = changes.filter { $0.currentID != nil || $0.baselineID != nil }
        guard !rows.isEmpty else { return }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        var oldByID: [String: Finding] = [:], newByID: [String: Finding] = [:]
        for finding in baseline.findings { oldByID[finding.id] = finding }
        for finding in current.findings { newByID[finding.id] = finding }
        for row in rows {
            let source: Finding?
            if let id = row.currentID { source = newByID[id] }
            else if let id = row.baselineID { source = oldByID[id] }
            else { continue }
            // Current-ID presence is authoritative; a missing current lookup
            // must never fall back to an available baseline or display label.
            guard let name = source?.function.name else {
                throw ReportError.invalidContents("Selected function name is unavailable from its source report.")
            }
            guard row.functionName.utf8.elementsEqual(name.utf8) else {
                throw ReportError.invalidContents("Comparison function label contradicts its selected source name.")
            }
        }
    }
}
