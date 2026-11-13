import Foundation
import AIRSCore
import EntitlementDiffCore

/// Decoder for src/airs/coverage.py, not a second analyzer or deduplicator.
public struct CoverageInventory:Decodable,Sendable {
    public struct Summary:Decodable,Sendable {
        public let duplicate_report_count:Int
        public let function_count:Int
        public let agreement_count:Int
        public let inconsistency_count:Int
        public let unresolved_count:Int
        public let input_report_count:Int
        public let unique_image_model_config_count:Int
        public let conflicting_report_count:Int
    }
    public struct Record:Decodable,Identifiable,Sendable {
        public var id:Int {index}
        public let index:Int
        public let image:Image
        public let model:String
        public let summary:ReportSummary
        public let duplicate_of:Int?
    }
    public struct Image:Decodable,Sendable {
        public let display_name:String
        public let slice_sha256:String
        public let architecture:String
        public let cpu_subtype:Int
        public let uuid:String?
    }
    public struct Reason:Decodable,Identifiable,Sendable {
        public var id:String {Data(reason.utf8).base64EncodedString()}
        public let reason:String
        public let count:Int
        public let examples:[Example]
    }
    public struct Example:Decodable,Identifiable,Sendable {
        public var id:String {String(report_index)+":"+finding_id}
        public let report_index:Int
        public let finding_id:String
        public let function_name:String?
        /// Function-entry preferred VM, not a checked-PC observation claim.
        public let pc:String
        public let scope:String
        public let mode:String
    }
    public let schema_version:Int
    public let report_kind:String
    public let status:String
    public let summary:Summary
    public let reports:[Record]
    public let conflicting_report_indices:[Int]
    public let models:[String:Int]
    public let reasons:[Reason]
    public let limitations:[String]
    public private(set) var selection: CoverageSelectionMetadata? = nil
    private var configurationIdentities:[CoverageJSONIdentity]=[]
    private enum CodingKeys:String,CodingKey {case schema_version,report_kind,status,summary,reports,conflicting_report_indices,models,reasons,limitations}
    public struct VerdictRatio:Sendable {
        public let resolvedNumerator:Int
        public let functionDenominator:Int
    }
    /// This ratio concerns verdict counts only. Never combine different models,
    /// configurations, CPU scopes, unknown configurations or conflicting variants.
    public var compatibleVerdictRatio:VerdictRatio? {
        let inputs=reports.filter{$0.duplicate_of == nil}
        guard status == "complete",let first=inputs.first,configurationIdentities.count == reports.count,configurationIdentities[first.index] != .null,summary.function_count > 0,
              inputs.allSatisfy({$0.model.utf8.elementsEqual(first.model.utf8) && configurationIdentities[$0.index] == configurationIdentities[first.index] && $0.image.architecture == first.image.architecture && $0.image.cpu_subtype == first.image.cpu_subtype}) else {return nil}
        return .init(resolvedNumerator:summary.agreement_count+summary.inconsistency_count,functionDenominator:summary.function_count)
    }
    public func configurationLabel(for record:Record)->String {
        guard configurationIdentities.indices.contains(record.index),configurationIdentities[record.index] != .null else {return "Configuration not recorded"}
        let first=configurationIdentities.firstIndex(of:configurationIdentities[record.index]) ?? record.index
        return "Configuration identity group \(first + 1)"
    }
    public static func decode(_ bytes:Data) throws -> Self {
        guard bytes.count <= 32*1_048_576 else {throw ReportError.invalidContents("Native coverage admission is limited to 32 MiB of output; reduce selected reason details and apply again.")}
        let root=try CoverageJSONIdentity.parse(bytes, detailedLimits: true)
        try ProjectionAdmission.keys(root, required: ["schema_version","report_kind","status","summary","reports","conflicting_report_indices","models","reasons","limitations"], optional: CoverageSelectionMetadata.keys)
        var value=try JSONDecoder().decode(Self.self,from:bytes)
        guard let records=root["reports"]?.array else {throw InspectionArchiveError.invalid}
        value.configurationIdentities=records.map{$0["analysis_config"] ?? .null}
        if value.reasons.count > 4096 { throw ReportError.invalidContents("Native coverage admission is limited to 4,096 reason rows; use an explicit detail limit or reason filter.") }
        if value.reports.count > 128 { throw ReportError.invalidContents("Native coverage admission is limited to 128 report records.") }
        if value.models.count > 128 { throw ReportError.invalidContents("Native coverage admission is limited to 128 models.") }
        if value.limitations.count > 64 { throw ReportError.invalidContents("Native coverage admission is limited to 64 limitations.") }
        try value.validate()
        if CoverageSelectionMetadata.keys.contains(where: { root[$0] != nil }) {
            let selection = try JSONDecoder().decode(CoverageSelectionMetadata.self, from: bytes)
            try selection.validate(root: root, rows: value.reasons)
            value.selection = selection
        }
        return value
    }
    private func validate() throws {
        func nonnegative(_ s:ReportSummary)->Bool {
            [s.functionCount,s.agreementCount,s.inconsistencyCount,s.unresolvedCount,s.metadataEntryCount,s.checkedPCCount].allSatisfy{$0 >= 0 && $0 <= 10_000_000} && s.functionCount <= 50_000 && s.agreementCount+s.inconsistencyCount+s.unresolvedCount == s.functionCount
        }
        guard schema_version == 1,report_kind == "airs.coverage_inventory",["complete","conflicting_reports"].contains(status),reports.count <= 128,configurationIdentities.count == reports.count,reasons.count <= 4096,models.count <= 128,limitations.count <= 64,
              summary.input_report_count == reports.count,summary.function_count >= 0,summary.function_count <= 200_000,
              [summary.agreement_count,summary.inconsistency_count,summary.unresolved_count,summary.duplicate_report_count,summary.unique_image_model_config_count,summary.conflicting_report_count].allSatisfy({$0 >= 0 && $0 <= 200_000}),
              summary.agreement_count+summary.inconsistency_count+summary.unresolved_count == summary.function_count,
              limitations.allSatisfy({$0.utf8.count <= 16_384}) else {throw InspectionArchiveError.invalid}
        var groups:[[Record]]=[],modelCounts:[String:Int]=[:],totals=[0,0,0,0],duplicates=0,inputFindings=0
        func sameKey(_ a:Record,_ b:Record)->Bool {
            a.image.slice_sha256 == b.image.slice_sha256 && a.image.architecture == b.image.architecture && a.image.cpu_subtype == b.image.cpu_subtype && a.model.utf8.elementsEqual(b.model.utf8) && configurationIdentities[a.index] == configurationIdentities[b.index]
        }
        for (index,r) in reports.enumerated() {
            guard r.index == index,ReviewPolicy.validDigest(r.image.slice_sha256),["arm64","arm64e"].contains(r.image.architecture),r.image.cpu_subtype >= 0,
                  r.image.uuid.map({UUID(uuidString:$0) != nil}) ?? true,!r.model.isEmpty,r.model.utf8.count <= 256,r.image.display_name.utf8.count <= 4096,nonnegative(r.summary) else {throw InspectionArchiveError.invalid}
            inputFindings += r.summary.functionCount
            guard inputFindings <= 200_000 else {throw InspectionArchiveError.limit}
            if let earlier=r.duplicate_of {
                guard earlier >= 0,earlier < index,reports[earlier].duplicate_of == nil,sameKey(r,reports[earlier]),
                      r.summary.functionCount == reports[earlier].summary.functionCount,r.summary.agreementCount == reports[earlier].summary.agreementCount,
                      r.summary.inconsistencyCount == reports[earlier].summary.inconsistencyCount,r.summary.unresolvedCount == reports[earlier].summary.unresolvedCount,
                      r.summary.checkedPCCount == reports[earlier].summary.checkedPCCount,r.summary.metadataEntryCount == reports[earlier].summary.metadataEntryCount else {throw InspectionArchiveError.invalid}
                duplicates += 1;continue
            }
            if let group=groups.firstIndex(where:{$0.first.map{sameKey($0,r)} ?? false}) {groups[group].append(r)} else {groups.append([r])}
            modelCounts[r.model,default:0] += 1
            totals[0] += r.summary.functionCount;totals[1] += r.summary.agreementCount;totals[2] += r.summary.inconsistencyCount;totals[3] += r.summary.unresolvedCount
        }
        let conflicts=groups.filter{$0.count > 1}.flatMap{$0.map(\.index)}.sorted()
        guard conflicts == conflicting_report_indices,summary.conflicting_report_count == conflicts.count,status == (conflicts.isEmpty ? "complete":"conflicting_reports"),summary.duplicate_report_count == duplicates,summary.unique_image_model_config_count == groups.count,models == modelCounts,
              totals == [summary.function_count,summary.agreement_count,summary.inconsistency_count,summary.unresolved_count],
              Set(reasons.map{Data($0.reason.utf8)}).count == reasons.count else {throw InspectionArchiveError.invalid}
        for reason in reasons {
            guard !reason.reason.isEmpty,reason.reason.utf8.count <= 4096,reason.count > 0,reason.count <= summary.unresolved_count,!reason.examples.isEmpty,reason.examples.count <= min(8,reason.count),Set(reason.examples.map(\.id)).count == reason.examples.count else {throw InspectionArchiveError.invalid}
            for e in reason.examples {
                guard reports.indices.contains(e.report_index),reports[e.report_index].duplicate_of == nil,e.finding_id.hasPrefix("airsf-"),ReviewPolicy.validDigest(String(e.finding_id.dropFirst(6))),e.pc.hasPrefix("0x"),e.pc.count <= 18,UInt64(e.pc.dropFirst(2),radix:16) != nil,
                      ["synchronous_call_sites","modeled_leaf_body","metadata_only"].contains(e.scope),["frame","frameless","dwarf","pauth_frame","none","unknown"].contains(e.mode),(e.function_name?.utf8.count ?? 0) <= 4096 else {throw InspectionArchiveError.invalid}
            }
        }
    }
    public func bindSource(_ sourceBytes: Data, at index: Int) throws -> AuditReport {
        guard reports.indices.contains(index), configurationIdentities.count == reports.count else { throw InspectionArchiveError.invalid }
        guard sourceBytes.count <= 64 * 1_048_576 else { throw ReportError.invalidContents("Saved source admission is limited to 64 MiB per report.") }
        let record = reports[index], report = try AuditReport.decode(sourceBytes)
        let root = try CoverageJSONIdentity.parse(sourceBytes, detailedLimits: true)
        guard report.image.sliceSHA256 == record.image.slice_sha256,
              report.image.architecture == record.image.architecture, report.image.cpuSubtype == record.image.cpu_subtype,
              report.image.uuid == record.image.uuid, ProjectionAdmission.same(report.image.displayName, record.image.display_name),
              ProjectionAdmission.same(report.generator.analysisModelVersion, record.model),
              (root["analysis_config"] ?? .null) == configurationIdentities[index],
              report.summary.functionCount == record.summary.functionCount,
              report.summary.agreementCount == record.summary.agreementCount,
              report.summary.inconsistencyCount == record.summary.inconsistencyCount,
              report.summary.unresolvedCount == record.summary.unresolvedCount,
              report.summary.metadataEntryCount == record.summary.metadataEntryCount,
              report.summary.checkedPCCount == record.summary.checkedPCCount else { throw InspectionArchiveError.invalid }
        return report
    }

