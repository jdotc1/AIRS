import Foundation
import CryptoKit
import AIRSCore
import EntitlementDiffCore

/// Pure analysis over an already captured review. It does not open a bundle.
/// Additional evidence categories and correlation are added separately.
public enum ComponentSecurityDeltaAnalyzer {
    public static func analyze(review: ComponentReview, options: SecurityDeltaOptions = .default) throws -> ComponentSecurityDeltaReport {
        try analyze(input: .init(review: review), options: options)
    }

    public static func analyze(input: SecurityDeltaInput, options: SecurityDeltaOptions = .default) throws -> ComponentSecurityDeltaReport {
        try securityDeltaBoundary { try analyzeAdmitted(input: input, options: options) }
    }

    private static func analyzeAdmitted(input: SecurityDeltaInput, options: SecurityDeltaOptions) throws -> ComponentSecurityDeltaReport {
        let review = input.review
        try options.validate()
        try Task.checkCancellation()
        guard review.previous.components.count + review.current.components.count <= 128 else { throw SecurityDeltaRefusal(.componentLimit) }
        for inventory in [review.previous, review.current] {
            guard Set(inventory.components.map(\.id)).count == inventory.components.count,
                  Set(inventory.components.map { Data($0.relativePath.utf8) }).count == inventory.components.count else {
                throw SecurityDeltaRefusal(.duplicateComponentIdentity)
            }
        }
        // Two guards of three comparisons each keep every condition list short for the type
        // checker. Both throw the same refusal, in the same order as one six-term guard.
        guard review.previousDeclarations.count <= 384, review.currentDeclarations.count <= 384,
              review.entitlementResults.count <= 128 else { throw SecurityDeltaRefusal(.sourceRecordLimit) }
        guard input.signatureEvidence.count <= 128, input.entitlementEvidence.count <= 128,
              input.signatureRefusals.count <= 128 else { throw SecurityDeltaRefusal(.sourceRecordLimit) }
        let retainedByteLimit: Int = 32 * 1_048_576
        var retainedBytes = 0
        for side in [review.previousDeclarations, review.currentDeclarations] {
            for item in side {
                let count = item.bytes?.count ?? 0
                guard count <= retainedByteLimit - retainedBytes else { throw SecurityDeltaRefusal(.retainedByteLimit) }
                retainedBytes += count
            }
        }
        for item in input.signatureEvidence {
            guard item.sourceBytes.count <= retainedByteLimit - retainedBytes else { throw SecurityDeltaRefusal(.retainedByteLimit) }
            retainedBytes += item.sourceBytes.count
        }
        for item in input.entitlementEvidence {
            guard item.sourceBytes.count <= retainedByteLimit - retainedBytes else { throw SecurityDeltaRefusal(.retainedByteLimit) }
            retainedBytes += item.sourceBytes.count
            if let value = item.values { try value.validate(maxNodes: 10_000, maxBytes: 8 * 1_048_576) }
        }
        for item in input.signatureRefusals {
            guard item.sourceBytes.count <= retainedByteLimit - retainedBytes else { throw SecurityDeltaRefusal(.retainedByteLimit) }
            retainedBytes += item.sourceBytes.count
        }
        var remainingNodes = 100_000, remainingValueBytes = 16 * 1_048_576
        func charge(_ count: Int) throws {
            guard count >= 0, count <= remainingValueBytes else { throw SecurityDeltaRefusal(.decodedByteLimit) }
            remainingValueBytes -= count
        }
        func inspect(_ value: EntitlementValue, depth: Int) throws {
            guard depth <= 32 else { throw SecurityDeltaRefusal(.typedDepthLimit) }
            guard remainingNodes > 0 else { throw SecurityDeltaRefusal(.typedNodeLimit) }
            remainingNodes -= 1
            switch value {
            case .boolean: try charge(1)
            case .integer, .unsignedInteger, .real, .date: try charge(8)
            case .string(let value): try charge(value.utf8.count)
            case .data(let value): try charge(value.count)
            case .array(let values):
                guard values.count <= remainingNodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
                for item in values { try inspect(item, depth: depth + 1) }
            case .dictionary(let dictionary):
                guard dictionary.entries.count <= remainingNodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
                for entry in dictionary.entries { try charge(entry.key.utf8.count); try inspect(entry.value, depth: depth + 1) }
            }
        }
        func inspectStrict(_ value: SecurityDeltaValue, depth: Int) throws {
            guard depth <= 32 else { throw SecurityDeltaRefusal(.typedDepthLimit) }
            guard remainingNodes > 0 else { throw SecurityDeltaRefusal(.typedNodeLimit) }
            remainingNodes -= 1
            switch value {
            case .boolean: try charge(1)
            case .signed, .unsigned, .realBits, .dateBits: try charge(8)
            case .normalizedInteger(let value), .string(let value): try charge(value.utf8.count)
            case .data(let value): try charge(value.count)
            case .array(let values):
                guard values.count <= remainingNodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
                for item in values { try inspectStrict(item, depth: depth + 1) }
            case .dictionary(let values):
                guard values.count <= remainingNodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
                for entry in values { try charge(entry.key.utf8.count); try inspectStrict(entry.value, depth: depth + 1) }
            }
        }
        for item in input.entitlementEvidence {
            try Task.checkCancellation()
            if let value = item.values { try inspectStrict(value, depth: 0) }
        }
        for outcome in review.entitlementResults {
            try Task.checkCancellation()
            if case .compared(_, _, let report) = outcome {
                try inspect(.dictionary(report.previous.entitlements), depth: 0)
                try inspect(.dictionary(report.current.entitlements), depth: 0)
            }
        }
        let admitted = try ComponentComparison.review(previous: review.previous, current: review.current,
            architecture: review.architecture, entitlementResults: review.entitlementResults,
            previousDeclarations: review.previousDeclarations, currentDeclarations: review.currentDeclarations)
        var signatures = Set<String>()
        for item in input.signatureEvidence {
            let inventory = item.side == .previous ? admitted.previous : admitted.current
            let evidence = item.document.evidence
            guard item.inventoryID == inventory.id,
                  let component = inventory.components.first(where: { $0.id == evidence.componentID }),
                  component.relativePath.utf8.elementsEqual(evidence.componentRelativePath.utf8) else { throw SecurityDeltaRefusal(.evidenceBindingMismatch) }
            guard signatures.insert(item.side.rawValue + ":" + evidence.componentID.uuidString).inserted else { throw SecurityDeltaRefusal(.duplicateObservationIdentity) }
        }
        for item in input.signatureRefusals {
            let inventory = item.side == .previous ? admitted.previous : admitted.current
            guard item.inventoryID == inventory.id, item.architecture == admitted.architecture,
                  let component = inventory.components.first(where: { $0.id == item.componentID }),
                  component.relativePath.utf8.elementsEqual(item.relativePath.utf8) else { throw SecurityDeltaRefusal(.evidenceBindingMismatch) }
            guard signatures.insert(item.side.rawValue + ":" + item.componentID.uuidString).inserted else { throw SecurityDeltaRefusal(.duplicateObservationIdentity) }
        }
        var strictEntitlements = Set<String>()
        for item in input.entitlementEvidence {
            let inventory = item.side == .previous ? admitted.previous : admitted.current
            guard item.inventoryID == inventory.id, item.architecture == admitted.architecture,
                  let component = inventory.components.first(where: { $0.id == item.componentID }),
                  component.relativePath.utf8.elementsEqual(item.relativePath.utf8) else { throw SecurityDeltaRefusal(.evidenceBindingMismatch) }
            guard strictEntitlements.insert(item.side.rawValue + ":" + item.componentID.uuidString).inserted else { throw SecurityDeltaRefusal(.duplicateObservationIdentity) }
        }
        let supplied = review.matching.matches
        guard supplied.count == admitted.matching.matches.count,
              Set(supplied.map(\.id)).count == supplied.count else { throw InspectionArchiveError.invalid }
        for match in admitted.matching.matches {
            guard let original = supplied.first(where: { $0.id == match.id }),
                  original.previousID == match.previousID, original.currentID == match.currentID,
                  original.relation == match.relation else { throw SecurityDeltaRefusal(.componentCorrespondenceUnaccepted) }
        }
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        func exactSorted(_ values: [String]) -> [String] { values.sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) } }
        func canonicalScope(_ scope: InventoryScope) -> InventoryScope {
            .init(searchedLocations: exactSorted(scope.searchedLocations), completion: scope.completion,
                  exclusions: exactSorted(scope.exclusions), issues: exactSorted(scope.issues))
        }
        func canonicalRecord(_ record: ComponentRecord) -> ComponentRecord {
            .init(id: record.id, parentID: record.parentID, relativePath: record.relativePath, kind: record.kind,
                  declaredBundleID: record.declaredBundleID, declaredVersion: record.declaredVersion,
                  architectures: exactSorted(record.architectures), minimumOSByArchitecture: record.minimumOSByArchitecture,
                  readIssues: exactSorted(record.readIssues))
        }
        guard try encoder.encode(review.matching.previousScope) == encoder.encode(review.previous.scope),
              try encoder.encode(review.matching.currentScope) == encoder.encode(review.current.scope) else { throw InspectionArchiveError.invalid }
        let previous = admitted.previous.components, current = admitted.current.components
        var observations: [SecurityDeltaObservation] = []
        var findings: [SecurityDeltaFinding] = []
        var lastAdded: SecurityDeltaObservation?, omittedObservations = 0
        let reviewFields = [admitted.previous.id.uuidString, admitted.current.id.uuidString, admitted.architecture.rawValue]

        func digest(_ fields: [Data]) -> String {
            var hasher = SHA256()
            for field in fields {
                var length = UInt64(field.count).bigEndian
                withUnsafeBytes(of: &length) { hasher.update(data: Data($0)) }
                hasher.update(data: field)
            }
            return hasher.finalize().map { String(format: "%02x", $0) }.joined()
        }
        // Bind derived IDs to captured input, including scope, exact component
        // records and category evidence. This is not verification of original files.
        var basisHasher = SHA256(), basisBytes = 0
        func appendBasis(_ bytes: Data) throws {
            guard bytes.count <= retainedByteLimit - basisBytes else { throw SecurityDeltaRefusal(.retainedByteLimit) }
            basisBytes += bytes.count
            var length = UInt64(bytes.count).bigEndian
            withUnsafeBytes(of: &length) { basisHasher.update(data: Data($0)) }
            basisHasher.update(data: bytes)
        }
        try appendBasis(Data("airs.security-delta.basis.v1".utf8))
        try appendBasis(Data(ComponentSecurityDeltaReport.modelVersion.utf8))
        try appendBasis(Data(ComponentSecurityDeltaReport.rulesVersion.utf8))
        try appendBasis(encoder.encode(options))
        try appendBasis(Data(admitted.architecture.rawValue.utf8))
        for (side, inventory) in [("previous", admitted.previous), ("current", admitted.current)] {
            try appendBasis(Data(side.utf8))
            try appendBasis(Data(inventory.id.uuidString.utf8))
            try appendBasis(encoder.encode(inventory.capturedAt))
            try appendBasis(encoder.encode(canonicalScope(inventory.scope)))
            try appendBasis(Data(String(inventory.components.count).utf8))
            for component in inventory.components.sorted(by: { $0.relativePath.utf8.lexicographicallyPrecedes($1.relativePath.utf8) }) {
                try appendBasis(encoder.encode(canonicalRecord(component)))
            }
        }
        for (side, declarations) in [("previous-declarations", admitted.previousDeclarations), ("current-declarations", admitted.currentDeclarations)] {
            try appendBasis(Data(side.utf8))
            try appendBasis(Data(String(declarations.count).utf8))
            for item in declarations.sorted(by: { ($0.componentID.uuidString, $0.category.rawValue) < ($1.componentID.uuidString, $1.category.rawValue) }) {
                try appendBasis(encoder.encode(item))
            }
        }
        for outcome in admitted.entitlementResults.sorted(by: { $0.matchID.uuidString < $1.matchID.uuidString }) {
            try appendBasis(Data(outcome.matchID.uuidString.utf8))
            switch outcome {
            case .compared(_, _, let report):
                try appendBasis(Data("compared".utf8))
                // Notices are reconstructed presentation state, including the
                // import-only saved-baseline notice; bind the recorded snapshots.
                let old = try encoder.encode(report.previous), new = try encoder.encode(report.current)
                guard old.count <= 8 * 1_048_576, new.count <= 8 * 1_048_576 else { throw SecurityDeltaRefusal(.retainedByteLimit) }
                try appendBasis(old); try appendBasis(new)
            case .unavailable(_, _, let reason): try appendBasis(Data("unavailable".utf8)); try appendBasis(Data(reason.utf8))
            }
        }
        try appendBasis(Data("signature-evidence".utf8))
        try appendBasis(Data(String(input.signatureEvidence.count).utf8))
        for item in input.signatureEvidence.sorted(by: {
            ($0.side.rawValue, $0.document.evidence.componentID.uuidString) < ($1.side.rawValue, $1.document.evidence.componentID.uuidString)
        }) {
            try appendBasis(Data(item.side.rawValue.utf8))
            try appendBasis(Data(item.inventoryID.uuidString.utf8))
            try appendBasis(item.sourceBytes)
        }
        try appendBasis(Data("strict-entitlement-evidence".utf8))
        try appendBasis(Data(String(input.entitlementEvidence.count).utf8))
        for item in input.entitlementEvidence.sorted(by: { ($0.side.rawValue, $0.componentID.uuidString) < ($1.side.rawValue, $1.componentID.uuidString) }) {
            try appendBasis(item.sourceBytes)
        }
        try appendBasis(Data("signature-refusals".utf8))
        try appendBasis(Data(String(input.signatureRefusals.count).utf8))
        for item in input.signatureRefusals.sorted(by: { ($0.side.rawValue, $0.componentID.uuidString) < ($1.side.rawValue, $1.componentID.uuidString) }) { try appendBasis(item.sourceBytes) }
        let basis = basisHasher.finalize().map { String(format: "%02x", $0) }.joined()
        func stableID(_ fields: [String]) -> String { digest((["airs.security-delta.v1", basis] + reviewFields + fields).map { Data($0.utf8) }) }
        func ref(_ side: SecurityDeltaSide, _ inventory: ComponentInventory, _ item: ComponentRecord, _ key: String) -> SecurityDeltaEvidenceReference {
            .init(side: side, inventoryID: inventory.id, componentID: item.id, category: .componentInventory,
                  relativeSource: item.relativePath, evidenceKey: key)
        }
        var retainedNodes = 100_000, retainedValueBytes = 16 * 1_048_576, retainedTextBytes = 16 * 1_048_576
        func chargeText(_ value: String, maximum: Int = 4096) throws {
            let count = value.utf8.count
            guard count <= maximum else { throw SecurityDeltaRefusal(.diagnosticLimit) }
            guard count <= retainedTextBytes else { throw SecurityDeltaRefusal(.retainedByteLimit) }
            retainedTextBytes -= count
        }
        func chargeRetained(_ value: SecurityDeltaValue, depth: Int = 0) throws {
            guard depth <= 32 else { throw SecurityDeltaRefusal(.typedDepthLimit) }
            guard retainedNodes > 0 else { throw SecurityDeltaRefusal(.typedNodeLimit) }
            retainedNodes -= 1
            func bytes(_ count: Int) throws {
                guard count <= retainedValueBytes else { throw SecurityDeltaRefusal(.decodedByteLimit) }
                retainedValueBytes -= count
            }
            switch value {
            case .boolean: try bytes(1)
            case .signed, .unsigned, .realBits, .dateBits: try bytes(8)
            case .normalizedInteger(let text), .string(let text): try bytes(text.utf8.count)
            case .data(let data): try bytes(data.count)
            case .array(let values):
                guard values.count <= retainedNodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
                for value in values { try chargeRetained(value, depth: depth + 1) }
            case .dictionary(let entries):
                guard entries.count <= retainedNodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
                for entry in entries { try bytes(entry.key.utf8.count); try chargeRetained(entry.value, depth: depth + 1) }
            }
        }
        func add(_ match: ComponentMatch, _ a: ComponentRecord?, _ b: ComponentRecord?, subject: String,
                 disposition: SecurityDeltaDisposition, before: SecurityDeltaSourceState, after: SecurityDeltaSourceState,
                 old: SecurityDeltaValue? = nil, new: SecurityDeltaValue? = nil,
                 reason: SecurityDeltaReason? = nil, category: SecurityDeltaCategory = .componentInventory,
                 sourceReferences: [SecurityDeltaEvidenceReference]? = nil) throws {
            guard let location = a?.relativePath ?? b?.relativePath else { throw InspectionArchiveError.invalid }
            lastAdded = nil
            guard observations.count < options.maximumObservations else { omittedObservations += 1; return }
            if let old { try chargeRetained(old) }
            if let new { try chargeRetained(new) }
            var references = sourceReferences ?? [a.map { ref(.previous, admitted.previous, $0, subject) }, b.map { ref(.current, admitted.current, $0, subject) }].compactMap { $0 }
            if sourceReferences == nil && (before == .absent || before == .unexamined) {
                references.append(.init(side: .previous, inventoryID: admitted.previous.id, componentID: nil,
                    category: .componentInventory, relativeSource: location, evidenceKey: "scope"))
            }
            if sourceReferences == nil && (after == .absent || after == .unexamined) {
                references.append(.init(side: .current, inventoryID: admitted.current.id, componentID: nil,
                    category: .componentInventory, relativeSource: location, evidenceKey: "scope"))
            }
            try chargeText(location)
            try chargeText(subject, maximum: category == .loadCommands ? 8192 : 4096)
            if let reason { try chargeText(reason.code, maximum: 256); try chargeText(reason.diagnostic) }
            for reference in references {
                try chargeText(reference.relativeSource)
                if let key = reference.evidenceKey { try chargeText(key, maximum: reference.category == .loadCommands ? 8192 : 4096) }
                if let architecture = reference.architecture { try chargeText(architecture, maximum: 256) }
            }
            let id = stableID([match.id.uuidString, category.rawValue, subject, disposition.rawValue, before.rawValue, after.rawValue,
                try old.map { try encoder.encode($0).base64EncodedString() } ?? "", try new.map { try encoder.encode($0).base64EncodedString() } ?? ""])
            let observation = SecurityDeltaObservation(id: id, category: category, componentPath: location, subject: subject,
                disposition: disposition, previousState: before, currentState: after, previousValue: old, currentValue: new,
                evidence: references, limitations: reason.map { [$0] } ?? [])
            observations.append(observation); lastAdded = observation
        }
        var declarationBytesRemaining = 16 * 1_048_576
        func normalizedIntegers(_ value: SecurityDeltaValue) -> Bool {
            switch value {
            case .normalizedInteger: return true
            case .array(let values): return values.contains(where: normalizedIntegers)
            case .dictionary(let entries): return entries.contains { normalizedIntegers($0.value) }
            default: return false
            }
        }
        func compareDeclarations(_ match: ComponentMatch, _ a: ComponentRecord, _ b: ComponentRecord,
                                 _ sourceCategory: DeclarationCategory, _ category: SecurityDeltaCategory) throws {
            let old = admitted.previousDeclarations.first { $0.componentID == a.id && $0.category == sourceCategory }
            let new = admitted.currentDeclarations.first { $0.componentID == b.id && $0.category == sourceCategory }
            func state(_ item: DeclarationObservation?, record: ComponentRecord,
                       observations: [DeclarationObservation]) -> (SecurityDeltaSourceState, Bool) {
                guard let item else { return (.unexamined, false) }
                if item.state == .unavailable { return (.unavailable, false) }
                if sourceCategory == .loadCommands {
                    guard item.relativeSource.utf8.elementsEqual(record.relativePath.utf8) else { return (.unavailable, true) }
                    return (.observed, false)
                }
                if record.kind == "appDeclarations" {
                    let path = sourceCategory == .info ? "Contents/Info.plist" : "Contents/Resources/PrivacyInfo.xcprivacy"
                    guard record.relativePath.utf8.elementsEqual("Contents/Info.plist".utf8), item.relativeSource.utf8.elementsEqual(path.utf8) else { return (.unavailable, true) }
                    return (item.state == .present ? .observed : .absent, false)
                }
                guard let location = try? CodeUnitPreflight.declarationLocations(relativePath: record.relativePath),
                      let info = observations.first(where: { $0.componentID == record.id && $0.category == .info && $0.state == .present }),
                      info.relativeSource.utf8.elementsEqual(location.infoPath.utf8), let bytes = info.bytes,
                      let plist = (try? PropertyListSerialization.propertyList(from: bytes, format: nil)) as? [String: Any],
                      let executable = plist["CFBundleExecutable"] as? String, !executable.isEmpty,
                      executable != ".", executable != "..", executable.utf8.count <= 255,
                      !executable.contains("/"), !executable.contains("\\"), !executable.contains("\0"),
                      (location.executablePrefix + executable).utf8.elementsEqual(record.relativePath.utf8) else { return (.unavailable, true) }
                let expected = sourceCategory == .info ? location.infoPath : location.resourcePath + "/PrivacyInfo.xcprivacy"
                guard item.relativeSource.utf8.elementsEqual(expected.utf8) else { return (.unavailable, true) }
                return (item.state == .present ? .observed : .absent, false)
            }
            let (oldState, oldBindingFailed) = state(old, record: a, observations: admitted.previousDeclarations)
            let (newState, newBindingFailed) = state(new, record: b, observations: admitted.currentDeclarations)
            func source(_ side: SecurityDeltaSide, _ inventory: ComponentInventory, _ record: ComponentRecord,
                        _ item: DeclarationObservation?, key: String) -> SecurityDeltaEvidenceReference {
                .init(side: side, inventoryID: inventory.id, componentID: record.id,
                      category: item == nil ? .componentInventory : category,
                      relativeSource: item?.relativeSource ?? record.relativePath,
                      architecture: item?.architecture, evidenceKey: item == nil ? "declaration:not-captured:" + sourceCategory.rawValue : key)
            }
            func refs(_ key: String) -> [SecurityDeltaEvidenceReference] {
                var references = [source(.previous, admitted.previous, a, old, key: key), source(.current, admitted.current, b, new, key: key)]
                if sourceCategory == .info || sourceCategory == .privacy {
                    for (side, inventory, record, declarations) in [(SecurityDeltaSide.previous, admitted.previous, a, admitted.previousDeclarations),
                                                                  (.current, admitted.current, b, admitted.currentDeclarations)] {
                        let info = declarations.first { $0.componentID == record.id && $0.category == .info }
                        references.append(.init(side: side, inventoryID: inventory.id, componentID: record.id,
                            category: info == nil ? .componentInventory : .informationPropertyList,
                            relativeSource: info?.relativeSource ?? record.relativePath,
                            evidenceKey: info == nil ? "declaration:not-captured:info" : "declaration:binding:CFBundleExecutable"))
                    }
                }
                return references
            }
            let knownOld = oldState == .observed || oldState == .absent
            let knownNew = newState == .observed || newState == .absent
            let presence: SecurityDeltaDisposition
            if !knownOld || !knownNew { presence = .unresolved }
            else if oldState == newState { presence = .unchanged }
            else { presence = oldState == .absent ? .observedAddition : .observedRemoval }
            let missingReason = oldBindingFailed || newBindingFailed ?
                SecurityDeltaReason(code: "source_binding_unverified", diagnostic: "A recorded declaration cannot be bound to this component and its conventional source path.") :
                SecurityDeltaReason(code: "source_unavailable", diagnostic: "A declaration was unavailable or not captured; absence is not inferred.")
            try add(match, a, b, subject: "presence", disposition: presence, before: oldState, after: newState,
                    reason: presence == .unresolved ? missingReason : nil, category: category, sourceReferences: refs("declaration:presence"))
            func finding(_ observation: SecurityDeltaObservation, title: String) throws {
                findings.append(.init(id: stableID(["declaration-finding", observation.id]), kind: .declarationChanged,
                    disposition: observation.disposition, title: title,
                    explanation: category == .privacyManifest ? "Recorded privacy declaration changed; absence is not a compliance determination." :
                        (category == .loadCommands ? "Recorded loader declaration changed; this does not establish that a library was loaded." : "Recorded Info.plist declaration changed within the compared allowlist."),
                    observationIDs: [observation.id], evidence: observation.evidence, limitations: observation.limitations))
            }
            if presence == .observedAddition || presence == .observedRemoval, let observation = lastAdded {
                try finding(observation, title: "Recorded declaration presence changed")
            }
            guard knownOld && knownNew else { return }
            for item in [old, new].compactMap({ $0 }) where item.state == .present {
                let size = item.bytes?.count ?? 0
                guard size <= declarationBytesRemaining else { throw SecurityDeltaRefusal(.retainedByteLimit) }
                declarationBytesRemaining -= size
            }
            func values(_ item: DeclarationObservation?, state: SecurityDeltaSourceState) throws -> EntitlementDictionary {
                guard state == .observed else { return EntitlementDictionary() }
                guard let item else { throw InspectionArchiveError.invalid }
                return try item.values()
            }
            let before = try values(old, state: oldState)
            let after = try values(new, state: newState)
            let oldEntries = Dictionary(uniqueKeysWithValues: before.entries.map { (ExactUTF8Key($0.key), $0) })
            let newEntries = Dictionary(uniqueKeysWithValues: after.entries.map { (ExactUTF8Key($0.key), $0) })
            let keys = Set(oldEntries.keys).union(newEntries.keys).sorted { $0.bytes.lexicographicallyPrecedes($1.bytes) }
            for key in keys {
                try Task.checkCancellation()
                guard let name = oldEntries[key]?.key ?? newEntries[key]?.key else { throw InspectionArchiveError.invalid }
                let before = try oldEntries[key].map { try SecurityDeltaValue.from($0.value, normalizedIntegers: true) }
                let after = try newEntries[key].map { try SecurityDeltaValue.from($0.value, normalizedIntegers: true) }
                let disposition: SecurityDeltaDisposition
                if let before, let after {
                    switch try before.compare(to: after) {
                    case .equal: disposition = .unchanged
                    case .different: disposition = .observedChange
                    case .representationUnresolved: disposition = .unresolved
                    }
                } else { disposition = before == nil ? .observedAddition : .observedRemoval }
                let hasNormalized = before.map(normalizedIntegers) == true || after.map(normalizedIntegers) == true
                try add(match, a, b, subject: "key:" + name, disposition: disposition,
                    before: before == nil ? .absent : .observed, after: after == nil ? .absent : .observed,
                    old: before, new: after,
                    reason: hasNormalized ? .init(code: "numeric_representation_unspecified", diagnostic: "The captured source normalized integer representations; original signedness is unavailable.") : nil,
                    category: category, sourceReferences: refs("declaration:key:" + name))
                if [.observedAddition, .observedRemoval, .observedChange].contains(disposition), let observation = lastAdded {
                    try finding(observation, title: "Recorded declaration value changed")
                }
            }
            if sourceCategory == .loadCommands {
                let changes: [ComponentSecurityDeltaLoader.Change]
                do { changes = try ComponentSecurityDeltaLoader.changes(previous: before, current: after, architecture: admitted.architecture.rawValue) }
                catch {
                    if error is CancellationError || Task.isCancelled { throw CancellationError() }
                    if let refusal = error as? SecurityDeltaRefusal { throw refusal }
                    if (error as? InspectionArchiveError) == .limit { throw InspectionArchiveError.limit }
                    try add(match, a, b, subject: "dependency-interpretation", disposition: .unresolved,
                        before: .observed, after: .observed,
                        reason: .init(code: "loader_interpretation_unavailable", diagnostic: "Captured loader records could not be interpreted as bounded dependency declarations."),
                        category: .loadCommands, sourceReferences: refs("declaration:key:commands"))
                    return
                }
                for change in changes {
                    let disposition: SecurityDeltaDisposition = change.previousCount == 0 ? .observedAddition :
                        (change.currentCount == 0 ? .observedRemoval : .observedChange)
                    let countsChanged = change.previousCount != change.currentCount
                    let subject = "dependency:" + change.command + ":" + change.path
                    try add(match, a, b, subject: subject, disposition: disposition,
                        before: change.previousCount == 0 ? .absent : .observed,
                        after: change.currentCount == 0 ? .absent : .observed,
                        old: countsChanged ? .signed(Int64(change.previousCount)) : nil,
                        new: countsChanged ? .signed(Int64(change.currentCount)) : nil,
                        reason: countsChanged ? nil : .init(code: "loader_group_evidence", diagnostic: "Counts are equal; inspect all recorded rows in this dependency group for metadata changes."),
                        category: .loadCommands, sourceReferences: refs("loader:dependency:" + change.command + ":" + change.path))
                    if let observation = lastAdded { try finding(observation, title: "Recorded library dependency changed") }
                }
            }
        }
        func compareEntitlements(_ match: ComponentMatch, _ a: ComponentRecord, _ b: ComponentRecord) throws {
            let outcome = admitted.entitlementResults.first { $0.matchID == match.id }
            func refs(_ key: String) -> [SecurityDeltaEvidenceReference] {
                [SecurityDeltaEvidenceReference(side: .previous, inventoryID: admitted.previous.id, componentID: a.id,
                    category: .entitlements, relativeSource: a.relativePath, architecture: admitted.architecture.rawValue, evidenceKey: key),
                 SecurityDeltaEvidenceReference(side: .current, inventoryID: admitted.current.id, componentID: b.id,
                    category: .entitlements, relativeSource: b.relativePath, architecture: admitted.architecture.rawValue, evidenceKey: key)]
            }
            let strictOld = input.entitlementEvidence.first { $0.side == .previous && $0.componentID == a.id }
            let strictNew = input.entitlementEvidence.first { $0.side == .current && $0.componentID == b.id }
            func strictRefs(_ key: String) -> [SecurityDeltaEvidenceReference] {
                    [SecurityDeltaEvidenceReference(side: .previous, inventoryID: admitted.previous.id, componentID: a.id,
                        category: strictOld == nil ? .componentInventory : .entitlements, relativeSource: a.relativePath,
                        architecture: admitted.architecture.rawValue, evidenceKey: strictOld == nil ? "entitlement:not-captured" : "strict-entitlement:" + key),
                     SecurityDeltaEvidenceReference(side: .current, inventoryID: admitted.current.id, componentID: b.id,
                        category: strictNew == nil ? .componentInventory : .entitlements, relativeSource: b.relativePath,
                        architecture: admitted.architecture.rawValue, evidenceKey: strictNew == nil ? "entitlement:not-captured" : "strict-entitlement:" + key)]
            }
            func conflicts(_ item: SecurityDeltaEntitlementEvidence, _ snapshot: EntitlementSnapshot) throws -> Bool {
                let state: SecurityDeltaSourceState = snapshot.presence == .notPresent ? .absent : .observed
                guard state == item.state, item.signingIdentifier?.utf8.elementsEqual(snapshot.signingIdentifier.utf8) == true else { return true }
                guard state == .observed, let value = item.values else { return false }
                let historical = try SecurityDeltaValue.from(.dictionary(snapshot.entitlements), normalizedIntegers: true,
                    maxNodes: 10_000, maxBytes: 8 * 1_048_576)
                return try value.compare(to: historical) == .different
            }
            let strictPairComplete = strictOld.map { [.observed, .absent].contains($0.state) } == true &&
                strictNew.map { [.observed, .absent].contains($0.state) } == true
            var hasLegacyPair = false
            if case .compared(_, _, let legacy)? = outcome {
                hasLegacyPair = true
                if !strictPairComplete && (strictOld != nil || strictNew != nil) {
                    let oldConflict = try strictOld.map { [.observed, .absent].contains($0.state) ? try conflicts($0, legacy.previous) : false } ?? false
                    let newConflict = try strictNew.map { [.observed, .absent].contains($0.state) ? try conflicts($0, legacy.current) : false } ?? false
                    if oldConflict || newConflict {
                        try add(match, a, b, subject: "evidence-consistency", disposition: .unresolved, before: .observed, after: .observed,
                            reason: .init(code: "evidence_conflict", diagnostic: "Strict and legacy entitlement records disagree. Captures were not necessarily simultaneous."),
                            category: .entitlements, sourceReferences: strictRefs("presence") + refs("entitlement:result"))
                        return
                    }
                    try add(match, a, b, subject: "strict-evidence-coverage", disposition: .unresolved,
                        before: strictOld?.state ?? .unexamined, after: strictNew?.state ?? .unexamined,
                        reason: .init(code: strictOld?.state == .unavailable || strictNew?.state == .unavailable ? "source_unavailable" : "category_unexamined",
                                      diagnostic: "Strict entitlement evidence is incomplete. The separately recorded legacy pair remains available with its historical numeric-fidelity limits."),
                        category: .entitlements, sourceReferences: strictRefs("presence"))
                }
            }
            if (strictOld != nil || strictNew != nil) && (strictPairComplete || !hasLegacyPair) {
                guard let old = strictOld, let new = strictNew,
                      [.observed, .absent].contains(old.state), [.observed, .absent].contains(new.state) else {
                    try add(match, a, b, subject: "presence", disposition: .unresolved,
                        before: strictOld?.state ?? .unexamined, after: strictNew?.state ?? .unexamined,
                        reason: .init(code: strictOld?.state == .unavailable || strictNew?.state == .unavailable ? "source_unavailable" : "category_unexamined",
                                      diagnostic: "Strict entitlement evidence is unavailable or unexamined on at least one side."),
                        category: .entitlements, sourceReferences: strictRefs("presence"))
                    return
                }
                let oldHasArchitecture = a.architectures.contains { $0.utf8.elementsEqual(admitted.architecture.rawValue.utf8) }
                let newHasArchitecture = b.architectures.contains { $0.utf8.elementsEqual(admitted.architecture.rawValue.utf8) }
                guard oldHasArchitecture && newHasArchitecture else {
                    try add(match, a, b, subject: "slice", disposition: .unresolved,
                        before: oldHasArchitecture ? .observed : .unavailable, after: newHasArchitecture ? .observed : .unavailable,
                        reason: .init(code: "slice_correspondence_unresolved", diagnostic: "Recorded component architectures do not establish the requested slice on both sides."),
                        category: .entitlements, sourceReferences: strictRefs("presence") + [
                            ref(.previous, admitted.previous, a, "architectures"), ref(.current, admitted.current, b, "architectures")])
                    return
                }
                if case .compared(_, _, let legacy)? = outcome {
                    if try conflicts(old, legacy.previous) || conflicts(new, legacy.current) {
                        try add(match, a, b, subject: "evidence-consistency", disposition: .unresolved, before: .observed, after: .observed,
                            reason: .init(code: "evidence_conflict", diagnostic: "Strict and legacy entitlement records disagree. Captures were not necessarily simultaneous."),
                            category: .entitlements, sourceReferences: strictRefs("presence") + refs("entitlement:result"))
                        return
                    }
                }
                func strictFinding(_ observation: SecurityDeltaObservation) throws {
                    findings.append(.init(id: stableID(["strict-entitlement-finding", observation.id]), kind: .declarationChanged,
                        disposition: observation.disposition, title: "Recorded entitlement declaration changed",
                        explanation: "The captured declaration changed; this does not establish effective runtime authorization or signature trust. The captures are sequential observations.",
                        observationIDs: [observation.id], evidence: observation.evidence, limitations: observation.limitations))
                }
                let presence: SecurityDeltaDisposition = old.state == new.state ? .unchanged : (old.state == .absent ? .observedAddition : .observedRemoval)
                try add(match, a, b, subject: "presence", disposition: presence, before: old.state, after: new.state,
                    category: .entitlements, sourceReferences: strictRefs("presence"))
                if presence != .unchanged, let observation = lastAdded { try strictFinding(observation) }
                func entries(_ item: SecurityDeltaEntitlementEvidence) throws -> [ExactUTF8Key: SecurityDeltaValueEntry] {
                    guard let values = item.values else { return [:] }
                    guard case .dictionary(let entries) = values else { throw InspectionArchiveError.invalid }
                    var result: [ExactUTF8Key: SecurityDeltaValueEntry] = [:]
                    for entry in entries { guard result.updateValue(entry, forKey: ExactUTF8Key(entry.key)) == nil else { throw InspectionArchiveError.invalid } }
                    return result
                }
                let before = try entries(old), after = try entries(new)
                for key in Set(before.keys).union(after.keys).sorted(by: { $0.bytes.lexicographicallyPrecedes($1.bytes) }) {
                    try Task.checkCancellation()
                    guard let name = before[key]?.key ?? after[key]?.key else { throw InspectionArchiveError.invalid }
                    let oldValue = before[key]?.value, newValue = after[key]?.value
                    let disposition: SecurityDeltaDisposition
                    if let oldValue, let newValue {
                        switch try oldValue.compare(to: newValue) {
                        case .equal: disposition = .unchanged
                        case .different: disposition = .observedChange
                        case .representationUnresolved: disposition = .unresolved
                        }
                    } else { disposition = oldValue == nil ? .observedAddition : .observedRemoval }
                    try add(match, a, b, subject: "key:" + name, disposition: disposition,
                        before: oldValue == nil ? .absent : .observed, after: newValue == nil ? .absent : .observed,
                        old: oldValue, new: newValue, category: .entitlements, sourceReferences: strictRefs("key:" + name))
                    if [.observedAddition, .observedRemoval, .observedChange].contains(disposition), let observation = lastAdded { try strictFinding(observation) }
                }
                return
            }
            guard let outcome else { throw InspectionArchiveError.invalid }
            guard case .compared(_, _, let report) = outcome else {
                guard case .unavailable = outcome else { throw InspectionArchiveError.invalid }
                try add(match, a, b, subject: "presence", disposition: .unresolved, before: .unknown, after: .unknown,
                        reason: .init(code: "source_unavailable", diagnostic: "The recorded pair outcome does not establish each side's acquisition state; inspect the retained reason."), category: .entitlements,
                        sourceReferences: refs("entitlement:result"))
                return
            }
            let oldState: SecurityDeltaSourceState = report.previous.presence == .notPresent ? .absent : .observed
            let newState: SecurityDeltaSourceState = report.current.presence == .notPresent ? .absent : .observed
            let presence: SecurityDeltaDisposition = oldState == newState ? .unchanged : (oldState == .absent ? .observedAddition : .observedRemoval)
            try add(match, a, b, subject: "presence", disposition: presence, before: oldState, after: newState,
                    category: .entitlements, sourceReferences: refs("entitlement:presence"))
            func finding(_ observation: SecurityDeltaObservation) throws {
                findings.append(.init(id: stableID(["entitlement-finding", observation.id]), kind: .declarationChanged,
                    disposition: observation.disposition, title: "Recorded entitlement declaration changed",
                    explanation: "The captured declaration changed; this does not establish effective runtime authorization or signature trust.",
                    observationIDs: [observation.id], evidence: observation.evidence, limitations: observation.limitations))
            }
            if presence != .unchanged, let observation = lastAdded { try finding(observation) }
            let before = Dictionary(uniqueKeysWithValues: report.previous.entitlements.entries.map { (ExactUTF8Key($0.key), $0) })
            let after = Dictionary(uniqueKeysWithValues: report.current.entitlements.entries.map { (ExactUTF8Key($0.key), $0) })
            let keys = Set(before.keys).union(after.keys).sorted { $0.bytes.lexicographicallyPrecedes($1.bytes) }
            for key in keys {
                try Task.checkCancellation()
                guard let name = before[key]?.key ?? after[key]?.key else { throw InspectionArchiveError.invalid }
                let old = try before[key].map { try SecurityDeltaValue.from($0.value, normalizedIntegers: true, maxNodes: 100_000, maxBytes: 8 * 1_048_576) }
                let new = try after[key].map { try SecurityDeltaValue.from($0.value, normalizedIntegers: true, maxNodes: 100_000, maxBytes: 8 * 1_048_576) }
                let disposition: SecurityDeltaDisposition
                if let old, let new {
                    switch try old.compare(to: new) {
                    case .equal: disposition = .unchanged
                    case .different: disposition = .observedChange
                    case .representationUnresolved: disposition = .unresolved
                    }
                } else { disposition = old == nil ? .observedAddition : .observedRemoval }
                let hasNormalized = old.map(normalizedIntegers) == true || new.map(normalizedIntegers) == true
                try add(match, a, b, subject: "key:" + name, disposition: disposition,
                    before: old == nil ? .absent : .observed, after: new == nil ? .absent : .observed, old: old, new: new,
                    reason: hasNormalized ? .init(code: "numeric_representation_unspecified", diagnostic: "Legacy entitlement evidence normalized integer representations; original signedness is unavailable.") : nil,
                    category: .entitlements, sourceReferences: refs("entitlement:key:" + name))
                if [.observedAddition, .observedRemoval, .observedChange].contains(disposition), let observation = lastAdded { try finding(observation) }
            }
        }
        func compareSignatures(_ match: ComponentMatch, _ a: ComponentRecord, _ b: ComponentRecord) throws {
            let old = input.signatureEvidence.first { $0.side == .previous && $0.document.evidence.componentID == a.id }
            let new = input.signatureEvidence.first { $0.side == .current && $0.document.evidence.componentID == b.id }
            let oldFailure = input.signatureRefusals.first { $0.side == .previous && $0.componentID == a.id }
            let newFailure = input.signatureRefusals.first { $0.side == .current && $0.componentID == b.id }
            func sliceIdentity(_ slice: CodeSignatureSliceEvidence?) -> SecurityDeltaSliceIdentity? {
                guard let slice else { return nil }
                return .init(cpuType: slice.cpuType, cpuSubtype: slice.cpuSubtype, headerMagic: slice.headerMagic,
                             index: slice.index, offset: slice.sliceOffset, size: slice.sliceSize, recordedSHA256: slice.sliceSHA256)
            }
            func refs(_ key: String, oldSlice: CodeSignatureSliceEvidence? = nil,
                      newSlice: CodeSignatureSliceEvidence? = nil) -> [SecurityDeltaEvidenceReference] {
                [SecurityDeltaEvidenceReference(side: .previous, inventoryID: admitted.previous.id, componentID: a.id,
                    category: old == nil && oldFailure == nil ? .componentInventory : .signatureEvidence, relativeSource: a.relativePath,
                    architecture: oldSlice == nil ? nil : admitted.architecture.rawValue,
                    evidenceKey: oldFailure != nil ? "signature:refusal" : (old == nil ? "signature:not-captured" : key), slice: sliceIdentity(oldSlice)),
                 SecurityDeltaEvidenceReference(side: .current, inventoryID: admitted.current.id, componentID: b.id,
                    category: new == nil && newFailure == nil ? .componentInventory : .signatureEvidence, relativeSource: b.relativePath,
                    architecture: newSlice == nil ? nil : admitted.architecture.rawValue,
                    evidenceKey: newFailure != nil ? "signature:refusal" : (new == nil ? "signature:not-captured" : key), slice: sliceIdentity(newSlice))]
            }
            func finding(_ observation: SecurityDeltaObservation) throws {
                let explanation: String
                switch observation.subject {
                case "containerSHA256":
                    explanation = "Recorded whole-container digests differ. The container includes all slices and padding; original image bytes are not retained or authenticated by this analysis. No trust or runtime conclusion is implied."
                case "sliceSHA256":
                    explanation = "Recorded requested-slice digests differ. Original slice bytes are not retained or authenticated by this analysis. No trust or runtime conclusion is implied."
                default:
                    explanation = "This compares retained structural byte evidence. It does not establish signature validity, trust, notarization, or runtime behavior."
                }
                findings.append(.init(id: stableID(["signature-finding", observation.id]), kind: .signatureEvidenceChanged,
                    disposition: observation.disposition, title: "Recorded signature evidence changed",
                    explanation: explanation,
                    observationIDs: [observation.id], evidence: observation.evidence, limitations: observation.limitations))
            }
            guard let old, let new else {
                try add(match, a, b, subject: "presence", disposition: .unresolved,
                    before: oldFailure != nil ? .unavailable : (old == nil ? .unexamined : .observed),
                    after: newFailure != nil ? .unavailable : (new == nil ? .unexamined : .observed),
                    reason: .init(code: oldFailure?.code ?? newFailure?.code ?? "category_unexamined", diagnostic: "Signature evidence is unavailable or was not captured for both sides."),
                    category: .signatureEvidence, sourceReferences: refs("signature:document"))
                return
            }
            func contradictsContainer(_ evidence: CodeSignatureEvidence) -> Bool {
                evidence.slices.contains { slice in
                    slice.sliceOffset == 0 && slice.sliceSize == evidence.containerByteCount && slice.sliceSHA256 != evidence.containerSHA256
                }
            }
            guard !contradictsContainer(old.document.evidence), !contradictsContainer(new.document.evidence) else {
                try add(match, a, b, subject: "container-slice-consistency", disposition: .unresolved,
                    before: .observed, after: .observed,
                    reason: .init(code: "evidence_conflict", diagnostic: "A recorded whole-container slice digest contradicts its recorded container digest."),
                    category: .signatureEvidence, sourceReferences: refs("signature:container-slice-consistency"))
                return
            }
            let oldHasArchitecture = a.architectures.contains { $0.utf8.elementsEqual(admitted.architecture.rawValue.utf8) }
            let newHasArchitecture = b.architectures.contains { $0.utf8.elementsEqual(admitted.architecture.rawValue.utf8) }
            guard oldHasArchitecture && newHasArchitecture else {
                try add(match, a, b, subject: "slice", disposition: .unresolved,
                    before: oldHasArchitecture ? .observed : .unavailable, after: newHasArchitecture ? .observed : .unavailable,
                    reason: .init(code: "slice_correspondence_unresolved", diagnostic: "Recorded component architectures do not establish the requested slice on both sides."),
                    category: .signatureEvidence, sourceReferences: refs("signature:document") + [
                        ref(.previous, admitted.previous, a, "architectures"),
                        ref(.current, admitted.current, b, "architectures")])
                return
            }
            func emit(_ subject: String, oldValue: String, newValue: String,
                      oldSlice: CodeSignatureSliceEvidence? = nil, newSlice: CodeSignatureSliceEvidence? = nil) throws {
                let disposition: SecurityDeltaDisposition = oldValue.utf8.elementsEqual(newValue.utf8) ? .unchanged : .observedChange
                try add(match, a, b, subject: subject, disposition: disposition, before: .observed, after: .observed,
                        old: .string(oldValue), new: .string(newValue), category: .signatureEvidence,
                        sourceReferences: refs("signature:" + subject, oldSlice: oldSlice, newSlice: newSlice))
                if disposition == .observedChange, let observation = lastAdded { try finding(observation) }
            }
            try emit("containerSHA256", oldValue: old.document.evidence.containerSHA256, newValue: new.document.evidence.containerSHA256)
            let cpu: UInt32 = admitted.architecture == .arm64 ? 0x0100000c : 0x01000007
            let subtype: UInt32 = admitted.architecture == .arm64 ? 0 : 3
            let oldSlices = old.document.evidence.slices.filter { $0.cpuType == cpu && $0.cpuSubtype == subtype }
            let newSlices = new.document.evidence.slices.filter { $0.cpuType == cpu && $0.cpuSubtype == subtype }
            guard oldSlices.count == 1, newSlices.count == 1,
                  let oldSlice = oldSlices.first, let newSlice = newSlices.first, oldSlice.headerMagic == newSlice.headerMagic else {
                try add(match, a, b, subject: "slice", disposition: .unresolved, before: .unavailable, after: .unavailable,
                    reason: .init(code: "slice_correspondence_unresolved", diagnostic: "Exact requested raw CPU, subtype and header correspondence is unavailable."),
                    category: .signatureEvidence, sourceReferences: refs("signature:slice"))
                return
            }
            func knownSignaturePresence(_ state: CodeSignatureEvidenceState) -> Bool? {
                switch state {
                case .signatureAbsent: return false
                case .collected, .entitlementsAbsent: return true
                case .unexamined, .malformed, .budgetExceeded: return nil
                }
            }
            if oldSlice.sliceSHA256 == newSlice.sliceSHA256, oldSlice.sliceSize == newSlice.sliceSize,
               let oldPresence = knownSignaturePresence(oldSlice.state), let newPresence = knownSignaturePresence(newSlice.state) {
                let inconsistent: Bool
                if oldPresence != newPresence { inconsistent = true }
                else if oldPresence, let oldOffset = oldSlice.signatureOffset, let newOffset = newSlice.signatureOffset {
                    inconsistent = oldOffset - oldSlice.sliceOffset != newOffset - newSlice.sliceOffset ||
                        oldSlice.signatureByteCount != newSlice.signatureByteCount || oldSlice.signatureSHA256 != newSlice.signatureSHA256
                } else { inconsistent = false }
                if inconsistent {
                    try add(match, a, b, subject: "cross-document-consistency", disposition: .unresolved,
                        before: .observed, after: .observed,
                        reason: .init(code: "evidence_conflict", diagnostic: "Equal recorded slice digests conflict with recorded signature presence, range or digest."),
                        category: .signatureEvidence, sourceReferences: refs("signature:consistency", oldSlice: oldSlice, newSlice: newSlice))
                    return
                }
            }
            // Equal claimed slice identities cannot support incompatible retained
            // bytes at the same slice-relative offsets, even if each document's
            // internally retained signature is valid in isolation.
            if oldSlice.sliceSHA256 == newSlice.sliceSHA256, oldSlice.sliceSize == newSlice.sliceSize,
               let oldOffset = oldSlice.signatureOffset, let newOffset = newSlice.signatureOffset,
               let oldBytes = oldSlice.signatureBytes, let newBytes = newSlice.signatureBytes {
                let oldStart = oldOffset - oldSlice.sliceOffset, newStart = newOffset - newSlice.sliceOffset
                let start = max(oldStart, newStart)
                let end = min(oldStart + UInt64(oldBytes.count), newStart + UInt64(newBytes.count))
                if start < end {
                    let lhs = oldBytes.subdata(in: Int(start - oldStart)..<Int(end - oldStart))
                    let rhs = newBytes.subdata(in: Int(start - newStart)..<Int(end - newStart))
                    if lhs != rhs {
                        try add(match, a, b, subject: "cross-document-consistency", disposition: .unresolved,
                            before: .observed, after: .observed,
                            reason: .init(code: "evidence_conflict", diagnostic: "Equal recorded slice digests conflict with retained signature bytes at overlapping slice-relative offsets."),
                            category: .signatureEvidence, sourceReferences: refs("signature:retained-bytes", oldSlice: oldSlice, newSlice: newSlice))
                        return
                    }
                }
            }
            try emit("sliceSHA256", oldValue: oldSlice.sliceSHA256, newValue: newSlice.sliceSHA256, oldSlice: oldSlice, newSlice: newSlice)
            func examined(_ state: CodeSignatureEvidenceState) -> Bool {
                switch state { case .collected, .signatureAbsent, .entitlementsAbsent: return true; case .unexamined, .malformed, .budgetExceeded: return false }
            }
            guard examined(oldSlice.state), examined(newSlice.state) else {
                func sourceState(_ state: CodeSignatureEvidenceState) -> SecurityDeltaSourceState {
                    if examined(state) { return .observed }
                    return state == .unexamined ? .unexamined : .unavailable
                }
                func detail(_ slice: CodeSignatureSliceEvidence) -> String {
                    slice.state.rawValue + (slice.problem.map { ":" + $0.rawValue } ?? "")
                }
                let codes = [oldSlice.state, newSlice.state].filter { !examined($0) }
                let code: String
                if codes.allSatisfy({ $0 == .unexamined }) { code = "signature_unexamined" }
                else if codes.allSatisfy({ $0 == .malformed }) { code = "signature_malformed" }
                else if codes.allSatisfy({ $0 == .budgetExceeded }) { code = "signature_budget_exceeded" }
                else { code = "signature_states_unresolved" }
                try add(match, a, b, subject: "signatureState", disposition: .unresolved,
                    before: sourceState(oldSlice.state), after: sourceState(newSlice.state),
                    old: .string(detail(oldSlice)), new: .string(detail(newSlice)),
                    reason: .init(code: code, diagnostic: "At least one requested slice was unexamined, malformed or exceeded its capture budget; inspect both recorded states."),
                    category: .signatureEvidence, sourceReferences: refs("signature:state", oldSlice: oldSlice, newSlice: newSlice))
                return
            }
            try emit("signatureState", oldValue: oldSlice.state.rawValue, newValue: newSlice.state.rawValue, oldSlice: oldSlice, newSlice: newSlice)
            let oldHash = oldSlice.signatureSHA256, newHash = newSlice.signatureSHA256
            let disposition: SecurityDeltaDisposition
            if let oldHash, let newHash { disposition = oldHash == newHash ? .unchanged : .observedChange }
            else if oldHash == nil && newHash == nil { disposition = .unchanged }
            else { disposition = oldHash == nil ? .observedAddition : .observedRemoval }
            try add(match, a, b, subject: "signatureSHA256", disposition: disposition,
                before: oldHash == nil ? .absent : .observed, after: newHash == nil ? .absent : .observed,
                old: oldHash.map(SecurityDeltaValue.string), new: newHash.map(SecurityDeltaValue.string),
                category: .signatureEvidence, sourceReferences: refs("signature:signatureSHA256", oldSlice: oldSlice, newSlice: newSlice))
            if [.observedAddition, .observedRemoval, .observedChange].contains(disposition), let observation = lastAdded { try finding(observation) }
            for (slotType, name) in [(UInt32(5), "xmlSlotSHA256"), (UInt32(7), "derSlotSHA256")] {
                let before = oldSlice.slots.first { $0.type == slotType }?.sha256
                let after = newSlice.slots.first { $0.type == slotType }?.sha256
                let change: SecurityDeltaDisposition
                if let before, let after { change = before == after ? .unchanged : .observedChange }
                else if before == nil && after == nil { change = .unchanged }
                else { change = before == nil ? .observedAddition : .observedRemoval }
                try add(match, a, b, subject: name, disposition: change,
                    before: before == nil ? .absent : .observed, after: after == nil ? .absent : .observed,
                    old: before.map(SecurityDeltaValue.string), new: after.map(SecurityDeltaValue.string),
                    category: .signatureEvidence, sourceReferences: refs("signature:slot:\(slotType):sha256", oldSlice: oldSlice, newSlice: newSlice))
                if [.observedAddition, .observedRemoval, .observedChange].contains(change), let observation = lastAdded { try finding(observation) }
            }
        }
        let ordered = admitted.matching.matches.sorted { left, right in
            let lp = previous.first { $0.id == left.previousID }?.relativePath ?? current.first { $0.id == left.currentID }?.relativePath ?? ""
            let rp = previous.first { $0.id == right.previousID }?.relativePath ?? current.first { $0.id == right.currentID }?.relativePath ?? ""
            if !lp.utf8.elementsEqual(rp.utf8) { return lp.utf8.lexicographicallyPrecedes(rp.utf8) }
            return left.id.uuidString < right.id.uuidString
        }
        for match in ordered {
            try Task.checkCancellation()
            let a = previous.first { $0.id == match.previousID }, b = current.first { $0.id == match.currentID }
            if (a == nil) != (b == nil), let record = a ?? b {
                let side: SecurityDeltaSide = a == nil ? .current : .previous
                let inventory = side == .previous ? admitted.previous : admitted.current
                let other = side == .previous ? admitted.current : admitted.previous
                if let evidence = input.entitlementEvidence.first(where: { $0.side == side && $0.componentID == record.id }) {
                    let hasArchitecture = record.architectures.contains { $0.utf8.elementsEqual(admitted.architecture.rawValue.utf8) }
                    let state: SecurityDeltaSourceState = hasArchitecture || [.unavailable, .unexamined].contains(evidence.state) ? evidence.state : .unavailable
                    var references: [SecurityDeltaEvidenceReference] = [.init(side: side, inventoryID: inventory.id, componentID: record.id,
                        category: .entitlements, relativeSource: record.relativePath, architecture: admitted.architecture.rawValue,
                        evidenceKey: "strict-entitlement:document"), .init(side: side == .previous ? .current : .previous,
                        inventoryID: other.id, componentID: nil, category: .componentInventory, relativeSource: record.relativePath, evidenceKey: "scope")]
                    if !hasArchitecture { references.append(ref(side, inventory, record, "architectures")) }
                    try add(match, a, b, subject: "one-sided-context", disposition: .unresolved,
                        before: side == .previous ? state : .unexamined, after: side == .current ? state : .unexamined,
                        old: side == .previous && state == .observed ? evidence.values : nil,
                        new: side == .current && state == .observed ? evidence.values : nil,
                        reason: .init(code: hasArchitecture ? "component_correspondence_unaccepted" : "slice_correspondence_unresolved",
                            diagnostic: "One-sided entitlement evidence is recorded as component context; no pairwise entitlement change is inferred."),
                        category: .entitlements, sourceReferences: references)
                } else {
                    try add(match, a, b, subject: "one-sided-context", disposition: .unresolved, before: .unexamined, after: .unexamined,
                        reason: .init(code: "category_unexamined", diagnostic: "Entitlement evidence was not captured for this observed component."),
                        category: .entitlements, sourceReferences: [ref(side, inventory, record, "entitlement:not-captured"),
                            .init(side: side == .previous ? .current : .previous, inventoryID: other.id, componentID: nil,
                                  category: .componentInventory, relativeSource: record.relativePath, evidenceKey: "scope")])
                }
                let signature = input.signatureEvidence.first { $0.side == side && $0.document.evidence.componentID == record.id }
                let refusal = input.signatureRefusals.first { $0.side == side && $0.componentID == record.id }
                if signature != nil || refusal != nil {
                    let state: SecurityDeltaSourceState = refusal == nil ? .observed : .unavailable
                    let references: [SecurityDeltaEvidenceReference] = [.init(side: side, inventoryID: inventory.id, componentID: record.id,
                        category: .signatureEvidence, relativeSource: record.relativePath, evidenceKey: refusal == nil ? "signature:document" : "signature:refusal"),
                        .init(side: side == .previous ? .current : .previous, inventoryID: other.id, componentID: nil,
                              category: .componentInventory, relativeSource: record.relativePath, evidenceKey: "scope")]
                    let digest = signature.map { SecurityDeltaValue.string($0.document.evidence.containerSHA256) }
                    try add(match, a, b, subject: "one-sided-context", disposition: .unresolved,
                        before: side == .previous ? state : .unexamined, after: side == .current ? state : .unexamined,
                        old: side == .previous ? digest : nil, new: side == .current ? digest : nil,
                        reason: .init(code: refusal?.code ?? "component_correspondence_unaccepted",
                            diagnostic: "One-sided signature evidence is recorded as component context; no pairwise signature change is inferred."),
                        category: .signatureEvidence, sourceReferences: references)
                } else {
                    try add(match, a, b, subject: "one-sided-context", disposition: .unresolved, before: .unexamined, after: .unexamined,
                        reason: .init(code: "category_unexamined", diagnostic: "Signature evidence was not captured for this observed component."),
                        category: .signatureEvidence, sourceReferences: [ref(side, inventory, record, "signature:not-captured"),
                            .init(side: side == .previous ? .current : .previous, inventoryID: other.id, componentID: nil,
                                  category: .componentInventory, relativeSource: record.relativePath, evidenceKey: "scope")])
                }
            }
            switch match.relation {
            case .addedWithinScope, .removedWithinScope:
                let isAddition = match.relation == .addedWithinScope
                let record = isAddition ? b : a
                guard let record else { throw InspectionArchiveError.invalid }
                let usable = record.kind != "appDeclarations" && !record.architectures.isEmpty
                let disposition: SecurityDeltaDisposition = usable ? (isAddition ? .observedAddition : .observedRemoval) : .unresolved
                let reason = !usable ? SecurityDeltaReason(code: "source_unavailable", diagnostic: "The recorded component was not fully characterized as an executable image.") :
                    (record.readIssues.isEmpty ? nil : SecurityDeltaReason(code: "source_unavailable", diagnostic: "Some component metadata was unavailable; consult the recorded inventory issues."))
                try add(match, a, b, subject: "component", disposition: disposition,
                    before: isAddition ? .absent : .observed, after: isAddition ? .observed : .absent, reason: reason)
                guard usable, let observation = lastAdded else { continue }
                let isXPC = record.kind == "xpc"
                let identifier = record.declaredBundleID.map { " Recorded identifier: " + $0 + "." } ?? " Recorded identifier unavailable."
                let surface = isXPC ? " Recorded kind: XPC service." : ""
                findings.append(.init(id: stableID(["finding", observation.id]), kind: isAddition ? (isXPC ? .xpcAdded : .componentAdded) : .componentRemoved,
                    disposition: disposition, title: isAddition ? "Component added within recorded scope" : "Component removed within recorded scope",
                    explanation: (isAddition ? "A component was observed at this location in the current inventory, within the previous recorded search scope." : "A component was not observed at this location within the current recorded search scope.") + surface + identifier + " Inspect category availability in observations.",
                    observationIDs: [observation.id], evidence: observation.evidence, limitations: observation.limitations))
            case .sameLocation:
                guard let a, let b else { throw InspectionArchiveError.invalid }
                func inventoryFinding(_ observation: SecurityDeltaObservation) {
                    findings.append(.init(id: stableID(["inventory-finding", observation.id]), kind: .declarationChanged,
                        disposition: observation.disposition, title: "Recorded component inventory changed",
                        explanation: "A recorded component field changed at an accepted exact location. This does not establish executable-byte changes or runtime behavior.",
                        observationIDs: [observation.id], evidence: observation.evidence, limitations: observation.limitations))
                }
                for (key, old, new) in [("kind", Optional(a.kind), Optional(b.kind)), ("bundleIdentifier", a.declaredBundleID, b.declaredBundleID), ("version", a.declaredVersion, b.declaredVersion)] {
                    let oldValue = old.map(SecurityDeltaValue.string), newValue = new.map(SecurityDeltaValue.string)
                    let disposition: SecurityDeltaDisposition
                    if let old, let new { disposition = old.utf8.elementsEqual(new.utf8) ? .unchanged : .observedChange }
                    else { disposition = .unresolved }
                    try add(match, a, b, subject: key, disposition: disposition,
                        before: old == nil ? .unavailable : .observed, after: new == nil ? .unavailable : .observed,
                        old: oldValue, new: newValue,
                        reason: disposition == .unresolved ? .init(code: "source_unavailable", diagnostic: "A declaration is unavailable; absence is not inferred.") : nil)
                    if disposition == .observedChange, let observation = lastAdded { inventoryFinding(observation) }
                }
                let oldArchitectures = a.architectures.sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) }
                let newArchitectures = b.architectures.sorted { $0.utf8.lexicographicallyPrecedes($1.utf8) }
                let knownArchitectures = !oldArchitectures.isEmpty && !newArchitectures.isEmpty
                let architecturesEqual = oldArchitectures.map { Data($0.utf8) } == newArchitectures.map { Data($0.utf8) }
                let architectureDisposition: SecurityDeltaDisposition = !knownArchitectures ? .unresolved : (architecturesEqual ? .unchanged : .observedChange)
                try add(match, a, b, subject: "architectures", disposition: architectureDisposition,
                    before: oldArchitectures.isEmpty ? .unavailable : .observed, after: newArchitectures.isEmpty ? .unavailable : .observed,
                    old: oldArchitectures.isEmpty ? nil : .array(oldArchitectures.map(SecurityDeltaValue.string)),
                    new: newArchitectures.isEmpty ? nil : .array(newArchitectures.map(SecurityDeltaValue.string)),
                    reason: knownArchitectures ? nil : .init(code: "slice_unavailable", diagnostic: "At least one component's architecture declarations were not available."))
                if architectureDisposition == .observedChange, let observation = lastAdded { inventoryFinding(observation) }
                var oldMinimum: [ExactUTF8Key: (String, String)] = [:], newMinimum: [ExactUTF8Key: (String, String)] = [:]
                for (key, value) in a.minimumOSByArchitecture { oldMinimum[ExactUTF8Key(key)] = (key, value) }
                for (key, value) in b.minimumOSByArchitecture { newMinimum[ExactUTF8Key(key)] = (key, value) }
                for key in Set(oldMinimum.keys).union(newMinimum.keys).sorted(by: { $0.bytes.lexicographicallyPrecedes($1.bytes) }) {
                    guard let label = oldMinimum[key]?.0 ?? newMinimum[key]?.0 else { throw InspectionArchiveError.invalid }
                    let old = oldMinimum[key]?.1, new = newMinimum[key]?.1
                    let disposition: SecurityDeltaDisposition
                    if let old, let new { disposition = old.utf8.elementsEqual(new.utf8) ? .unchanged : .observedChange }
                    else { disposition = .unresolved }
                    try add(match, a, b, subject: "minimumOS:" + label, disposition: disposition,
                        before: old == nil ? .unavailable : .observed, after: new == nil ? .unavailable : .observed,
                        old: old.map(SecurityDeltaValue.string), new: new.map(SecurityDeltaValue.string),
                        reason: disposition == .unresolved ? .init(code: "source_unavailable", diagnostic: "Minimum OS metadata is unavailable for at least one side; absence is not inferred.") : nil)
                    if disposition == .observedChange, let observation = lastAdded { inventoryFinding(observation) }
                }
                try compareDeclarations(match, a, b, .info, .informationPropertyList)
                try compareDeclarations(match, a, b, .loadCommands, .loadCommands)
                try compareDeclarations(match, a, b, .privacy, .privacyManifest)
                try compareEntitlements(match, a, b)
                try compareSignatures(match, a, b)
            case .uniqueIdentifierCandidate, .ambiguous, .unobservedInOtherScope:
                let otherScope = a == nil ? admitted.previous.scope : admitted.current.scope
                let scopeReason: String
                if !otherScope.exclusions.isEmpty { scopeReason = "inventory_excluded" }
                else if otherScope.completion != .completeWithinScope || !otherScope.issues.isEmpty { scopeReason = "inventory_incomplete" }
                else { scopeReason = "scope_unsearched" }
                try add(match, a, b, subject: "component", disposition: .unresolved,
                    before: a == nil ? .unexamined : .observed, after: b == nil ? .unexamined : .observed,
                    reason: .init(code: match.relation == .unobservedInOtherScope ? scopeReason : "component_correspondence_unaccepted",
                                  diagnostic: match.reasons.joined(separator: " ")))
            }
        }
        let related = try ComponentSecurityDeltaRules.relatedComponents(observations, review: admitted)
        let repeated = try ComponentSecurityDeltaRules.repeatedDeclarations(observations, review: admitted)
        let correlated = try ComponentSecurityDeltaRules.sameComponent(observations, review: admitted) + related.findings + repeated.findings
        let unresolved = observations.filter { $0.disposition == .unresolved && !$0.limitations.isEmpty }.map { observation in
            let conflict = observation.limitations.contains { $0.code == "evidence_conflict" }
            return SecurityDeltaFinding(id: stableID(["unresolved-finding", observation.id]), kind: conflict ? .evidenceConflict : .coverageIncomplete,
                disposition: .unresolved, title: conflict ? "Recorded evidence is contradictory" : "A comparison remains unresolved",
                explanation: conflict ? "The linked recorded sources disagree; the affected conclusion is withheld." : "The linked observation identifies evidence or coverage that does not support a complete comparison.",
                observationIDs: [observation.id], evidence: observation.evidence, limitations: observation.limitations)
        }
        findings = unresolved.filter { $0.kind == .evidenceConflict } + unresolved.filter { $0.kind != .evidenceConflict } + correlated + findings
        let omittedFromOutput = max(0, findings.count - options.maximumFindings)
        let omittedFindings = omittedFromOutput + repeated.omittedForFindingLimit
        if omittedFromOutput > 0 { findings = Array(findings.prefix(options.maximumFindings)) }
        var coverageLimitations: [SecurityDeltaReason] = [.init(code: "static_evidence_only", diagnostic: "Loader and signature results describe recorded declarations and bytes, not resolved libraries, signature trust or runtime behavior.")]
        if repeated.unspecifiedNumericObservations > 0 {
            coverageLimitations.append(.init(code: "numeric_representation_unspecified", diagnostic: "Repeated typed-transition grouping excludes \(repeated.unspecifiedNumericObservations) observations with unspecified historical integer representation."))
        }
        if repeated.unrepresentedValueObservations > 0 {
            coverageLimitations.append(.init(code: "transition_value_unavailable", diagnostic: "Repeated typed-transition grouping excludes \(repeated.unrepresentedValueObservations) observations without complete typed endpoints."))
        }
        var omissions: [SecurityDeltaOmission] = []
        if related.omittedForReferenceLimit + repeated.omittedForReferenceLimit > 0 {
            omissions.append(.init(count: related.omittedForReferenceLimit + repeated.omittedForReferenceLimit, countIsExact: true,
                detailListComplete: false, reason: .init(code: "evidence_reference_limit", diagnostic: "Related-component findings requiring more than 32 evidence references were omitted.")))
        }
        if related.omittedForLimitationLimit + repeated.omittedForLimitationLimit > 0 {
            omissions.append(.init(count: related.omittedForLimitationLimit + repeated.omittedForLimitationLimit, countIsExact: true,
                detailListComplete: false, reason: .init(code: "limitation_limit", diagnostic: "Related-component findings requiring more than 32 distinct limitations were omitted.")))
        }
        if omittedObservations > 0 {
            omissions.append(.init(count: omittedObservations, countIsExact: true, detailListComplete: false,
                reason: .init(code: "observation_limit", diagnostic: "Observation records were omitted; dependent findings could not all be generated.")))
            omissions.append(.init(count: 0, countIsExact: false, detailListComplete: false,
                reason: .init(code: "finding_limit", diagnostic: "Additional findings may depend on omitted observations; their count is not known.")))
        }
        if omittedFindings > 0 {
            omissions.append(.init(count: omittedFindings, countIsExact: true, detailListComplete: false,
                reason: .init(code: "finding_limit", diagnostic: "Generated findings exceeding the retained finding limit were omitted.")))
        }
        let coverage = SecurityDeltaCoverage(previousScope: admitted.previous.scope.completion.rawValue,
            currentScope: admitted.current.scope.completion.rawValue,
            previousLocations: exactSorted(admitted.previous.scope.searchedLocations), currentLocations: exactSorted(admitted.current.scope.searchedLocations),
            previousExclusions: exactSorted(admitted.previous.scope.exclusions), currentExclusions: exactSorted(admitted.current.scope.exclusions),
            previousIssues: exactSorted(admitted.previous.scope.issues), currentIssues: exactSorted(admitted.current.scope.issues),
            limitations: coverageLimitations, omissions: omissions)
        try Task.checkCancellation()
        return .init(identity: .init(previousInventoryID: admitted.previous.id, currentInventoryID: admitted.current.id,
                                    architecture: admitted.architecture.rawValue, evidenceBasisID: basis),
                     options: options, observations: observations, findings: findings, coverage: coverage)
    }
}
