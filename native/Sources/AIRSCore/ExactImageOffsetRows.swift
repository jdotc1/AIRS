import Foundation

public extension ComparisonReport {
    /// Validates declared exact-image groups, not original bytes or source completeness.
    /// Offset authority follows the host contract; other matching bases remain separate.
    func validateExactImageOffsetRows(baselineData: Data, currentData: Data) throws {
        try validateMatchedChangeLabels(baselineData: baselineData, currentData: currentData)
        if !comparison.sameImage {
            guard changes.allSatisfy({ $0.matchBasis != "exact_image_offset" }) else {
                throw ReportError.invalidContents("Different source images cannot claim exact-image offset matching.")
            }
            return
        }
        guard changes.allSatisfy({ $0.matchBasis == "exact_image_offset" }) else {
            throw ReportError.invalidContents("Same-image comparison rows require exact-image offset authority.")
        }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let oldGroups = try exactOffsetGroups(baseline.findings)
        let newGroups = try exactOffsetGroups(current.findings)
        for row in changes {
            let prefix = "offset:0x"
            guard row.key.hasPrefix(prefix), let offset = UInt64(row.key.dropFirst(prefix.count), radix: 16),
                  row.key == prefix + String(offset, radix: 16) else {
                throw ReportError.invalidContents("Exact-image rows require canonical numeric offset keys.")
            }
            let old = oldGroups[offset] ?? ExactOffsetGroup()
            let new = newGroups[offset] ?? ExactOffsetGroup()
            guard old.count > 0 || new.count > 0,
                  row.baselineID == old.selectedID, row.currentID == new.selectedID else {
                throw ReportError.invalidContents("Exact-image row selections contradict their source offset groups.")
            }
            let expected: String?
            if old.count > 1 || new.count > 1 { expected = "ambiguous" }
            else if old.count == 0 { expected = "added" }
            else if new.count == 0 { expected = "removed" }
            else { expected = nil } // Unique pairs already passed observation-label checks.
            if let expected, row.change != expected {
                throw ReportError.invalidContents("Exact-image group multiplicity contradicts its row classification.")
            }
        }
    }
}

private struct ExactOffsetGroup {
    var count = 0
    var selectedID: String?
}

private func exactOffsetGroups(_ findings: [Finding]) throws -> [UInt64: ExactOffsetGroup] {
    var groups: [UInt64: ExactOffsetGroup] = [:]
    for finding in findings {
        let text = finding.function.imageOffset
        guard text.hasPrefix("0x"), let offset = UInt64(text.dropFirst(2), radix: 16) else {
            throw ReportError.invalidContents("Source finding has an invalid image offset.")
        }
        var group = groups[offset] ?? ExactOffsetGroup()
        group.count += 1
        group.selectedID = group.count == 1 ? finding.id : nil
        groups[offset] = group
    }
    return groups
}
