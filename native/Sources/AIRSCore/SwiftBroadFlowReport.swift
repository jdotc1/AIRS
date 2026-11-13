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
        let callerTestProfile = object["model_version"] as? String == "swift-broad-error-flow-extended-v2"
            && object["profile"] as? String == "broad-extended-v2"
        let importsProfile = object["model_version"] as? String == "swift-broad-error-flow-imports-v1"
            && object["profile"] as? String == "broad-imports-v1"
        let extendedProfile = object["model_version"] as? String == "swift-broad-error-flow-extended-v1"
            && object["profile"] as? String == "broad-extended-v1"
        let maxCalls: Int = importsProfile || extendedProfile || callerTestProfile ? 8192 : maximumCalls
        guard let model = object["model_version"] as? String,
              let identity = object["identity"] as? [String: Any],
              let architecture = identity["architecture"] as? String,
              let subtype = unsigned(identity["cpu_subtype"]), subtype <= UInt64(UInt32.max),
              let containerDigest = digest(identity["container_sha256"]), let sliceDigest = digest(identity["slice_sha256"]),
              let base = address(identity["preferred_base"]),
              let offset = hex(identity["slice_offset"]), let size = hex(identity["slice_size"]), size > 0, offset <= UInt64.max - size,
              let sliceIndex = unsigned(identity["slice_index"]), let sliceCount = unsigned(identity["container_slice_count"]),
              sliceCount > 0, sliceCount <= 4096, sliceIndex < sliceCount,
              let rows = object["calls"] as? [[String: Any]], rows.count <= maxCalls,
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
            guard let counters = object[key] as? [String: Any], counters.count <= maxCalls else { throw fail("invalid status/reason accounting") }
            var total = 0
            for value in counters.values {
                guard let n = count(value), n <= 262_144, total <= 524_288 - n else { throw fail("invalid status/reason counts") }; total += n
            }
            if key == "status_counts" && total != rows.count { throw fail("status denominator mismatch") }
        }
        let reportedProfile = object["profile"] as? String
        let profilePairSupported = AnalysisModels.swiftBroadNativePairs.contains(where: { pair in
            pair.model == model && pair.profile == reportedProfile
        })
        let importSummary: String
        if importsProfile || callerTestProfile {
            importSummary = try validateImportEnvelope(object, rows: rows, selected: selected, observed: observed,
                detailsComplete: detailsComplete, limitations: limitations, boolean: boolean, count: count)
        } else { importSummary = "" }
        let supported = profilePairSupported
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
        var importStubs: [UInt64: Data] = [:]
        var callerShapes: [String: Int] = [:], callerDeclines: [String: Int] = [:]
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
            let importRow = (importsProfile || callerTestProfile) && admission?["model_version"] as? String == "swift-broad-import-callsite-v1"
            let gotRow = callerTestProfile && admission?["model_version"] as? String == "swift-broad-got-callsite-v1"
            if callerTestProfile {
                if importRow || gotRow {
                    try validateCallerErrorTest(row, call: callNumber, caller: callerNumber,
                        boolean: boolean, address: address, shapes: &callerShapes, declines: &callerDeclines)
                } else if row["caller_error_test"] != nil {
                    throw fail("caller error test without imported callsite model")
                }
            }
            var importFacts: [String] = []
            if importsProfile || callerTestProfile {
                if importRow, let admission {
                    importFacts = try validateImportRow(row, admission: admission, call: callNumber,
                        caller: callerNumber, sliceOffset: offset, sliceSize: size, stubs: &importStubs,
                        boolean: boolean, unsigned: unsigned, count: count, nonclaims: nonclaims,
                        allowDisagreement: callerTestProfile)
                } else if !gotRow {
                    let importKeys = ["import_attribution_admitted", "callee_stub_pc", "import_provenance", "library_ordinal"]
                    if importKeys.contains(where: { admission?[$0] != nil }) {
                        throw fail("import evidence without import callsite model")
                    }
                }
            }
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
            if supported && importRow {
                facts = importFacts.map { summary($0) }
            } else if supported {
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
        if callerTestProfile {
            for (key, expected) in [("caller_error_test_counts", callerShapes),
                                    ("caller_error_test_decline_counts", callerDeclines)] {
                guard let counters = object[key] as? [String: Any], Set(counters.keys) == Set(expected.keys) else {
                    throw fail("invalid caller error test counters")
                }
                for (name, value) in expected where count(counters[name]) != value {
                    throw fail("caller error test counter mismatch")
                }
            }
        }
        let uuidText = uuid as? String ?? "explicitly absent"
        let accounting = "\(calls.count) retained calls · \(omitted) omitted calls · \(scanned) scanned words · \(observed) observed call instructions · \(selected) selected candidates · \(analysisWork) analysis work · scan \(wordComplete ? "complete" : "partial") · details \(detailsComplete ? "complete" : "partial") · witnesses \(witnessesComplete ? "complete" : "partial")"
        return .init(sourceData: data,
            imageDescription: "\(architecture) · full CPU subtype \(subtype) · UUID \(uuidText) · base \(base) · slice index \(sliceIndex) of \(sliceCount) · container offset 0x\(String(offset, radix: 16)) · slice size 0x\(String(size, radix: 16)) · slice SHA256 \(sliceDigest) · container SHA256 \(containerDigest)",
            modelVersion: model, supportsInterpretation: supported, wordScanComplete: wordComplete,
            callDetailsComplete: detailsComplete, witnessesComplete: witnessesComplete, calls: calls,
            limitations: limitations, summaryText: accounting + importSummary, omittedCallCount: omitted)
    }

    /// Checks bounded recorded shape only; no input bytes or callee behavior are established.
    private static func validateCallerErrorTest(
        _ row: [String: Any], call: UInt64, caller: UInt64,
        boolean: (Any?) -> Bool?, address: (Any?) -> String?,
        shapes: inout [String: Int], declines: inout [String: Int]
    ) throws {
        func fail() -> SwiftFlowReportError { .invalid("broad-extended-v2: malformed caller error test") }
        func pc(_ value: Any?) -> UInt64? {
            guard let text = address(value) else { return nil }
            return UInt64(text.dropFirst(2), radix: 16)
        }
        func window(_ value: Any?, maximum: Int) throws -> [[String: Any]] {
            guard let words = value as? [[String: Any]], words.count <= maximum else { throw fail() }
            var previous: UInt64?
            for word in words {
                guard Set(word.keys) == Set(["pc", "word", "kind"]), let here = pc(word["pc"]),
                      let text = word["word"] as? String, text.count == 10, text.hasPrefix("0x"),
                      text.dropFirst(2).utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
                      let kind = word["kind"] as? String, !kind.isEmpty, kind.utf8.count <= 64 else { throw fail() }
                if let previous, previous > UInt64.max - 4 || here != previous + 4 { throw fail() }
                previous = here
            }
            return words
        }
        guard let fact = row["caller_error_test"] as? [String: Any],
              Set(fact.keys) == Set(["model", "postcall", "precall", "shape", "claims_callee_behaviour"]),
              fact["model"] as? String == AnalysisModels.swiftCallerErrorTest,
              boolean(fact["claims_callee_behaviour"]) == false,
              let pre = fact["precall"] as? [String: Any],
              let post = fact["postcall"] as? [String: Any],
              let preStatus = pre["status"] as? String,
              ["x21_zeroed", "x21_not_zeroed", "precall_entries_unchecked", "precall_window_outside_caller"].contains(preStatus),
              let shape = fact["shape"] as? String else { throw fail() }
        let before = preStatus == "x21_zeroed"
        let after = post["status"] as? String == "recovered_candidate"
        let expectedShape = before ? (after ? "swifterror_idiom" : "precall_zero_only")
                                   : (after ? "postcall_test_only" : "none")
        guard shape == expectedShape,
              Set(pre.keys) == Set(before ? ["status", "zero_pc", "window"] : ["status", "window"]) else { throw fail() }
        let preWords = try window(pre["window"], maximum: 4)
        for word in preWords {
            guard let here = pc(word["pc"]), here >= caller, here < call, call - here <= 16 else { throw fail() }
        }
        if let last = preWords.last {
            guard let lastPC = pc(last["pc"]), call >= 4, lastPC == call - 4 else { throw fail() }
        }
        if before {
            guard let first = preWords.first, pc(pre["zero_pc"]) == pc(first["pc"]),
                  first["word"] as? String == "0xaa1f03f5", first["kind"] as? String == "mov" else { throw fail() }
        }
        let postWords = try window(post["window"], maximum: 8)
        if let first = postWords.first {
            guard call <= UInt64.max - 4, pc(first["pc"]) == call + 4 else { throw fail() }
        }
        if after {
            let baseKeys: Set<String> = ["status", "test_pc", "tested_register", "success_pc", "error_pc", "window"]
            let compare = post["test_kind"] as? String == "cmp_zero_bcond"
            let expectedKeys = compare ? baseKeys.union(["test_kind", "comparison_pc", "test_condition"]) : baseKeys
            guard Set(post.keys) == expectedKeys, let last = postWords.last,
                  let test = pc(post["test_pc"]), pc(last["pc"]) == test, test <= UInt64.max - 4,
                  let success = pc(post["success_pc"]), let error = pc(post["error_pc"]),
                  success > test, error > test, success != error,
                  let register = post["tested_register"] as? String,
                  (0...30).map({ "x\($0)" }).contains(register) else { throw fail() }
            if compare {
                guard postWords.count >= 2, let comparison = pc(post["comparison_pc"]), test >= 4,
                      comparison == test - 4, pc(postWords[postWords.count - 2]["pc"]) == comparison,
                      last["kind"] as? String == "bcond",
                      let condition = post["test_condition"] as? String, ["eq", "ne"].contains(condition),
                      (condition == "eq" ? error : success) == test + 4 else { throw fail() }
            } else {
                guard let kind = last["kind"] as? String, ["xcbz", "xcbnz"].contains(kind),
                      (kind == "xcbz" ? error : success) == test + 4 else { throw fail() }
            }
        } else {
            let reasons: Set<String> = ["comparison_branch_unmodeled", "intervening_instruction_unmodeled",
                "comparison_branch_not_adjacent_or_supported", "error_value_clobbered",
                "not_error_result_comparison", "narrow_error_test", "literal_prefix_requires_compare_test",
                "not_error_result_test", "unsupported_successor_region",
                "comparison_branch_missing_or_outside_window", "postcall_window_exhausted"]
            guard Set(post.keys) == Set(["reason", "window"]), let reason = post["reason"] as? String,
                  reasons.contains(reason) else { throw fail() }
            declines[reason, default: 0] += 1
        }
        guard let admission = row["admission"] as? [String: Any],
              admission["status"] as? String == "unresolved", row["candidate"] is NSNull,
              row["validation"] is NSNull, boolean(admission["call_return_proven"]) == false,
              boolean(admission["syntactic_call_target_admitted"]) == false,
              boolean(admission["import_attribution_admitted"]) == true,
              admission["abi"] == nil, let reason = admission["reason"] as? String,
              let declaration = admission["declaration"] as? [String: Any] else { throw fail() }
        let declarationIdentity = declaration["identity"] as? [String: Any]
        let nonthrowing = declaration["status"] as? String == "syntax_admitted"
            && boolean(declarationIdentity?["throws"]) == false
        if nonthrowing {
            guard shape == "swifterror_idiom", reason == "declaration_caller_disagreement",
                  ["bl", "blr_got"].contains(admission["call_kind"] as? String ?? "") else { throw fail() }
        } else if reason != "imported_callee_abi_unqualified" { throw fail() }
        shapes[shape, default: 0] += 1
    }

    private static func validateImportEnvelope(
        _ object: [String: Any], rows: [[String: Any]], selected: Int, observed: Int,
        detailsComplete: Bool, limitations: [String], boolean: (Any?) -> Bool?, count: (Any?) -> Int?
    ) throws -> String {
        func fail(_ message: String) -> SwiftFlowReportError { .invalid("broad-v1: " + message) }
        let keys: Set<String> = ["attributed_stubs", "declined_stubs", "invalid_stub_sections",
            "selected_import_calls", "non_throwing_swift_import_calls", "non_swift_import_calls", "declined_stub_calls"]
        guard object["import_stub_model"] as? String == "arm64-import-stub-double-binding-v1",
              let complete = boolean(object["import_stubs_complete"]),
              let rawCounts = object["import_stub_counts"] as? [String: Any], Set(rawCounts.keys) == keys,
              limitations.filter({ $0 == "imported_callees_attribution_only" }).count == 1,
              boolean(object["call_return_proven"]) == false,
              boolean(object["runtime_reachability_proven"]) == false else {
            throw fail("invalid import envelope or non-claims")
        }
        var counts: [String: Int] = [:]
        // Call counters can reach the imports scan limit (2,097,152 words); the stub and section
        // counts keep their own tighter caps in the accounting check below.
        for key in keys {
            guard let value = count(rawCounts[key]), value <= 2_097_152 else { throw fail("invalid import count") }
            counts[key] = value
        }
        let attributed = counts["attributed_stubs", default: 0]
        let declined = counts["declined_stubs", default: 0]
        let invalid = counts["invalid_stub_sections", default: 0]
        let selectedImports = counts["selected_import_calls", default: 0]
        var importRows = 0
        for row in rows {
            let admission = row["admission"] as? [String: Any]
            if admission?["model_version"] as? String == "swift-broad-import-callsite-v1" { importRows += 1 }
        }
        guard attributed + declined <= 65_536, invalid <= 4096,
              selectedImports <= selected, importRows <= selectedImports else { throw fail("invalid import accounting") }
        var accounted = selected
        for key in ["declined_stub_calls", "non_swift_import_calls", "non_throwing_swift_import_calls"] {
            let value = counts[key, default: 0]
            guard value <= observed - accounted else { throw fail("import calls exceed observed instructions") }
            accounted += value
        }
        let state: String
        if complete {
            guard object["import_stub_reason"] is NSNull else { throw fail("complete import table has a reason") }
            state = "complete"
        } else {
            guard let reason = object["import_stub_reason"] as? String, !reason.isEmpty, reason.utf8.count <= 256,
                  !detailsComplete, attributed == 0, declined == 0, invalid == 0,
                  selectedImports == 0, importRows == 0 else { throw fail("invalid incomplete import table") }
            state = "incomplete: " + reason
        }
        let nonSwift = counts["non_swift_import_calls", default: 0]
        let nonThrowing = counts["non_throwing_swift_import_calls", default: 0]
        let declinedCalls = counts["declined_stub_calls", default: 0]
        var summary = " · import stubs \(state)"
        summary += " · \(attributed) attributed / \(declined) declined stubs"
        summary += " · \(selectedImports) selected import calls"
        summary += " · \(nonSwift)/\(nonThrowing)/\(declinedCalls) skipped"
        return summary
    }

    private static func validateImportRow(
        _ row: [String: Any], admission: [String: Any], call: UInt64, caller: UInt64,
        sliceOffset: UInt64, sliceSize: UInt64, stubs: inout [UInt64: Data],
        boolean: (Any?) -> Bool?, unsigned: (Any?) -> UInt64?, count: (Any?) -> Int?,
        nonclaims: (Any) -> Bool, allowDisagreement: Bool = false
    ) throws -> [String] {
        func fail(_ message: String) -> SwiftFlowReportError { .invalid("broad-v1: " + message) }
        let disagreement = allowDisagreement && admission["reason"] as? String == "declaration_caller_disagreement"
        guard row["candidate"] is NSNull, row["validation"] is NSNull,
              admission["status"] as? String == "unresolved",
              (admission["reason"] as? String == "imported_callee_abi_unqualified" || disagreement),
              let kind = admission["call_kind"] as? String, ["bl", "b"].contains(kind),
              unsigned(admission["call_pc"]) == call, unsigned(admission["caller_start"]) == caller,
              let stub = unsigned(admission["callee_stub_pc"]), stub % 4 == 0, stub != call,
              let symbol = admission["symbol"] as? String, !symbol.isEmpty, symbol.utf8.count <= 4096,
              symbol.utf8.allSatisfy({ $0 < 128 }), symbol.drop(while: { $0 == "_" }).hasPrefix("$s"),
              let ordinal = unsigned(admission["library_ordinal"]), ordinal <= 255 else {
            throw fail("invalid import call binding")
        }
        guard boolean(admission["details_complete"]) == true,
              boolean(admission["call_return_proven"]) == false,
              boolean(admission["syntactic_call_target_admitted"]) == false,
              boolean(admission["import_attribution_admitted"]) == true,
              count(admission["work_steps"]) != nil, nonclaims(admission),
              admission["abi"] == nil, admission["callee_pc"] == nil else {
            throw fail("invalid import attribution non-claims")
        }
        guard let provenance = admission["import_provenance"] as? [String: Any],
              provenance["stub_model"] as? String == "arm64-import-stub-double-binding-v1",
              let stubSection = provenance["stub_section"] as? String, stubSection.utf8.count <= 64,
              let pointerSection = provenance["pointer_section"] as? String, pointerSection.utf8.count <= 64,
              let stubIndex = unsigned(provenance["stub_index"]),
              let symbolIndex = unsigned(provenance["symbol_index"]),
              let pointer = unsigned(provenance["pointer_address"]), pointer % 8 == 0,
              unsigned(provenance["stub_indirect_entry_offset"]) != nil,
              unsigned(provenance["pointer_indirect_entry_offset"]) != nil,
              unsigned(provenance["nlist_offset"]) != nil,
              let words = provenance["stub_words"] as? [[String: Any]], words.count == 3 else {
            throw fail("invalid import stub provenance")
        }
        var decoded: [UInt64] = []
        var firstFileOffset: UInt64 = 0
        for (index, word) in words.enumerated() {
            let delta = UInt64(index * 4)
            // The three words are consecutive, and the 12-byte stub lies inside the slice.
            let remaining: UInt64 = 12 - delta
            guard stub <= UInt64.max - delta, unsigned(word["pc"]) == stub + delta,
                  let text = word["word"] as? String, text.utf8.count == 10, text.hasPrefix("0x"),
                  text.dropFirst(2).utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
                  let number = UInt64(text.dropFirst(2), radix: 16),
                  let fileOffset = unsigned(word["slice_file_offset"]),
                  fileOffset <= sliceSize, sliceSize - fileOffset >= remaining,
                  fileOffset <= UInt64.max - sliceOffset,
                  unsigned(word["container_file_offset"]) == fileOffset + sliceOffset else {
                throw fail("invalid import stub word or offset")
            }
            if index == 0 { firstFileOffset = fileOffset }
            guard fileOffset >= delta, fileOffset - delta == firstFileOffset else {
                throw fail("import stub words are not consecutive")
            }
            decoded.append(number)
        }
        // The single admitted pattern is ADRP x16; LDR x16, [x16, #imm]; BR x16.
        let w0 = decoded[0], w1 = decoded[1], w2 = decoded[2]
        guard w0 & 0x9f00001f == 0x90000010, w1 & 0xffc003ff == 0xf9400210,
              w2 == 0xd61f0200 else { throw fail("invalid import stub instruction pattern") }
        let immediateHigh: UInt64 = ((w0 >> 5) & 0x7ffff) << 2
        let immediateLow: UInt64 = (w0 >> 29) & 3
        var immediate = Int64(immediateHigh | immediateLow)
        if immediate & (1 << 20) != 0 { immediate -= 1 << 21 }
        let displacement: Int64 = immediate * 4096 + Int64(((w1 >> 10) & 0xfff) * 8)
        let page: UInt64 = stub & ~UInt64(0xfff)
        let slot: UInt64
        if displacement < 0 {
            let magnitude = UInt64(-displacement)
            guard page >= magnitude else { throw fail("import pointer underflow") }
            slot = page - magnitude
        } else {
            let magnitude = UInt64(displacement)
            guard page <= UInt64.max - magnitude else { throw fail("import pointer overflow") }
            slot = page + magnitude
        }
        guard slot == pointer, slot <= UInt64.max - 7 else { throw fail("import pointer binding mismatch") }
        guard let declaration = admission["declaration"] as? [String: Any],
              Set(declaration.keys) == Set(["status", "identity", "reason"]),
              let declarationStatus = declaration["status"] as? String else { throw fail("invalid import declaration") }
        let declarationFact: String
        switch declarationStatus {
        case "syntax_admitted":
            guard let identity = declaration["identity"] as? [String: Any], declaration["reason"] is NSNull,
                  identity["symbol"] as? String == symbol,
                  let syntax = identity["syntax_model"] as? String else { throw fail("invalid admitted import declaration") }
            if syntax == "swift-import-declaration-syntax-v1" {
                guard boolean(identity["throws"]) == !disagreement else { throw fail("import declaration is not throwing") }
                declarationFact = disagreement
                    ? "Declaration syntax says non-throwing; caller x21 idiom disagrees (review required)."
                    : "Declaration syntax: syntax_admitted (throws per mangled name)"
            } else {
                declarationFact = "Declaration syntax: declaration syntax model unrecognized; raw only"
            }
        case "syntax_unresolved":
            guard declaration["identity"] is NSNull, let reason = declaration["reason"] as? String,
                  !reason.isEmpty, reason.utf8.count <= 256 else { throw fail("invalid unresolved import declaration") }
            declarationFact = "Declaration syntax: syntax_unresolved · " + reason
        default: throw fail("invalid import declaration status")
        }
        var binding: [String: Any] = [:]
        binding["symbol"] = symbol
        binding["library_ordinal"] = ordinal
        binding["import_provenance"] = provenance
        binding["declaration"] = declaration
        let encoded = try JSONSerialization.data(withJSONObject: binding, options: [.sortedKeys])
        if let previous = stubs[stub], previous != encoded { throw fail("inconsistent repeated import stub") }
        stubs[stub] = encoded
        let stubText = "0x" + String(stub, radix: 16)
        let pointerText = "0x" + String(pointer, radix: 16)
        var attribution = "Imported callee: attributed through stub \(stubText) (\(stubSection) #\(stubIndex))"
        attribution += " · pointer \(pointerText) in \(pointerSection) · symbol index \(symbolIndex)"
        attribution += " · library ordinal \(ordinal) (recorded; not a dyld binding)"
        return [attribution, declarationFact,
            "No ABI admission, outcome witness or validation was recorded for this call (attribution only).",
            "Recorded attribution only; no source bytes were reread by this view.",
            "Stub section bounds are not recorded; this view cannot check section containment."]
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
