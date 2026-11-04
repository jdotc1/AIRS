import Foundation
import AIRSCore
import EntitlementDiffCore

/// A recorded acquisition failure, distinct from an unexamined signature.
public struct SecurityDeltaSignatureRefusal: Sendable {
    public let side: SecurityDeltaSide
    public let inventoryID: UUID
    public let componentID: UUID
    public let relativePath: String
    public let architecture: Architecture
    public let code: String
    public let capturedAt: Date
    public let sourceBytes: Data

    public static func record(side: SecurityDeltaSide, inventoryID: UUID, componentID: UUID, relativePath: String,
                              architecture: Architecture, code: String, capturedAt: Date) throws -> Self {
        let wire = Wire(kind: "airs.security-delta.signature-refusal", schemaVersion: 1, side: side, inventoryID: inventoryID,
                        componentID: componentID, relativePath: relativePath, architecture: architecture.rawValue, code: code,
                        capturedAtBits: String(format: "%016llx", capturedAt.timeIntervalSince1970.bitPattern))
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try admit(encoder.encode(wire))
    }

    public static func admit(_ bytes: Data) throws -> Self {
        guard !bytes.isEmpty, bytes.count <= 16_384 else { throw InspectionArchiveError.limit }
        let fields = try BoundJSON.object(BoundJSON.parse(bytes), keys: ["kind", "schemaVersion", "side", "inventoryID", "componentID", "relativePath", "architecture", "code", "capturedAtBits"])
        guard try BoundJSON.text(fields["kind"]) == "airs.security-delta.signature-refusal", try BoundJSON.integer(fields["schemaVersion"]) == 1 else { throw InspectionArchiveError.unsupportedVersion }
        let wire = try JSONDecoder().decode(Wire.self, from: bytes)
        guard let architecture = Architecture(rawValue: wire.architecture),
              ["source_unavailable", "source_stale", "slice_unavailable", "evidence_binding_mismatch"].contains(wire.code),
              !wire.relativePath.contains("\\"), !wire.relativePath.contains("\0"), wire.relativePath.utf8.count <= 4096,
              wire.relativePath.split(separator: "/", omittingEmptySubsequences: false).allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
              wire.capturedAtBits.utf8.count == 16, let bits = UInt64(wire.capturedAtBits, radix: 16),
              String(format: "%016llx", bits) == wire.capturedAtBits, Double(bitPattern: bits).isFinite,
              (0...253_402_300_799).contains(Double(bitPattern: bits)) else { throw InspectionArchiveError.invalid }
        return .init(side: wire.side, inventoryID: wire.inventoryID, componentID: wire.componentID, relativePath: wire.relativePath,
                     architecture: architecture, code: wire.code, capturedAt: Date(timeIntervalSince1970: Double(bitPattern: bits)), sourceBytes: bytes)
    }
    private struct Wire: Codable {
        let kind: String; let schemaVersion: Int; let side: SecurityDeltaSide; let inventoryID: UUID; let componentID: UUID
        let relativePath: String; let architecture: String; let code: String; let capturedAtBits: String
    }
}

/// A side-bound historical signature document, admitted once from retained
/// bytes. It contains no filesystem capability and grants no live-read access.
public struct SecurityDeltaSignatureEvidence: Sendable {
    public let side: SecurityDeltaSide
    public let inventoryID: UUID
    public let document: CodeSignatureEvidenceDocument
    public let sourceBytes: Data

    private init(side: SecurityDeltaSide, inventoryID: UUID, document: CodeSignatureEvidenceDocument, sourceBytes: Data) {
        self.side = side; self.inventoryID = inventoryID; self.document = document; self.sourceBytes = sourceBytes
    }

    /// Use for the first admission of a newly supplied document, not for
    /// refreshing an unchanged admitted session.
    public static func admit(_ bytes: Data, side: SecurityDeltaSide, inventoryID: UUID) throws -> Self {
        try Task.checkCancellation()
        let document = try CodeSignatureEvidenceDocument.decode(bytes)
        try Task.checkCancellation()
        return .init(side: side, inventoryID: inventoryID, document: document, sourceBytes: bytes)
    }
    /// Capture is explicitly invoked by a host holding the live capability.
    /// The returned value retains only historical bytes, not that capability.
    public static func capture(unit: BundleImageProvenance, componentID: UUID, side: SecurityDeltaSide, inventoryID: UUID) throws -> Self {
        guard unit.inventoryID == inventoryID else { throw InspectionArchiveError.invalid }
        try Task.checkCancellation()
        let document = try CodeSignatureEvidenceDocument.capture(unit: unit, componentID: componentID)
        let bytes = try document.encodedAdmittedData()
        try Task.checkCancellation()
        return .init(side: side, inventoryID: inventoryID, document: document, sourceBytes: bytes)
    }
}

/// All supplemental bindings are checked against the review by the analyzer.
public struct SecurityDeltaInput: Sendable {
    public let review: ComponentReview
    public let signatureEvidence: [SecurityDeltaSignatureEvidence]
    public let entitlementEvidence: [SecurityDeltaEntitlementEvidence]
    public let signatureRefusals: [SecurityDeltaSignatureRefusal]
    public init(review: ComponentReview, signatureEvidence: [SecurityDeltaSignatureEvidence] = [], entitlementEvidence: [SecurityDeltaEntitlementEvidence] = [], signatureRefusals: [SecurityDeltaSignatureRefusal] = []) {
        self.review = review; self.signatureEvidence = signatureEvidence; self.entitlementEvidence = entitlementEvidence; self.signatureRefusals = signatureRefusals
    }
}
