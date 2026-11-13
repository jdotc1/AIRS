import Foundation
import CoreFoundation

public enum SwiftFlowProfile: String, CaseIterable, Identifiable, Sendable {
    case standard, broad, broadLarge, broadExtended, broadExtendedV2, broadExtendedV3, broadImports
    public var id: Self { self }
    public var title: String {
        switch self {
        case .standard: return "Standard Swift · v37/v38"
        case .broad: return "Broad Swift · broad-v1"
        case .broadLarge: return "Broad Swift · larger function inventory"
        case .broadExtended: return "Broad Swift · extended scan"
        case .broadExtendedV2: return "Broad Swift · extended + caller error tests (v2)"
        case .broadExtendedV3: return "Broad Swift · v2 + indirect targets and value witnesses (v3)"
        case .broadImports: return "Broad Swift · imported callees (attribution only)"
        }
    }
    public var broadModel: String? {
        switch self {
        case .standard: return nil
        case .broad: return "swift-broad-error-flow-v1"
        case .broadLarge: return "swift-broad-error-flow-large-v1"
        case .broadExtended: return "swift-broad-error-flow-extended-v1"
        case .broadExtendedV2: return "swift-broad-error-flow-extended-v2"
        case .broadExtendedV3: return "swift-broad-error-flow-extended-v3"
        case .broadImports: return "swift-broad-error-flow-imports-v1"
        }
    }
    public var broadArgument: String? {
        switch self {
        case .standard: return nil
        case .broad: return "broad-v1"
        case .broadLarge: return "broad-large-v1"
        case .broadExtended: return "broad-extended-v1"
        case .broadExtendedV2: return "broad-extended-v2"
        case .broadExtendedV3: return "broad-extended-v3"
        case .broadImports: return "broad-imports-v1"
        }
    }
}

public struct SwiftFlowOptions: Sendable, Equatable {
    public var includeMethods: Bool
    public var includeWitnesses: Bool
    public var profile: SwiftFlowProfile
    public init(includeMethods: Bool = false, includeWitnesses: Bool = false, profile: SwiftFlowProfile = .standard) {
        self.includeMethods = includeMethods; self.includeWitnesses = includeWitnesses; self.profile = profile
    }
    public func arguments(input: URL, output: URL) -> [String] {
        var result = ["swift-error-flow", "--format", "json", "--output", output.path,
                      "--include-error-regions", "--validate-region-entries", "--include-structured-presentation"]
        if let broadArgument = profile.broadArgument { result += ["--swift-profile", broadArgument, "--include-outcome-witnesses"] }
        else {
            if includeMethods { result.append("--include-swift-methods") }
            if includeWitnesses { result.append("--include-outcome-witnesses") }
        }
        return result + ["--", input.path]
    }
}

public enum SwiftFlowReportError: Error, LocalizedError {
    case invalid(String)
    public var errorDescription: String? {
        switch self { case .invalid(let reason): return "Swift error-flow report unavailable: \(reason)" }
    }
}

public struct SwiftFlowCall: Identifiable, Sendable {
    public let id: String
    public let callPC: String
    public let callerPC: String
    public let calleeSymbol: String
    public let status: String
    public let reason: String?
    public let testPC: String?
    public let successPC: String?
    public let errorPC: String?
    public let witnessStatus: String?
    public let witnessReason: String?
    public let witnessFacts: [String]
    public let witnessWorkSteps: Int?
    public let witnessCheckedInstructionCount: Int?
    public let witnessEdges: [String]
    public let detailJSON: String
}

/// Shape admission only. Loading a saved validation result never revalidates image bytes.
public struct SwiftFlowReport: Sendable {
    public static let maximumBytes = 64 * 1024 * 1024
    public let sourceData: Data
    public let imageDescription: String
    public let modelVersion: String
    public let supportsInterpretation: Bool
    public let wordScanComplete: Bool
    public let callDetailsComplete: Bool
    public let witnessesComplete: Bool
    public let calls: [SwiftFlowCall]
    public let limitations: [String]
    public let summaryText: String
    public let omittedCallCount: Int?

