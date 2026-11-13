import SwiftUI
import AIRSCore
import AIRSEntitlements

@MainActor
struct SavedReportTriageView: View {
    @ObservedObject var session: SavedReportTriageSession
    @Bindable var owner: AIRSFileOpen
    @ObservedObject var audit: AuditWorkspace
    let entitlements: EntitlementsWorkspace
    let navigation: AIRSNavigation

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            if session.page == .source, let report = session.sourceReport, let finding = session.sourceFinding {
                HStack {
                    Text("Original saved finding").font(.headline)
                    Spacer()
                    Button("Back to Inventory") { session.backToInventory() }
                    if session.findings != nil { Button("Back to Findings") { session.backToFindings() } }
                }
                FindingDetailView(report: report, finding: finding, isBusy: false, exportHandoff: {}, permitsHandoff: false)
            } else if session.page == .findings, let findings = session.findings {
                TriageFindingsView(session: session, value: findings, busy: owner.isBusy,
                    apply: { owner.chooseTriageFindings(reportIndex: session.selectedReport, reason: session.selectedReason, audit: audit, entitlements: entitlements) })
            } else {
                Text("Unresolved reasons").font(.title2).bold()
                if session.importedURL == nil || !session.sources.isEmpty {
                    TriageInputView(session: session, busy: owner.isBusy,
                        add: { owner.chooseTriageReports(audit: audit, entitlements: entitlements) },
                        apply: { _ = owner.runTriageCoverage(audit: audit, entitlements: entitlements) })
                }
                if let inventory = session.inventory {
                    CoverageReviewView(inventory: inventory, busy: owner.isBusy, status: "",
                        openObservation: { example, reason in
                            if session.inventorySources.indices.contains(example.report_index) {
                                owner.chooseTriageFindings(reportIndex: example.report_index, reason: reason, audit: audit, entitlements: entitlements)
                            } else {
                                owner.chooseCoverageObservation(example, reason: reason, audit: audit, entitlements: entitlements, navigation: navigation)
                            }
                        }, close: owner.closeCoverage,
                        reviewFindings: { index, reason in owner.chooseTriageFindings(reportIndex: index, reason: reason, audit: audit, entitlements: entitlements) },
                        embedded: true)
                } else {
                    Text("Choose saved audit reports and Apply to collect their unresolved reasons. The current saved report is the only automatic initial input.")
                    Spacer()
                }
            }
            if let message = session.message { Text(message).foregroundStyle(.red).textSelection(.enabled) }
            Text(owner.status).foregroundStyle(.secondary)
            HStack {
                if owner.isBusy { ProgressView().controlSize(.small) }
                Button("Export Result…") { owner.exportTriage(audit: audit, entitlements: entitlements) }
                    .disabled(owner.isBusy || (session.page == .inventory ? session.inventoryData == nil : session.findings == nil))
                Spacer()
                if owner.canCancel { Button("Cancel Operation", action: owner.cancel) }
                Button("Done", action: owner.closeCoverage).disabled(owner.isBusy && !owner.canCancel)
            }
        }
        .padding(20).frame(minWidth: 820, idealWidth: 1040, minHeight: 680, idealHeight: 820)
        .onDisappear { owner.triageSheetDisappeared(session) }
        .onChange(of: audit.reportRevision) { _, revision in
            if revision != session.auditRevision { owner.closeCoverage() }
        }
        .onChange(of: entitlements.model.reportRevision) { _, revision in
            if revision != session.entitlementRevision { owner.closeCoverage() }
        }
    }
}

@MainActor
private struct TriageInputView: View {
    @ObservedObject var session: SavedReportTriageSession
    let busy: Bool
    let add: () -> Void
    let apply: () -> Void
    @State private var page = 0
    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text("\(session.sources.count) explicit inputs; order and duplicates retained").bold()
                Button("Add Reports…", action: add).disabled(busy)
            }
            ScrollView {
                LazyVStack(alignment: .leading) {
                    ForEach(Array(session.sources.dropFirst(page * 10).prefix(10))) { source in
                        HStack {
                            Text(source.name + " · \(source.findingCount) findings").lineLimit(2)
                            Spacer()
                            Button("Remove") { session.removeSource(source.id); page = min(page, max(0, (session.sources.count - 1) / 10)) }.disabled(busy)
                        }
                    }
                }
            }.frame(maxHeight: 105)
            TriagePageControls(page: $page, count: session.sources.count, size: 10)
            HStack {
                TextField("Reason codes, comma separated (optional)", text: $session.reasonText)
                TextField("Minimum", text: $session.minimumText).frame(width: 85)
                Picker("Order", selection: $session.coverageOrder) {
                    Text("Count").tag(CoverageOptions.Order.count)
                    Text("Reason").tag(CoverageOptions.Order.reason)
                }.frame(width: 170)
                TextField("Limit (optional)", text: $session.coverageLimitText).frame(width: 115)
                Button("Apply", action: apply).disabled(busy || session.sources.isEmpty)
            }
            Text("Blank limit retains all reason details; pages change only the display. Minimum 1 includes singleton unresolved reasons.").font(.caption).foregroundStyle(.secondary)
        }
    }
}

