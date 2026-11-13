import SwiftUI
import AIRSEntitlements

struct CoverageReviewSession:Identifiable,Sendable {
    let id=UUID()
    let inventory:CoverageInventory
    let sourceURL:URL
}
struct CoverageReviewView:View {
    let inventory:CoverageInventory
    let busy:Bool
    let status:String
    let openObservation:(CoverageInventory.Example,String)->Void
    let close:()->Void
    var reviewFindings: ((Int, String?) -> Void)? = nil
    var embedded = false
    @State private var reasonPage = 0
    var body:some View {
        VStack(alignment:.leading,spacing:12) {
            if !embedded { Text("Saved-report Coverage Inventory").font(.title2).bold() }
            Text("Aggregation: "+(inventory.status == "complete" ? "Complete" : "Conflicting reports")+" · Supplied reports: \(inventory.summary.input_report_count) · Duplicate reports excluded: \(inventory.summary.duplicate_report_count)")
            Text("Supplied findings: \(inventory.summary.function_count) · Agreement: \(inventory.summary.agreement_count) · Inconsistency: \(inventory.summary.inconsistency_count) · Unresolved: \(inventory.summary.unresolved_count)")
            DisclosureGroup("Interpretation and limits") {
                Text("Aggregation complete does not mean analysis complete. Input limits, partial reads and issues remain in each source report. These are verdict counts, separate from metadata coverage and observation scope; they are not real-world prevalence.").foregroundStyle(.secondary)
                if let ratio=inventory.compatibleVerdictRatio {
                    Text("Resolved verdict count: \(ratio.resolvedNumerator) / \(ratio.functionDenominator) supplied functions in compatible reports. This is not all-PC or whole-binary unwind coverage.")
                } else {
                    Text("No combined ratio: zero functions, unknown configuration, incompatible model/configuration/CPU scope, or conflicting reports.")
                }
            }
            if let selected = inventory.selection?.reason_selection {
                Text("Reason selection: \(selected.matched.count) matched · \(selected.unmatched.count) unmatched / \(selected.requested.count) requested")
                DisclosureGroup("Reason selection details") {
                    Text("Requested: " + selected.requested.joined(separator: ", "))
                    Text("Unmatched: " + selected.unmatched.joined(separator: ", "))
                }
            }
            if let frequency = inventory.selection?.reason_frequency_selection {
                Text("Minimum \(frequency.minimum_count): \(frequency.selected_count) selected · \(frequency.omitted_count) omitted / \(frequency.input_count) reason rows")
            }
            if let limit = inventory.selection?.reason_limit {
                Text("Detail limit: \(limit.returned_count) returned · \(limit.omitted_count) omitted / \(limit.selected_count) selected reason rows")
            }
            List {
                Section("Supplied report records") {
                    ForEach(inventory.reports) {record in
                        VStack(alignment:.leading,spacing:4) {
                            Text("Report \(record.index + 1) · "+record.image.display_name)
                            DisclosureGroup("Saved report details") { Text(record.model) }
                            if let reviewFindings { Button("Review Findings…") { reviewFindings(record.index, nil) }.disabled(busy) }
                            Text(inventory.configurationLabel(for:record)+" · "+record.image.architecture+" · "+record.image.slice_sha256).textSelection(.enabled)
                            Text("\(record.summary.unresolvedCount) unresolved / \(record.summary.functionCount) supplied functions · \(record.summary.checkedPCCount) checked PCs"+(record.duplicate_of.map{" · Duplicate of report \($0 + 1)"} ?? ""))
                        }
                    }
                }
                Section("Unresolved reasons · counts overlap; at most eight examples per reason") {
                    ForEach(Array(inventory.reasons.dropFirst(reasonPage * 25).prefix(25))) {reason in
                        DisclosureGroup(reason.reason.replacingOccurrences(of: "_", with: " ").capitalized+" · \(reason.count) unresolved functions") {
                            Text(reason.reason).textSelection(.enabled)
                            if let reviewFindings {
                                Menu("Review Findings in Report…") {
                                    ForEach(inventory.reports) { record in
                                        Button("Report \(record.index + 1) · " + record.image.display_name) { reviewFindings(record.index, reason.reason) }
                                    }
                                }.disabled(busy)
                            }
                            ForEach(reason.examples) {example in
                                VStack(alignment:.leading,spacing:4) {
                                    Text("Report \(example.report_index + 1) · "+(example.function_name ?? example.finding_id)+" · "+example.pc)
                                    Text("Function-entry preferred VM · "+example.scope+" · "+example.mode)
                                    Button("Choose Saved Source Observation…") {openObservation(example,reason.reason)}.disabled(busy)
                                }
                            }
                        }
                    }
                }
            }
            TriagePageControls(page: $reasonPage, count: inventory.reasons.count, size: 25)
            Text("Select an original saved audit report to resolve a reference. Inventory files contain no source path, full observations or original-report byte digest; a match does not authenticate the original export.").foregroundStyle(.secondary)
            Text(status).foregroundStyle(.secondary)
            if !embedded { HStack {Spacer();Button("Done",action:close).keyboardShortcut(.cancelAction).disabled(busy)} }
        }.padding(embedded ? 0 : 24)
        .onChange(of: inventory.reasons.map(\.id)) { _, _ in reasonPage = 0 }
    }
}
