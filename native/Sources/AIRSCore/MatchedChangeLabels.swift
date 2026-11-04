import Foundation

public extension ComparisonReport {
    /// Verifies host observation labels for selected pairs, without proving matches.
    /// Completeness, matching-basis semantics, binary authenticity and UI activation
    /// remain separate from this explicit report-validation path.
    func validateMatchedChangeLabels(baselineData: Data, currentData: Data) throws {
        try validateSelectedSourceFacts(baselineData: baselineData, currentData: currentData)
        try validateManualPairChanges(baselineData: baselineData, currentData: currentData)
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let configurationChanged = try admittedComparisonConfigurationsDiffer(baselineData: baselineData, currentData: currentData)
        let comparable = comparison.modelCompatible && !configurationChanged
        var oldByID: [String: Finding] = [:], newByID: [String: Finding] = [:]
        for finding in baseline.findings { oldByID[finding.id] = finding }
        for finding in current.findings { newByID[finding.id] = finding }
        for row in changes where row.matchBasis != "manual_review" {
            // One-sided rows and unselected ambiguity groups have no chosen pair.
            guard let oldID = row.baselineID, let newID = row.currentID else { continue }
            guard let old = oldByID[oldID], let new = newByID[newID] else {
                throw ReportError.invalidContents("Selected pair endpoints are unavailable.")
            }
            let expected: String
            if comparable {
                expected = try FindingObservationSignature(old) == FindingObservationSignature(new) ? "unchanged" : "changed"
            } else {
                expected = "ambiguous"
            }
            guard row.change == expected else {
                throw ReportError.invalidContents("Selected pair label contradicts its source observations or compatibility.")
            }
        }
    }
}
