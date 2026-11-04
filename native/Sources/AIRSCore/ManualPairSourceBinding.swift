import Foundation

public extension ComparisonReport {
    /// Adapts MacScope's selected-endpoint lookup to validated AIRS report data.
    /// This binds declared identities and manual row facts only. It does not
    /// authenticate reports, validate configuration identity or recompute changes.
    func validateManualPairEndpoints(baselineData: Data, currentData: Data) throws {
        guard baselineData.count <= ReportFiles.maximumBytes,
              currentData.count <= ReportFiles.maximumBytes else {
            throw ReportError.tooLarge(ReportFiles.maximumBytes)
        }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        guard recordedImageMatches(comparison.baselineImage, baseline.image),
              recordedImageMatches(comparison.currentImage, current.image) else {
            throw ReportError.invalidContents("Manual-pair source image does not match its selected report.")
        }
        let sameImage = baseline.image.sliceSHA256 == current.image.sliceSHA256
            && baseline.image.architecture == current.image.architecture
        let compatible = baseline.generator.analysisModelVersion == current.generator.analysisModelVersion
            && baseline.image.architecture == current.image.architecture
        guard comparison.sameImage == sameImage, comparison.modelCompatible == compatible else {
            throw ReportError.invalidContents("Comparison identity/model flags contradict the selected reports.")
        }
        let pairs = comparison.manualPairs ?? []
        guard !sameImage || pairs.isEmpty else {
            throw ReportError.invalidContents("Manual pairs cannot override exact-image offset authority.")
        }
        // AuditReport.decode already enforces unique finding IDs and count limits.
        var oldByID: [String: Finding] = [:], newByID: [String: Finding] = [:]
        for finding in baseline.findings { oldByID[finding.id] = finding }
        for finding in current.findings { newByID[finding.id] = finding }
        var expected: [String: String] = [:]
        for pair in pairs {
            guard oldByID[pair.baselineID] != nil, newByID[pair.currentID] != nil else {
                throw ReportError.invalidContents("Manual pair endpoint is absent from its selected source report.")
            }
            expected[pair.baselineID] = pair.currentID
        }
        var seen = Set<String>()
        for row in changes where row.matchBasis == "manual_review" {
            guard let oldID = row.baselineID, let newID = row.currentID,
                  expected[oldID] == newID, seen.insert(oldID).inserted,
                  let before = oldByID[oldID], let after = newByID[newID] else {
                throw ReportError.invalidContents("Manual review row does not uniquely represent a recorded source pair.")
            }
            guard row.beforeVerdict == before.verdict, row.afterVerdict == after.verdict,
                  row.beforeScope == before.scope, row.afterScope == after.scope else {
                throw ReportError.invalidContents("Manual review row facts contradict their selected source findings.")
            }
        }
        guard seen.count == pairs.count else {
            throw ReportError.invalidContents("Each recorded manual pair requires one corresponding review row.")
        }
    }
}

private func recordedImageMatches(_ context: ComparisonImage, _ source: ImageInfo) -> Bool {
    // Display names and paths are not identity evidence. No digest is recomputed.
    context.sliceSHA256 == source.sliceSHA256
        && context.architecture == source.architecture && context.uuid == source.uuid
}
