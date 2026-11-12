import Foundation
import XCTest
@testable import AIRSCore

final class SwiftBroadFlowReportTests: XCTestCase {
    func testExtendedCallEnvelopeAtLimitAndAbove() throws {
        var value = fixture()
        value["model_version"] = "swift-broad-error-flow-extended-v1"; value["profile"] = "broad-extended-v1"
        let rows = (0..<8193).map { ["caller_pc": "0x1000", "call_pc": "0x" + String(4100 + $0 * 4, radix: 16), "admission": ["status": "unresolved", "reason": "unqualified"], "candidate": NSNull(), "validation": NSNull()] as [String: Any] }
        value["calls"] = Array(rows.prefix(8192)); value["selected_call_candidates"] = 8192
        value["observed_call_instructions"] = 8192; value["status_counts"] = ["unresolved": 8192]; value["reason_counts"] = ["unqualified": 8192]
        XCTAssertEqual(try decode(value).calls.count,8192)
        value["calls"] = rows
        XCTAssertThrowsError(try decode(value))
    }
    func testExtendedProfileAdmitsLargerRetainedCallEnvelope() throws {
        var value = fixture()
        value["model_version"] = "swift-broad-error-flow-extended-v1"; value["profile"] = "broad-extended-v1"
        value["calls"] = (0..<4097).map { ["caller_pc": "0x1000", "call_pc": "0x" + String(4100 + $0 * 4, radix: 16), "admission": ["status": "unresolved", "reason": "unqualified"], "candidate": NSNull(), "validation": NSNull()] as [String: Any] }
        value["selected_call_candidates"] = 4097; value["observed_call_instructions"] = 4097
        value["status_counts"] = ["unresolved": 4097]; value["reason_counts"] = ["unqualified": 4097]
        XCTAssertEqual(try decode(value).calls.count,4097)
        value["model_version"] = "swift-broad-error-flow-large-v1"; value["profile"] = "broad-large-v1"
        XCTAssertThrowsError(try decode(value))
    }
    func testExtendedProfileModelAndPartialEvidenceAdmission() throws {
        let options = SwiftFlowOptions(profile: .broadExtended)
        XCTAssertTrue(options.arguments(input: URL(fileURLWithPath: "/owned"), output: URL(fileURLWithPath: "/out")).contains("broad-extended-v1"))
        var value = fixture()
        value["model_version"] = "swift-broad-error-flow-extended-v1"; value["profile"] = "broad-extended-v1"
        value["selected_call_candidates"] = 2; value["observed_call_instructions"] = 2; value["omitted_calls"] = 1
        value["scanned_words"] = 500_000; value["call_details_complete"] = false; value["outcome_witnesses_complete"] = false
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        let result = try SwiftFlowReport.decode(data)
        XCTAssertTrue(result.supportsInterpretation); XCTAssertTrue(result.wordScanComplete)
        XCTAssertFalse(result.callDetailsComplete); XCTAssertEqual(result.omittedCallCount, 1)
        value["profile"] = "broad-large-v1"
        XCTAssertFalse(try decode(value).supportsInterpretation)
    }
    func testLargerProfileRoutingAndHistoricalModelBinding() throws {
        let options = SwiftFlowOptions(profile: .broadLarge)
        XCTAssertTrue(options.arguments(input: URL(fileURLWithPath: "/owned"), output: URL(fileURLWithPath: "/out")).contains("broad-large-v1"))
        var value = fixture()
        value["model_version"] = "swift-broad-error-flow-large-v1"
        value["profile"] = "broad-large-v1"
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        let report = try SwiftFlowReport.decode(data)
        XCTAssertTrue(report.supportsInterpretation)
        XCTAssertEqual(report.calls.first?.witnessStatus, "eligible_structural_only")
        value["profile"] = "broad-v1"
        XCTAssertFalse(try decode(value).supportsInterpretation)
    }
    func fixture() -> [String: Any] {
        let identity: [String: Any] = ["container_sha256": String(repeating: "a", count: 64), "slice_sha256": String(repeating: "b", count: 64), "architecture": "arm64", "cpu_subtype": 0, "uuid": NSNull(), "preferred_base": "0x1000", "slice_index": 1, "container_slice_count": 2, "slice_offset": "0x1000", "slice_size": "0x10000"]
        var bound = identity
        bound["caller"] = ["start_pc": "0x1000", "end_pc_exclusive": "0x1020", "boundary_source": "lc_function_starts"]
        bound["callee"] = ["start_pc": "0x1100", "end_pc_exclusive": "0x1108", "boundary_source": "lc_function_starts"]
        bound["call_pc"] = "0x1004"
        let candidate: [String: Any] = ["model_version": "swift-outcome-witness-v2", "validation_model": "swift-outcome-validation-v2", "profile": "broad-v1", "source_models": ["edge": "swift-broad-error-flow-v1", "witness": "swift-outcome-witness-v2", "validation": "swift-outcome-validation-v2", "cfg": "swift-bounded-structural-cfg-v1", "value": "swift-outcome-values-v1"], "status": "unresolved", "eligible": false, "identity": bound, "completeness": ["complete": true, "missing": []], "call": ["pc": "0x1004", "callee_pc": "0x1100", "abi": ["status": "admitted", "profile": "swift6-arm64-sync-untyped-stable-research-v2", "error_register": "x21"], "declaration": ["status": "syntax_admitted"]], "post_call": ["test_pc": "0x1008", "success_successor_pc": "0x1010", "error_successor_pc": "0x100c"], "regions": ["paths": []], "cfg": ["edges": []], "value_facts": ["seed": ["origin": "raw_post_call_register:x21"]]]
        let validation: [String: Any] = ["model_version": "swift-outcome-validation-v2", "status": "eligible_structural_only", "eligible": true, "reason": "independent_bounded_byte_replay", "eligibility_scope": "checked_structural_facts_only", "completeness": ["complete": true, "missing": []], "value_fact_status": "checked_symbolic_values", "facts": ["call": "independently checked"], "fact_statuses": ["identity": "checked", "call": "checked", "abi": "checked", "cfg": "checked", "post_call": "checked", "regions": "checked", "values": "checked_symbolic_values"], "accounting": ["work": 24, "instructions": 4], "runtime_branch_proven": false, "call_return_proven": false, "error_state_proven": false, "source_reconstruction_allowed": false, "handler_semantics_proven": false, "exclusive_entry_proven": false]
        return ["model_version": "swift-broad-error-flow-v1", "profile": "broad-v1", "witness_model_version": "swift-outcome-witness-v2", "validation_model_version": "swift-outcome-validation-v2", "identity": identity, "word_scan_complete": true, "call_details_complete": true, "outcome_witnesses_complete": true, "observed_call_instructions": 1, "selected_call_candidates": 1, "omitted_calls": 0, "scanned_words": 24, "analysis_work": 100, "research_only": true, "call_return_proven": false, "runtime_reachability_proven": false, "status_counts": ["eligible_structural_only": 1], "reason_counts": ["independent_bounded_byte_replay": 1], "calls": [["caller_pc": "0x1000", "call_pc": "0x1004", "admission": ["status": "admitted_callsite", "call_pc": 4100, "callee_pc": 4352, "symbol": "$sOwned", "abi": ["status": "admitted", "profile": "swift6-arm64-sync-untyped-stable-research-v2", "error_register": "x21"], "declaration": ["status": "syntax_admitted"]], "candidate": candidate, "validation": validation]], "limitations": ["structural_only"]]
    }
    func decode(_ value: [String: Any]) throws -> SwiftFlowReport {
        try SwiftBroadFlowReport.decode(value, data: JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]))
    }
    func testRecordedBroadWitnessAndCoordinatesRemainHistorical() throws {
        let value = fixture(), report = try decode(value), row = try XCTUnwrap(report.calls.first)
        XCTAssertTrue(report.supportsInterpretation)
        XCTAssertEqual(row.witnessStatus, "eligible_structural_only")
        XCTAssertEqual(row.witnessWorkSteps, 24); XCTAssertEqual(row.witnessCheckedInstructionCount, 4)
        XCTAssertEqual(row.testPC, "0x1008"); XCTAssertEqual(row.calleeSymbol, "$sOwned")
        XCTAssertTrue(row.detailJSON.contains("value_facts")); XCTAssertTrue(row.detailJSON.contains("declaration"))
        XCTAssertTrue(report.imageDescription.contains("slice index 1 of 2"))
        XCTAssertEqual(report.sourceData, try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys]))
    }
    func testIndependentStatusCannotBePromotedFromCandidateOrContradiction() throws {
        for key in ["eligible", "runtime_branch_proven", "completeness"] {
            var object = fixture(), rows = object["calls"] as! [[String: Any]], validation = rows[0]["validation"] as! [String: Any]
            if key == "eligible" { validation[key] = false }
            else if key == "completeness" { validation[key] = ["complete": false, "missing": ["partial"]] }
            else { validation[key] = true }
            rows[0]["validation"] = validation; object["calls"] = rows
            XCTAssertNotEqual(try decode(object).calls.first?.witnessStatus, "eligible_structural_only")
        }
        var object = fixture(), rows = object["calls"] as! [[String: Any]], candidate = rows[0]["candidate"] as! [String: Any]
        candidate["eligible"] = true; rows[0]["candidate"] = candidate; rows[0]["validation"] = NSNull(); object["calls"] = rows
        XCTAssertNotEqual(try decode(object).calls.first?.witnessStatus, "eligible_structural_only")
    }
    func testWrongImageCallAndSliceBindingsRefuse() throws {
        for key in ["slice_sha256", "cpu_subtype", "slice_index", "call_pc"] {
            var object = fixture(), rows = object["calls"] as! [[String: Any]], candidate = rows[0]["candidate"] as! [String: Any], identity = candidate["identity"] as! [String: Any]
            identity[key] = key == "slice_sha256" ? String(repeating: "c", count: 64) : key == "call_pc" ? "0x1008" : 3
            candidate["identity"] = identity; rows[0]["candidate"] = candidate; object["calls"] = rows
            XCTAssertThrowsError(try decode(object), key)
        }
    }
    func testUnknownOrMixedModelsRetainRawWithoutInterpretation() throws {
        for key in ["model_version", "witness_model_version", "validation_model_version"] {
            var object = fixture(); object[key] = "future"
            let report = try decode(object)
            XCTAssertFalse(report.supportsInterpretation); XCTAssertNil(report.calls.first?.witnessStatus)
            XCTAssertFalse(report.sourceData.isEmpty)
        }
    }
    func testUnavailableAdmissionAndPartialCountsRemainExplicit() throws {
        var object = fixture(); object["calls"] = [["caller_pc": "0x1000", "call_pc": "0x1004", "admission": ["status": "unresolved", "reason": "authenticated_indirect_unsupported"], "candidate": NSNull(), "validation": NSNull()]]
        object["selected_call_candidates"] = 3; object["observed_call_instructions"] = 3; object["omitted_calls"] = 2; object["call_details_complete"] = false; object["outcome_witnesses_complete"] = false
        object["status_counts"] = ["unresolved": 1]; object["reason_counts"] = ["authenticated_indirect_unsupported": 1]
        let report = try decode(object)
        XCTAssertEqual(report.calls.first?.reason, "authenticated_indirect_unsupported")
        XCTAssertEqual(report.omittedCallCount, 2); XCTAssertFalse(report.callDetailsComplete)
        XCTAssertTrue(report.summaryText.contains("2 omitted"))
    }
    func testDuplicateAndMalformedAccountingRefuse() throws {
        var object = fixture(); let rows = object["calls"] as! [[String: Any]]; object["calls"] = rows + rows
        XCTAssertThrowsError(try decode(object))
        for bad in [true, -1, 1.5] as [Any] { object = fixture(); object["omitted_calls"] = bad; XCTAssertThrowsError(try decode(object)) }
        object = fixture(); object["selected_call_candidates"] = 0; XCTAssertThrowsError(try decode(object))
    }
    func testEntire4096CallEnvelopeAndDeterministicProjection() throws {
        var object = fixture()
        object["calls"] = (0..<4096).map { ["caller_pc": "0x1000", "call_pc": "0x" + String(4100 + $0 * 4, radix: 16), "admission": ["status": "unresolved", "reason": "unqualified"], "candidate": NSNull(), "validation": NSNull()] as [String: Any] }
        object["selected_call_candidates"] = 4096; object["observed_call_instructions"] = 4096; object["status_counts"] = ["unresolved": 4096]; object["reason_counts"] = ["unqualified": 4096]
        let first = try decode(object), second = try decode(object)
        XCTAssertEqual(first.calls.count, 4096); XCTAssertEqual(first.calls.map(\.id), second.calls.map(\.id))
        XCTAssertEqual(first.calls.first?.detailJSON, second.calls.first?.detailJSON)
        var rows = object["calls"] as! [[String: Any]]; rows.append(rows[0]); object["calls"] = rows
        XCTAssertThrowsError(try decode(object))
    }
    func testDepthAndCandidateSizeLimitsRefuse() throws {
        var object = fixture(), nested: Any = "leaf"
        for _ in 0..<35 { nested = [nested] }; object["extra"] = nested
        XCTAssertThrowsError(try decode(object))
        object = fixture(); var rows = object["calls"] as! [[String: Any]], candidate = rows[0]["candidate"] as! [String: Any]
        candidate["extra"] = Array(repeating: String(repeating: "x", count: 2048), count: 140); rows[0]["candidate"] = candidate; object["calls"] = rows
        XCTAssertThrowsError(try decode(object))
    }
    func testDuplicateJSONKeysAndEscapedAliasesRefuse() throws {
        let object = fixture(), data = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        let text = String(decoding: data, as: UTF8.self)
        for mutation in [text.replacingOccurrences(of: "\"profile\":\"broad-v1\"", with: "\"profile\":\"future\",\"profile\":\"broad-v1\""),
                         text.replacingOccurrences(of: "\"slice_index\":1", with: "\"slice_index\":0,\"slice_index\":1"),
                         text.replacingOccurrences(of: "\"model_version\":\"swift-broad-error-flow-v1\"", with: "\"model\\u005fversion\":\"future\",\"model_version\":\"swift-broad-error-flow-v1\"")] {
            let raw = Data(mutation.utf8)
            let lastWins = try XCTUnwrap(JSONSerialization.jsonObject(with: raw) as? [String: Any])
            XCTAssertThrowsError(try SwiftBroadFlowReport.decode(lastWins, data: raw))
        }
    }
    func testUnknownCandidateSourceModelsCannotPromoteEligibility() throws {
        var object = fixture(), rows = object["calls"] as! [[String: Any]], candidate = rows[0]["candidate"] as! [String: Any]
        candidate["source_models"] = ["edge": "swift-broad-error-flow-v1", "witness": "swift-outcome-witness-v2", "validation": "swift-outcome-validation-v2", "cfg": "future", "value": "swift-outcome-values-v1"]
        rows[0]["candidate"] = candidate; object["calls"] = rows
        XCTAssertNotEqual(try decode(object).calls.first?.witnessStatus, "eligible_structural_only")
    }

    func testCancelledBroadProjectionRefusesBeforePublication() async throws {
        let result = await Task.detached { () -> Bool in
            withUnsafeCurrentTask { $0?.cancel() }
            do { _ = try self.decode(self.fixture()); return false }
            catch is CancellationError { return true }
            catch { return false }
        }.value
        XCTAssertTrue(result)
    }

    func testUnknownOrContradictoryRecordedABICannotPromoteEligibility() throws {
        var object = fixture(), rows = object["calls"] as! [[String: Any]], candidate = rows[0]["candidate"] as! [String: Any], call = candidate["call"] as! [String: Any], abi = call["abi"] as! [String: Any]
        abi["profile"] = "future"; call["abi"] = abi; candidate["call"] = call; rows[0]["candidate"] = candidate; object["calls"] = rows
        XCTAssertNotEqual(try decode(object).calls.first?.witnessStatus, "eligible_structural_only")
    }

    func testNonobjectRangesAndMissingNumericAdmissionCannotBindEligibility() throws {
        for key in ["caller", "callee"] {
            var object = fixture(), rows = object["calls"] as! [[String: Any]], candidate = rows[0]["candidate"] as! [String: Any], identity = candidate["identity"] as! [String: Any]
            identity[key] = NSNull(); candidate["identity"] = identity; rows[0]["candidate"] = candidate; object["calls"] = rows
            XCTAssertThrowsError(try decode(object))
        }
        for key in ["call_pc", "callee_pc"] {
            var object = fixture(), rows = object["calls"] as! [[String: Any]], admission = rows[0]["admission"] as! [String: Any]
            admission.removeValue(forKey: key); rows[0]["admission"] = admission; object["calls"] = rows
            XCTAssertNotEqual(try decode(object).calls.first?.witnessStatus, "eligible_structural_only")
        }
    }
    func testIndependentCoreFactsMustBeCheckedAndValueUnknownsRemainExplicit() throws {
        for key in ["identity", "call", "abi", "cfg", "post_call", "regions"] {
            var object = fixture(), rows = object["calls"] as! [[String: Any]], validation = rows[0]["validation"] as! [String: Any], facts = validation["fact_statuses"] as! [String: String]
            facts[key] = "unchecked"; validation["fact_statuses"] = facts; rows[0]["validation"] = validation; object["calls"] = rows
            let call = try XCTUnwrap(try decode(object).calls.first)
            XCTAssertNotEqual(call.witnessStatus, "eligible_structural_only")
            XCTAssertTrue(call.witnessReason?.contains("Recorded eligibility") == true)
        }
        for state in ["checked_symbolic_values", "checked_with_explicit_unknowns", "not_applicable_no_return_paths"] {
            var object = fixture(), rows = object["calls"] as! [[String: Any]], validation = rows[0]["validation"] as! [String: Any], facts = validation["fact_statuses"] as! [String: String]
            facts["values"] = state; validation["fact_statuses"] = facts; validation["value_fact_status"] = state; rows[0]["validation"] = validation; object["calls"] = rows
            XCTAssertEqual(try decode(object).calls.first?.witnessStatus, "eligible_structural_only")
        }
    }
    func testForeignFactKeysAndOversizedStatusesStayInRawDetails() throws {
        var object = fixture(), rows = object["calls"] as! [[String: Any]], validation = rows[0]["validation"] as! [String: Any], facts = validation["fact_statuses"] as! [String: String]
        for index in 0..<1000 { facts["foreign-\(index)"] = "checked" }
        facts["cfg"] = String(repeating: "x", count: 10000)
        validation["fact_statuses"] = facts; rows[0]["validation"] = validation; object["calls"] = rows
        let call = try XCTUnwrap(try decode(object).calls.first)
        XCTAssertLessThanOrEqual(call.witnessFacts.filter { $0.hasPrefix("Independent ") }.count, 7)
        XCTAssertLessThan(call.witnessFacts.joined().utf8.count, 4096)
        XCTAssertTrue(call.detailJSON.contains("foreign-999"))
        XCTAssertNotEqual(call.witnessStatus, "eligible_structural_only")
    }

}

