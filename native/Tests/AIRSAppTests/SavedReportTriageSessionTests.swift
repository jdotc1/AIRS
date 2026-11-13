import Foundation
import XCTest
import AIRSCore
import AIRSEntitlements
@testable import AIRSApp

private actor TriageResultGate {
    private var released = false
    private var continuation: CheckedContinuation<Void, Never>?
    private(set) var entered = false
    private var entryWaiter: CheckedContinuation<Void, Never>?
    func waitUntilEntered() async {
        if entered { return }
        await withCheckedContinuation { entryWaiter = $0 }
    }
    func wait() async {
        entered = true
        entryWaiter?.resume(); entryWaiter = nil
        if released { return }
        await withCheckedContinuation { continuation = $0 }
    }
    func release() { released = true; continuation?.resume(); continuation = nil }
}

private enum TriageTestFixture {
    static var root: URL { URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().appendingPathComponent("fixtures/coverage") }
    static func source() throws -> Data { try Data(contentsOf: root.appendingPathComponent("source.audit.json")) }
    static func inventory() throws -> Data {
        var value = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("single.json"))) as? [String: Any])
        value["reason_frequency_selection"] = ["minimum_count": 1, "input_count": 4, "selected_count": 4, "omitted_count": 0]
        return try JSONSerialization.data(withJSONObject: value)
    }
    static func nonExample() throws -> (source: Data, inventory: Data, summary: Data) {
        var source = try XCTUnwrap(JSONSerialization.jsonObject(with: self.source()) as? [String: Any])
        let all = try XCTUnwrap(source["findings"] as? [[String: Any]])
        let original = try XCTUnwrap(all.first { $0["verdict"] as? String == "unresolved" })
        let rows = (0..<12).map { index -> [String: Any] in
            var row = original; row["id"] = "airsf-" + String(format: "%064x", index + 1); return row
        }
        var totals = try XCTUnwrap(source["summary"] as? [String: Any])
        totals["function_count"] = 12; totals["agreement_count"] = 0; totals["inconsistency_count"] = 0; totals["unresolved_count"] = 12; totals["checked_pc_count"] = 0
        source["summary"] = totals; source["findings"] = rows
        let reason = try XCTUnwrap((original["reason_codes"] as? [String])?.first)
        let function = try XCTUnwrap(original["function"] as? [String: Any])
        var inventory = try XCTUnwrap(JSONSerialization.jsonObject(with: Data(contentsOf: root.appendingPathComponent("single.json"))) as? [String: Any])
        var records = try XCTUnwrap(inventory["reports"] as? [[String: Any]]); records[0]["summary"] = totals; inventory["reports"] = records
        var summary = try XCTUnwrap(inventory["summary"] as? [String: Any]); summary["function_count"] = 12; summary["agreement_count"] = 0; summary["inconsistency_count"] = 0; summary["unresolved_count"] = 12; inventory["summary"] = summary
        let examples: [[String: Any]] = try rows.prefix(8).map { row in
            ["report_index": 0, "finding_id": try XCTUnwrap(row["id"]), "function_name": try XCTUnwrap(function["name"]),
             "pc": try XCTUnwrap(function["address"]), "scope": try XCTUnwrap(row["scope"]), "mode": try XCTUnwrap(row["mode"])]
        }
        inventory["reasons"] = [["reason": reason, "count": 12, "examples": examples]]
        inventory["reason_frequency_selection"] = ["minimum_count": 1, "input_count": 1, "selected_count": 1, "omitted_count": 0]
        let ranges = try XCTUnwrap(source["metadata_ranges"] as? [[String: Any]])
        let rangeCounts = ranges.reduce(into: [String: Int]()) { counts, row in counts[row["mode"] as? String ?? "", default: 0] += 1 }
        let issues = try XCTUnwrap(source["issues"] as? [[String: Any]])
        let output: [String: Any] = ["schema_version": 1, "report_kind": "airs.report_summary",
            "source_report": source.filter { ["schema_version", "report_kind", "generator", "image", "analysis_config"].contains($0.key) },
            "summary": totals,
            "finding_counts": ["by_verdict": ["agreement": 0, "inconsistency": 0, "unresolved": 12],
                "by_coverage": [try XCTUnwrap(original["coverage"] as? String): 12], "by_mode": [try XCTUnwrap(original["mode"] as? String): 12], "by_scope": [try XCTUnwrap(original["scope"] as? String): 12]],
            "reason_counts_by_verdict": ["agreement": [:], "inconsistency": [:], "unresolved": [reason: 12]],
            "findings": rows.map { $0.filter { $0.key != "evidence" } },
            "metadata": ["entry_count": ranges.count, "entry_counts_by_mode": rangeCounts, "issue_count": issues.count, "issues": issues],
            "source_limitations": try XCTUnwrap(source["limitations"]), "limitations": ["Owned saved projection."],
            "finding_selection": ["requested": ["unresolved"], "requested_reasons": [reason], "selected_count": 12, "omitted_count": 0, "original_count": 12]]
        return (try JSONSerialization.data(withJSONObject: source), try JSONSerialization.data(withJSONObject: inventory), try JSONSerialization.data(withJSONObject: output))
    }
}

