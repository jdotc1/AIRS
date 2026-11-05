import Foundation
import CoreFoundation

/// A bounded projection of recorded broad-v1 results, never an independent byte validator.
/// Source JSON remains the export authority. Import creates no source-read capability.
enum SwiftBroadFlowReport {
    static let maximumBytes = 16 * 1024 * 1024
    static let maximumCalls = 4096

    static func validateJSON(_ data: Data) throws {
        guard data.count <= SwiftFlowReport.maximumBytes else { throw SwiftFlowReportError.invalid("64 MiB JSON input limit exceeded") }
        try Task.checkCancellation()
        var wire = BroadJSONKeyPreflight(data: data)
        try wire.check()
    }

    static func decode(_ object: [String: Any], data: Data, jsonPreflighted: Bool = false) throws -> SwiftFlowReport {
        func fail(_ message: String) -> SwiftFlowReportError { .invalid("broad-v1: " + message) }
        guard data.count <= maximumBytes else { throw fail("16 MiB report limit exceeded") }
        try Task.checkCancellation()
        if !jsonPreflighted { try validateJSON(data) }
        var nodes = 0
        func inspect(_ value: Any, depth: Int) throws {
            nodes += 1
            if nodes % 1024 == 0 { try Task.checkCancellation() }
            guard nodes <= 2_000_000, depth <= 32 else { throw fail("nested evidence limit exceeded") }
            if let text = value as? String {
                guard text.utf8.count <= 65_536 else { throw fail("evidence string limit exceeded") }
            } else if let dict = value as? [String: Any] {
                for (key, child) in dict { try inspect(key, depth: depth + 1); try inspect(child, depth: depth + 1) }
            } else if let array = value as? [Any] {
                for child in array { try inspect(child, depth: depth + 1) }
            } else if let number = value as? NSNumber {
                guard number.doubleValue.isFinite else { throw fail("nonfinite number") }
            }
        }
        try inspect(object, depth: 0)
        func boolean(_ value: Any?) -> Bool? {
            guard let number = value as? NSNumber, CFGetTypeID(number) == CFBooleanGetTypeID() else { return nil }
            return number.boolValue
        }
        func unsigned(_ value: Any?) -> UInt64? {
            guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
                  !["f", "d"].contains(String(cString: number.objCType)), number.doubleValue >= 0 else { return nil }
            return number.uint64Value
        }
        func count(_ value: Any?) -> Int? {
            guard let n = unsigned(value), n <= UInt64(Int.max) else { return nil }; return Int(n)
        }
        func hex(_ value: Any?, aligned: Bool = false) -> UInt64? {
            guard let text = value as? String, text.hasPrefix("0x"), text.count <= 18,
                  let n = UInt64(text.dropFirst(2), radix: 16), text == "0x" + String(n, radix: 16),
                  !aligned || n % 4 == 0 else { return nil }; return n
        }
        func address(_ value: Any?) -> String? { hex(value, aligned: true) == nil ? nil : value as? String }
        func digest(_ value: Any?) -> String? {
            guard let text = value as? String, text.utf8.count == 64,
                  text.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else { return nil }; return text
        }
        func json(_ value: Any, pretty: Bool = false) throws -> Data {
            try JSONSerialization.data(withJSONObject: value, options: pretty ? [.sortedKeys, .prettyPrinted] : [.sortedKeys, .fragmentsAllowed])
        }
        guard let model = object["model_version"] as? String,
              let identity = object["identity"] as? [String: Any],
              let architecture = identity["architecture"] as? String,
              let subtype = unsigned(identity["cpu_subtype"]), subtype <= UInt64(UInt32.max),
              let containerDigest = digest(identity["container_sha256"]), let sliceDigest = digest(identity["slice_sha256"]),
              let base = address(identity["preferred_base"]),
              let offset = hex(identity["slice_offset"]), let size = hex(identity["slice_size"]), size > 0, offset <= UInt64.max - size,
              let sliceIndex = unsigned(identity["slice_index"]), let sliceCount = unsigned(identity["container_slice_count"]),
              sliceCount > 0, sliceCount <= 4096, sliceIndex < sliceCount,
              let rows = object["calls"] as? [[String: Any]], rows.count <= maximumCalls,
              let limitations = object["limitations"] as? [String], limitations.count <= 64,
              let wordComplete = boolean(object["word_scan_complete"]), let detailsComplete = boolean(object["call_details_complete"]),
              let witnessesComplete = boolean(object["outcome_witnesses_complete"]),
              let observed = count(object["observed_call_instructions"]), let selected = count(object["selected_call_candidates"]),
              let omitted = count(object["omitted_calls"]), let scanned = count(object["scanned_words"]),
              let analysisWork = count(object["analysis_work"]), selected <= observed, omitted <= selected,
              rows.count == selected - omitted else { throw fail("invalid report shape, identity or accounting") }
        guard let uuid = identity["uuid"], uuid is NSNull || ((uuid as? String).flatMap(UUID.init(uuidString:)) != nil) else { throw fail("missing or malformed UUID state") }
        if omitted > 0 && (detailsComplete || witnessesComplete) { throw fail("omissions contradict completeness") }
        for key in ["status_counts", "reason_counts"] {
            guard let counters = object[key] as? [String: Any], counters.count <= maximumCalls else { throw fail("invalid status/reason accounting") }
            var total = 0
            for value in counters.values {
                guard let n = count(value), n <= 262_144, total <= 524_288 - n else { throw fail("invalid status/reason counts") }; total += n
            }
            if key == "status_counts" && total != rows.count { throw fail("status denominator mismatch") }
        }
        let supported = model == "swift-broad-error-flow-v1" && object["profile"] as? String == "broad-v1"
            && object["witness_model_version"] as? String == "swift-outcome-witness-v2"
            && object["validation_model_version"] as? String == "swift-outcome-validation-v2"
            && architecture == "arm64" && [UInt64(0), UInt64(1)].contains(subtype)
            && boolean(object["research_only"]) == true && boolean(object["call_return_proven"]) == false
            && boolean(object["runtime_reachability_proven"]) == false
        func nonclaims(_ value: Any) -> Bool {
            if let dict = value as? [String: Any] {
                return dict.allSatisfy { key, child in
                    (!(key.hasSuffix("_proven") || key == "source_reconstruction_allowed") || boolean(child) == false) && nonclaims(child)
                }
            }
            if let array = value as? [Any] { return array.allSatisfy(nonclaims) }
            return true
        }
        func complete(_ value: Any?) -> Bool {
            guard let record = value as? [String: Any], let missing = record["missing"] as? [String] else { return false }
            return boolean(record["complete"]) == true && missing.isEmpty
        }
        var seen = Set<String>(), calls: [SwiftFlowCall] = []
        for row in rows {
            try Task.checkCancellation()
            guard let callPC = address(row["call_pc"]), let callerPC = address(row["caller_pc"]),
                  let callNumber = hex(callPC), let callerNumber = hex(callerPC), callerNumber <= callNumber,
                  seen.insert(callerPC + ":" + callPC).inserted else { throw fail("invalid or duplicate call identity") }
            let admission = row["admission"] as? [String: Any]
            let candidate = row["candidate"] as? [String: Any]
            let validation = row["validation"] as? [String: Any]
            for key in ["admission", "candidate", "validation"] {
                guard let value = row[key], value is NSNull || value is [String: Any] else { throw fail("invalid call evidence state") }
            }
            for record in [candidate, validation].compactMap({ $0 }) {
                guard try json(record).count <= 256 * 1024 else { throw fail("witness/validation exceeds 256 KiB") }
            }
            if let pc = admission?["call_pc"], unsigned(pc) != callNumber { throw fail("admission call binding mismatch") }
            var fullyBound = false
            if let candidate {
                guard let binding = candidate["identity"] as? [String: Any] else { throw fail("missing candidate identity state") }
                for key in ["container_sha256", "slice_sha256", "architecture", "cpu_subtype", "uuid", "preferred_base", "slice_index", "container_slice_count", "slice_offset", "slice_size"] where binding[key] != nil {
                    if ["cpu_subtype", "slice_index", "container_slice_count"].contains(key), unsigned(binding[key]) == nil { throw fail("invalid numeric candidate identity") }
                    guard let recorded = binding[key], let expected = identity[key], try json(recorded) == json(expected) else { throw fail("candidate image binding mismatch") }
                }
                if let pc = binding["call_pc"], address(pc) != callPC { throw fail("candidate call binding mismatch") }
                if let call = candidate["call"] as? [String: Any], let pc = call["pc"], address(pc) != callPC { throw fail("candidate call evidence mismatch") }
                for role in ["caller", "callee"] where binding[role] != nil {
                    guard binding[role] is [String: Any] else { throw fail("candidate function range must be an object") }
                }
                if let caller = binding["caller"] as? [String: Any] {
                    guard address(caller["start_pc"]) == callerPC, let end = hex(caller["end_pc_exclusive"], aligned: true), end > callNumber,
                          caller["boundary_source"] as? String == "lc_function_starts" else { throw fail("candidate caller range mismatch") }
                }
                let identityKeys = ["container_sha256", "slice_sha256", "architecture", "cpu_subtype", "uuid", "preferred_base", "slice_index", "container_slice_count", "slice_offset", "slice_size", "call_pc", "caller", "callee"]
                fullyBound = identityKeys.allSatisfy { binding[$0] != nil }
                    && binding["caller"] is [String: Any] && binding["callee"] is [String: Any]
                if let callee = binding["callee"] as? [String: Any] {
                    guard let start = hex(callee["start_pc"], aligned: true), let end = hex(callee["end_pc_exclusive"], aligned: true), end > start,
                          callee["boundary_source"] as? String == "lc_function_starts" else { throw fail("candidate callee range mismatch") }
                    if let target = admission?["callee_pc"], unsigned(target) != start { throw fail("admission callee binding mismatch") }
                    if let call = candidate["call"] as? [String: Any], let target = call["callee_pc"], hex(target, aligned: true) != start { throw fail("candidate callee binding mismatch") }
                }
            }
            let recordedStatus = validation?["status"] as? String ?? admission?["status"] as? String ?? "unresolved"
            let validationModels = validation?["model_version"] as? String == "swift-outcome-validation-v2"
                && candidate?["model_version"] as? String == "swift-outcome-witness-v2"
                && candidate?["validation_model"] as? String == "swift-outcome-validation-v2" && candidate?["profile"] as? String == "broad-v1"
            let proofs = ["runtime_branch_proven", "call_return_proven", "error_state_proven", "source_reconstruction_allowed", "handler_semantics_proven", "exclusive_entry_proven"]
            let expectedSources = ["edge": "swift-broad-error-flow-v1", "witness": "swift-outcome-witness-v2", "validation": "swift-outcome-validation-v2", "cfg": "swift-bounded-structural-cfg-v1", "value": "swift-outcome-values-v1"]
            let sourceModelsSupported = candidate?["source_models"] as? [String: String] == expectedSources
            let candidateCall = candidate?["call"] as? [String: Any]
            let candidateABI = candidateCall?["abi"] as? [String: Any], admittedABI = admission?["abi"] as? [String: Any]
            let candidateDeclaration = candidateCall?["declaration"] as? [String: Any], admittedDeclaration = admission?["declaration"] as? [String: Any]
            let abiProfile = candidateABI?["profile"] as? String ?? ""
            let abiSupported = ["swift6-arm64-sync-untyped-research-v1", "swift6-arm64-sync-untyped-stable-research-v2"].contains(abiProfile)
                && candidateABI?["status"] as? String == "admitted" && candidateABI?["error_register"] as? String == "x21"
            let candidateIdentity = candidate?["identity"] as? [String: Any]
            let candidateCallee = candidateIdentity?["callee"] as? [String: Any]
            let targetPC = hex(candidateCallee?["start_pc"], aligned: true)
            let admissionConsistent = try admission?["status"] as? String == "admitted_callsite" && abiSupported
                && unsigned(admission?["call_pc"]) == callNumber && targetPC != nil && unsigned(admission?["callee_pc"]) == targetPC
                && candidateABI != nil && admittedABI != nil && json(candidateABI ?? [:]) == json(admittedABI ?? [:])
                && candidateDeclaration?["status"] as? String == "syntax_admitted" && admittedDeclaration != nil
                && json(candidateDeclaration ?? [:]) == json(admittedDeclaration ?? [:])
            let factStatuses = validation?["fact_statuses"] as? [String: String] ?? [:]
            let coreFacts = ["identity", "call", "abi", "cfg", "post_call", "regions"]
            let valueStatus = validation?["value_fact_status"] as? String ?? ""
            let valueStates = ["checked_symbolic_values", "checked_with_explicit_unknowns", "not_applicable_no_return_paths"]
            let checkedFacts = coreFacts.allSatisfy { factStatuses[$0] == "checked" }
                && valueStates.contains(valueStatus) && factStatuses["values"] == valueStatus
            let consistent = validationModels && sourceModelsSupported && admissionConsistent && checkedFacts && fullyBound && candidate?["status"] as? String == "unresolved" && boolean(candidate?["eligible"]) == false
                && proofs.allSatisfy { boolean(validation?[$0]) == false } && nonclaims(candidate ?? [:]) && nonclaims(validation ?? [:])
                && validation?["eligibility_scope"] as? String == "checked_structural_facts_only"
            let eligible = consistent && recordedStatus == "eligible_structural_only" && boolean(validation?["eligible"]) == true
                && complete(validation?["completeness"]) && complete(candidate?["completeness"])
            let status: String
            if !supported { status = "unavailable" }
            else if recordedStatus == "eligible_structural_only" { status = eligible ? "eligible_structural_only" : "unresolved" }
            else { status = ["unresolved", "declined", "blocked", "tail_call_candidate", "admitted_callsite"].contains(recordedStatus) ? recordedStatus : "unresolved" }
            let rawDetail = try json(row, pretty: true)
            guard rawDetail.count <= 1024 * 1024 else { throw fail("call detail exceeds 1 MiB") }
            var facts: [String] = []
            func summary(_ text: String) -> String {
                text.utf8.count <= 2048 ? text : String(text.prefix(512)) + " … [summary truncated; see original JSON]"
            }
            if supported {
                for key in ["status", "reason"] { if let text = admission?[key] as? String { facts.append("Admission \(key): \(summary(text))") } }
                for key in ["declaration", "abi"] {
                    if let value = admission?[key] as? [String: Any] { facts.append("\(key): \(summary(value["status"] as? String ?? "unavailable")) · \(summary(value["reason"] as? String ?? "see recorded details"))") }
                }
                let knownFacts = coreFacts + ["values"]
                let knownStates = ["checked", "unchecked"] + valueStates
                for key in knownFacts {
                    let state = factStatuses[key] ?? "unchecked"
                    facts.append("Independent \(key): \(knownStates.contains(state) ? state : "unrecognized; see original JSON")")
                }
                let additional = factStatuses.keys.filter { !knownFacts.contains($0) }.count
                if additional > 0 { facts.append("\(additional) additional fact-status fields retained in original JSON.") }
                if let value = validation?["outcome_scope"] as? String { facts.append("Outcome scope: \(summary(value))") }
                facts.append("Recorded validation only; no source bytes were reread by this view.")
            }
            let postCall = candidate?["post_call"] as? [String: Any]
            let reason = !supported ? "Unsupported broad model profile; raw evidence only"
                : recordedStatus == "eligible_structural_only" && !eligible ? "Recorded eligibility has inconsistent or unsupported evidence; inspect the retained call details."
                : validation?["reason"] as? String ?? admission?["reason"] as? String
            calls.append(.init(id: callerPC + ":" + callPC, callPC: callPC, callerPC: callerPC,
                calleeSymbol: admission?["symbol"] as? String ?? "Unattributed target", status: status, reason: reason,
                testPC: supported ? address(postCall?["test_pc"]) : nil,
                successPC: supported ? address(postCall?["success_successor_pc"]) : nil,
                errorPC: supported ? address(postCall?["error_successor_pc"]) : nil,
                witnessStatus: supported && validation != nil ? status : nil,
                witnessReason: reason, witnessFacts: facts,
                witnessWorkSteps: supported ? count((validation?["accounting"] as? [String: Any])?["work"]) : nil,
                witnessCheckedInstructionCount: supported ? count((validation?["accounting"] as? [String: Any])?["instructions"]) : nil,
                witnessEdges: [], detailJSON: String(decoding: rawDetail, as: UTF8.self)))
        }
        let uuidText = uuid as? String ?? "explicitly absent"
        let accounting = "\(calls.count) retained calls · \(omitted) omitted calls · \(scanned) scanned words · \(observed) observed call instructions · \(selected) selected candidates · \(analysisWork) analysis work · scan \(wordComplete ? "complete" : "partial") · details \(detailsComplete ? "complete" : "partial") · witnesses \(witnessesComplete ? "complete" : "partial")"
        return .init(sourceData: data,
            imageDescription: "\(architecture) · full CPU subtype \(subtype) · UUID \(uuidText) · base \(base) · slice index \(sliceIndex) of \(sliceCount) · container offset 0x\(String(offset, radix: 16)) · slice size 0x\(String(size, radix: 16)) · slice SHA256 \(sliceDigest) · container SHA256 \(containerDigest)",
            modelVersion: model, supportsInterpretation: supported, wordScanComplete: wordComplete,
            callDetailsComplete: detailsComplete, witnessesComplete: witnessesComplete, calls: calls,
            limitations: limitations, summaryText: accounting, omittedCallCount: omitted)
    }
}

