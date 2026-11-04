import Foundation

public extension ComparisonReport {
    /// Binds every selected row ID/verdict/scope to its admitted source side.
    /// Accounting and declared source identity precede lookup; matching truth,
    /// configuration compatibility, signatures and source completeness remain separate.
    func validateSelectedSourceFacts(baselineData: Data, currentData: Data) throws {
        try validateRowAccounting()
        try validateManualPairEndpoints(baselineData: baselineData, currentData: currentData)
        // Reuse the admitted source/report contract rather than reading files or
        // dropping missing endpoints from a donor-style compactMap lookup.
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        var oldByID: [String: Finding] = [:], newByID: [String: Finding] = [:]
        for finding in baseline.findings { oldByID[finding.id] = finding }
        for finding in current.findings { newByID[finding.id] = finding }
        for row in changes {
            if let id = row.baselineID {
                guard let finding = oldByID[id], row.beforeVerdict == finding.verdict,
                      row.beforeScope == finding.scope else {
                    throw ReportError.invalidContents("Selected baseline row facts contradict their source finding.")
                }
            }
            if let id = row.currentID {
                guard let finding = newByID[id], row.afterVerdict == finding.verdict,
                      row.afterScope == finding.scope else {
                    throw ReportError.invalidContents("Selected current row facts contradict their source finding.")
                }
            }
        }
    }
}