    /// Validate selection claims against all retained inputs, decoding one input at a time.
    public func validateSources(_ sources: [Data], options: CoverageOptions) throws {
        guard sources.count == reports.count, configurationIdentities.count == reports.count else { throw InspectionArchiveError.invalid }
        guard selection?.reason_selection?.requested == options.reasons,
              selection?.reason_frequency_selection?.minimum_count == options.minimumCount,
              selection?.reason_order == (options.order == .reason ? "reason" : nil),
              selection?.reason_limit?.maximum == options.limit else { throw InspectionArchiveError.invalid }
        var counts: [Data: Int] = [:]
        for (index, bytes) in sources.enumerated() {
            let record = reports[index]
            var duplicate: Int?
            let peers = reports.prefix(index).filter {
                $0.duplicate_of == nil && $0.image.slice_sha256 == record.image.slice_sha256 &&
                $0.image.architecture == record.image.architecture && $0.image.cpu_subtype == record.image.cpu_subtype &&
                ProjectionAdmission.same($0.model, record.model) && configurationIdentities[$0.index] == configurationIdentities[index]
            }
            if !peers.isEmpty {
                // Retain a flat comparison buffer, releasing each decoded input before the next.
                let signature = try Self.duplicateBytes(bytes)
                for peer in peers {
                    if try sources[peer.index] == bytes || Self.duplicateBytes(sources[peer.index]) == signature {
                        duplicate = peer.index; break
                    }
                }
            }
            guard duplicate == record.duplicate_of else { throw InspectionArchiveError.invalid }
            let source = try bindSource(bytes, at: index)
            if duplicate != nil { continue }
            for finding in source.findings where finding.verdict == .unresolved {
                for reason in Set(finding.reasonCodes.map { Data($0.utf8) }) { counts[reason, default: 0] += 1 }
            }
            let findingsByID = Dictionary(uniqueKeysWithValues: source.findings.map { ($0.id, $0) })
            for row in reasons {
                for example in row.examples where example.report_index == index {
                    guard let finding = findingsByID[example.finding_id],
                          finding.verdict == .unresolved, finding.function.address == example.pc,
                          finding.function.name.map({ Data($0.utf8) }) == example.function_name.map({ Data($0.utf8) }),
                          finding.scope == example.scope, finding.mode == example.mode,
                          finding.reasonCodes.contains(where: { ProjectionAdmission.same($0, row.reason) }) else { throw InspectionArchiveError.invalid }
                }
            }
        }
        var selected = counts.keys.map { String(decoding: $0, as: UTF8.self) }.filter { options.reasons?.contains($0) ?? true }
        if let requested = options.reasons {
            guard selection?.reason_selection?.matched == requested.filter({ counts[Data($0.utf8)] != nil }),
                  selection?.reason_selection?.unmatched == requested.filter({ counts[Data($0.utf8)] == nil }) else { throw InspectionArchiveError.invalid }
        }
        if let minimum = options.minimumCount {
            let input = selected.count
            selected = selected.filter { counts[Data($0.utf8), default: 0] >= minimum }
            guard selection?.reason_frequency_selection?.input_count == input,
                  selection?.reason_frequency_selection?.selected_count == selected.count else { throw InspectionArchiveError.invalid }
        }
        selected.sort {
            if options.order == .reason || counts[Data($0.utf8)] == counts[Data($1.utf8)] { return $0.utf8.lexicographicallyPrecedes($1.utf8) }
            return counts[Data($0.utf8), default: 0] > counts[Data($1.utf8), default: 0]
        }
        if let limit = options.limit {
            guard selection?.reason_limit?.selected_count == selected.count else { throw InspectionArchiveError.invalid }
            selected = Array(selected.prefix(limit))
        }
        guard reasons.map({ Data($0.reason.utf8) }) == selected.map({ Data($0.utf8) }),
              reasons.allSatisfy({ counts[Data($0.reason.utf8)] == $0.count }) else { throw InspectionArchiveError.invalid }
    }

