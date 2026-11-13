import Foundation
import AIRSCore

/// A projection has no evidence bodies. Only a bound original report can open evidence.
public struct SavedReportSummary: Decodable, Sendable {
    public struct Source: Decodable, Sendable {
        public let schema_version: Int
        public let report_kind: String
        public let generator: GeneratorInfo
        public let image: ImageInfo
        public let analysis_config: JSONValue?
    }
    public struct Counts: Decodable, Sendable {
        public let by_verdict: [String: Int]
        public let by_coverage: [String: Int]
        public let by_mode: [String: Int]
        public let by_scope: [String: Int]
    }
    public struct Row: Decodable, Identifiable, Sendable {
        public let id: String
        public let function: FunctionInfo
        public let verdict: AuditVerdict
        public let coverage: String
        public let mode: String
        public let scope: String
        public let encoding: String?
        public let checked_pcs: [String]
        public let instruction_count: Int
        public let reason_codes: [String]
        public let limitations: [String]
    }
    public struct Metadata: Decodable, Sendable {
        public let entry_count: Int
        public let entry_counts_by_mode: [String: Int]
        public let issue_count: Int
        public let issues: [InputIssue]
    }
    public struct Selection: Decodable, Sendable {
        public let requested: [String]
        public let requested_reasons: [String]?
        public let selected_count: Int
        public let omitted_count: Int
        public let original_count: Int
    }
    public struct NameSelection: Decodable, Sendable {
        public let contains: String
        public let case_sensitive: Bool
        public let normalization: String
        public let input_count: Int
        public let selected_count: Int
        public let omitted_count: Int
    }
    public let schema_version: Int
    public let report_kind: String
    public let source_report: Source
    public let summary: ReportSummary
    public let finding_counts: Counts
    public let reason_counts_by_verdict: [String: [String: Int]]
    public let findings: [Row]
    public let metadata: Metadata
    public let source_limitations: [String]
    public let limitations: [String]
    public let finding_selection: Selection?
    public let finding_name_selection: NameSelection?
    public let finding_order: String?
    public let finding_limit: SavedDetailLimit?
    public private(set) var hasAnalysisConfiguration = false
    private var admittedBytes: Data? = nil
    private enum CodingKeys: String, CodingKey {
        case schema_version, report_kind, source_report, summary, finding_counts, reason_counts_by_verdict
        case findings, metadata, source_limitations, limitations
        case finding_selection, finding_name_selection, finding_order, finding_limit
    }
    private static let optionalKeys = ["finding_selection", "finding_name_selection", "finding_order", "finding_limit"]
    private static let rowKeys = ["id", "function", "verdict", "coverage", "mode", "scope", "encoding", "checked_pcs", "instruction_count", "reason_codes", "limitations"]

    public static func decode(_ bytes: Data) throws -> Self {
        guard bytes.count <= 32 * 1_048_576 else { throw ReportError.invalidContents("Native summary admission is limited to 32 MiB of output; use an explicit finding limit or filter.") }
        let root = try CoverageJSONIdentity.parse(bytes, detailedLimits: true)
        try ProjectionAdmission.keys(root, required: ["schema_version", "report_kind", "source_report", "summary", "finding_counts", "reason_counts_by_verdict", "findings", "metadata", "source_limitations", "limitations"], optional: optionalKeys)
        try ProjectionAdmission.rejectNull(root, keys: optionalKeys)
        var value = try JSONDecoder().decode(Self.self, from: bytes)
        value.hasAnalysisConfiguration = root["source_report"]?["analysis_config"] != nil
        value.admittedBytes = bytes
        try value.validate(root: root)
        return value
    }

