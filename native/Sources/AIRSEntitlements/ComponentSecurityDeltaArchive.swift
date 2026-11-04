import Foundation

/// A self-contained historical document. It never carries live capabilities.
/// Imported report bytes are compared with a fresh derivation rather
/// than being decoded into trusted findings.
public struct ComponentSecurityDeltaArchive: Sendable {
    public static let maximumBytes = 32 * 1_048_576
    private static let chunkSize = 512 * 1024
    private static let maximumChunks = 64

    public let sourceReviewArchive: Data
    public let admittedReview: AdmittedComponentReview
    public let signatureEvidence: [SecurityDeltaSignatureEvidence]
    public let entitlementEvidence: [SecurityDeltaEntitlementEvidence]
    public let signatureRefusals: [SecurityDeltaSignatureRefusal]
    public let report: ComponentSecurityDeltaReport
    private let reportBytes: Data

    /// Admit a newly selected source archive once and derive its report.
    public static func create(sourceReviewArchive: Data) throws -> Self {
        try securityDeltaBoundary {
            try Task.checkCancellation()
            guard !sourceReviewArchive.isEmpty else { throw SecurityDeltaRefusal(.invalidReview) }
            guard sourceReviewArchive.count <= InspectionArchive.maximumBytes else { throw SecurityDeltaRefusal(.retainedByteLimit) }
            return try create(admittedReview: ComponentReviewArchive.admit(sourceReviewArchive))
        }
    }

    /// Reuse the immutable in-process review/bytes pairing without re-admitting
    /// or rehashing its unchanged source archive.
    public static func create(admittedReview: AdmittedComponentReview, signatureEvidence: [SecurityDeltaSignatureEvidence] = [],
                              entitlementEvidence: [SecurityDeltaEntitlementEvidence] = [], signatureRefusals: [SecurityDeltaSignatureRefusal] = [],
                              options: SecurityDeltaOptions = .default) throws -> Self {
        try securityDeltaBoundary {
            try createAdmitted(admittedReview: admittedReview, signatureEvidence: signatureEvidence, entitlementEvidence: entitlementEvidence,
                               signatureRefusals: signatureRefusals, options: options)
        }
    }

