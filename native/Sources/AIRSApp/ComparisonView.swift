import SwiftUI
import LumenUI
import AIRSCore

@MainActor
struct ComparisonView: View {
    let document: ComparisonDocument
    @ObservedObject var workspace: AuditWorkspace
    var permitsExport = true
    var reviewPairs: (() -> Void)? = nil
    @Environment(\.dismiss) private var dismiss
    @State private var showUnchanged = false
    @State private var showJSON = false
    @State private var changePage = 0
    @State private var manualPage = 0
    @State private var sourceDetail: ComparisonSourceDetail?

    private var visibleChanges: [ComparisonChange] {
        document.report.changes.filter { $0.matchBasis != "manual_review" && (showUnchanged || $0.change != "unchanged") }
    }

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading, spacing: 5) {
                    AppDialogTitle(title: "Baseline comparison")
                    Text("\(document.report.comparison.baselineImage.displayName) → \(document.report.comparison.currentImage.displayName)")
                        .font(.callout).foregroundStyle(.secondary)
                }
                Spacer()
                if let reviewPairs {
                    Button("Review Pairs…", action: reviewPairs).disabled(workspace.isBusy)
                }
                Button("Export JSON…") { if permitsExport { workspace.exportComparison(document) } }
                    .disabled(workspace.isBusy || !permitsExport)
                Button("Done") { dismiss() }.keyboardShortcut(.defaultAction)
                    .disabled(workspace.isBusy && !workspace.canCancel)
            }
            .padding(AppDesign.Space.page)
            Divider()
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    if !document.manualChanges.isEmpty {
                        SectionCard("User-selected review pairs") {
                            Text("All selected review pairs are shown, including unchanged findings. These selections do not prove source-function identity or establish a regression or fix.")
                                .font(.callout).foregroundStyle(.secondary)
                            let rows = document.manualChanges
                            let page = ComparisonChangePage(count: rows.count, index: manualPage)
                            ReviewPageControls(page: page, count: rows.count, index: $manualPage)
                            ForEach(Array(rows[page.range]), id: \.key) { change in
                                ComparisonChangeView(change: change)
                                sourceButtons(change)
                                Divider()
                            }
                        }
                    }
                    SectionCard("Comparison scope") {
                        // Six fixed tiles can be measured eagerly while the native
                        // sheet negotiates its initial size through the ScrollView.
                        Grid(horizontalSpacing: 10, verticalSpacing: 10) {
                            GridRow {
                                StatTile(value: document.report.summary.matchedCount, title: "Matched functions")
                                StatTile(value: document.report.summary.changedCount, title: "Changed findings", tint: .orange)
                                StatTile(value: document.report.summary.unchangedCount, title: "Unchanged findings")
                            }
                            GridRow {
                                StatTile(value: document.report.summary.addedCount, title: "Added functions")
                                StatTile(value: document.report.summary.removedCount, title: "Removed functions")
                                StatTile(value: document.report.summary.ambiguousCount, title: "Ambiguous comparisons")
                            }
                        }
                        FactRow(label: "Image identity", value: document.report.comparison.sameImage
                                ? "Same selected image" : "Different selected images")
                        FactRow(label: "Analysis models", value: document.report.comparison.modelCompatible
                                ? "Compatible model versions" : "Model versions differ; interpret comparisons with the reported limitations")
                        FactRow(label: "Matching policy", value: document.report.comparison.matchingPolicy, monospaced: true)
                    }
                    LimitationsView(title: "Comparison limitations", limitations: document.report.limitations)
                    SectionCard("Function changes") {
                        Toggle("Include unchanged findings", isOn: $showUnchanged)
                            .onChange(of: showUnchanged) { _, _ in changePage = 0 }
                        if visibleChanges.isEmpty {
                            LumenEmptyState("No changes are visible with this filter.", prominence: .inline)
                        } else {
                            let page = ComparisonChangePage(count: visibleChanges.count, index: changePage)
                            if page.pageCount > 1 {
                                HStack {
                                    Text("Findings \(page.range.lowerBound + 1)–\(page.range.upperBound) of \(visibleChanges.count)")
                                        .font(.callout).foregroundStyle(.secondary)
                                    Spacer()
                                    Button("Previous") { changePage = page.index - 1 }
                                        .disabled(page.index == 0)
                                    Button("Next") { changePage = page.index + 1 }
                                        .disabled(page.index + 1 == page.pageCount)
                                }
                            }
                            // Eager, bounded rows avoid lazy scroll preferences feeding
                            // back into native sheet sizing, even after filter changes.
                            VStack(alignment: .leading, spacing: 16) {
                                ForEach(Array(visibleChanges[page.range].enumerated()), id: \.offset) { index, change in
                                    if index > 0 { Divider() }
                                    ComparisonChangeView(change: change)
                                    sourceButtons(change)
                                }
                            }
                        }
                    }
                    DisclosureGroup("Complete comparison JSON", isExpanded: $showJSON) {
                        ScrollView(.horizontal) {
                            Text(document.formattedJSON)
                                .font(.system(.caption, design: .monospaced))
                                .textSelection(.enabled)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .padding(.vertical, 10)
                        }
                    }
                }
                .padding(AppDesign.Space.page)
            }
        }
        .frame(minWidth: 780, idealWidth: 940, minHeight: 600, idealHeight: 740)
        .appDialogSurface()
        .sheet(item: $sourceDetail) { detail in
            VStack(spacing: 0) {
                HStack {
                    Text(detail.title).font(.headline)
                    Spacer()
                    Button("Back to Comparison") { sourceDetail = nil }
                }.padding()
                FindingDetailView(report: detail.source.report, finding: detail.finding,
                                  isBusy: false, exportHandoff: {}, permitsHandoff: false)
            }
            .frame(minWidth: 700, idealWidth: 850, minHeight: 550, idealHeight: 700)
        }
    }

    @ViewBuilder
    private func sourceButtons(_ change: ComparisonChange) -> some View {
        if let sources = document.sources {
            HStack {
                if let id = change.baselineID,
                   let finding = sources.baseline.report.findings.first(where: { $0.id == id }) {
                    Button("View Baseline Finding") {
                        sourceDetail = ComparisonSourceDetail(title: "Baseline saved finding", source: sources.baseline, finding: finding)
                    }
                }
                if let id = change.currentID,
                   let finding = sources.current.report.findings.first(where: { $0.id == id }) {
                    Button("View Current Finding") {
                        sourceDetail = ComparisonSourceDetail(title: "Current saved finding", source: sources.current, finding: finding)
                    }
                }
            }
        }
    }
}

