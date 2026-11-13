import SwiftUI
import AIRSCore
import LumenUI

/// Keeps the sheet identity stable while an accepted comparison changes inside it.
@MainActor
struct ComparisonPresentationView: View {
    let initialDocument: ComparisonDocument
    @ObservedObject var workspace: AuditWorkspace

    var body: some View {
        Group {
            if let session = workspace.manualPairSession {
                ManualPairSessionView(session: session, workspace: workspace)
            } else {
                ComparisonView(document: initialDocument, workspace: workspace)
            }
        }
        .onDisappear { workspace.closeComparison(documentID: initialDocument.id) }
    }
}

@MainActor
private struct ManualPairSessionView: View {
    @ObservedObject var session: ManualPairReviewSession
    @ObservedObject var workspace: AuditWorkspace

    var body: some View {
        Group {
            if session.isEditing {
                ManualPairReviewView(session: session, workspace: workspace)
            } else {
                ComparisonView(document: session.acceptedDocument, workspace: workspace,
                               reviewPairs: { session.isEditing = true })
                    .id(session.acceptedDocument.id)
            }
        }
    }
}

@MainActor
struct ManualPairReviewView: View {
    @ObservedObject var session: ManualPairReviewSession
    @ObservedObject var workspace: AuditWorkspace
    @State private var baselineID: String?
    @State private var currentID: String?
    @State private var pairPage = 0

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                AppDialogTitle(title: "Review Pairs")
                Spacer()
                Button("Back to Result") { session.isEditing = false }
                    .disabled(workspace.isBusy)
                Button("Done") { workspace.closeComparison() }
                    .disabled(workspace.isBusy && !workspace.canCancel)
            }
            Text("Choose one finding from each saved report. A user-selected review pair does not prove source-function identity or establish a regression or fix.")
                .font(.callout).foregroundStyle(.secondary)
            HStack(alignment: .top, spacing: 16) {
                ManualPairFindingList(title: "Baseline", source: session.sources.baseline, selectedID: $baselineID)
                ManualPairFindingList(title: "Current", source: session.sources.current, selectedID: $currentID)
            }
            HStack {
                Button("Add Review Pair") {
                    if let baselineID, let currentID { session.add(baselineID: baselineID, currentID: currentID) }
                }
                .disabled(baselineID == nil || currentID == nil)
                Text("\(session.pairs.count) selected pairs").foregroundStyle(.secondary)
                Spacer()
                if workspace.isBusy {
                    ProgressView().controlSize(.small)
                    Button("Cancel Comparison") { workspace.cancel() }.disabled(!workspace.canCancel)
                }
                Button("Compare") { workspace.compareManualPairs() }.disabled(workspace.isBusy)
            }
            if let message = session.message {
                Text(message).font(.callout).foregroundStyle(.orange).textSelection(.enabled)
            }
            Text(workspace.status).font(.callout).foregroundStyle(.secondary)
            Divider()
            Text("Selected review pairs").font(.headline)
            let page = ComparisonChangePage(count: session.pairs.count, index: pairPage)
            ReviewPageControls(page: page, count: session.pairs.count, index: $pairPage)
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    if session.pairs.isEmpty {
                        Text("No review pairs selected. Compare uses the existing automatic matching policy.")
                            .foregroundStyle(.secondary)
                    }
                    ForEach(Array(session.pairs[page.range]), id: \.baselineID) { pair in
                        HStack(alignment: .top) {
                            VStack(alignment: .leading, spacing: 5) {
                                Text("Baseline: \(pair.baselineID)")
                                Text("Current: \(pair.currentID)")
                            }
                            .font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                            Spacer()
                            Button("Remove") { session.remove(pair) }
                        }
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(minHeight: 100, idealHeight: 160, maxHeight: 200)
        }
        .padding(AppDesign.Space.page)
        .frame(minWidth: 900, idealWidth: 1080, minHeight: 680, idealHeight: 820)
        .appDialogSurface()
    }
}

@MainActor
private struct ManualPairFindingList: View {
    let title: String
    let source: SavedComparisonSource
    @Binding var selectedID: String?
    @State private var search = ""
    @State private var pageIndex = 0
    @State private var findings: [Finding] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.headline)
            Text(source.report.image.displayName).font(.callout).textSelection(.enabled)
            TextField("Search name, ID, offset, verdict or scope", text: $search)
                .onChange(of: search) { _, _ in refresh() }
            let page = ComparisonChangePage(count: findings.count, index: pageIndex)
            ReviewPageControls(page: page, count: findings.count, index: $pageIndex)
            ScrollView {
                VStack(alignment: .leading, spacing: 10) {
                    if findings.isEmpty { Text("No findings match this search.").foregroundStyle(.secondary) }
                    ForEach(Array(findings[page.range])) { finding in
                        VStack(alignment: .leading, spacing: 5) {
                            Button { selectedID = finding.id } label: {
                                Label(finding.displayName, systemImage: selectedID == finding.id ? "checkmark.circle.fill" : "circle")
                                    .frame(maxWidth: .infinity, alignment: .leading)
                            }
                            .buttonStyle(.plain)
                            Text(finding.id).font(.system(.caption, design: .monospaced))
                            Text("Entry offset: \(finding.function.imageOffset) · \(finding.verdict.title) · \(finding.scope)")
                                .font(.caption).foregroundStyle(.secondary)
                        }
                        .textSelection(.enabled)
                        .padding(8)
                        .background(selectedID == finding.id ? Color.accentColor.opacity(0.12) : Color.clear,
                                    in: RoundedRectangle(cornerRadius: 6))
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .frame(minHeight: 200, idealHeight: 320)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .onAppear { refresh() }
    }

    private func refresh() {
        let query = search.trimmingCharacters(in: .whitespacesAndNewlines)
        findings = source.report.findings.filter { $0.matches(query) || $0.id.localizedCaseInsensitiveContains(query) }
        pageIndex = 0
    }
}

struct ReviewPageControls: View {
    let page: ComparisonChangePage
    let count: Int
    @Binding var index: Int

    var body: some View {
        HStack {
            Text(count == 0 ? "0 findings" : "\(page.range.lowerBound + 1)–\(page.range.upperBound) of \(count)")
                .font(.caption).foregroundStyle(.secondary)
            Spacer()
            Button("Previous") { index = page.index - 1 }.disabled(page.index == 0)
            Button("Next") { index = page.index + 1 }.disabled(page.index + 1 >= page.pageCount)
        }
    }
}