    private func validate(root: CoverageJSONIdentity) throws {
        try ProjectionAdmission.keys(root["source_report"], required: ["schema_version", "report_kind", "generator", "image"], optional: ["analysis_config"])
        try ProjectionAdmission.integers(root, keys: ["schema_version"])
        try ProjectionAdmission.integers(root["source_report"], keys: ["schema_version"])
        guard findings.count <= 50_000 else { throw ReportError.invalidContents("Native summary admission is limited to 50,000 finding rows.") }
        guard limitations.count <= 64, source_limitations.count <= 64 else { throw ReportError.invalidContents("Native summary admission is limited to 64 limitations per list.") }
        let countMaps = [finding_counts.by_verdict, finding_counts.by_coverage, finding_counts.by_mode, finding_counts.by_scope, metadata.entry_counts_by_mode] + Array(reason_counts_by_verdict.values)
        guard countMaps.allSatisfy({ $0.count <= 4096 }) else { throw ReportError.invalidContents("Native summary admission is limited to 4,096 entries per count map.") }
        let verdicts = AuditVerdict.allCases.map(\.rawValue)
        guard schema_version == 1, report_kind == "airs.report_summary", source_report.schema_version == 1,
              source_report.report_kind == "airs.audit", (0...50_000).contains(summary.functionCount),
              findings.count <= 50_000, Set(findings.map(\.id)).count == findings.count,
              Set(finding_counts.by_verdict.keys) == Set(verdicts), Set(reason_counts_by_verdict.keys) == Set(verdicts),
              summary.agreementCount == finding_counts.by_verdict["agreement"],
              summary.inconsistencyCount == finding_counts.by_verdict["inconsistency"],
              summary.unresolvedCount == finding_counts.by_verdict["unresolved"],
              metadata.entry_count == summary.metadataEntryCount, metadata.issue_count == metadata.issues.count,
              summary.checkedPCCount >= 0, limitations.count <= 64, source_limitations.count <= 64,
              ReviewPolicy.validDigest(source_report.image.sliceSHA256), ReviewPolicy.validDigest(source_report.image.containerSHA256),
              ["arm64", "arm64e"].contains(source_report.image.architecture) else { throw InspectionArchiveError.invalid }
        for map in [finding_counts.by_verdict, finding_counts.by_coverage, finding_counts.by_mode, finding_counts.by_scope] {
            guard map.count <= 4096, map.values.allSatisfy({ (0...50_000).contains($0) }), map.values.reduce(0, +) == summary.functionCount else { throw InspectionArchiveError.invalid }
        }
        guard metadata.entry_count >= 0, metadata.entry_count <= 200_000,
              metadata.entry_counts_by_mode.count <= 4096,
              metadata.entry_counts_by_mode.values.allSatisfy({ (0...200_000).contains($0) }),
              metadata.entry_counts_by_mode.values.reduce(0, +) == metadata.entry_count else { throw InspectionArchiveError.invalid }
        for verdict in verdicts {
            guard let counts = reason_counts_by_verdict[verdict], counts.count <= 4096,
                  counts.values.allSatisfy({ $0 > 0 && $0 <= finding_counts.by_verdict[verdict, default: 0] }) else { throw InspectionArchiveError.invalid }
        }
        guard let rawRows = root["findings"]?.array, rawRows.count == findings.count else { throw InspectionArchiveError.invalid }
        for (index, row) in findings.enumerated() {
            try ProjectionAdmission.keys(rawRows[index], required: Self.rowKeys.filter { $0 != "encoding" }, optional: ["encoding"])
            guard row.id.hasPrefix("airsf-"), ReviewPolicy.validDigest(String(row.id.dropFirst(6))), row.instruction_count >= 0,
                  row.reason_codes.count <= 4096, row.limitations.count <= 64,
                  row.checked_pcs.count <= 200_000,
                  ["compact", "dwarf_reference", "dwarf_evaluated", "none", "unavailable"].contains(row.coverage),
                  ["frame", "frameless", "dwarf", "pauth_frame", "none", "unknown"].contains(row.mode),
                  ["synchronous_call_sites", "modeled_leaf_body", "metadata_only"].contains(row.scope) else { throw InspectionArchiveError.invalid }
        }
        for row in findings {
            func address(_ text: String) throws -> UInt64 {
                guard text.hasPrefix("0x"), (1...16).contains(text.dropFirst(2).utf8.count),
                      text.dropFirst(2).utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
                      let value = UInt64(text.dropFirst(2), radix: 16) else { throw InspectionArchiveError.invalid }
                return value
            }
            let start = try address(row.function.address), end = try address(row.function.endAddress)
            let base = try address(source_report.image.preferredBase), offset = try address(row.function.imageOffset)
            guard end > start, end - start == row.function.size, start >= base, start - base == offset else { throw InspectionArchiveError.invalid }
            for pc in row.checked_pcs { let pc = try address(pc); guard pc >= start, pc < end else { throw InspectionArchiveError.invalid } }
            if let encoding = row.encoding, try address(encoding) > UInt64(UInt32.max) { throw InspectionArchiveError.invalid }
            if row.verdict != .unresolved && (row.checked_pcs.isEmpty || row.scope == "metadata_only") { throw InspectionArchiveError.invalid }
        }
        var count = summary.functionCount
        if let selection = finding_selection {
            try ProjectionAdmission.keys(root["finding_selection"], required: ["requested", "selected_count", "omitted_count", "original_count"], optional: ["requested_reasons"])
            if let stage = root["finding_selection"] { try ProjectionAdmission.rejectNull(stage, keys: ["requested_reasons"]) }
            guard selection.requested == verdicts.filter({ selection.requested.contains($0) }),
                  !selection.requested.isEmpty || selection.requested_reasons != nil,
                  selection.original_count == count else { throw InspectionArchiveError.invalid }
            if let reasons = selection.requested_reasons { try ProjectionAdmission.codes(reasons) }
            try ProjectionAdmission.integers(root["finding_selection"], keys: ["selected_count", "omitted_count", "original_count"])
            try ProjectionAdmission.stage(input: count, selected: selection.selected_count, omitted: selection.omitted_count)
            guard findings.allSatisfy({ row in
                (selection.requested.isEmpty || selection.requested.contains(row.verdict.rawValue)) &&
                (selection.requested_reasons.map { reasons in row.reason_codes.contains(where: { reasons.contains($0) }) } ?? true)
            }) else { throw InspectionArchiveError.invalid }
            count = selection.selected_count
        }
        if let names = finding_name_selection {
            try ProjectionAdmission.keys(root["finding_name_selection"], required: ["contains", "case_sensitive", "normalization", "input_count", "selected_count", "omitted_count"])
            _ = try SummaryOptions(nameContains: names.contains)
            guard names.case_sensitive, names.normalization == "none", names.input_count == count,
                  findings.allSatisfy({ Self.nameMatches($0.function.name, query: names.contains) }) else { throw InspectionArchiveError.invalid }
            try ProjectionAdmission.integers(root["finding_name_selection"], keys: ["input_count", "selected_count", "omitted_count"])
            try ProjectionAdmission.stage(input: count, selected: names.selected_count, omitted: names.omitted_count)
            count = names.selected_count
        }
        if let finding_order {
            guard finding_order == "verdict", zip(findings, findings.dropFirst()).allSatisfy({ Self.rank($0.0.verdict) <= Self.rank($0.1.verdict) }) else { throw InspectionArchiveError.invalid }
        }
        if let limit = finding_limit {
            try ProjectionAdmission.keys(root["finding_limit"], required: SavedDetailLimit.keys)
            try ProjectionAdmission.integers(root["finding_limit"], keys: SavedDetailLimit.keys)
            try limit.validate(returned: findings.count, selected: count)
            count = limit.returned_count
        }
        guard count == findings.count else { throw InspectionArchiveError.invalid }
    }

