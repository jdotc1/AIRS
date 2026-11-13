import Foundation
import XCTest
import AIRSCore
@testable import AIRSApp

@MainActor
private final class ManualPairRecents: WorkspaceRecentsRecording {
    var recentDocumentURLs: [URL] = []
    func noteRecentDocument(_ url: URL) { recentDocumentURLs.append(url) }
    func clearRecentDocuments() { recentDocumentURLs = [] }
}

private actor ManualPairGate {
    private var released = false
    private var waiting: CheckedContinuation<Void, Never>?
    private(set) var entered = false
    func wait() async {
        entered = true
        if released { return }
        await withCheckedContinuation { waiting = $0 }
    }
    func release() { released = true; waiting?.resume(); waiting = nil }
}

/// Uses owned saved reports and an injected result producer, never a binary audit.
private struct ManualWorkspaceFixture {
    let directory: URL
    let baselineURL: URL
    let currentURL: URL
    let before: Data
    let after: Data
    let preferences: UserDefaults
    let suite: String

    init() throws {
        let project = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent()
            .deletingLastPathComponent().deletingLastPathComponent()
        before = try Data(contentsOf: project.appendingPathComponent("examples/before.audit.json"))
        var current = try XCTUnwrap(JSONSerialization.jsonObject(with: before) as? [String: Any])
        var image = try XCTUnwrap(current["image"] as? [String: Any])
        image["slice_sha256"] = String(repeating: "e", count: 64)
        image["display_name"] = "Owned current report"
        current["image"] = image
        var findings = try XCTUnwrap(current["findings"] as? [[String: Any]])
        for index in findings.indices { findings[index]["id"] = "airsf-" + String(format: "%064x", index + 100) }
        current["findings"] = findings
        after = try JSONSerialization.data(withJSONObject: current)
        directory = FileManager.default.temporaryDirectory.appendingPathComponent("manual-pair-workspace-\(UUID())")
        baselineURL = directory.appendingPathComponent("baseline.json")
        currentURL = directory.appendingPathComponent("current.json")
        suite = "dev.airs.manual-pair-tests.\(UUID())"
        preferences = try XCTUnwrap(UserDefaults(suiteName: suite))
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        try before.write(to: baselineURL)
        try after.write(to: currentURL)
    }

    func remove() {
        preferences.removePersistentDomain(forName: suite)
        try? FileManager.default.removeItem(at: directory)
    }

    static func output(before: Data, after: Data, selection: ManualPairSelection) throws -> Data {
        let old = try AuditReport.decode(before), new = try AuditReport.decode(after)
        let oldObject = try XCTUnwrap(JSONSerialization.jsonObject(with: before) as? [String: Any])
        let newObject = try XCTUnwrap(JSONSerialization.jsonObject(with: after) as? [String: Any])
        let oldImage = try XCTUnwrap(oldObject["image"]), newImage = try XCTUnwrap(newObject["image"])
        var context: [String: Any] = ["baseline_image": oldImage, "current_image": newImage,
            "same_image": false, "model_compatible": true, "analysis_configuration_changed": false,
            "exact_body_candidates": false, "matching_policy": "exact_digest_then_unique_symbol"]
        var rows: [[String: Any]] = []
        for pair in selection.pairs {
            let baseline = try XCTUnwrap(old.findings.first { $0.id == pair.baselineID })
            let current = try XCTUnwrap(new.findings.first { $0.id == pair.currentID })
            rows.append(["key": "manual:\(pair.baselineID):\(pair.currentID)", "match_basis": "manual_review",
                "function_name": current.function.name ?? "", "change": "unchanged", "notes": [],
                "baseline_id": pair.baselineID, "current_id": pair.currentID,
                "before_verdict": baseline.verdict.rawValue, "after_verdict": current.verdict.rawValue,
                "before_scope": baseline.scope, "after_scope": current.scope])
        }
        if !selection.pairs.isEmpty {
            context["matching_policy"] = "manual_then_unique_symbol"
            context["manual_pairs"] = selection.pairs.map { ["baseline_id": $0.baselineID, "current_id": $0.currentID] }
        }
        // The initial empty-selection output exercises the unchanged basic decode path.
        return try JSONSerialization.data(withJSONObject: ["schema_version": 1, "report_kind": "airs.diff",
            "comparison": context, "summary": ["matched_count": rows.count, "changed_count": 0,
                "unchanged_count": rows.count, "added_count": 0, "removed_count": 0, "ambiguous_count": 0],
            "changes": rows, "limitations": ["Owned synthetic workspace interaction fixture."]])
    }

