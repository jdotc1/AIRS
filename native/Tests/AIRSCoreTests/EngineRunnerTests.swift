import Foundation
import Darwin
import XCTest
@testable import AIRSCore

/// These tests execute only a temporary test-owned Python script, never a target image.
final class EngineRunnerTests: XCTestCase {
    func testManualPairArgumentsAreCanonicalAndSnapshotsAreStaged() async throws {
        let fixture = try TestEngine(script: """
        import json, pathlib, sys
        args = sys.argv[1:]
        old = pathlib.Path(args[args.index('--baseline') + 1]).read_text()
        new = pathlib.Path(args[args.index('--current') + 1]).read_text()
        pathlib.Path(args[args.index('--output') + 1]).write_text(json.dumps({'args': args, 'old': old, 'new': new}))
        """)
        defer { fixture.remove() }
        let before = try ManualPairRequestFixtures.source(current: false), after = try ManualPairRequestFixtures.source(current: true)
        let selection = try ManualPairRequestFixtures.selection()
        let result = try await EngineRunner().run(.diff(baseline: before, current: after, manualPairs: selection), configuration: fixture.configuration)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: result.data) as? [String: Any])
        let args = try XCTUnwrap(object["args"] as? [String])
        XCTAssertEqual(Array(args.suffix(4)), selection.arguments)
        XCTAssertEqual(args.filter { $0 == "--pair" }.count, 2)
        XCTAssertEqual(object["old"] as? String, String(decoding: before, as: UTF8.self))
        XCTAssertEqual(object["new"] as? String, String(decoding: after, as: UTF8.self))
    }

    func testManualPairEmptyDefaultPreservesExactLegacyArgumentList() async throws {
        let fixture = try TestEngine(script: """
        import json, pathlib, sys
        args = sys.argv[1:]
        pathlib.Path(args[args.index('--output') + 1]).write_text(json.dumps(args))
        """)
        defer { fixture.remove() }
        let runner = EngineRunner()
        for command in [EngineCommand.diff(baseline: Data(), current: Data()),
                        EngineCommand.diff(baseline: Data(), current: Data(), manualPairs: .empty)] {
            let result = try await runner.run(command, configuration: fixture.configuration)
            let args = try JSONDecoder().decode([String].self, from: result.data)
            XCTAssertEqual(args.count, 7)
            guard args.count == 7 else { continue }
            let root = URL(fileURLWithPath: args[6]).deletingLastPathComponent()
            XCTAssertEqual(args, ["diff", "--baseline", root.appendingPathComponent("baseline.json").path,
                                  "--current", root.appendingPathComponent("current.json").path,
                                  "--output", root.appendingPathComponent("output.json").path])
        }
    }

    func testManualPairRunnerRefusesReboundSourcesBeforeLaunch() async throws {
        let fixture = try TestEngine(script: """
        import pathlib
        pathlib.Path(__file__).with_suffix('.started').write_text('unexpected launch')
        """)
        defer { fixture.remove() }
        let selection = try ManualPairRequestFixtures.selection()
        do {
            _ = try await EngineRunner().run(.diff(baseline: ManualPairRequestFixtures.source(current: false),
                current: ManualPairRequestFixtures.source(current: true, digest: "1"), manualPairs: selection), configuration: fixture.configuration)
            XCTFail("Same-image rebound request must be refused")
        } catch let error as ReportError {
            XCTAssertTrue(error.localizedDescription.contains("exact-image"))
        }
        XCTAssertFalse(FileManager.default.fileExists(atPath: fixture.scriptURL.deletingPathExtension().appendingPathExtension("started").path))
    }

    func testManualPairRunnerRefusesArgumentBudgetBeforeLaunching() async throws {
        let fixture = try TestEngine(script: "raise RuntimeError('must not launch')")
        defer { fixture.remove() }
        // Oversize one launcher argument rather than constructing a large report corpus.
        let oversized = URL(fileURLWithPath: "/" + String(repeating: "x", count: max(16_384, Int(sysconf(_SC_ARG_MAX)))))
        let configuration = EngineConfiguration(pythonExecutable: fixture.configuration.pythonExecutable, bootstrap: oversized)
        do {
            _ = try await EngineRunner().run(.diff(baseline: ManualPairRequestFixtures.source(current: false),
                current: ManualPairRequestFixtures.source(current: true), manualPairs: ManualPairRequestFixtures.selection()),
                configuration: configuration)
            XCTFail("Oversized argv must be refused before Process.run")
        } catch let error as ReportError {
            XCTAssertTrue(error.localizedDescription.contains("process argument budget"))
        }
    }

    func testSwiftCommandAcceptsOnlyItsPartialExitAndPreservesArguments() async throws {
        let fixture = try TestEngine(script: """
        import json, pathlib, sys
        args = sys.argv[1:]
        pathlib.Path(args[args.index('--output') + 1]).write_text(json.dumps({'args': args}))
        raise SystemExit(1)
        """)
        defer { fixture.remove() }
        let runner = EngineRunner()
        let input = fixture.directory.appendingPathComponent("--owned input;quote")
        let artifact = try await runner.run(.swiftErrorFlow(input: input, options: .init(includeMethods: true, includeWitnesses: true)), configuration: fixture.configuration)
        let value = try XCTUnwrap(JSONSerialization.jsonObject(with: artifact.data) as? [String: [String]])
        let args = try XCTUnwrap(value["args"])
        XCTAssertEqual(args.first, "swift-error-flow")
        XCTAssertEqual(Array(args.suffix(2)), ["--", input.path])
        XCTAssertTrue(args.contains("--include-outcome-witnesses"))
        XCTAssertTrue(artifact.statusText.contains("Partial"))
        do {
            _ = try await runner.run(.audit(input: input), configuration: fixture.configuration)
            XCTFail("Audit must not accept exit1")
        } catch EngineError.failed(let status, _) { XCTAssertEqual(status, 1) }
    }

    func testSymbolsCommandStagesOriginalReportAndPreservesDebugPathArgument() async throws {
        let fixture = try TestEngine(script: """
        import json, pathlib, sys
        args = sys.argv[1:]
        output = pathlib.Path(args[args.index('--output') + 1])
        source = pathlib.Path(args[args.index('--report') + 1]).read_text()
        output.write_text(json.dumps({'command': args[0], 'dsym': args[args.index('--dsym') + 1], 'report': source}))
        """)
        defer { fixture.remove() }
        let symbols = fixture.directory.appendingPathComponent("Owned symbols; 'quoted'.dSYM")
        let original = Data("{\"future\": true}".utf8)
        let result = try await EngineRunner().run(.symbols(report: original, dsym: symbols), configuration: fixture.configuration)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: result.data) as? [String: String])
        XCTAssertEqual(object["command"], "symbols")
        XCTAssertEqual(object["dsym"], symbols.path)
        XCTAssertEqual(object["report"], String(data: original, encoding: .utf8))
    }

    func testPathArgumentIsPreservedAndLargeLogsDoNotBlockTheChild() async throws {
        let fixture = try TestEngine(script: """
        import json, pathlib, sys
        args = sys.argv[1:]
        output = pathlib.Path(args[args.index('--output') + 1])
        sys.stdout.write('status ' * 32768)
        sys.stderr.write('diagnostic ' * 32768)
        output.write_text(json.dumps({'input': args[-1], 'separator': args[-2]}))
        """)
        defer { fixture.remove() }
        let input = URL(fileURLWithPath: "/tmp/owned input with spaces; and 'quotes'.bin")
        let artifact = try await EngineRunner().run(.audit(input: input), configuration: fixture.configuration)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: artifact.data) as? [String: String])
        XCTAssertEqual(object["input"], input.path)
        XCTAssertEqual(object["separator"], "--")
        XCTAssertFalse(artifact.statusText.isEmpty)
        XCTAssertLessThanOrEqual(artifact.statusText.utf8.count, 16 * 1024)
    }

    func testNonzeroExitNeverReturnsAnOutputFileAsSuccess() async throws {
        let fixture = try TestEngine(script: """
        import pathlib, sys
        args = sys.argv[1:]
        pathlib.Path(args[args.index('--output') + 1]).write_text('{"stale": true}')
        sys.stderr.write('Known input rejection')
        raise SystemExit(2)
        """)
        defer { fixture.remove() }
        do {
            _ = try await EngineRunner().run(.audit(input: fixture.directory), configuration: fixture.configuration)
            XCTFail("A nonzero process exit must fail even when a JSON output exists.")
        } catch EngineError.failed(let status, let diagnostic) {
            XCTAssertEqual(status, 2)
            XCTAssertTrue(diagnostic.contains("Known input rejection"))
        }
    }

    func testMissingOversizedAndInternalErrorOutputsRemainFailures() async throws {
        for (script, expected) in [
            ("pass", "missing"),
            ("import sys; sys.stderr.write('owned internal error'); sys.exit(3)", "internal"),
            ("import pathlib, sys; a=sys.argv; p=pathlib.Path(a[a.index('--output')+1]); f=p.open('wb'); f.truncate(64*1024*1024+1); f.close()", "oversized")
        ] {
            let fixture = try TestEngine(script: script)
            defer { fixture.remove() }
            do {
                _ = try await EngineRunner().run(.audit(input: fixture.directory), configuration: fixture.configuration)
                XCTFail("Expected failure for \(expected)")
            } catch EngineError.failed(let code, let diagnostic) {
                XCTAssertEqual(expected, "internal")
                XCTAssertEqual(code, 3)
                XCTAssertTrue(diagnostic.contains("owned internal error"))
            } catch EngineError.missingOutput {
                XCTAssertEqual(expected, "missing")
            } catch ReportError.tooLarge {
                XCTAssertEqual(expected, "oversized")
            }
        }
    }

    func testLaunchFailureIsReportedAndRunnerRemainsAvailable() async throws {
        let fixture = try TestEngine(script: "pass")
        defer { fixture.remove() }
        let runner = EngineRunner()
        let bad = EngineConfiguration(pythonExecutable: fixture.directory.appendingPathComponent("absent"),
                                      bootstrap: fixture.scriptURL)
        do {
            _ = try await runner.run(.audit(input: fixture.directory), configuration: bad)
            XCTFail("Expected launch failure")
        } catch EngineError.launchFailed { }
        try fixture.replaceScript("import pathlib, sys; a=sys.argv; pathlib.Path(a[a.index('--output')+1]).write_text('{}')")
        let output = try await runner.run(.audit(input: fixture.directory), configuration: fixture.configuration)
        XCTAssertEqual(output.data, Data("{}".utf8))
    }

    func testCancellationFinishesBeforeTheRunnerAcceptsAnotherCommand() async throws {
        let fixture = try TestEngine(script: """
        import pathlib, time
        pathlib.Path(__file__).with_suffix('.started').write_text('ready')
        while True:
            time.sleep(0.1)
        """)
        defer { fixture.remove() }
        let runner = EngineRunner()
        let task = Task {
            try await runner.run(.audit(input: fixture.directory), configuration: fixture.configuration)
        }
        let marker = fixture.scriptURL.deletingPathExtension().appendingPathExtension("started")
        for _ in 0..<60 {
            if FileManager.default.fileExists(atPath: marker.path) { break }
            try await Task.sleep(nanoseconds: 50_000_000)
        }
        let childStarted = FileManager.default.fileExists(atPath: marker.path)
        task.cancel()
        do {
            _ = try await task.value
            XCTFail("The cancelled command returned success.")
        } catch is CancellationError {
            // Expected: no completion is published until the owned child terminates.
        }
        XCTAssertTrue(childStarted, "The test-owned child did not start before cancellation.")
        try fixture.replaceScript("""
        import pathlib, sys
        args = sys.argv[1:]
        pathlib.Path(args[args.index('--output') + 1]).write_text('{"ready": true}')
        """)
        let next = try await runner.run(.audit(input: fixture.directory), configuration: fixture.configuration)
        let object = try XCTUnwrap(JSONSerialization.jsonObject(with: next.data) as? [String: Bool])
        XCTAssertEqual(object["ready"], true)
    }
}

