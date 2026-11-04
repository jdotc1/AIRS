import Foundation
import CoreFoundation

public extension ComparisonReport {
    /// Adds configuration/model prerequisites to the reused endpoint-binding path.
    /// Compatibility is not authentication or change-signature verification.
    func validateManualPairCompatibility(baselineData: Data, currentData: Data) throws {
        try validateManualPairEndpoints(baselineData: baselineData, currentData: currentData)
        let baseline = try savedAnalysisConfiguration(baselineData)
        let current = try savedAnalysisConfiguration(currentData)
        // Reuse the host's structural NSDictionary configuration comparison.
        // Two legacy omissions compare equal; absence is not a default config.
        let changed = baseline != current
        if let reported = comparison.analysisConfigurationChanged, reported != changed {
            throw ReportError.invalidContents("Configuration-change status contradicts the selected source reports.")
        }
        if changed || !comparison.modelCompatible {
            guard changes.allSatisfy({ $0.matchBasis != "manual_review" || $0.change == "ambiguous" }) else {
                throw ReportError.invalidContents("Manual review rows require ambiguous classification when source configurations or models differ.")
            }
        }
    }
}

private func savedAnalysisConfiguration(_ data: Data) throws -> NSDictionary? {
    // The endpoint validator has already bounded and admitted both source reports.
    guard let object = try JSONSerialization.jsonObject(with: data) as? NSDictionary else {
        throw ReportError.invalidContents("Expected a source audit-report object.")
    }
    guard let raw = object["analysis_config"] else { return nil }
    guard let configuration = raw as? NSDictionary, let limits = configuration["limits"] as? NSDictionary else {
        throw ReportError.invalidContents("Analysis configuration requires an object of limits.")
    }
    let integerTypes: Set<String> = ["c", "s", "i", "l", "q", "C", "S", "I", "L", "Q"]
    for value in limits.allValues {
        guard let number = value as? NSNumber,
              CFGetTypeID(number) != CFBooleanGetTypeID(),
              integerTypes.contains(String(cString: number.objCType)),
              UInt64(number.stringValue) != nil else {
            throw ReportError.invalidContents("Analysis limits must be native-representable nonnegative integers, not Boolean or floating values.")
        }
    }
    return configuration
}
