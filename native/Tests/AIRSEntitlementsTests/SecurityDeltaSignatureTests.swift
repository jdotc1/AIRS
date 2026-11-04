import XCTest
import Foundation
import CryptoKit
import AIRSCore
import EntitlementDiffCore
@testable import AIRSEntitlements

final class SecurityDeltaSignatureTests: XCTestCase {
    func testUnavailableSignatureIsRetainedWithoutBecomingAbsence() throws {
        let a = inventory(), b = inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let failure = try SecurityDeltaSignatureRefusal.record(side: .previous, inventoryID: a.id, componentID: a.components[0].id,
            relativePath: a.components[0].relativePath, architecture: .arm64, code: "source_stale", capturedAt: Date(timeIntervalSince1970: 0))
        let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureRefusals: [failure]))
        let observation = try XCTUnwrap(report.observations.first { $0.category == .signatureEvidence && $0.subject == "presence" })
        XCTAssertEqual(observation.disposition, .unresolved)
        XCTAssertEqual(observation.previousState, .unavailable)
        XCTAssertEqual(observation.currentState, .unexamined)
        XCTAssertTrue(observation.evidence.contains { $0.side == .previous && $0.evidenceKey == "signature:refusal" })
        let token = try ComponentReviewArchive.capture(review)
        let archive = try ComponentSecurityDeltaArchive.create(admittedReview: token, signatureRefusals: [failure])
        let restored = try ComponentSecurityDeltaArchive.decode(archive.data())
        XCTAssertEqual(restored.signatureRefusals.first?.sourceBytes, failure.sourceBytes)
    }
    func testSupplementalSignatureArchiveRoundTripAndBindingRefusal() throws {
        let a = inventory(), b = inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let oldBytes = try document(componentID: a.components[0].id, container: String(repeating: "a", count: 64), slice: String(repeating: "a", count: 64))
        let newBytes = try document(componentID: b.components[0].id, container: String(repeating: "b", count: 64), slice: String(repeating: "b", count: 64))
        let old = try SecurityDeltaSignatureEvidence.admit(oldBytes, side: .previous, inventoryID: a.id)
        let new = try SecurityDeltaSignatureEvidence.admit(newBytes, side: .current, inventoryID: b.id)
        let admitted = try ComponentReviewArchive.capture(review)
        let archive = try ComponentSecurityDeltaArchive.create(admittedReview: admitted, signatureEvidence: [new, old])
        let bytes = try archive.data()
        let restored = try ComponentSecurityDeltaArchive.decode(bytes)
        XCTAssertEqual(restored.signatureEvidence.map(\.sourceBytes), [oldBytes, newBytes])
        XCTAssertEqual(try restored.data(), bytes)
        XCTAssertTrue(restored.report.observations.contains { $0.subject == "sliceSHA256" && $0.disposition == .observedChange })
        let wrong = try SecurityDeltaSignatureEvidence.admit(oldBytes, side: .previous, inventoryID: b.id)
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.create(admittedReview: admitted, signatureEvidence: [wrong]))
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: bytes) as? [String: Any])
        var supplements = try XCTUnwrap(object["signatureEvidence"] as? [[String: Any]])
        supplements[0]["inventoryID"] = b.id.uuidString
        object["signatureEvidence"] = supplements
        let tampered = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys, .withoutEscapingSlashes])
        XCTAssertThrowsError(try ComponentSecurityDeltaArchive.decode(tampered))
    }
    private func inventory() -> ComponentInventory {
        .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
              components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["arm64"])])
    }
    private func document(componentID: UUID, container: String, slice: String, subtype: UInt32 = 0,
                          cpu: UInt32 = 0x0100000c, state: String = "signatureAbsent", problem: String? = nil) throws -> Data {
        let limits: [String: Any] = ["maximumContainerBytes": 536_870_912, "maximumHeaderBytes": 1_048_576,
            "maximumSignatureBytes": 524_288, "maximumTotalSignatureBytes": 4_194_304, "maximumSlotCount": 4096]
        var unit: [String: Any] = ["index": 0, "cpuType": cpu, "cpuSubtype": subtype,
            "headerMagic": UInt32(0xcffaedfe), "sliceOffset": 0, "sliceSize": 64, "sliceSHA256": slice,
            "loadCommandsEnd": 32, "state": state, "slots": []]
        if let problem { unit["problem"] = problem }
        let evidence: [String: Any] = ["componentID": componentID.uuidString, "componentRelativePath": "Contents/MacOS/Main",
            "containerSHA256": container, "containerByteCount": 64, "bytesHashed": 64, "headerBytesRead": 32,
            "signatureBytesRead": 0, "limits": limits, "slices": [unit]]
        return try JSONSerialization.data(withJSONObject: ["kind": "airs.signature-evidence", "schemaVersion": 1,
            "capturedAt": "2026-01-01T00:00:00Z", "producerVersion": "synthetic", "evidence": evidence], options: [.sortedKeys])
    }
    private func collectedDocument(componentID: UUID, digest: String, payload: UInt8) throws -> Data {
        func word(_ value: UInt32) -> Data { Data((0..<4).map { UInt8(truncatingIfNeeded: value >> ((3 - $0) * 8)) }) }
        func sha(_ bytes: Data) -> String { SHA256.hash(data: bytes).map { String(format: "%02x", $0) }.joined() }
        let blob = word(0xfade7171) + word(9) + Data([payload])
        let signature = word(0xfade0cc0) + word(29) + word(1) + word(5) + word(20) + blob
        let limits: [String: Any] = ["maximumContainerBytes": 536_870_912, "maximumHeaderBytes": 1_048_576,
            "maximumSignatureBytes": 524_288, "maximumTotalSignatureBytes": 4_194_304, "maximumSlotCount": 4096]
        let slot: [String: Any] = ["type": 5, "magic": UInt32(0xfade7171), "containerOffset": 52, "sliceRelativeOffset": 52,
            "byteCount": 9, "sha256": sha(blob), "bytes": blob.base64EncodedString()]
        let slice: [String: Any] = ["index": 0, "cpuType": 0x0100000c, "cpuSubtype": 0, "headerMagic": UInt32(0xcffaedfe),
            "sliceOffset": 0, "sliceSize": 61, "sliceSHA256": digest, "loadCommandsEnd": 32, "state": "collected",
            "signatureOffset": 32, "signatureByteCount": 29, "signatureSHA256": sha(signature),
            "signatureBytes": signature.base64EncodedString(), "slots": [slot]]
        let evidence: [String: Any] = ["componentID": componentID.uuidString, "componentRelativePath": "Contents/MacOS/Main",
            "containerSHA256": digest, "containerByteCount": 61, "bytesHashed": 61, "headerBytesRead": 32,
            "signatureBytesRead": 29, "limits": limits, "slices": [slice]]
        return try JSONSerialization.data(withJSONObject: ["kind": "airs.signature-evidence", "schemaVersion": 1,
            "capturedAt": "2026-01-01T00:00:00Z", "producerVersion": "synthetic", "evidence": evidence], options: [.sortedKeys])
    }
    func testRecordedDigestsCompareWithExactSliceEvidence() throws {
        let a = inventory(), b = inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let old = try SecurityDeltaSignatureEvidence.admit(document(componentID: a.components[0].id,
            container: String(repeating: "a", count: 64), slice: String(repeating: "a", count: 64)), side: .previous, inventoryID: a.id)
        let new = try SecurityDeltaSignatureEvidence.admit(document(componentID: b.components[0].id,
            container: String(repeating: "c", count: 64), slice: String(repeating: "c", count: 64)), side: .current, inventoryID: b.id)
        let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, new]))
        let change = try XCTUnwrap(report.observations.first { $0.category == .signatureEvidence && $0.subject == "sliceSHA256" })
        XCTAssertEqual(change.disposition, .observedChange)
        XCTAssertEqual(change.evidence.map { $0.slice?.cpuSubtype }, [0, 0])
        XCTAssertTrue(report.findings.contains { $0.observationIDs.contains(change.id) && $0.explanation.contains("not retained or authenticated") })
        let absent = try XCTUnwrap(report.observations.first { $0.subject == "signatureSHA256" && $0.category == .signatureEvidence })
        XCTAssertEqual(absent.disposition, .unchanged)
        XCTAssertEqual(absent.previousState, .absent)
    }
    func testMissingOrMismatchedBindingsRemainUnresolvedOrRefuse() throws {
        let a = inventory(), b = inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let bytes = try document(componentID: a.components[0].id, container: String(repeating: "a", count: 64), slice: String(repeating: "a", count: 64))
        let old = try SecurityDeltaSignatureEvidence.admit(bytes, side: .previous, inventoryID: a.id)
        let missing = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old]))
        XCTAssertEqual(missing.observations.first { $0.category == .signatureEvidence && $0.subject == "presence" }?.disposition, .unresolved)
        let wrong = try SecurityDeltaSignatureEvidence.admit(bytes, side: .previous, inventoryID: b.id)
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [wrong]))) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .evidenceBindingMismatch)
        }
        XCTAssertThrowsError(try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, old]))) {
            XCTAssertEqual(($0 as? SecurityDeltaRefusal)?.code, .duplicateObservationIdentity)
        }
    }
    func testCapabilityBitsCannotBeMatchedByArchitectureLabel() throws {
        let a = inventory(), b = inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let old = try SecurityDeltaSignatureEvidence.admit(document(componentID: a.components[0].id,
            container: String(repeating: "a", count: 64), slice: String(repeating: "a", count: 64)), side: .previous, inventoryID: a.id)
        let new = try SecurityDeltaSignatureEvidence.admit(document(componentID: b.components[0].id,
            container: String(repeating: "c", count: 64), slice: String(repeating: "c", count: 64), subtype: 0x80000000), side: .current, inventoryID: b.id)
        let report = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, new]))
        XCTAssertEqual(report.observations.first { $0.category == .signatureEvidence && $0.subject == "slice" }?.disposition, .unresolved)
        XCTAssertFalse(report.observations.contains { $0.category == .signatureEvidence && $0.subject == "sliceSHA256" })
    }
    func testInventoryMustAdvertiseRequestedSliceBeforeComparison() throws {
        let a = inventory(), original = inventory()
        let currentRecord = ComponentRecord(id: original.components[0].id, relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["x86_64"])
        let b = ComponentInventory(id: original.id, capturedAt: original.capturedAt, scope: original.scope, components: [currentRecord])
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let old = try SecurityDeltaSignatureEvidence.admit(document(componentID: a.components[0].id,
            container: String(repeating: "a", count: 64), slice: String(repeating: "a", count: 64)), side: .previous, inventoryID: a.id)
        let new = try SecurityDeltaSignatureEvidence.admit(document(componentID: b.components[0].id,
            container: String(repeating: "c", count: 64), slice: String(repeating: "c", count: 64)), side: .current, inventoryID: b.id)
        let result = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, new]))
        let refusal = try XCTUnwrap(result.observations.first { $0.category == .signatureEvidence && $0.subject == "slice" })
        XCTAssertEqual(refusal.disposition, .unresolved)
        XCTAssertEqual(Set(refusal.evidence.filter { $0.category == .componentInventory && $0.evidenceKey == "architectures" }.map(\.side)), Set([.previous, .current]))
        XCTAssertFalse(result.observations.contains { $0.category == .signatureEvidence && $0.subject == "sliceSHA256" })
    }
    func testContradictoryWholeSliceDigestRemainsUnresolved() throws {
        let a = inventory(), b = inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let old = try SecurityDeltaSignatureEvidence.admit(document(componentID: a.components[0].id,
            container: String(repeating: "a", count: 64), slice: String(repeating: "b", count: 64)), side: .previous, inventoryID: a.id)
        let new = try SecurityDeltaSignatureEvidence.admit(document(componentID: b.components[0].id,
            container: String(repeating: "c", count: 64), slice: String(repeating: "c", count: 64)), side: .current, inventoryID: b.id)
        let result = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, new]))
        let conflict = try XCTUnwrap(result.observations.first { $0.subject == "container-slice-consistency" })
        XCTAssertEqual(conflict.disposition, .unresolved)
        XCTAssertTrue(conflict.limitations.contains { $0.code == "evidence_conflict" })
        XCTAssertFalse(result.observations.contains { $0.subject == "sliceSHA256" })
        let prioritized = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, new]),
            options: SecurityDeltaOptions(maximumObservations: 8192, maximumFindings: 1))
        XCTAssertEqual(prioritized.findings.first?.kind, .evidenceConflict)
    }
    func testRecordedEntitlementSlotBytesCanChangeWithoutTrustClaim() throws {
        let a = inventory(), b = inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let old = try SecurityDeltaSignatureEvidence.admit(collectedDocument(componentID: a.components[0].id,
            digest: String(repeating: "a", count: 64), payload: 1), side: .previous, inventoryID: a.id)
        let new = try SecurityDeltaSignatureEvidence.admit(collectedDocument(componentID: b.components[0].id,
            digest: String(repeating: "b", count: 64), payload: 2), side: .current, inventoryID: b.id)
        let result = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, new]))
        let change = try XCTUnwrap(result.observations.first { $0.category == .signatureEvidence && $0.subject == "xmlSlotSHA256" })
        XCTAssertEqual(change.disposition, .observedChange)
        XCTAssertTrue(change.evidence.allSatisfy { $0.evidenceKey == "signature:slot:5:sha256" && $0.slice != nil })
        XCTAssertTrue(result.findings.contains { $0.observationIDs.contains(change.id) && $0.explanation.contains("does not establish") })
    }
    func testEqualSliceDigestWithConflictingRetainedBytesIsUnresolved() throws {
        let a = inventory(), b = inventory(), digest = String(repeating: "a", count: 64)
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let old = try SecurityDeltaSignatureEvidence.admit(collectedDocument(componentID: a.components[0].id, digest: digest, payload: 1), side: .previous, inventoryID: a.id)
        let new = try SecurityDeltaSignatureEvidence.admit(collectedDocument(componentID: b.components[0].id, digest: digest, payload: 2), side: .current, inventoryID: b.id)
        let result = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, new]))
        let conflict = try XCTUnwrap(result.observations.first { $0.subject == "cross-document-consistency" })
        XCTAssertEqual(conflict.disposition, .unresolved)
        XCTAssertTrue(conflict.limitations.contains { $0.code == "evidence_conflict" })
        XCTAssertFalse(result.observations.contains { $0.subject == "signatureSHA256" && $0.disposition == .observedChange })
    }
    func testEqualSliceDigestWithConflictingSignaturePresenceIsUnresolved() throws {
        let a = inventory(), b = inventory(), digest = String(repeating: "a", count: 64)
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .arm64, entitlementResults: [])
        let captured = try collectedDocument(componentID: b.components[0].id, digest: digest, payload: 1)
        var object = try XCTUnwrap(JSONSerialization.jsonObject(with: captured) as? [String: Any])
        var evidence = try XCTUnwrap(object["evidence"] as? [String: Any])
        evidence["componentID"] = a.components[0].id.uuidString; evidence["signatureBytesRead"] = 0
        var slices = try XCTUnwrap(evidence["slices"] as? [[String: Any]])
        slices[0]["state"] = "signatureAbsent"; slices[0]["slots"] = []
        for key in ["signatureOffset", "signatureByteCount", "signatureSHA256", "signatureBytes"] { slices[0].removeValue(forKey: key) }
        evidence["slices"] = slices; object["evidence"] = evidence
        let absentBytes = try JSONSerialization.data(withJSONObject: object, options: [.sortedKeys])
        let old = try SecurityDeltaSignatureEvidence.admit(absentBytes, side: .previous, inventoryID: a.id)
        let new = try SecurityDeltaSignatureEvidence.admit(captured, side: .current, inventoryID: b.id)
        let result = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [old, new]))
        let conflict = try XCTUnwrap(result.observations.first { $0.subject == "cross-document-consistency" })
        XCTAssertEqual(conflict.disposition, .unresolved)
        XCTAssertTrue(conflict.limitations.contains { $0.code == "evidence_conflict" })
        XCTAssertFalse(result.observations.contains { $0.subject == "signatureSHA256" && $0.disposition == .observedAddition })
    }
    func testUnsupportedX86SignatureParsingRemainsUnexamined() throws {
        func x86Inventory() -> ComponentInventory {
            .init(scope: .init(searchedLocations: ["Contents/MacOS"], completion: .completeWithinScope, exclusions: [], issues: []),
                  components: [.init(relativePath: "Contents/MacOS/Main", kind: "app", architectures: ["x86_64"])])
        }
        let a = x86Inventory(), b = x86Inventory()
        let review = try ComponentComparison.review(previous: a, current: b, architecture: .x86_64, entitlementResults: [])
        func evidence(_ inventory: ComponentInventory, side: SecurityDeltaSide, digest: String) throws -> SecurityDeltaSignatureEvidence {
            try .admit(document(componentID: inventory.components[0].id, container: digest, slice: digest, subtype: 3,
                                cpu: 0x01000007, state: "unexamined", problem: "unsupportedArchitecture"),
                       side: side, inventoryID: inventory.id)
        }
        let result = try ComponentSecurityDeltaAnalyzer.analyze(input: .init(review: review, signatureEvidence: [
            evidence(a, side: .previous, digest: String(repeating: "a", count: 64)),
            evidence(b, side: .current, digest: String(repeating: "b", count: 64))]))
        let state = try XCTUnwrap(result.observations.first { $0.category == .signatureEvidence && $0.subject == "signatureState" })
        XCTAssertEqual(state.disposition, .unresolved)
        XCTAssertEqual(state.previousState, .unexamined)
        XCTAssertTrue(state.limitations.contains { $0.code == "signature_unexamined" })
        XCTAssertFalse(result.observations.contains { $0.subject == "signatureSHA256" })
    }
}
