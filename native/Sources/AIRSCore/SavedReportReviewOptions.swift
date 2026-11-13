import Foundation
import Darwin

/// An immutable, one-to-one review selection. It does not assert function identity.
public struct ManualPairSelection: Sendable, Equatable {
    public static let maximumCount = 50_000
    public static let empty = ManualPairSelection()
    public let pairs: [ComparisonManualPair]

    private init() { pairs = [] }

    public init(_ entries: [ComparisonManualPair], baseline: AuditReport, current: AuditReport) throws {
        guard entries.count <= Self.maximumCount else {
            throw ReportError.invalidContents("Select at most 50,000 review pairs, including duplicate entries.")
        }
        let ordered = entries.sorted {
            $0.baselineID == $1.baselineID ? $0.currentID < $1.currentID : $0.baselineID < $1.baselineID
        }
        var canonical: [ComparisonManualPair] = []
        var baselineIDs = Set<String>(), currentIDs = Set<String>()
        for pair in ordered {
            if canonical.last == pair { continue }
            guard baselineIDs.insert(pair.baselineID).inserted else {
                throw ReportError.invalidContents("Baseline endpoint \(pair.baselineID) is already paired. Remove that pair before assigning it again.")
            }
            guard currentIDs.insert(pair.currentID).inserted else {
                throw ReportError.invalidContents("Current endpoint \(pair.currentID) is already paired. Remove that pair before assigning it again.")
            }
            canonical.append(pair)
        }
        pairs = canonical
        try validateSources(baseline: baseline, current: current)
    }

    public func validateSources(baseline: AuditReport, current: AuditReport) throws {
        guard !pairs.isEmpty else { return }
        guard baseline.image.sliceSHA256 != current.image.sliceSHA256 ||
                baseline.image.architecture != current.image.architecture else {
            throw ReportError.invalidContents("Review pairs cannot override exact-image offsets. Choose reports with different selected-slice digests or architectures.")
        }
        let oldIDs = Set(baseline.findings.map(\.id)), newIDs = Set(current.findings.map(\.id))
        guard pairs.allSatisfy({ oldIDs.contains($0.baselineID) && newIDs.contains($0.currentID) }) else {
            throw ReportError.invalidContents("A review endpoint is missing from the selected saved reports. Reopen Review Pairs for these sources.")
        }
    }

    var arguments: [String] { pairs.flatMap { ["--pair", $0.baselineID + "=" + $0.currentID] } }

    /// Manual output must prove both saved-source consistency and the submitted selection.
    public func decodeComparison(_ data: Data, baselineData: Data, currentData: Data) throws -> ComparisonReport {
        guard !pairs.isEmpty else {
            let report = try ComparisonReport.decode(data)
            guard report.comparison.manualPairs?.isEmpty != false else {
                throw ReportError.invalidContents("The comparison returned review pairs that were not submitted.")
            }
            return report
        }
        let report = try ComparisonReport.decodeWithSavedReportCoverage(data, baselineData: baselineData, currentData: currentData)
        guard report.comparison.manualPairs == pairs else {
            throw ReportError.invalidContents("The comparison returned a different review-pair selection. The previous result and draft have been retained.")
        }
        return report
    }
}

/// Includes executable, NUL terminators, environment and pointer storage, with headroom
/// for the host launcher. Oversized selections are refused as one operation, never split.
enum ReviewArgumentBudget: Sendable {
    static func validate(executable: String, arguments: [String], environment: [String: String],
                         limit: Int = Int(sysconf(_SC_ARG_MAX))) throws {
        let strings = [executable] + arguments + environment.map { $0.key + "=" + $0.value }
        var remaining = limit > 16_384 ? limit - 16_384 : 0
        for string in strings {
            let size = string.utf8.count + 1 + MemoryLayout<UnsafeRawPointer>.size
            guard size <= remaining else {
                throw ReportError.invalidContents("The review-pair request exceeds this Mac's process argument budget. Remove pairs and compare again; no pairs were truncated or submitted.")
            }
            remaining -= size
        }
    }
}

/// CLI presentation options; absence is distinct from an explicit zero/empty selection.
public struct CoverageOptions: Sendable, Equatable {
    public enum Order: String, Sendable { case count, reason }
    public let reasons: [String]?
    public let minimumCount: Int?
    public let order: Order
    public let limit: Int?

    public init(reasons: [String]? = nil, minimumCount: Int? = nil, order: Order = .count, limit: Int? = nil) throws {
        self.reasons = try SavedReportOptionValidation.reasons(reasons)
        guard minimumCount.map({ $0 > 0 }) ?? true else {
            throw ReportError.invalidContents("Minimum reason count must be a positive integer that fits this Mac's integer range.")
        }
        try SavedReportOptionValidation.limit(limit)
        self.minimumCount = minimumCount; self.order = order; self.limit = limit
    }
    var arguments: [String] {
        var result = (reasons ?? []).flatMap { ["--reason", $0] }
        if let minimumCount { result += ["--minimum-count", String(minimumCount)] }
        if order == .reason { result += ["--sort", order.rawValue] }
        if let limit { result += ["--limit", String(limit)] }
        return result
    }
}