extension SwiftBroadFlowReportTests {
    private func importCounts(_ selected: Int = 2) -> [String: Any] {
        var counts: [String: Any] = [:]
        counts["attributed_stubs"] = selected
        counts["declined_stubs"] = 0
        counts["invalid_stub_sections"] = 0
        counts["selected_import_calls"] = selected
        counts["non_throwing_swift_import_calls"] = 0
        counts["non_swift_import_calls"] = 0
        counts["declined_stub_calls"] = 0
        return counts
    }

    func importsFixture() -> [String: Any] {
        var value = fixture()
        value["model_version"] = "swift-broad-error-flow-imports-v1"
        value["profile"] = "broad-imports-v1"
        value["import_stub_model"] = "arm64-import-stub-double-binding-v1"
        value["import_stubs_complete"] = true
        value["import_stub_reason"] = NSNull()
        value["import_stub_counts"] = importCounts()
        value["limitations"] = ["structural_only", "imported_callees_attribution_only"]
        var rows = value["calls"] as! [[String: Any]]
        rows.append(importRow(index: 0, admitted: true))
        rows.append(importRow(index: 1, admitted: false))
        value["calls"] = rows
        value["observed_call_instructions"] = 3
        value["selected_call_candidates"] = 3
        value["status_counts"] = ["eligible_structural_only": 1, "unresolved": 2]
        value["reason_counts"] = ["independent_bounded_byte_replay": 1, "imported_callee_abi_unqualified": 2]
        return value
    }