    public static func decode(_ data: Data) throws -> Self {
        func fail(_ text: String) -> SwiftFlowReportError { .invalid(text) }
        guard data.count <= maximumBytes else { throw fail("64 MiB input limit exceeded") }
        try SwiftBroadFlowReport.validateJSON(data)
        let raw = try JSONSerialization.jsonObject(with: data)
        if let object = raw as? [String: Any],
           AnalysisModels.swiftBroadNativePairs.contains(where: { pair in
               pair.model == object["model_version"] as? String
               || pair.profile == object["profile"] as? String
           }) {
            return try SwiftBroadFlowReport.decode(object, data: data, jsonPreflighted: true)
        }
        // Bound recursive display/storage before retaining any per-call representation.
        var nodes = 0
        func inspect(_ value: Any, _ depth: Int) throws {
            nodes += 1
            guard nodes <= 250_000, depth <= 32 else { throw fail("nested evidence limit exceeded") }
            if let string = value as? String {
                guard string.utf8.count <= 65_536 else { throw fail("evidence string limit exceeded") }
            } else if let object = value as? [String: Any] {
                for (key, child) in object { try inspect(key, depth + 1); try inspect(child, depth + 1) }
            } else if let values = value as? [Any] {
                for child in values { try inspect(child, depth + 1) }
            }
        }
        try inspect(raw, 0)
        func unsignedInteger(_ value: Any?) -> UInt64? {
            guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
                  !["f", "d"].contains(String(cString: number.objCType)), number.doubleValue >= 0 else { return nil }
            return number.uint64Value
        }
        guard let object = raw as? [String: Any],
              unsignedInteger(object["schema_version"]) == 1,
              object["report_kind"] as? String == "airs.swift_error_flow",
              let model = object["model_version"] as? String,
              let image = object["image"] as? [String: Any],
              let rows = object["calls"] as? [[String: Any]], rows.count <= 256,
              let limitations = object["limitations"] as? [String], limitations.count <= 64 else {
            throw fail("wrong format or call/detail limits")
        }
        func boolean(_ value: Any?) -> Bool? {
            guard let number = value as? NSNumber, CFGetTypeID(number) == CFBooleanGetTypeID() else { return nil }
            return number.boolValue
        }
        guard let wordComplete = boolean(object["word_scan_complete"]),
              let detailComplete = boolean(object["call_details_complete"]) else { throw fail("missing scan completeness") }
        func address(_ value: Any?) -> String? {
            guard let text = value as? String, text.hasPrefix("0x"), text.count <= 18,
                  let number = UInt64(text.dropFirst(2), radix: 16), text == "0x" + String(number, radix: 16), number % 4 == 0 else { return nil }
            return text
        }
        guard let architecture = image["architecture"] as? String,
              let digest = image["slice_sha256"] as? String, digest.count == 64,
              digest.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
              let base = address(image["preferred_base"]) else { throw fail("missing selected-image identity") }
        guard unsignedInteger(image["cpu_subtype"]) != nil,
              unsignedInteger(image["slice_offset"]) != nil,
              let size = unsignedInteger(image["slice_size"]), size > 0,
              let container = image["container_sha256"] as? String, container.count == 64,
              container.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else { throw fail("incomplete selected-slice identity") }
        let methodProfile = model == "swift-sync-error-edges-v38"
        var supported = (model == "swift-sync-error-edges-v37" || methodProfile) && architecture == "arm64" && [UInt64(0), UInt64(1)].contains(unsignedInteger(image["cpu_subtype"]) ?? UInt64.max)
        let models = ["error_region_model_version": "swift-sync-error-region-v24",
                      "region_incoming_model_version": "swift-region-direct-entries-v7",
                      "flag_entry_model_version": "swift-compare-flag-entries-v1",
                      "structured_presentation_model_version": "swift-structural-presentation-v10",
                      "success_result_model_version": "swift-success-result-v24",
                      "success_constant_model_version": "swift-success-constant-v17",
                      "error_constant_model_version": "swift-error-constant-v19",
                      "return_choice_model_version": methodProfile ? "swift-return-choice-v46" : "swift-return-choice-v45"]
        for (key, expected) in models where object[key] != nil { supported = supported && object[key] as? String == expected }
        if methodProfile { supported = supported && object["declaration_model_version"] as? String == "swift-throwing-declarations-v1" }
        if !methodProfile && object["declaration_model_version"] != nil { supported = false }
        let hasWitnesses = rows.contains { $0["outcome_witness"] != nil } || object["outcome_witness_model_version"] != nil
        if hasWitnesses {
            supported = supported && object["outcome_witness_model_version"] as? String == "swift-outcome-witness-v1"
                && object["outcome_validation_model_version"] as? String == "swift-outcome-validation-v1"
            for (key, expected) in models { supported = supported && object[key] as? String == expected }
        }
        let witnessComplete = hasWitnesses ? boolean(object["outcome_witnesses_complete"]) == true : true
        func hasStrongerProof(_ value: Any) -> Bool {
            if let dict = value as? [String: Any] {
                return dict.contains { key, child in
                    ((key.hasSuffix("_proven") || key == "source_reconstruction_allowed") && boolean(child) != false) || hasStrongerProof(child)
                }
            }
            if let rows = value as? [Any] { return rows.contains(where: hasStrongerProof) }
            return false
        }
        func displayCost(_ value: Any) -> Int {
            if let text = value as? String { return text.utf8.count * 6 + 8 }
            if let dict = value as? [String: Any] { return dict.reduce(2) { $0 + displayCost($1.key) + displayCost($1.value) } }
            if let rows = value as? [Any] { return rows.reduce(2) { $0 + displayCost($1) } }
            return 32
        }
        var seen = Set<String>(); var calls: [SwiftFlowCall] = []
        for row in rows {
            guard let pc = address(row["call_pc"]), let caller = address(row["caller_pc"]) else { throw fail("invalid call identity") }
            let identity = caller + ":" + pc
            guard seen.insert(identity).inserted else { throw fail("duplicate call identity") }
            guard displayCost(row) <= 256 * 1024 else { throw fail("call evidence display allocation limit") }
            let detail = try JSONSerialization.data(withJSONObject: row, options: [.prettyPrinted, .sortedKeys])
            guard detail.count <= 256 * 1024 else { throw fail("call evidence exceeds 256 KiB display limit") }
            let callee = row["callee"] as? [String: Any]
            let witness = row["outcome_witness"] as? [String: Any]
            if let witness {
                guard try JSONSerialization.data(withJSONObject: witness).count <= 65_536 else { throw fail("witness exceeds 64 KiB") }
            }
            let validation = witness?["validation"] as? [String: Any]
            let recordedWitnessStatus = witness?["status"] as? String
            let requiredProofs = ["source_reconstruction_allowed", "call_return_proven", "runtime_branch_proven", "handler_semantics_proven"]
            let proofScopeComplete = requiredProofs.allSatisfy { boolean(witness?[$0]) == false && boolean(validation?[$0]) == false }
            let witnessConsistent = proofScopeComplete && witness?["model_version"] as? String == "swift-outcome-witness-v1"
                && witness?["validation_model_version"] as? String == "swift-outcome-validation-v1"
                && validation?["model_version"] as? String == "swift-outcome-validation-v1"
                && validation?["status"] as? String == recordedWitnessStatus
                && !hasStrongerProof(witness ?? [:]) && wordComplete && detailComplete && witnessComplete
            let facts = validation?["facts"] as? [String: String] ?? [:]
            let graph = witness?["graph"] as? [String: Any]
            let edges = graph?["edges"] as? [[String: Any]] ?? []
            guard facts.count <= 32, edges.count <= 24 else { throw fail("witness projection limit exceeded") }
            func count(_ value: Any?) -> Int? {
                guard let number = unsignedInteger(value), number <= UInt64(Int.max) else { return nil }
                return Int(number)
            }
            let status = row["status"] as? String ?? "unresolved"
            let knownWitnessStatuses = ["eligible_structural_only", "unresolved", "blocked", "declined"]
            let displayedWitnessStatus = recordedWitnessStatus.flatMap { knownWitnessStatuses.contains($0) ? $0 : nil }
            calls.append(.init(id: identity, callPC: pc, callerPC: caller,
                calleeSymbol: callee?["symbol"] as? String ?? "Unattributed target",
                status: supported ? (["recovered_candidate", "declined"].contains(status) ? status : "unresolved") : "unavailable",
                reason: supported ? row["reason"] as? String : "Unsupported model profile; raw evidence only",
                testPC: supported ? address(row["test_pc"]) : nil, successPC: supported ? address(row["success_pc"]) : nil, errorPC: supported ? address(row["error_pc"]) : nil,
                witnessStatus: supported && witness != nil ? (witnessConsistent ? displayedWitnessStatus ?? "unresolved" : "unresolved") : nil,
                witnessReason: supported ? witness?["reason"] as? String : nil,
                witnessFacts: supported ? facts.keys.sorted().map { "\($0): \(facts[$0] ?? "unavailable")" } : [],
                witnessWorkSteps: supported ? count(validation?["work_steps"]) : nil,
                witnessCheckedInstructionCount: supported ? count(validation?["checked_instruction_count"]) : nil,
                witnessEdges: supported ? edges.compactMap { edge in
                    guard let from = edge["from"] as? String, let to = edge["to"] as? String,
                          let pc = address(edge["provenance_pc"]) else { return nil }
                    return "\(from) → \(to) · \(pc)"
                } : [],
                detailJSON: String(decoding: detail, as: UTF8.self)))
        }
        var accounting = "\(calls.count) retained calls · scan \(wordComplete ? "complete" : "partial") · details \(detailComplete ? "complete" : "partial")"
        if let summary = object["summary"] as? [String: Any] {
            let labels = [("scanned_word_count", "scanned words"), ("observed_direct_call_count", "observed direct calls"), ("omitted_call_count", "omitted calls")]
            for (key, label) in labels {
                guard let number = unsignedInteger(summary[key]) else { throw fail("invalid summary accounting") }
                accounting += " · \(number) \(label)"
            }
        } else {
            accounting += " · source accounting unavailable"
        }
        let summary = object["summary"] as? [String: Any]
        let omitted = unsignedInteger(summary?["omitted_call_count"]).flatMap { $0 <= UInt64(Int.max) ? Int($0) : nil }
        accounting += " · witness details \(hasWitnesses ? (witnessComplete ? "complete" : "partial") : "not requested")"
        let uuid = image["uuid"] as? String ?? "unavailable"
        let sliceOffset = unsignedInteger(image["slice_offset"]) ?? 0
        return .init(sourceData: data, imageDescription: "\(architecture) · UUID \(uuid) · base \(base) · container offset \(sliceOffset) · slice size \(size) · slice SHA256 \(digest) · container SHA256 \(container)",
            modelVersion: model, supportsInterpretation: supported, wordScanComplete: wordComplete,
            callDetailsComplete: detailComplete, witnessesComplete: witnessComplete, calls: calls,
            limitations: limitations, summaryText: accounting, omittedCallCount: omitted)
    }
}
