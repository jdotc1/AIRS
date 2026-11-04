import XCTest
import AIRSCore
import EntitlementDiffCore
@testable import AIRSEntitlements

final class SecurityDeltaInventoryTests: XCTestCase {
    func testCancelledAnalyzerDoesNotPublishReport() async throws {
        let value = try review(inventory([record("A")]), inventory([record("A")]))
        let task = Task { () throws -> ComponentSecurityDeltaReport in
            withUnsafeCurrentTask { $0?.cancel() }
            return try ComponentSecurityDeltaAnalyzer.analyze(review: value)
        }
        do { _ = try await task.value; XCTFail("Cancelled analysis must not publish a report") }
        catch { XCTAssertTrue(error is CancellationError) }
    }
    func testReducedOutputLimitsDiscloseOmissionsAndRoundTrip() throws {
        let old = inventory([record("A"), record("B")]), new = inventory([record("C"), record("D")])
        let value = try review(old, new), options = try SecurityDeltaOptions(maximumObservations: 2, maximumFindings: 1)
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: value, options: options)
        XCTAssertEqual(report.observations.count, 2)
        XCTAssertLessThanOrEqual(report.findings.count, 1)
        XCTAssertTrue(report.findings.allSatisfy { finding in finding.observationIDs.allSatisfy { id in report.observations.contains { $0.id == id } } })
        XCTAssertTrue(report.coverage.omissions.contains { $0.reason.code == "observation_limit" && $0.count > 0 && $0.countIsExact })
        let token = try ComponentReviewArchive.capture(value)
        let document = try ComponentSecurityDeltaArchive.create(admittedReview: token, options: options)
        let reopened = try ComponentSecurityDeltaArchive.decode(document.data())
        XCTAssertEqual(reopened.report.options.maximumObservations, 2)
        XCTAssertEqual(reopened.report.identity.evidenceBasisID, report.identity.evidenceBasisID)
        XCTAssertThrowsError(try SecurityDeltaOptions(maximumObservations: 8193)) { XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .observationLimit) }
        XCTAssertThrowsError(try SecurityDeltaOptions(maximumFindings: 2049)) { XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .findingLimit) }
    }
    func testObservationCapDisclosesUnknownDependentFindingCount() throws {
        let old = inventory([record("First"), record("Second")]), new = inventory([record("Third")])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review(old, new),
            options: SecurityDeltaOptions(maximumObservations: 1, maximumFindings: 1))
        let unknown = try XCTUnwrap(report.coverage.omissions.first { $0.reason.code == "finding_limit" && !$0.countIsExact })
        XCTAssertEqual(unknown.count, 0)
        XCTAssertFalse(unknown.detailListComplete)
        XCTAssertTrue(report.coverage.omissions.contains { $0.reason.code == "observation_limit" && $0.count > 0 && $0.countIsExact })
    }
    func testInventoryFieldsProduceEvidenceLinkedChangesWithoutBinaryClaim() throws {
        let scope = InventoryScope(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: [])
        let old = ComponentInventory(scope: scope, components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", declaredVersion: "1",
            architectures: ["arm64"], minimumOSByArchitecture: ["arm64": "14.0"])])
        let new = ComponentInventory(scope: scope, components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", declaredVersion: "2",
            architectures: ["arm64", "x86_64"], minimumOSByArchitecture: ["arm64": "15.0", "x86_64": "14.0"])])
        let result = try ComponentSecurityDeltaAnalyzer.analyze(review: ComponentComparison.review(previous: old, current: new, architecture: .arm64, entitlementResults: []))
        let version = try XCTUnwrap(result.observations.first { $0.category == .componentInventory && $0.subject == "version" })
        XCTAssertEqual(version.disposition, .observedChange)
        XCTAssertTrue(result.findings.contains { $0.observationIDs.contains(version.id) && $0.explanation.contains("does not establish executable-byte changes") })
        XCTAssertEqual(result.observations.first { $0.subject == "architectures" }?.disposition, .observedChange)
        XCTAssertEqual(result.observations.first { $0.subject == "minimumOS:arm64" }?.disposition, .observedChange)
        XCTAssertEqual(result.observations.first { $0.subject == "minimumOS:x86_64" }?.disposition, .unresolved)
    }
    func testUnorderedInventoryAndScopeRecordsAreCanonical() throws {
        let id = UUID(), componentID = UUID(), capturedAt = Date(timeIntervalSince1970: 1)
        func inventory(reversed: Bool) -> ComponentInventory {
            let locations = ["Contents/Helpers", "Contents/MacOS"], issues = ["a", "b"], architectures = ["arm64", "x86_64"]
            return .init(id: id, capturedAt: capturedAt,
                scope: .init(searchedLocations: reversed ? locations.reversed() : locations, completion: .partial,
                             exclusions: reversed ? issues.reversed() : issues, issues: reversed ? issues.reversed() : issues),
                components: [.init(id: componentID, relativePath: "Contents/MacOS/Main", kind: "app",
                    architectures: reversed ? architectures.reversed() : architectures, readIssues: reversed ? issues.reversed() : issues)])
        }
        let previous = inventory(reversed: false)
        let first = try ComponentSecurityDeltaAnalyzer.analyze(review: review(previous, inventory(reversed: false)))
        let second = try ComponentSecurityDeltaAnalyzer.analyze(review: review(previous, inventory(reversed: true)))
        XCTAssertEqual(first.identity.evidenceBasisID, second.identity.evidenceBasisID)
        XCTAssertEqual(first.observations.map(\.id), second.observations.map(\.id))
        XCTAssertEqual(first.coverage.currentIssues, second.coverage.currentIssues)
    }
    func testRelatedComponentsRequireRecordedMatchedAncestry() throws {
        func inventory(version: String, related: Bool) -> ComponentInventory {
            let root = ComponentRecord(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])
            let first = ComponentRecord(parentID: related ? root.id : nil, relativePath: "Contents/Helpers/A", kind: "helper", declaredVersion: version, architectures: ["arm64"])
            let second = ComponentRecord(parentID: related ? root.id : nil, relativePath: "Contents/Helpers/B", kind: "helper", declaredVersion: version, architectures: ["arm64"])
            return .init(scope: .init(searchedLocations: ["Contents/MacOS", "Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: []), components: [root, first, second])
        }
        let old = inventory(version: "1", related: true), new = inventory(version: "2", related: true)
        let review = try ComponentComparison.review(previous: old, current: new, architecture: .arm64, entitlementResults: [])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        let finding = try XCTUnwrap(report.findings.first { $0.kind == .relatedComponents })
        XCTAssertEqual(finding.observationIDs.count, 2)
        XCTAssertTrue(finding.evidence.contains { $0.category == .componentInventory && $0.evidenceKey == "parentID" })
        XCTAssertEqual(try ComponentSecurityDeltaRules.relatedComponents(Array(report.observations.reversed()), review: review).findings.map(\.id), [finding.id])
        let unrelated = try ComponentComparison.review(previous: inventory(version: "1", related: false), current: inventory(version: "2", related: false), architecture: .arm64, entitlementResults: [])
        XCTAssertFalse(try ComponentSecurityDeltaAnalyzer.analyze(review: unrelated).findings.contains { $0.kind == .relatedComponents })
        let changedHierarchy = try ComponentComparison.review(previous: old, current: inventory(version: "2", related: false), architecture: .arm64, entitlementResults: [])
        XCTAssertFalse(try ComponentSecurityDeltaAnalyzer.analyze(review: changedHierarchy).findings.contains { $0.kind == .relatedComponents })
    }
    func testDeepRelatedHierarchyReportsOmittedFindingWithoutLosingObservations() throws {
        func inventory(_ version: String) -> ComponentInventory {
            let root = ComponentRecord(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])
            var records = [root]
            for branch in ["A", "B"] {
                var parent = root.id
                for index in 0..<18 {
                    let record = ComponentRecord(parentID: parent, relativePath: "Contents/Helpers/\(branch)\(index)", kind: "helper",
                        declaredVersion: index == 17 ? version : nil, architectures: ["arm64"])
                    records.append(record); parent = record.id
                }
            }
            return .init(scope: .init(searchedLocations: ["Contents/MacOS", "Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: []), components: records)
        }
        let review = try ComponentComparison.review(previous: inventory("1"), current: inventory("2"), architecture: .arm64, entitlementResults: [])
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: review)
        XCTAssertTrue(report.observations.contains { $0.subject == "version" && $0.disposition == .observedChange })
        let omission = try XCTUnwrap(report.coverage.omissions.first { $0.reason.code == "evidence_reference_limit" })
        XCTAssertEqual(omission.count, 1)
        XCTAssertTrue(omission.countIsExact)
        XCTAssertFalse(omission.detailListComplete)
    }
    private func inventory(_ records: [ComponentRecord], completion: InventoryCompletion = .completeWithinScope,
                           exclusions: [String] = []) -> ComponentInventory {
        .init(scope: .init(searchedLocations: ["Contents/XPCServices"], completion: completion,
                           exclusions: exclusions, issues: []), components: records)
    }
    private func record(_ name: String, kind: String = "xpc", identifier: String? = nil) -> ComponentRecord {
        .init(relativePath: "Contents/XPCServices/" + name, kind: kind, declaredBundleID: identifier, architectures: ["arm64"])
    }
    private func review(_ old: ComponentInventory, _ new: ComponentInventory) throws -> ComponentReview {
        try ComponentComparison.review(previous: old, current: new, architecture: .arm64, entitlementResults: [])
    }
    func testAddedXPCAndRemovedComponentRequireCoveredScopes() throws {
        let a = inventory([record("Old")]), b = inventory([record("New")])
        let result = try ComponentSecurityDeltaAnalyzer.analyze(review: review(a, b))
        XCTAssertTrue(result.findings.contains { $0.kind == .xpcAdded && $0.disposition == .observedAddition })
        XCTAssertTrue(result.findings.contains { $0.kind == .componentRemoved && $0.disposition == .observedRemoval })
        XCTAssertTrue(result.findings.allSatisfy { !$0.evidence.isEmpty })
        XCTAssertTrue(result.findings.allSatisfy { $0.evidence.contains { $0.componentID == nil && $0.evidenceKey == "scope" } })
        XCTAssertEqual(result.observations.map(\.id), try ComponentSecurityDeltaAnalyzer.analyze(review: review(a, b)).observations.map(\.id))
    }
    func testEvidenceIdentityBindsPathKindAndScope() throws {
        let old = inventory([]), id = UUID(), captured = Date(timeIntervalSince1970: 1)
        func current(path: String, kind: String, issues: [String] = []) -> ComponentInventory {
            .init(id: id, capturedAt: captured,
                scope: .init(searchedLocations: ["Contents/XPCServices"], completion: .completeWithinScope, exclusions: [], issues: []),
                components: [.init(id: UUID(uuidString: "00000000-0000-0000-0000-000000000001")!, relativePath: path,
                    kind: kind, architectures: ["arm64"], readIssues: issues)])
        }
        let a = try ComponentSecurityDeltaAnalyzer.analyze(review: review(old, current(path: "Contents/XPCServices/A", kind: "xpc")))
        let b = try ComponentSecurityDeltaAnalyzer.analyze(review: review(old, current(path: "Contents/XPCServices/B", kind: "xpc")))
        let c = try ComponentSecurityDeltaAnalyzer.analyze(review: review(old, current(path: "Contents/XPCServices/A", kind: "helper")))
        let d = try ComponentSecurityDeltaAnalyzer.analyze(review: review(old, current(path: "Contents/XPCServices/A", kind: "helper", issues: ["No containing bundle metadata"])))
        XCTAssertNotEqual(a.identity.evidenceBasisID, b.identity.evidenceBasisID)
        XCTAssertNotEqual(a.identity.evidenceBasisID, c.identity.evidenceBasisID)
        XCTAssertNotEqual(c.identity.evidenceBasisID, d.identity.evidenceBasisID)
        XCTAssertNotEqual(a.findings.first?.id, c.findings.first?.id)
        let surface = try XCTUnwrap(d.findings.first { $0.kind == .componentAdded })
        XCTAssertFalse(surface.limitations.isEmpty)
    }
    func testPartialAndExcludedInventoriesDoNotProveRemoval() throws {
        let old = inventory([record("Old")])
        for current in [inventory([], completion: .partial), inventory([], exclusions: ["symbolic link skipped"])] {
            let result = try ComponentSecurityDeltaAnalyzer.analyze(review: review(old, current))
            XCTAssertFalse(result.findings.contains { $0.kind == .componentRemoved })
            XCTAssertEqual(result.observations.first?.disposition, .unresolved)
            XCTAssertEqual(result.coverage.currentExclusions, current.scope.exclusions)
            XCTAssertEqual(result.coverage.currentLocations, current.scope.searchedLocations)
        }
    }
    func testForgedMatchingCannotBecomeAnAddition() throws {
        let a = inventory([record("Old")]), b = inventory([], completion: .partial)
        let valid = try review(a, b), original = try XCTUnwrap(valid.matching.matches.first)
        let forged = ComponentMatch(id: original.id, previousID: original.previousID, currentID: nil,
                                    relation: .removedWithinScope, reasons: [])
        let invalid = ComponentReview(previous: a, current: b,
            matching: .init(matches: [forged], previousScope: a.scope, currentScope: b.scope), architecture: .arm64,
            entitlementResults: valid.entitlementResults, previousDeclarations: [], currentDeclarations: [])
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(review: invalid)) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .componentCorrespondenceUnaccepted)
        }
    }
    func testDuplicateComponentIdentityHasStableRefusal() throws {
        let item = record("A"), a = inventory([item]), b = inventory([record("A")])
        let valid = try review(a, b)
        let duplicated = ComponentInventory(id: a.id, capturedAt: a.capturedAt, scope: a.scope, components: [item, item])
        let invalid = ComponentReview(previous: duplicated, current: b, matching: valid.matching, architecture: .arm64,
            entitlementResults: [], previousDeclarations: [], currentDeclarations: [])
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(review: invalid)) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .duplicateComponentIdentity)
        }
    }
    func testOverdeepCapturedEntitlementRefusesBeforeBasisEncoding() throws {
        let old = inventory([record("A")]), new = inventory([record("A")])
        let match = try XCTUnwrap(ComponentMatcher.match(previous: old, current: new).matches.first)
        var value = EntitlementValue.boolean(true)
        for _ in 0..<34 { value = .array([value]) }
        func snapshot(_ id: UUID) -> EntitlementSnapshot {
            .init(sourceName: ComponentComparison.sourceName(componentID: id), signingIdentifier: "owned", architecture: .arm64,
                  entitlements: .init(["deep": value]))
        }
        let report = try ComparisonReport(previous: snapshot(old.components[0].id), current: snapshot(new.components[0].id))
        let review = try ComponentComparison.review(previous: old, current: new, architecture: .arm64,
            entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: report)])
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(review: review)) { error in
            XCTAssertEqual((error as? SecurityDeltaRefusal)?.code, .typedDepthLimit)
        }
    }
    func testAggregateDecodedByteLimitRefusesBeforeBasisEncoding() throws {
        let old = inventory([record("A")]), new = inventory([record("A")])
        let match = try XCTUnwrap(ComponentMatcher.match(previous: old, current: new).matches.first)
        let bytes = Data(repeating: 0x5a, count: 8 * 1_048_576)
        func snapshot(_ id: UUID) -> EntitlementSnapshot {
            .init(sourceName: ComponentComparison.sourceName(componentID: id), signingIdentifier: "owned", architecture: .arm64,
                  entitlements: .init(["x": .data(bytes)]))
        }
        let pair = try ComparisonReport(previous: snapshot(old.components[0].id), current: snapshot(new.components[0].id))
        let value = try ComponentComparison.review(previous: old, current: new, architecture: .arm64,
            entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: pair)])
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(review: value)) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .decodedByteLimit)
        }
    }
    func testSameLocationKeepsIdentifierChangeAndUnicodePathsDistinct() throws {
        let a = inventory([record("é", identifier: "before")])
        let b = inventory([record("é", identifier: "after"), record("e\u{301}")])
        let result = try ComponentSecurityDeltaAnalyzer.analyze(review: review(a, b))
        XCTAssertTrue(result.observations.contains { $0.subject == "bundleIdentifier" && $0.disposition == .observedChange })
        XCTAssertTrue(result.observations.contains { $0.disposition == .observedAddition && $0.componentPath.utf8.elementsEqual("Contents/XPCServices/e\u{301}".utf8) })
    }
}
