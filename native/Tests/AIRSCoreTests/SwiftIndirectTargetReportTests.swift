import Foundation
import XCTest
@testable import AIRSCore

final class SwiftIndirectTargetReportTests: XCTestCase {
    private func shape() -> [String: Any] {
        ["model": "swift-indirect-target-shape-v1", "site_pc": "0x100c", "site_kind": "blr", "class": "value_witness",
         "slot_offset": 8, "unknown_reason": NSNull(),
         "deciding_instructions": [["pc": "0x1000", "word": "0x94000005", "role": "metadata_call_result"],
                                   ["pc": "0x1004", "word": "0xf85f8008", "role": "table_load"],
                                   ["pc": "0x1008", "word": "0xf9400508", "role": "target_load"],
                                   ["pc": "0x100c", "word": "0xd63f0100", "role": "indirect_branch"]],
         "evidence": "table base loaded from [x0, #-8]", "class_before_join_refusal": NSNull(),
         "slot_address": NSNull(), "slot_section": NSNull(), "claims_callee_behaviour": false,
         "bounds": ["window_words": 256, "max_register_hops": 6, "max_function_words": 262144]]
    }

    private func witness() -> [String: Any] {
        ["model": "swift-value-witness-admission-v1", "admitted": true, "provenance_kind": "imported_metadata_accessor_call",
         "first_failing_condition": NSNull(), "reason": "meets_tier2_conditions", "site_pc": "0x100c", "site_kind": "blr",
         "slot_offset": 8, "metadata_register": "x0", "symbol": "_$sSS10FoundationE8EncodingVMa",
         "metadata_callee_pc": "0x1014", "claims_callee_behaviour": false,
         "abi_basis": "value_witness_function_slots_cannot_throw"]
    }

    private func fixture() -> [String: Any] {
        let admission: [String: Any] = ["model_version": "swift-broad-callsite-v1", "status": "declined",
            "reason": "value_witness_abi_nonthrowing", "call_pc": 4108, "details_complete": true]
        let row: [String: Any] = ["caller_pc": "0x1000", "call_pc": "0x100c", "admission": admission, "candidate": NSNull(),
                                  "validation": NSNull(), "indirect_target_shape": shape(), "value_witness_admission": witness()]
        let identity: [String: Any] = ["container_sha256": String(repeating: "a", count: 64),
            "slice_sha256": String(repeating: "b", count: 64), "architecture": "arm64", "cpu_subtype": 0,
            "uuid": NSNull(), "preferred_base": "0x1000", "slice_index": 0, "container_slice_count": 1,
            "slice_offset": "0x0", "slice_size": "0x1000"]
        return ["model_version": "swift-broad-error-flow-extended-v3", "profile": "broad-extended-v3",
            "witness_model_version": "swift-outcome-witness-v2", "validation_model_version": "swift-outcome-validation-v2",
            "identity": identity, "word_scan_complete": true, "call_details_complete": true,
            "outcome_witnesses_complete": true, "observed_call_instructions": 1, "selected_call_candidates": 1,
            "omitted_calls": 0, "scanned_words": 8, "analysis_work": 100, "research_only": true,
            "call_return_proven": false, "runtime_reachability_proven": false,
            "status_counts": ["declined": 1], "reason_counts": ["value_witness_abi_nonthrowing": 1],
            "calls": [row],
            "limitations": ["structural_only", "imported_callees_attribution_only",
                            "indirect_target_shape_does_not_claim_callee_behaviour",
                            "value_witness_admission_by_abi_with_recorded_provenance"],
            "import_stub_model": "arm64-import-stub-double-binding-v1", "import_stubs_complete": true,
            "import_stub_reason": NSNull(), "import_stub_counts": ["attributed_stubs": 0, "declined_stubs": 0,
                "invalid_stub_sections": 0, "selected_import_calls": 0, "non_throwing_swift_import_calls": 0,
                "non_swift_import_calls": 0, "declined_stub_calls": 0],
            "caller_error_test_counts": [:], "caller_error_test_decline_counts": [:],
            "indirect_target_shape_model": "swift-indirect-target-shape-v1",
            "value_witness_admission_model": "swift-value-witness-admission-v1",
            "indirect_target_shape_counts": ["value_witness": 1],
            "value_witness_admission_counts": ["admitted": 1, "refused": 0],
            "value_witness_refusal_condition_counts": [:]]
    }

    private func decode(_ object: [String: Any]) throws -> SwiftFlowReport {
        try SwiftFlowReport.decode(JSONSerialization.data(withJSONObject: object, options: [.sortedKeys]))
    }

    private func withRow(_ change: (inout [String: Any]) -> Void, report: (inout [String: Any]) -> Void = { _ in }) -> [String: Any] {
        var object = fixture(), rows = object["calls"] as! [[String: Any]]
        change(&rows[0]); object["calls"] = rows; report(&object)
        return object
    }

    private func mutateShape(_ change: @escaping (inout [String: Any]) -> Void) -> [String: Any] {
        withRow { row in var value = row["indirect_target_shape"] as! [String: Any]; change(&value); row["indirect_target_shape"] = value }
    }