    private func importRow(index: Int, admitted: Bool) -> [String: Any] {
        let symbol = admitted ? "_$s4Test3fooyS2iKF" : "_$sZZZ"
        var identity: [String: Any] = [:]
        identity["syntax_model"] = "swift-import-declaration-syntax-v1"
        identity["symbol"] = symbol
        identity["entity"] = "function"
        identity["module"] = "Test"
        identity["name"] = "foo"
        identity["context"] = [Any]()
        identity["parameter_labels"] = [NSNull()]
        var integerType: [String: Any] = [:]
        integerType["name"] = "Swift.Int"
        integerType["arguments"] = [Any]()
        integerType["inout"] = false
        integerType["label"] = NSNull()
        integerType["generic_depth"] = NSNull()
        integerType["generic_index"] = NSNull()
        integerType["nominal_kind"] = "struct"
        identity["parameter_types"] = [integerType]
        identity["result_type"] = integerType
        identity["throws"] = true
        var declaration: [String: Any] = [:]
        declaration["status"] = admitted ? "syntax_admitted" : "syntax_unresolved"
        if admitted {
            declaration["identity"] = identity
            declaration["reason"] = NSNull()
        } else {
            declaration["identity"] = NSNull()
            declaration["reason"] = "unsupported_syntax"
        }
        // Default synthetic stub from test_swift_broad_imports.provenance; the second
        // slot uses stub_image_helpers.ldr_x_uimm's eight-byte offset encoding.
        let stub = 0x100001008 + index * 12
        let pointer = 0x100004000 + index * 8
        let words: [String] = ["0xf0000010", index == 0 ? "0xf9400210" : "0xf9400610", "0xd61f0200"]
        var recorded: [[String: Any]] = []
        for k in 0..<3 {
            var word: [String: Any] = [:]
            word["pc"] = stub + k * 4
            word["word"] = words[k]
            word["slice_file_offset"] = 0x1008 + index * 12 + k * 4
            word["container_file_offset"] = 0x2008 + index * 12 + k * 4
            recorded.append(word)
        }
        var provenance: [String: Any] = [:]
        provenance["stub_words"] = recorded
        provenance["stub_indirect_entry_offset"] = 0x8038 + index * 4
        provenance["pointer_indirect_entry_offset"] = 0x8040 + index * 4
        provenance["nlist_offset"] = 0x8018 + index * 16
        provenance["stub_model"] = "arm64-import-stub-double-binding-v1"
        provenance["stub_section"] = "__TEXT,__stubs"
        provenance["stub_index"] = index
        provenance["symbol_index"] = index + 1
        provenance["pointer_address"] = pointer
        provenance["pointer_section"] = "__DATA_CONST,__got"
        var admission: [String: Any] = [:]
        admission["model_version"] = "swift-broad-import-callsite-v1"
        admission["status"] = "unresolved"
        admission["reason"] = "imported_callee_abi_unqualified"
        admission["call_kind"] = index == 0 ? "bl" : "b"
        admission["call_pc"] = 0x100001000 + index * 4
        admission["caller_start"] = 0x100001000
        admission["callee_stub_pc"] = stub
        admission["symbol"] = symbol
        admission["library_ordinal"] = 2
        admission["declaration"] = declaration
        admission["import_provenance"] = provenance
        admission["details_complete"] = true
        admission["call_return_proven"] = false
        admission["syntactic_call_target_admitted"] = false
        admission["import_attribution_admitted"] = true
        admission["work_steps"] = 16 + symbol.utf8.count
        var row: [String: Any] = [:]
        row["caller_pc"] = "0x100001000"
        row["call_pc"] = "0x" + String(0x100001000 + index * 4, radix: 16)
        row["admission"] = admission
        row["candidate"] = NSNull()
        row["validation"] = NSNull()
        return row
    }