/// A lexical preflight preserving exact decoded key bytes. Foundation remains the
/// JSON grammar/value decoder; duplicate object members must never become last-wins
/// identities, profiles or proof claims. No source document is canonicalized here.
private struct BroadJSONKeyPreflight {
    let bytes: [UInt8]
    var position = 0
    var values = 0
    init(data: Data) { bytes = Array(data) }
    func invalid() -> SwiftFlowReportError { .invalid("broad-v1: malformed or duplicate JSON object key") }
    mutating func whitespace() { while position < bytes.count && [UInt8(9), 10, 13, 32].contains(bytes[position]) { position += 1 } }
    mutating func string() throws -> Data {
        guard position < bytes.count, bytes[position] == 34 else { throw invalid() }
        let start = position; position += 1
        while position < bytes.count {
            if position % 1024 == 0 { try Task.checkCancellation() }
            let byte = bytes[position]; position += 1
            if byte == 34 {
                guard position - start <= 393_218,
                      let key = try JSONSerialization.jsonObject(with: Data(bytes[start..<position]), options: [.fragmentsAllowed]) as? String else { throw invalid() }
                return Data(key.utf8)
            }
            if byte == 92 { guard position < bytes.count else { throw invalid() }; position += 1 }
        }
        throw invalid()
    }
    mutating func value(depth: Int) throws {
        try Task.checkCancellation()
        values += 1
        guard depth <= 32, values <= 2_000_000 else { throw invalid() }
        whitespace(); guard position < bytes.count else { throw invalid() }
        switch bytes[position] {
        case 123:
            position += 1; whitespace()
            if position < bytes.count && bytes[position] == 125 { position += 1; return }
            var keys = Set<Data>()
            while position < bytes.count {
                whitespace(); let key = try string()
                guard keys.insert(key).inserted else { throw invalid() }
                values += 1; guard values <= 2_000_000 else { throw invalid() }
                whitespace(); guard position < bytes.count && bytes[position] == 58 else { throw invalid() }; position += 1
                try value(depth: depth + 1); whitespace()
                guard position < bytes.count else { throw invalid() }
                let next = bytes[position]; position += 1
                if next == 125 { return }; guard next == 44 else { throw invalid() }
            }
            throw invalid()
        case 91:
            position += 1; whitespace()
            if position < bytes.count && bytes[position] == 93 { position += 1; return }
            while position < bytes.count {
                try value(depth: depth + 1); whitespace()
                guard position < bytes.count else { throw invalid() }
                let next = bytes[position]; position += 1
                if next == 93 { return }; guard next == 44 else { throw invalid() }
            }
            throw invalid()
        case 34: _ = try string()
        default:
            let start = position
            while position < bytes.count && ![UInt8(9), 10, 13, 32, 44, 93, 125].contains(bytes[position]) { position += 1 }
            guard position > start else { throw invalid() }
        }
    }
    mutating func check() throws {
        try value(depth: 0); whitespace()
        guard position == bytes.count else { throw invalid() }
    }
}
