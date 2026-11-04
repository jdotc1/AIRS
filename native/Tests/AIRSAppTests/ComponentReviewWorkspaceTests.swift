import XCTest
import Darwin
import AIRSCore
import AIRSEntitlements
import EntitlementDiffCore
@testable import AIRSApp

private actor SecurityCaptureGate {
    private var continuation: CheckedContinuation<ComponentReviewSession, Never>?
    private var waiter: CheckedContinuation<Void, Never>?
    func capture() async -> ComponentReviewSession {
        await withCheckedContinuation { continuation = $0; waiter?.resume(); waiter = nil }
    }
    func started() async {
        if continuation != nil { return }
        await withCheckedContinuation { waiter = $0 }
    }
    func finish(_ result: ComponentReviewSession) { continuation?.resume(returning: result); continuation = nil }
}
final class ComponentReviewWorkspaceTests: XCTestCase {
    @MainActor
    func testRefusedSecurityExportDoesNotWriteDestinationOrReplaceReport() throws {
        let base = try session()
        let report = try ComponentSecurityDeltaAnalyzer.analyze(review: base.review)
        let refused = try ComponentReviewSession(review: base.review, archiveBytes: base.archiveBytes, sourceURLs: [], live: nil,
            securityDeltaReport: report, securityDeltaExportFailure: "export_size_limit")
        let project = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let root = project.appendingPathComponent(".build/security-delta-export-fixtures/\(UUID())")
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        defer { try? FileManager.default.removeItem(at: root) }
        let destination = root.appendingPathComponent("existing.json"), original = Data("existing destination".utf8)
        try original.write(to: destination)
        let owner = AIRSFileOpen(hasModal: { false }, inventoryWrite: { _, _ in XCTFail("A refused export must not reach the writer") })
        owner.componentReview = refused
        XCTAssertNil(owner.exportInventory(to: destination, audit: AuditWorkspace(), entitlements: EntitlementsWorkspace(), securityDelta: true))
        XCTAssertEqual(owner.status, "export_size_limit")
        XCTAssertEqual(owner.componentReview?.id, refused.id)
        XCTAssertEqual(try Data(contentsOf: destination), original)
    }
    func testDiscoveredLinkAndSpecialFileRemainExcludedInDelta() throws {
        let project = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let root = project.appendingPathComponent(".build/security-delta-exclusion-fixtures/\(UUID())")
        defer { try? FileManager.default.removeItem(at: root) }
        func app(_ name: String) throws -> URL {
            let url = root.appendingPathComponent(name + ".app"), contents = url.appendingPathComponent("Contents")
            try FileManager.default.createDirectory(at: contents.appendingPathComponent("MacOS"), withIntermediateDirectories: true)
            try FileManager.default.createDirectory(at: contents.appendingPathComponent("Helpers"), withIntermediateDirectories: true)
            var image = Data([0xcf, 0xfa, 0xed, 0xfe])
            for word: UInt32 in [0x0100000c, 0, 2, 1, 24, 0, 0, 0x32, 24, 1, 0x000e0000, 0, 0] {
                image.append(contentsOf: (0..<4).map { UInt8(truncatingIfNeeded: word >> ($0 * 8)) })
            }
            try image.write(to: contents.appendingPathComponent("MacOS/Main"))
            try PropertyListSerialization.data(fromPropertyList: ["CFBundleExecutable": "Main", "CFBundleIdentifier": "synthetic"], format: .xml, options: 0)
                .write(to: contents.appendingPathComponent("Info.plist"))
            return url
        }
        let old = try app("Old"), new = try app("New")
        try FileManager.default.copyItem(at: old.appendingPathComponent("Contents/MacOS/Main"), to: old.appendingPathComponent("Contents/Helpers/Child"))
        try FileManager.default.createSymbolicLink(atPath: new.appendingPathComponent("Contents/Helpers/Child").path, withDestinationPath: "missing")
        XCTAssertEqual(mkfifo(new.appendingPathComponent("Contents/Helpers/Special").path, 0o600), 0)
        let session = try ComponentReviewOperations.build(old, new, .arm64)
        let exclusions = session.review.current.scope.exclusions
        XCTAssertTrue(exclusions.contains { $0.contains("Child") })
        XCTAssertTrue(exclusions.contains { $0.contains("Special") })
        let report = try XCTUnwrap(session.securityDeltaReport)
        XCTAssertTrue(report.observations.contains { $0.componentPath == "Contents/Helpers/Child" && $0.disposition == .unresolved })
        XCTAssertFalse(report.observations.contains { $0.componentPath == "Contents/Helpers/Child" && $0.disposition == .observedRemoval })
    }
    func session() throws -> ComponentReviewSession {
        func inventory() -> ComponentInventory { .init(scope:.init(searchedLocations:["Contents/MacOS"],completion:.partial,exclusions:[],issues:["Owned gap"]),components:[.init(relativePath:"Contents/MacOS/Main",kind:"app",architectures:["arm64"])]) }
        let review = try ComponentComparison.review(previous:inventory(),current:inventory(),architecture:.arm64,entitlementResults:[])
        return try .init(review:review,archiveBytes:ComponentReviewArchive.encode(review),sourceURLs:[URL(fileURLWithPath:"/owned/report.airsreview")],live:nil)
    }
    @MainActor
    func testSecurityCaptureCancellationRevisionAndQuitRetainPriorSession() async throws {
        let historical = try session(), review = historical.review
        let live = [LiveComponentInventory(inventory: review.previous, units: [:]), LiveComponentInventory(inventory: review.current, units: [:])]
        let original = try ComponentReviewSession(review: review, archiveBytes: historical.archiveBytes, sourceURLs: [], live: live)
        let replacement = try ComponentReviewSession(review: review, archiveBytes: historical.archiveBytes, sourceURLs: [], live: live)
        for signature in [false, true] {
            for scenario in 0..<3 {
                let gate = SecurityCaptureGate(), audit = AuditWorkspace(), entitlements = EntitlementsWorkspace()
                let owner = AIRSFileOpen(hasModal: { false }, componentEntitlementCapture: { _, _, _ in await gate.capture() },
                                         componentSignatureCapture: { _, _, _ in await gate.capture() })
                owner.componentReview = original
                let id = review.previous.components[0].id
                let task = try XCTUnwrap(signature ? owner.captureComponentSecuritySignature(.previous, componentID: id, audit: audit, entitlements: entitlements) :
                    owner.captureComponentSecurityEntitlements(.previous, componentID: id, audit: audit, entitlements: entitlements))
                await gate.started()
                var quit: Task<Bool, Never>?
                if scenario == 0 { owner.cancel() }
                else if scenario == 1 { entitlements.model.loadExample() }
                else {
                    quit = Task { await owner.finishBeforeQuit() }
                    while !owner.isTerminating { await Task.yield() }
                }
                XCTAssertTrue(owner.isBusy, "The owned operation must settle before controls resume")
                XCTAssertEqual(owner.componentReview?.id, original.id)
                await gate.finish(replacement)
                await task.value
                XCTAssertNotEqual(owner.componentReview?.id, replacement.id, "Late capture must never be published")
                if let quit { let settled = await quit.value; XCTAssertTrue(settled) }
                if scenario == 2 { XCTAssertNil(owner.componentReview, "Successful Quit closes the owned review after settlement") }
                else { XCTAssertEqual(owner.componentReview?.id, original.id) }
                XCTAssertFalse(owner.isBusy)
            }
        }
    }
    func testReadAvailabilityRequiresLivePairCapabilitiesAndRequestedSlice() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("AIRS-availability-\(UUID())")
        defer { try? FileManager.default.removeItem(at:root) }
        func app(_ name: String, workerCPU: UInt32) throws -> URL {
            let app = root.appendingPathComponent(name + ".app")
            for (container, executable, cpu) in [("", "Main", UInt32(0x0100000c)), ("Contents/XPCServices/Worker.xpc/", "Worker", workerCPU)] {
                let contents = app.appendingPathComponent(container + "Contents")
                try FileManager.default.createDirectory(at:contents.appendingPathComponent("MacOS"),withIntermediateDirectories:true)
                var image = Data([0xcf,0xfa,0xed,0xfe])
                for word: UInt32 in [cpu, cpu == 0x01000007 ? 3 : 0, 2, 1, 24, 0, 0, 0x32, 24, 1, 0x000e0000, 0, 0] {
                    image.append(contentsOf:(0..<4).map { UInt8(truncatingIfNeeded:word >> ($0 * 8)) })
                }
                try image.write(to:contents.appendingPathComponent("MacOS/" + executable))
                try PropertyListSerialization.data(fromPropertyList:["CFBundleExecutable":executable,"CFBundleIdentifier":"owned." + executable,"CFBundleVersion":"1"],format:.xml,options:0).write(to:contents.appendingPathComponent("Info.plist"))
            }
            return app
        }
        let previous = try app("Previous",workerCPU:0x0100000c), current = try app("Current",workerCPU:0x01000007)
        let value = try ComponentReviewOperations.build(previous,current,.arm64)
        let main = try XCTUnwrap(value.review.matching.matches.first { match in
            value.review.previous.components.first { $0.id == match.previousID }?.kind == "app"
        })
        let ready = ComponentReviewOperations.readAvailability(value, matchID: main.id)
        XCTAssertTrue(ready.available)
        XCTAssertTrue(ready.reason.contains("arm64"))
        XCTAssertFalse(ComponentReviewOperations.readAvailability(value, matchID: main.id, busy: true).available)
        XCTAssertFalse(ComponentReviewOperations.readAvailability(value, matchID: UUID()).available)
        func session(_ live: [LiveComponentInventory]?) throws -> ComponentReviewSession {
            try .init(review:value.review,archiveBytes:value.archiveBytes,sourceURLs:value.sourceURLs,live:live)
        }
        for previousMissing in [true,false] {
            let broken = ComponentMatch(id:main.id,previousID:previousMissing ? nil : main.previousID,currentID:previousMissing ? main.currentID : nil,relation:.sameLocation,reasons:[])
            let review = ComponentReview(previous:value.review.previous,current:value.review.current,
                matching:.init(matches:[broken],previousScope:value.review.previous.scope,currentScope:value.review.current.scope),
                architecture:.arm64,entitlementResults:[],previousDeclarations:[],currentDeclarations:[])
            let malformed = try ComponentReviewSession(review:review,archiveBytes:value.archiveBytes,sourceURLs:value.sourceURLs,live:value.live)
            XCTAssertTrue(ComponentReviewOperations.readAvailability(malformed,matchID:main.id).reason.contains("identities"))
        }
        let imported = try session(nil)
        XCTAssertTrue(ComponentReviewOperations.readAvailability(imported,matchID:main.id).reason.contains("Imported"))
        let live = try XCTUnwrap(value.live)
        XCTAssertFalse(ComponentReviewOperations.readAvailability(try session([live[0]]),matchID:main.id).available)
        let missingPrevious = LiveComponentInventory(inventory:live[0].inventory,units:[:])
        let missingCurrent = LiveComponentInventory(inventory:live[1].inventory,units:[:])
        for capabilities in [[missingPrevious,live[1]], [live[0],missingCurrent]] {
            let unavailable = try session(capabilities)
            XCTAssertTrue(ComponentReviewOperations.readAvailability(unavailable,matchID:main.id).reason.contains("capability"))
            do { _ = try await ComponentReviewOperations.read(unavailable,matchID:main.id,reader:ForbiddenUnitReader()); XCTFail("Missing capability must refuse") } catch {}
        }
        let worker = try XCTUnwrap(value.review.matching.matches.first { match in
            value.review.previous.components.first { $0.id == match.previousID }?.relativePath.contains("Worker") == true
        })
        let unsupported = ComponentReviewOperations.readAvailability(value,matchID:worker.id)
        XCTAssertFalse(unsupported.available)
        XCTAssertTrue(unsupported.reason.contains("arm64"))
        let updated = try await ComponentReviewOperations.read(value,matchID:worker.id,reader:ForbiddenUnitReader())
        guard case .unavailable(_,let architecture,let reason) = updated.review.entitlementResults.first(where: { $0.matchID == worker.id }) else { return XCTFail("Missing slice remains explicit unavailable evidence") }
        XCTAssertEqual(architecture,.arm64)
        XCTAssertEqual(reason,unsupported.reason)
        let archive = try InspectionArchive.decode(updated.archiveBytes)
        let attachment = try XCTUnwrap(archive.attachments.first { $0.kind == ComponentReviewArchive.kind })
        guard case .componentReview(let reopened) = try AIRSOpenedReport.attachment(archive,id:attachment.id) else { return XCTFail("Archive route") }
        XCTAssertEqual(reopened.entitlementResults.count,value.review.matching.matches.count)
        guard case .unavailable(_,_,let reopenedReason) = reopened.entitlementResults.first(where: { $0.matchID == worker.id }) else { return XCTFail("Missing slice result survived archive") }
        XCTAssertEqual(reopenedReason,unsupported.reason)
        for match in value.review.matching.matches where match.relation != .sameLocation {
            XCTAssertFalse(ComponentReviewOperations.readAvailability(value,matchID:match.id).available)
        }
    }

    @MainActor
    func testPairJobStagesWithoutReplacingSessionsAndRejectsStaleResults() async throws {
        let session = try session(), audit = AuditWorkspace(), entitlements = EntitlementsWorkspace()
        let owner = AIRSFileOpen(hasModal:{false}, componentBuild:{ _,_,_ in session })
        let before = audit.reportRevision
        await owner.compareComponents(previous:URL(fileURLWithPath:"/owned/A.app"),current:URL(fileURLWithPath:"/owned/B.app"),architecture:.arm64,audit:audit,entitlements:entitlements)?.value
        XCTAssertNotNil(owner.componentReview)
        XCTAssertEqual(audit.reportRevision,before)
        owner.closeComponentReview()
        let task = try XCTUnwrap(owner.compareComponents(previous:URL(fileURLWithPath:"/owned/A.app"),current:URL(fileURLWithPath:"/owned/B.app"),architecture:.arm64,audit:audit,entitlements:entitlements))
        entitlements.model.loadExample()
        await task.value
        XCTAssertNil(owner.componentReview)
    }
    @MainActor
    func testPairConfirmationDefersBuildUntilSheetDismissal() async throws {
        let value = try session(), audit = AuditWorkspace(), entitlements = EntitlementsWorkspace()
        var modal = true
        let owner = AIRSFileOpen(hasModal:{modal},componentBuild:{_,_,_ in value})
        owner.componentPairReview = .init(previous:URL(fileURLWithPath:"/owned/A.app"),current:URL(fileURLWithPath:"/owned/B.app"),auditRevision:audit.reportRevision,entitlementRevision:entitlements.model.reportRevision)
        owner.confirmComponentPair(.arm64,audit:audit,entitlements:entitlements)
        XCTAssertNil(owner.componentPairReview)
        XCTAssertNil(owner.componentReview)
        // AppKit may still expose the dismissing owned sheet in onDismiss.
        await owner.componentPairDismissed(audit:audit,entitlements:entitlements)?.value
        modal = false
        XCTAssertNotNil(owner.componentReview)
    }
    func testMetadataChangedAfterBuildRequiresRebuildBeforeEntitlementJoin() async throws {
        let root = FileManager.default.temporaryDirectory.appendingPathComponent("AIRS-source-tests/\(UUID())/AIRS-component-review-20261020/stale-info/\(UUID())")
        defer { try? FileManager.default.removeItem(at:root) }
        let project = URL(fileURLWithPath:#filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        func app(_ name:String) throws -> URL {
            let url = root.appendingPathComponent(name + ".app")
            try FileManager.default.createDirectory(at:url.appendingPathComponent("Contents/MacOS"),withIntermediateDirectories:true)
            try FileManager.default.copyItem(at:project.appendingPathComponent("fixtures/generated/before.macho"),to:url.appendingPathComponent("Contents/MacOS/Main"))
            try PropertyListSerialization.data(fromPropertyList:["CFBundleExecutable":"Main","CFBundleIdentifier":"owned","CFBundleShortVersionString":"1.0","CFBundleVersion":"1"],format:.xml,options:0).write(to:url.appendingPathComponent("Contents/Info.plist"))
            return url
        }
        let a = try app("A"), b = try app("B"), session = try ComponentReviewOperations.build(a,b,.arm64)
        let info = a.appendingPathComponent("Contents/Info.plist")
        var plist = try XCTUnwrap(PropertyListSerialization.propertyList(from:Data(contentsOf:info),format:nil) as? [String:Any])
        plist["CFBundleVersion"] = "2"
        try PropertyListSerialization.data(fromPropertyList:plist,format:.xml,options:0).write(to:info)
        let updated = try await ComponentReviewOperations.read(session,matchID:session.review.matching.matches[0].id,reader:OwnedUnitReader())
        guard case .unavailable(_,_,let reason) = updated.review.entitlementResults[0] else { return XCTFail("Changed metadata must not join old capture") }
        XCTAssertTrue(reason.contains("rebuild"))
    }
    func testMissingPrincipalReviewRetainsRootDeclarationsThroughArchiveWithoutLiveAuthority() async throws {
        let project = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let root = project.appendingPathComponent("build/rea5589/review-fixtures/\(UUID())")
        defer { try? FileManager.default.removeItem(at: root) }
        func app(_ name: String) throws -> URL {
            let url = root.appendingPathComponent(name + ".app")
            try FileManager.default.createDirectory(at: url.appendingPathComponent("Contents/Resources"), withIntermediateDirectories: true)
            try PropertyListSerialization.data(fromPropertyList: ["CFBundleIdentifier": "owned.resources", "CFBundleShortVersionString": "1.0"], format: .xml, options: 0).write(to: url.appendingPathComponent("Contents/Info.plist"))
            try PropertyListSerialization.data(fromPropertyList: ["NSPrivacyTracking": false], format: .xml, options: 0).write(to: url.appendingPathComponent("Contents/Resources/PrivacyInfo.xcprivacy"))
            return url
        }
        let session = try ComponentReviewOperations.build(app("A"), app("B"), .arm64)
        let id = try XCTUnwrap(session.review.previous.components.first?.id)
        XCTAssertEqual(session.review.previous.components.count, 1)
        XCTAssertTrue(session.live?[0].units.isEmpty == true)
        let match = try XCTUnwrap(session.review.matching.matches.first)
        XCTAssertEqual(match.relation, .sameLocation)
        let availability = ComponentReviewOperations.readAvailability(session, matchID: match.id)
        XCTAssertFalse(availability.available)
        XCTAssertTrue(availability.reason.contains("live discovered file capability"))
        XCTAssertEqual(session.review.previousDeclarations.first { $0.componentID == id && $0.category == .info }?.state, .present)
        XCTAssertEqual(session.review.previousDeclarations.first { $0.componentID == id && $0.category == .privacy }?.state, .present)
        XCTAssertEqual(session.review.previousDeclarations.first { $0.componentID == id && $0.category == .loadCommands }?.state, .unavailable)
        let archive = try InspectionArchive.decode(session.archiveBytes)
        let attachment = try XCTUnwrap(archive.attachments.first { $0.kind == ComponentReviewArchive.kind })
        guard case .componentReview(let value) = try AIRSOpenedReport.attachment(archive, id: attachment.id) else { return XCTFail("Review route") }
        XCTAssertEqual(value.previousDeclarations.first { $0.componentID == id && $0.category == .info }?.bytes, session.review.previousDeclarations.first { $0.componentID == id && $0.category == .info }?.bytes)
        do { _ = try await ComponentReviewOperations.read(session, matchID: match.id, reader: ForbiddenUnitReader()); XCTFail("Declaration record cannot authorize entitlement reads") }
        catch AIRSCore.ReportError.invalidContents(let reason) { XCTAssertEqual(reason, availability.reason) }
    }
    func testImportedReviewCannotAuthorizeLiveReadsAndArchiveSelectsReview() async throws {
        let session = try session()
        do { _ = try await ComponentReviewOperations.read(session,matchID:session.review.matching.matches[0].id); XCTFail("No live capability") } catch {}
        let archive = try InspectionArchive.decode(session.archiveBytes)
        let id = try XCTUnwrap(archive.attachments.first { $0.kind == ComponentReviewArchive.kind }?.id)
        guard case .componentReview(let value) = try AIRSOpenedReport.attachment(archive,id:id) else { return XCTFail("Review route") }
        XCTAssertEqual(value.previous.id,session.review.previous.id)
    }
    func testHistoricalSessionCannotCaptureStrictEntitlements() async throws {
        let historical = try session()
        do {
            _ = try await ComponentSecurityDeltaOperations.captureEntitlements(historical, side: .previous,
                componentID: historical.review.previous.components[0].id, reader: ForbiddenUnitReader())
            XCTFail("A historical review must not authorize acquisition")
        } catch { XCTAssertTrue(error is AIRSCore.ReportError) }
        XCTAssertThrowsError(try ComponentSecurityDeltaOperations.capturingSignature(historical, side: .previous,
            componentID: historical.review.previous.components[0].id))
    }
    func testDerivedHistoricalSessionRetainsSourceAndHasNoLiveAuthority() throws {
        let historical = try session()
        let derived = try ComponentSecurityDeltaOperations.derive(historical)
        XCTAssertEqual(derived.archiveBytes, historical.archiveBytes)
        XCTAssertNil(derived.live)
        XCTAssertNotNil(derived.securityDeltaReport)
        XCTAssertNil(derived.securityDeltaFailure)
    }
    func testDeltaExportIsRoutedByDocumentKind() throws {
        let token = try ComponentReviewArchive.capture(session().review)
        let document = try ComponentSecurityDeltaArchive.create(admittedReview: token)
        let bytes = try document.data()
        guard case .securityDelta(let restored, let original) = try AIRSOpenedReport.parse(bytes) else { return XCTFail("Security delta route") }
        XCTAssertEqual(original, bytes)
        XCTAssertEqual(restored.sourceReviewArchive, token.sourceArchive)
        XCTAssertEqual(restored.report.identity.evidenceBasisID, document.report.identity.evidenceBasisID)
    }
    func testDependencyEvidenceResolvesAllRecordedDuplicateRows() throws {
        func inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])])
        }
        let a = inventory(), b = inventory()
        func loader(_ component: ComponentRecord, count: Int) throws -> DeclarationObservation {
            let row: [String: Any] = ["architecture": "arm64", "command": "load", "path": "@rpath/Example.dylib"]
            return .init(componentID: component.id, category: .loadCommands, architecture: "arm64", relativeSource: component.relativePath,
                state: .present, bytes: try PropertyListSerialization.data(fromPropertyList: ["commands": Array(repeating: row, count: count)], format: .binary, options: 0))
        }
        let old = try loader(a.components[0], count: 2), new = try loader(b.components[0], count: 1)
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [], previousDeclarations: [old], currentDeclarations: [new])
        let session = try ComponentSecurityDeltaOperations.derive(.init(review: review, archiveBytes: ComponentReviewArchive.encode(review), sourceURLs: [], live: nil))
        let observation = try XCTUnwrap(session.securityDeltaReport?.observations.first { $0.subject.hasPrefix("dependency:load:") })
        let reference = try XCTUnwrap(observation.evidence.first { $0.side == .previous })
        let content = try ComponentSecurityDeltaOperations.resolveEvidence(reference, in: session)
        guard case .array(let rows)? = content.value else { return XCTFail("Expected full recorded dependency group") }
        XCTAssertEqual(rows.count, 2)
        XCTAssertEqual(content.sourceBytes, old.bytes)
    }
    func testFiltersUseExactComponentBytesAndDoNotChangeReport() throws {
        let composed = "Contents/Helpers/é", decomposed = "Contents/Helpers/e\u{301}"
        let scope = InventoryScope(searchedLocations: ["Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: [])
        let a = ComponentInventory(scope: scope, components: [])
        let b = ComponentInventory(scope: scope, components: [
            .init(relativePath: composed, kind: "helper", architectures: ["arm64"]),
            .init(relativePath: decomposed, kind: "helper", architectures: ["arm64"])])
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let session = try ComponentSecurityDeltaOperations.derive(.init(review: review, archiveBytes: ComponentReviewArchive.encode(review), sourceURLs: [], live: nil))
        let before = try XCTUnwrap(session.securityDeltaReport).identity.evidenceBasisID
        let rows = try ComponentSecurityDeltaOperations.filteredRows(session, category: SecurityDeltaCategory.componentInventory.rawValue,
            component: Data(composed.utf8).base64EncodedString())
        XCTAssertFalse(rows.observations.flatMap { $0 }.isEmpty)
        XCTAssertTrue(rows.observations.flatMap { $0 }.allSatisfy { $0.componentPath.utf8.elementsEqual(composed.utf8) })
        XCTAssertEqual(session.securityDeltaReport?.identity.evidenceBasisID, before)
    }
    func testLegacyEntitlementSourceResolvesWithoutReopeningArchive() throws {
        func inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])])
        }
        let a = inventory(), b = inventory(), match = try XCTUnwrap(ComponentMatcher.match(previous: a, current: b).matches.first)
        func snapshot(_ id: UUID, _ value: Int64) -> EntitlementSnapshot {
            .init(sourceName: ComponentComparison.sourceName(componentID: id), signingIdentifier: "owned", architecture: .arm64, entitlements: .init(["key": .integer(value)]))
        }
        let comparison = try ComparisonReport(previous: snapshot(a.components[0].id, 1), current: snapshot(b.components[0].id, 2))
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: comparison)])
        let token = try ComponentReviewArchive.capture(review)
        let session = try ComponentSecurityDeltaOperations.derive(.init(review: token.review, archiveBytes: token.sourceArchive, sourceURLs: [], live: nil, admittedReview: token))
        let observation = try XCTUnwrap(session.securityDeltaReport?.observations.first { $0.category == .entitlements && $0.subject == "key:key" })
        let content = try ComponentSecurityDeltaOperations.resolveEvidence(XCTUnwrap(observation.evidence.first), in: session)
        XCTAssertEqual(content.sourceBytes, token.entitlementSource(matchID: match.id))
        guard case .normalizedInteger("1")? = content.value else { return XCTFail("Legacy numeric representation must remain unspecified") }
    }
    func testExplicitStrictCaptureRejectsChangedInfo() async throws {
        let project = URL(fileURLWithPath: #filePath).deletingLastPathComponent().deletingLastPathComponent().deletingLastPathComponent()
        let root = project.appendingPathComponent(".build/security-delta-fixtures/\(UUID())")
        defer { try? FileManager.default.removeItem(at: root) }
        func app(_ name: String) throws -> URL {
            let app = root.appendingPathComponent(name + ".app"), contents = app.appendingPathComponent("Contents")
            try FileManager.default.createDirectory(at: contents.appendingPathComponent("MacOS"), withIntermediateDirectories: true)
            var image = Data([0xcf, 0xfa, 0xed, 0xfe])
            for word: UInt32 in [0x0100000c, 0, 2, 1, 24, 0, 0, 0x32, 24, 1, 0x000e0000, 0, 0] {
                image.append(contentsOf: (0..<4).map { UInt8(truncatingIfNeeded: word >> ($0 * 8)) })
            }
            try image.write(to: contents.appendingPathComponent("MacOS/Main"))
            try FileManager.default.createDirectory(at: contents.appendingPathComponent("Helpers"), withIntermediateDirectories: true)
            try image.write(to: contents.appendingPathComponent("Helpers/Helper"))
            try PropertyListSerialization.data(fromPropertyList: ["CFBundleExecutable": "Main", "CFBundleIdentifier": "owned", "CFBundleVersion": "1"],
                format: .xml, options: 0).write(to: contents.appendingPathComponent("Info.plist"))
            return app
        }
        let a = try app("A"), b = try app("B"), session = try ComponentReviewOperations.build(a, b, .arm64)
        let helper = try XCTUnwrap(session.review.previous.components.first { $0.relativePath == "Contents/Helpers/Helper" })
        let helperCapture = try ComponentSecurityDeltaOperations.capturingSignature(session, side: .previous, componentID: helper.id)
        XCTAssertEqual(helperCapture.signatureEvidence.first?.document.evidence.componentID, helper.id)
        XCTAssertTrue(helperCapture.signatureRefusals.isEmpty)
        let component = try XCTUnwrap(session.review.previous.components.first { $0.relativePath == "Contents/MacOS/Main" })
        let initial = try XCTUnwrap(session.securityDeltaReport?.observations.first { $0.category == .entitlements && $0.subject == "presence" })
        XCTAssertEqual(initial.previousState, .unexamined)
        XCTAssertEqual(initial.currentState, .unexamined)
        XCTAssertTrue(initial.limitations.contains { $0.code == "category_unexamined" })
        let captured = try await ComponentSecurityDeltaOperations.captureEntitlements(session, side: .previous, componentID: component.id, reader: ExposedSyntheticReader())
        XCTAssertEqual(captured.state, .observed)
        do {
            _ = try await ComponentSecurityDeltaOperations.captureEntitlements(session, side: .previous, componentID: component.id, reader: DeepSyntheticReader())
            XCTFail("A typed resource refusal must not become an unavailable acquisition")
        } catch { XCTAssertEqual((error as? SecurityDeltaRefusal)?.code, .typedDepthLimit) }
        do {
            _ = try await ComponentSecurityDeltaOperations.captureEntitlements(session, side: .previous, componentID: component.id, reader: BudgetSyntheticReader())
            XCTFail("A decoder budget failure must not become source unavailable")
        } catch { XCTAssertEqual((error as? SecurityDeltaRefusal)?.code, .resourceLimit) }
        XCTAssertThrowsError(try ComponentSecurityDeltaOperations.capturingSignature(session, side: .previous, componentID: component.id,
            capture: { _, _, _, _ in throw CodeSignatureEvidenceError.budgetExceeded })) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .resourceLimit)
        }
        let capacityLimited = try ComponentReviewSession(review: session.review, archiveBytes: Data(repeating: 0, count: 25 * 1_048_576),
            sourceURLs: session.sourceURLs, live: session.live, entitlementEvidence: session.entitlementEvidence)
        do {
            _ = try await ComponentSecurityDeltaOperations.capturingEntitlements(capacityLimited, side: .previous, componentID: component.id, reader: ForbiddenUnitReader())
            XCTFail("A capture exceeding the conservative reserve must refuse before reading")
        } catch { XCTAssertEqual(error as? InspectionArchiveError, .limit) }
        let revised = try await ComponentSecurityDeltaOperations.capturingEntitlements(session, side: .previous, componentID: component.id, reader: ExposedSyntheticReader())
        XCTAssertTrue(session.entitlementEvidence.allSatisfy { $0.state == .unexamined })
        XCTAssertEqual(revised.entitlementEvidence.filter { $0.state == .observed }.count, 1)
        XCTAssertNotEqual(revised.securityDeltaReport?.identity.evidenceBasisID, session.securityDeltaReport?.identity.evidenceBasisID)
        XCTAssertEqual(revised.archiveBytes, session.archiveBytes)
        let repeatedRefusal = try SecurityDeltaSignatureRefusal.record(side: .previous, inventoryID: session.review.previous.id, componentID: component.id,
            relativePath: component.relativePath, architecture: .arm64, code: "source_stale", capturedAt: Date(timeIntervalSince1970: 0))
        let full = try ComponentReviewSession(review: session.review, archiveBytes: session.archiveBytes, sourceURLs: session.sourceURLs, live: session.live,
            entitlementEvidence: Array(repeating: captured, count: 128), signatureRefusals: Array(repeating: repeatedRefusal, count: 125), admittedReview: session.admittedReview)
        let match = try XCTUnwrap(session.review.matching.matches.first { $0.previousID == component.id })
        do { _ = try await ComponentReviewOperations.read(full, matchID: match.id, reader: ForbiddenUnitReader()); XCTFail("Pair read must preflight the source-record cap") }
        catch { XCTAssertEqual(error as? InspectionArchiveError, .limit) }
        let oversized = try await ComponentReviewOperations.read(session, matchID: match.id, reader: OversizedSyntheticReader())
        guard case .unavailable(_, _, let oversizedReason) = oversized.review.entitlementResults.first(where: { $0.matchID == match.id }) else {
            return XCTFail("Oversized pair must be recorded as unavailable")
        }
        XCTAssertTrue(oversizedReason.contains("retained_byte_limit"))
        let malformedRefusal = try SecurityDeltaSignatureRefusal.record(side: .previous, inventoryID: UUID(), componentID: component.id,
            relativePath: component.relativePath, architecture: .arm64, code: "source_stale", capturedAt: Date(timeIntervalSince1970: 0))
        let broken = try ComponentReviewSession(review: session.review, archiveBytes: session.archiveBytes, sourceURLs: session.sourceURLs,
            live: session.live, signatureRefusals: [malformedRefusal], admittedReview: session.admittedReview)
        let preserved = try await ComponentSecurityDeltaOperations.capturingEntitlements(broken, side: .previous, componentID: component.id, reader: ExposedSyntheticReader())
        XCTAssertEqual(preserved.entitlementEvidence.count, 1)
        XCTAssertNil(preserved.securityDeltaReport)
        XCTAssertNotNil(preserved.securityDeltaFailure)
        do {
            _ = try await ComponentSecurityDeltaOperations.capturingEntitlements(preserved, side: .previous, componentID: component.id, reader: ForbiddenUnitReader())
            XCTFail("A failed derivation must not discard capture or allow a silent retry")
        } catch {}
        let signed = try ComponentSecurityDeltaOperations.capturingSignature(session, side: .previous, componentID: component.id)
        XCTAssertEqual(signed.signatureEvidence.count, 1)
        XCTAssertEqual(signed.signatureEvidence.first?.inventoryID, session.review.previous.id)
        XCTAssertNotNil(signed.securityDeltaArchiveBytes)
        let currentComponent = try XCTUnwrap(session.review.current.components.first)
        let signedPair = try ComponentSecurityDeltaOperations.capturingSignature(signed, side: .current, componentID: currentComponent.id)
        let signatureState = try XCTUnwrap(signedPair.securityDeltaReport?.observations.first { $0.category == .signatureEvidence && $0.subject == "signatureState" })
        for reference in signatureState.evidence { XCTAssertNoThrow(try ComponentSecurityDeltaOperations.resolveEvidence(reference, in: signedPair)) }
        let unknown = SecurityDeltaEvidenceReference(side: .previous, inventoryID: session.review.previous.id, componentID: component.id,
            category: .signatureEvidence, relativeSource: component.relativePath, evidenceKey: "signature:unknown")
        XCTAssertThrowsError(try ComponentSecurityDeltaOperations.resolveEvidence(unknown, in: signed))
        let bogusInventory = SecurityDeltaEvidenceReference(side: .previous, inventoryID: session.review.previous.id, componentID: component.id,
            category: .componentInventory, relativeSource: component.relativePath, evidenceKey: "unknown")
        XCTAssertThrowsError(try ComponentSecurityDeltaOperations.resolveEvidence(bogusInventory, in: signed))
        let missingStrict = SecurityDeltaEvidenceReference(side: .current, inventoryID: session.review.current.id,
            componentID: session.review.current.components[0].id, category: .entitlements,
            relativeSource: session.review.current.components[0].relativePath, architecture: "arm64", evidenceKey: "strict-entitlement:unknown")
        XCTAssertThrowsError(try ComponentSecurityDeltaOperations.resolveEvidence(missingStrict, in: signed))
        let live = try XCTUnwrap(session.live), other = try XCTUnwrap(session.review.current.components.first { $0.relativePath == "Contents/MacOS/Main" })
        let foreign = try XCTUnwrap(live[1].units[other.id])
        let mixed = LiveComponentInventory(inventory: live[0].inventory, units: [component.id: foreign])
        let forged = try ComponentReviewSession(review: session.review, archiveBytes: session.archiveBytes, sourceURLs: session.sourceURLs, live: [mixed, live[1]])
        let rejected = try await ComponentSecurityDeltaOperations.captureEntitlements(forged, side: .previous, componentID: component.id, reader: ForbiddenUnitReader())
        XCTAssertEqual(rejected.state, .unavailable)
        XCTAssertEqual(rejected.reason, "evidence_binding_mismatch")
        let currentImage = b.appendingPathComponent("Contents/MacOS/Main")
        let handle = try FileHandle(forWritingTo: currentImage)
        try handle.seekToEnd(); try handle.write(contentsOf: Data([0])); try handle.close()
        let changedImage = try await ComponentSecurityDeltaOperations.captureEntitlements(session, side: .current, componentID: other.id, reader: ForbiddenUnitReader())
        XCTAssertEqual(changedImage.state, .unavailable)
        XCTAssertNil(changedImage.values)
        let info = a.appendingPathComponent("Contents/Info.plist")
        try PropertyListSerialization.data(fromPropertyList: ["CFBundleExecutable": "Main", "CFBundleIdentifier": "owned", "CFBundleVersion": "2"],
            format: .xml, options: 0).write(to: info)
        let stale = try await ComponentSecurityDeltaOperations.captureEntitlements(session, side: .previous, componentID: component.id, reader: ForbiddenUnitReader())
        XCTAssertEqual(stale.state, .unavailable)
        XCTAssertEqual(stale.reason, "source_stale")
        let refusedSignature = try ComponentSecurityDeltaOperations.capturingSignature(session, side: .previous, componentID: component.id)
        XCTAssertEqual(refusedSignature.signatureRefusals.first?.code, "source_stale")
        XCTAssertTrue(refusedSignature.signatureEvidence.isEmpty)
        XCTAssertThrowsError(try ComponentSecurityDeltaOperations.capturingSignature(signed, side: .previous, componentID: component.id))
    }
}