    private func replacingImportField(_ node: Any, path: ArraySlice<String>, with replacement: Any?) -> Any {
        guard let key = path.first else { return replacement ?? NSNull() }
        if var array = node as? [Any], let index = Int(key) {
            array[index] = replacingImportField(array[index], path: path.dropFirst(), with: replacement)
            return array
        }
        var object = node as! [String: Any]
        if path.count == 1 { object[key] = replacement }
        else { object[key] = replacingImportField(object[key]!, path: path.dropFirst(), with: replacement) }
        return object
    }

    private func changingImportField(_ value: [String: Any], _ path: String, _ replacement: Any?) -> [String: Any] {
        replacingImportField(value, path: path.components(separatedBy: ".")[...], with: replacement) as! [String: Any]
    }

    private func assertImportRefusals(_ value: [String: Any], _ mutations: [(String, Any?)],
                                      file: StaticString = #filePath, line: UInt = #line) throws {
        for (path, replacement) in mutations {
            XCTAssertTrue(try decode(value).supportsInterpretation, "Positive control: \(path)", file: file, line: line)
            let malformed = changingImportField(value, path, replacement)
            XCTAssertThrowsError(try decode(malformed), path, file: file, line: line)
        }
    }

    private func incompleteImportsFixture() -> [String: Any] {
        var value = importsFixture()
        value["import_stubs_complete"] = false
        value["import_stub_reason"] = "missing_indirect_symbol_table"
        value["call_details_complete"] = false
        value["import_stub_counts"] = importCounts(0)
        var rows = value["calls"] as! [[String: Any]]
        for index in 1...2 {
            let admission: [String: Any] = ["status": "unresolved", "reason": "imported_callee_abi_unqualified"]
            rows[index]["admission"] = admission
        }
        value["calls"] = rows
        return value
    }