    private func mutateWitness(_ change: @escaping (inout [String: Any]) -> Void) -> [String: Any] {
        withRow { row in var value = row["value_witness_admission"] as! [String: Any]; change(&value); row["value_witness_admission"] = value }
    }

    func testAdmittedPairAcceptedAsRecordedEvidenceOnly() throws {
        let report = try decode(fixture())
        XCTAssertTrue(report.supportsInterpretation)
        XCTAssertEqual(report.calls.first?.status, "declined")
        XCTAssertEqual(report.calls.first?.reason, "value_witness_abi_nonthrowing")
        XCTAssertTrue(report.calls.first?.detailJSON.contains("indirect_target_shape") == true)
    }

    func testRefusedSiteKeepsItsRowAndRecords() throws {
        var object = withRow { row in
            var admission = row["admission"] as! [String: Any]
            admission["status"] = "unresolved"; admission["reason"] = "indirect_target_unresolved"; row["admission"] = admission
            var refused = row["value_witness_admission"] as! [String: Any]
            refused["admitted"] = false; refused["first_failing_condition"] = 2; refused["reason"] = "metadata_stack_transport_not_admitted"
            refused["provenance_kind"] = "stack_transport"; row["value_witness_admission"] = refused
        }
        object["status_counts"] = ["unresolved": 1]; object["reason_counts"] = ["indirect_target_unresolved": 1]
        object["value_witness_admission_counts"] = ["admitted": 0, "refused": 1]
        object["value_witness_refusal_condition_counts"] = ["2": 1]
        XCTAssertEqual(try decode(object).calls.first?.status, "unresolved")
        object["value_witness_refusal_condition_counts"] = ["3": 1]
        XCTAssertThrowsError(try decode(object))
    }

    func testMalformedShapeRecordsRejected() throws {
        var variants: [[String: Any]] = []
        for value in [true, 1, "false", NSNull()] as [Any] { variants.append(mutateShape { $0["claims_callee_behaviour"] = value }) }
        for key in ["model", "class", "site_pc", "site_kind", "slot_offset", "deciding_instructions", "bounds", "claims_callee_behaviour"] {
            variants.append(mutateShape { $0.removeValue(forKey: key) })
        }
        variants.append(mutateShape { $0["model"] = "swift-indirect-target-shape-v2" })
        variants.append(mutateShape { $0["class"] = "mystery" })
        variants.append(mutateShape { $0["site_pc"] = "0x1010" })
        variants.append(mutateShape { $0["site_pc"] = "4108" })
        variants.append(mutateShape { $0["slot_offset"] = "8" })
        variants.append(mutateShape { $0["slot_offset"] = -0x1000 })
        variants.append(mutateShape { $0["site_kind"] = 7 })
        variants.append(mutateShape { $0["deciding_instructions"] = [["pc": "0x1000", "word": "94000005", "role": "metadata_call_result"]] })
        variants.append(mutateShape { $0["deciding_instructions"] = [["pc": "0x1000", "word": "0x94000005"]] })
        for object in variants { XCTAssertThrowsError(try decode(object)) }
        XCTAssertThrowsError(try decode(withRow { $0.removeValue(forKey: "indirect_target_shape") }))
        XCTAssertThrowsError(try decode(withRow { $0.removeValue(forKey: "value_witness_admission") }))
    }

    func testAdmissionWithoutRecordedTierTwoProvenanceRejected() throws {
        var variants: [[String: Any]] = []
        for value in [true, 1, NSNull()] as [Any] { variants.append(mutateWitness { $0["claims_callee_behaviour"] = value }) }
        variants.append(mutateWitness { $0["provenance_kind"] = "isa_load" })
        variants.append(mutateWitness { $0["provenance_kind"] = "stack_transport" })
        variants.append(mutateWitness { $0["first_failing_condition"] = 1 })
        variants.append(mutateWitness { $0["reason"] = "isa_is_not_proven_swift_metadata" })
        variants.append(mutateWitness { $0["metadata_register"] = "x1" })
        variants.append(mutateWitness { $0["metadata_register"] = NSNull() })
        variants.append(mutateWitness { $0["symbol"] = "_swift_retain" })
        variants.append(mutateWitness { $0["symbol"] = NSNull() })
        variants.append(mutateWitness { $0["symbol"] = "" })
        variants.append(mutateWitness { $0["provenance_kind"] = "runtime_metadata_call" })
        variants.append(mutateWitness { $0["slot_offset"] = 16 })
        variants.append(mutateWitness { $0["metadata_callee_pc"] = "0x1018" })
        variants.append(mutateWitness { $0.removeValue(forKey: "metadata_callee_pc") })
        variants.append(mutateShape { $0["slot_offset"] = 0x40; })
        variants.append(mutateShape { $0["class"] = "class_vtable" })
        variants.append(mutateShape {
            $0["deciding_instructions"] = [["pc": "0x1000", "word": "0xaa0003e0", "role": "metadata_call_result"],
                                           ["pc": "0x100c", "word": "0xd63f0100", "role": "indirect_branch"]]
        })
        variants.append(mutateShape {
            $0["deciding_instructions"] = [["pc": "0x100c", "word": "0xd63f0100", "role": "indirect_branch"]]
        })
        for object in variants { XCTAssertThrowsError(try decode(object)) }
        let wrongReason = withRow { row in
            var admission = row["admission"] as! [String: Any]
            admission["reason"] = "indirect_target_unresolved"; admission["status"] = "unresolved"; row["admission"] = admission
        }
        XCTAssertThrowsError(try decode(wrongReason))
        let runtime = mutateWitness { $0["provenance_kind"] = "runtime_metadata_call"; $0["symbol"] = "swift_getGenericMetadata" }
        XCTAssertTrue(try decode(runtime).supportsInterpretation)
    }

