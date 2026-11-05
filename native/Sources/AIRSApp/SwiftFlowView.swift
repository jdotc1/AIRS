import SwiftUI
import AIRSCore

struct SwiftFlowView: View {
    @Bindable var workspace: SwiftFlowWorkspace
    @ObservedObject var audit: AuditWorkspace
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
                Toggle("Include qualified struct methods", isOn: $workspace.includeMethods).disabled(workspace.isBusy)
                Toggle("Include outcome witnesses", isOn: $workspace.includeWitnesses).disabled(workspace.isBusy)
                Button("Analyze") {
                    do { workspace.run(configuration: try EngineConfiguration.resolve(pythonSetting: audit.pythonPath, useExternalPython: audit.usesExternalPython)) }
                    catch { workspace.errorMessage = error.localizedDescription }
                }.disabled(workspace.isBusy || workspace.input == nil)
                if workspace.isBusy { Button("Cancel", action: workspace.cancel) }
                Button("Export JSON…", action: workspace.chooseExport).disabled(workspace.report == nil || workspace.isBusy)
            }
            .toggleStyle(.checkbox)
            Text("Methods: qualified synchronous Int → Int struct calls only. Witnesses include required region, entry and presentation evidence. ARM64 only; other forms decline or remain unresolved.")
                .font(.caption).foregroundStyle(.secondary)
            if let report = workspace.report {
                Text(workspace.isHistorical ? "Historical evidence · recorded validation only" : "Current analysis · bounded recorded evidence")
                    .font(.headline)
                Text(report.imageDescription).font(.caption).textSelection(.enabled)
                Text("Model: \(report.modelVersion)").font(.caption)
                Text(report.summaryText).font(.caption)
                if !report.supportsInterpretation { Text("Unknown model profile. Raw evidence is available; interpretations are unavailable.").foregroundStyle(.orange) }
                HSplitView {
                    List(report.calls, selection: $workspace.selection) { call in
                        VStack(alignment: .leading, spacing: 3) {
                            Text(call.calleeSymbol).lineLimit(1)
                            Text("\(call.callPC) · \(call.status)").font(.caption).foregroundStyle(.secondary)
                            if let status = call.witnessStatus { Text("Witness: \(status)").font(.caption) }
                        }.tag(call.id)
                    }.frame(minWidth: 230, idealWidth: 300)
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
                                Text(String(call.detailJSON.prefix(16000))).font(.system(.caption, design: .monospaced)).textSelection(.enabled)
                                if call.detailJSON.count > 16000 { Text("Display capped at 16,000 characters. Export retains the original report.").font(.caption) }
                            } else { Text("Select a recorded call to inspect its evidence.") }
                            Divider()
                            Text("Report limitations").font(.headline)
                            Text(report.limitations.prefix(32).joined(separator: "\n")).font(.caption)
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