    func testImportsPairKeepsAttributionUnresolvedAndLocalEligibility() throws {
        let value = importsFixture()
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        let report = try SwiftFlowReport.decode(data)
        XCTAssertTrue(report.supportsInterpretation)
        XCTAssertEqual(report.sourceData, data)
        XCTAssertEqual(report.calls[0].witnessStatus, "eligible_structural_only")
        XCTAssertEqual(report.calls[0].status, "eligible_structural_only")
        let symbols = ["_$s4Test3fooyS2iKF", "_$sZZZ"]
        for (index, row) in report.calls.dropFirst().enumerated() {
            XCTAssertEqual(row.status, "unresolved")
            XCTAssertNil(row.witnessStatus)
            XCTAssertEqual(row.reason, "imported_callee_abi_unqualified")
            XCTAssertEqual(row.calleeSymbol, symbols[index])
            XCTAssertNil(row.testPC); XCTAssertNil(row.successPC); XCTAssertNil(row.errorPC)
            XCTAssertFalse(row.witnessFacts.contains { $0.hasPrefix("Independent ") })
            XCTAssertTrue(row.witnessFacts.contains { $0.contains("attribution only") })
        }
        XCTAssertTrue(report.summaryText.contains("import stubs"))
    }

    func testImportsIncompleteTableDecodesAsPartial() throws {
        let report = try decode(incompleteImportsFixture())
        XCTAssertTrue(report.supportsInterpretation)
        XCTAssertFalse(report.callDetailsComplete)
        XCTAssertTrue(report.summaryText.contains("missing_indirect_symbol_table"))
    }

