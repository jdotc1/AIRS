import Foundation

public extension ComparisonReport {
    /// Verifies manual row labels against admitted source findings, not binary bytes.
    /// Matching, authenticity, nonmanual rows and summary integrity remain separate.
    func validateManualPairChanges(baselineData: Data, currentData: Data) throws {
        try validateManualPairCompatibility(baselineData: baselineData, currentData: currentData)
        let before = try AuditReport.decode(baselineData)
        let after = try AuditReport.decode(currentData)
        // Unknown model labels are still wire facts. Swift canonical Unicode
        // equivalence must not collapse distinct Python model identities.
        let exactModels = before.generator.analysisModelVersion.utf8.elementsEqual(after.generator.analysisModelVersion.utf8)
            && before.image.architecture.utf8.elementsEqual(after.image.architecture.utf8)
        guard comparison.modelCompatible == exactModels else {
            throw ReportError.invalidContents("Model compatibility contradicts exact source model labels.")
        }
        let configurationsDiffer = try admittedComparisonConfigurationsDiffer(baselineData: baselineData, currentData: currentData)
        var oldByID: [String: Finding] = [:], newByID: [String: Finding] = [:]
        for finding in before.findings { oldByID[finding.id] = finding }
        for finding in after.findings { newByID[finding.id] = finding }
        for row in changes where row.matchBasis == "manual_review" {
            guard let oldID = row.baselineID, let newID = row.currentID,
                  let old = oldByID[oldID], let new = newByID[newID] else {
                throw ReportError.invalidContents("Manual change endpoints are unavailable.")
            }
            let expected: String
            if !exactModels || configurationsDiffer {
                expected = "ambiguous"
            } else {
                expected = try FindingObservationSignature(old) == FindingObservationSignature(new) ? "unchanged" : "changed"
            }
            guard row.change == expected else {
                throw ReportError.invalidContents("Manual row change label contradicts its selected source finding signatures.")
            }
        }
    }
}

/// Internal reuse only: both inputs must already pass configuration admission.
func admittedComparisonConfigurationsDiffer(baselineData: Data, currentData: Data) throws -> Bool {
    try manualChangeConfiguration(baselineData) != manualChangeConfiguration(currentData)
}

private func manualChangeConfiguration(_ data: Data) throws -> NSDictionary? {
    // Compatibility has already admitted the bounded original configuration.
    guard let object = try JSONSerialization.jsonObject(with: data) as? NSDictionary else {
        throw ReportError.invalidContents("Expected a saved source report object.")
    }
    return object["analysis_config"] as? NSDictionary
}

private struct ManualRelativeAddress: Equatable {
    let belowStart: Bool
    let magnitude: UInt64

    init(_ address: UInt64, start: UInt64) {
        belowStart = address < start
        magnitude = belowStart ? start - address : address - start
    }
}

private func manualAddress(_ text: String) throws -> UInt64 {
    guard text.hasPrefix("0x"), let value = UInt64(text.dropFirst(2), radix: 16) else {
        throw ReportError.invalidContents("Invalid manual source address.")
    }
    return value
}

private func manualEvidenceText(_ value: JSONValue?) throws -> Data? {
    switch value {
    case nil, .null: return nil
    case .string(let text): return Data(text.utf8)
    default: throw ReportError.invalidContents("Manual evidence values require schema 1 strings or null.")
    }
}

/// Adapts the donor comparator's observation signature while preserving AIRS's
/// raw encoding text, negative relative evidence addresses and exact wire strings.
struct FindingObservationSignature: Equatable {
    private struct EvidenceSignature: Equatable {
        let code: Data
        let expected: Data?
        let observed: Data?
        let address: ManualRelativeAddress?
    }

    private let verdict: AuditVerdict
    private let coverage: String
    private let mode: String
    private let scope: String
    private let encoding: Data?
    private let reasons: [Data]
    private let checkedPCs: [ManualRelativeAddress]
    private let evidence: [EvidenceSignature]

    init(_ finding: Finding) throws {
        let start = try manualAddress(finding.function.address)
        verdict = finding.verdict; coverage = finding.coverage
        mode = finding.mode; scope = finding.scope
        encoding = finding.encoding.map { Data($0.utf8) }
        reasons = finding.reasonCodes.map { Data($0.utf8) }.sorted { $0.lexicographicallyPrecedes($1) }
        checkedPCs = try finding.checkedPCs.map { ManualRelativeAddress(try manualAddress($0), start: start) }
        evidence = try finding.evidence.map { item in
            EvidenceSignature(code: Data(item.code.utf8), expected: try manualEvidenceText(item.expected),
                observed: try manualEvidenceText(item.observed),
                address: try item.address.map { ManualRelativeAddress(try manualAddress($0), start: start) })
        }
    }
}
