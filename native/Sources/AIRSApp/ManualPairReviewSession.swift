import Combine
import Foundation
import AIRSCore

struct SavedComparisonSource: Sendable {
    let report: AuditReport
    let data: Data
    let url: URL?
}

struct SavedComparisonSources: Sendable {
    let baseline: SavedComparisonSource
    let current: SavedComparisonSource
    let workspaceRevision: UUID

    var urls: [URL] { [baseline.url, current.url].compactMap { $0 } }
}

struct ManualPairSubmission: Sendable {
    let sessionID: UUID
    let draftRevision: UUID
    let sources: SavedComparisonSources
    let selection: ManualPairSelection
}

/// Drafts and accepted results are session-only. Immutable source snapshots are
/// shared with the worker; editing never changes either saved source.
@MainActor
final class ManualPairReviewSession: ObservableObject, Identifiable {
    let id = UUID()
    let sources: SavedComparisonSources
    @Published private(set) var pairs: [ComparisonManualPair] = []
    @Published private(set) var acceptedDocument: ComparisonDocument
    @Published var isEditing = false
    @Published private(set) var message: String?
    private(set) var draftRevision = UUID()
    private(set) var isClosed = false

    init(sources: SavedComparisonSources, document: ComparisonDocument) {
        self.sources = sources
        acceptedDocument = document
        pairs = document.report.comparison.manualPairs ?? []
    }

    func add(baselineID: String, currentID: String) {
        guard !isClosed else { return }
        do {
            let pair = try ComparisonManualPair(baselineID: baselineID, currentID: currentID)
            let selection = try ManualPairSelection(pairs + [pair], baseline: sources.baseline.report, current: sources.current.report)
            guard selection.pairs != pairs else { message = "This review pair is already selected."; return }
            pairs = selection.pairs
            draftRevision = UUID()
            message = nil
        } catch { message = error.localizedDescription }
    }

    func remove(_ pair: ComparisonManualPair) {
        guard !isClosed, pairs.contains(pair) else { return }
        pairs.removeAll { $0 == pair }
        draftRevision = UUID()
        message = nil
    }

    func submission() throws -> ManualPairSubmission {
        guard !isClosed else { throw CancellationError() }
        return ManualPairSubmission(sessionID: id, draftRevision: draftRevision, sources: sources,
            selection: try ManualPairSelection(pairs, baseline: sources.baseline.report, current: sources.current.report))
    }

    @discardableResult
    func accept(_ document: ComparisonDocument, submission: ManualPairSubmission, workspaceRevision: UUID) -> Bool {
        guard !isClosed, id == submission.sessionID, draftRevision == submission.draftRevision,
              sources.workspaceRevision == workspaceRevision,
              submission.sources.workspaceRevision == workspaceRevision else { return false }
        acceptedDocument = document
        isEditing = false
        message = nil
        return true
    }

    func invalidatePendingResult() { draftRevision = UUID() }
    func close() { isClosed = true; invalidatePendingResult() }
}

/// This check runs again on the file worker immediately before the atomic write.
/// It is not a guarantee against another process racing a path replacement.
enum ComparisonExportProtection {
    static func validate(_ destination: URL, sources: [URL]) throws {
        for source in sources {
            if PathContainment.sameLocation(destination, source) {
                throw ReportError.invalidContents("Choose a new JSON destination; an export cannot replace a saved source report.")
            }
            if ["app", "dsym"].contains(source.pathExtension.lowercased()), PathContainment.isInside(destination, source) {
                throw ReportError.invalidContents("Choose a JSON destination outside the inspected images and attached debug artifacts.")
            }
        }
    }

    static func write(_ data: Data, to destination: URL, sources: [URL]) throws {
        try Task.checkCancellation()
        try validate(destination, sources: sources)
        try data.write(to: destination, options: .atomic)
    }
}
