import XCTest
import Foundation
import AIRSCore
import AIRSEntitlements

/// Owned tampering is ordinary CI. Real release evidence is strictly opt-in.
final class SecurityDeltaRealArchiveAcceptanceTests: XCTestCase {
    private func tampering(_ bytes: Data) throws -> [(String, Data)] {
        let original = try XCTUnwrap(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
        var results: [(String, Data)] = []
        func append(_ name: String, _ edit: (inout [String: Any]) throws -> Void) throws {
            var object = original; try edit(&object)
            results.append((name, try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])))
        }
        try append("schema_future") { $0["schemaVersion"] = 2 }
        try append("schema_boolean") { $0["schemaVersion"] = true }
        try append("model_future") { $0["modelVersion"] = "future" }
        try append("rules_future") { $0["rulesVersion"] = "future" }
        try append("kind_substitution") { $0["kind"] = "airs.component.review" }
        try append("source_substitution") { $0["reviewChunks"] = [Data("owned substituted source".utf8).base64EncodedString()] }
        try append("source_invalid_base64") { $0["reviewChunks"] = ["not-base64"] }
        try append("source_empty") { $0["reviewChunks"] = [] }
        try append("unknown_interpreted_field") { $0["validated"] = true }
        try append("output_limit_raise") { $0["options"] = ["maximumObservations": 8193, "maximumFindings": 2048] }
        func reportEdit(_ object: inout [String: Any], _ edit: (inout [String: Any]) -> Void) throws {
            let chunks = try XCTUnwrap(object["reportChunks"] as? [String])
            var joined = Data()
            for chunk in chunks { joined.append(try XCTUnwrap(Data(base64Encoded: chunk))) }
            var report = try XCTUnwrap(JSONSerialization.jsonObject(with: joined) as? [String: Any])
            edit(&report)
            object["reportChunks"] = [try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys, .withoutEscapingSlashes]).base64EncodedString()]
        }
        try append("report_inventory_side_swap") { object in
            try reportEdit(&object) { report in
                guard var identity = report["identity"] as? [String: Any] else { return }
                let previous = identity["previousInventoryID"]; identity["previousInventoryID"] = identity["currentInventoryID"]; identity["currentInventoryID"] = previous
                report["identity"] = identity
            }
        }
        for mutation in ["explanation", "observation_id", "evidence_side", "evidence_offset", "numeric_tag", "duplicate_observation"] {
            try append(mutation) { object in
                try reportEdit(&object) { report in
                    guard var observations = report["observations"] as? [[String: Any]], !observations.isEmpty else { return }
                    switch mutation {
                    case "observation_id": observations[0]["id"] = "forged"
                    case "duplicate_observation": observations.append(observations[0])
                    case "numeric_tag": observations[0]["currentValue"] = ["type": "unsigned", "value": "18446744073709551616"]
                    case "evidence_side", "evidence_offset":
                        if var evidence = observations[0]["evidence"] as? [[String: Any]], !evidence.isEmpty {
                            if mutation == "evidence_side" { evidence[0]["side"] = "wrong-side" }
                            else { evidence[0]["slice"] = ["offset": 999, "size": 1] }
                            observations[0]["evidence"] = evidence
                        }
                    default:
                        if var findings = report["findings"] as? [[String: Any]], !findings.isEmpty {
                            findings[0]["explanation"] = "Forged runtime authorization assertion"; report["findings"] = findings
                        } else { observations[0]["subject"] = "forged" }
                    }
                    report["observations"] = observations
                }
            }
        }
        return results
    }
    private func assertRefusals(_ bytes: Data) throws {
        let mutations = try tampering(bytes)
        XCTAssertEqual(mutations.count, 17)
        for (name, changed) in mutations {
            XCTAssertNotEqual(changed, bytes, name)
            XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(changed), name) { error in
                XCTAssertNotNil(error as? SecurityDeltaRefusal, "Classified refusal required: \(name)")
            }
        }
    }
    func testSeventeenOwnedArchiveMutationsRefuse() throws {
        func inventory(_ version: String) -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                components: [.init(relativePath: "Contents/MacOS/Owned", kind: "app", declaredVersion: version, architectures: ["arm64"])])
        }
        let review = try ComponentComparison.review(previous: inventory("1"), current: inventory("2"), architecture: .arm64, entitlementResults: [])
        try assertRefusals(ComponentSecurityDeltaArchive.create(sourceReviewArchive: ComponentReviewArchive.encode(review)).data())
    }
    func testOptInAuthenticArchiveTamperingRefuses() throws {
        guard let path = ProcessInfo.processInfo.environment["AIRS_REAL_CORPUS_TAMPER"] else {
            throw XCTSkip("Authentic retained archive absent; ordinary CI uses owned evidence.")
        }
        try assertRefusals(Data(contentsOf: URL(fileURLWithPath: path)))
    }
}
