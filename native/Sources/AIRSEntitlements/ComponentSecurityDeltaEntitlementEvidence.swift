import Foundation
import EntitlementDiffCore

/// A retained side-bound API observation. This document is historical data and
/// does not confer authority to reopen or inspect a live application.
public struct SecurityDeltaEntitlementEvidence: Sendable {
    public static let maximumBytes = 8 * 1_048_576
    public let side: SecurityDeltaSide
    public let inventoryID: UUID
    public let componentID: UUID
    public let relativePath: String
    public let architecture: Architecture
    public let capturedAt: Date
    public let state: SecurityDeltaSourceState
    public let signingIdentifier: String?
    public let values: SecurityDeltaValue?
    public let reason: String?
    public let sourceBytes: Data

    /// The caller must supply a newly extracted snapshot from the opt-in
    /// `.exposed` numeric decoder. A legacy or imported snapshot is not eligible.
    public static func capture(snapshot: EntitlementSnapshot, side: SecurityDeltaSide, inventoryID: UUID,
                               componentID: UUID, relativePath: String, capturedAt: Date) throws -> Self {
        guard snapshot.origin == .extracted, !snapshot.isSavedBaseline, snapshot.numericRepresentation == .exposed else { throw InspectionArchiveError.invalid }
        let state: SecurityDeltaSourceState = snapshot.presence == .notPresent ? .absent : .observed
        guard state != .absent || snapshot.entitlements.entries.isEmpty else { throw InspectionArchiveError.invalid }
        let values = state == .observed ? try SecurityDeltaValue.from(.dictionary(snapshot.entitlements), normalizedIntegers: false,
            maxNodes: 10_000, maxBytes: maximumBytes) : nil
        return try make(.init(kind: "airs.security-delta.entitlements", schemaVersion: 1, side: side, inventoryID: inventoryID,
            componentID: componentID, relativePath: relativePath, architecture: snapshot.architecture.rawValue,
            capturedAtBits: String(format: "%016llx", capturedAt.timeIntervalSince1970.bitPattern), state: state,
            signingIdentifier: snapshot.signingIdentifier, values: values, reason: nil))
    }

    public static func unavailable(side: SecurityDeltaSide, inventoryID: UUID, componentID: UUID, relativePath: String,
                                   architecture: Architecture, capturedAt: Date, reason: String) throws -> Self {
        try make(.init(kind: "airs.security-delta.entitlements", schemaVersion: 1, side: side, inventoryID: inventoryID,
            componentID: componentID, relativePath: relativePath, architecture: architecture.rawValue,
            capturedAtBits: String(format: "%016llx", capturedAt.timeIntervalSince1970.bitPattern), state: .unavailable,
            signingIdentifier: nil, values: nil, reason: reason))
    }

    /// Host-recorded acquisition state; this performs no live read.
    public static func unexamined(side: SecurityDeltaSide, inventoryID: UUID, componentID: UUID, relativePath: String,
                                  architecture: Architecture, recordedAt: Date) throws -> Self {
        try make(.init(kind: "airs.security-delta.entitlements", schemaVersion: 1, side: side, inventoryID: inventoryID,
            componentID: componentID, relativePath: relativePath, architecture: architecture.rawValue,
            capturedAtBits: String(format: "%016llx", recordedAt.timeIntervalSince1970.bitPattern), state: .unexamined,
            signingIdentifier: nil, values: nil, reason: "category_unexamined"))
    }

    public static func admit(_ bytes: Data) throws -> Self {
        guard !bytes.isEmpty, bytes.count <= maximumBytes else { throw InspectionArchiveError.limit }
        try Task.checkCancellation()
        let fields = try BoundJSON.object(BoundJSON.parse(bytes))
        let required: Set<String> = ["kind", "schemaVersion", "side", "inventoryID", "componentID", "relativePath", "architecture", "capturedAtBits", "state"]
        guard required.isSubset(of: Set(fields.keys)), Set(fields.keys).isSubset(of: required.union(["signingIdentifier", "values", "reason"])) else { throw InspectionArchiveError.invalid }
        guard try BoundJSON.text(fields["kind"]) == "airs.security-delta.entitlements", try BoundJSON.integer(fields["schemaVersion"]) == 1 else { throw InspectionArchiveError.unsupportedVersion }
        var nodes = 0
        func typed(_ node: BoundJSONNode, depth: Int) throws {
            nodes += 1
            guard depth <= 32, nodes <= 10_000 else { throw InspectionArchiveError.limit }
            let value = try BoundJSON.object(node, keys: ["type", "value"])
            switch try BoundJSON.text(value["type"], max: 32) {
            case "array":
                guard case .array(let children) = value["value"] else { throw InspectionArchiveError.invalid }
                for child in children { try typed(child, depth: depth + 1) }
            case "dictionary":
                guard case .array(let entries) = value["value"] else { throw InspectionArchiveError.invalid }
                for entry in entries {
                    let item = try BoundJSON.object(entry, keys: ["key", "value"])
                    _ = try BoundJSON.text(item["key"], max: 4096)
                    guard let child = item["value"] else { throw InspectionArchiveError.invalid }
                    try typed(child, depth: depth + 1)
                }
            case "boolean", "signed", "unsigned", "realBits", "string", "data", "dateBits": break
            default: throw InspectionArchiveError.invalid
            }
        }
        if let value = fields["values"] { try typed(value, depth: 0) }
        let wire = try JSONDecoder().decode(Wire.self, from: bytes)
        return try validate(wire, bytes: bytes)
    }

