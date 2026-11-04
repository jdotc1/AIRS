import SwiftUI
import AIRSCore
import AIRSEntitlements
import EntitlementDiffCore
struct ComponentPairReview: Identifiable {
    let id = UUID()
    var previous: URL
    var current: URL
    let auditRevision: UUID
    let entitlementRevision: UUID
}
struct ComponentPairView: View {
    let pair: ComponentPairReview
    let swap: () -> Void
    let cancel: () -> Void
    let confirm: (Architecture) -> Void
    @State private var architecture = Architecture.arm64
    var body: some View {
        VStack(alignment:.leading,spacing:16) {
            Text("Compare App Components").font(.title2).bold()
            Text("Previous: " + pair.previous.path).textSelection(.enabled)
            Text("Current: " + pair.current.path).textSelection(.enabled)
            Text("Confirm direction before any component reads. Targets are read as data and never executed.")
            Picker("Requested slice",selection:$architecture) { ForEach(Architecture.allCases,id:\.self) { Text($0.rawValue).tag($0) } }
            HStack { Button("Cancel",action:cancel); Button("Swap",action:swap); Spacer(); Button("Build Review") { confirm(architecture) }.keyboardShortcut(.defaultAction) }
        }.padding(24).frame(width:700)
    }
}
struct ComponentReviewView: View {
    let session: ComponentReviewSession
    let status: String
    let busy: Bool
    let read: (UUID) -> Void
    let capture: (SecurityDeltaSide, UUID) -> Void
    let captureSignature: (SecurityDeltaSide, UUID) -> Void
    let export: () -> Void
    let exportDelta: () -> Void
    let close: () -> Void
    @State private var mode = "Components"
    var body: some View {
        VStack(alignment:.leading,spacing:12) {
            Text("Component Review").font(.title2).bold()
            Text("Previous → Current · Requested slice: " + session.review.architecture.rawValue)
            Text(session.live == nil ? "Imported evidence is unverified and cannot authorize live reads." : "Explicit live selections. Identifier moves remain candidates; only exact-location pairs can request entitlement reads.")
            Text("Previous scope: \(session.review.previous.scope.completion.rawValue) · Current scope: \(session.review.current.scope.completion.rawValue). No whole-app unchanged, compatibility or trust verdict is implied.")
            Picker("Review mode", selection: $mode) { Text("Components").tag("Components"); Text("Security Changes").tag("Security Changes") }.pickerStyle(.segmented)
            if mode == "Components" {
            List(session.review.matching.matches) { match in
                ComponentReviewRow(match:match,previous:session.review.previous.components.first{$0.id == match.previousID},
                    current:session.review.current.components.first{$0.id == match.currentID},differences:session.differences[match.id] ?? [],
                    outcome:session.review.entitlementResults.first{$0.matchID == match.id},availability:ComponentReviewOperations.readAvailability(session,matchID:match.id,busy:busy),
                    canCapture: session.live != nil && !busy, capture: capture, captureSignature: captureSignature, read:{read(match.id)})
            }
            } else { ComponentSecurityDeltaView(session: session) }
            Text(status).foregroundStyle(.secondary)
            Text("The component review archive includes its captured declarations and pair reads. Security Changes export also includes separately captured evidence. Info comparisons use an allowlist; an absent privacy manifest is not a compliance defect.").foregroundStyle(.secondary)
            HStack {
                Button("Export Component Review Archive…",action:export)
                Button("Export Security Changes…",action:exportDelta).disabled(session.securityDeltaArchiveBytes == nil)
                Spacer(); Button("Done",action:close).keyboardShortcut(.cancelAction)
            }.disabled(busy)
            if let reason = session.securityDeltaExportFailure { Text(reason).foregroundStyle(.secondary) }
        }.padding(24).frame(minWidth:800,idealWidth:1000,minHeight:560,idealHeight:700)
    }
}
private struct ComponentReviewRow: View {
    let match: ComponentMatch
    let previous: ComponentRecord?
    let current: ComponentRecord?
    let differences: [DeclarationDifference]
    let outcome: ComponentEntitlementResult?
    let availability: ComponentReadAvailability
    let canCapture: Bool
    let capture: (SecurityDeltaSide, UUID) -> Void
    let captureSignature: (SecurityDeltaSide, UUID) -> Void
    let read: () -> Void
    var body: some View {
        VStack(alignment:.leading,spacing:6) {
            Text("\(previous?.relativePath ?? "Unobserved") → \(current?.relativePath ?? "Unobserved")").font(.headline).textSelection(.enabled)
            Text(match.relation.rawValue + " · " + match.reasons.joined(separator:" "))
            Text("Recorded identifiers: \(previous?.declaredBundleID ?? "unavailable") → \(current?.declaredBundleID ?? "unavailable")").foregroundStyle(.secondary)
            ForEach(differences,id:\.category) { difference in
                VStack(alignment:.leading,spacing:3) {
                    Text(difference.category.rawValue + ": " + (difference.comparison.map { "\($0.changes.count) typed changes" } ?? "unavailable"))
                    Text(difference.message).foregroundStyle(.secondary)
                    if let comparison = difference.comparison {
                        ForEach(Array(comparison.changes.prefix(8))) { change in
                            Text("\(DisplayText.escaped(change.key)): \(change.previous?.preview(maxCharacters:80) ?? "absent") → \(change.current?.preview(maxCharacters:80) ?? "absent")")
                        }
                        if comparison.changes.count > 8 { Text("First 8 shown; complete archive preserves all values.") }
                    }
                }
            }
            if let outcome {
                switch outcome {
                case .unavailable(_,_,let reason): Text("Entitlements unavailable: " + reason).foregroundStyle(.secondary)
                case .compared(_,let architecture,let report):
                    Text("Entitlements \(architecture.rawValue): \(report.changes.count) changes, \(report.unchangedCount) unchanged declarations; no trust verdict.")
                    ForEach(Array(report.changes.prefix(8))) { change in
                        Text("\(DisplayText.escaped(change.key)): \(change.previous?.preview(maxCharacters:80) ?? "absent") → \(change.current?.preview(maxCharacters:80) ?? "absent")")
                    }
                }
            }
            Button("Read Entitlements for Requested Slice",action:read).disabled(!availability.available)
            Text(availability.reason).foregroundStyle(.secondary)
            HStack {
                if let previous { Button("Capture Previous Entitlements") { capture(.previous, previous.id) }.disabled(!canCapture) }
                if let current { Button("Capture Current Entitlements") { capture(.current, current.id) }.disabled(!canCapture) }
            }
            HStack {
                if let previous { Button("Capture Previous Signature Evidence") { captureSignature(.previous, previous.id) }.disabled(!canCapture) }
                if let current { Button("Capture Current Signature Evidence") { captureSignature(.current, current.id) }.disabled(!canCapture) }
            }
        }.padding(.vertical,8)
    }
}