    @MainActor
    func workspace(gate: ManualPairGate? = nil, fails: Bool = false, invalidManualOutput: Bool = false) -> AuditWorkspace {
        AuditWorkspace(recents: ManualPairRecents(), compareSavedReports: { old, new, selection in
            if !selection.pairs.isEmpty {
                if let gate { await gate.wait() }
                if fails { throw ReportError.invalidContents("Owned comparison failure") }
            }
            let data = try Self.output(before: old, after: new, selection: selection)
            if invalidManualOutput && !selection.pairs.isEmpty {
                var object = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
                var rows = try XCTUnwrap(object["changes"] as? [[String: Any]])
                rows[0]["before_scope"] = "not_the_source_scope"
                object["changes"] = rows
                return try JSONSerialization.data(withJSONObject: object)
            }
            return data
        }, supportRoot: directory, preferences: preferences)
    }
}

final class ManualPairWorkspaceTests: XCTestCase {
    @MainActor
    private func settle(_ workspace: AuditWorkspace) async throws {
        for _ in 0..<500 {
            if !workspace.isBusy { return }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        throw ReportError.invalidContents("Owned workspace operation did not settle.")
    }

    private func waitForProducer(_ gate: ManualPairGate) async throws {
        for _ in 0..<500 {
            if await gate.entered { return }
            try await Task.sleep(nanoseconds: 10_000_000)
        }
        await gate.release()
        throw ReportError.invalidContents("Owned result producer did not start.")
    }

    @MainActor
    private func stage(_ fixture: ManualWorkspaceFixture, workspace: AuditWorkspace) async throws -> ManualPairReviewSession {
        workspace.importReport(fixture.currentURL)
        try await settle(workspace)
        workspace.compareBaseline(fixture.baselineURL)
        try await settle(workspace)
        return try XCTUnwrap(workspace.manualPairSession)
    }

    @MainActor
    private func selectAll(_ session: ManualPairReviewSession) {
        for (old, new) in zip(session.sources.baseline.report.findings, session.sources.current.report.findings) {
            session.add(baselineID: old.id, currentID: new.id)
        }
    }

    @MainActor
    func testManualPairWorkspaceFileSourcesAndUnchangedRowsSurviveAcceptedRerun() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let workspace = fixture.workspace(), revision = workspace.reportRevision
        let session = try await stage(fixture, workspace: workspace)
        XCTAssertNotEqual(workspace.reportRevision, revision)
        XCTAssertEqual(session.sources.baseline.url, fixture.baselineURL)
        XCTAssertEqual(session.sources.current.url, fixture.currentURL)
        XCTAssertEqual(session.sources.baseline.data, fixture.before)
        XCTAssertEqual(session.sources.current.data, fixture.after)
        XCTAssertTrue(workspace.blocksFileOpen)
        selectAll(session)
        let originalID = session.acceptedDocument.id
        workspace.compareManualPairs()
        try await settle(workspace)
        XCTAssertFalse(workspace.showingError, workspace.errorMessage)
        XCTAssertNotEqual(session.acceptedDocument.id, originalID)
        XCTAssertEqual(session.acceptedDocument.report.comparison.manualPairs, session.pairs)
        XCTAssertEqual(session.acceptedDocument.manualChanges.count, session.pairs.count)
        XCTAssertTrue(session.acceptedDocument.manualChanges.allSatisfy { $0.change == "unchanged" })
        for row in session.acceptedDocument.manualChanges {
            XCTAssertNotNil(session.sources.baseline.report.findings.first { $0.id == row.baselineID })
            XCTAssertNotNil(session.sources.current.report.findings.first { $0.id == row.currentID })
        }
        XCTAssertEqual(Set(session.acceptedDocument.protectedInputs), Set([fixture.baselineURL, fixture.currentURL]))
    }