@MainActor
final class SavedReportTriageSessionTests: XCTestCase {
    private func setup(output: Data, gate: TriageResultGate? = nil) async throws -> (AIRSFileOpen, AuditWorkspace, EntitlementsWorkspace) {
        let audit = AuditWorkspace(), entitlements = EntitlementsWorkspace(), data = try TriageTestFixture.source()
        audit.openValidatedReport(try AuditReport.decode(data), data: data, from: TriageTestFixture.root.appendingPathComponent("source.audit.json"))
        let owner = AIRSFileOpen(triageOperation: { _ in if let gate { await gate.wait() }; return output }, hasModal: { false })
        await owner.beginSavedReportTriage(audit: audit, entitlements: entitlements)?.value
        return (owner, audit, entitlements)
    }
    private func waitForEntry(_ gate: TriageResultGate) async {
        await gate.waitUntilEntered()
    }
    func testTriageInitialInputAndAddedDuplicateOrderRemainExplicit() async throws {
        let (owner, audit, entitlements) = try await setup(output: TriageTestFixture.inventory())
        let session = try XCTUnwrap(owner.savedReportTriage)
        XCTAssertEqual(session.sources.count, 1)
        let a = TriageTestFixture.root.appendingPathComponent("unicode-source.audit.json"), b = TriageTestFixture.root.appendingPathComponent("source.audit.json")
        await owner.addTriageReports([a, b, a], audit: audit, entitlements: entitlements)?.value
        XCTAssertEqual(session.sources.compactMap(\.url), [b, a, b, a])
        XCTAssertEqual(Set(session.sources.map(\.id)).count, 4)
        XCTAssertEqual(session.sources[1].data, session.sources[3].data)
    }
    func testTriageEditAndRevisionMismatchDropLateResult() async throws {
        let gate = TriageResultGate(), output = try TriageTestFixture.inventory()
        let (owner, audit, entitlements) = try await setup(output: output, gate: gate)
        let session = try XCTUnwrap(owner.savedReportTriage)
        let job = owner.runTriageCoverage(audit: audit, entitlements: entitlements)
        await waitForEntry(gate)
        session.minimumText = "2"
        await gate.release(); await job?.value
        XCTAssertNil(session.inventory); XCTAssertEqual(session.minimumText, "2")
        let token = try session.submission()
        XCTAssertFalse(session.isCurrent(token, audit: UUID(), entitlements: entitlements.model.reportRevision))
        XCTAssertFalse(session.isCurrent(token, audit: audit.reportRevision, entitlements: UUID()))
    }
    func testTriageCancellationPreservesDraftAndLastAcceptedInventory() async throws {
        // The late reply differs byte-wise from the accepted inventory but would also be admissible,
        // so accepting it after cancellation changes inventoryData.
        let output = try TriageTestFixture.inventory(), late = output + Data(" \n".utf8), gate = TriageResultGate()
        let (owner, audit, entitlements) = try await setup(output: late, gate: gate)
        let session = try XCTUnwrap(owner.savedReportTriage), token = try session.submission()
        XCTAssertTrue(session.acceptInventory(try CoverageInventory.decode(output), data: output, sources: session.sources, token: token, audit: audit.reportRevision, entitlements: entitlements.model.reportRevision))
        let job = owner.runTriageCoverage(audit: audit, entitlements: entitlements)
        await waitForEntry(gate); owner.cancel(); await gate.release(); await job?.value
        XCTAssertEqual(session.inventoryData, output); XCTAssertNotEqual(session.inventoryData, late)
        XCTAssertEqual(session.minimumText, "1"); XCTAssertFalse(owner.isBusy)
        XCTAssertNil(session.message); XCTAssertTrue(owner.status.hasPrefix("Cancelled"))
    }
    func testTriageCloseAndSourceReplacementDropLateResults() async throws {
        for close in [false, true] {
            let output = try TriageTestFixture.inventory(), gate = TriageResultGate()
            let (owner, audit, entitlements) = try await setup(output: output, gate: gate)
            let session = try XCTUnwrap(owner.savedReportTriage), job = owner.runTriageCoverage(audit: audit, entitlements: entitlements)
            await waitForEntry(gate)
            if close { owner.closeCoverage() }
            else {
                let data = try TriageTestFixture.source()
                audit.openValidatedReport(try AuditReport.decode(data), data: data, from: TriageTestFixture.root.appendingPathComponent("source.audit.json"))
            }
            await gate.release(); await job?.value
            XCTAssertNil(session.inventory)
            if close { XCTAssertNil(owner.savedReportTriage); XCTAssertTrue(session.closed) }
        }
    }
    func testTriageQuitCancelsAndWaitsBeforeDroppingSession() async throws {
        let output = try TriageTestFixture.inventory(), gate = TriageResultGate()
        let (owner, audit, entitlements) = try await setup(output: output, gate: gate)
        let session = try XCTUnwrap(owner.savedReportTriage), job = owner.runTriageCoverage(audit: audit, entitlements: entitlements)
        await waitForEntry(gate)
        let quit = Task { await owner.finishBeforeQuit() }
        while !owner.isTerminating { await Task.yield() }
        await gate.release(); await job?.value
        let finished = await quit.value
        XCTAssertTrue(finished); XCTAssertTrue(session.closed); XCTAssertNil(owner.savedReportTriage); XCTAssertNil(session.inventory)
    }
    func testCancelledQuitReopensTheVisibleSession() async throws {
        let (owner, _, _) = try await setup(output: TriageTestFixture.inventory())
        let session = try XCTUnwrap(owner.savedReportTriage)
        session.close(); XCTAssertThrowsError(try session.submission())
        owner.resumeAfterCancelledQuit()
        XCTAssertFalse(session.closed); XCTAssertNoThrow(try session.submission()); XCTAssertNotNil(owner.savedReportTriage)
    }
    func testSheetDisappearanceCancelsInFlightRunAndClearsSession() async throws {
        let output = try TriageTestFixture.inventory(), gate = TriageResultGate()
        let (owner, audit, entitlements) = try await setup(output: output, gate: gate)
        let session = try XCTUnwrap(owner.savedReportTriage), job = owner.runTriageCoverage(audit: audit, entitlements: entitlements)
        await waitForEntry(gate)
        owner.triageSheetDisappeared(session)
        XCTAssertNil(owner.savedReportTriage); XCTAssertTrue(session.closed)
        await gate.release(); await job?.value
        XCTAssertNil(session.inventory); XCTAssertFalse(owner.isBusy); XCTAssertFalse(owner.blocksActions)
    }
    func testTriageFailedRerunPreservesResultAndNamesTheInvalidDraftLimit() async throws {
        let output = try TriageTestFixture.inventory()
        let (owner, audit, entitlements) = try await setup(output: output)
        await owner.runTriageCoverage(audit: audit, entitlements: entitlements)?.value
        let session = try XCTUnwrap(owner.savedReportTriage)
        XCTAssertNotNil(session.inventory)
        session.coverageLimitText = "200001"
        XCTAssertNil(owner.runTriageCoverage(audit: audit, entitlements: entitlements))
        XCTAssertEqual(session.inventoryData, output)
        XCTAssertTrue(session.message?.contains("200,000") == true)
        session.coverageLimitText = String(repeating: "9", count: 50)
        XCTAssertThrowsError(try session.coverageOptions()) { XCTAssertTrue($0.localizedDescription.contains("integer range")) }
    }
    func testTriageFindingsBeyondEightExamplesOpenOriginalAndReturnToInventory() async throws {
        let fixture = try TriageTestFixture.nonExample(), audit = AuditWorkspace(), entitlements = EntitlementsWorkspace()
        audit.openValidatedReport(try AuditReport.decode(fixture.source), data: fixture.source, from: TriageTestFixture.root.appendingPathComponent("owned-source.json"))
        let owner = AIRSFileOpen(triageOperation: { command in
            if case .coverage = command { return fixture.inventory }
            return fixture.summary
        }, hasModal: { false })
        await owner.beginSavedReportTriage(audit: audit, entitlements: entitlements)?.value
        await owner.runTriageCoverage(audit: audit, entitlements: entitlements)?.value
        let session = try XCTUnwrap(owner.savedReportTriage), inventory = try XCTUnwrap(session.inventory)
        let reason = try XCTUnwrap(inventory.reasons.first), revision = audit.reportRevision
        session.select(reason: reason.reason, report: 0)
        await owner.runTriageSummary(source: session.sources[0], audit: audit, entitlements: entitlements)?.value
        let findings = try XCTUnwrap(session.findings), last = try XCTUnwrap(findings.summary.findings.last)
        XCTAssertFalse(reason.examples.contains { $0.finding_id == last.id })
        session.openFinding(last.id)
        XCTAssertEqual(session.page, .source); XCTAssertEqual(session.sourceFinding?.id, last.id)
        XCTAssertFalse(session.sourceFinding?.evidence.isEmpty ?? true)
        session.backToFindings(); XCTAssertEqual(session.page, .findings)
        session.backToInventory(); XCTAssertEqual(session.page, .inventory)
        XCTAssertEqual(session.inventoryData, fixture.inventory); XCTAssertEqual(audit.reportRevision, revision)
    }
    func testTriageInputBudgetAndPagesStateTheirNativeLimits() throws {
        let source = try SavedTriageSource.admit(TriageTestFixture.source(), url: nil)
        XCTAssertThrowsError(try SavedTriageSource.validate(Array(repeating: source, count: 129))) { XCTAssertTrue($0.localizedDescription.contains("128")) }
        let session = SavedReportTriageSession(sources: [source], auditRevision: UUID(), entitlementRevision: UUID())
        XCTAssertEqual(try session.coverageOptions().minimumCount, 1)
        XCTAssertNil(try session.coverageOptions().limit)
        XCTAssertEqual(TriagePageControls.lastPage(count: 50_000, size: 50), 999)
        XCTAssertEqual(TriagePageControls.lastPage(count: 0, size: 50), 0)
        XCTAssertEqual(TriagePageControls.lastPage(count: 51, size: 50), 1)
    }
    func testTriageExportProtectsEveryInputAndOriginalInventoryAlias() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("triage-export-\(UUID())")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let a = directory.appendingPathComponent("source.json"), inventory = directory.appendingPathComponent("coverage.json"), alias = directory.appendingPathComponent("alias.json")
        let bytes = try TriageTestFixture.source(); try bytes.write(to: a); try Data().write(to: inventory)
        try FileManager.default.createSymbolicLink(at: alias, withDestinationURL: a)
        let session = SavedReportTriageSession(sources: [try SavedTriageSource.admit(bytes, url: a)], auditRevision: UUID(), entitlementRevision: UUID(), importedURL: inventory)
        for url in [a, inventory, alias] { XCTAssertThrowsError(try ComparisonExportProtection.write(Data(), to: url, sources: session.protectedURLs)) }
        XCTAssertNoThrow(try ComparisonExportProtection.write(Data(), to: directory.appendingPathComponent("new-result.json"), sources: session.protectedURLs))
    }
}