    func testImportsCallEnvelopeAtLimitAndAbove() throws {
        var value = importsFixture()
        var rows: [[String: Any]] = []
        for index in 0..<8193 {
            var row: [String: Any] = [:]
            row["caller_pc"] = "0x1000"
            row["call_pc"] = "0x" + String(0x1004 + index * 4, radix: 16)
            let admission: [String: Any] = ["status": "unresolved", "reason": "unqualified"]
            row["admission"] = admission
            row["candidate"] = NSNull(); row["validation"] = NSNull()
            rows.append(row)
        }
        value["calls"] = Array(rows.prefix(8192))
        value["selected_call_candidates"] = 8193
        value["observed_call_instructions"] = 8193
        value["omitted_calls"] = 1
        // A report that omits calls cannot claim complete details or complete witnesses.
        value["call_details_complete"] = false
        value["outcome_witnesses_complete"] = false
        value["import_stub_counts"] = importCounts(0)
        value["status_counts"] = ["unresolved": 8192]
        value["reason_counts"] = ["unqualified": 8192]
        XCTAssertEqual(try decode(value).calls.count, 8192)
        // Prepare an internally accounted over-limit report; only the call envelope is invalid.
        value["calls"] = rows; value["omitted_calls"] = 0
        value["status_counts"] = ["unresolved": 8193]
        value["reason_counts"] = ["unqualified": 8193]
        XCTAssertThrowsError(try decode(value))
    }

    func testImportsMismatchedProfilePairsRemainRawOnly() throws {
        for (model, profile) in [("swift-broad-error-flow-imports-v1", "broad-extended-v1"),
                                 ("swift-broad-error-flow-extended-v1", "broad-imports-v1")] {
            var value = importsFixture()
            value["model_version"] = model; value["profile"] = profile
            let report = try decode(value)
            XCTAssertFalse(report.supportsInterpretation)
            XCTAssertFalse(report.sourceData.isEmpty)
        }
    }

    func testImportsUnknownDeclarationSyntaxRemainsRawOnly() throws {
        for model in ["future", "swift-broad-declaration-syntax-v1"] {
            var value = changingImportField(importsFixture(), "calls.1.admission.declaration.identity.syntax_model", model)
            value = changingImportField(value, "calls.1.admission.declaration.identity.throws", false)
            let report = try decode(value)
            XCTAssertTrue(report.supportsInterpretation)
            XCTAssertEqual(report.calls[1].status, "unresolved")
            XCTAssertNil(report.calls[1].witnessStatus)
            XCTAssertTrue(report.calls[1].witnessFacts.contains { $0.contains("declaration syntax model unrecognized; raw only") })
        }
    }

