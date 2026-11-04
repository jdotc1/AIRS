import Foundation
import XCTest
@testable import AIRSCore

final class ManualPairChangeTests: XCTestCase {
    private let oldID = "airsf-" + String(repeating: "a", count: 64)
    private let newID = "airsf-" + String(repeating: "b", count: 64)
    private func source(_ name: String, id: String, digest: String, config: Any? = nil, model: String = "arm64-bounded-test-bit-branch-v50") throws -> Data {
        var value: [String: Any] = [
            "schema_version": 1, "report_kind": "airs.audit",
            "generator": ["name": "AIRS", "version": "0.3.3", "analysis_model_version": model],
            "image": ["display_name": name, "architecture": "arm64", "file_type": "dylib", "preferred_base": "0x1000",
                      "container_sha256": String(repeating: "0", count: 64), "slice_sha256": String(repeating: digest, count: 64),
                      "cpu_subtype": 0, "slice_offset": 0, "slice_size": 16],
            "summary": ["function_count": 1, "agreement_count": 1, "inconsistency_count": 0, "unresolved_count": 0,
                        "metadata_entry_count": 1, "checked_pc_count": 1],
            "issues": [], "limitations": ["Synthetic compatibility test"],
            "metadata_ranges": [["start": "0x1000", "end": "0x1010", "encoding": "0x04000000", "mode": "frame"]],
            "findings": [["id": id, "function": ["name": name, "address": "0x1000", "end_address": "0x1010", "image_offset": "0x0",
                                                  "size": 16, "boundary_source": "lc_function_starts"],
                          "verdict": "agreement", "coverage": "compact", "mode": "frame", "scope": "synchronous_call_sites",
                          "encoding": "0x04000000", "checked_pcs": ["0x1008"], "instruction_count": 4,
                          "reason_codes": ["supported_model_agreement"], "evidence": [], "limitations": []]]]
        if let config { value["analysis_config"] = config }
        return try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    }

    private func object(_ data: Data) throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    private func edit(_ data: Data, fields: [String: Any] = [:], function: [String: Any] = [:]) throws -> Data {
        var report = try object(data)
        var findings = try XCTUnwrap(report["findings"] as? [[String: Any]])
        var finding = findings[0]
        for (key, value) in fields { finding[key] = value }
        var info = try XCTUnwrap(finding["function"] as? [String: Any])
        for (key, value) in function { info[key] = value }
        finding["function"] = info; findings[0] = finding; report["findings"] = findings
        var summary = try XCTUnwrap(report["summary"] as? [String: Any])
        for verdict in ["agreement", "inconsistency", "unresolved"] {
            summary[verdict + "_count"] = (finding["verdict"] as? String) == verdict ? 1 : 0
        }
        summary["checked_pc_count"] = (finding["checked_pcs"] as? [String])?.count ?? 0
        report["summary"] = summary
        return try JSONSerialization.data(withJSONObject: report)
    }

    private func comparison(_ label: String, before: Data, after: Data) throws -> ComparisonReport {
        let old = try object(before), new = try object(after)
        let oldFindings = try XCTUnwrap(old["findings"] as? [[String: Any]])
        let newFindings = try XCTUnwrap(new["findings"] as? [[String: Any]])
        let oldGenerator = try XCTUnwrap(old["generator"] as? [String: Any])
        let newGenerator = try XCTUnwrap(new["generator"] as? [String: Any])
        let oldImage = try XCTUnwrap(old["image"] as? [String: Any]), newImage = try XCTUnwrap(new["image"] as? [String: Any])
        let value: [String: Any] = ["schema_version": 1, "report_kind": "airs.diff",
            "comparison": ["baseline_image": oldImage, "current_image": newImage, "same_image": false,
                "model_compatible": (oldGenerator["analysis_model_version"] as? String) == (newGenerator["analysis_model_version"] as? String),
                "matching_policy": "manual_then_unique_symbol", "manual_pairs": [["baseline_id": oldID, "current_id": newID]]],
            "summary": ["matched_count": 1, "changed_count": label == "changed" ? 1 : 0, "unchanged_count": label == "unchanged" ? 1 : 0,
                        "ambiguous_count": label == "ambiguous" ? 1 : 0, "added_count": 0, "removed_count": 0],
            "changes": [["key": "manual:pair", "match_basis": "manual_review", "function_name": "after",
                "baseline_id": oldID, "current_id": newID, "change": label,
                "before_verdict": oldFindings[0]["verdict"] ?? "", "after_verdict": newFindings[0]["verdict"] ?? "",
                "before_scope": oldFindings[0]["scope"] ?? "", "after_scope": newFindings[0]["scope"] ?? "", "notes": []]], "limitations": []]
        return try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
    }

    private func pair() throws -> (Data, Data) {
        (try source("before", id: oldID, digest: "1"), try source("after", id: newID, digest: "2"))
    }

