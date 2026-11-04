import SwiftUI
import AIRSEntitlements
import EntitlementDiffCore

/// Presentation only: report derivation and paging are owned by the session.
struct ComponentSecurityDeltaView: View {
    let session: ComponentReviewSession
    @State private var page = 0
    @State private var selection: String?
    @State private var showingObservations = false
    @State private var category = "all"
    @State private var component = "all"
    @State private var filtered: SecurityDeltaFilteredRows?

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            if let report = session.securityDeltaReport {
                SecurityDeltaHeader(report: report)
                HStack {
                    Picker("Category", selection: $category) {
                        Text("All categories").tag("all")
                        ForEach(SecurityDeltaCategory.allCases, id: \.rawValue) { item in Text(item.rawValue).tag(item.rawValue) }
                    }
                    Picker("Component", selection: $component) {
                        Text("All components").tag("all")
                        ForEach(session.securityDeltaComponents) { item in Text(DisplayText.escaped(item.path)).tag(item.id) }
                    }
                }
                Picker("Display", selection: $showingObservations) {
                    Text("Findings").tag(false); Text("All observations").tag(true)
                }.pickerStyle(.segmented).onChange(of: showingObservations) { _, _ in page = 0; selection = nil }
                HStack {
                    Button("Previous page") { page -= 1; selection = nil }.disabled(page <= 0)
                    Text(pageCount == 0 ? "No records" : "Page \(page + 1) of \(pageCount)")
                    Button("Next page") { page += 1; selection = nil }.disabled(page + 1 >= pageCount)
                    Spacer()
                }
                HSplitView {
                    if showingObservations, let pages = filtered?.observations, pages.indices.contains(page) {
                        List(pages[page], selection: $selection) { observation in
                            VStack(alignment: .leading) {
                                Text(DisplayText.escaped(observation.subject)).font(.headline)
                                Text(DisplayText.escaped(observation.componentPath) + " · " + observation.disposition.rawValue).foregroundStyle(.secondary)
                            }.tag(observation.id)
                        }.frame(minWidth: 280)
                    } else if !showingObservations, let pages = filtered?.findings, pages.indices.contains(page) {
                        List(pages[page], selection: $selection) { finding in
                            VStack(alignment: .leading) {
                                Text(finding.title).font(.headline)
                                Text(finding.disposition.rawValue).foregroundStyle(.secondary)
                            }.tag(finding.id)
                        }.frame(minWidth: 280)
                    }
                    if showingObservations, let selection, let observation = session.securityDeltaObservations[selection] {
                        ScrollView { SecurityDeltaObservationDetail(observation: observation, session: session).id(observation.id).padding() }
                    } else if let selection, let finding = session.securityDeltaFindings[selection] {
                        SecurityDeltaFindingDetail(finding: finding, session: session).id(finding.id)
                    } else {
                        Text("Select a finding to inspect its recorded evidence.").frame(maxWidth: .infinity, maxHeight: .infinity)
                    }
                }
                SecurityDeltaCoverageView(coverage: report.coverage)
            } else {
                Text(session.securityDeltaFailure ?? "Security change analysis is unavailable for this review.")
            }
        }.task(id: FilterIdentity(session: session.id, category: category, component: component)) {
            filtered = nil; page = 0; selection = nil
            let selectedCategory = category, selectedComponent = component, capturedSession = session
            let worker = Task.detached { try ComponentSecurityDeltaOperations.filteredRows(capturedSession, category: selectedCategory, component: selectedComponent) }
            do {
                let result = try await withTaskCancellationHandler(operation: { try await worker.value }, onCancel: { worker.cancel() })
                try Task.checkCancellation(); filtered = result
            } catch { }
        }
    }
    private var pageCount: Int { showingObservations ? (filtered?.observations.count ?? 0) : (filtered?.findings.count ?? 0) }
    private struct FilterIdentity: Hashable { let session: UUID; let category: String; let component: String }
}

private struct SecurityDeltaHeader: View {
    let report: ComponentSecurityDeltaReport
    var body: some View {
        VStack(alignment: .leading) {
            Text("Previous → Current · Requested slice: " + report.identity.architecture).font(.headline)
            Text("\(report.findings.count) findings · \(report.observations.count) recorded observations")
            Text("Static evidence describes recorded declarations and bytes; it is not a trust or runtime verdict.").foregroundStyle(.secondary)
        }
    }
}

private struct SecurityDeltaFindingDetail: View {
    let finding: SecurityDeltaFinding
    let session: ComponentReviewSession
    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 8) {
                Text(finding.title).font(.headline)
                Text(DisplayText.escaped(finding.explanation))
                ForEach(finding.observationIDs, id: \.self) { id in
                    if let observation = session.securityDeltaObservations[id] {
                        SecurityDeltaObservationDetail(observation: observation, session: session)
                    }
                }
                Text("Evidence references").font(.headline)
                ForEach(Array(finding.evidence.enumerated()), id: \.offset) { _, reference in
                    SecurityDeltaReferenceDetail(reference: reference, session: session)
                }
                ForEach(finding.limitations, id: \.code) { Text($0.code + ": " + $0.diagnostic).foregroundStyle(.secondary) }
            }.frame(maxWidth: .infinity, alignment: .leading).padding()
        }
    }
}

