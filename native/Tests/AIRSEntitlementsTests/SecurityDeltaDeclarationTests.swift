import XCTest
import Foundation
import AIRSCore
import EntitlementDiffCore
@testable import AIRSEntitlements

final class SecurityDeltaDeclarationTests: XCTestCase {
    func testCandidateAndAmbiguousMatchesNeverCompareDeclarations() throws {
        func component(_ name: String) -> ComponentRecord {
            .init(relativePath: "Contents/XPCServices/\(name).xpc/Contents/MacOS/\(name)", kind: "xpc", declaredBundleID: "shared", architectures: ["arm64"])
        }
        func inventory(_ components: [ComponentRecord]) -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/XPCServices"], completion: .completeWithinScope, exclusions: [], issues: []), components: components)
        }
        func info(_ record: ComponentRecord, _ version: String) throws -> DeclarationObservation {
            let source = try CodeUnitPreflight.declarationLocations(relativePath: record.relativePath).infoPath
            return .init(componentID: record.id, category: .info, relativeSource: source, state: .present,
                bytes: try PropertyListSerialization.data(fromPropertyList: ["CFBundleVersion": version], format: .binary, options: 0))
        }
        for ambiguous in [false, true] {
            let old = inventory(ambiguous ? [component("A"), component("B")] : [component("A")]), new = inventory([component("C")])
            let review = try ComponentComparison.review(previous: old, current: new, architecture: .arm64, entitlementResults: [],
                previousDeclarations: try old.components.map { try info($0, "1") }, currentDeclarations: try new.components.map { try info($0, "2") })
            XCTAssertTrue(review.matching.matches.contains { $0.relation == (ambiguous ? .ambiguous : .uniqueIdentifierCandidate) })
            let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
            XCTAssertFalse(report.observations.contains { $0.category == .informationPropertyList && $0.subject == "key:CFBundleVersion" })
            XCTAssertTrue(report.observations.contains { $0.disposition == .unresolved || $0.disposition == .declined })
        }
    }
    private func fixture() -> (ComponentInventory, ComponentInventory) {
        func inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                  components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])])
        }
        return (inventory(), inventory())
    }
    private func observation(_ component: ComponentRecord, _ category: DeclarationCategory, _ values: [String: Any]) throws -> DeclarationObservation {
        .init(componentID: component.id, category: category, architecture: category == .loadCommands ? "arm64" : nil,
              relativeSource: category == .info ? "Contents/Info.plist" : (category == .privacy ? "Contents/Resources/PrivacyInfo.xcprivacy" : component.relativePath), state: .present,
              bytes: try PropertyListSerialization.data(fromPropertyList: values, format: .binary, options: 0))
    }
    private func binding(_ component: ComponentRecord) throws -> DeclarationObservation {
        try observation(component, .info, ["CFBundleExecutable": "Main"])
    }
    func testTypedInfoChangesAndEvidenceAreBoundToBothSides() throws {
        let (a, b) = fixture()
        let old = try observation(a.components[0], .info, ["CFBundleExecutable": "Main", "CFBundleVersion": true, "ignored": "before"])
        let new = try observation(b.components[0], .info, ["CFBundleExecutable": "Main", "CFBundleVersion": 1, "ignored": "after"])
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
            previousDeclarations: [old], currentDeclarations: [new])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        let change = try XCTUnwrap(report.observations.first { $0.category == .informationPropertyList && $0.subject == "key:CFBundleVersion" })
        XCTAssertEqual(change.disposition, .observedChange)
        XCTAssertEqual(change.evidence.count, 4)
        XCTAssertEqual(change.evidence.prefix(2).map(\.inventoryID), [a.id, b.id])
        XCTAssertTrue(change.evidence.prefix(2).allSatisfy { $0.relativeSource == "Contents/Info.plist" && $0.evidenceKey == "declaration:key:CFBundleVersion" })
        XCTAssertTrue(change.evidence.suffix(2).allSatisfy { $0.evidenceKey == "declaration:binding:CFBundleExecutable" })
        XCTAssertTrue(report.findings.contains { $0.observationIDs.contains(change.id) })
        XCTAssertFalse(report.observations.contains { $0.subject == "key:ignored" })
    }
    func testPresenceKeyCannotAliasManifestPresenceEvidence() throws {
        let (a, b) = fixture()
        let old = try observation(a.components[0], .privacy, ["presence": false])
        let new = try observation(b.components[0], .privacy, ["presence": true])
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
            previousDeclarations: [try binding(a.components[0]), old], currentDeclarations: [try binding(b.components[0]), new])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        let presence = try XCTUnwrap(report.observations.first { $0.category == .privacyManifest && $0.subject == "presence" })
        let key = try XCTUnwrap(report.observations.first { $0.category == .privacyManifest && $0.subject == "key:presence" })
        XCTAssertNotEqual(presence.evidence.first?.evidenceKey, key.evidence.first?.evidenceKey)
        XCTAssertEqual(key.evidence.first?.relativeSource, "Contents/Resources/PrivacyInfo.xcprivacy")
        XCTAssertTrue(key.evidence.contains { $0.category == .informationPropertyList && $0.evidenceKey == "declaration:binding:CFBundleExecutable" })
    }
    func testMismatchedSourceOrExecutableBindingDeclinesComparison() throws {
        let (a, b) = fixture()
        let old = try observation(a.components[0], .privacy, ["flag": false])
        let newBytes = try PropertyListSerialization.data(fromPropertyList: ["flag": true], format: .binary, options: 0)
        let wrongSource = DeclarationObservation(componentID: b.components[0].id, category: .privacy,
            relativeSource: "Contents/Other/PrivacyInfo.xcprivacy", state: .present, bytes: newBytes)
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
            previousDeclarations: [try binding(a.components[0]), old], currentDeclarations: [try binding(b.components[0]), wrongSource])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        let presence = try XCTUnwrap(report.observations.first { $0.category == .privacyManifest && $0.subject == "presence" })
        XCTAssertEqual(presence.disposition, .unresolved)
        XCTAssertTrue(presence.limitations.contains { $0.code == "source_binding_unverified" })
        XCTAssertFalse(report.observations.contains { $0.category == .privacyManifest && $0.subject == "key:flag" })
        let wrongExecutable = try observation(b.components[0], .info, ["CFBundleExecutable": "Different"])
        let wrongInfo = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
            previousDeclarations: [try binding(a.components[0]), old],
            currentDeclarations: [wrongExecutable, try observation(b.components[0], .privacy, ["flag": true])])
        let wrongReport = try ComponentSecurityDeltaAnalyzer.analyze(review: wrongInfo)
        XCTAssertEqual(wrongReport.observations.first { $0.category == .privacyManifest && $0.subject == "presence" }?.disposition, .unresolved)
    }
    func testPureConventionalSourcePaths() throws {
        let root = try CodeUnitPreflight.declarationLocations(relativePath: "Contents/MacOS/Main")
        XCTAssertEqual(root.infoPath, "Contents/Info.plist")
        let xpc = try CodeUnitPreflight.declarationLocations(relativePath: "Contents/XPCServices/A.xpc/Contents/MacOS/A")
        XCTAssertEqual(xpc.infoPath, "Contents/XPCServices/A.xpc/Contents/Info.plist")
        let framework = try CodeUnitPreflight.declarationLocations(relativePath: "Contents/Frameworks/A.framework/Versions/A/A")
        XCTAssertEqual(framework.infoPath, "Contents/Frameworks/A.framework/Versions/A/Resources/Info.plist")
        let flat = try CodeUnitPreflight.declarationLocations(relativePath: "Contents/Frameworks/A.framework/A")
        XCTAssertEqual(flat.resourcePath, "Contents/Frameworks/A.framework/Resources")
        XCTAssertThrowsError(try CodeUnitPreflight.declarationLocations(relativePath: "Contents/Helpers/Tool"))
        XCTAssertThrowsError(try CodeUnitPreflight.declarationLocations(relativePath: "Contents/../MacOS/Tool"))
    }
    func testMissingPrivacyManifestDiffersFromEmptyAndUnreadable() throws {
        let (a, b) = fixture()
        let absent = DeclarationObservation(componentID: a.components[0].id, category: .privacy,
            relativeSource: "Contents/Resources/PrivacyInfo.xcprivacy", state: .notPresent)
        let empty = try observation(b.components[0], .privacy, [:])
        func report(_ current: DeclarationObservation) throws -> ComponentSecurityDeltaReport {
            let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
                previousDeclarations: [try binding(a.components[0]), absent], currentDeclarations: [try binding(b.components[0]), current])
            return try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        }
        let added = try report(empty)
        XCTAssertEqual(added.observations.first { $0.category == .privacyManifest && $0.subject == "presence" }?.disposition, .observedAddition)
        let unreadable = DeclarationObservation(componentID: b.components[0].id, category: .privacy,
            relativeSource: "Contents/Resources/PrivacyInfo.xcprivacy", state: .unavailable, issue: "unreadable")
        let unresolved = try report(unreadable)
        XCTAssertEqual(unresolved.observations.first { $0.category == .privacyManifest && $0.subject == "presence" }?.disposition, .unresolved)
        XCTAssertFalse(unresolved.findings.contains { $0.explanation.contains("privacy declaration changed") })
    }
    func testLoaderChangeIsStaticAndMissingSideIsNotAnEmptySet() throws {
        let (a, b) = fixture()
        let old = try observation(a.components[0], .loadCommands, ["commands": [["path": "A", "command": "load", "architecture": "arm64"]]])
        let new = try observation(b.components[0], .loadCommands, ["commands": [["path": "B", "command": "load", "architecture": "arm64"]]])
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
            previousDeclarations: [old], currentDeclarations: [new])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        let changed = try XCTUnwrap(report.observations.first { $0.category == .loadCommands && $0.subject == "key:commands" })
        XCTAssertEqual(changed.disposition, .observedChange)
        XCTAssertTrue(report.findings.contains { $0.observationIDs.contains(changed.id) && $0.explanation.contains("does not establish") })
        XCTAssertTrue(report.observations.contains { $0.subject == "dependency:load:A" && $0.disposition == .observedRemoval })
        XCTAssertTrue(report.observations.contains { $0.subject == "dependency:load:B" && $0.disposition == .observedAddition })
        let missing = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [], previousDeclarations: [old])
        let missingReport = try ComponentSecurityDeltaAnalyzer.analyze(review: missing)
        XCTAssertEqual(missingReport.observations.first { $0.category == .loadCommands && $0.subject == "presence" }?.disposition, .unresolved)
        XCTAssertFalse(missingReport.observations.contains { $0.category == .loadCommands && $0.subject == "key:commands" })
    }
    func testLoaderDuplicateOrderAndMalformedFields() throws {
        let (a, b) = fixture()
        func row(_ path: String, _ command: String = "load") -> [String: Any] {
            ["architecture": "arm64", "command": command, "path": path]
        }
        let original = try observation(a.components[0], .loadCommands, ["commands": [row("A"), row("A"), row("B")]])
        let reordered = try observation(b.components[0], .loadCommands, ["commands": [row("B"), row("A"), row("A")]])
        XCTAssertTrue(try ComponentSecurityDeltaLoader.changes(previous: original.values(), current: reordered.values(), architecture: "arm64").isEmpty)
        let removed = try observation(b.components[0], .loadCommands, ["commands": [row("B"), row("A")]])
        let changes = try ComponentSecurityDeltaLoader.changes(previous: original.values(), current: removed.values(), architecture: "arm64")
        XCTAssertEqual(changes.count, 1)
        XCTAssertEqual(changes.first?.previousCount, 2)
        XCTAssertEqual(changes.first?.currentCount, 1)
        let malformed = try observation(b.components[0], .loadCommands, ["commands": [["architecture": "arm64", "command": "load", "path": "A", "useFlags": "not-an-integer"]]])
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
            previousDeclarations: [original], currentDeclarations: [malformed])
        let result = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        XCTAssertTrue(result.observations.contains { $0.subject == "dependency-interpretation" && $0.disposition == .unresolved })
        XCTAssertTrue(result.observations.contains { $0.subject == "key:commands" && $0.disposition == .observedChange })
        XCTAssertFalse(result.observations.contains { $0.subject.hasPrefix("dependency:load:") })
    }
    func testLoaderPropagatesTypedValueNodeLimit() {
        let rows = Array(repeating: EntitlementValue.boolean(true), count: 10_000)
        let dictionary = EntitlementDictionary(["commands": .array(rows)])
        XCTAssertThrowsError(try ComponentSecurityDeltaLoader.changes(previous: dictionary, current: dictionary, architecture: "arm64")) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .typedNodeLimit)
        }
    }
    func testLoaderMetadataChangesAndMaximumPathAreRetained() throws {
        let (a, b) = fixture(), path = String(repeating: "x", count: 4096)
        func row(_ version: String) -> [String: Any] {
            ["architecture": "arm64", "command": "load", "path": path, "currentVersion": version, "compatibilityVersion": "1.0.0"]
        }
        let old = try observation(a.components[0], .loadCommands, ["commands": [row("1.0.0"), row("2.0.0")]])
        let new = try observation(b.components[0], .loadCommands, ["commands": [row("1.0.0"), row("3.0.0")]])
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
            previousDeclarations: [old], currentDeclarations: [new])
        let result = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        let change = try XCTUnwrap(result.observations.first { $0.subject.hasPrefix("dependency:load:") })
        XCTAssertEqual(change.disposition, .observedChange)
        XCTAssertTrue(change.limitations.contains { $0.code == "loader_group_evidence" })
        XCTAssertTrue(change.evidence.allSatisfy { $0.evidenceKey?.hasSuffix(path) == true })
        let invalidVersion = try observation(b.components[0], .loadCommands, ["commands": [row("01.0.0")]])
        XCTAssertThrowsError(try ComponentSecurityDeltaLoader.changes(previous: old.values(), current: invalidVersion.values(), architecture: "arm64"))
    }
    func testCorrelatesOnlyRecordedChangesInTheSameComponent() throws {
        let (a, b) = fixture()
        let oldInfo = try observation(a.components[0], .info, ["CFBundleExecutable": "Main", "CFBundleVersion": "1"])
        let newInfo = try observation(b.components[0], .info, ["CFBundleExecutable": "Main", "CFBundleVersion": "2"])
        let oldPrivacy = try observation(a.components[0], .privacy, ["tracking": false])
        let newPrivacy = try observation(b.components[0], .privacy, ["tracking": true])
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
            previousDeclarations: [oldInfo, oldPrivacy], currentDeclarations: [newInfo, newPrivacy])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        let finding = try XCTUnwrap(report.findings.first { $0.kind == .componentMultiCategory })
        XCTAssertEqual(finding.observationIDs.count, 2)
        XCTAssertTrue(finding.explanation.contains("does not establish causation"))
        XCTAssertTrue(finding.evidence.contains { $0.category == .informationPropertyList })
        XCTAssertTrue(finding.evidence.contains { $0.category == .privacyManifest })
        let reordered = try ComponentSecurityDeltaRules.sameComponent(Array(report.observations.reversed()), review: review)
        XCTAssertEqual(reordered.map(\.id), [finding.id])
        let wrongReview = try ComponentComparison.review(previous: fixture().0, current: fixture().1, architecture: .arm64, entitlementResults: [])
        XCTAssertThrowsError(try ComponentSecurityDeltaRules.sameComponent(report.observations, review: wrongReview))
        let infoChange = try XCTUnwrap(report.observations.first { $0.category == .informationPropertyList && $0.disposition == .observedChange })
        let forged = SecurityDeltaObservation(id: infoChange.id, category: .loadCommands, componentPath: infoChange.componentPath,
            subject: infoChange.subject, disposition: infoChange.disposition, previousState: infoChange.previousState,
            currentState: infoChange.currentState, previousValue: infoChange.previousValue, currentValue: infoChange.currentValue,
            evidence: infoChange.evidence, limitations: infoChange.limitations)
        XCTAssertThrowsError(try ComponentSecurityDeltaRules.sameComponent([forged], review: review))
        XCTAssertThrowsError(try ComponentSecurityDeltaRules.sameComponent([infoChange, infoChange], review: review))
    }
    func testEntitlementSnapshotsPreserveTypesAndUnavailableOutcome() throws {
        let (a, b) = fixture()
        let match = try XCTUnwrap(ComponentMatcher.match(previous: a, current: b).matches.first)
        func snapshot(_ id: UUID, _ value: EntitlementValue) -> EntitlementSnapshot {
            .init(sourceName: ComponentComparison.sourceName(componentID: id), signingIdentifier: "owned", architecture: .arm64,
                  entitlements: .init(["capability": value]))
        }
        let comparison = try ComparisonReport(previous: snapshot(a.components[0].id, .boolean(true)), current: snapshot(b.components[0].id, .integer(1)))
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64,
            entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: comparison)])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        let change = try XCTUnwrap(report.observations.first { $0.category == .entitlements && $0.subject == "key:capability" })
        XCTAssertEqual(change.disposition, .observedChange)
        XCTAssertTrue(change.limitations.contains { $0.code == "numeric_representation_unspecified" })
        XCTAssertTrue(report.findings.contains { $0.observationIDs.contains(change.id) && $0.explanation.contains("does not establish") })
        let unavailable = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let missingReport = try ComponentSecurityDeltaAnalyzer.analyze(review: unavailable)
        XCTAssertEqual(missingReport.observations.first { $0.category == .entitlements && $0.subject == "presence" }?.disposition, .unresolved)
        XCTAssertEqual(missingReport.observations.first { $0.category == .entitlements && $0.subject == "presence" }?.previousState, .unknown)
        XCTAssertFalse(missingReport.observations.contains { $0.category == .entitlements && $0.subject == "key:capability" })
    }
    func testPrivacyDistinctUnicodeKeysRemainDistinctOrAreDeclined() throws {
        let (a, b) = fixture()
        func plist(_ first: String, _ second: String) -> Data {
            Data(("<?xml version=\"1.0\" encoding=\"UTF-8\"?><plist version=\"1.0\"><dict><key>é</key><string>" + first + "</string><key>e\u{301}</key><string>" + second + "</string></dict></plist>").utf8)
        }
        func privacy(_ record: ComponentRecord, _ bytes: Data) -> DeclarationObservation {
            .init(componentID: record.id, category: .privacy, relativeSource: "Contents/Resources/PrivacyInfo.xcprivacy", state: .present, bytes: bytes)
        }
        do {
            let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [],
                previousDeclarations: [try binding(a.components[0]), privacy(a.components[0], plist("a", "b"))],
                currentDeclarations: [try binding(b.components[0]), privacy(b.components[0], plist("c", "d"))])
            let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
            let keys = report.observations.filter { $0.category == .privacyManifest && $0.subject.hasPrefix("key:") }
            XCTAssertEqual(keys.count, 2, "A collapsed pair must never become a successful comparison")
            if keys.count == 2 { XCTAssertNotEqual(Data(keys[0].subject.utf8), Data(keys[1].subject.utf8)) }
        } catch { XCTAssertEqual(error as? InspectionArchiveError, .invalid) }
    }
    func testOversizedEvidenceKeyRefusesBeforePublishingReport() throws {
        let (a, b) = fixture()
        let match = try XCTUnwrap(ComponentMatcher.match(previous: a, current: b).matches.first)
        let key = String(repeating: "k", count: 4097)
        func snapshot(_ id: UUID, _ value: Bool) -> EntitlementSnapshot {
            .init(sourceName: ComponentComparison.sourceName(componentID: id), signingIdentifier: "owned", architecture: .arm64,
                  entitlements: .init([key: .boolean(value)]))
        }
        let comparison = try ComparisonReport(previous: snapshot(a.components[0].id, false), current: snapshot(b.components[0].id, true))
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64,
            entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: comparison)])
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(review: review)) { error in
            XCTAssertEqual((error as? SecurityDeltaRefusal)?.code, .diagnosticLimit)
        }
    }
}