@MainActor
private struct TriageFindingsView: View {
    @ObservedObject var session: SavedReportTriageSession
    let value: TriageFindings
    let busy: Bool
    let apply: () -> Void
    @State private var page = 0
    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            HStack {
                Text("Findings · Report \(value.reportIndex + 1) · " + value.source.name).font(.headline)
                Spacer()
                Button("Back to Inventory") { session.backToInventory() }.disabled(busy)
            }
            Text("Full source: \(value.summary.summary.functionCount) findings, \(value.summary.summary.unresolvedCount) unresolved. Showing \(value.summary.findings.count) selected findings; omitted details remain in the denominator.")
            if let selection = value.summary.finding_selection {
                Text("Verdict/reason selection: \(selection.selected_count) selected · \(selection.omitted_count) omitted / \(selection.original_count)")
            }
            if let selection = value.summary.finding_name_selection {
                Text("Name selection: \(selection.selected_count) selected · \(selection.omitted_count) omitted / \(selection.input_count)")
            }
            if let limit = value.summary.finding_limit {
                Text("Detail limit: \(limit.returned_count) returned · \(limit.omitted_count) omitted / \(limit.selected_count)")
            }
            HStack {
                Picker("Verdict", selection: $session.summaryVerdict) {
                    Text("All verdicts").tag(Optional<AuditVerdict>.none)
                    ForEach(AuditVerdict.allCases) { verdict in Text(verdict.title).tag(Optional(verdict)) }
                }
                TextField("Literal name contains (case sensitive)", text: $session.nameText)
                Picker("Order", selection: $session.summaryOrder) {
                    Text("Source").tag(SummaryOptions.Order.source)
                    Text("Verdict").tag(SummaryOptions.Order.verdict)
                }
                TextField("Limit (optional)", text: $session.summaryLimitText).frame(width: 115)
                Button("Apply", action: apply).disabled(busy)
            }
            if value.summary.findings.isEmpty { Text("No findings match this selection. Full saved-report counts remain unchanged.").foregroundStyle(.secondary) }
            List {
                ForEach(Array(value.summary.findings.dropFirst(page * 50).prefix(50))) { row in
                    VStack(alignment: .leading, spacing: 4) {
                        Text((row.function.name ?? row.function.address) + " · " + row.verdict.title)
                        DisclosureGroup("Saved finding details") {
                            Text(row.id).textSelection(.enabled)
                            Text("Function entry: " + row.function.address + " · " + row.scope + " · " + row.mode)
                            Text(row.reason_codes.joined(separator: ", ")).textSelection(.enabled)
                        }
                        Button("Open Original Finding") { session.openFinding(row.id) }.disabled(busy)
                    }
                }
            }
            TriagePageControls(page: $page, count: value.summary.findings.count, size: 50)
            Text("Summary rows omit evidence bodies. Original saved findings retain issues, checked PCs and limitations; they do not establish whole-image correctness.").foregroundStyle(.secondary)
        }
        .onChange(of: value.id) { _, _ in page = 0 }
    }
}

struct TriagePageControls: View {
    @Binding var page: Int
    let count: Int
    let size: Int
    static func lastPage(count: Int, size: Int) -> Int { max(0, (count - 1) / size) }
    var body: some View {
        HStack {
            Button("Previous") { page -= 1 }.disabled(page == 0)
            Text("Page \(page + 1) of \(Self.lastPage(count: count, size: size) + 1) · \(count) rows")
            Button("Next") { page += 1 }.disabled(page >= Self.lastPage(count: count, size: size))
        }.controlSize(.small)
    }
}
