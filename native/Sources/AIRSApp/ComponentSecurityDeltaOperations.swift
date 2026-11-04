import Foundation
import AIRSCore
import AIRSEntitlements
import EntitlementDiffCore

struct SecurityDeltaEvidenceContent: Sendable {
    let description: String
    let value: SecurityDeltaValue?
    let sourceBytes: Data?
}
struct SecurityDeltaFilteredRows: Sendable {
    let findings: [[SecurityDeltaFinding]]
    let observations: [[SecurityDeltaObservation]]
}

/// Explicit capture owned by the live review. Imported sessions never have a
/// capability; the analysis engine receives only the resulting retained data.
enum ComponentSecurityDeltaOperations {
    static func preflightLegacyPair(_ session: ComponentReviewSession, matchID: UUID, previousID: UUID, currentID: UUID) throws {
        guard let token = session.admittedReview else { return }
        let replaced = session.entitlementEvidence.filter { item in
            item.state == .unexamined && ((item.side == .previous && item.componentID == previousID) || (item.side == .current && item.componentID == currentID))
        }.count
        let alreadyCompared = session.review.entitlementResults.contains { item in
            guard item.matchID == matchID else { return false }
            if case .compared = item { return true }; return false
        }
        let projected = token.sourceRecordCount + (alreadyCompared ? 0 : 1) + session.entitlementEvidence.count - replaced + session.signatureEvidence.count + session.signatureRefusals.count
        guard projected <= 256 else { throw InspectionArchiveError.limit }
        try preflightCapacity(session, additionalBytes: 8 * 1_048_576)
    }
    /// Reserve a conservative maximum before invoking any live reader. The
    /// encoded source archive is used as an upper bound for its retained bytes.
    private static func preflightCapacity(_ session: ComponentReviewSession, excludingEntitlement: (SecurityDeltaSide, UUID)? = nil,
                                          additionalBytes: Int) throws {
        let limit = 32 * 1_048_576
        guard additionalBytes <= limit, session.archiveBytes.count <= limit - additionalBytes else { throw InspectionArchiveError.limit }
        var remaining = limit - additionalBytes - session.archiveBytes.count
        let existing = session.entitlementEvidence.filter { item in
            guard let (side, id) = excludingEntitlement else { return true }
            return item.side != side || item.componentID != id
        }.map(\.sourceBytes) + session.signatureEvidence.map(\.sourceBytes) + session.signatureRefusals.map(\.sourceBytes)
        for bytes in existing {
            guard bytes.count <= remaining else { throw InspectionArchiveError.limit }
            remaining -= bytes.count
        }
    }
    static func filteredRows(_ session: ComponentReviewSession, category: String, component: String) throws -> SecurityDeltaFilteredRows {
        try Task.checkCancellation()
        guard let report = session.securityDeltaReport else { throw InspectionArchiveError.invalid }
        let bytes = component == "all" ? nil : Data(base64Encoded: component)
        guard component == "all" || bytes != nil else { throw InspectionArchiveError.invalid }
        func matches(_ observation: SecurityDeltaObservation) -> Bool {
            (category == "all" || observation.category.rawValue == category) &&
            (bytes == nil || Data(observation.componentPath.utf8) == bytes)
        }
        var selected: [SecurityDeltaObservation] = []
        for observation in report.observations {
            try Task.checkCancellation()
            if matches(observation) { selected.append(observation) }
        }
        let ids = Set(selected.map(\.id))
        var findings: [SecurityDeltaFinding] = []
        for finding in report.findings {
            try Task.checkCancellation()
            if finding.observationIDs.contains(where: ids.contains) { findings.append(finding) }
        }
        func pages<T>(_ values: [T]) -> [[T]] {
            stride(from: 0, to: values.count, by: 200).map { Array(values[$0..<min($0 + 200, values.count)]) }
        }
        return .init(findings: pages(findings), observations: pages(selected))
    }
    /// Resolve only retained session data; this function never reads a bundle.
    static func resolveEvidence(_ reference: SecurityDeltaEvidenceReference, in session: ComponentReviewSession) throws -> SecurityDeltaEvidenceContent {
        try Task.checkCancellation()
        let inventory = reference.side == .previous ? session.review.previous : session.review.current
        let declarations = reference.side == .previous ? session.review.previousDeclarations : session.review.currentDeclarations
        guard reference.inventoryID == inventory.id else { throw InspectionArchiveError.invalid }
        guard let id = reference.componentID else {
            guard reference.category == .componentInventory, reference.evidenceKey == "scope" else { throw InspectionArchiveError.invalid }
            return .init(description: "Recorded inventory scope: " + inventory.scope.completion.rawValue, value: nil, sourceBytes: nil)
        }
        guard let record = inventory.components.first(where: { $0.id == id }) else { throw InspectionArchiveError.invalid }
        switch reference.category {
        case .componentInventory:
            guard record.relativePath.utf8.elementsEqual(reference.relativeSource.utf8) else { throw InspectionArchiveError.invalid }
            let value: SecurityDeltaValue?
            switch reference.evidenceKey {
            case "architectures": value = .array(record.architectures.map(SecurityDeltaValue.string))
            case "parentID": value = record.parentID.map { .string($0.uuidString) }
            case "kind": value = .string(record.kind)
            case "bundleIdentifier": value = record.declaredBundleID.map(SecurityDeltaValue.string)
            case "version": value = record.declaredVersion.map(SecurityDeltaValue.string)
            case let key? where key.hasPrefix("minimumOS:"):
                let label = String(key.dropFirst("minimumOS:".count))
                value = record.minimumOSByArchitecture.first(where: { $0.key.utf8.elementsEqual(label.utf8) }).map { .string($0.value) }
            case "component", "entitlement:not-captured", "signature:not-captured": value = nil
            case let key? where key.hasPrefix("declaration:not-captured:"): value = nil
            default: throw InspectionArchiveError.invalid
            }
            return .init(description: "Recorded component inventory: " + record.relativePath, value: value, sourceBytes: nil)
        case .informationPropertyList, .loadCommands, .privacyManifest:
            let category: DeclarationCategory = reference.category == .informationPropertyList ? .info : (reference.category == .loadCommands ? .loadCommands : .privacy)
            guard let item = declarations.first(where: { $0.componentID == id && $0.category == category }),
                  item.relativeSource.utf8.elementsEqual(reference.relativeSource.utf8),
                  item.architecture == reference.architecture else { throw InspectionArchiveError.invalid }
            guard let key = reference.evidenceKey,
                  key == "declaration:presence" || key == "declaration:binding:CFBundleExecutable" ||
                  key.hasPrefix("declaration:key:") || (category == .loadCommands && key.hasPrefix("loader:dependency:")) else { throw InspectionArchiveError.invalid }
            var value: SecurityDeltaValue?
            if item.state == .present, let key = reference.evidenceKey, key.hasPrefix("loader:dependency:") {
                let suffix = String(key.dropFirst("loader:dependency:".count))
                guard let split = suffix.firstIndex(of: ":") else { throw InspectionArchiveError.invalid }
                let command = String(suffix[..<split]), path = String(suffix[suffix.index(after: split)...])
                let dictionary = try item.values()
                guard case .array(let rows)? = dictionary["commands"] else { throw InspectionArchiveError.invalid }
                let matching = rows.filter { row in
                    guard case .dictionary(let fields) = row, case .string(let c)? = fields["command"], case .string(let p)? = fields["path"] else { return false }
                    return c.utf8.elementsEqual(command.utf8) && p.utf8.elementsEqual(path.utf8)
                }
                value = .array(try matching.map { try SecurityDeltaValue.from($0, normalizedIntegers: true) })
            }
            return .init(description: "Recorded declaration state: " + item.state.rawValue + (item.issue.map { " · " + $0 } ?? ""), value: value, sourceBytes: item.bytes)
        case .entitlements:
            guard record.relativePath.utf8.elementsEqual(reference.relativeSource.utf8), reference.architecture == session.review.architecture.rawValue else { throw InspectionArchiveError.invalid }
            guard let key = reference.evidenceKey else { throw InspectionArchiveError.invalid }
            if key.hasPrefix("strict-entitlement:") {
                guard key == "strict-entitlement:presence" || key == "strict-entitlement:document" || key.hasPrefix("strict-entitlement:key:"),
                      let item = session.entitlementEvidence.first(where: { $0.side == reference.side && $0.componentID == id }) else { throw InspectionArchiveError.invalid }
                return .init(description: "Recorded entitlement state: " + item.state.rawValue, value: item.values, sourceBytes: item.sourceBytes)
            }
            guard key == "entitlement:result" || key == "entitlement:presence" || key.hasPrefix("entitlement:key:"),
                  let match = session.review.matching.matches.first(where: { reference.side == .previous ? $0.previousID == id : $0.currentID == id }),
                  let outcome = session.review.entitlementResults.first(where: { $0.matchID == match.id }) else { throw InspectionArchiveError.invalid }
            switch outcome {
            case .unavailable(_, _, let reason):
                return .init(description: "Recorded legacy pair outcome: " + reason, value: nil, sourceBytes: nil)
            case .compared(_, _, let comparison):
                let snapshot = reference.side == .previous ? comparison.previous : comparison.current
                var value: SecurityDeltaValue?
                if snapshot.presence == .dictionaryPresent {
                    if key.hasPrefix("entitlement:key:") {
                        let name = String(key.dropFirst("entitlement:key:".count))
                        if let entry = snapshot.entitlements.entries.first(where: { $0.key.utf8.elementsEqual(name.utf8) }) {
                            value = try SecurityDeltaValue.from(entry.value, normalizedIntegers: true, maxNodes: 10_000, maxBytes: 8 * 1_048_576)
                        }
                    } else { value = try SecurityDeltaValue.from(.dictionary(snapshot.entitlements), normalizedIntegers: true, maxNodes: 10_000, maxBytes: 8 * 1_048_576) }
                }
                return .init(description: "Recorded legacy entitlement state: " + snapshot.presence.rawValue + "; original numeric representation may be unspecified.",
                    value: value, sourceBytes: session.admittedReview?.entitlementSource(matchID: match.id))
            }
        case .signatureEvidence:
            guard record.relativePath.utf8.elementsEqual(reference.relativeSource.utf8) else { throw InspectionArchiveError.invalid }
            guard let key = reference.evidenceKey else { throw InspectionArchiveError.invalid }
            if key == "signature:refusal", let item = session.signatureRefusals.first(where: { $0.side == reference.side && $0.componentID == id }) {
                guard reference.slice == nil, reference.architecture == nil else { throw InspectionArchiveError.invalid }
                return .init(description: "Recorded signature capture refusal: " + item.code, value: nil, sourceBytes: item.sourceBytes)
            }
            guard let item = session.signatureEvidence.first(where: { $0.side == reference.side && $0.document.evidence.componentID == id }) else { throw InspectionArchiveError.invalid }
            let sliced = ["signature:sliceSHA256", "signature:state", "signature:signatureState", "signature:signatureSHA256", "signature:slot:5:sha256", "signature:slot:7:sha256", "signature:retained-bytes", "signature:consistency"]
            let document = ["signature:document", "signature:containerSHA256", "signature:container-slice-consistency", "signature:slice"]
            guard sliced.contains(key) || document.contains(key) else { throw InspectionArchiveError.invalid }
            if sliced.contains(key) {
                let cpu: UInt32 = session.review.architecture == .arm64 ? 0x0100000c : 0x01000007
                let subtype: UInt32 = session.review.architecture == .arm64 ? 0 : 3
                guard reference.architecture == session.review.architecture.rawValue, let slice = reference.slice,
                      slice.cpuType == cpu, slice.cpuSubtype == subtype,
                      item.document.evidence.slices.contains(where: { $0.index == slice.index && $0.cpuType == slice.cpuType && $0.cpuSubtype == slice.cpuSubtype &&
                          $0.headerMagic == slice.headerMagic && $0.sliceOffset == slice.offset && $0.sliceSize == slice.size && $0.sliceSHA256 == slice.recordedSHA256 }) else { throw InspectionArchiveError.invalid }
            } else if reference.slice != nil || reference.architecture != nil { throw InspectionArchiveError.invalid }
            return .init(description: "Recorded structural signature evidence; original image bytes are not authenticated.", value: nil, sourceBytes: item.sourceBytes)
        }
    }
    /// Call on the owned background job, not from a SwiftUI body.
    static func derive(_ session: ComponentReviewSession) throws -> ComponentReviewSession {
        try Task.checkCancellation()
        var report: ComponentSecurityDeltaReport?
        let failure: String?
        var exportBytes: Data?, exportFailure: String?
        do {
            if let token = session.admittedReview {
                let document = try ComponentSecurityDeltaArchive.create(admittedReview: token,
                    signatureEvidence: session.signatureEvidence, entitlementEvidence: session.entitlementEvidence, signatureRefusals: session.signatureRefusals)
                report = document.report
                do { exportBytes = try document.data() }
                catch { if error is CancellationError || Task.isCancelled { throw CancellationError() }; exportFailure = error.localizedDescription }
            } else {
                report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: session.review,
                    signatureEvidence: session.signatureEvidence, entitlementEvidence: session.entitlementEvidence, signatureRefusals: session.signatureRefusals))
                exportFailure = "The original historical archive is retained; a validated export session has not been assembled."
            }
            failure = nil
        } catch {
            if error is CancellationError || Task.isCancelled { throw CancellationError() }
            report = nil; failure = "Security change analysis unavailable: " + error.localizedDescription
        }
        try Task.checkCancellation()
        return try .init(review: session.review, archiveBytes: session.archiveBytes, sourceURLs: session.sourceURLs, live: session.live,
            securityDeltaReport: report, securityDeltaFailure: failure, entitlementEvidence: session.entitlementEvidence, signatureEvidence: session.signatureEvidence, signatureRefusals: session.signatureRefusals,
            admittedReview: session.admittedReview, securityDeltaArchiveBytes: exportBytes, securityDeltaExportFailure: exportFailure)
    }
    static func capturingEntitlements(_ session: ComponentReviewSession, side: SecurityDeltaSide, componentID: UUID,
                                     reader: any CodeUnitSnapshotReading = CodeUnitEntitlementReader(numericRepresentation: .exposed)) async throws -> ComponentReviewSession {
        guard !session.entitlementEvidence.contains(where: { $0.side == side && $0.componentID == componentID && $0.state != .unexamined }) else {
            throw AIRSCore.ReportError.invalidContents("Entitlement evidence for this side is already retained; rebuild the review for a new capture.")
        }
        if let token = session.admittedReview {
            let existing = session.entitlementEvidence.contains { $0.side == side && $0.componentID == componentID }
            guard token.sourceRecordCount + session.entitlementEvidence.count + session.signatureEvidence.count + session.signatureRefusals.count + (existing ? 0 : 1) <= 256 else { throw InspectionArchiveError.limit }
        }
        try preflightCapacity(session, excludingEntitlement: (side, componentID), additionalBytes: SecurityDeltaEntitlementEvidence.maximumBytes)
        let captured = try await captureEntitlements(session, side: side, componentID: componentID, reader: reader)
        try Task.checkCancellation()
        let retained = session.entitlementEvidence.filter { $0.side != side || $0.componentID != componentID } + [captured]
        let revision = try ComponentReviewSession(review: session.review, archiveBytes: session.archiveBytes, sourceURLs: session.sourceURLs,
            live: session.live, entitlementEvidence: retained, signatureEvidence: session.signatureEvidence, signatureRefusals: session.signatureRefusals, admittedReview: session.admittedReview)
        return try derive(revision)
    }
    static func capturingSignature(_ session: ComponentReviewSession, side: SecurityDeltaSide, componentID: UUID,
                                   capture: (BundleImageProvenance, UUID, SecurityDeltaSide, UUID) throws -> SecurityDeltaSignatureEvidence = {
        try SecurityDeltaSignatureEvidence.capture(unit: $0, componentID: $1, side: $2, inventoryID: $3)
    }) throws -> ComponentReviewSession {
        try Task.checkCancellation()
        guard let live = session.live, live.count == 2 else { throw AIRSCore.ReportError.invalidContents("Historical evidence cannot authorize signature capture.") }
        guard !session.signatureEvidence.contains(where: { $0.side == side && $0.document.evidence.componentID == componentID }),
              !session.signatureRefusals.contains(where: { $0.side == side && $0.componentID == componentID }) else {
            throw AIRSCore.ReportError.invalidContents("Signature evidence for this side is already retained; rebuild the review for a new capture.")
        }
        if let token = session.admittedReview {
            guard token.sourceRecordCount + session.entitlementEvidence.count + session.signatureEvidence.count + session.signatureRefusals.count + 1 <= 256 else { throw InspectionArchiveError.limit }
        }
        try preflightCapacity(session, additionalBytes: CodeSignatureEvidenceDocument.maximumBytes)
        let index = side == .previous ? 0 : 1
        let inventory = side == .previous ? session.review.previous : session.review.current
        let declarations = side == .previous ? session.review.previousDeclarations : session.review.currentDeclarations
        guard live[index].inventory.id == inventory.id, let record = inventory.components.first(where: { $0.id == componentID }) else {
            throw AIRSCore.ReportError.invalidContents("The component no longer belongs to the active review.")
        }
        func finish(_ captured: SecurityDeltaSignatureEvidence?, _ refusal: SecurityDeltaSignatureRefusal?) throws -> ComponentReviewSession {
            let revision = try ComponentReviewSession(review: session.review, archiveBytes: session.archiveBytes, sourceURLs: session.sourceURLs,
                live: session.live, entitlementEvidence: session.entitlementEvidence,
                signatureEvidence: session.signatureEvidence + (captured.map { [$0] } ?? []),
                signatureRefusals: session.signatureRefusals + (refusal.map { [$0] } ?? []), admittedReview: session.admittedReview)
            return try derive(revision)
        }
        func unavailable(_ code: String) throws -> ComponentReviewSession {
            let refusal = try SecurityDeltaSignatureRefusal.record(side: side, inventoryID: inventory.id, componentID: componentID,
                relativePath: record.relativePath, architecture: session.review.architecture, code: code, capturedAt: Date())
            return try finish(nil, refusal)
        }
        guard let unit = live[index].units[componentID] else { return try unavailable("source_unavailable") }
        guard unit.inventoryID == inventory.id, unit.relativePath.utf8.elementsEqual(record.relativePath.utf8) else { return try unavailable("evidence_binding_mismatch") }
        var captured: SecurityDeltaSignatureEvidence?, refusalCode: String?
        do {
            let info = declarations.first(where: { $0.componentID == componentID && $0.category == .info })
            if let info, info.state == .present {
                guard let bytes = info.bytes, try CodeUnitPreflight.inspect(unit).infoBytes == bytes else {
                    return try unavailable("source_stale")
                }
                let value = try capture(unit, componentID, side, inventory.id)
                try Task.checkCancellation()
                if try CodeUnitPreflight.inspect(unit).infoBytes == bytes { captured = value }
                else { refusalCode = "source_stale" }
            } else {
                // The signature reader validates the descriptor-bound image itself.
                // An absent or inapplicable Info declaration is not a stale image.
                captured = try capture(unit, componentID, side, inventory.id)
                try Task.checkCancellation()
            }
        } catch {
            if error is CancellationError || Task.isCancelled { throw CancellationError() }
            if let error = error as? CodeSignatureEvidenceError, error == .budgetExceeded { throw SecurityDeltaRefusal(.resourceLimit) }
            if let refusal = error as? SecurityDeltaRefusal { throw refusal }
            if let error = error as? InspectionArchiveError, error == .limit { throw error }
            refusalCode = "source_unavailable"
        }
        if let refusalCode { return try unavailable(refusalCode) }
        guard let captured else { throw InspectionArchiveError.invalid }
        return try finish(captured, nil)
    }
    static func captureEntitlements(_ session: ComponentReviewSession, side: SecurityDeltaSide, componentID: UUID,
                                    reader: any CodeUnitSnapshotReading = CodeUnitEntitlementReader(numericRepresentation: .exposed)) async throws -> SecurityDeltaEntitlementEvidence {
        try Task.checkCancellation()
        guard let live = session.live, live.count == 2 else {
            throw AIRSCore.ReportError.invalidContents("Historical evidence cannot authorize live entitlement capture.")
        }
        let index = side == .previous ? 0 : 1
        let inventory = side == .previous ? session.review.previous : session.review.current
        let declarations = side == .previous ? session.review.previousDeclarations : session.review.currentDeclarations
        guard let record = inventory.components.first(where: { $0.id == componentID }), live[index].inventory.id == inventory.id else {
            throw AIRSCore.ReportError.invalidContents("The component no longer belongs to the active review.")
        }
        func unavailable(_ code: String) throws -> SecurityDeltaEntitlementEvidence {
            try .unavailable(side: side, inventoryID: inventory.id, componentID: componentID, relativePath: record.relativePath,
                             architecture: session.review.architecture, capturedAt: Date(), reason: code)
        }
        guard record.architectures.contains(where: { $0.utf8.elementsEqual(session.review.architecture.rawValue.utf8) }),
              let unit = live[index].units[componentID] else { return try unavailable("slice_unavailable") }
        guard unit.inventoryID == inventory.id, unit.relativePath.utf8.elementsEqual(record.relativePath.utf8) else { return try unavailable("evidence_binding_mismatch") }
        do {
            guard let info = declarations.first(where: { $0.componentID == componentID && $0.category == .info }),
                  info.state == .present, let bytes = info.bytes,
                  try CodeUnitPreflight.inspect(unit).infoBytes == bytes else { return try unavailable("source_stale") }
            let snapshot = try await reader.read(unit: unit, architecture: session.review.architecture)
            try Task.checkCancellation()
            guard snapshot.architecture == session.review.architecture,
                  try CodeUnitPreflight.inspect(unit).infoBytes == bytes else { return try unavailable("source_stale") }
            return try .capture(snapshot: snapshot, side: side, inventoryID: inventory.id, componentID: componentID,
                                relativePath: record.relativePath, capturedAt: Date())
        } catch {
            if error is CancellationError || Task.isCancelled { throw CancellationError() }
            if let refusal = error as? SecurityDeltaRefusal { throw refusal }
            if let error = error as? EntitlementDataError, case .limitExceeded = error { throw SecurityDeltaRefusal(.resourceLimit) }
            if let error = error as? InspectionArchiveError, error == .limit { throw error }
            return try unavailable("source_unavailable")
        }
    }
}
