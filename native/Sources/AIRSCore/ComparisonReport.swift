import Foundation

public struct ComparisonReport: Codable, Sendable {
    public let schemaVersion: Int
    public let reportKind: String
    public let comparison: ComparisonContext
    public let summary: ComparisonSummary
    public let changes: [ComparisonChange]
    public let limitations: [String]

    enum CodingKeys: String, CodingKey {
        case schemaVersion = "schema_version"
        case reportKind = "report_kind"
        case comparison, summary, changes, limitations
    }

    public static func decode(_ data: Data) throws -> ComparisonReport {
        let report = try JSONDecoder().decode(ComparisonReport.self, from: data)
        guard report.schemaVersion == 1, report.reportKind == "airs.diff" else {
            throw ReportError.invalidContents("Unsupported comparison format.")
        }
        let counts = [report.summary.matchedCount, report.summary.changedCount,
                      report.summary.unchangedCount, report.summary.addedCount,
                      report.summary.removedCount, report.summary.ambiguousCount]
        guard counts.allSatisfy({ $0 >= 0 }) else {
            throw ReportError.invalidContents("Comparison counts must be nonnegative.")
        }
        return report
    }
}

public struct ComparisonContext: Codable, Sendable {
    public let baselineImage: ComparisonImage
    public let currentImage: ComparisonImage
    public let sameImage: Bool
    public let modelCompatible: Bool
    public let matchingPolicy: String
    public let analysisConfigurationChanged: Bool?
    public let exactBodyCandidates: Bool?
    public let manualPairs: [ComparisonManualPair]?

    enum CodingKeys: String, CodingKey {
        case baselineImage = "baseline_image"
        case currentImage = "current_image"
        case sameImage = "same_image"
        case modelCompatible = "model_compatible"
        case matchingPolicy = "matching_policy"
        case analysisConfigurationChanged = "analysis_configuration_changed"
        case exactBodyCandidates = "exact_body_candidates"
        case manualPairs = "manual_pairs"
    }

    public init(from decoder: Decoder) throws {
        let values = try decoder.container(keyedBy: CodingKeys.self)
        baselineImage = try values.decode(ComparisonImage.self, forKey: .baselineImage)
        currentImage = try values.decode(ComparisonImage.self, forKey: .currentImage)
        sameImage = try values.decode(Bool.self, forKey: .sameImage)
        modelCompatible = try values.decode(Bool.self, forKey: .modelCompatible)
        matchingPolicy = try values.decode(String.self, forKey: .matchingPolicy)
        // Missing metadata is unavailable, never an invented false or empty value.
        analysisConfigurationChanged = values.contains(.analysisConfigurationChanged)
            ? try values.decode(Bool.self, forKey: .analysisConfigurationChanged) : nil
        exactBodyCandidates = values.contains(.exactBodyCandidates)
            ? try values.decode(Bool.self, forKey: .exactBodyCandidates) : nil
        if values.contains(.manualPairs) {
            var entries = try values.nestedUnkeyedContainer(forKey: .manualPairs)
            if let count = entries.count, count > 50_000 {
                throw ReportError.invalidContents("At most 50,000 manual comparison pairs are supported.")
            }
            var pairs: [ComparisonManualPair] = []
            var oldIDs = Set<String>(), newIDs = Set<String>()
            while !entries.isAtEnd {
                guard pairs.count < 50_000 else {
                    throw ReportError.invalidContents("Manual comparison pair limit exceeded.")
                }
                let pair = try entries.decode(ComparisonManualPair.self)
                guard oldIDs.insert(pair.baselineID).inserted,
                      newIDs.insert(pair.currentID).inserted else {
                    throw ReportError.invalidContents("Manual comparison pairs must have unique one-to-one endpoints.")
                }
                pairs.append(pair)
            }
            guard !sameImage || pairs.isEmpty else {
                throw ReportError.invalidContents("Manual comparison pairs cannot override declared exact-image matching.")
            }
            manualPairs = pairs
        } else {
            manualPairs = nil
        }
    }
}

/// Retains MacScope-style recorded pair selection, not authenticated source identity.
public struct ComparisonManualPair: Codable, Equatable, Sendable {
    public let baselineID: String
    public let currentID: String

    enum CodingKeys: String, CodingKey {
        case baselineID = "baseline_id"
        case currentID = "current_id"
    }

    private struct FieldKey: CodingKey {
        let stringValue: String
        var intValue: Int? { nil }
        init?(stringValue: String) { self.stringValue = stringValue }
        init?(intValue: Int) { return nil }
    }

    public init(from decoder: Decoder) throws {
        let fields = try decoder.container(keyedBy: FieldKey.self)
        guard Set(fields.allKeys.map(\.stringValue)) == Set(["baseline_id", "current_id"]) else {
            throw ReportError.invalidContents("Manual comparison pair requires exactly baseline_id and current_id.")
        }
        let values = try decoder.container(keyedBy: CodingKeys.self)
        baselineID = try values.decode(String.self, forKey: .baselineID)
        currentID = try values.decode(String.self, forKey: .currentID)
        for id in [baselineID, currentID] {
            let suffix = id.dropFirst("airsf-".count)
            guard id.hasPrefix("airsf-"), suffix.utf8.count == 64,
                  suffix.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
                throw ReportError.invalidContents("Manual comparison endpoints must be AIRS finding identifiers.")
            }
        }
    }
}

public struct ComparisonImage: Codable, Sendable {
    public let displayName: String
    public let uuid: String?
    public let sliceSHA256: String
    public let architecture: String

    enum CodingKeys: String, CodingKey {
        case displayName = "display_name"
        case uuid, architecture
        case sliceSHA256 = "slice_sha256"
    }
}

public struct ComparisonSummary: Codable, Sendable {
    public let matchedCount: Int
    public let changedCount: Int
    public let unchangedCount: Int
    public let addedCount: Int
    public let removedCount: Int
    public let ambiguousCount: Int

    enum CodingKeys: String, CodingKey {
        case matchedCount = "matched_count"
        case changedCount = "changed_count"
        case unchangedCount = "unchanged_count"
        case addedCount = "added_count"
        case removedCount = "removed_count"
        case ambiguousCount = "ambiguous_count"
    }
}

public struct ComparisonChange: Codable, Sendable {
    public let key: String
    public let matchBasis: String
    public let functionName: String
    public let baselineID: String?
    public let currentID: String?
    public let change: String
    public let beforeVerdict: AuditVerdict?
    public let afterVerdict: AuditVerdict?
    public let beforeScope: String?
    public let afterScope: String?
    public let notes: [String]

    enum CodingKeys: String, CodingKey {
        case key, change, notes
        case matchBasis = "match_basis"
        case functionName = "function_name"
        case baselineID = "baseline_id"
        case currentID = "current_id"
        case beforeVerdict = "before_verdict"
        case afterVerdict = "after_verdict"
        case beforeScope = "before_scope"
        case afterScope = "after_scope"
    }
}
