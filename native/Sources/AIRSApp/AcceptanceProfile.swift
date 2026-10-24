import AppKit
import SwiftUI
import AIRSCore
import LumenTokens
import LumenUI

/// App-owned acceptance storage, not an operating-system sandbox. The restricted
/// surface deliberately exposes no file panels, recent documents, or export routes.
struct AcceptanceProfile {
    let root: URL
    let suite: String
    let report: URL
    let comparison: URL

    enum Failure: Error { case invalidArguments, invalidRoot, invalidFixture, usedPreferences }

    static func parse(arguments: [String], environment: [String: String], bundleIdentifier: String?) throws -> Self? {
        guard arguments.contains(where: { $0.hasPrefix("--acceptance-") }) else { return nil }
        guard arguments.count == 7, arguments[1] == "--acceptance-profile",
              arguments[3] == "--acceptance-report", arguments[5] == "--acceptance-comparison",
              bundleIdentifier == "dev.airs.app",
              !environment.keys.contains(where: { $0.hasPrefix("AIRS_SETTINGS_REVIEW") || $0 == "AIRS_COMPARISON_REVIEW_FIXTURE" }) else {
            throw Failure.invalidArguments
        }
        let parent = SettingsReviewConfiguration.reviewParent.standardizedFileURL
        let root = URL(fileURLWithPath: arguments[2], isDirectory: true).standardizedFileURL
        let prefix = "AIRS-acceptance-"
        guard arguments[2].hasPrefix("/"), root.deletingLastPathComponent() == parent,
              root.lastPathComponent.hasPrefix(prefix),
              let id = UUID(uuidString: String(root.lastPathComponent.dropFirst(prefix.count))),
              root.resolvingSymlinksInPath() == root,
              try root.resourceValues(forKeys: [.isDirectoryKey]).isDirectory == true,
              try FileManager.default.contentsOfDirectory(atPath: root.path).isEmpty else { throw Failure.invalidRoot }
        func fixture(_ path: String) throws -> URL {
            let url = URL(fileURLWithPath: path).standardizedFileURL
            guard path.hasPrefix("/"), url.path.hasPrefix(parent.path + "/"),
                  url.resolvingSymlinksInPath() == url,
                  try url.resourceValues(forKeys: [.isRegularFileKey]).isRegularFile == true else { throw Failure.invalidFixture }
            return url
        }
        return try Self(root: root, suite: "dev.airs.acceptance.\(id.uuidString.lowercased())",
                        report: fixture(arguments[4]), comparison: fixture(arguments[6]))
    }

    func prepare() throws -> (UserDefaults, AuditReport, ComparisonDocument) {
        guard let preferences = UserDefaults(suiteName: suite),
              let lumen = UserDefaults(suiteName: suite + ".lumen"),
              preferences.persistentDomain(forName: suite) == nil,
              lumen.persistentDomain(forName: suite + ".lumen") == nil else { throw Failure.usedPreferences }
        // Exclusive creation also rejects a second process racing to use this root.
        let claim = root.appendingPathComponent("profile.json")
        let receipt: [String: Any] = ["profile": suite, "bundle": "dev.airs.app",
            "executable": Bundle.main.executableURL?.path ?? "unknown",
            "storage": root.path, "restoration": false, "systemPanels": false,
            "externalOpenEvents": false, "productionControllers": false]
        try JSONSerialization.data(withJSONObject: receipt, options: [.prettyPrinted, .sortedKeys])
            .write(to: claim, options: .withoutOverwriting)
        let auditData = try ReportFiles.readBounded(report)
        let comparisonData = try ReportFiles.readBounded(comparison)
        let audit = try AuditReport.decode(auditData)
        let diff = try ComparisonReport.decode(comparisonData)
        let inputs = root.appendingPathComponent("Inputs", isDirectory: true)
        try FileManager.default.createDirectory(at: inputs, withIntermediateDirectories: false)
        try auditData.write(to: inputs.appendingPathComponent("audit.json"), options: .withoutOverwriting)
        try comparisonData.write(to: inputs.appendingPathComponent("comparison.json"), options: .withoutOverwriting)
        return (preferences, audit, ComparisonDocument(report: diff, data: comparisonData,
            formattedJSON: try ReportFiles.prettyJSON(comparisonData), protectedInputs: []))
    }
}