public struct SummaryOptions: Sendable, Equatable {
    public enum Order: String, Sendable { case source, verdict }
    public let verdicts: [AuditVerdict]?
    public let reasons: [String]?
    public let nameContains: String?
    public let order: Order
    public let limit: Int?

    public init(verdicts: [AuditVerdict]? = nil, reasons: [String]? = nil, nameContains: String? = nil,
                order: Order = .source, limit: Int? = nil) throws {
        guard verdicts?.isEmpty != true else { throw ReportError.invalidContents("Select at least one finding verdict.") }
        self.verdicts = verdicts.map { values in AuditVerdict.allCases.filter { values.contains($0) } }
        self.reasons = try SavedReportOptionValidation.reasons(reasons)
        if let nameContains {
            guard !nameContains.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty,
                  nameContains.utf8.count <= 256,
                  !nameContains.utf8.contains(where: { $0 < 32 || $0 == 127 }) else {
                throw ReportError.invalidContents("Name query must be nonblank literal UTF-8 text of 1–256 bytes without ASCII controls.")
            }
        }
        try SavedReportOptionValidation.limit(limit)
        self.nameContains = nameContains; self.order = order; self.limit = limit
    }
    var arguments: [String] {
        var result = (verdicts ?? []).flatMap { ["--verdict", $0.rawValue] }
        result += (reasons ?? []).flatMap { ["--reason", $0] }
        if let nameContains { // One token: argparse would read a separate value that starts with "-" as an option.
            result += ["--name-contains=" + nameContains] }
        if order == .verdict { result += ["--sort", order.rawValue] }
        if let limit { result += ["--limit", String(limit)] }
        return result
    }
}

public enum SavedReportOptionValidation {
    public static func reasons(_ values: [String]?) throws -> [String]? {
        guard let values else { return nil }
        guard values.count <= 32 else { throw ReportError.invalidContents("Select at most 32 reason codes, including duplicate entries.") }
        // An empty list has no CLI spelling. Refuse instead of silently selecting all reasons.
        guard !values.isEmpty else { throw ReportError.invalidContents("Select at least one reason code, or clear the reason filter.") }
        guard values.allSatisfy({ value in
            let bytes = Array(value.utf8)
            return (1...128).contains(bytes.count) && (97...122).contains(bytes[0]) &&
                bytes.dropFirst().allSatisfy { (97...122).contains($0) || (48...57).contains($0) || $0 == 95 }
        }) else { throw ReportError.invalidContents("Reason codes must match ASCII [a-z][a-z0-9_]{0,127}.") }
        return Array(Set(values)).sorted()
    }
    public static func limit(_ value: Int?) throws {
        guard value.map({ (0...200_000).contains($0) }) ?? true else {
            throw ReportError.invalidContents("Detail limit must be an integer from 0 to 200,000; leave it blank for all details.")
        }
    }
}

/// Input budgets count duplicates. Decode one source at a time before staging or launch.
public enum SavedReportInputBudget {
    public static let maximumReports = 128
    public static let maximumBytes = 128 * 1_048_576
    public static let maximumFindings = 200_000
    public static func validateCounts(reportCount: Int, byteCount: Int, findingCount: Int) throws {
        guard (1...maximumReports).contains(reportCount) else { throw ReportError.invalidContents("Choose 1–128 saved reports; duplicate inputs count toward the 128-report limit.") }
        guard (0...maximumBytes).contains(byteCount) else { throw ReportError.invalidContents("Saved report inputs exceed the 128 MiB total size limit. Remove reports before applying.") }
        guard (0...maximumFindings).contains(findingCount) else { throw ReportError.invalidContents("Saved report inputs exceed the 200,000-finding limit, including duplicates. Remove reports before applying.") }
    }
    public static func validate(_ reports: [Data]) throws {
        try validateCounts(reportCount: reports.count, byteCount: 0, findingCount: 0)
        var bytes = 0, findings = 0
        for data in reports {
            guard data.count <= 64 * 1_048_576 else { throw ReportError.invalidContents("A saved report exceeds the 64 MiB per-report size limit.") }
            bytes += data.count
            try validateCounts(reportCount: reports.count, byteCount: bytes, findingCount: findings)
            let report = try AuditReport.decode(data)
            guard report.findings.count <= 50_000 else { throw ReportError.invalidContents("A saved report exceeds the 50,000-finding per-report limit.") }
            findings += report.findings.count
            try validateCounts(reportCount: reports.count, byteCount: bytes, findingCount: findings)
        }
    }
}
