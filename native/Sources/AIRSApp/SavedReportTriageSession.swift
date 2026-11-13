import Foundation
import Combine
import AIRSCore
import AIRSEntitlements

struct SavedTriageSource: Sendable, Identifiable {
    let id = UUID()
    let data: Data
    let url: URL?
    let name: String
    let findingCount: Int

    static func admit(_ data: Data, url: URL?) throws -> Self {
        try SavedReportInputBudget.validate([data])
        let report = try AuditReport.decode(data)
        return Self(data: data, url: url, name: report.image.displayName, findingCount: report.findings.count)
    }
    static func adding(_ urls: [URL], to sources: [Self]) throws -> [Self] {
        try SavedReportInputBudget.validateCounts(reportCount: sources.count + urls.count, byteCount: 0, findingCount: 0)
        // Stat every selected file before reading any of them; duplicates count separately.
        var total = sources.reduce(0) { $0 + $1.data.count }
        for url in urls {
            let access = url.startAccessingSecurityScopedResource()
            defer { if access { url.stopAccessingSecurityScopedResource() } }
            let values = try url.resourceValues(forKeys: [.fileSizeKey, .isRegularFileKey])
            guard values.isRegularFile == true, let size = values.fileSize, size <= 64 * 1_048_576 else {
                throw ReportError.invalidContents("Choose regular saved report files of at most 64 MiB each.")
            }
            total += size
            try SavedReportInputBudget.validateCounts(reportCount: sources.count + urls.count, byteCount: total, findingCount: 0)
        }
        var result = sources
        for url in urls {
            try Task.checkCancellation()
            let access = url.startAccessingSecurityScopedResource()
            defer { if access { url.stopAccessingSecurityScopedResource() } }
            result.append(try admit(ReportFiles.readBounded(url), url: url))
            try validate(result)
        }
        return result
    }
    static func validate(_ sources: [Self]) throws {
        try SavedReportInputBudget.validateCounts(reportCount: sources.count,
            byteCount: sources.reduce(0) { $0 + $1.data.count }, findingCount: sources.reduce(0) { $0 + $1.findingCount })
    }
}

struct TriageSubmission: Sendable {
    let sessionID: UUID
    let revision: UUID
    let auditRevision: UUID
    let entitlementRevision: UUID
}

struct TriageFindings: Sendable, Identifiable {
    let id = UUID()
    let summary: SavedReportSummary
    let data: Data
    let source: SavedTriageSource
    let report: AuditReport
    let reportIndex: Int
}

@MainActor
final class SavedReportTriageSession: ObservableObject, Identifiable {
    enum Page { case inventory, findings, source }
    let id = UUID()
    let auditRevision: UUID
    let entitlementRevision: UUID
    let importedURL: URL?
    @Published private(set) var sources: [SavedTriageSource]
    @Published private(set) var inventory: CoverageInventory?
    @Published private(set) var inventoryData: Data?
    private(set) var inventorySources: [SavedTriageSource] = []
    private(set) var resolvedSources: [Int: SavedTriageSource] = [:]
    private(set) var observedSourceURLs: [URL] = []
    @Published private(set) var findings: TriageFindings?
    @Published private(set) var sourceReport: AuditReport?
    private(set) var sourceURL: URL?
    @Published private(set) var sourceFinding: Finding?
    @Published private(set) var page: Page = .inventory
    @Published var reasonText = "" { didSet { invalidate() } }
    @Published var minimumText = "1" { didSet { invalidate() } }
    @Published var coverageOrder: CoverageOptions.Order = .count { didSet { invalidate() } }
    @Published var coverageLimitText = "" { didSet { invalidate() } }
    @Published var nameText = "" { didSet { invalidate() } }
    @Published var summaryVerdict: AuditVerdict? = .unresolved { didSet { invalidate() } }
    @Published var summaryOrder: SummaryOptions.Order = .source { didSet { invalidate() } }
    @Published var summaryLimitText = "" { didSet { invalidate() } }
    @Published private(set) var selectedReason: String?
    @Published private(set) var selectedReport = 0
    @Published var message: String?
    private(set) var revision = UUID()
    private(set) var closed = false

