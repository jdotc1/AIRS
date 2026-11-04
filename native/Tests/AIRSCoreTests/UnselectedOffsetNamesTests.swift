import Foundation
import XCTest
@testable import AIRSCore

final class UnselectedOffsetNamesTests: XCTestCase {
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
        try report.validateUnselectedOffsetNames(baselineData: before, currentData: after)
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

    private func labeled(_ name: String) -> [String: Any] {
        var value = row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: nil, new: nil)
        value["function_name"] = name; return value
    }
    func testUnselectedOffsetCannotBorrowUnrelatedLabel() throws {
        let (before, after) = try sameImagePair()
        let old = try additional(before, id: unknownID, offset: 0)
        let new = try additional(after, id: "airsf-" + String(repeating: "d", count: 64), offset: 0)
        XCTAssertThrowsError(try validate([labeled("unrelated")], before: old, after: new))
    }
    private let otherNewID = "airsf-" + String(repeating: "d", count: 64)
    private func rename(_ data: Data, index: Int, name: String?) throws -> Data {
        var value = try object(data), findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(findings[index]["function"] as? [String: Any])
        function["name"] = name.map { $0 as Any } ?? NSNull()
        findings[index]["function"] = function; value["findings"] = findings
        return try JSONSerialization.data(withJSONObject: value)
    }
    private func group(oldCount: Int, newCount: Int) throws -> (Data, Data) {
        let (before, after) = try sameImagePair()
        var old = before, new = after
        if oldCount == 0 { old = try moved(old, offset: 0x20) }
        if newCount == 0 { new = try moved(new, offset: 0x20) }
        if oldCount == 2 { old = try rename(additional(old, id: unknownID, offset: 0), index: 1, name: "baselineSecond") }
        if newCount == 2 { new = try rename(additional(new, id: otherNewID, offset: 0), index: 1, name: "currentSecond") }
        return (old, new)
    }
    private func reordered(_ data: Data) throws -> Data {
        var value = try object(data)
        value["findings"] = Array(try XCTUnwrap(value["findings"] as? [[String: Any]]).reversed())
        return try JSONSerialization.data(withJSONObject: value)
    }
    func testBaselineOnlyUsesFirstBaselineMember() throws {
        let (old, new) = try group(oldCount: 2, newCount: 0)
        try validate([labeled("before")], before: old, after: new)
        XCTAssertThrowsError(try validate([labeled("baselineSecond")], before: old, after: new))
    }
    func testCurrentOnlyUsesFirstCurrentMember() throws {
        let (old, new) = try group(oldCount: 0, newCount: 2)
        try validate([labeled("after")], before: old, after: new)
        XCTAssertThrowsError(try validate([labeled("currentSecond")], before: old, after: new))
    }
    func testBothGroupsPreferCurrentOverBaseline() throws {
        let (old, new) = try group(oldCount: 2, newCount: 2)
        try validate([labeled("after")], before: old, after: new)
        XCTAssertThrowsError(try validate([labeled("before")], before: old, after: new))
    }
    func testCurrentSourceOrderIsPreserved() throws {
        let (old, new) = try group(oldCount: 2, newCount: 2)
        let reversed = try reordered(new)
        try validate([labeled("currentSecond")], before: old, after: reversed)
        XCTAssertThrowsError(try validate([labeled("after")], before: old, after: reversed))
    }
    func testBaselineSourceOrderIsPreservedWhenCurrentGroupAbsent() throws {
        let (old, new) = try group(oldCount: 2, newCount: 0)
        let reversed = try reordered(old)
        try validate([labeled("baselineSecond")], before: reversed, after: new)
        XCTAssertThrowsError(try validate([labeled("before")], before: reversed, after: new))
    }
    func testRepresentativeNamesPreserveRawUnicode() throws {
        let (old, new) = try group(oldCount: 0, newCount: 2)
        let after = try rename(new, index: 0, name: "caf\u{e9}")
        try validate([labeled("caf\u{e9}")], before: old, after: after)
        XCTAssertThrowsError(try validate([labeled("cafe\u{301}")], before: old, after: after))
    }
    func testEmptyGeneratedAndCombiningNamesRemainPresentationFacts() throws {
        let (old, new) = try group(oldCount: 0, newCount: 2)
        for name in ["", "_entry", "sub_1000", "\u{301}work", " Work:variant "] {
            try validate([labeled(name)], before: old, after: rename(new, index: 0, name: name))
        }
    }
    func testMissingFirstNameDoesNotBorrowSecondName() throws {
        let (old, new) = try group(oldCount: 0, newCount: 2)
        XCTAssertThrowsError(try validate([labeled("currentSecond")], before: old, after: rename(new, index: 0, name: nil)))
    }
    func testNumericSourceOffsetSpellingDoesNotChangeRepresentative() throws {
        let (old, new) = try group(oldCount: 2, newCount: 2)
        let padded = try changed(new, function: ["image_offset": "0x0000"])
        try validate([labeled("after")], before: old, after: padded)
    }
    func testInheritedCanonicalKeyAndImageAuthorityRemainRequired() throws {
        let (old, new) = try group(oldCount: 2, newCount: 2)
        for key in ["offset:0x00", "offset:0X0", "offset:0x20", "offset:0x10000000000000000"] {
            var value = labeled("after"); value["key"] = key
            XCTAssertThrowsError(try validate([value], before: old, after: new))
        }
        let (before, after) = try pair()
        XCTAssertThrowsError(try validate([labeled("after")], before: additional(before, id: unknownID, offset: 0), after: additional(after, id: otherNewID, offset: 0)))
    }
    func testSelectedSingletonStillControlsAmbiguousLabel() throws {
        let (old, new) = try group(oldCount: 1, newCount: 2)
        var value = row("offset:0x0", basis: "exact_image_offset", label: "ambiguous", old: oldID, new: nil)
        value["function_name"] = "before"
        try validate([value], before: old, after: new)
        value["function_name"] = "after"
        XCTAssertThrowsError(try validate([value], before: old, after: new))
    }
    func testEarlierAPIKeepsUnselectedOffsetLabelScope() throws {
        let (old, new) = try group(oldCount: 2, newCount: 2)
        let report = try ComparisonReport.decode(JSONSerialization.data(withJSONObject: wire([labeled("unrelated")], before: old, after: new)))
        try report.validateUnselectedSymbolNames(baselineData: old, currentData: new)
        XCTAssertThrowsError(try report.validateUnselectedOffsetNames(baselineData: old, currentData: new))
        XCTAssertEqual(report.changes[0].functionName, "unrelated")
    }
    func testOmittedGroupsDoNotBecomeCompletenessClaim() throws {
        let (old, new) = try group(oldCount: 2, newCount: 2)
        try validate([], before: old, after: new)
    }
}