    @MainActor
    func testManualPairWorkspaceConflictRemovalAndExplicitReassignment() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let workspace = fixture.workspace(), session = try await stage(fixture, workspace: workspace)
        let old = session.sources.baseline.report.findings, new = session.sources.current.report.findings
        session.add(baselineID: old[0].id, currentID: new[0].id)
        let first = try XCTUnwrap(session.pairs.first)
        session.add(baselineID: old[0].id, currentID: new[1].id)
        XCTAssertEqual(session.pairs, [first])
        XCTAssertTrue(session.message?.contains(old[0].id) == true)
        session.remove(first)
        session.add(baselineID: old[0].id, currentID: new[1].id)
        XCTAssertEqual(session.pairs.first?.currentID, new[1].id)
        XCTAssertNil(session.message)
    }

    @MainActor
    func testManualPairWorkspaceEditDropsLateResultAndPreservesDraftAndLastResult() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let gate = ManualPairGate(), workspace = fixture.workspace(gate: gate)
        let session = try await stage(fixture, workspace: workspace)
        selectAll(session)
        let accepted = session.acceptedDocument.id
        workspace.compareManualPairs()
        try await waitForProducer(gate)
        session.remove(try XCTUnwrap(session.pairs.first))
        let edited = session.pairs
        await gate.release()
        try await settle(workspace)
        XCTAssertEqual(session.acceptedDocument.id, accepted)
        XCTAssertEqual(session.pairs, edited)
        XCTAssertTrue(workspace.status.contains("discarded"))
    }

    @MainActor
    func testManualPairWorkspaceCancellationDropsLateResultWithoutLosingDraft() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let gate = ManualPairGate(), workspace = fixture.workspace(gate: gate)
        let session = try await stage(fixture, workspace: workspace)
        selectAll(session)
        let accepted = session.acceptedDocument.id, pairs = session.pairs
        workspace.compareManualPairs()
        try await waitForProducer(gate)
        workspace.cancel()
        await gate.release()
        try await settle(workspace)
        XCTAssertEqual(session.acceptedDocument.id, accepted)
        XCTAssertEqual(session.pairs, pairs)
        XCTAssertFalse(workspace.showingError)
    }

    @MainActor
    func testManualPairWorkspaceCloseAndSourceReplacementInvalidateOldSubmission() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let gate = ManualPairGate(), workspace = fixture.workspace(gate: gate)
        let session = try await stage(fixture, workspace: workspace)
        selectAll(session)
        let submission = try session.submission(), accepted = session.acceptedDocument
        workspace.compareManualPairs()
        try await waitForProducer(gate)
        workspace.closeComparison()
        await gate.release()
        try await settle(workspace)
        XCTAssertNil(workspace.comparisonDocument)
        XCTAssertNil(workspace.manualPairSession)
        workspace.importReport(fixture.baselineURL)
        try await settle(workspace)
        XCTAssertEqual(workspace.savedReportURL, fixture.baselineURL)
        XCTAssertFalse(session.accept(accepted, submission: submission, workspaceRevision: workspace.reportRevision))
        XCTAssertTrue(session.isClosed)
    }

    @MainActor
    func testManualPairWorkspaceRevisionMismatchRejectsResultEvenForOpenSession() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let workspace = fixture.workspace(), session = try await stage(fixture, workspace: workspace)
        selectAll(session)
        let submission = try session.submission()
        XCTAssertFalse(session.accept(session.acceptedDocument, submission: submission, workspaceRevision: UUID()))
    }

    @MainActor
    func testManualPairWorkspaceSourceReplacementClosesTheExistingDraft() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let workspace = fixture.workspace(), session = try await stage(fixture, workspace: workspace)
        selectAll(session)
        let submission = try session.submission()
        workspace.importReport(fixture.baselineURL)
        try await settle(workspace)
        XCTAssertTrue(session.isClosed)
        XCTAssertNil(workspace.manualPairSession)
        XCTAssertNil(workspace.comparisonDocument)
        XCTAssertEqual(workspace.savedReportURL, fixture.baselineURL)
        XCTAssertFalse(session.accept(session.acceptedDocument, submission: submission, workspaceRevision: workspace.reportRevision))
    }

    @MainActor
    func testManualPairWorkspaceRejectsInvalidSourceBoundResultBeforeInstallation() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let workspace = fixture.workspace(invalidManualOutput: true), session = try await stage(fixture, workspace: workspace)
        selectAll(session)
        let accepted = session.acceptedDocument.id, pairs = session.pairs
        workspace.compareManualPairs()
        try await settle(workspace)
        XCTAssertTrue(workspace.showingError)
        XCTAssertEqual(session.acceptedDocument.id, accepted)
        XCTAssertEqual(session.pairs, pairs)
    }

    @MainActor
    func testManualPairWorkspaceFailedRerunPreservesDraftAndLastResult() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let workspace = fixture.workspace(fails: true), session = try await stage(fixture, workspace: workspace)
        selectAll(session)
        let accepted = session.acceptedDocument.id, pairs = session.pairs
        workspace.compareManualPairs()
        try await settle(workspace)
        XCTAssertEqual(session.acceptedDocument.id, accepted)
        XCTAssertEqual(session.pairs, pairs)
        XCTAssertTrue(workspace.showingError)
    }

    @MainActor
    func testManualPairWorkspaceQuitPreventsLatePublication() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let gate = ManualPairGate(), workspace = fixture.workspace(gate: gate)
        let session = try await stage(fixture, workspace: workspace)
        selectAll(session)
        let accepted = session.acceptedDocument.id
        workspace.compareManualPairs()
        try await waitForProducer(gate)
        let submittedRevision = session.draftRevision
        let quitting = Task { @MainActor in await workspace.finishBeforeQuit() }
        for _ in 0..<100 {
            if session.draftRevision != submittedRevision { break }
            await Task.yield()
        }
        XCTAssertNotEqual(session.draftRevision, submittedRevision)
        await gate.release()
        let canQuit = await quitting.value
        XCTAssertTrue(canQuit)
        XCTAssertEqual(session.acceptedDocument.id, accepted)
        XCTAssertFalse(workspace.isBusy)
    }

    @MainActor
    func testManualPairWorkspaceRetainedBaselineAndCurrentCarryStoredURLs() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let library = ReportLibrary(root: fixture.directory.appendingPathComponent("owned-library"))
        let baselineID = try await library.keep(fixture.before, provenance: LibraryProvenance(sourceLabel: "Owned baseline"))
        let currentID = try await library.keep(fixture.after, provenance: LibraryProvenance(sourceLabel: "Owned current"))
        let baseline = try await library.load(baselineID), current = try await library.load(currentID)
        let workspace = AuditWorkspace(library: library, recents: ManualPairRecents(), compareSavedReports: {
            try ManualWorkspaceFixture.output(before: $0, after: $1, selection: $2)
        }, supportRoot: fixture.directory, preferences: fixture.preferences)
        workspace.openRetainedReport(currentID)
        try await settle(workspace)
        workspace.compareRetainedReport(baselineID)
        try await settle(workspace)
        let document = try XCTUnwrap(workspace.comparisonDocument)
        XCTAssertEqual(document.sources?.baseline.url, baseline.reportURL)
        XCTAssertEqual(document.sources?.current.url, current.reportURL)
        XCTAssertEqual(Set(document.protectedInputs), Set([try XCTUnwrap(baseline.reportURL), try XCTUnwrap(current.reportURL)]))
    }

    @MainActor
    func testManualPairExportRefusesBothSourcesAndSymlinkAndHardLinkAtWriteBoundary() async throws {
        let fixture = try ManualWorkspaceFixture(); defer { fixture.remove() }
        let workspace = fixture.workspace(), session = try await stage(fixture, workspace: workspace)
        let symlink = fixture.directory.appendingPathComponent("baseline-alias.json")
        let hardlink = fixture.directory.appendingPathComponent("current-alias.json")
        try FileManager.default.createSymbolicLink(at: symlink, withDestinationURL: fixture.baselineURL)
        try FileManager.default.linkItem(at: fixture.currentURL, to: hardlink)
        let data = session.acceptedDocument.data, sources = session.acceptedDocument.protectedInputs
        for destination in [fixture.baselineURL, fixture.currentURL, symlink, hardlink] {
            // Deliberately bypass save-panel validation to exercise the actual worker write.
            workspace.showingError = false
            workspace.exportJSON(data, to: destination, protectedInputs: sources)
            try await settle(workspace)
            XCTAssertTrue(workspace.showingError)
            XCTAssertEqual(try Data(contentsOf: fixture.baselineURL), fixture.before)
            XCTAssertEqual(try Data(contentsOf: fixture.currentURL), fixture.after)
        }
        let output = fixture.directory.appendingPathComponent("comparison.json")
        workspace.showingError = false
        workspace.exportJSON(data, to: output, protectedInputs: sources)
        try await settle(workspace)
        XCTAssertFalse(workspace.showingError, workspace.errorMessage)
        XCTAssertEqual(try Data(contentsOf: output), data)
    }

    func testManualPairPagesKeepAllFiftyThousandRowsReachableAndClampAfterRemoval() {
        let first = ComparisonChangePage(count: 50_000, index: 0)
        let pages = (0..<first.pageCount).map { ComparisonChangePage(count: 50_000, index: $0) }
        XCTAssertTrue(pages.allSatisfy { $0.range.count <= 50 })
        XCTAssertEqual(pages.flatMap { Array($0.range) }, Array(0..<50_000))
        XCTAssertEqual(ComparisonChangePage(count: 1, index: 999).range, 0..<1)
        XCTAssertTrue(ComparisonChangePage(count: 0, index: 999).range.isEmpty)
    }
}