    init(sources: [SavedTriageSource], auditRevision: UUID, entitlementRevision: UUID,
         inventory: CoverageInventory? = nil, importedURL: URL? = nil) {
        self.sources = sources; self.auditRevision = auditRevision; self.entitlementRevision = entitlementRevision
        self.inventory = inventory; self.importedURL = importedURL
    }
    var protectedURLs: [URL] { observedSourceURLs + sources.compactMap(\.url) + inventorySources.compactMap(\.url) + [findings?.source.url, sourceURL, importedURL].compactMap { $0 } }
    func invalidate() { revision = UUID() }
    func close() { closed = true; invalidate() }
    /// A cancelled quit keeps the sheet on screen, so the session it shows must accept work again.
    func reopen() { closed = false; invalidate() }
    func replaceSources(_ sources: [SavedTriageSource]) { guard !closed else { return }; self.sources = sources; invalidate() }
    func removeSource(_ id: UUID) { replaceSources(sources.filter { $0.id != id }) }
    func submission() throws -> TriageSubmission {
        guard !closed else { throw CancellationError() }
        return TriageSubmission(sessionID: id, revision: revision, auditRevision: auditRevision, entitlementRevision: entitlementRevision)
    }
    func isCurrent(_ token: TriageSubmission, audit: UUID, entitlements: UUID) -> Bool {
        !closed && token.sessionID == id && token.revision == revision && audit == auditRevision &&
        entitlements == entitlementRevision && token.auditRevision == audit && token.entitlementRevision == entitlements
    }
    @discardableResult
    func acceptInventory(_ value: CoverageInventory, data: Data, sources: [SavedTriageSource], token: TriageSubmission, audit: UUID, entitlements: UUID) -> Bool {
        guard isCurrent(token, audit: audit, entitlements: entitlements) else { return false }
        observedSourceURLs += sources.compactMap(\.url)
        resolvedSources = [:]
        inventory = value; inventoryData = data; inventorySources = sources; findings = nil; sourceReport = nil; sourceFinding = nil; page = .inventory; message = nil
        return true
    }
    func select(reason: String?, report: Int) { selectedReason = reason; selectedReport = report; invalidate() }
    func acceptFindings(_ value: TriageFindings, token: TriageSubmission, audit: UUID, entitlements: UUID) -> Bool {
        guard isCurrent(token, audit: audit, entitlements: entitlements) else { return false }
        if let url = value.source.url { observedSourceURLs.append(url) }
        if importedURL != nil { resolvedSources[value.reportIndex] = value.source }
        findings = value; sourceReport = nil; sourceFinding = nil; page = .findings; message = nil; return true
    }
    func openFinding(_ id: String) {
        guard !closed, let findings, findings.summary.findings.contains(where: { $0.id == id }),
              let original = findings.report.findings.first(where: { $0.id == id }) else { return }
        sourceFinding = original; sourceReport = findings.report; sourceURL = findings.source.url; page = .source; invalidate()
    }
    func openReferenced(report: AuditReport, finding: Finding, url: URL) {
        guard !closed else { return }
        observedSourceURLs.append(url)
        findings = nil; sourceReport = report; sourceFinding = finding; sourceURL = url; page = .source; invalidate()
    }
    func backToInventory() { page = .inventory; sourceFinding = nil; invalidate() }
    func backToFindings() { page = .findings; sourceFinding = nil; invalidate() }
    func coverageOptions() throws -> CoverageOptions {
        let reasons = reasonText.isEmpty ? nil : reasonText.split(separator: ",", omittingEmptySubsequences: false).map { $0.trimmingCharacters(in: .whitespaces) }
        return try CoverageOptions(reasons: reasons, minimumCount: Self.number(minimumText, label: "Minimum reason count"),
            order: coverageOrder, limit: Self.number(coverageLimitText, label: "Reason detail limit"))
    }
    func summaryOptions() throws -> SummaryOptions {
        try SummaryOptions(verdicts: summaryVerdict.map { [$0] }, reasons: selectedReason.map { [$0] },
            nameContains: nameText.isEmpty ? nil : nameText, order: summaryOrder,
            limit: Self.number(summaryLimitText, label: "Finding detail limit"))
    }
    private static func number(_ text: String, label: String) throws -> Int? {
        if text.isEmpty { return nil }
        guard let value = Int(text) else { throw ReportError.invalidContents(label + " must be an integer that fits this Mac's integer range; clear it to omit the option.") }
        return value
    }
}
