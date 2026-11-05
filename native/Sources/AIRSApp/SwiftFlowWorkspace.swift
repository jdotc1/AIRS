import AppKit
import Observation
import AIRSCore

/// A window-owned job. Imported or superseded reports remain historical evidence.
@Observable @MainActor
final class SwiftFlowWorkspace {
    private(set) var input: URL?
    var includeMethods = false { didSet { if oldValue != includeMethods { invalidate() } } }
    var includeWitnesses = false { didSet { if oldValue != includeWitnesses { invalidate() } } }
    private(set) var report: SwiftFlowReport?
    private(set) var isBusy = false
    private(set) var isHistorical = true
    private(set) var status = "Choose a binary or app, or open a saved Swift report."
    var errorMessage: String?
    var selection: String?
    private let runner = EngineRunner()
    private var task: Task<Void, Never>?
    private var revision = UUID()
    private var protectedInputs: [URL] = []
    private var quitting = false
    private let execute: (@Sendable (URL, SwiftFlowOptions, EngineConfiguration) async throws -> Data)?

    init(execute: (@Sendable (URL, SwiftFlowOptions, EngineConfiguration) async throws -> Data)? = nil) { self.execute = execute }
    var selectedCall: SwiftFlowCall? { report?.calls.first { $0.id == selection } }
    private func invalidate() { revision = UUID(); isHistorical = true; if report != nil { status = "Settings changed. Previous report is historical; run a new analysis." } }
    func selectInput(_ url: URL) { guard !isBusy, !quitting else { return }; input = url; invalidate(); status = "Selected \(url.lastPathComponent). Ready to analyze." }
    func chooseInput() {
        guard !isBusy, !quitting else { return }
        let panel = NSOpenPanel(); panel.title = "Swift Error Flow Input"; panel.canChooseDirectories = true
        panel.canChooseFiles = true; panel.allowsMultipleSelection = false; panel.treatsFilePackagesAsDirectories = false
        if panel.runModal() == .OK, let url = panel.url { selectInput(url) }
    }
    func run(configuration: EngineConfiguration) {
        guard let input, !isBusy, !quitting else { return }
        let id = UUID(); revision = id; isBusy = true; isHistorical = true; errorMessage = nil
        let options = SwiftFlowOptions(includeMethods: includeMethods, includeWitnesses: includeWitnesses)
        status = "Analyzing bounded Swift call evidence…"
        task = Task { [self] in
            defer { isBusy = false; task = nil }
            do {
                let data: Data
                if let execute { data = try await execute(input, options, configuration) }
                else { data = try await runner.run(.swiftErrorFlow(input: input, options: options), configuration: configuration).data }
                try Task.checkCancellation()
                let decoded = try await Task.detached { try SwiftFlowReport.decode(data) }.value
                try Task.checkCancellation()
                guard revision == id, !quitting else { status = "Result superseded; previous report remains historical."; return }
                report = decoded; selection = decoded.calls.first?.id; protectedInputs = [input]; isHistorical = false
                status = decoded.wordScanComplete && decoded.callDetailsComplete && decoded.witnessesComplete ? "Analysis complete within the recorded scope." : "Partial analysis: inspect omitted details and limits."
            } catch is CancellationError { status = "Analysis cancelled. Previous report remains historical." }
            catch { status = "Analysis unavailable. Previous report remains historical."; errorMessage = error.localizedDescription }
        }
    }
    func cancel() { guard isBusy else { return }; revision = UUID(); status = "Cancelling owned engine job…"; task?.cancel() }
    func finishBeforeQuit() async -> Bool { quitting = true; cancel(); await task?.value; return true }
    func resumeAfterCancelledQuit() { quitting = false }
    func openSaved() {
        guard !isBusy, !quitting else { return }
        let panel = NSOpenPanel(); panel.title = "Open Saved Swift Error Flow"; panel.allowsMultipleSelection = false
        if panel.runModal() == .OK, let url = panel.url { importReport(url) }
    }
    func importReport(_ url: URL) {
        guard !isBusy, !quitting else { return }
        let id = UUID(); revision = id; isBusy = true; errorMessage = nil
        isHistorical = true; status = "Opening historical Swift evidence…"
        task = Task { [self] in
            defer { isBusy = false; task = nil }
            do {
                let value = try await Task.detached {
                    try Task.checkCancellation()
                    return try SwiftFlowReport.decode(ReportFiles.readBounded(url))
                }.value
                try Task.checkCancellation()
                guard revision == id, !quitting else { return }
                report = value; selection = value.calls.first?.id; protectedInputs = [url]
                status = "Historical saved report. Recorded validation is not a fresh byte check."
            } catch is CancellationError { status = "Opening cancelled." }
            catch { errorMessage = error.localizedDescription; status = "Saved Swift report unavailable." }
        }
    }
    func waitUntilSettled() async { await task?.value }
    func chooseExport() {
        guard report != nil, !isBusy, !quitting else { return }
        let panel = NSSavePanel(); panel.nameFieldStringValue = "swift-error-flow.json"
        if panel.runModal() == .OK, let url = panel.url {
            do {
                try validateExport(to: url)
                guard let data = report?.sourceData else { return }
                isBusy = true; status = "Exporting recorded Swift evidence…"
                task = Task { [self] in
                    defer { isBusy = false; task = nil }
                    do {
                        try await Task.detached { try data.write(to: url, options: .atomic) }.value
                        status = "Exported recorded Swift evidence."
                    } catch { errorMessage = error.localizedDescription; status = "Export failed." }
                }
            } catch { errorMessage = error.localizedDescription }
        }
    }
    private func validateExport(to url: URL) throws {
        let dest = url.resolvingSymlinksInPath().standardizedFileURL
        // Protect the current selection as well as the retained report sources.
        // Selecting a new input or importing a historical report does not grant overwrite authority.
        for source in protectedInputs + [input].compactMap({ $0 }) {
            let src = source.resolvingSymlinksInPath().standardizedFileURL
            let sourceAttributes = try? FileManager.default.attributesOfItem(atPath: src.path)
            let destAttributes = try? FileManager.default.attributesOfItem(atPath: dest.path)
            let sameInode = sourceAttributes?[.systemFileNumber] as? NSNumber == destAttributes?[.systemFileNumber] as? NSNumber && sourceAttributes?[.systemNumber] as? NSNumber == destAttributes?[.systemNumber] as? NSNumber && sourceAttributes != nil && destAttributes != nil
            if dest == src || dest.path.hasPrefix(src.path + "/") || sameInode {
                throw EngineError.configuration("Export cannot replace an input or write inside the selected app.")
            }
        }
    }
    func export(to url: URL) throws {
        guard let report, !isBusy, !quitting else { return }
        try validateExport(to: url)
        try report.sourceData.write(to: url, options: .atomic)
    }
}
