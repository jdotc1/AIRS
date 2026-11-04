import Foundation

public extension ComparisonReport {
    /// Bounded decoding plus saved-report group coverage; not binary authentication.
    static func decodeWithSavedReportCoverage(_ data: Data, baselineData: Data, currentData: Data) throws -> ComparisonReport {
        guard data.count <= ReportFiles.maximumBytes else { throw ReportError.tooLarge(ReportFiles.maximumBytes) }
        let report = try decode(data)
        if report.comparison.sameImage {
            try report.validateSameImageRowCoverage(baselineData: baselineData, currentData: currentData)
        } else {
            switch report.comparison.exactBodyCandidates {
            case .some(false):
                try report.validateBodyDisabledRowCoverage(baselineData: baselineData, currentData: currentData)
            case .some(true):
                try report.validateBodyEnabledRowCoverage(baselineData: baselineData, currentData: currentData)
            case .none:
                throw ReportError.invalidContents("Cross-image group coverage requires explicit body-candidate status.")
            }
        }
        return report
    }
}
