import Foundation
import XCTest
@testable import AIRSCore

final class SwiftBroadFlowReportTests: XCTestCase {
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
