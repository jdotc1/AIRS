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