    func testNegativeSlotOnUnknownClassShapeAccepted() throws {
        var object = withRow { row in
            var admission = row["admission"] as! [String: Any]
            admission["status"] = "unresolved"; admission["reason"] = "indirect_target_unresolved"; row["admission"] = admission
            var shape = row["indirect_target_shape"] as! [String: Any]
            shape["class"] = "unknown"; shape["slot_offset"] = -16; shape["unknown_reason"] = "value_witness_offset_not_function_slot"
            row["indirect_target_shape"] = shape
            var refused = row["value_witness_admission"] as! [String: Any]
            refused["admitted"] = false; refused["first_failing_condition"] = 1; refused["reason"] = "value_witness_offset_not_function_slot"
            refused["slot_offset"] = -16; refused["provenance_kind"] = "none"; row["value_witness_admission"] = refused
        }
        object["status_counts"] = ["unresolved": 1]; object["reason_counts"] = ["indirect_target_unresolved": 1]
        object["indirect_target_shape_counts"] = ["unknown": 1]
        object["value_witness_admission_counts"] = ["admitted": 0, "refused": 1]
        object["value_witness_refusal_condition_counts"] = ["1": 1]
        XCTAssertEqual(try decode(object).calls.first?.status, "unresolved")
    }

    func testAdmittedMetadataCopiedThroughMovAccepted() throws {
        func copied(_ words: [(String, String)], register: String) -> [String: Any] {
            withRow { row in
                var shape = row["indirect_target_shape"] as! [String: Any]
                var deciding = shape["deciding_instructions"] as! [[String: Any]]
                for (pc, word) in words { deciding.append(["pc": pc, "word": word, "role": "metadata_copy"]) }
                shape["deciding_instructions"] = deciding; row["indirect_target_shape"] = shape
                var w = row["value_witness_admission"] as! [String: Any]
                w["metadata_register"] = register; row["value_witness_admission"] = w
            }
        }
        // mov x22, x0 ; add x23, x22, #0 ; the chain must end in the named register
        XCTAssertTrue(try decode(copied([("0x1020", "0xaa0003f6")], register: "x22")).supportsInterpretation)
        XCTAssertTrue(try decode(copied([("0x1020", "0xaa0003f6"), ("0x1024", "0x910002d7")], register: "x23")).supportsInterpretation)
        XCTAssertThrowsError(try decode(mutateWitness { $0["metadata_register"] = "x22" }))
        XCTAssertThrowsError(try decode(copied([("0x1020", "0xaa0003f6")], register: "x23")))
        XCTAssertThrowsError(try decode(copied([("0x1020", "0xaa0103f6")], register: "x22")))
        XCTAssertThrowsError(try decode(copied([("0x1020", "0x91000ad6")], register: "x22")))
    }

    func testCountersMustMatchRetainedRows() throws {
        for (key, value) in [("indirect_target_shape_counts", ["value_witness": 2]),
                             ("indirect_target_shape_counts", ["unknown": 1]),
                             ("value_witness_admission_counts", ["admitted": 0, "refused": 1]),
                             ("value_witness_refusal_condition_counts", ["1": 1])] as [(String, [String: Int])] {
            var object = fixture(); object[key] = value
            XCTAssertThrowsError(try decode(object))
        }
        for key in ["indirect_target_shape_model", "value_witness_admission_model"] {
            var object = fixture(); object[key] = "other"; XCTAssertThrowsError(try decode(object))
            var missing = fixture(); missing.removeValue(forKey: key); XCTAssertThrowsError(try decode(missing))
        }
        var limits = fixture(); limits["limitations"] = ["structural_only", "imported_callees_attribution_only"]
        XCTAssertThrowsError(try decode(limits))
    }

    func testIndirectValidationIsLimitedToTheNewProfile() throws {
        var object = fixture()
        object["model_version"] = "swift-broad-error-flow-extended-v2"; object["profile"] = "broad-extended-v2"
        var rows = object["calls"] as! [[String: Any]]
        rows[0]["indirect_target_shape"] = ["claims_callee_behaviour": true]; object["calls"] = rows
        object.removeValue(forKey: "indirect_target_shape_model")
        XCTAssertTrue(try decode(object).supportsInterpretation)
    }
}