    private static func make(_ wire: Wire) throws -> Self {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        let bytes = try encoder.encode(wire)
        guard bytes.count <= maximumBytes else { throw InspectionArchiveError.limit }
        return try admit(bytes)
    }

    private static func validate(_ wire: Wire, bytes: Data) throws -> Self {
        guard wire.kind == "airs.security-delta.entitlements", wire.schemaVersion == 1,
              let architecture = Architecture(rawValue: wire.architecture),
              wire.relativePath.utf8.count <= 4096, !wire.relativePath.contains("\\"), !wire.relativePath.contains("\0"),
              wire.relativePath.split(separator: "/", omittingEmptySubsequences: false).allSatisfy({ !$0.isEmpty && $0 != "." && $0 != ".." }),
              wire.capturedAtBits.utf8.count == 16, let bits = UInt64(wire.capturedAtBits, radix: 16),
              String(format: "%016llx", bits) == wire.capturedAtBits,
              Double(bitPattern: bits).isFinite, (0...253_402_300_799).contains(Double(bitPattern: bits)) else { throw InspectionArchiveError.invalid }
        switch wire.state {
        case .observed:
            guard let values = wire.values, case .dictionary = values, wire.signingIdentifier != nil, wire.reason == nil else { throw InspectionArchiveError.invalid }
            try values.validate(maxNodes: 10_000, maxBytes: maximumBytes)
            func keyLengthsValid(_ value: SecurityDeltaValue) -> Bool {
                switch value {
                case .dictionary(let entries): return entries.allSatisfy { $0.key.utf8.count <= 4096 && keyLengthsValid($0.value) }
                case .array(let entries): return entries.allSatisfy(keyLengthsValid)
                default: return true
                }
            }
            guard keyLengthsValid(values) else { throw InspectionArchiveError.limit }
            guard try values.compare(to: values) == .equal else { throw InspectionArchiveError.invalid }
        case .absent:
            guard wire.values == nil, wire.signingIdentifier != nil, wire.reason == nil else { throw InspectionArchiveError.invalid }
        case .unavailable:
            guard wire.values == nil, wire.signingIdentifier == nil, let reason = wire.reason, !reason.isEmpty, reason.utf8.count <= 4096 else { throw InspectionArchiveError.invalid }
        case .unexamined:
            guard wire.values == nil, wire.signingIdentifier == nil, wire.reason == "category_unexamined" else { throw InspectionArchiveError.invalid }
        default: throw InspectionArchiveError.invalid
        }
        if let identifier = wire.signingIdentifier {
            guard !identifier.isEmpty, identifier.utf8.count <= 4096 else { throw InspectionArchiveError.invalid }
        }
        return .init(side: wire.side, inventoryID: wire.inventoryID, componentID: wire.componentID, relativePath: wire.relativePath,
            architecture: architecture, capturedAt: Date(timeIntervalSince1970: Double(bitPattern: bits)), state: wire.state,
            signingIdentifier: wire.signingIdentifier, values: wire.values, reason: wire.reason, sourceBytes: bytes)
    }

    private struct Wire: Codable {
        let kind: String
        let schemaVersion: Int
        let side: SecurityDeltaSide
        let inventoryID: UUID
        let componentID: UUID
        let relativePath: String
        let architecture: String
        let capturedAtBits: String
        let state: SecurityDeltaSourceState
        let signingIdentifier: String?
        let values: SecurityDeltaValue?
        let reason: String?
    }
}
