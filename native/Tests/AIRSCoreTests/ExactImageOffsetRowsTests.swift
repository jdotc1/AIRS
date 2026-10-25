import Foundation
import XCTest
@testable import AIRSCore

final class ExactImageOffsetRowsTests: XCTestCase {
    private let oldID = "airsf-" + String(repeating: "a", count: 64)
    private let newID = "airsf-" + String(repeating: "b", count: 64)
    private let unknownID = "airsf-" + String(repeating: "c", count: 64)
    private func source(_ name: String, id: String, digest: String) throws -> Data {
        try JSONSerialization.data(withJSONObject: [
            "schema_version": 1, "report_kind": "airs.audit",
            "generator": ["name": "AIRS", "version": "0.3.3", "analysis_model_version": "arm64-bounded-test-bit-branch-v50"],
            "image": ["display_name": name, "architecture": "arm64", "file_type": "dylib", "preferred_base": "0x1000",
                      "container_sha256": String(repeating: "0", count: 64), "slice_sha256": String(repeating: digest, count: 64),
                      "cpu_subtype": 0, "slice_offset": 0, "slice_size": 16],
            "summary": ["function_count": 1, "agreement_count": 1, "inconsistency_count": 0, "unresolved_count": 0,
                        "metadata_entry_count": 1, "checked_pc_count": 1],
            "issues": [], "limitations": ["Synthetic binding test; identity is not authenticated"],
            "metadata_ranges": [["start": "0x1000", "end": "0x1010", "encoding": "0x04000000", "mode": "frame"]],
            "findings": [["id": id, "function": ["name": name, "address": "0x1000", "end_address": "0x1010",
                                                  "image_offset": "0x0", "size": 16, "boundary_source": "lc_function_starts"],
                          "verdict": "agreement", "coverage": "compact", "mode": "frame", "scope": "synchronous_call_sites",
                          "encoding": "0x04000000", "checked_pcs": ["0x1008"], "instruction_count": 4,
                          "reason_codes": ["supported_model_agreement"], "evidence": [], "limitations": []]]])
    }

    private func object(_ data: Data) throws -> [String: Any] {
        try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
    }

    private func row(_ key: String = "symbol:pair", basis: String = "unique_symbol", label: String = "unchanged", old: String?, new: String?) -> [String: Any] {
        var value: [String: Any] = ["key": key, "match_basis": basis, "function_name": "Candidate", "change": label, "notes": []]
        if let old { value["baseline_id"] = old; value["before_verdict"] = "agreement"; value["before_scope"] = "synchronous_call_sites" }
        if let new { value["current_id"] = new; value["after_verdict"] = "agreement"; value["after_scope"] = "synchronous_call_sites" }
        return value
    }

    private func wire(_ rows: [[String: Any]], before: Data, after: Data) throws -> [String: Any] {
        let old = try object(before), new = try object(after)
        let oldImage = try XCTUnwrap(old["image"] as? [String: Any]), newImage = try XCTUnwrap(new["image"] as? [String: Any])
        let oldGenerator = try XCTUnwrap(old["generator"] as? [String: Any]), newGenerator = try XCTUnwrap(new["generator"] as? [String: Any])
        let context: [String: Any] = ["baseline_image": oldImage, "current_image": newImage,
            "same_image": (oldImage["slice_sha256"] as? String) == (newImage["slice_sha256"] as? String) && (oldImage["architecture"] as? String) == (newImage["architecture"] as? String),
            "model_compatible": (oldGenerator["analysis_model_version"] as? String) == (newGenerator["analysis_model_version"] as? String) && (oldImage["architecture"] as? String) == (newImage["architecture"] as? String),
            "matching_policy": "exact_digest_then_unique_symbol"]
        var summary = ["matched_count": rows.filter { $0["baseline_id"] is String && $0["current_id"] is String }.count]
        for label in ["changed", "unchanged", "added", "removed", "ambiguous"] {
            summary[label + "_count"] = rows.filter { ($0["change"] as? String) == label }.count
        }
        return ["schema_version": 1, "report_kind": "airs.diff", "comparison": context,
                "summary": summary, "changes": rows, "limitations": ["Synthetic selected facts only"]]
    }

    private func pair() throws -> (Data, Data) {
        (try source("before", id: oldID, digest: "1"), try source("after", id: newID, digest: "2"))
    }

