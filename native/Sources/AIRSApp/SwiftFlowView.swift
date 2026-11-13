import SwiftUI
import AIRSCore

struct SwiftFlowView: View {
    @Bindable var workspace: SwiftFlowWorkspace
    @ObservedObject var audit: AuditWorkspace
    private var profileCaption: String {
        guard workspace.profile != .standard else {
            return "Methods: qualified synchronous Int → Int struct calls only. Witnesses include required region, entry and presentation evidence. ARM64 only; other forms decline or remain unresolved."
        }
        let extendedLimits: Bool = [.broadExtended, .broadExtendedV2, .broadExtendedV3, .broadImports].contains(workspace.profile)
        let functionLimit: String = workspace.profile == .broad ? "8,192" : "9,216"
        let scanLimit: String = extendedLimits ? "2,097,152" : "262,144"
        let retainedCalls: String = extendedLimits ? "8,192" : "4,096"
        var caption: String = "Broad: recorded declaration, ABI, callsite, control-flow, value and independent witness checks. ARM64 only."
        caption += " Function limit: \(functionLimit); scan limit: \(scanLimit) words; retained calls: \(retainedCalls); image 8 MiB, report 16 MiB."
        caption += " Call, metadata, per-function and work limits can still make results incomplete. Structural eligibility is not runtime or source proof."
        if workspace.profile == .broadImports {
            caption += " Direct calls to imported `$s` symbols are attributed through verified stubs and remain unresolved: no ABI, witness, return or dyld-binding claim."
        }
        if workspace.profile == .broadExtendedV2 || workspace.profile == .broadExtendedV3 {
            caption += " Imported callees are attributed only and stay unresolved."
        }
        if workspace.profile == .broadExtendedV2 {
            caption += " Each retained imported-call row also records a caller-side error test: a fact about the caller at that call, with no claim about whether the callee throws; absence of the idiom proves nothing."
        }
        if workspace.profile == .broadExtendedV3 {
            caption += " Adds the caller-side error test (a fact about the caller only), plus indirect-target shape and value-witness admission records for indirect call sites: recorded evidence with no claim about callee behaviour; an admitted value-witness call stays declined as value_witness_abi_nonthrowing."
        }
        return caption
    }
    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Swift Error Flow").font(.title2.bold())
            Text("Bounded structural evidence. Calls may not return; branches, exclusive handlers and reconstructed source are not proven.")
                .font(.callout).foregroundStyle(.secondary)
            HStack {
                Button("Choose Binary or App…", action: workspace.chooseInput)
                Button("Open Saved JSON…", action: workspace.openSaved)
                Text(workspace.input?.lastPathComponent ?? "No analysis input selected").lineLimit(1)
            }.disabled(workspace.isBusy)
            HStack {
                Picker("Analysis profile", selection: $workspace.profile) {
                    ForEach(SwiftFlowProfile.allCases) { profile in Text(profile.title).tag(profile) }
                }.frame(maxWidth: 340).disabled(workspace.isBusy)
                if workspace.profile == .standard {
                    Toggle("Include qualified struct methods", isOn: $workspace.includeMethods).disabled(workspace.isBusy)
                    Toggle("Include outcome witnesses", isOn: $workspace.includeWitnesses).disabled(workspace.isBusy)
                } else {
                    Text("Outcome witnesses and required region/entry checks included").font(.caption)
                }
            }
            HStack {
                Button("Analyze") {
                    do { workspace.run(configuration: try EngineConfiguration.resolve(pythonSetting: audit.pythonPath, useExternalPython: audit.usesExternalPython)) }
                    catch { workspace.errorMessage = error.localizedDescription }
                }.disabled(workspace.isBusy || workspace.input == nil)
                if workspace.isBusy { Button("Cancel", action: workspace.cancel) }
                Button("Export JSON…", action: workspace.chooseExport).disabled(workspace.report == nil || workspace.isBusy)
            }
            .toggleStyle(.checkbox)
            Text(profileCaption)
                .font(.caption).foregroundStyle(.secondary)
            if let report = workspace.report {
                Text(workspace.isHistorical ? "Historical evidence · recorded validation only" : "Current analysis · bounded recorded evidence")
                    .font(.headline)
                Text(report.imageDescription).font(.caption).textSelection(.enabled)
                Text("Model: \(report.modelVersion)").font(.caption)
                Text(report.summaryText).font(.caption)
                if !report.supportsInterpretation { Text("Unknown model profile. Raw evidence is available; interpretations are unavailable.").foregroundStyle(.orange) }
                HStack {
                    Button("Previous calls") { workspace.moveCallPage(-1) }.disabled(workspace.callPage == 0 || workspace.isBusy)
                    Text("Calls page \(workspace.callPage + 1) of \(workspace.callPageCount)")
                    Button("Next calls") { workspace.moveCallPage(1) }.disabled(workspace.callPage + 1 >= workspace.callPageCount || workspace.isBusy)
                    Text("Up to 200 retained calls per page; export includes the complete recorded report.").font(.caption)
                }
                HSplitView {
                    List(workspace.displayedCalls, selection: $workspace.selection) { call in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(call.calleeSymbol).lineLimit(1)
                            Text("\(call.callPC) · \(call.status)").font(.caption).foregroundStyle(.secondary)
                            if let status = call.witnessStatus { Text("Witness: \(status)").font(.caption) }
                        }.tag(call.id)
                    }.frame(minWidth: 230, idealWidth: 300, maxWidth: 440)
                    ScrollView {
                        VStack(alignment: .leading, spacing: 10) {
                            if let call = workspace.selectedCall {
                                Text(call.calleeSymbol).font(.headline).textSelection(.enabled)
                                Text("Call \(call.callPC) · caller \(call.callerPC)").textSelection(.enabled)
                                if let pc = call.testPC { Text("Recorded test: \(pc)") }
                                if let success = call.successPC, let error = call.errorPC { Text("Success successor: \(success)\nError successor: \(error)") }
                                if let reason = call.reason { Text("Reason: \(reason)") }
                                if let status = call.witnessStatus { Text("Witness: \(status) · structural scope only").font(.headline) }
                                if let reason = call.witnessReason { Text("Witness reason: \(reason)") }
                                if let steps = call.witnessWorkSteps { Text("Recorded validation work: \(steps) steps") }
                                if let count = call.witnessCheckedInstructionCount { Text("Recorded checked instructions: \(count)") }
                                if !call.witnessFacts.isEmpty { Text("Recorded validation facts").font(.headline); Text(call.witnessFacts.joined(separator: "\n")).font(.caption) }
                                if !call.witnessEdges.isEmpty { Text("Recorded structural edges").font(.headline); Text(call.witnessEdges.joined(separator: "\n")).font(.caption.monospaced()) }
                                Text("Recorded instruction, identity and witness details").font(.headline)
                                HStack {
                                    Button("Previous detail") { workspace.moveDetailPage(-1) }.disabled(workspace.detailPage == 0)
                                    Text("Evidence page \(workspace.detailPage + 1) of \(workspace.detailPageCount)")
                                    Button("Next detail") { workspace.moveDetailPage(1) }.disabled(workspace.detailPage + 1 >= workspace.detailPageCount)
                                }
                                Text(workspace.detailText).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                                Text("Every retained declaration, ABI, graph, instruction, value, validator outcome and refusal is available through these evidence pages. Export preserves original JSON bytes.").font(.caption)
                            } else { Text("Select a recorded call to inspect its evidence.") }
                            Divider()
                            Text("Report limitations").font(.headline)
                            Text(report.limitations.joined(separator: "\n")).font(.caption)
                        }.frame(maxWidth: .infinity, alignment: .leading).padding(12)
                    }.frame(minWidth: 300)
                }
            } else {
                ContentUnavailableView("No Swift report", systemImage: "point.3.connected.trianglepath.dotted", description: Text("Choose an owned binary to analyze or open saved evidence. Selecting an input does not start analysis."))
            }
        }
        .padding(16)
        .alert("Swift Error Flow", isPresented: Binding(get: { workspace.errorMessage != nil }, set: { if !$0 { workspace.errorMessage = nil } })) {
            Button("OK") { workspace.errorMessage = nil }
        } message: { Text(workspace.errorMessage ?? "") }
    }
}