    func testImportsEnvelopeFieldsRefuseMalformedValues() throws {
        var mutations: [(String, Any?)] = []
        mutations.append(("import_stub_model", "future"))
        mutations.append(("import_stubs_complete", 1))
        mutations.append(("import_stubs_complete", "true"))
        mutations.append(("import_stub_reason", "unexpected"))
        mutations.append(("import_stub_counts.attributed_stubs", nil))
        mutations.append(("import_stub_counts.extra", 0))
        for bad in [true, -1, 1.5] as [Any] { mutations.append(("import_stub_counts.declined_stubs", bad)) }
        mutations.append(("import_stub_counts.selected_import_calls", 1))
        mutations.append(("import_stub_counts.selected_import_calls", 4))
        for key in ["declined_stub_calls", "non_swift_import_calls", "non_throwing_swift_import_calls"] {
            mutations.append(("import_stub_counts." + key, 1))
        }
        mutations.append(("limitations", ["structural_only"]))
        mutations.append(("limitations", ["structural_only", "imported_callees_attribution_only", "imported_callees_attribution_only"]))
        try assertImportRefusals(importsFixture(), mutations)
    }

    func testImportsIncompleteTableContradictionsRefuse() throws {
        let imported = importRow(index: 0, admitted: true)
        let admission = imported["admission"] as! [String: Any]
        let mutations: [(String, Any?)] = [
            ("import_stub_reason", NSNull()), ("call_details_complete", true),
            ("calls.1.admission", admission)
        ]
        try assertImportRefusals(incompleteImportsFixture(), mutations)
    }

    func testImportsDuplicateStubModelKeyRefusesRawData() throws {
        let data = try JSONSerialization.data(withJSONObject: importsFixture(), options: [.sortedKeys])
        XCTAssertTrue(try SwiftFlowReport.decode(data).supportsInterpretation)
        let text = String(decoding: data, as: UTF8.self)
        let key = "\"import_stub_model\":\"arm64-import-stub-double-binding-v1\""
        let duplicate = key + "," + key
        let raw = Data(text.replacingOccurrences(of: key, with: duplicate).utf8)
        XCTAssertNotEqual(raw, data)
        XCTAssertThrowsError(try SwiftFlowReport.decode(raw))
    }

    func testImportsAdmissionFieldsRefuseClaimsAndMalformedValues() throws {
        var fields: [(String, Any?)] = []
        fields.append(("status", "eligible_structural_only"))
        fields.append(("reason", "unqualified"))
        fields.append(("call_kind", "blr"))
        fields.append(("caller_start", 0x100001004))
        fields.append(("callee_stub_pc", 0x100001009))
        fields.append(("callee_stub_pc", "0x100001008"))
        fields.append(("symbol", "_ordinary"))
        fields.append(("library_ordinal", 256))
        fields.append(("details_complete", false))
        fields.append(("call_return_proven", true))
        fields.append(("syntactic_call_target_admitted", true))
        fields.append(("import_attribution_admitted", false))
        fields.append(("import_attribution_admitted", 1))
        fields.append(("abi", [String: Any]()))
        fields.append(("callee_pc", 0x100001008))
        fields.append(("import_provenance.foo_proven", true))
        fields.append(("declaration.identity.source_reconstruction_allowed", true))
        let mutations = fields.map { ("calls.1.admission." + $0.0, $0.1) }
        try assertImportRefusals(importsFixture(), mutations)
        let candidate: [String: Any] = [:]
        let validation: [String: Any] = ["eligible": true]
        try assertImportRefusals(importsFixture(), [("calls.1.candidate", candidate), ("calls.1.validation", validation)])
    }

    func testImportsStubProvenanceRefusesInconsistentRecordedArithmetic() throws {
        let value = importsFixture()
        let rows = value["calls"] as! [[String: Any]]
        let admission = rows[1]["admission"] as! [String: Any]
        let provenance = admission["import_provenance"] as! [String: Any]
        let words = provenance["stub_words"] as! [[String: Any]]
        var fields: [(String, Any?)] = []
        fields.append(("stub_model", "future"))
        fields.append(("stub_words", Array(words.prefix(2))))
        fields.append(("stub_words.1.pc", 0x100001010))
        fields.append(("stub_words.0.container_file_offset", 0x200c))
        fields.append(("pointer_address", 0x100004001))
        fields.append(("pointer_address", 0x100004008))
        // Well-formed word text with the wrong instruction/register must still refuse.
        fields.append(("stub_words.0.word", "0xf0000011"))
        fields.append(("stub_words.1.word", "0xf9400231"))
        fields.append(("stub_words.2.word", "0xd61f0220"))
        fields.append(("stub_words.0.word", "0xF0000010"))
        try assertImportRefusals(value, fields.map { ("calls.1.admission.import_provenance." + $0.0, $0.1) })
    }