private struct ComparisonSourceDetail: Identifiable {
    let id = UUID()
    let title: String
    let source: SavedComparisonSource
    let finding: Finding
}

struct ComparisonChangeView: View {
    let change: ComparisonChange

    var body: some View {
        VStack(alignment: .leading, spacing: 9) {
            HStack(alignment: .firstTextBaseline) {
                Text(change.functionName)
                    .font(.system(.body, design: .monospaced).weight(.semibold))
                Spacer()
                Text(readableToken(change.change)).font(.caption.weight(.semibold))
                    .foregroundStyle(change.change == "changed" ? Color.orange : Color.secondary)
            }
            FactRow(label: "Match basis", value: readableToken(change.matchBasis))
            if let id = change.baselineID { FactRow(label: "Baseline ID", value: id, monospaced: true) }
            if let id = change.currentID { FactRow(label: "Current ID", value: id, monospaced: true) }
            HStack(alignment: .top, spacing: 12) {
                EvidenceValueView(title: "Baseline", value: stateText(verdict: change.beforeVerdict, scope: change.beforeScope))
                EvidenceValueView(title: "Current", value: stateText(verdict: change.afterVerdict, scope: change.afterScope))
            }
            ForEach(Array(change.notes.enumerated()), id: \.offset) { _, note in
                Text(note).font(.callout).foregroundStyle(.secondary)
            }
        }
        .textSelection(.enabled)
    }

    private func stateText(verdict: AuditVerdict?, scope: String?) -> String {
        var parts = [verdict?.title ?? "No matched finding"]
        if let scope { parts.append("Scope: \(readableToken(scope))") }
        return parts.joined(separator: "\n")
    }
}

/// Bounds eager view construction without truncating or changing report evidence.
struct ComparisonChangePage {
    static let size = 50
    let index: Int
    let pageCount: Int
    let range: Range<Int>

    init(count: Int, index: Int) {
        let count = max(0, count)
        pageCount = count / Self.size + (count % Self.size == 0 ? 0 : 1)
        self.index = min(max(0, index), max(0, pageCount - 1))
        let lower = self.index * Self.size
        range = lower..<(lower + min(Self.size, count - lower))
    }
}