@main
@MainActor
enum AIRSEntryPoint {
    static func main() {
        do {
            guard let profile = try AcceptanceProfile.parse(arguments: CommandLine.arguments,
                environment: ProcessInfo.processInfo.environment, bundleIdentifier: Bundle.main.bundleIdentifier) else {
                AIRSApp.main()
                return
            }
            let (preferences, report, comparison) = try profile.prepare()
            let workspace = AuditWorkspace(recents: SettingsReviewRecents(),
                supportRoot: profile.root.appendingPathComponent("data"), preferences: preferences)
            LumenThemeStore.install(LumenThemeStore(registry: LumenRegistry(packs: [.core]),
                configuration: LumenStoreConfiguration(appName: "AIRS",
                    themesDirectory: profile.root.appendingPathComponent("themes"),
                    defaultThemeID: LumenThemes.standardID, defaultsSuiteName: profile.suite + ".lumen")))
            let app = NSApplication.shared
            let delegate = AcceptanceApplicationDelegate()
            app.delegate = delegate
            app.setActivationPolicy(.regular)
            let window = NSWindow(contentRect: NSRect(x: 0, y: 0, width: 1120, height: 800),
                styleMask: [.titled, .closable, .miniaturizable, .resizable], backing: .buffered, defer: false)
            window.title = "AIRS — Isolated acceptance"
            window.isReleasedWhenClosed = false
            window.isRestorable = false
            window.setFrameAutosaveName("")
            window.contentMinSize = NSSize(width: 960, height: 680)
            window.contentViewController = NSHostingController(rootView:
                AcceptanceView(workspace: workspace, report: report, comparison: comparison, profile: profile.suite)
                    .lumenPaletteRoot().lumenMetrics(.standard).lumenDensityRoot()
                    .defaultAppStorage(preferences))
            delegate.window = window
            window.center()
            window.makeKeyAndOrderFront(nil)
            app.activate(ignoringOtherApps: true)
            withExtendedLifetime(delegate) { app.run() }
        } catch {
            // Fail before constructing any normal app controller or scene.
            fputs("AIRS acceptance profile rejected: \(error)\n", stderr)
            exit(64)
        }
    }
}

@MainActor
private final class AcceptanceApplicationDelegate: NSObject, NSApplicationDelegate {
    var window: NSWindow?
    func applicationShouldTerminateAfterLastWindowClosed(_ sender: NSApplication) -> Bool { true }
    func applicationShouldSaveSecureApplicationState(_ app: NSApplication) -> Bool { false }
    func applicationShouldRestoreSecureApplicationState(_ app: NSApplication) -> Bool { false }
    func application(_ application: NSApplication, open urls: [URL]) { /* No external routing in this profile. */ }
}

@MainActor
private struct AcceptanceView: View {
    @ObservedObject var workspace: AuditWorkspace
    let report: AuditReport
    let comparison: ComparisonDocument
    let profile: String
    @State private var showsComparison = false

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                VStack(alignment: .leading) {
                    Text("Isolated acceptance profile").font(.headline)
                    Text("Owned fixtures · no recents, file pickers, exports, or window restoration")
                        .font(.caption).foregroundStyle(.secondary)
                }
                Spacer()
                Button("Baseline comparison") { showsComparison = true }
            }.padding()
            Divider()
            ReportOverviewView(report: report, sourceLabel: "Accepted owned-image fixture")
            Divider()
            Text(profile).font(.caption).foregroundStyle(.secondary).padding(8)
        }
        .sheet(isPresented: $showsComparison) {
            ComparisonView(document: comparison, workspace: workspace, permitsExport: false)
        }
    }
}