private actor TriageReplyQueue {
    var replies: [Data]
    init(_ replies: [Data]) { self.replies = replies }
    func next() -> Data { replies.isEmpty ? Data() : replies.removeFirst() }
}

extension SavedReportTriageSessionTests {
    func testTriageMalformedRerunRetainsAcceptedResultAndEditableDraft() async throws {
        let output = try TriageTestFixture.inventory(), queue = TriageReplyQueue([output, Data("{}".utf8)])
        let source = try TriageTestFixture.source(), audit = AuditWorkspace(), entitlements = EntitlementsWorkspace()
        audit.openValidatedReport(try AuditReport.decode(source), data: source, from: TriageTestFixture.root.appendingPathComponent("source.audit.json"))
        let owner = AIRSFileOpen(triageOperation: { _ in await queue.next() }, hasModal: { false })
        await owner.beginSavedReportTriage(audit: audit, entitlements: entitlements)?.value
        await owner.runTriageCoverage(audit: audit, entitlements: entitlements)?.value
        let session = try XCTUnwrap(owner.savedReportTriage)
        XCTAssertEqual(session.inventoryData, output)
        await owner.runTriageCoverage(audit: audit, entitlements: entitlements)?.value
        XCTAssertEqual(session.inventoryData, output); XCTAssertNotNil(session.message)
        session.minimumText = "2"; XCTAssertEqual(try session.coverageOptions().minimumCount, 2)
    }
    func testTriageSummaryEditsAndInputReplacementInvalidateCapturedSubmissions() throws {
        let source = try SavedTriageSource.admit(TriageTestFixture.source(), url: nil), a = UUID(), e = UUID()
        let session = SavedReportTriageSession(sources: [source], auditRevision: a, entitlementRevision: e)
        let original = try session.submission()
        session.nameText = "literal"
        XCTAssertFalse(session.isCurrent(original, audit: a, entitlements: e))
        let next = try session.submission()
        session.replaceSources([source, source])
        XCTAssertFalse(session.isCurrent(next, audit: a, entitlements: e))
        let final = try session.submission(); session.close()
        XCTAssertFalse(session.isCurrent(final, audit: a, entitlements: e))
    }
}

extension SavedReportTriageSessionTests {
    func testTriageFileSizePreflightRefusesAggregateBeforeReadingMalformedFiles() throws {
        let directory = FileManager.default.temporaryDirectory.appendingPathComponent("triage-size-\(UUID())")
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: directory) }
        let url = directory.appendingPathComponent("sparse.json")
        XCTAssertTrue(FileManager.default.createFile(atPath: url.path, contents: Data()))
        let handle = try FileHandle(forWritingTo: url)
        try handle.truncate(atOffset: UInt64(64 * 1_048_576)); try handle.close()
        // One sparse file selected three times exceeds the aggregate budget before JSON admission.
        XCTAssertThrowsError(try SavedTriageSource.adding([url, url, url], to: [])) { XCTAssertTrue($0.localizedDescription.contains("128 MiB")) }
        let large = try FileHandle(forWritingTo: url)
        try large.truncate(atOffset: UInt64(64 * 1_048_576 + 1)); try large.close()
        XCTAssertThrowsError(try SavedTriageSource.adding([url], to: [])) { XCTAssertTrue($0.localizedDescription.contains("64 MiB")) }
    }
}
