import Foundation
import AIRSCore
import EntitlementDiffCore

/// Stable machine-readable refusal codes for the derived security-delta API.
/// Cancellation remains `CancellationError` so structured concurrency can
/// distinguish it from an ordinary refused input.
public enum SecurityDeltaRefusalCode: String, Codable, Sendable {
    case invalidReview = "invalid_review", duplicateComponentIdentity = "duplicate_component_identity"
    case duplicateObservationIdentity = "duplicate_observation_identity", danglingEvidenceReference = "dangling_evidence_reference"
    case evidenceBindingMismatch = "evidence_binding_mismatch", componentCorrespondenceUnaccepted = "component_correspondence_unaccepted"
    case inventoryIncomplete = "inventory_incomplete", inventoryExcluded = "inventory_excluded"
    case sourceUnavailable = "source_unavailable", sourceStale = "source_stale", categoryUnexamined = "category_unexamined"
    case sliceUnavailable = "slice_unavailable", sliceCorrespondenceUnresolved = "slice_correspondence_unresolved"
    case numericRepresentationUnspecified = "numeric_representation_unspecified"
    case unsupportedSchemaVersion = "unsupported_schema_version", unsupportedModelVersion = "unsupported_model_version"
    case componentLimit = "component_limit", observationLimit = "observation_limit", findingLimit = "finding_limit"
    case evidenceReferenceLimit = "evidence_reference_limit", typedDepthLimit = "typed_depth_limit"
    case typedNodeLimit = "typed_node_limit", retainedByteLimit = "retained_byte_limit", exportSizeLimit = "export_size_limit"
    case decodedByteLimit = "decoded_byte_limit", sourceRecordLimit = "source_record_limit", diagnosticLimit = "diagnostic_limit"
    case documentSizeLimit = "document_size_limit"
    case limitationLimit = "limitation_limit"
    /// A legacy validator exhausted a limit without exposing which budget.
    case resourceLimit = "resource_limit"
    case cancelled
}

public struct SecurityDeltaRefusal: Error, Sendable, Equatable, LocalizedError {
    public let code: SecurityDeltaRefusalCode
    public init(_ code: SecurityDeltaRefusalCode) { self.code = code }
    public var errorDescription: String? { "Security change analysis refused: \(code.rawValue)." }
}

/// Preserve precise delta refusals and cancellation while translating the
/// legacy archive's deliberately broad errors at the new API boundary.
func securityDeltaBoundary<T>(_ operation: () throws -> T) throws -> T {
    do { return try operation() }
    catch is CancellationError { throw CancellationError() }
    catch let error as SecurityDeltaRefusal { throw error }
    catch let error as InspectionArchiveError {
        switch error {
        case .invalid: throw SecurityDeltaRefusal(.invalidReview)
        case .limit: throw SecurityDeltaRefusal(.resourceLimit)
        case .unsupportedVersion: throw SecurityDeltaRefusal(.unsupportedSchemaVersion)
        }
    }
    catch let error as AIRSCore.ReportError {
        switch error {
        case .unsupportedSchema: throw SecurityDeltaRefusal(.unsupportedSchemaVersion)
        case .tooLarge: throw SecurityDeltaRefusal(.resourceLimit)
        case .wrongKind, .notRegularFile, .invalidContents: throw SecurityDeltaRefusal(.invalidReview)
        }
    }
    catch is EntitlementDiffCore.ReportError { throw SecurityDeltaRefusal(.invalidReview) }
    catch let error as SavedReportError {
        switch error {
        case .invalid: throw SecurityDeltaRefusal(.invalidReview)
        case .limit: throw SecurityDeltaRefusal(.resourceLimit)
        }
    }
    catch let error as CodeSignatureEvidenceError {
        switch error {
        case .invalid: throw SecurityDeltaRefusal(.invalidReview)
        case .budgetExceeded: throw SecurityDeltaRefusal(.resourceLimit)
        case .unavailable: throw SecurityDeltaRefusal(.sourceUnavailable)
        }
    }
    catch let error as EntitlementDataError {
        if case .limitExceeded = error { throw SecurityDeltaRefusal(.resourceLimit) }
        throw SecurityDeltaRefusal(.invalidReview)
    }
    catch is DecodingError { throw SecurityDeltaRefusal(.invalidReview) }
}

/// A disposition describes an observation, never a trust or runtime verdict.
public enum SecurityDeltaDisposition: String, Codable, Sendable {
    case observedAddition, observedRemoval, observedChange, unchanged, unresolved, declined
}

public enum SecurityDeltaCategory: String, Codable, Sendable, CaseIterable {
    case componentInventory, informationPropertyList, loadCommands, entitlements, privacyManifest, signatureEvidence
}

public enum SecurityDeltaSide: String, Codable, Sendable {
    case previous, current
}

public enum SecurityDeltaSourceState: String, Codable, Sendable {
    case observed, absent, unavailable, unexamined, excluded, unknown
}