private struct SecurityDeltaObservationDetail: View {
    let observation: SecurityDeltaObservation
    let session: ComponentReviewSession
    var body: some View {
        VStack(alignment: .leading) {
            Text(DisplayText.escaped(observation.componentPath) + " · " + DisplayText.escaped(observation.subject)).bold()
            Text("\(observation.previousState.rawValue) → \(observation.currentState.rawValue) · \(observation.disposition.rawValue)")
            if let value = observation.previousValue { DisclosureGroup("Previous typed value") { SecurityDeltaTypedValueView(value: value) } }
            if let value = observation.currentValue { DisclosureGroup("Current typed value") { SecurityDeltaTypedValueView(value: value) } }
            ForEach(observation.limitations, id: \.code) { Text($0.code + ": " + $0.diagnostic).foregroundStyle(.secondary) }
            ForEach(Array(observation.evidence.enumerated()), id: \.offset) { _, reference in
                SecurityDeltaReferenceDetail(reference: reference, session: session)
            }
        }
    }
}

private struct SecurityDeltaReferenceDetail: View {
    let reference: SecurityDeltaEvidenceReference
    let session: ComponentReviewSession
    @State private var expanded = false
    var body: some View {
        DisclosureGroup(isExpanded: $expanded) {
            Text("Inventory \(reference.inventoryID.uuidString) · Component \(reference.componentID?.uuidString ?? "scope")")
            Text("Locator: \(DisplayText.escaped(reference.evidenceKey ?? "source")) · Slice: \(reference.architecture ?? "not selected")")
            if let slice = reference.slice {
                Text("CPU " + String(format: "0x%08X", slice.cpuType) + ", subtype " + String(format: "0x%08X", slice.cpuSubtype) +
                     ", magic " + String(format: "0x%08X", slice.headerMagic) + ", index \(slice.index), offset \(slice.offset), size \(slice.size)")
                if let digest = slice.recordedSHA256 { Text("Recorded slice digest: " + digest) }
            }
            if expanded { SecurityDeltaSourceInspector(reference: reference, session: session) }
        } label: {
            Text("\(reference.side.rawValue) · \(reference.category.rawValue) · \(DisplayText.escaped(reference.relativeSource))")
        }.textSelection(.enabled)
    }
}

private struct SecurityDeltaSourceInspector: View {
    let reference: SecurityDeltaEvidenceReference
    let session: ComponentReviewSession
    @State private var content: SecurityDeltaEvidenceContent?
    @State private var failure: String?
    var body: some View {
        VStack(alignment: .leading) {
            if let content {
                Text(content.description)
                let inventory = reference.side == .previous ? session.review.previous : session.review.current
                Text("Inventory recorded: " + inventory.capturedAt.formatted(date: .abbreviated, time: .standard))
                if let id = reference.componentID, reference.category == .entitlements,
                   let item = session.entitlementEvidence.first(where: { $0.side == reference.side && $0.componentID == id }) {
                    Text((item.state == .unexamined ? "Unexamined state recorded: " : "Entitlement acquisition recorded: ") + item.capturedAt.formatted(date: .abbreviated, time: .standard))
                } else if let id = reference.componentID, reference.category == .signatureEvidence,
                          let item = session.signatureEvidence.first(where: { $0.side == reference.side && $0.document.evidence.componentID == id }) {
                    Text("Signature acquisition recorded: " + item.document.capturedAt.formatted(date: .abbreviated, time: .standard))
                } else if let id = reference.componentID, reference.category == .signatureEvidence,
                          let item = session.signatureRefusals.first(where: { $0.side == reference.side && $0.componentID == id }) {
                    Text("Signature refusal recorded: " + item.capturedAt.formatted(date: .abbreviated, time: .standard))
                } else {
                    Text("Separate source acquisition time: not recorded.")
                }
                Text("Recorded acquisitions may have occurred at different times.").foregroundStyle(.secondary)
                if let value = content.value { DisclosureGroup("Recorded typed source") { SecurityDeltaTypedValueView(value: value) } }
                if let bytes = content.sourceBytes { DisclosureGroup("Retained source bytes") { SecurityDeltaDataPages(bytes: bytes) } }
            } else if let failure { Text("Source detail unavailable: " + failure) }
            else { Text("Resolving recorded source…") }
        }.task {
            let worker = Task.detached { try ComponentSecurityDeltaOperations.resolveEvidence(reference, in: session) }
            do {
                let result = try await withTaskCancellationHandler(operation: { try await worker.value }, onCancel: { worker.cancel() })
                try Task.checkCancellation(); content = result
            } catch { if !Task.isCancelled { failure = error.localizedDescription } }
        }
    }
}

