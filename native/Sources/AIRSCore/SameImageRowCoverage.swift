import Foundation

public extension ComparisonReport {
    /// Requires every same-image offset group in the admitted saved reports.
    /// Does not establish coverage of original binary functions or other fields.
    func validateSameImageRowCoverage(baselineData: Data, currentData: Data) throws {
        try validateCanonicalRowOrder(baselineData: baselineData, currentData: currentData)
        guard comparison.sameImage else {
            throw ReportError.invalidContents("Offset-group coverage requires same-image source reports.")
        }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        var expected = Set<String>()
        for report in [baseline, current] {
            for finding in report.findings {
                let text = finding.function.imageOffset
                guard text.hasPrefix("0x"), let offset = UInt64(text.dropFirst(2), radix: 16) else {
                    throw ReportError.invalidContents("Source finding has an invalid image offset.")
                }
                // Numeric groups collapse duplicate candidates and source spellings.
                expected.insert("offset:0x" + String(offset, radix: 16))
            }
        }
        guard Set(changes.map(\.key)) == expected else {
            throw ReportError.invalidContents("Comparison rows do not cover every saved-report offset group.")
        }
    }
}