private struct OwnedUnitReader: CodeUnitSnapshotReading {
    func read(unit:BundleImageProvenance,architecture:Architecture) async throws -> EntitlementSnapshot {
        .init(sourceName:unit.relativePath,signingIdentifier:"owned",architecture:architecture,presence:.dictionaryPresent,entitlements:.init())
    }
}

private struct ForbiddenUnitReader: CodeUnitSnapshotReading {
    func read(unit:BundleImageProvenance,architecture:Architecture) async throws -> EntitlementSnapshot {
        XCTFail("Availability refusal must precede extraction")
        throw InspectionArchiveError.invalid
    }
}
private struct ExposedSyntheticReader: CodeUnitSnapshotReading {
    func read(unit: BundleImageProvenance, architecture: Architecture) async throws -> EntitlementSnapshot {
        .init(sourceName: "Main", signingIdentifier: "owned", architecture: architecture,
            entitlements: .init(["flag": .boolean(true)]), numericRepresentation: .exposed)
    }
}
private struct DeepSyntheticReader: CodeUnitSnapshotReading {
    func read(unit: BundleImageProvenance, architecture: Architecture) async throws -> EntitlementSnapshot {
        var value = EntitlementValue.boolean(true)
        for _ in 0..<34 { value = .array([value]) }
        return .init(sourceName: "Main", signingIdentifier: "owned", architecture: architecture,
                     entitlements: .init(["deep": value]), numericRepresentation: .exposed)
    }
}
private struct BudgetSyntheticReader: CodeUnitSnapshotReading {
    func read(unit: BundleImageProvenance, architecture: Architecture) async throws -> EntitlementSnapshot {
        throw EntitlementDataError.limitExceeded("synthetic")
    }
}
private struct OversizedSyntheticReader: CodeUnitSnapshotReading {
    func read(unit: BundleImageProvenance, architecture: Architecture) async throws -> EntitlementSnapshot {
        .init(sourceName: "Main", signingIdentifier: "owned", architecture: architecture,
            entitlements: .init(["large": .string(String(repeating: "x", count: 4_300_000))]))
    }
}