    private static func createAdmitted(admittedReview: AdmittedComponentReview, signatureEvidence: [SecurityDeltaSignatureEvidence],
                                       entitlementEvidence: [SecurityDeltaEntitlementEvidence], signatureRefusals: [SecurityDeltaSignatureRefusal],
                                       options: SecurityDeltaOptions) throws -> Self {
        try Task.checkCancellation()
        let sourceReviewArchive = admittedReview.sourceArchive
        guard !sourceReviewArchive.isEmpty, sourceReviewArchive.count <= InspectionArchive.maximumBytes else { throw InspectionArchiveError.limit }
        let supplements = signatureEvidence.sorted {
            if $0.side != $1.side { return $0.side == .previous }
            return $0.document.evidence.componentID.uuidString < $1.document.evidence.componentID.uuidString
        }
        let entitlements = entitlementEvidence.sorted {
            if $0.side != $1.side { return $0.side == .previous }
            return $0.componentID.uuidString < $1.componentID.uuidString
        }
        let refusals = signatureRefusals.sorted {
            if $0.side != $1.side { return $0.side == .previous }
            return $0.componentID.uuidString < $1.componentID.uuidString
        }
        let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: admittedReview.review, signatureEvidence: supplements, entitlementEvidence: entitlements, signatureRefusals: refusals), options: options)
        let bytes = try encodeReport(report)
        try Task.checkCancellation()
        return .init(sourceReviewArchive: sourceReviewArchive, admittedReview: admittedReview, signatureEvidence: supplements, entitlementEvidence: entitlements, signatureRefusals: refusals, report: report, reportBytes: bytes)
    }

    /// Validate an incoming envelope and compare its report with derived output.
    public static func decode(_ bytes: Data) throws -> Self {
        try securityDeltaBoundary { try decodeAdmitted(bytes) }
    }

    private static func decodeAdmitted(_ bytes: Data) throws -> Self {
        guard bytes.count <= maximumBytes else { throw SecurityDeltaRefusal(.documentSizeLimit) }
        try Task.checkCancellation()
        let object = try BoundJSON.object(BoundJSON.parse(bytes))
        let required: Set<String> = ["kind", "schemaVersion", "modelVersion", "rulesVersion", "reviewChunks", "reportChunks", "options"]
        guard required.isSubset(of: Set(object.keys)), Set(object.keys).isSubset(of: required.union(["signatureEvidence", "entitlementEvidence", "signatureRefusals"])) else { throw InspectionArchiveError.invalid }
        guard try BoundJSON.text(object["kind"]).utf8.elementsEqual(ComponentSecurityDeltaReport.kind.utf8) else { throw InspectionArchiveError.invalid }
        guard try BoundJSON.integer(object["schemaVersion"]) == 1 else { throw SecurityDeltaRefusal(.unsupportedSchemaVersion) }
        guard try BoundJSON.text(object["modelVersion"]).utf8.elementsEqual(ComponentSecurityDeltaReport.modelVersion.utf8),
              try BoundJSON.text(object["rulesVersion"]).utf8.elementsEqual(ComponentSecurityDeltaReport.rulesVersion.utf8) else { throw SecurityDeltaRefusal(.unsupportedModelVersion) }
        guard let optionNode = object["options"] else { throw InspectionArchiveError.invalid }
        let optionFields = try BoundJSON.object(optionNode, keys: ["maximumObservations", "maximumFindings"])
        let maximumObservations = try BoundJSON.integer(optionFields["maximumObservations"], positive: true)
        let maximumFindings = try BoundJSON.integer(optionFields["maximumFindings"], positive: true)
        guard maximumObservations <= 8192 else { throw SecurityDeltaRefusal(.observationLimit) }
        guard maximumFindings <= 2048 else { throw SecurityDeltaRefusal(.findingLimit) }
        let options = try SecurityDeltaOptions(maximumObservations: Int(maximumObservations), maximumFindings: Int(maximumFindings))
        var total = 0
        func payload(_ node: BoundJSONNode?) throws -> Data {
            guard case .array(let chunks) = node, !chunks.isEmpty, chunks.count <= maximumChunks else { throw InspectionArchiveError.invalid }
            var result = Data()
            for (index, node) in chunks.enumerated() {
                try Task.checkCancellation()
                let encoded = try BoundJSON.text(node, max: ((chunkSize + 2) / 3) * 4)
                guard let decoded = Data(base64Encoded: encoded), !decoded.isEmpty,
                      decoded.count <= chunkSize, decoded.base64EncodedString().utf8.elementsEqual(encoded.utf8),
                      index == chunks.count - 1 || decoded.count == chunkSize else { throw InspectionArchiveError.invalid }
                guard decoded.count <= maximumBytes - total else { throw SecurityDeltaRefusal(.decodedByteLimit) }
                total += decoded.count
                result.append(decoded)
            }
            return result
        }
        let review = try payload(object["reviewChunks"])
        let claimedReport = try payload(object["reportChunks"])
        var supplements: [SecurityDeltaSignatureEvidence] = []
        if let node = object["signatureEvidence"] {
            guard case .array(let entries) = node, !entries.isEmpty, entries.count <= 128 else { throw InspectionArchiveError.invalid }
            for entry in entries {
                let fields = try BoundJSON.object(entry, keys: ["side", "inventoryID", "sourceChunks"])
                guard let side = SecurityDeltaSide(rawValue: try BoundJSON.text(fields["side"], max: 16)) else { throw InspectionArchiveError.invalid }
                let inventoryID = try BoundJSON.uuid(fields["inventoryID"])
                supplements.append(try SecurityDeltaSignatureEvidence.admit(payload(fields["sourceChunks"]), side: side, inventoryID: inventoryID))
            }
        }
        var entitlements: [SecurityDeltaEntitlementEvidence] = []
        if let node = object["entitlementEvidence"] {
            guard case .array(let entries) = node, !entries.isEmpty, entries.count <= 128 else { throw InspectionArchiveError.invalid }
            for entry in entries { entitlements.append(try SecurityDeltaEntitlementEvidence.admit(payload(entry))) }
        }
        var refusals: [SecurityDeltaSignatureRefusal] = []
        if let node = object["signatureRefusals"] {
            guard case .array(let entries) = node, !entries.isEmpty, entries.count <= 128 else { throw InspectionArchiveError.invalid }
            for entry in entries { refusals.append(try SecurityDeltaSignatureRefusal.admit(payload(entry))) }
        }
        let admittedReview = try ComponentReviewArchive.admit(review)
        guard admittedReview.sourceRecordCount + supplements.count + entitlements.count + refusals.count <= 256 else { throw SecurityDeltaRefusal(.sourceRecordLimit) }
        let admitted = try create(admittedReview: admittedReview, signatureEvidence: supplements, entitlementEvidence: entitlements, signatureRefusals: refusals, options: options)
        guard claimedReport == admitted.reportBytes else { throw SecurityDeltaRefusal(.invalidReview) }
        guard supplements.map({ $0.document.evidence.componentID }) == admitted.signatureEvidence.map({ $0.document.evidence.componentID }),
              supplements.map({ $0.side }) == admitted.signatureEvidence.map({ $0.side }) else { throw InspectionArchiveError.invalid }
        guard entitlements.map({ $0.componentID }) == admitted.entitlementEvidence.map({ $0.componentID }),
              entitlements.map({ $0.side }) == admitted.entitlementEvidence.map({ $0.side }) else { throw InspectionArchiveError.invalid }
        guard refusals.map({ $0.componentID }) == admitted.signatureRefusals.map({ $0.componentID }),
              refusals.map({ $0.side }) == admitted.signatureRefusals.map({ $0.side }) else { throw InspectionArchiveError.invalid }
        try Task.checkCancellation()
        return admitted
    }

    /// Encoding an already admitted immutable document does not re-open inputs.
    public func data() throws -> Data {
        try securityDeltaBoundary { try encodedData() }
    }

    private func encodedData() throws -> Data {
        try Task.checkCancellation()
        guard !sourceReviewArchive.isEmpty, !reportBytes.isEmpty else { throw InspectionArchiveError.invalid }
        guard admittedReview.sourceRecordCount + signatureEvidence.count + entitlementEvidence.count + signatureRefusals.count <= 256 else { throw SecurityDeltaRefusal(.sourceRecordLimit) }
        func chunks(_ data: Data) throws -> [String] {
            let count = (data.count + Self.chunkSize - 1) / Self.chunkSize
            guard count > 0, count <= Self.maximumChunks else { throw InspectionArchiveError.limit }
            var result: [String] = []
            for offset in stride(from: 0, to: data.count, by: Self.chunkSize) {
                try Task.checkCancellation()
                result.append(data.subdata(in: offset..<min(data.count, offset + Self.chunkSize)).base64EncodedString())
            }
            return result
        }
        try Self.exportBudget(sourceCount: sourceReviewArchive.count, reportCount: reportBytes.count, supplements: signatureEvidence, entitlements: entitlementEvidence, refusals: signatureRefusals)
        let wire = Wire(kind: ComponentSecurityDeltaReport.kind, schemaVersion: 1,
                        modelVersion: ComponentSecurityDeltaReport.modelVersion, rulesVersion: ComponentSecurityDeltaReport.rulesVersion,
                        options: report.options,
                        reviewChunks: try chunks(sourceReviewArchive), reportChunks: try chunks(reportBytes),
                        signatureEvidence: signatureEvidence.isEmpty ? nil : try signatureEvidence.map {
                            .init(side: $0.side.rawValue, inventoryID: $0.inventoryID.uuidString, sourceChunks: try chunks($0.sourceBytes))
                        }, entitlementEvidence: entitlementEvidence.isEmpty ? nil : try entitlementEvidence.map { try chunks($0.sourceBytes) },
                        signatureRefusals: signatureRefusals.isEmpty ? nil : try signatureRefusals.map { try chunks($0.sourceBytes) })
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let result = try encoder.encode(wire)
        guard result.count <= Self.maximumBytes else { throw SecurityDeltaRefusal(.exportSizeLimit) }
        try Task.checkCancellation()
        return result
    }

    static func exportBudget(sourceCount: Int, reportCount: Int, supplements: [SecurityDeltaSignatureEvidence] = [], entitlements: [SecurityDeltaEntitlementEvidence] = [], refusals: [SecurityDeltaSignatureRefusal] = []) throws {
        guard sourceCount > 0, sourceCount <= InspectionArchive.maximumBytes,
              reportCount >= 0, reportCount <= maximumBytes else { throw InspectionArchiveError.limit }
        let sourceEncoded = ((sourceCount + 2) / 3) * 4
        let reportEncoded = ((reportCount + 2) / 3) * 4
        var remaining = maximumBytes - 65_536
        for count in [sourceEncoded, reportEncoded] + supplements.map({ (($0.sourceBytes.count + 2) / 3) * 4 }) + entitlements.map({ (($0.sourceBytes.count + 2) / 3) * 4 }) + refusals.map({ (($0.sourceBytes.count + 2) / 3) * 4 }) {
            guard count <= remaining else { throw SecurityDeltaRefusal(.exportSizeLimit) }
            remaining -= count
        }
    }

    private static func encodeReport(_ report: ComponentSecurityDeltaReport) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let data = try encoder.encode(report)
        guard !data.isEmpty, data.count <= maximumBytes else { throw InspectionArchiveError.limit }
        return data
    }

    private struct Wire: Encodable {
        let kind: String
        let schemaVersion: Int
        let modelVersion: String
        let rulesVersion: String
        let options: SecurityDeltaOptions
        let reviewChunks: [String]
        let reportChunks: [String]
        let signatureEvidence: [SignatureWire]?
        let entitlementEvidence: [[String]]?
        let signatureRefusals: [[String]]?
    }
    private struct SignatureWire: Encodable {
        let side: String
        let inventoryID: String
        let sourceChunks: [String]
    }
}
