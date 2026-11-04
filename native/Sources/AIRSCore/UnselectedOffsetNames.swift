import Foundation

public extension ComparisonReport {
    /// Binds unselected exact-offset labels to the recorded source-order representative.
    /// Source order and names are admitted report facts, not authenticated symbols.
    func validateUnselectedOffsetNames(baselineData: Data, currentData: Data) throws {
        try validateUnselectedSymbolNames(baselineData: baselineData, currentData: currentData)
        let rows = changes.filter {
            $0.matchBasis == "exact_image_offset" && $0.baselineID == nil && $0.currentID == nil
        }
        guard !rows.isEmpty else { return }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let oldFirst = try firstOffsetRepresentatives(baseline.findings)
        let newFirst = try firstOffsetRepresentatives(current.findings)
        let prefix = "offset:0x"
        for row in rows {
            guard row.key.hasPrefix(prefix),
                  let offset = UInt64(row.key.dropFirst(prefix.count), radix: 16),
                  let representative = newFirst[offset] ?? oldFirst[offset],
                  let name = representative.function.name,
                  row.functionName.utf8.elementsEqual(name.utf8) else {
                throw ReportError.invalidContents("Comparison function label contradicts its source-order offset representative.")
            }
        }
    }
}

private func firstOffsetRepresentatives(_ findings: [Finding]) throws -> [UInt64: Finding] {
    var first: [UInt64: Finding] = [:]
    for finding in findings {
        let text = finding.function.imageOffset
        guard text.hasPrefix("0x"), let offset = UInt64(text.dropFirst(2), radix: 16) else {
            throw ReportError.invalidContents("Source finding has an invalid image offset.")
        }
        // Do not sort or overwrite: the producer uses the first recorded member.
        if first[offset] == nil { first[offset] = finding }
    }
    return first
}
