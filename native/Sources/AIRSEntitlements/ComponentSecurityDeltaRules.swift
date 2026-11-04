import Foundation
import CryptoKit
import AIRSCore

/// Correlation summarizes recorded changes; it does not establish causation.
enum ComponentSecurityDeltaRules {
    struct RelatedResult {
        let findings: [SecurityDeltaFinding]
        let omittedForReferenceLimit: Int
        let omittedForLimitationLimit: Int
        let unspecifiedNumericObservations: Int
        let unrepresentedValueObservations: Int
        let omittedForFindingLimit: Int
        init(findings: [SecurityDeltaFinding], omittedForReferenceLimit: Int, omittedForLimitationLimit: Int = 0, unspecifiedNumericObservations: Int = 0, unrepresentedValueObservations: Int = 0, omittedForFindingLimit: Int = 0) {
            self.findings = findings; self.omittedForReferenceLimit = omittedForReferenceLimit
            self.omittedForLimitationLimit = omittedForLimitationLimit
            self.unspecifiedNumericObservations = unspecifiedNumericObservations; self.unrepresentedValueObservations = unrepresentedValueObservations
            self.omittedForFindingLimit = omittedForFindingLimit
        }
    }
    /// Group only exact typed transitions, then reuse the ancestry rule to
    /// establish that the affected components are structurally related.
    static func repeatedDeclarations(_ observations: [SecurityDeltaObservation], review: ComponentReview) throws -> RelatedResult {
        struct Transition: Encodable {
            let category: SecurityDeltaCategory
            let subject: String
            let disposition: SecurityDeltaDisposition
            let previousState: SecurityDeltaSourceState
            let currentState: SecurityDeltaSourceState
            let previousValue: SecurityDeltaValue?
            let currentValue: SecurityDeltaValue?
        }
        guard observations.count <= 8192, Set(observations.map(\.id)).count == observations.count else { throw InspectionArchiveError.invalid }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        var groups: [Data: [SecurityDeltaObservation]] = [:], remaining = 16 * 1_048_576
        var unspecified = 0, unrepresented = 0
        for observation in observations where observation.category != .componentInventory &&
            [.observedAddition, .observedRemoval, .observedChange].contains(observation.disposition) {
            try Task.checkCancellation()
            guard observation.subject.utf8.count <= 8192 else { throw InspectionArchiveError.limit }
            if let value = observation.previousValue { try value.validate(maxNodes: 100_000, maxBytes: 8 * 1_048_576) }
            if let value = observation.currentValue { try value.validate(maxNodes: 100_000, maxBytes: 8 * 1_048_576) }
            func complete(_ state: SecurityDeltaSourceState, _ value: SecurityDeltaValue?) -> Bool {
                switch state { case .observed: return value != nil; case .absent: return value == nil; default: return false }
            }
            guard complete(observation.previousState, observation.previousValue), complete(observation.currentState, observation.currentValue) else {
                unrepresented += 1; continue
            }
            if try [observation.previousValue, observation.currentValue].compactMap({ $0 }).contains(where: { try $0.compare(to: $0) != .equal }) {
                unspecified += 1; continue
            }
            let key = try encoder.encode(Transition(category: observation.category, subject: observation.subject,
                disposition: observation.disposition, previousState: observation.previousState, currentState: observation.currentState,
                previousValue: observation.previousValue, currentValue: observation.currentValue))
            guard key.count <= remaining else { throw InspectionArchiveError.limit }
            remaining -= key.count
            groups[key, default: []].append(observation)
        }
        var findings: [SecurityDeltaFinding] = [], omitted = 0, omittedLimitations = 0, findingOmissions = 0
        for key in groups.keys.sorted(by: { $0.lexicographicallyPrecedes($1) }) {
            guard let rows = groups[key], rows.count >= 2 else { continue }
            let related = try relatedComponents(rows, review: review)
            omitted += related.omittedForReferenceLimit
            omittedLimitations += related.omittedForLimitationLimit
            for item in related.findings {
                guard findings.count < 2048 else { findingOmissions += 1; continue }
                var hash = SHA256()
                for field in [Data("airs.security-delta.repeated.v1".utf8), key, Data(item.id.utf8)] {
                    var length = UInt64(field.count).bigEndian
                    withUnsafeBytes(of: &length) { hash.update(data: Data($0)) }; hash.update(data: field)
                }
                findings.append(.init(id: hash.finalize().map { String(format: "%02x", $0) }.joined(), kind: .repeatedDeclaration,
                    disposition: item.disposition, title: "A declaration change was recorded in related components",
                    explanation: "The linked components have the same recorded typed declaration transition and share an accepted recorded ancestor. This does not establish causation or runtime behavior.",
                    observationIDs: item.observationIDs, evidence: item.evidence, limitations: item.limitations))
            }
        }
        return .init(findings: findings, omittedForReferenceLimit: omitted, omittedForLimitationLimit: omittedLimitations,
                     unspecifiedNumericObservations: unspecified, unrepresentedValueObservations: unrepresented, omittedForFindingLimit: findingOmissions)
    }
    /// Group changes only when both inventories record the same accepted
    /// ancestor relationship. Identifiers and filenames are never joins.
    static func relatedComponents(_ observations: [SecurityDeltaObservation], review: ComponentReview) throws -> RelatedResult {
        try review.previous.validate(); try review.current.validate()
        guard observations.count <= 8192, Set(observations.map(\.id)).count == observations.count else { throw InspectionArchiveError.invalid }
        guard observations.allSatisfy({ $0.limitations.count <= 32 }) else { throw SecurityDeltaRefusal(.limitationLimit) }
        let old = Dictionary(uniqueKeysWithValues: review.previous.components.map { ($0.id, $0) })
        let new = Dictionary(uniqueKeysWithValues: review.current.components.map { ($0.id, $0) })
        var pairs: [ExactUTF8Key: (ComponentRecord, ComponentRecord)] = [:]
        var additions: [ExactUTF8Key: ComponentRecord] = [:], removals: [ExactUTF8Key: ComponentRecord] = [:]
        for match in review.matching.matches {
            if match.relation == .addedWithinScope, let id = match.currentID, match.previousID == nil, let component = new[id] {
                additions[ExactUTF8Key(component.relativePath)] = component
            } else if match.relation == .removedWithinScope, let id = match.previousID, match.currentID == nil, let component = old[id] {
                removals[ExactUTF8Key(component.relativePath)] = component
            }
        }
        for match in review.matching.matches where match.relation == .sameLocation {
            guard let a = match.previousID.flatMap({ old[$0] }), let b = match.currentID.flatMap({ new[$0] }),
                  a.relativePath.utf8.elementsEqual(b.relativePath.utf8), pairs[ExactUTF8Key(a.relativePath)] == nil else { throw InspectionArchiveError.invalid }
            pairs[ExactUTF8Key(a.relativePath)] = (a, b)
        }
        func ancestors(_ record: ComponentRecord, records: [UUID: ComponentRecord]) throws -> [ExactUTF8Key: [ComponentRecord]] {
            var result: [ExactUTF8Key: [ComponentRecord]] = [:], chain: [ComponentRecord] = [], current = record
            while let parentID = current.parentID {
                try Task.checkCancellation()
                guard let parent = records[parentID], chain.count < 128 else { throw InspectionArchiveError.invalid }
                chain.append(current); result[ExactUTF8Key(parent.relativePath)] = chain; current = parent
            }
            return result
        }
        struct Member { let observation: SecurityDeltaObservation; let oldChain: [ComponentRecord]; let newChain: [ComponentRecord] }
        var grouped: [ExactUTF8Key: [Member]] = [:], usedPaths = Set<ExactUTF8Key>()
        let ordered = observations.sorted { $0.id < $1.id }
        for observation in ordered where [.observedAddition, .observedRemoval, .observedChange].contains(observation.disposition) {
            try Task.checkCancellation()
            let path = ExactUTF8Key(observation.componentPath)
            guard !usedPaths.contains(path) else { continue }
            if let (a, b) = pairs[path],
               observation.evidence.contains(where: { $0.side == .previous && $0.inventoryID == review.previous.id && $0.componentID == a.id }),
               observation.evidence.contains(where: { $0.side == .current && $0.inventoryID == review.current.id && $0.componentID == b.id }) {
                usedPaths.insert(path)
                let oldAncestors = try ancestors(a, records: old), newAncestors = try ancestors(b, records: new)
                for (ancestor, oldChain) in oldAncestors {
                    guard pairs[ancestor] != nil, let newChain = newAncestors[ancestor] else { continue }
                    grouped[ancestor, default: []].append(.init(observation: observation, oldChain: oldChain, newChain: newChain))
                }
            } else if observation.category == .componentInventory, observation.subject == "component" {
                let addition = observation.disposition == .observedAddition ? additions[path] : nil
                let removal = observation.disposition == .observedRemoval ? removals[path] : nil
                guard let component = addition ?? removal else { continue }
                let side: SecurityDeltaSide = addition != nil ? .current : .previous
                let inventory = side == .current ? review.current : review.previous
                let other = side == .current ? review.previous : review.current
                guard observation.evidence.contains(where: { $0.side == side && $0.inventoryID == inventory.id && $0.componentID == component.id }),
                      observation.evidence.contains(where: { $0.side != side && $0.inventoryID == other.id && $0.componentID == nil && $0.evidenceKey == "scope" }) else { continue }
                usedPaths.insert(path)
                let chain = try ancestors(component, records: side == .current ? new : old)
                for (ancestor, records) in chain where pairs[ancestor] != nil {
                    grouped[ancestor, default: []].append(.init(observation: observation,
                        oldChain: side == .previous ? records : [], newChain: side == .current ? records : []))
                }
            }
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        var findings: [SecurityDeltaFinding] = [], omitted = 0, omittedLimitations = 0
        for key in grouped.keys.sorted(by: { $0.bytes.lexicographicallyPrecedes($1.bytes) }) {
            guard let members = grouped[key], members.count >= 2 else { continue }
            let selected = members.sorted { $0.observation.id < $1.observation.id }
            var references: [(Data, SecurityDeltaEvidenceReference)] = [], seen = Set<Data>()
            func append(_ reference: SecurityDeltaEvidenceReference) throws {
                guard references.count <= 32 else { return }
                let bytes = try encoder.encode(reference)
                if seen.insert(bytes).inserted { references.append((bytes, reference)) }
            }
            if let (ancestorOld, ancestorNew) = pairs[key] {
                for (side, inventory, component) in [(SecurityDeltaSide.previous, review.previous, ancestorOld), (.current, review.current, ancestorNew)] {
                    try append(.init(side: side, inventoryID: inventory.id, componentID: component.id,
                                     category: .componentInventory, relativeSource: component.relativePath, evidenceKey: "component"))
                }
            }
            for member in selected {
                for reference in member.observation.evidence { try append(reference) }
                for (side, inventory, chain) in [(SecurityDeltaSide.previous, review.previous, member.oldChain), (.current, review.current, member.newChain)] {
                    for record in chain {
                        try append(.init(side: side, inventoryID: inventory.id, componentID: record.id,
                            category: .componentInventory, relativeSource: record.relativePath, evidenceKey: "parentID"))
                    }
                }
            }
            guard references.count <= 32 else { omitted += 1; continue }
            var limitations: [(Data, SecurityDeltaReason)] = [], seenLimitations = Set<Data>()
            for member in selected {
                for limitation in member.observation.limitations {
                    guard limitation.code.utf8.count <= 256, limitation.diagnostic.utf8.count <= 4096 else { throw SecurityDeltaRefusal(.diagnosticLimit) }
                    if limitations.count <= 32 {
                        let encoded = try encoder.encode(limitation)
                        if seenLimitations.insert(encoded).inserted { limitations.append((encoded, limitation)) }
                    }
                }
            }
            guard limitations.count <= 32 else { omittedLimitations += 1; continue }
            var hash = SHA256()
            let fields = [Data("airs.security-delta.related.v1".utf8), Data(key.bytes)] + selected.map { Data($0.observation.id.utf8) }
            for field in fields { var length = UInt64(field.count).bigEndian; withUnsafeBytes(of: &length) { hash.update(data: Data($0)) }; hash.update(data: field) }
            findings.append(.init(id: hash.finalize().map { String(format: "%02x", $0) }.joined(), kind: .relatedComponents,
                disposition: .observedChange, title: "Changes share a recorded component ancestor",
                explanation: "The linked component changes share an accepted recorded ancestor. Added or removed components are linked only through their observed side and recorded scope. This structural relationship does not establish causation or runtime behavior.",
                observationIDs: selected.map { $0.observation.id },
                evidence: references.sorted { $0.0.lexicographicallyPrecedes($1.0) }.map(\.1),
                limitations: limitations.sorted { $0.0.lexicographicallyPrecedes($1.0) }.map(\.1)))
        }
        return .init(findings: findings, omittedForReferenceLimit: omitted, omittedForLimitationLimit: omittedLimitations)
    }

    static func sameComponent(_ observations: [SecurityDeltaObservation], review: ComponentReview) throws -> [SecurityDeltaFinding] {
        guard observations.count <= 8192,
              observations.allSatisfy({ $0.id.utf8.count <= 256 && $0.componentPath.utf8.count <= 4096 &&
                  $0.subject.utf8.count <= 8192 && $0.evidence.count <= 32 && $0.limitations.count <= 32 &&
                  $0.evidence.allSatisfy { $0.relativeSource.utf8.count <= 4096 && ($0.evidenceKey?.utf8.count ?? 0) <= 8192 } &&
                  $0.limitations.allSatisfy { $0.code.utf8.count <= 256 && $0.diagnostic.utf8.count <= 4096 } }),
              Set(observations.map(\.id)).count == observations.count else { throw InspectionArchiveError.invalid }
        let categories: [SecurityDeltaCategory] = [.informationPropertyList, .loadCommands, .entitlements, .privacyManifest, .signatureEvidence]
        var accepted: [ExactUTF8Key: (UUID, UUID)] = [:]
        for match in review.matching.matches where match.relation == .sameLocation {
            guard let oldID = match.previousID, let newID = match.currentID,
                  let old = review.previous.components.first(where: { $0.id == oldID }),
                  let new = review.current.components.first(where: { $0.id == newID }),
                  old.relativePath.utf8.elementsEqual(new.relativePath.utf8) else { throw InspectionArchiveError.invalid }
            let key = ExactUTF8Key(old.relativePath)
            guard accepted[key] == nil else { throw InspectionArchiveError.invalid }
            accepted[key] = (oldID, newID)
        }
        var groups: [ExactUTF8Key: [SecurityDeltaObservation]] = [:]
        for observation in observations {
            try Task.checkCancellation()
            guard categories.contains(observation.category),
                  [.observedAddition, .observedRemoval, .observedChange].contains(observation.disposition) else { continue }
            let key = ExactUTF8Key(observation.componentPath)
            guard let (oldID, newID) = accepted[key],
                  observation.evidence.contains(where: { $0.side == .previous && $0.inventoryID == review.previous.id && $0.componentID == oldID && $0.category == observation.category }),
                  observation.evidence.contains(where: { $0.side == .current && $0.inventoryID == review.current.id && $0.componentID == newID && $0.category == observation.category }),
                  observation.evidence.allSatisfy({ reference in
                      switch reference.side {
                      case .previous: return reference.inventoryID == review.previous.id && reference.componentID == oldID
                      case .current: return reference.inventoryID == review.current.id && reference.componentID == newID
                      }
                  }) else { throw InspectionArchiveError.invalid }
            groups[key, default: []].append(observation)
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        var findings: [SecurityDeltaFinding] = []
        for key in groups.keys.sorted(by: { $0.bytes.lexicographicallyPrecedes($1.bytes) }) {
            guard let rows = groups[key] else { continue }
            // Choose one complete observation per category. The finding only
            // summarizes those observations, not every change in the component.
            let selected = categories.compactMap { category in
                rows.filter { $0.category == category }.sorted { left, right in
                    if !left.subject.utf8.elementsEqual(right.subject.utf8) { return left.subject.utf8.lexicographicallyPrecedes(right.subject.utf8) }
                    return left.id < right.id
                }.first
            }
            guard selected.count >= 2 else { continue }
            var references: [(Data, SecurityDeltaEvidenceReference)] = [], seen = Set<Data>()
            var limitations: [(Data, SecurityDeltaReason)] = [], seenLimits = Set<Data>()
            for observation in selected {
                for reference in observation.evidence {
                    let bytes = try encoder.encode(reference)
                    if seen.insert(bytes).inserted { references.append((bytes, reference)) }
                }
                for limitation in observation.limitations {
                    let bytes = try encoder.encode(limitation)
                    if seenLimits.insert(bytes).inserted { limitations.append((bytes, limitation)) }
                }
            }
            guard references.count <= 32, !references.isEmpty else { throw InspectionArchiveError.limit }
            var hash = SHA256()
            for field in ["airs.security-delta.correlation.v1"] + selected.map(\.id) {
                let bytes = Data(field.utf8); var length = UInt64(bytes.count).bigEndian
                withUnsafeBytes(of: &length) { hash.update(data: Data($0)) }; hash.update(data: bytes)
            }
            let id = hash.finalize().map { String(format: "%02x", $0) }.joined()
            findings.append(.init(id: id, kind: .componentMultiCategory, disposition: .observedChange,
                title: "Multiple declaration categories changed in one component",
                explanation: "The linked observations were recorded at the same accepted component location. Their relationship does not establish causation or runtime behavior.",
                observationIDs: selected.map(\.id),
                evidence: references.sorted { $0.0.lexicographicallyPrecedes($1.0) }.map(\.1),
                limitations: limitations.sorted { $0.0.lexicographicallyPrecedes($1.0) }.map(\.1)))
        }
        return findings
    }
}