/// Callers may reduce, but never raise, the version-1 output ceilings.
public struct SecurityDeltaOptions: Codable, Sendable {
    public let maximumObservations: Int
    public let maximumFindings: Int
    public static let `default` = SecurityDeltaOptions(uncheckedObservations: 8192, findings: 2048)
    private init(uncheckedObservations: Int, findings: Int) { maximumObservations = uncheckedObservations; maximumFindings = findings }
    public init(maximumObservations: Int = 8192, maximumFindings: Int = 2048) throws {
        guard (1...8192).contains(maximumObservations) else { throw SecurityDeltaRefusal(.observationLimit) }
        guard (1...2048).contains(maximumFindings) else { throw SecurityDeltaRefusal(.findingLimit) }
        self.maximumObservations = maximumObservations; self.maximumFindings = maximumFindings
    }
    func validate() throws {
        guard (1...8192).contains(maximumObservations) else { throw SecurityDeltaRefusal(.observationLimit) }
        guard (1...2048).contains(maximumFindings) else { throw SecurityDeltaRefusal(.findingLimit) }
    }
}

public enum SecurityDeltaFindingKind: String, Codable, Sendable {
    case componentAdded, componentRemoved, xpcAdded, declarationChanged, signatureEvidenceChanged
    case componentMultiCategory, relatedComponents, repeatedDeclaration, coverageIncomplete, evidenceConflict
}

public struct SecurityDeltaComponentIdentity: Codable, Sendable {
    public let side: SecurityDeltaSide
    public let inventoryID: UUID
    public let componentID: UUID
    public let relativePath: String
    public let kind: String
    public let parentID: UUID?
}

public struct SecurityDeltaSliceIdentity: Codable, Sendable {
    public let cpuType: UInt32
    public let cpuSubtype: UInt32
    public let headerMagic: UInt32
    public let index: Int
    public let offset: UInt64
    public let size: UInt64
    public let recordedSHA256: String?
}

public struct SecurityDeltaReviewIdentity: Codable, Sendable {
    public let previousInventoryID: UUID
    public let currentInventoryID: UUID
    public let architecture: String
    public let evidenceBasisID: String
}

public struct SecurityDeltaReason: Codable, Sendable {
    public let code: String
    public let diagnostic: String
}

public struct SecurityDeltaObservation: Codable, Sendable, Identifiable {
    public let id: String
    public let category: SecurityDeltaCategory
    public let componentPath: String
    public let subject: String
    public let disposition: SecurityDeltaDisposition
    public let previousState: SecurityDeltaSourceState
    public let currentState: SecurityDeltaSourceState
    public let previousValue: SecurityDeltaValue?
    public let currentValue: SecurityDeltaValue?
    public let evidence: [SecurityDeltaEvidenceReference]
    public let limitations: [SecurityDeltaReason]
}

public struct SecurityDeltaFinding: Codable, Sendable, Identifiable {
    public let id: String
    public let kind: SecurityDeltaFindingKind
    public let disposition: SecurityDeltaDisposition
    public let title: String
    public let explanation: String
    public let observationIDs: [String]
    public let evidence: [SecurityDeltaEvidenceReference]
    public let limitations: [SecurityDeltaReason]
}

public struct SecurityDeltaOmission: Codable, Sendable {
    public let count: Int
    public let countIsExact: Bool
    public let detailListComplete: Bool
    public let reason: SecurityDeltaReason
}

public struct SecurityDeltaCoverage: Codable, Sendable {
    public let previousScope: String
    public let currentScope: String
    public let previousLocations: [String]
    public let currentLocations: [String]
    public let previousExclusions: [String]
    public let currentExclusions: [String]
    public let previousIssues: [String]
    public let currentIssues: [String]
    public let limitations: [SecurityDeltaReason]
    public let omissions: [SecurityDeltaOmission]
}

public struct ComponentSecurityDeltaReport: Codable, Sendable {
    public static let kind = "airs.component.security-delta"
    public static let modelVersion = "component-security-delta-v1"
    public static let rulesVersion = "component-security-delta-rules-v1"
    public let identity: SecurityDeltaReviewIdentity
    public let options: SecurityDeltaOptions
    public let observations: [SecurityDeltaObservation]
    public let findings: [SecurityDeltaFinding]
    public let coverage: SecurityDeltaCoverage
}

/// A location in captured review evidence; it carries no live file authority.
public struct SecurityDeltaEvidenceReference: Codable, Sendable {
    public let side: SecurityDeltaSide
    public let inventoryID: UUID
    /// Nil denotes the inventory scope itself rather than a component record.
    public let componentID: UUID?
    public let category: SecurityDeltaCategory
    public let relativeSource: String
    public let architecture: String?
    public let evidenceKey: String?
    public let slice: SecurityDeltaSliceIdentity?

    public init(side: SecurityDeltaSide, inventoryID: UUID, componentID: UUID?,
                category: SecurityDeltaCategory, relativeSource: String,
                architecture: String? = nil, evidenceKey: String? = nil, slice: SecurityDeltaSliceIdentity? = nil) {
        self.side = side
        self.inventoryID = inventoryID
        self.componentID = componentID
        self.category = category
        self.relativeSource = relativeSource
        self.architecture = architecture
        self.evidenceKey = evidenceKey
        self.slice = slice
    }
}
