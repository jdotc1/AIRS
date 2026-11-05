import XCTest
import Darwin
import Foundation
import AIRSCore
import AIRSEntitlements
@testable import AIRSApp

struct RealCorpusCase: Codable {
    let caseID: String
    let previous: String
    let current: String
}
struct RealCorpusDriver: Decodable {
    let cases: [RealCorpusCase]
    let architecture: String?
    let output: String
    static func validate(_ cases: [RealCorpusCase]) throws {
        guard !cases.isEmpty, cases.count <= 64,
              Set(cases.map { Data($0.caseID.utf8) }).count == cases.count,
              cases.allSatisfy({ !$0.caseID.isEmpty && $0.caseID.utf8.count <= 192 &&
                  $0.caseID.utf8.allSatisfy { ($0 == 45 || $0 == 46 || (48...57).contains($0)) || (65...90).contains($0) || (97...122).contains($0) } &&
                  $0.previous.hasPrefix("/") && $0.current.hasPrefix("/") &&
                  $0.previous.utf8.count <= 4096 && $0.current.utf8.count <= 4096 &&
                  !Data($0.previous.utf8).elementsEqual(Data($0.current.utf8)) }) else {
            throw SecurityDeltaRefusal(.invalidReview)
        }
    }
    static func load(_ url: URL) throws -> Self {
        let bytes = try readBounded(url, maximum: 131072)
        guard bytes.count <= 131072 else { throw SecurityDeltaRefusal(.documentSizeLimit) }
        let value = try JSONDecoder().decode(Self.self, from: bytes)
        guard value.architecture == nil || value.architecture == "arm64" else { throw SecurityDeltaRefusal(.sliceUnavailable) }
        try validate(value.cases)
        return value
    }
    static func readBounded(_ url: URL, maximum: Int) throws -> Data {
        var directory = Darwin.open("/", O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
        guard directory >= 0 else { throw SecurityDeltaRefusal(.sourceUnavailable) }
        defer { Darwin.close(directory) }
        let parts = url.path.split(separator: "/").map(String.init)
        guard let name = parts.last else { throw SecurityDeltaRefusal(.invalidReview) }
        for part in parts.dropLast() {
            guard part != ".", part != ".." else { throw SecurityDeltaRefusal(.invalidReview) }
            let child = Darwin.openat(directory, part, O_RDONLY | O_DIRECTORY | O_NOFOLLOW)
            guard child >= 0 else { throw SecurityDeltaRefusal(.sourceUnavailable) }
            Darwin.close(directory); directory = child
        }
        let fd = Darwin.openat(directory, name, O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
        guard fd >= 0 else { throw SecurityDeltaRefusal(.sourceUnavailable) }
        defer { Darwin.close(fd) }
        var before = stat(), after = stat()
        guard fstat(fd, &before) == 0, before.st_mode & S_IFMT == S_IFREG,
              before.st_size <= maximum else { throw SecurityDeltaRefusal(.documentSizeLimit) }
        let handle = FileHandle(fileDescriptor: fd, closeOnDealloc: false)
        var result = Data()
        while result.count <= maximum {
            try Task.checkCancellation()
            let chunk = try handle.read(upToCount: min(65536, maximum + 1 - result.count)) ?? Data()
            if chunk.isEmpty { break }; result.append(chunk)
        }
        guard result.count <= maximum else { throw SecurityDeltaRefusal(.documentSizeLimit) }
        guard fstat(fd, &after) == 0, before.st_size == after.st_size,
              before.st_mtimespec.tv_sec == after.st_mtimespec.tv_sec,
              before.st_mtimespec.tv_nsec == after.st_mtimespec.tv_nsec else { throw SecurityDeltaRefusal(.sourceStale) }
        return result
    }
    static func publish(_ data: Data, to path: URL) throws {
        guard !FileManager.default.fileExists(atPath: path.path) else { throw SecurityDeltaRefusal(.invalidReview) }
        let temporary = path.deletingLastPathComponent().appendingPathComponent(".capture-" + UUID().uuidString)
        try data.write(to: temporary, options: [.withoutOverwriting])
        defer { try? FileManager.default.removeItem(at: temporary) }
        guard Darwin.link(temporary.path, path.path) == 0 else { throw SecurityDeltaRefusal(.invalidReview) }
    }
    private func encode<T: Encodable>(_ value: T) throws -> Data {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        return try encoder.encode(value)
    }
    private func write<T: Encodable>(_ value: T, _ path: URL) throws {
        guard !FileManager.default.fileExists(atPath: path.path) else { throw SecurityDeltaRefusal(.invalidReview) }
        try Self.publish(encode(value), to: path)
    }
    func capture() async throws {
        let root = URL(fileURLWithPath: output, isDirectory: true)
        try FileManager.default.createDirectory(at: root, withIntermediateDirectories: true)
        var results: [[String: String]] = []
        var repetitions = 0
        for item in cases {
            try Task.checkCancellation()
            let start = Date()
            let directory = root.appendingPathComponent(item.caseID, isDirectory: true)
            guard !FileManager.default.fileExists(atPath: directory.path) else { throw SecurityDeltaRefusal(.invalidReview) }
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: false)
            var result = ["case_id": item.caseID]
            do {
                var session = try ComponentReviewOperations.build(URL(fileURLWithPath: item.previous), URL(fileURLWithPath: item.current), .arm64)
                var captureOutcomes: [[String: String]] = []
                // Harness-only explicit selection: at most one primary component on each side.
                // No capture-all action or automatic production behavior is introduced.
                for side in [SecurityDeltaSide.previous, .current] {
                    let inventory = side == .previous ? session.review.previous : session.review.current
                    guard let component = inventory.components.first(where: { $0.kind == "app" }) else { continue }
                    for category in ["entitlements", "signature"] {
                        do {
                            if category == "entitlements" {
                                session = try await ComponentSecurityDeltaOperations.capturingEntitlements(session, side: side, componentID: component.id)
                            } else {
                                session = try ComponentSecurityDeltaOperations.capturingSignature(session, side: side, componentID: component.id)
                            }
                            captureOutcomes.append(["side": side.rawValue, "category": category, "state": "recorded"])
                        } catch is CancellationError { throw CancellationError() }
                        catch { captureOutcomes.append(["side": side.rawValue, "category": category, "state": "refused", "reason": String(describing: type(of: error))]) }
                    }
                }
                try write(captureOutcomes, directory.appendingPathComponent("capture-outcomes.json"))
                let report = try XCTUnwrap(session.securityDeltaReport, session.securityDeltaFailure ?? "No derived report")
                try write(report, directory.appendingPathComponent("report.json"))
                try write(session.review.previous, directory.appendingPathComponent("previous-inventory.json"))
                try write(session.review.current, directory.appendingPathComponent("current-inventory.json"))
                try write(session.review.previousDeclarations, directory.appendingPathComponent("previous-declarations.json"))
                try write(session.review.currentDeclarations, directory.appendingPathComponent("current-declarations.json"))
                try write(session.review.matching, directory.appendingPathComponent("matching.json"))
                for finding in report.findings {
                    XCTAssertFalse(finding.evidence.isEmpty, "Every explanation needs evidence")
                    for reference in finding.evidence { _ = try ComponentSecurityDeltaOperations.resolveEvidence(reference, in: session) }
                    XCTAssertTrue(finding.observationIDs.allSatisfy { session.securityDeltaObservations[$0] != nil })
                }
                let rows = try ComponentSecurityDeltaOperations.filteredRows(session, category: "all", component: "all")
                XCTAssertEqual(rows.observations.flatMap { $0 }.map(\.id), report.observations.map(\.id))
                XCTAssertTrue(rows.observations.allSatisfy { $0.count <= 200 })
                XCTAssertTrue(rows.findings.allSatisfy { $0.count <= 200 })
                let input = SecurityDeltaInput(review: session.review, signatureEvidence: session.signatureEvidence,
                    entitlementEvidence: session.entitlementEvidence, signatureRefusals: session.signatureRefusals)
                // Five distinct retained cases, twenty pure analyses each. No additional live read.
                if repetitions < 100 {
                    let first = try encode(ComponentSecurityDeltaAnalyzer.analyze(input: input))
                    for _ in 0..<20 {
                        XCTAssertEqual(first, try encode(ComponentSecurityDeltaAnalyzer.analyze(input: input)))
                        repetitions += 1
                    }
                }
                if let archive = session.securityDeltaArchiveBytes {
                    try Self.publish(archive, to: directory.appendingPathComponent("historical.json"))
                    result["archive_bytes"] = String(archive.count)
                    result["archive"] = "retained"
                } else { result["archive"] = "refused"; result["archive_reason"] = session.securityDeltaExportFailure ?? "unavailable" }
                result["state"] = "captured"; result["observations"] = String(report.observations.count)
                result["findings"] = String(report.findings.count)
            } catch is CancellationError { throw CancellationError() }
            catch { result["state"] = "refused"; result["reason"] = (error as? SecurityDeltaRefusal)?.code.rawValue ?? String(describing: type(of: error)) }
            result["elapsed_seconds"] = String(Date().timeIntervalSince(start))
            results.append(result)
            print("TRACK_A_CASE \(item.caseID) \(result["state"] ?? "unknown")")
        }
        try write(results, root.appendingPathComponent("capture-ledger.json"))
        try write(["pure_replays": repetitions, "attempted_pairs": cases.count], root.appendingPathComponent("replay-counts.json"))
        XCTAssertEqual(repetitions, 100)
    }
    func replay() throws {
        let root = URL(fileURLWithPath: output, isDirectory: true)
        var results: [[String: String]] = []
        for item in cases {
            let directory = root.appendingPathComponent(item.caseID, isDirectory: true)
            let path = directory.appendingPathComponent("historical.json")
            guard FileManager.default.fileExists(atPath: path.path) else {
                results.append(["case_id": item.caseID, "state": "blocked", "reason": "capture_export_unavailable"]); continue
            }
            let bytes = try Self.readBounded(path, maximum: ComponentSecurityDeltaArchive.maximumBytes)
            let restored = try ComponentSecurityDeltaArchive.decode(bytes)
            XCTAssertEqual(try restored.data(), bytes)
            XCTAssertEqual(try encode(restored.report), try Self.readBounded(directory.appendingPathComponent("report.json"), maximum: ComponentSecurityDeltaArchive.maximumBytes))
            let session = try ComponentReviewSession(review: restored.admittedReview.review, archiveBytes: restored.sourceReviewArchive,
                sourceURLs: [], live: nil, securityDeltaReport: restored.report, entitlementEvidence: restored.entitlementEvidence,
                signatureEvidence: restored.signatureEvidence, signatureRefusals: restored.signatureRefusals, admittedReview: restored.admittedReview)
            for finding in restored.report.findings {
                for reference in finding.evidence { _ = try ComponentSecurityDeltaOperations.resolveEvidence(reference, in: session) }
            }
            if let component = session.review.current.components.first {
                XCTAssertThrowsError(try ComponentSecurityDeltaOperations.capturingSignature(session, side: .current, componentID: component.id))
            }
            results.append(["case_id": item.caseID, "state": "historical_replay_passed"])
        }
        try write(results, root.appendingPathComponent("historical-replay-ledger.json"))
    }
}