    private func validate(_ label: String, before: Data, after: Data) throws {
        try comparison(label, before: before, after: after).validateManualPairChanges(baselineData: before, currentData: after)
    }

    func testEquivalentFindingsRejectAChangedClaim() throws {
        let (before, after) = try pair()
        XCTAssertNoThrow(try validate("unchanged", before: before, after: after))
        XCTAssertThrowsError(try validate("changed", before: before, after: after))
    }

    private func relocate(_ data: Data, to base: UInt64) throws -> Data {
        var report = try object(data)
        var findings = try XCTUnwrap(report["findings"] as? [[String: Any]])
        var finding = findings[0], function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        let hex: (UInt64) -> String = { "0x" + String($0, radix: 16) }
        let prior = try XCTUnwrap(UInt64(String(try XCTUnwrap(function["address"] as? String).dropFirst(2)), radix: 16))
        func moved(_ text: String) throws -> String {
            let old = try XCTUnwrap(UInt64(text.dropFirst(2), radix: 16))
            return hex(old < prior ? base - (prior - old) : base + (old - prior))
        }
        function["address"] = hex(base); function["end_address"] = hex(base + 16)
        finding["function"] = function
        finding["checked_pcs"] = try XCTUnwrap(finding["checked_pcs"] as? [String]).map(moved)
        var evidence = try XCTUnwrap(finding["evidence"] as? [[String: Any]])
        for index in evidence.indices { if let address = evidence[index]["address"] as? String { evidence[index]["address"] = try moved(address) } }
        finding["evidence"] = evidence; findings[0] = finding; report["findings"] = findings
        var image = try XCTUnwrap(report["image"] as? [String: Any]); image["preferred_base"] = hex(base); report["image"] = image
        report["metadata_ranges"] = [["start": hex(base), "end": hex(base + 16), "encoding": "0x04000000", "mode": "frame"]]
        return try JSONSerialization.data(withJSONObject: report)
    }

    func testRelocationKeepsRelativeObservationIdentity() throws {
        let (before, after) = try pair()
        let shifted = try relocate(after, to: 0x8000000000000000)
        XCTAssertNoThrow(try validate("unchanged", before: before, after: shifted))
    }

    func testEachObservationFieldCanRequireChangedClassification() throws {
        let before = try source("before", id: oldID, digest: "1", model: "future-model")
        let after = try source("after", id: newID, digest: "2", model: "future-model")
        let changes: [[String: Any]] = [
            ["verdict": "inconsistency"], ["coverage": "dwarf_reference"], ["mode": "frameless"],
            ["scope": "modeled_leaf_body"], ["encoding": "0x4000000"],
            ["checked_pcs": ["0x100c"]], ["reason_codes": ["new_reason"]]]
        for fields in changes {
            let edited = try edit(after, fields: fields)
            XCTAssertNoThrow(try validate("changed", before: before, after: edited))
            XCTAssertThrowsError(try validate("unchanged", before: before, after: edited))
        }
    }

    func testReasonsSortButRetainDuplicateCounts() throws {
        let (before, after) = try pair()
        let old = try edit(before, fields: ["reason_codes": ["z", "a"]])
        let reordered = try edit(after, fields: ["reason_codes": ["a", "z"]])
        XCTAssertNoThrow(try validate("unchanged", before: old, after: reordered))
        let repeated = try edit(after, fields: ["reason_codes": ["a", "z", "z"]])
        XCTAssertNoThrow(try validate("changed", before: old, after: repeated))
    }

    func testEvidenceFactsAndOrderParticipate() throws {
        let (before, after) = try pair()
        let item: [String: Any] = ["code": "observation", "message": "Display text", "address": "0x1004", "expected": "caller", "observed": "saved"]
        let old = try edit(before, fields: ["evidence": [item]])
        for field in ["code", "expected", "observed", "address"] {
            var changed = item; changed[field] = field == "address" ? "0x1008" : "different"
            let new = try edit(after, fields: ["evidence": [changed]])
            XCTAssertNoThrow(try validate("changed", before: old, after: new))
            XCTAssertThrowsError(try validate("unchanged", before: old, after: new))
        }
        var second = item; second["code"] = "second"
        let ordered = try edit(before, fields: ["evidence": [item, second]])
        let reversed = try edit(after, fields: ["evidence": [second, item]])
        XCTAssertNoThrow(try validate("changed", before: ordered, after: reversed))
    }

    func testDisplayTextAndNonSignatureFieldsDoNotInventChanges() throws {
        let (before, after) = try pair()
        let old = try edit(before, fields: ["evidence": [["code": "fact", "message": "Before"]]])
        let new = try edit(after, fields: ["evidence": [["code": "fact", "message": "After"]], "limitations": ["Different prose"], "instruction_count": 9], function: ["name": "Renamed"])
        XCTAssertNoThrow(try validate("unchanged", before: old, after: new))
    }

