import Foundation

public extension ComparisonReport {
    /// Checks evidence for selected two-sided symbol candidates, not function identity.
    /// One-sided symbol groups, other bases and source completeness remain separate.
    func validateUniqueSymbolPairs(baselineData: Data, currentData: Data) throws {
        try validateExactImageOffsetRows(baselineData: baselineData, currentData: currentData)
        guard !comparison.sameImage else { return } // Exact-offset authority already enforced.
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        let oldPins = Set((comparison.manualPairs ?? []).map(\.baselineID))
        let newPins = Set((comparison.manualPairs ?? []).map(\.currentID))
        let oldGroups = admittedSymbolCandidateGroups(baseline.findings, excluding: oldPins)
        let newGroups = admittedSymbolCandidateGroups(current.findings, excluding: newPins)
        var oldByID: [String: Finding] = [:], newByID: [String: Finding] = [:]
        for finding in baseline.findings { oldByID[finding.id] = finding }
        for finding in current.findings { newByID[finding.id] = finding }
        for row in changes where row.matchBasis == "unique_symbol" {
            guard let oldID = row.baselineID, let newID = row.currentID else { continue }
            guard let old = oldByID[oldID], let new = newByID[newID],
                  let oldName = old.function.name, let newName = new.function.name,
                  usableComparisonSymbol(oldName), usableComparisonSymbol(newName) else {
                throw ReportError.invalidContents("Selected symbol candidates require usable source names.")
            }
            let name = Data(oldName.utf8)
            var key = Data("symbol:".utf8); key.append(contentsOf: oldName.utf8)
            guard name == Data(newName.utf8), Data(row.key.utf8) == key,
                  let before = oldGroups[name], before.count == 1, before.selectedID == oldID,
                  let after = newGroups[name], after.count == 1, after.selectedID == newID else {
                throw ReportError.invalidContents("Selected symbol pair is not unique under its exact source name after manual pins.")
            }
        }
    }
}

struct SymbolCandidateGroup {
    var count = 0
    var selectedID: String?
}

func admittedSymbolCandidateGroups(_ findings: [Finding], excluding pins: Set<String>) -> [Data: SymbolCandidateGroup] {
    var groups: [Data: SymbolCandidateGroup] = [:]
    // Only validated manual pins precede the host symbol phase. Imported body or
    // other selected rows must not hide a duplicate source-name blocker.
    for finding in findings where !pins.contains(finding.id) {
        guard let name = finding.function.name, usableComparisonSymbol(name) else { continue }
        let key = Data(name.utf8)
        var group = groups[key] ?? SymbolCandidateGroup()
        group.count += 1; group.selectedID = group.count == 1 ? finding.id : nil
        groups[key] = group
    }
    return groups
}

/// The host's broader generated-name exclusions remain authoritative. Raw UTF-8
/// prefixes preserve Python code-point behavior at combining-character boundaries.
func usableComparisonSymbol(_ name: String) -> Bool {
    let bytes = Array(name.utf8)
    guard !bytes.isEmpty, bytes != Array("_entry".utf8), bytes != Array("__text".utf8) else { return false }
    for prefix in ["sub_", "<", "0x", "0X"] where bytes.starts(with: prefix.utf8) { return false }
    for prefix in ["loc_", "unk_", "off_", "nullsub_"] where bytes.starts(with: prefix.utf8) {
        var suffix = bytes.dropFirst(prefix.utf8.count)
        if suffix.starts(with: [48, 120]) || suffix.starts(with: [48, 88]) { suffix = suffix.dropFirst(2) }
        if !suffix.isEmpty && suffix.allSatisfy({ (48...57).contains($0) || (65...70).contains($0) || (97...102).contains($0) }) { return false }
    }
    return true
}