    private func validate(_ rows: [[String: Any]], before: Data, after: Data) throws {
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: wire(rows, before: before, after: after)))
        try report.validateExactImageOffsetRows(baselineData: before, currentData: after)
    }

    func testDifferentImagesCannotClaimExactImageOffsetAuthority() throws {
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: after))
    }

    private func sameImagePair() throws -> (Data, Data) {
        (try source("before", id: oldID, digest: "1"), try source("after", id: newID, digest: "1"))
    }

    private func changed(_ data: Data, top: [String: Any] = [:], fields: [String: Any] = [:], function: [String: Any] = [:]) throws -> Data {
        var report = try object(data)
        for (key, value) in top { report[key] = value }
        var findings = try XCTUnwrap(report["findings"] as? [[String: Any]])
        for (key, value) in fields { findings[0][key] = value }
        var info = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        for (key, value) in function { info[key] = value }
        findings[0]["function"] = info; report["findings"] = findings
        return try JSONSerialization.data(withJSONObject: report)
    }

    private func moved(_ data: Data, offset: UInt64, base: UInt64 = 0x1000) throws -> Data {
        let hex: (UInt64) -> String = { "0x" + String($0, radix: 16) }
        var image = try XCTUnwrap(object(data)["image"] as? [String: Any]); image["preferred_base"] = hex(base); image["slice_size"] = offset + 16
        return try changed(data,
            top: ["image": image, "metadata_ranges": [["start": hex(base + offset), "end": hex(base + offset + 16), "encoding": "0x04000000", "mode": "frame"]]],
            fields: ["checked_pcs": [hex(base + offset + 8)]],
            function: ["address": hex(base + offset), "end_address": hex(base + offset + 16), "image_offset": hex(offset)])
    }

    private func additional(_ data: Data, id: String, offset: UInt64) throws -> Data {
        var report = try object(data), findings = try XCTUnwrap(object(data)["findings"] as? [[String: Any]])
        let addition = try moved(data, offset: offset)
        var extra = try XCTUnwrap(object(addition)["findings"] as? [[String: Any]])[0]; extra["id"] = id; findings.append(extra); report["findings"] = findings
        var ranges = try XCTUnwrap(report["metadata_ranges"] as? [[String: Any]])
        if offset != 0 { ranges += try XCTUnwrap(object(addition)["metadata_ranges"] as? [[String: Any]]) }
        report["metadata_ranges"] = ranges
        report["summary"] = ["function_count": 2, "agreement_count": 2, "inconsistency_count": 0, "unresolved_count": 0, "metadata_entry_count": ranges.count, "checked_pc_count": 2]
        var image = try XCTUnwrap(report["image"] as? [String: Any]); image["slice_size"] = max(16, offset + 16); report["image"] = image
        return try JSONSerialization.data(withJSONObject: report)
    }

    func testUniqueSameImagePairUsesNumericOffsetsNotAbsoluteAddresses() throws {
        let (before, after) = try sameImagePair()
        let shifted = try moved(after, offset: 0, base: 0x8000000000000000)
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: shifted))
        let padded = try changed(after, function: ["image_offset": "0x0000"])
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: padded))
    }

    func testSameImageAuthorityCannotBeReplacedByAnotherBasis() throws {
        let (before, after) = try sameImagePair()
        for basis in ["unique_symbol", "exact_body_candidate", "future_matcher"] {
            XCTAssertThrowsError(try validate([row("offset:0x0", basis: basis, old: oldID, new: newID)], before: before, after: after))
        }
    }

    func testCanonicalKeysAndExistingGroupsAreRequired() throws {
        let (before, after) = try sameImagePair()
        for key in ["offset:0x00", "offset:0X0", "symbol:0x0", "offset:0x", "offset:0x-1", "offset:0x10000000000000000", "offset:0x20"] {
            XCTAssertThrowsError(try validate([row(key, basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: after))
        }
        let old = try moved(before, offset: 0xa0), new = try moved(after, offset: 0xa0)
        XCTAssertNoThrow(try validate([row("offset:0xa0", basis: "exact_image_offset", old: oldID, new: newID)], before: old, after: new))
        XCTAssertThrowsError(try validate([row("offset:0xA0", basis: "exact_image_offset", old: oldID, new: newID)], before: old, after: new))
    }

    func testValidSourceIDsCannotBeJoinedUnderAnotherOffsetKey() throws {
        let (before, after) = try sameImagePair()
        let extraNew = "airsf-" + String(repeating: "d", count: 64)
        let old = try additional(before, id: unknownID, offset: 0x20), new = try additional(after, id: extraNew, offset: 0x20)
        XCTAssertThrowsError(try validate([row("offset:0x20", basis: "exact_image_offset", old: oldID, new: newID)], before: old, after: new))
        XCTAssertNoThrow(try validate([row("offset:0x20", basis: "exact_image_offset", old: unknownID, new: extraNew)], before: old, after: new))
    }

    func testDuplicateBaselineGroupRetainsOnlyUniqueCurrentSelection() throws {
        let (before, after) = try sameImagePair()
        let duplicate = try additional(before, id: unknownID, offset: 0)
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: nil, new: newID)], before: duplicate, after: after))
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: duplicate, after: after))
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", label: "added", old: nil, new: newID)], before: duplicate, after: after))
    }

    func testDuplicateCurrentGroupAndBothDuplicateGroupsStayAmbiguous() throws {
        let (before, after) = try sameImagePair()
        let extraNew = "airsf-" + String(repeating: "d", count: 64)
        let old = try additional(before, id: unknownID, offset: 0), new = try additional(after, id: extraNew, offset: 0)
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: oldID, new: nil)], before: before, after: new))
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", label: "removed", old: oldID, new: nil)], before: before, after: new))
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: nil, new: nil)], before: old, after: new))
    }

    func testUniqueGroupsCannotHideSelectedEndpointsAsAmbiguity() throws {
        let (before, after) = try sameImagePair()
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: nil, new: nil)], before: before, after: after))
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: oldID, new: nil)], before: before, after: after))
    }

    func testUniqueOneSidedGroupsRequireAddedOrRemoved() throws {
        let (before, after) = try sameImagePair()
        let shiftedBefore = try moved(before, offset: 0x20)
        let added = row("offset:0x0", basis: "exact_image_offset", label: "added", old: nil, new: newID)
        XCTAssertNoThrow(try validate([added], before: shiftedBefore, after: after))
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: nil, new: newID)], before: shiftedBefore, after: after))
        let shiftedAfter = try moved(after, offset: 0x20)
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", label: "removed", old: oldID, new: nil)], before: before, after: shiftedAfter))
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: oldID, new: nil)], before: before, after: shiftedAfter))
    }

    func testUniquePairsRetainObservationAndCompatibilityGuards() throws {
        let (before, after) = try sameImagePair()
        let configured = try changed(after, top: ["analysis_config": ["limits": ["work": 1]]])
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: oldID, new: newID)], before: before, after: configured))
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: configured))
        let observed = try changed(after, fields: ["reason_codes": ["different"]])
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", label: "changed", old: oldID, new: newID)], before: before, after: observed))
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: before, after: observed))
    }

    func testSameDigestWithDifferentArchitectureCannotClaimOffsetAuthority() throws {
        let (before, after) = try sameImagePair()
        var image = try XCTUnwrap(object(after)["image"] as? [String: Any]); image["architecture"] = "arm64e"; image["cpu_subtype"] = 2
        var generator = try XCTUnwrap(object(after)["generator"] as? [String: Any]); generator["analysis_model_version"] = "future-model"
        let different = try changed(after, top: ["image": image, "generator": generator])
        XCTAssertThrowsError(try validate([row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: oldID, new: newID)], before: before, after: different))
    }

    func testOmittedGroupsAndOtherImageBasesRemainOutsideThisScope() throws {
        let (before, after) = try sameImagePair()
        let extraNew = "airsf-" + String(repeating: "d", count: 64)
        let old = try additional(before, id: unknownID, offset: 0x20), new = try additional(after, id: extraNew, offset: 0x20)
        XCTAssertNoThrow(try validate([row("offset:0x0", basis: "exact_image_offset", old: oldID, new: newID)], before: old, after: new))
        XCTAssertNoThrow(try validate([], before: old, after: new))
        let crossImage = try source("other", id: newID, digest: "2")
        XCTAssertNoThrow(try validate([row("symbol:candidate", old: oldID, new: newID)], before: before, after: crossImage))
    }
}
