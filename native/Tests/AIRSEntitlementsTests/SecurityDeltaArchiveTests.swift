import XCTest
import Foundation
import CryptoKit
import AIRSCore
import EntitlementDiffCore
@testable import AIRSEntitlements

final class SecurityDeltaArchiveTests: XCTestCase {
    private func source() throws -> Data {
        func inventory(_ name: String) -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/Helpers"], completion: .completeWithinScope, exclusions: [], issues: []),
                  components: [.init(relativePath: "Contents/Helpers/" + name, kind: "helper", architectures: ["arm64"])])
        }
        let review = try ComponentComparison.review(previous: inventory("Old"), current: inventory("New"), architecture: .arm64, entitlementResults: [])
        let original = try InspectionArchive.decode(ComponentReviewArchive.encode(review))
        let payload = Data("unknown historical evidence".utf8)
        let digest = SHA256.hash(data: payload).map { String(format: "%02x", $0) }.joined()
        let extra = EvidenceAttachment(id: UUID(), kind: "owned.unknown", schemaVersion: 7, mediaType: "application/octet-stream",
                                       sha256: digest, byteCount: payload.count, bytes: payload)
        return try InspectionArchive(attachments: original.attachments + [extra], components: original.components).encode()
    }
    private func modified(_ bytes: Data, _ change: (inout [String: Any]) -> Void) throws -> Data {
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
        change(&object)
        return try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])
    }
    func testRoundTripDeterminismAndPreservationOfSourceBytes() throws {
        let original = try source()
        let admitted = try ComponentReviewArchive.admit(original)
        let document = try ComponentSecurityDeltaArchive.create(admittedReview: admitted)
        let bytes = try document.data()
        XCTAssertEqual(bytes, try document.data())
        let restored = try ComponentSecurityDeltaArchive.decode(bytes)
        XCTAssertEqual(restored.sourceReviewArchive, original)
        XCTAssertEqual(restored.report.identity.evidenceBasisID, document.report.identity.evidenceBasisID)
        XCTAssertEqual(try restored.data(), bytes)
        XCTAssertTrue(try InspectionArchive.decode(restored.sourceReviewArchive).attachments.contains { $0.kind == "owned.unknown" && $0.schemaVersion == 7 })
    }
    func testAlreadyAdmittedLegacyArchiveCanBeReusedWithoutReopeningSource() throws {
        let original = try source()
        let decoded = try InspectionArchive.decode(original)
        let token = try ComponentReviewArchive.admit(decoded)
        XCTAssertEqual(token.sourceArchive, original)
        let delta = try ComponentSecurityDeltaArchive.create(admittedReview: token)
        XCTAssertEqual(delta.sourceReviewArchive, original)
        let assembled = InspectionArchive(attachments: decoded.attachments, components: decoded.components)
        XCTAssertThrowsError(try ComponentReviewArchive.admit(assembled))
    }
    func testTamperedReportAndUnknownFieldsRefuse() throws {
        let bytes = try ComponentSecurityDeltaArchive.create(sourceReviewArchive: source()).data()
        let altered = try modified(bytes) { object in
            guard var chunks = object["reportChunks"] as? [String], let first = chunks.first,
                  var data = Data(base64Encoded: first), !data.isEmpty else { return }
            data[0] ^= 1; chunks[0] = data.base64EncodedString(); object["reportChunks"] = chunks
        }
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(altered))
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(modified(bytes) { $0["unrecognized"] = true }))
        let wrongVersion = try modified(bytes) { $0["schemaVersion"] = 2 }
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(wrongVersion)) { XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .unsupportedSchemaVersion) }
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(modified(bytes) { $0["schemaVersion"] = true }))
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(modified(bytes) { $0["rulesVersion"] = "future" })) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .unsupportedModelVersion)
        }
    }
    func testFreshCaptureTokenRoundTripsLegacyNumericRepresentation() throws {
        func inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                  components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])])
        }
        let a = inventory(), b = inventory(), match = try XCTUnwrap(ComponentMatcher.match(previous: a, current: b).matches.first)
        func snapshot(_ id: UUID, value: EntitlementValue) -> EntitlementSnapshot {
            .init(sourceName: ComponentComparison.sourceName(componentID: id), signingIdentifier: "owned", architecture: .arm64,
                  entitlements: .init(["key": value]))
        }
        let comparison = try ComparisonReport(previous: snapshot(a.components[0].id, value: .integer(1)),
                                              current: snapshot(b.components[0].id, value: .unsignedInteger(1)))
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64,
            entitlementResults: [.compared(matchID: match.id, architecture: .arm64, report: comparison)])
        let token = try ComponentReviewArchive.capture(review)
        let document = try ComponentSecurityDeltaArchive.create(admittedReview: token)
        let bytes = try document.data()
        let restored = try ComponentSecurityDeltaArchive.decode(bytes)
        XCTAssertEqual(restored.report.identity.evidenceBasisID, document.report.identity.evidenceBasisID)
        XCTAssertNotNil(token.entitlementSource(matchID: match.id))
        XCTAssertEqual(restored.admittedReview.entitlementSource(matchID: match.id), token.entitlementSource(matchID: match.id))
        XCTAssertEqual(restored.report.observations.first { $0.category == .entitlements && $0.subject == "key:key" }?.disposition, .unresolved)
    }
    func testMalformedChunksAndDuplicateKeysRefuse() throws {
        let bytes = try ComponentSecurityDeltaArchive.create(sourceReviewArchive: source()).data()
        let malformed = try modified(bytes) { $0["reviewChunks"] = ["not-base64"] }
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(malformed)) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .invalidReview)
        }
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(modified(bytes) { $0["reviewChunks"] = [] }))
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(modified(bytes) { $0["reviewChunks"] = ["", "AA=="] }))
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(modified(bytes) { $0["reviewChunks"] = ["AA==", "AA=="] }))
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(modified(bytes) { $0["reviewChunks"] = ["AB=="] }))
        let duplicate = Data(#"{"kind":"airs.component.security-delta","kind":"airs.component.security-delta","schemaVersion":1,"modelVersion":"component-security-delta-v1","rulesVersion":"component-security-delta-rules-v1","reviewChunks":["AA=="],"reportChunks":["AA=="]}"#.utf8)
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(duplicate))
    }
    func testCancelledAdmissionDoesNotPublishDocument() async {
        let task = Task { () throws -> ComponentSecurityDeltaArchive in
            try Task.checkCancellation()
            return try ComponentSecurityDeltaArchive.create(sourceReviewArchive: source())
        }
        task.cancel()
        do { _ = try await task.value; XCTFail("Cancelled work must not publish a document") }
        catch { XCTAssertTrue(error is CancellationError) }
    }

    func testOversizedIncomingDocumentHasImportLimitCode() {
        let bytes = Data(repeating: 0, count: ComponentSecurityDeltaArchive.maximumBytes + 1)
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(bytes)) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .documentSizeLimit)
        }
    }
    func testValidJSONReportReferenceAndIdentitySubstitutionsRefuse() throws {
        for mutation in 0..<11 {
            // A fresh synthetic source is used for each distinct admission case.
            let data = try ComponentSecurityDeltaArchive.create(sourceReviewArchive: source()).data()
            var envelope = try XCTUnwrap(JSONSerialization.jsonObject(with: data) as? [String: Any])
            let chunks = try XCTUnwrap(envelope["reportChunks"] as? [String])
            XCTAssertEqual(chunks.count, 1)
            let reportData = try XCTUnwrap(Data(base64Encoded: XCTUnwrap(chunks.first)))
            var report = try XCTUnwrap(JSONSerialization.jsonObject(with: reportData) as? [String: Any])
            var observations = try XCTUnwrap(report["observations"] as? [[String: Any]])
            var first = try XCTUnwrap(observations.first), evidence = try XCTUnwrap(first["evidence"] as? [[String: Any]])
            var reference = try XCTUnwrap(evidence.first)
            switch mutation {
            case 0: reference["side"] = reference["side"] as? String == "previous" ? "current" : "previous"
            case 1: reference["inventoryID"] = UUID().uuidString
            case 2: reference["componentID"] = UUID().uuidString
            case 3: reference["category"] = "entitlements"
            case 4: reference["evidenceKey"] = "forged:key"
            case 5: reference["slice"] = ["cpuType": 1, "cpuSubtype": 2, "headerMagic": 3, "index": 0, "offset": 0, "size": 1]
            case 6: first["id"] = "forged-observation"
            case 7:
                first["id"] = try XCTUnwrap(observations.dropFirst().first?["id"])
            case 8:
                var findings = try XCTUnwrap(report["findings"] as? [[String: Any]])
                findings[0]["observationIDs"] = ["dangling-observation"]
                report["findings"] = findings
            case 9:
                var findings = try XCTUnwrap(report["findings"] as? [[String: Any]])
                findings[0]["id"] = try XCTUnwrap(findings.dropFirst().first?["id"])
                report["findings"] = findings
            default: reference["relativeSource"] = "Contents/Helpers/forged"
            }
            evidence[0] = reference; first["evidence"] = evidence; observations[0] = first; report["observations"] = observations
            let mutated = try JSONSerialization.data(withJSONObject: report, options: [.sortedKeys, .withoutEscapingSlashes])
            envelope["reportChunks"] = [mutated.base64EncodedString()]
            let forged = try JSONSerialization.data(withJSONObject: envelope, options: [.sortedKeys, .withoutEscapingSlashes])
            XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(forged), "mutation \(mutation)") {
                XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .invalidReview)
            }
        }
    }
    func testExportPreflightBudgetBoundaryAndExpansion() {
        let sourceAtLimit = ((ComponentSecurityDeltaArchive.maximumBytes - 65_536) / 4) * 3
        XCTAssertNoThrow(try ComponentSecurityDeltaArchive.exportBudget(sourceCount: sourceAtLimit, reportCount: 0))
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.exportBudget(sourceCount: sourceAtLimit + 1, reportCount: 0)) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .exportSizeLimit)
        }
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.exportBudget(sourceCount: sourceAtLimit, reportCount: 1)) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .exportSizeLimit)
        }
    }
}