    func testImportsSameStubCannotCarryDifferentSymbols() throws {
        var value = importsFixture()
        var rows = value["calls"] as! [[String: Any]]
        var repeated = rows[2]
        var admission = repeated["admission"] as! [String: Any]
        repeated["call_pc"] = "0x100001000"
        admission["call_pc"] = 0x100001000
        repeated["admission"] = admission
        rows[1] = repeated; value["calls"] = rows
        try assertImportRefusals(value, [("calls.2.admission.symbol", "_$sOther")])
    }

    func testImportsDeclarationTripleAndRecognizedIdentityRefuseContradictions() throws {
        var fields: [(String, Any?)] = []
        fields.append(("status", "admitted"))
        fields.append(("identity", NSNull()))
        fields.append(("reason", "unexpected"))
        fields.append(("extra", 0))
        fields.append(("identity.symbol", "_$sOther"))
        fields.append(("identity.throws", false))
        fields.append(("identity.throws", "true"))
        fields.append(("identity.syntax_model", nil))
        fields.append(("identity.syntax_model", 1))
        try assertImportRefusals(importsFixture(), fields.map { ("calls.1.admission.declaration." + $0.0, $0.1) })
        let identity: [String: Any] = [:]
        try assertImportRefusals(importsFixture(), [("calls.2.admission.declaration.identity", identity),
                                                   ("calls.2.admission.declaration.reason", NSNull())])
    }

    func testImportsOnlyKeysRequireImportCallsiteModel() throws {
        try assertImportRefusals(importsFixture(), [("calls.1.admission.model_version", "swift-broad-callsite-v1"),
                                                   ("calls.1.admission.model_version", nil)])
    }

    func testImportsIdentityAtSerializedDepthCapAndOneLevelBeyond() throws {
        // swift_import_declarations: native limit 32 minus identity report level 5.
        let maximumIdentityValueDepth = 27
        var type: [String: Any] = ["name": "Int"]
        for _ in 0..<12 {
            let wrapper: [String: Any] = ["name": "Optional", "arguments": [type]]
            type = wrapper
        }
        // identity -> parameter_types -> element -> twelve arguments/element pairs -> name.
        let value = changingImportField(importsFixture(), "calls.1.admission.declaration.identity.parameter_types", [type])
        XCTAssertEqual(2 + 12 * 2 + 1, maximumIdentityValueDepth)
        let data = try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
        XCTAssertTrue(try SwiftFlowReport.decode(data).supportsInterpretation)
        var leafPath = "calls.1.admission.declaration.identity.parameter_types.0"
        for _ in 0..<12 { leafPath.append(".arguments.0") }
        leafPath.append(".name")
        // One child container moves the deepest scalar from report depth 32 to 33.
        let deeper = changingImportField(value, leafPath, ["arguments": "Int"])
        let tooDeep = try JSONSerialization.data(withJSONObject: deeper, options: [.sortedKeys])
        XCTAssertThrowsError(try SwiftFlowReport.decode(tooDeep))
        XCTAssertThrowsError(try decode(deeper))
    }

    func testImportsCallCountersCoverTheScanLimit() throws {
        // The imports scan limit is 2,097,152 words, so a skipped-call counter can pass 1,048,576.
        var value = importsFixture()
        var counts = value["import_stub_counts"] as! [String: Any]
        counts["non_swift_import_calls"] = 1_048_577
        value["import_stub_counts"] = counts
        value["observed_call_instructions"] = 3 + 1_048_577
        XCTAssertTrue(try decode(value).supportsInterpretation)
        counts["non_swift_import_calls"] = 2_097_153
        value["import_stub_counts"] = counts
        value["observed_call_instructions"] = 3 + 2_097_153
        XCTAssertThrowsError(try decode(value))
    }

    func testImportsStubMayEndExactlyAtTheSliceEnd() throws {
        // The second fixture stub occupies slice offsets 0x1014 up to, not including, 0x1020.
        let exact = resizingSlice(importsFixture(), to: "0x1020") as! [String: Any]
        XCTAssertTrue(try decode(exact).supportsInterpretation)
        let short = resizingSlice(importsFixture(), to: "0x101f") as! [String: Any]
        XCTAssertThrowsError(try decode(short))
    }

    func testImportsStubWordsMustBeConsecutiveInTheFile() throws {
        // Each word is individually in range and agrees with its container offset; only the order is wrong.
        let word = "calls.2.admission.import_provenance.stub_words.1."
        var value = importsFixture()
        XCTAssertTrue(try decode(value).supportsInterpretation)
        value = changingImportField(value, word + "slice_file_offset", 0x101c)
        value = changingImportField(value, word + "container_file_offset", 0x201c)
        XCTAssertThrowsError(try decode(value))
    }

    private func resizingSlice(_ node: Any, to size: String) -> Any {
        if let array = node as? [Any] { return array.map { resizingSlice($0, to: size) } }
        guard var object = node as? [String: Any] else { return node }
        for (key, child) in object { object[key] = key == "slice_size" ? size : resizingSlice(child, to: size) }
        return object
    }
}
