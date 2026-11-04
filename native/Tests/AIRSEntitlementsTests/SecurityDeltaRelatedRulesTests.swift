import XCTest
import Foundation
import AIRSCore
import EntitlementDiffCore
@testable import AIRSEntitlements

final class SecurityDeltaRelatedRulesTests: XCTestCase {
    func testAddedAndChangedSiblingsGroupOnlyThroughAcceptedAncestor() throws {
        func inventory(current: Bool, relate: Bool) -> ComponentInventory {
            let root = ComponentRecord(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])
            let changed = ComponentRecord(parentID: relate ? root.id : nil, relativePath: "Contents/Helpers/Existing", kind: "helper",
                                          declaredVersion: current ? "2" : "1", architectures: ["arm64"])
            let additions = current ? ["NewA", "NewB"].map { ComponentRecord(parentID: relate ? root.id : nil,
                relativePath: "Contents/Helpers/" + $0, kind: "helper", architectures: ["arm64"]) } : []
            return .init(scope: .init(searchedLocations: ["Contents/MacOS", "Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: []),
                         components: [root, changed] + additions)
        }
        func analyze(_ relate: Bool) throws -> ComponentSecurityDeltaReport {
            let review = try ComponentComparison.review(previous: inventory(current: false, relate: relate), current: inventory(current: true, relate: relate), architecture: .arm64, entitlementResults: [])
            return try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        }
        let report = try analyze(true)
        let finding = try XCTUnwrap(report.findings.first { $0.kind == .relatedComponents })
        let linked = report.observations.filter { finding.observationIDs.contains($0.id) }
        XCTAssertEqual(Set(linked.map(\.componentPath)), ["Contents/Helpers/Existing", "Contents/Helpers/NewA", "Contents/Helpers/NewB"])
        XCTAssertEqual(linked.filter { $0.disposition == .observedAddition }.count, 2)
        XCTAssertTrue(finding.explanation.contains("observed side"))
        XCTAssertFalse(try analyze(false).findings.contains { $0.kind == .relatedComponents })
        let reversed = try ComponentComparison.review(previous: inventory(current: true, relate: true), current: inventory(current: false, relate: true), architecture: .arm64, entitlementResults: [])
        let reverseReport = try ComponentSecurityDeltaAnalyzer.analyze(review: reversed)
        let reverseFinding = try XCTUnwrap(reverseReport.findings.first { $0.kind == .relatedComponents })
        XCTAssertEqual(reverseReport.observations.filter { reverseFinding.observationIDs.contains($0.id) && $0.disposition == .observedRemoval }.count, 2)
    }
    func testRelatedGroupsIncludeEverySiblingOrDiscloseWholeFindingOmission() throws {
        func fixture(_ count: Int) throws -> (ComponentReview, [SecurityDeltaObservation]) {
            func inventory() -> ComponentInventory {
                let root = ComponentRecord(relativePath: "Contents/MacOS/Main", kind: "app")
                let children = (0..<count).map { ComponentRecord(parentID: root.id, relativePath: "Contents/Helpers/Child\($0)", kind: "helper") }
                return .init(scope: .init(searchedLocations: ["Contents/MacOS", "Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: []), components: [root] + children)
            }
            let review = try ComponentComparison.review(previous: inventory(), current: inventory(), architecture: .arm64, entitlementResults: [])
            let rows = (1...count).map { index in
                let a = review.previous.components[index], b = review.current.components[index]
                let refs = [(SecurityDeltaSide.previous, review.previous, a), (.current, review.current, b)].map { side, inventory, component in
                    SecurityDeltaEvidenceReference(side: side, inventoryID: inventory.id, componentID: component.id,
                        category: .privacyManifest, relativeSource: component.relativePath, evidenceKey: "declaration:key:flag")
                }
                return SecurityDeltaObservation(id: "child-\(index)", category: .privacyManifest, componentPath: a.relativePath, subject: "key:flag",
                    disposition: .observedChange, previousState: .observed, currentState: .observed,
                    previousValue: .boolean(false), currentValue: .boolean(true), evidence: refs, limitations: [])
            }
            return (review, rows)
        }
        let (small, rows) = try fixture(3)
        let related = try ComponentSecurityDeltaRules.relatedComponents(rows, review: small)
        let repeated = try ComponentSecurityDeltaRules.repeatedDeclarations(rows, review: small)
        XCTAssertEqual(Set(try XCTUnwrap(related.findings.first).observationIDs), Set(rows.map(\.id)))
        XCTAssertEqual(Set(try XCTUnwrap(repeated.findings.first).observationIDs), Set(rows.map(\.id)))
        XCTAssertEqual(related.omittedForReferenceLimit, 0)
        let manyLimitations = rows.enumerated().map { index, row in
            SecurityDeltaObservation(id: row.id, category: row.category, componentPath: row.componentPath, subject: row.subject,
                disposition: row.disposition, previousState: row.previousState, currentState: row.currentState,
                previousValue: row.previousValue, currentValue: row.currentValue, evidence: row.evidence,
                limitations: (0..<12).map { .init(code: "limit-\(index)-\($0)", diagnostic: "recorded limitation") })
        }
        let limitationOverflow = try ComponentSecurityDeltaRules.relatedComponents(manyLimitations, review: small)
        XCTAssertTrue(limitationOverflow.findings.isEmpty)
        XCTAssertEqual(limitationOverflow.omittedForLimitationLimit, 1)
        let repeatedOverflow = try ComponentSecurityDeltaRules.repeatedDeclarations(manyLimitations, review: small)
        XCTAssertTrue(repeatedOverflow.findings.isEmpty)
        XCTAssertEqual(repeatedOverflow.omittedForLimitationLimit, 1)
        let row = rows[0]
        let oversized = SecurityDeltaObservation(id: row.id, category: row.category, componentPath: row.componentPath, subject: row.subject,
            disposition: row.disposition, previousState: row.previousState, currentState: row.currentState,
            previousValue: row.previousValue, currentValue: row.currentValue, evidence: row.evidence,
            limitations: Array(repeating: .init(code: "same", diagnostic: "same"), count: 33))
        XCTAssertThrowsError(try ComponentSecurityDeltaRules.relatedComponents([oversized, rows[1]], review: small)) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .limitationLimit)
        }
        let (large, many) = try fixture(17)
        let omitted = try ComponentSecurityDeltaRules.relatedComponents(many, review: large)
        let repeatedOmitted = try ComponentSecurityDeltaRules.repeatedDeclarations(many, review: large)
        XCTAssertTrue(omitted.findings.isEmpty)
        XCTAssertEqual(omitted.omittedForReferenceLimit, 1)
        XCTAssertTrue(repeatedOmitted.findings.isEmpty)
        XCTAssertEqual(repeatedOmitted.omittedForReferenceLimit, 1)
    }
    func testRepeatedRuleCountsExcessFindingsWithoutAbort() throws {
        func inventory() -> ComponentInventory {
            var records: [ComponentRecord] = [], parent: UUID?
            for index in 0..<7 {
                let item = ComponentRecord(parentID: parent, relativePath: "Contents/Helpers/Parent\(index)", kind: "helper")
                records.append(item); parent = item.id
            }
            records.append(.init(parentID: parent, relativePath: "Contents/Helpers/A", kind: "helper"))
            records.append(.init(parentID: parent, relativePath: "Contents/Helpers/B", kind: "helper"))
            return .init(scope: .init(searchedLocations: ["Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: []), components: records)
        }
        let review = try ComponentComparison.review(previous: inventory(), current: inventory(), architecture: .arm64, entitlementResults: [])
        var observations: [SecurityDeltaObservation] = []
        for key in 0..<300 {
            for index in 7...8 {
                let a = review.previous.components[index], b = review.current.components[index]
                let refs = [(SecurityDeltaSide.previous, review.previous, a), (.current, review.current, b)].map { side, inventory, component in
                    SecurityDeltaEvidenceReference(side: side, inventoryID: inventory.id, componentID: component.id,
                        category: .privacyManifest, relativeSource: component.relativePath, evidenceKey: "key:flag")
                }
                observations.append(.init(id: "\(key)-\(index)", category: .privacyManifest, componentPath: a.relativePath, subject: "key:\(key)",
                    disposition: .observedChange, previousState: .observed, currentState: .observed, previousValue: .boolean(false), currentValue: .boolean(true), evidence: refs, limitations: []))
            }
        }
        let result = try ComponentSecurityDeltaRules.repeatedDeclarations(observations, review: review)
        XCTAssertEqual(result.findings.count, 2048)
        XCTAssertEqual(result.omittedForFindingLimit, 52)
        XCTAssertEqual(result.omittedForReferenceLimit, 0)
    }
    func testRepeatedDeclarationRequiresSameTransitionAndRecordedAncestry() throws {
        func inventory(_ related: Bool) -> ComponentInventory {
            let root = ComponentRecord(relativePath: "Contents/MacOS/Main", kind: "app")
            let a = ComponentRecord(parentID: related ? root.id : nil, relativePath: "Contents/Helpers/A", kind: "helper", declaredBundleID: "same")
            let b = ComponentRecord(parentID: related ? root.id : nil, relativePath: "Contents/Helpers/B", kind: "helper", declaredBundleID: "same")
            return .init(scope: .init(searchedLocations: ["Contents/MacOS", "Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: []), components: [root, a, b])
        }
        func rows(_ review: ComponentReview, secondValue: Bool) -> [SecurityDeltaObservation] {
            (1...2).map { index in
                let a = review.previous.components[index], b = review.current.components[index]
                let references = [(SecurityDeltaSide.previous, review.previous, a), (.current, review.current, b)].map { side, inventory, component in
                    SecurityDeltaEvidenceReference(side: side, inventoryID: inventory.id, componentID: component.id,
                        category: .privacyManifest, relativeSource: component.relativePath, evidenceKey: "declaration:key:flag")
                }
                return .init(id: "observation-\(index)", category: .privacyManifest, componentPath: a.relativePath, subject: "key:flag",
                    disposition: .observedChange, previousState: .observed, currentState: .observed, previousValue: .boolean(false),
                    currentValue: .boolean(index == 1 ? true : secondValue), evidence: references, limitations: [])
            }
        }
        let review = try ComponentComparison.review(previous: inventory(true), current: inventory(true), architecture: .arm64, entitlementResults: [])
        let repeated = try ComponentSecurityDeltaRules.repeatedDeclarations(rows(review, secondValue: true), review: review)
        XCTAssertEqual(repeated.findings.count, 1)
        XCTAssertEqual(repeated.findings.first?.kind, .repeatedDeclaration)
        XCTAssertEqual(repeated.findings.first?.observationIDs.count, 2)
        XCTAssertEqual(try ComponentSecurityDeltaRules.repeatedDeclarations(rows(review, secondValue: false), review: review).findings.count, 0)
        let unrelated = try ComponentComparison.review(previous: inventory(false), current: inventory(false), architecture: .arm64, entitlementResults: [])
        XCTAssertTrue(try ComponentSecurityDeltaRules.repeatedDeclarations(rows(unrelated, secondValue: true), review: unrelated).findings.isEmpty)
        let legacy = rows(review, secondValue: true).map { row in
            SecurityDeltaObservation(id: row.id, category: .entitlements, componentPath: row.componentPath, subject: row.subject,
                disposition: row.disposition, previousState: row.previousState, currentState: row.currentState,
                previousValue: .normalizedInteger("1"), currentValue: .normalizedInteger("2"),
                evidence: row.evidence, limitations: [.init(code: "numeric_representation_unspecified", diagnostic: "Legacy representation is unknown.")])
        }
        let unresolved = try ComponentSecurityDeltaRules.repeatedDeclarations(legacy, review: review)
        XCTAssertTrue(unresolved.findings.isEmpty)
        XCTAssertGreaterThan(unresolved.unspecifiedNumericObservations, 0)
        let unknownValues = rows(review, secondValue: true).map { row in
            SecurityDeltaObservation(id: row.id, category: .loadCommands, componentPath: row.componentPath, subject: "dependency:load:lib",
                disposition: .observedChange, previousState: .observed, currentState: .observed, previousValue: nil, currentValue: nil,
                evidence: row.evidence, limitations: [])
        }
        XCTAssertTrue(try ComponentSecurityDeltaRules.repeatedDeclarations(unknownValues, review: review).findings.isEmpty)
    }
}
