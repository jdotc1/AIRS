import Foundation
import XCTest
@testable import AIRSCore

final class SwiftCallerErrorTestReportTests: XCTestCase {
    private func fixture() -> [String: Any] {
        let fact: [String: Any] = [
            "model": "swift-caller-error-test-v1", "shape": "swifterror_idiom", "claims_callee_behaviour": false,
            "precall": ["status": "x21_zeroed", "zero_pc": "0x1000",
                        "window": [["pc": "0x1000", "word": "0xaa1f03f5", "kind": "mov"]]],
            "postcall": ["status": "recovered_candidate", "test_pc": "0x1008", "tested_register": "x21",
                         "success_pc": "0x100c", "error_pc": "0x1010",
                         "window": [["pc": "0x1008", "word": "0xb5000055", "kind": "xcbnz"]]]
        ]
        let declaration: [String: Any] = ["status": "syntax_admitted", "reason": NSNull(),
            "identity": ["symbol": "$s5Owned4workyyKF", "throws": true, "syntax_model": "swift-import-declaration-syntax-v1"]]
        let admission: [String: Any] = ["model_version": "swift-broad-got-callsite-v1", "status": "unresolved",
            "reason": "imported_callee_abi_unqualified", "call_kind": "blr_got", "call_pc": 4100,
            "caller_start": 4096, "symbol": "$s5Owned4workyyKF", "declaration": declaration,
            "call_return_proven": false, "syntactic_call_target_admitted": false, "import_attribution_admitted": true]
        let row: [String: Any] = ["caller_pc": "0x1000", "call_pc": "0x1004", "admission": admission,
                                  "candidate": NSNull(), "validation": NSNull(), "caller_error_test": fact]
        let identity: [String: Any] = ["container_sha256": String(repeating: "a", count: 64),
            "slice_sha256": String(repeating: "b", count: 64), "architecture": "arm64", "cpu_subtype": 0,
            "uuid": NSNull(), "preferred_base": "0x1000", "slice_index": 0, "container_slice_count": 1,
            "slice_offset": "0x0", "slice_size": "0x1000"]
        return ["model_version": "swift-broad-error-flow-extended-v2", "profile": "broad-extended-v2",
            "witness_model_version": "swift-outcome-witness-v2", "validation_model_version": "swift-outcome-validation-v2",
            "identity": identity, "word_scan_complete": true, "call_details_complete": true,
            "outcome_witnesses_complete": true, "observed_call_instructions": 1, "selected_call_candidates": 1,
            "omitted_calls": 0, "scanned_words": 8, "analysis_work": 100, "research_only": true,
            "call_return_proven": false, "runtime_reachability_proven": false,
            "status_counts": ["unresolved": 1], "reason_counts": ["imported_callee_abi_unqualified": 1],
            "calls": [row], "limitations": ["structural_only", "imported_callees_attribution_only"],
            "import_stub_model": "arm64-import-stub-double-binding-v1", "import_stubs_complete": true,
            "import_stub_reason": NSNull(), "import_stub_counts": ["attributed_stubs": 0, "declined_stubs": 0,
                "invalid_stub_sections": 0, "selected_import_calls": 0, "non_throwing_swift_import_calls": 0,
                "non_swift_import_calls": 0, "declined_stub_calls": 0],
            "caller_error_test_counts": ["swifterror_idiom": 1], "caller_error_test_decline_counts": [:]]
    }

    private func decode(_ object: [String: Any]) throws -> SwiftFlowReport {
        try SwiftFlowReport.decode(JSONSerialization.data(withJSONObject: object, options: [.sortedKeys]))
    }

    func testCallerFactAcceptedAsRecordedEvidenceOnly() throws {
        let report = try decode(fixture())
        XCTAssertTrue(report.supportsInterpretation)
        XCTAssertEqual(report.calls.first?.status, "unresolved")
        XCTAssertTrue(report.calls.first?.detailJSON.contains("caller_error_test") == true)
        XCTAssertNil(report.calls.first?.witnessStatus)
    }

    func testCalleeClaimsAndMalformedCallerFactsRejected() throws {
        let original = fixture()
        let rows = try XCTUnwrap(original["calls"] as? [[String: Any]])
        let fact = try XCTUnwrap(rows[0]["caller_error_test"] as? [String: Any])
        var variants: [[String: Any]] = []
        for value in [true, 1, "false", NSNull()] as [Any] {
            var changed = fact; changed["claims_callee_behaviour"] = value; variants.append(changed)
        }
        for key in ["model", "precall", "postcall", "shape", "claims_callee_behaviour"] {
            var changed = fact; changed.removeValue(forKey: key); variants.append(changed)
        }
        var wrongShape = fact; wrongShape["shape"] = "none"; variants.append(wrongShape)
        var wrongPre = fact; wrongPre["precall"] = ["status": "x21_zeroed", "window": []]; variants.append(wrongPre)
        var wrongPost = fact; wrongPost["postcall"] = ["status": "recovered_candidate", "window": []]; variants.append(wrongPost)
        for changed in variants {
            var object = original, changedRows = rows
            changedRows[0]["caller_error_test"] = changed; object["calls"] = changedRows
            XCTAssertThrowsError(try decode(object))
        }
        var missing = original, missingRows = rows
        missingRows[0].removeValue(forKey: "caller_error_test"); missing["calls"] = missingRows
        XCTAssertThrowsError(try decode(missing))
        var counters = original; counters["caller_error_test_counts"] = ["swifterror_idiom": 2]
        XCTAssertThrowsError(try decode(counters))
    }

    func testCallerFactValidationIsLimitedToNewProfile() throws {
        var object = fixture(), rows = try XCTUnwrap(object["calls"] as? [[String: Any]])
        rows[0]["caller_error_test"] = ["claims_callee_behaviour": true]; object["calls"] = rows
        object["model_version"] = "swift-broad-error-flow-extended-v1"; object["profile"] = "broad-extended-v1"
        XCTAssertTrue(try decode(object).supportsInterpretation)
    }

    func testNonthrowingDisagreementRequiresTheFullIdiom() throws {
        var object = fixture(), rows = try XCTUnwrap(object["calls"] as? [[String: Any]])
        var admission = try XCTUnwrap(rows[0]["admission"] as? [String: Any])
        var declaration = try XCTUnwrap(admission["declaration"] as? [String: Any])
        var identity = try XCTUnwrap(declaration["identity"] as? [String: Any])
        identity["throws"] = false; declaration["identity"] = identity; admission["declaration"] = declaration
        admission["reason"] = "declaration_caller_disagreement"; rows[0]["admission"] = admission
        object["calls"] = rows; object["reason_counts"] = ["declaration_caller_disagreement": 1]
        XCTAssertEqual(try decode(object).calls.first?.reason, "declaration_caller_disagreement")
        var fact = try XCTUnwrap(rows[0]["caller_error_test"] as? [String: Any])
        fact["precall"] = ["status": "x21_not_zeroed", "window": []]; fact["shape"] = "postcall_test_only"
        rows[0]["caller_error_test"] = fact; object["calls"] = rows
        object["caller_error_test_counts"] = ["postcall_test_only": 1]
        object["caller_error_test_decline_counts"] = [:]
        XCTAssertThrowsError(try decode(object))
    }
}
