import Foundation
import XCTest
@testable import AIRSCore

final class BodyFingerprintCodecTests: XCTestCase {
    private func object() -> [String: Any] {
        ["schema_version": 1, "report_kind": "airs.audit",
         "generator": ["name": "AIRS", "version": "0.3.3", "analysis_model_version": "arm64-bounded-test-bit-branch-v50"],
         "image": ["display_name": "synthetic-native-fingerprint", "architecture": "arm64", "file_type": "dylib",
                   "container_sha256": String(repeating: "1", count: 64), "slice_sha256": String(repeating: "2", count: 64),
                   "cpu_subtype": 0, "slice_offset": 0, "slice_size": 16, "preferred_base": "0x1000"],
         "summary": ["function_count": 1, "agreement_count": 1, "inconsistency_count": 0, "unresolved_count": 0,
                     "metadata_entry_count": 1, "checked_pc_count": 1],
         "issues": [], "limitations": ["Synthetic admission only; digest is not authenticated"],
         "metadata_ranges": [["start": "0x1000", "end": "0x1010", "encoding": "0x04000000", "mode": "frame"]],
         "findings": [["id": "airsf-" + String(repeating: "a", count: 64),
                       "function": ["name": "sub_1000", "address": "0x1000", "end_address": "0x1010", "image_offset": "0x0",
                                    "size": 16, "boundary_source": "lc_function_starts", "body_fingerprint": fingerprint()],
                       "verdict": "agreement", "coverage": "compact", "mode": "frame", "scope": "synchronous_call_sites",
                       "encoding": "0x04000000", "checked_pcs": ["0x1008"], "instruction_count": 4,
                       "reason_codes": ["supported_model_agreement"], "evidence": [], "limitations": []]]]
    }

    private func fingerprint() -> [String: Any] {
        ["kind": "arm64-exact-bytes-v1", "sha256": String(repeating: "e", count: 64), "instruction_count": 4]
    }

    private func decode(_ object: [String: Any]) throws -> AuditReport {
        try AuditReport.decode(JSONSerialization.data(withJSONObject: object))
    }

    private func replacingFingerprint(_ fingerprint: Any) throws -> [String: Any] {
        var value = object()
        var findings = try XCTUnwrap(value["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        function["body_fingerprint"] = fingerprint
        findings[0]["function"] = function; value["findings"] = findings
        return value
    }

    func testUnknownFingerprintKindIsRejected() throws {
        var changed = fingerprint(); changed["kind"] = "unqualified-future-kind"
        XCTAssertThrowsError(try decode(replacingFingerprint(changed)))
    }

    func testTypedRoundTripPreservesFingerprintAndFindingScope() throws {
        let first = try decode(object())
        let data = try JSONEncoder().encode(first)
        let wire = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
        let findings = try XCTUnwrap(wire["findings"] as? [[String: Any]])
        let function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        let body = try XCTUnwrap(function["body_fingerprint"] as? [String: Any])
        XCTAssertEqual(body["kind"] as? String, "arm64-exact-bytes-v1")
        XCTAssertEqual(body["sha256"] as? String, String(repeating: "e", count: 64))
        XCTAssertEqual(body["instruction_count"] as? Int, 4)
        let second = try AuditReport.decode(data)
        XCTAssertEqual(second.findings.first?.checkedPCs, ["0x1008"])
        XCTAssertEqual(second.findings.first?.scope, "synchronous_call_sites")
        XCTAssertEqual(second.summary.agreementCount, 1)
    }

    func testAbsentFingerprintRemainsAbsentAfterEncoding() throws {
        var wire = object()
        var findings = try XCTUnwrap(wire["findings"] as? [[String: Any]])
        var function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        function.removeValue(forKey: "body_fingerprint")
        findings[0]["function"] = function; wire["findings"] = findings
        let report = try decode(wire)
        let encoded = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(report)) as? [String: Any])
        let encodedFindings = try XCTUnwrap(encoded["findings"] as? [[String: Any]])
        let encodedFunction = try XCTUnwrap(encodedFindings[0]["function"] as? [String: Any])
        XCTAssertNil(encodedFunction["body_fingerprint"])
    }

    func testNullMissingExtraAndWrongFieldTypesReject() throws {
        let malformedValues: [Any] = [NSNull(), [Any](), "body", [String: Any]()]
        for malformed in malformedValues {
            XCTAssertThrowsError(try decode(replacingFingerprint(malformed)))
        }
        for field in ["kind", "sha256", "instruction_count"] {
            var missing = fingerprint(); missing.removeValue(forKey: field)
            XCTAssertThrowsError(try decode(replacingFingerprint(missing)))
        }
        var extra = fingerprint(); extra["unbound"] = "data"
        XCTAssertThrowsError(try decode(replacingFingerprint(extra)))
        let invalidCounts: [Any] = [true, "4", 4.5]
        for value in invalidCounts {
            var wrong = fingerprint(); wrong["instruction_count"] = value
            XCTAssertThrowsError(try decode(replacingFingerprint(wrong)))
        }
    }