private struct SecurityDeltaTypedValueView: View {
    let value: SecurityDeltaValue
    @State private var page = 0
    var body: some View {
        switch value {
        case .boolean(let value): Text("Boolean: \(value ? "true" : "false")")
        case .signed(let value): Text("Signed integer: \(value)")
        case .unsigned(let value): Text("Unsigned integer: \(value)")
        case .normalizedInteger(let value): Text("Integer, original representation unspecified: " + value)
        case .realBits(let bits): Text("Real bit pattern: " + String(format: "%016llx", bits))
        case .dateBits(let bits): Text("Date bit pattern: " + String(format: "%016llx", bits))
        case .string(let text): SecurityDeltaTextPages(text: text)
        case .data(let bytes): SecurityDeltaDataPages(bytes: bytes)
        case .array(let values):
            VStack(alignment: .leading) {
                Text("Ordered array: \(values.count) values")
                SecurityDeltaPageControls(page: $page, total: values.count, pageSize: 200)
                ForEach(Array(values.enumerated().dropFirst(page * 200).prefix(200)), id: \.offset) { index, child in
                    DisclosureGroup("[\(index)]") { SecurityDeltaTypedValueView(value: child) }
                }
            }
        case .dictionary(let entries):
            VStack(alignment: .leading) {
                Text("Dictionary: \(entries.count) exact keys")
                SecurityDeltaPageControls(page: $page, total: entries.count, pageSize: 200)
                ForEach(Array(entries.enumerated().dropFirst(page * 200).prefix(200)), id: \.offset) { _, entry in
                    DisclosureGroup(DisplayText.escaped(entry.key)) { SecurityDeltaTypedValueView(value: entry.value) }
                }
            }
        }
    }
}

private struct SecurityDeltaPageControls: View {
    @Binding var page: Int
    let total: Int
    let pageSize: Int
    var body: some View {
        HStack {
            Button("Previous") { page -= 1 }.disabled(page == 0)
            Text("\(total == 0 ? 0 : page * pageSize + 1)–\(min((page + 1) * pageSize, total)) of \(total)")
            Button("Next") { page += 1 }.disabled((page + 1) * pageSize >= total)
        }
    }
}

private struct SecurityDeltaTextPages: View {
    let text: String
    @State private var page = 0
    var body: some View {
        let scalars = text.unicodeScalars
        let start = scalars.index(scalars.startIndex, offsetBy: min(page * 1024, scalars.count))
        let end = scalars.index(start, offsetBy: min(1024, scalars.distance(from: start, to: scalars.endIndex)))
        VStack(alignment: .leading) {
            Text("String · Unicode scalars: \(scalars.count)")
            SecurityDeltaPageControls(page: $page, total: scalars.count, pageSize: 1024)
            Text(DisplayText.escaped(String(scalars[start..<end]))).textSelection(.enabled)
        }
    }
}

private struct SecurityDeltaDataPages: View {
    let bytes: Data
    @State private var page = 0
    var body: some View {
        let start = min(page * 256, bytes.count), end = min((page + 1) * 256, bytes.count)
        VStack(alignment: .leading) {
            Text("Data · \(bytes.count) bytes")
            SecurityDeltaPageControls(page: $page, total: bytes.count, pageSize: 256)
            Text(bytes[start..<end].map { String(format: "%02x", $0) }.joined()).textSelection(.enabled)
        }
    }
}

private struct SecurityDeltaCoverageView: View {
    let coverage: SecurityDeltaCoverage
    var body: some View {
        VStack(alignment: .leading) {
            Text("Coverage: previous \(coverage.previousScope), current \(coverage.currentScope)").bold()
            DisclosureGroup("Recorded scope, exclusions and issues") {
                ScrollView {
                    LazyVStack(alignment: .leading) {
                        SecurityDeltaCoverageRows(title: "Previous searched locations", rows: coverage.previousLocations)
                        SecurityDeltaCoverageRows(title: "Current searched locations", rows: coverage.currentLocations)
                        SecurityDeltaCoverageRows(title: "Previous exclusions", rows: coverage.previousExclusions)
                        SecurityDeltaCoverageRows(title: "Current exclusions", rows: coverage.currentExclusions)
                        SecurityDeltaCoverageRows(title: "Previous issues", rows: coverage.previousIssues)
                        SecurityDeltaCoverageRows(title: "Current issues", rows: coverage.currentIssues)
                    }
                }.frame(maxHeight: 200)
            }
            ForEach(coverage.limitations, id: \.code) { Text($0.code + ": " + $0.diagnostic) }
            ForEach(Array(coverage.omissions.enumerated()), id: \.offset) { _, omission in
                Text("Omitted \(omission.countIsExact ? "" : "at least ")\(omission.count); details \(omission.detailListComplete ? "complete" : "incomplete"): \(omission.reason.code)")
            }
        }.foregroundStyle(.secondary)
    }
}

private struct SecurityDeltaCoverageRows: View {
    let title: String
    let rows: [String]
    @State private var page = 0
    var body: some View {
        DisclosureGroup(title + " (\(rows.count))") {
            SecurityDeltaPageControls(page: $page, total: rows.count, pageSize: 200)
            ForEach(Array(rows.enumerated().dropFirst(page * 200).prefix(200)), id: \.offset) { _, row in
                Text(DisplayText.escaped(row)).textSelection(.enabled)
            }
        }
    }
}