    private static func duplicateBytes(_ bytes: Data) throws -> Data {
        let root = try CoverageJSONIdentity.parse(bytes, detailedLimits: true)
        var result = Data()
        func field(_ tag: UInt8, _ bytes: Data) {
            result.append(tag); result.append(contentsOf: String(bytes.count).utf8); result.append(58); result.append(bytes)
        }
        func append(_ value: CoverageJSONIdentity) {
            switch value {
            case .null: result.append(110)
            case .boolean(let b): result.append(b ? 116 : 102)
            case .string(let bytes): field(115, bytes)
            case .number(let number): field(100, Data(number.utf8))
            case .array(let array):
                result.append(91); for value in array { append(value) }; result.append(93)
            case .object(let object):
                result.append(123)
                for key in object.keys.sorted(by: { $0.lexicographicallyPrecedes($1) }) { field(107, key); if let value = object[key] { append(value) } }
                result.append(125)
            }
        }
        for key in ["findings", "summary", "metadata_ranges", "issues"] { append(root[key] ?? .null) }
        return result
    }

    /// Resolve only a user-selected saved report; no path inference or live read.
    /// The inventory has no original-report digest, so this proves a matching
    /// referenced observation, not the original file's byte identity.
    public func resolve(_ example:Example,reason:String,sourceBytes:Data) throws -> (AuditReport,Finding) {
        guard let category=reasons.first(where:{$0.reason.utf8.elementsEqual(reason.utf8)}),let example=category.examples.first(where:{$0.id == example.id}),reports.indices.contains(example.report_index),configurationIdentities.count == reports.count else {throw InspectionArchiveError.invalid}
        let record=reports[example.report_index],report=try AuditReport.decode(sourceBytes)
        let config=try CoverageJSONIdentity.parse(sourceBytes, detailedLimits: true)["analysis_config"] ?? .null
        guard report.image.sliceSHA256 == record.image.slice_sha256,report.image.architecture == record.image.architecture,report.image.cpuSubtype == record.image.cpu_subtype,report.image.uuid == record.image.uuid,
              report.generator.analysisModelVersion.utf8.elementsEqual(record.model.utf8),config == configurationIdentities[record.index],
              report.summary.functionCount == record.summary.functionCount,report.summary.agreementCount == record.summary.agreementCount,report.summary.inconsistencyCount == record.summary.inconsistencyCount,report.summary.unresolvedCount == record.summary.unresolvedCount,report.summary.metadataEntryCount == record.summary.metadataEntryCount,report.summary.checkedPCCount == record.summary.checkedPCCount,
              let finding=report.findings.first(where:{$0.id == example.finding_id}),finding.verdict == .unresolved,finding.function.address == example.pc,finding.function.name.map{Data($0.utf8)} == example.function_name.map{Data($0.utf8)},finding.scope == example.scope,finding.mode == example.mode,finding.reasonCodes.contains(where:{$0.utf8.elementsEqual(reason.utf8)}) else {throw InspectionArchiveError.invalid}
        return (report,finding)
    }
}