    private static func rank(_ verdict: AuditVerdict) -> Int { verdict == .inconsistency ? 0 : verdict == .unresolved ? 1 : 2 }
    private static func nameMatches(_ name: String?, query: String) -> Bool {
        // Swift String comparison normalizes canonically equivalent Unicode. The CLI does not.
        guard let name else { return false }
        return Data(name.utf8).range(of: Data(query.utf8)) != nil
    }

    /// Validate full counts, every selection stage and all projected facts against one original.
    public func bind(_ bytes: Data, projectionBytes: Data, options: SummaryOptions) throws -> AuditReport {
        guard admittedBytes == projectionBytes else { throw InspectionArchiveError.invalid }
        guard bytes.count <= 64 * 1_048_576 else { throw ReportError.invalidContents("Saved source admission is limited to 64 MiB per report.") }
        let report = try AuditReport.decode(bytes)
        let source = try CoverageJSONIdentity.parse(bytes, detailedLimits: true), projection = try CoverageJSONIdentity.parse(projectionBytes, detailedLimits: true)
        for key in ["schema_version", "report_kind", "generator", "image", "analysis_config"] {
            guard projection["source_report"]?[key] == source[key] else { throw InspectionArchiveError.invalid }
        }
        guard projection["summary"] == source["summary"], projection["source_limitations"] == source["limitations"],
              projection["metadata"]?["issues"] == source["issues"],
              finding_selection?.requested == ((options.verdicts != nil || options.reasons != nil) ? (options.verdicts ?? []).map(\.rawValue) : nil),
              finding_selection?.requested_reasons == options.reasons,
              (finding_name_selection?.contains).mapUTF8 == options.nameContains.mapUTF8,
              finding_order == (options.order == .verdict ? "verdict" : nil), finding_limit?.maximum == options.limit else { throw InspectionArchiveError.invalid }
        func counts(_ values: [String]) -> [String: Int] { values.reduce(into: [:]) { $0[$1, default: 0] += 1 } }
        let verdictCounts = Dictionary(uniqueKeysWithValues: AuditVerdict.allCases.map { verdict in (verdict.rawValue, report.findings.filter { $0.verdict == verdict }.count) })
        guard finding_counts.by_verdict == verdictCounts,
              finding_counts.by_coverage == counts(report.findings.map(\.coverage)),
              finding_counts.by_mode == counts(report.findings.map(\.mode)),
              finding_counts.by_scope == counts(report.findings.map(\.scope)),
              metadata.entry_counts_by_mode == counts(report.metadataRanges.map(\.mode)) else { throw InspectionArchiveError.invalid }
        for verdict in AuditVerdict.allCases {
            let reasons = report.findings.filter { $0.verdict == verdict }.flatMap { Set($0.reasonCodes) }
            guard reason_counts_by_verdict[verdict.rawValue] == counts(reasons) else { throw InspectionArchiveError.invalid }
        }
        var selected = report.findings.enumerated().filter { _, row in
            (options.verdicts?.contains(row.verdict) ?? true) &&
            (options.reasons.map { codes in row.reasonCodes.contains(where: { codes.contains($0) }) } ?? true)
        }
        if let selection = finding_selection, selection.selected_count != selected.count { throw InspectionArchiveError.invalid }
        if let query = options.nameContains {
            guard finding_name_selection?.input_count == selected.count else { throw InspectionArchiveError.invalid }
            selected = selected.filter { Self.nameMatches($0.element.function.name, query: query) }
            guard finding_name_selection?.selected_count == selected.count else { throw InspectionArchiveError.invalid }
        }
        if options.order == .verdict {
            selected.sort { Self.rank($0.element.verdict) == Self.rank($1.element.verdict) ? $0.offset < $1.offset : Self.rank($0.element.verdict) < Self.rank($1.element.verdict) }
        }
        if let limit = options.limit {
            guard finding_limit?.selected_count == selected.count else { throw InspectionArchiveError.invalid }
            selected = Array(selected.prefix(limit))
        }
        guard selected.map({ $0.element.id }) == findings.map(\.id), let sourceRows = source["findings"]?.array,
              let rows = projection["findings"]?.array, rows.count == selected.count else { throw InspectionArchiveError.invalid }
        for (row, original) in zip(rows, selected) {
            for key in Self.rowKeys { guard row[key] == sourceRows[original.offset][key] else { throw InspectionArchiveError.invalid } }
        }
        return report
    }
}

private extension Optional where Wrapped == String {
    var mapUTF8: Data? { map { Data($0.utf8) } }
}