private struct TestEngine: Sendable {
    let directory: URL
    let scriptURL: URL
    let configuration: EngineConfiguration

    init(script: String) throws {
        let fileManager = FileManager.default
        let explicit = ProcessInfo.processInfo.environment["AIRS_PYTHON"]
        let candidates = [explicit, "/opt/homebrew/bin/python3", "/usr/local/bin/python3", "/usr/bin/python3"]
            .compactMap { $0 }
        guard let python = candidates.first(where: { $0.hasPrefix("/") && fileManager.isExecutableFile(atPath: $0) }) else {
            throw XCTSkip("A local Python executable is required for the process-bridge integration tests.")
        }
        let directory = fileManager.temporaryDirectory
            .appendingPathComponent("AIRS native test \(UUID().uuidString)", isDirectory: true)
        try fileManager.createDirectory(at: directory, withIntermediateDirectories: false,
                                        attributes: [.posixPermissions: 0o700])
        let scriptURL = directory.appendingPathComponent("owned_test_bootstrap.py")
        do {
            try script.write(to: scriptURL, atomically: true, encoding: .utf8)
        } catch {
            try? fileManager.removeItem(at: directory)
            throw error
        }
        self.directory = directory
        self.scriptURL = scriptURL
        configuration = EngineConfiguration(pythonExecutable: URL(fileURLWithPath: python), bootstrap: scriptURL)
    }

    func replaceScript(_ script: String) throws {
        try script.write(to: scriptURL, atomically: true, encoding: .utf8)
    }

    func remove() {
        try? FileManager.default.removeItem(at: directory)
    }
}
