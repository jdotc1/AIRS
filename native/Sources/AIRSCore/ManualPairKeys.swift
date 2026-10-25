import Foundation

public extension ComparisonReport {
    /// Checks exact ordered manual keys after recorded policy and selected-row proof.
    /// Canonical keys remain review metadata, not source-function identity evidence.
    func validateManualPairKeys(baselineData: Data, currentData: Data) throws {
        try validateMatchingPolicy(baselineData: baselineData, currentData: currentData)
        for row in changes where row.matchBasis == "manual_review" {
            guard let oldID = row.baselineID, let newID = row.currentID else {
                throw ReportError.invalidContents("Canonical manual key requires both selected source endpoints.")
            }
            let expected = "manual:\(oldID):\(newID)"
            guard row.key.utf8.elementsEqual(expected.utf8) else {
                throw ReportError.invalidContents("Manual key must contain the exact selected baseline and current IDs in order.")
            }
        }
    }
}