    func testMissingAndNullEvidenceRemainEquivalentButEmptyStringDiffers() throws {
        let (before, after) = try pair()
        let old = try edit(before, fields: ["evidence": [["code": "fact", "message": "One"]]])
        let null = try edit(after, fields: ["evidence": [["code": "fact", "message": "Two", "expected": NSNull(), "observed": NSNull(), "address": NSNull()]]])
        XCTAssertNoThrow(try validate("unchanged", before: old, after: null))
        let empty = try edit(after, fields: ["evidence": [["code": "fact", "message": "Two", "expected": ""]]])
        XCTAssertNoThrow(try validate("changed", before: old, after: empty))
    }

    func testNegativeEvidenceOffsetsStaySignedWithoutClamping() throws {
        let (before, after) = try pair()
        let old = try edit(before, fields: ["evidence": [["code": "fact", "message": "One", "address": "0xffc"]]])
        let new = try edit(after, fields: ["evidence": [["code": "fact", "message": "Two", "address": "0xffc"]]])
        XCTAssertNoThrow(try validate("unchanged", before: old, after: relocate(new, to: 0x8000000000000000)))
        let above = try edit(after, fields: ["evidence": [["code": "fact", "message": "Two", "address": "0x1004"]]])
        XCTAssertNoThrow(try validate("changed", before: old, after: above))
    }

    func testUnicodeWireDifferencesAreNotCanonicalizedAway() throws {
        let (before, after) = try pair()
        let composed = "\u{e9}", decomposed = "e\u{301}"
        for key in ["code", "expected", "observed"] {
            var oldEvidence: [String: Any] = ["code": "fact", "message": "One"]
            var newEvidence = oldEvidence; oldEvidence[key] = composed; newEvidence[key] = decomposed
            let old = try edit(before, fields: ["evidence": [oldEvidence]])
            let new = try edit(after, fields: ["evidence": [newEvidence]])
            XCTAssertNoThrow(try validate("changed", before: old, after: new))
            XCTAssertThrowsError(try validate("unchanged", before: old, after: new))
        }
        XCTAssertNoThrow(try validate("changed", before: edit(before, fields: ["reason_codes": [composed]]), after: edit(after, fields: ["reason_codes": [decomposed]])))
    }

    func testIncompatibleInputsStayAmbiguousAndCompatibleAmbiguityRejects() throws {
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate("ambiguous", before: before, after: after))
        let incompatible = try source("after", id: newID, digest: "2", model: "future-model")
        XCTAssertNoThrow(try validate("ambiguous", before: before, after: incompatible))
        XCTAssertThrowsError(try validate("changed", before: before, after: incompatible))
        let configured = try source("after", id: newID, digest: "2", config: ["limits": ["work": 1]])
        XCTAssertNoThrow(try validate("ambiguous", before: before, after: configured))
    }

    func testCanonicallyEquivalentModelLabelsDoNotBecomeCompatible() throws {
        let before = try source("before", id: oldID, digest: "1", model: "future-\u{e9}")
        let after = try source("after", id: newID, digest: "2", model: "future-e\u{301}")
        XCTAssertThrowsError(try validate("unchanged", before: before, after: after))
    }

    func testPrerequisiteSourceBindingCannotBeSkipped() throws {
        let (before, after) = try pair()
        let report = try comparison("unchanged", before: before, after: after)
        let unrelated = try source("other", id: newID, digest: "3")
        XCTAssertThrowsError(try report.validateManualPairChanges(baselineData: before, currentData: unrelated))
    }

    func testCheckedPCOrderingIsPartOfTheObservation() throws {
        let (before, after) = try pair()
        let old = try edit(before, fields: ["checked_pcs": ["0x1004", "0x1008"]])
        let new = try edit(after, fields: ["checked_pcs": ["0x1008", "0x1004"]])
        XCTAssertNoThrow(try validate("changed", before: old, after: new))
        XCTAssertThrowsError(try validate("unchanged", before: old, after: new))
    }

    func testNonmanualRowsAndSummaryIntegrityRemainOutsideThisAPI() throws {
        let (before, after) = try pair()
        var value = try object(JSONEncoder().encode(comparison("unchanged", before: before, after: after)))
        var rows = try XCTUnwrap(value["changes"] as? [[String: Any]])
        rows.append(["key": "outside", "match_basis": "unmatched", "function_name": "Other", "change": "future_change", "notes": []])
        value["changes"] = rows
        value["summary"] = ["matched_count": 99, "changed_count": 0, "unchanged_count": 1, "added_count": 0, "removed_count": 0, "ambiguous_count": 0]
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: value))
        XCTAssertNoThrow(try report.validateManualPairChanges(baselineData: before, currentData: after))
        XCTAssertEqual(report.summary.matchedCount, 99)
        XCTAssertEqual(report.changes.count, 2)
    }
}