    func testDigestAndCountBoundsReject() throws {
        for digest in [String(repeating: "E", count: 64), String(repeating: "e", count: 63),
                       String(repeating: "g", count: 64)] {
            var wrong = fingerprint(); wrong["sha256"] = digest
            XCTAssertThrowsError(try decode(replacingFingerprint(wrong)))
        }
        for count in [-1, 0, 2, 16_385] {
            var wrong = fingerprint(); wrong["instruction_count"] = count
            XCTAssertThrowsError(try decode(replacingFingerprint(wrong)))
        }
    }

    func testFingerprintContextIsEnforcedEvenForFutureModels() throws {
        for fault in ["architecture", "subtype", "boundary", "size", "count", "unaligned", "unresolved"] {
            var wire = object()
            wire["generator"] = ["name": "AIRS", "version": "0.3.3", "analysis_model_version": "future-model"]
            var image = try XCTUnwrap(wire["image"] as? [String: Any])
            var findings = try XCTUnwrap(wire["findings"] as? [[String: Any]])
            var function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
            switch fault {
            case "architecture": image["architecture"] = "arm64e"
            case "subtype": image["cpu_subtype"] = 2
            case "boundary": function["boundary_source"] = "compact_unwind"
            case "size": function["size"] = 20; function["end_address"] = "0x1014"
            case "count": findings[0]["instruction_count"] = 5
            case "unaligned":
                function["address"] = "0x1001"; function["end_address"] = "0x1011"; function["image_offset"] = "0x1"
            default:
                findings[0]["verdict"] = "unresolved"; findings[0]["scope"] = "metadata_only"; findings[0]["checked_pcs"] = []
                wire["summary"] = ["function_count": 1, "agreement_count": 0, "inconsistency_count": 0, "unresolved_count": 1,
                                   "metadata_entry_count": 1, "checked_pc_count": 0]
            }
            findings[0]["function"] = function; wire["findings"] = findings; wire["image"] = image
            XCTAssertThrowsError(try decode(wire), fault)
        }
    }

    func testIntegralJSONNumberNormalizesToIntegerOnNativeRoundTrip() throws {
        let data = try JSONSerialization.data(withJSONObject: object(), options: [.sortedKeys])
        let text = try XCTUnwrap(String(data: data, encoding: .utf8))
        let modified = text.replacingOccurrences(of: "\"instruction_count\":4", with: "\"instruction_count\":4.0")
        XCTAssertNotEqual(modified, text)
        let decoded = try AuditReport.decode(Data(modified.utf8))
        let encoded = try XCTUnwrap(JSONSerialization.jsonObject(with: JSONEncoder().encode(decoded)) as? [String: Any])
        let findings = try XCTUnwrap(encoded["findings"] as? [[String: Any]])
        let function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
        let body = try XCTUnwrap(function["body_fingerprint"] as? [String: Any])
        XCTAssertEqual(body["instruction_count"] as? Int, 4)
    }


    func testTypedPropertiesExposeImportedEvidence() throws {
        let value = try decode(object())
        let body = try XCTUnwrap(value.findings.first?.function.bodyFingerprint)
        XCTAssertEqual(body.kind, "arm64-exact-bytes-v1")
        XCTAssertEqual(body.sha256, String(repeating: "e", count: 64))
        XCTAssertEqual(body.instructionCount, 4)
    }

    func testMinimumAndMaximumCountsRetainTheirExactExtents() throws {
        for count in [3, 16_384] {
            var body = fingerprint(); body["instruction_count"] = count
            var wire = try replacingFingerprint(body)
            var findings = try XCTUnwrap(wire["findings"] as? [[String: Any]])
            var function = try XCTUnwrap(findings[0]["function"] as? [String: Any])
            let end = "0x" + String(0x1000 + count * 4, radix: 16)
            function["size"] = count * 4; function["end_address"] = end
            findings[0]["function"] = function; findings[0]["instruction_count"] = count; wire["findings"] = findings
            var image = try XCTUnwrap(wire["image"] as? [String: Any]); image["slice_size"] = count * 4; wire["image"] = image
            wire["metadata_ranges"] = [["start": "0x1000", "end": end, "encoding": "0x04000000", "mode": "frame"]]
            let decoded = try decode(wire)
            XCTAssertEqual(decoded.findings.first?.function.bodyFingerprint?.instructionCount, count)
        }
    }

}
