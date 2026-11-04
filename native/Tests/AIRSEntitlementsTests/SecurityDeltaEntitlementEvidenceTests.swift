import XCTest
import Foundation
import EntitlementDiffCore
import AIRSCore
@testable import AIRSEntitlements

final class SecurityDeltaEntitlementEvidenceTests: XCTestCase {
    func testPartialCurrentStrictEvidencePreservesFidelityAndPresenceDistinctions() throws {
        func inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                  components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])])
        }
        let old = inventory(), new = inventory(), match = try XCTUnwrap(ComponentMatcher.match(previous: old, current: new).matches.first)
        func snapshot(_ inventory: ComponentInventory, _ value: EntitlementValue, strict: Bool = false) -> EntitlementSnapshot {
            .init(sourceName: ComponentComparison.sourceName(componentID: inventory.components[0].id), signingIdentifier: "example", architecture: .arm64,
                  entitlements: .init(["number": value]), numericRepresentation: strict ? .exposed : .normalized)
        }
        let pair = try ComparisonReport(previous: snapshot(old, .integer(1)), current: snapshot(new, .integer(1)))
        let review = try ComponentComparison.review(previous: old, current: new, architecture: .arm64,
            entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: pair)])
        let strict = try SecurityDeltaEntitlementEvidence.capture(snapshot: snapshot(new, .unsignedInteger(1), strict: true), side: .current,
            inventoryID: new.id, componentID: new.components[0].id, relativePath: "Contents/MacOS/Main", capturedAt: Date(timeIntervalSince1970: 0))
        let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [strict]))
        let numeric = try XCTUnwrap(report.observations.first { $0.category == .entitlements && $0.subject == "key:number" })
        XCTAssertEqual(numeric.disposition, .unresolved)
        XCTAssertTrue(numeric.limitations.contains { $0.code == "numeric_representation_unspecified" })
        XCTAssertFalse(report.observations.contains { $0.subject == "evidence-consistency" })
        let absent = EntitlementSnapshot(sourceName: ComponentComparison.sourceName(componentID: new.components[0].id), signingIdentifier: "example",
            architecture: .arm64, presence: .notPresent, entitlements: .init())
        let absentPair = try ComparisonReport(previous: snapshot(old, .integer(1)), current: absent)
        let absentReview = try ComponentComparison.review(previous: old, current: new, architecture: .arm64,
            entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: absentPair)])
        let empty = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64,
            presence: .dictionaryPresent, entitlements: .init(), numericRepresentation: .exposed)
        let emptyCapture = try SecurityDeltaEntitlementEvidence.capture(snapshot: empty, side: .current, inventoryID: new.id,
            componentID: new.components[0].id, relativePath: "Contents/MacOS/Main", capturedAt: Date(timeIntervalSince1970: 1))
        let conflict = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: absentReview, entitlementEvidence: [emptyCapture]))
        XCTAssertTrue(conflict.observations.contains { $0.subject == "evidence-consistency" && $0.disposition == .unresolved })
        XCTAssertFalse(conflict.observations.contains { $0.category == .entitlements && $0.subject == "presence" && $0.disposition == .observedRemoval })
    }
    func testPartialStrictEvidenceRetainsLegacyPairUnlessItConflicts() throws {
        func inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                  components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])])
        }
        let old = inventory(), new = inventory(), match = try XCTUnwrap(ComponentMatcher.match(previous: old, current: new).matches.first)
        func snapshot(_ inventory: ComponentInventory, _ value: Bool, strict: Bool = false) -> EntitlementSnapshot {
            .init(sourceName: ComponentComparison.sourceName(componentID: inventory.components[0].id), signingIdentifier: "example", architecture: .arm64,
                  entitlements: .init(["flag": .boolean(value)]), numericRepresentation: strict ? .exposed : .normalized)
        }
        let pair = try ComparisonReport(previous: snapshot(old, false), current: snapshot(new, true))
        let review = try ComponentComparison.review(previous: old, current: new, architecture: .arm64,
            entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: pair)])
        func strict(_ value: Bool) throws -> SecurityDeltaEntitlementEvidence {
            try .capture(snapshot: snapshot(old, value, strict: true), side: .previous, inventoryID: old.id,
                componentID: old.components[0].id, relativePath: "Contents/MacOS/Main", capturedAt: Date(timeIntervalSince1970: 0))
        }
        let unavailable = try SecurityDeltaEntitlementEvidence.unavailable(side: .previous, inventoryID: old.id, componentID: old.components[0].id,
            relativePath: "Contents/MacOS/Main", architecture: .arm64, capturedAt: Date(timeIntervalSince1970: 1), reason: "source_stale")
        for item in [try strict(false), unavailable] {
            let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [item]))
            XCTAssertEqual(report.observations.first { $0.subject == "key:flag" && $0.category == .entitlements }?.disposition, .observedChange)
            XCTAssertTrue(report.observations.contains { $0.subject == "strict-evidence-coverage" && $0.disposition == .unresolved })
        }
        let conflict = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [strict(true)]))
        XCTAssertTrue(conflict.observations.contains { $0.subject == "evidence-consistency" && $0.disposition == .unresolved })
        XCTAssertFalse(conflict.observations.contains { $0.subject == "key:flag" && $0.disposition == .observedChange })
    }
    func testStrictEvidenceComparesOnlyBoundMatchedPair() throws {
        func inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])])
        }
        let old = inventory(), new = inventory()
        let review = try ComponentComparison.review(previous: old, current: new, architecture: .arm64, entitlementResults: [])
        func evidence(_ inventory: ComponentInventory, _ side: SecurityDeltaSide, _ value: EntitlementValue) throws -> SecurityDeltaEntitlementEvidence {
            let snapshot = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64,
                entitlements: .init(["capability": value]), numericRepresentation: .exposed)
            return try .capture(snapshot: snapshot, side: side, inventoryID: inventory.id, componentID: inventory.components[0].id,
                relativePath: "Contents/MacOS/Main", capturedAt: Date(timeIntervalSince1970: 0))
        }
        let a = try evidence(old, .previous, .integer(1)), b = try evidence(new, .current, .unsignedInteger(1))
        let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [a, b]))
        let change = try XCTUnwrap(report.observations.first { $0.category == .entitlements && $0.subject == "key:capability" })
        XCTAssertEqual(change.disposition, .observedChange)
        XCTAssertTrue(change.evidence.allSatisfy { $0.evidenceKey?.hasPrefix("strict-entitlement:") == true })
        let missing = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [a]))
        XCTAssertFalse(missing.observations.contains { $0.category == .entitlements && $0.disposition == .observedRemoval })
        let wrong = try evidence(new, .previous, .boolean(true))
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [wrong])))
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [a, a])))
        let archive = try ComponentSecurityDeltaArchive.create(admittedReview: ComponentReviewArchive.capture(review), entitlementEvidence: [b, a])
        let bytes = try archive.data()
        let restored = try ComponentSecurityDeltaArchive.decode(bytes)
        XCTAssertEqual(restored.entitlementEvidence.map(\.sourceBytes), [a.sourceBytes, b.sourceBytes])
        XCTAssertEqual(restored.report.observations.first { $0.subject == "key:capability" && $0.category == .entitlements }?.disposition, .observedChange)
        XCTAssertEqual(try restored.data(), bytes)
    }
    func testStrictRepresentationAndHistoricalRoundTrip() throws {
        let snapshot = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64,
            entitlements: .init(["bool": .boolean(true), "signed": .integer(1), "unsigned": .unsignedInteger(1)]), numericRepresentation: .exposed)
        let evidence = try SecurityDeltaEntitlementEvidence.capture(snapshot: snapshot, side: .previous, inventoryID: UUID(),
            componentID: UUID(), relativePath: "Contents/MacOS/Main", capturedAt: Date(timeIntervalSince1970: 0))
        let restored = try SecurityDeltaEntitlementEvidence.admit(evidence.sourceBytes)
        XCTAssertEqual(restored.sourceBytes, evidence.sourceBytes)
        XCTAssertEqual(restored.state, .observed)
        guard case .dictionary(let entries)? = restored.values else { return XCTFail("Expected typed dictionary") }
        XCTAssertEqual(try entries[0].value.compare(to: .boolean(true)), .equal)
        XCTAssertEqual(try entries[1].value.compare(to: .signed(1)), .equal)
        XCTAssertEqual(try entries[2].value.compare(to: .unsigned(1)), .equal)
    }
    func testAbsentUnavailableAndMalformedStayDistinct() throws {
        let componentID = UUID(), inventoryID = UUID(), date = Date(timeIntervalSince1970: 0)
        let absent = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64, presence: .notPresent, entitlements: .init([:]), numericRepresentation: .exposed)
        let a = try SecurityDeltaEntitlementEvidence.capture(snapshot: absent, side: .current, inventoryID: inventoryID, componentID: componentID,
            relativePath: "Contents/MacOS/Main", capturedAt: date)
        XCTAssertEqual(try SecurityDeltaEntitlementEvidence.admit(a.sourceBytes).state, .absent)
        let unavailable = try SecurityDeltaEntitlementEvidence.unavailable(side: .current, inventoryID: inventoryID, componentID: componentID,
            relativePath: "Contents/MacOS/Main", architecture: .arm64, capturedAt: date, reason: "source_stale")
        XCTAssertEqual(try SecurityDeltaEntitlementEvidence.admit(unavailable.sourceBytes).state, .unavailable)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: a.sourceBytes) as? [String: Any])
        object["unknown"] = true
        XCTAssertThrowsError(try SecurityDeltaEntitlementEvidence.admit(JSONSerialization.data(withJSONObject: object)))
        XCTAssertThrowsError(try SecurityDeltaEntitlementEvidence.capture(snapshot: absent, side: .previous, inventoryID: inventoryID,
            componentID: componentID, relativePath: "../Main", capturedAt: date))
        let legacy = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64, entitlements: .init(["value": .integer(1)]))
        XCTAssertThrowsError(try SecurityDeltaEntitlementEvidence.capture(snapshot: legacy, side: .previous, inventoryID: inventoryID,
            componentID: componentID, relativePath: "Contents/MacOS/Main", capturedAt: date))
        let oversizedKey = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64,
            entitlements: .init([String(repeating: "a", count: 4097): .boolean(true)]), numericRepresentation: .exposed)
        XCTAssertThrowsError(try SecurityDeltaEntitlementEvidence.capture(snapshot: oversizedKey, side: .previous, inventoryID: inventoryID,
            componentID: componentID, relativePath: "Contents/MacOS/Main", capturedAt: date))
        let oversizedText = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64,
            entitlements: .init(["value": .string(String(repeating: "a", count: 1_048_577))]), numericRepresentation: .exposed)
        XCTAssertThrowsError(try SecurityDeltaEntitlementEvidence.capture(snapshot: oversizedText, side: .previous, inventoryID: inventoryID,
            componentID: componentID, relativePath: "Contents/MacOS/Main", capturedAt: date))
        let missingIdentifier = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "", architecture: .arm64,
            entitlements: .init([:]), numericRepresentation: .exposed)
        XCTAssertThrowsError(try SecurityDeltaEntitlementEvidence.capture(snapshot: missingIdentifier, side: .previous, inventoryID: inventoryID,
            componentID: componentID, relativePath: "Contents/MacOS/Main", capturedAt: date))
    }
    func testStrictDocumentsDoNotOverrideRecordedSliceConflict() throws {
        func inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["x86_64"])])
        }
        let a = inventory(), b = inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        func evidence(_ inventory: ComponentInventory, _ side: SecurityDeltaSide, _ flag: Bool) throws -> SecurityDeltaEntitlementEvidence {
            let snapshot = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64,
                entitlements: .init(["flag": .boolean(flag)]), numericRepresentation: .exposed)
            return try .capture(snapshot: snapshot, side: side, inventoryID: inventory.id, componentID: inventory.components[0].id,
                relativePath: "Contents/MacOS/Main", capturedAt: Date(timeIntervalSince1970: 0))
        }
        let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [evidence(a, .previous, false), evidence(b, .current, true)]))
        let refusal = try XCTUnwrap(report.observations.first { $0.category == .entitlements && $0.subject == "slice" })
        XCTAssertEqual(refusal.disposition, .unresolved)
        XCTAssertTrue(refusal.evidence.contains { $0.category == .componentInventory && $0.evidenceKey == "architectures" })
        XCTAssertFalse(report.observations.contains { $0.subject == "key:flag" && $0.disposition == .observedChange })
    }
    func testOneSidedEvidenceIsContextNotFabricatedPairwiseAddition() throws {
        let scope = InventoryScope(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: [])
        let old = ComponentInventory(scope: scope, components: [])
        let component = ComponentRecord(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])
        let new = ComponentInventory(scope: scope, components: [component])
        let review = try ComponentComparison.review(previous: old, current: new, architecture: .arm64, entitlementResults: [])
        let snapshot = EntitlementSnapshot(sourceName: "Main", signingIdentifier: "example", architecture: .arm64,
            entitlements: .init(["flag": .boolean(true)]), numericRepresentation: .exposed)
        let captured = try SecurityDeltaEntitlementEvidence.capture(snapshot: snapshot, side: .current, inventoryID: new.id,
            componentID: component.id, relativePath: component.relativePath, capturedAt: Date(timeIntervalSince1970: 0))
        let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, entitlementEvidence: [captured]))
        let context = try XCTUnwrap(report.observations.first { $0.category == .entitlements && $0.subject == "one-sided-context" })
        XCTAssertEqual(context.disposition, .unresolved)
        XCTAssertEqual(context.previousState, .unexamined)
        XCTAssertEqual(context.currentState, .observed)
        XCTAssertTrue(context.evidence.contains { $0.side == .current && $0.componentID == component.id })
        XCTAssertFalse(report.observations.contains { $0.category == .entitlements && $0.disposition == .observedAddition })
    }
}
