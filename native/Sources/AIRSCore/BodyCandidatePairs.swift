import Foundation

public extension ComparisonReport {
    /// Checks selected exact-body review candidates against admitted source snapshots.
    /// Imported fingerprints are not authenticated; omitted candidates remain unverified.
    func validateBodyCandidatePairs(baselineData: Data, currentData: Data) throws {
        try validateUniqueSymbolPairs(baselineData: baselineData, currentData: currentData)
        let rows = changes.filter { $0.matchBasis == "exact_body_candidate" }
        guard !rows.isEmpty else { return }
        guard comparison.exactBodyCandidates == true, !comparison.sameImage else {
            throw ReportError.invalidContents("Body candidates require explicit cross-image opt-in.")
        }
        let baseline = try AuditReport.decode(baselineData)
        let current = try AuditReport.decode(currentData)
        guard baseline.image.architecture == current.image.architecture,
              baseline.image.cpuSubtype == current.image.cpuSubtype else {
            throw ReportError.invalidContents("Body candidates require matching source architecture and CPU subtype.")
        }
        let oldPins = Set((comparison.manualPairs ?? []).map(\.baselineID))
        let newPins = Set((comparison.manualPairs ?? []).map(\.currentID))
        let oldGroups = admittedSymbolCandidateGroups(baseline.findings, excluding: oldPins)
        let newGroups = admittedSymbolCandidateGroups(current.findings, excluding: newPins)
        let oldBuckets = bodyCandidateBuckets(baseline.findings, excluding: oldPins, own: oldGroups, other: newGroups)
        let newBuckets = bodyCandidateBuckets(current.findings, excluding: newPins, own: newGroups, other: oldGroups)
        var oldByID: [String: Finding] = [:], newByID: [String: Finding] = [:]
        for finding in baseline.findings { oldByID[finding.id] = finding }
        for finding in current.findings { newByID[finding.id] = finding }
        for row in rows {
            guard let oldID = row.baselineID, let newID = row.currentID,
                  let old = oldByID[oldID]?.function.bodyFingerprint,
                  let new = newByID[newID]?.function.bodyFingerprint, old == new else {
                throw ReportError.invalidContents("Body pair requires both source fingerprints with equal kind, digest and instruction count.")
            }
            let key = BodyCandidateKey(old)
            guard Data(row.key.utf8) == Data(key.rowKey.utf8),
                  let before = oldBuckets[key], before.count == 1, before.eligible, before.selectedID == oldID,
                  let after = newBuckets[key], after.count == 1, after.eligible, after.selectedID == newID else {
                throw ReportError.invalidContents("Body pair is not an eligible unique source bucket after manual and symbol precedence.")
            }
        }
    }
}

private struct BodyCandidateKey: Hashable {
    let kind: String
    let digest: String
    let count: Int
    init(_ fingerprint: FunctionBodyFingerprint) {
        kind = fingerprint.kind; digest = fingerprint.sha256; count = fingerprint.instructionCount
    }
    var rowKey: String { "body:\(kind):\(digest):\(count)" }
}

private struct BodyCandidateSide {
    var count = 0
    var selectedID: String?
    var eligible = false
}

private func bodyCandidateBuckets(_ findings: [Finding], excluding pins: Set<String>,
                                  own: [Data: SymbolCandidateGroup], other: [Data: SymbolCandidateGroup]) -> [BodyCandidateKey: BodyCandidateSide] {
    var buckets: [BodyCandidateKey: BodyCandidateSide] = [:]
    for finding in findings where !pins.contains(finding.id) {
        var standalone = true // Unusable names are side-specific, ID-specific groups.
        if let name = finding.function.name, usableComparisonSymbol(name) {
            let key = Data(name.utf8)
            let ownCount = own[key]?.count ?? 0, otherCount = other[key]?.count ?? 0
            if ownCount == 1 && otherCount == 1 { continue } // Established symbols win even when their rows are omitted.
            standalone = ownCount == 1 && otherCount == 0
        }
        guard let fingerprint = finding.function.bodyFingerprint else { continue }
        let key = BodyCandidateKey(fingerprint)
        var bucket = buckets[key] ?? BodyCandidateSide()
        bucket.count += 1
        bucket.selectedID = bucket.count == 1 ? finding.id : nil
        bucket.eligible = bucket.count == 1 && standalone
        buckets[key] = bucket // Blocked symbol members still count against uniqueness.
    }
    return buckets
}
