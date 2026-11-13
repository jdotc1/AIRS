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
        try validateV4Report(object)
        let v4Profile = object["model_version"] as? String == v4Model && object["profile"] as? String == v4ProfileName
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
        let indirectProfile = v4Profile || (object["model_version"] as? String == "swift-broad-error-flow-extended-v3"
            && object["profile"] as? String == "broad-extended-v3")
        let callerTestProfile = indirectProfile || (object["model_version"] as? String == "swift-broad-error-flow-extended-v2"
            && object["profile"] as? String == "broad-extended-v2")
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
        var indirectShapes: [String: Int] = [:], indirectAdmission: [String: Int] = ["admitted": 0, "refused": 0]
        var indirectConditions: [String: Int] = [:]
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
                        boolean: boolean, address: address, shapes: &callerShapes, declines: &callerDeclines, v4: v4Profile)
                } else if row["caller_error_test"] != nil {
                    throw fail("caller error test without imported callsite model")
                }
            }
            if indirectProfile {
                try validateIndirectRecords(row, admission: admission, call: callNumber, importRow: importRow, gotRow: gotRow,
                    boolean: boolean, address: address, hex: { hex($0) }, unsigned: unsigned, shapes: &indirectShapes,
                    admissions: &indirectAdmission, conditions: &indirectConditions)
            }
            var importFacts: [String] = []
            if importsProfile || callerTestProfile {
                if importRow, let admission {
                    importFacts = try validateImportRow(row, admission: admission, call: callNumber,
                        caller: callerNumber, sliceOffset: offset, sliceSize: size, stubs: &importStubs,
                        boolean: boolean, unsigned: unsigned, count: count, nonclaims: nonclaims,
                        allowDisagreement: callerTestProfile, v4: v4Profile)
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
                if v4Profile { facts += v4Facts(row) }
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
        if indirectProfile {
            guard object["indirect_target_shape_model"] as? String == AnalysisModels.swiftIndirectTargetShape,
                  object["value_witness_admission_model"] as? String == AnalysisModels.swiftValueWitnessAdmission,
                  limitations.filter({ $0 == "indirect_target_shape_does_not_claim_callee_behaviour" }).count == 1,
                  limitations.filter({ $0 == "value_witness_admission_by_abi_with_recorded_provenance" }).count == 1,
                  let shapeCounts = object["indirect_target_shape_counts"] as? [String: Any],
                  let admissionCounts = object["value_witness_admission_counts"] as? [String: Any],
                  let conditionCounts = object["value_witness_refusal_condition_counts"] as? [String: Any],
                  Set(shapeCounts.keys) == Set(indirectShapes.keys), Set(admissionCounts.keys) == ["admitted", "refused"],
                  Set(conditionCounts.keys) == Set(indirectConditions.keys) else { throw fail("invalid indirect target counters") }
            for (counters, expected) in [(shapeCounts, indirectShapes), (admissionCounts, indirectAdmission),
                                         (conditionCounts, indirectConditions)] {
                for (name, value) in expected where count(counters[name]) != value { throw fail("indirect target counter mismatch") }
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

    private static let indirectClasses: Set<String> = ["value_witness", "protocol_witness_slot", "class_vtable", "closure_context",
        "got_or_global_fnptr", "static_address", "runtime_or_objc_ptr", "unknown"]
    private static let valueWitnessSlots: Set<UInt64> = [0x0, 0x8, 0x10, 0x18, 0x20, 0x28, 0x30, 0x38, 0x58, 0x60, 0x68]
    private static let runtimeMetadataFunctions: Set<String> = [
        "swift_getGenericMetadata", "swift_getTypeByMangledNameInContext",
        "swift_getTypeByMangledNameInContextInMetadataState", "swift_getTypeByMangledNameInContext2",
        "swift_getTypeByMangledNameInContextInMetadataState2", "swift_checkMetadataState",
        "swift_getExistentialTypeMetadata", "swift_getAssociatedTypeWitness"]

    /// Checks the recorded tier 1 shape and tier 2 admission records of one base callsite row.
    /// Everything is recorded evidence: no input bytes or callee behavior are established here.
    private static func validateIndirectRecords(
        _ row: [String: Any], admission: [String: Any]?, call: UInt64, importRow: Bool, gotRow: Bool,
        boolean: (Any?) -> Bool?, address: (Any?) -> String?, hex: (Any?) -> UInt64?, unsigned: (Any?) -> UInt64?,
        shapes: inout [String: Int], admissions: inout [String: Int], conditions: inout [String: Int]
    ) throws {
        func fail(_ message: String) -> SwiftFlowReportError { .invalid("broad-extended-v3: " + message) }
        let admittedReason = "value_witness_abi_nonthrowing"
        let reason = admission?["reason"] as? String
        let required = reason == "indirect_target_unresolved" || reason == admittedReason
        let shapeValue = row["indirect_target_shape"], witnessValue = row["value_witness_admission"]
        if shapeValue == nil && witnessValue == nil {
            if required { throw fail("indirect row without shape and admission records") }
            return
        }
        guard !importRow, !gotRow, admission?["model_version"] as? String == "swift-broad-callsite-v1",
              let shape = shapeValue as? [String: Any], let witness = witnessValue as? [String: Any] else {
            throw fail("indirect records on a row that cannot carry them")
        }
        let shapeKeys: Set<String> = ["model", "site_pc", "site_kind", "class", "slot_offset", "unknown_reason",
            "deciding_instructions", "evidence", "class_before_join_refusal", "slot_address", "slot_section",
            "claims_callee_behaviour", "bounds"]
        guard Set(shape.keys) == shapeKeys, shape["model"] as? String == AnalysisModels.swiftIndirectTargetShape,
              let cls = shape["class"] as? String, indirectClasses.contains(cls),
              boolean(shape["claims_callee_behaviour"]) == false,
              let sitePC = address(shape["site_pc"]), hex(sitePC) == call,
              shape["site_kind"] is NSNull || (shape["site_kind"] as? String).map({ !$0.isEmpty && $0.utf8.count <= 16 }) == true,
              shape["unknown_reason"] is NSNull || (shape["unknown_reason"] as? String).map({ $0.utf8.count <= 256 }) == true,
              shape["evidence"] is NSNull || (shape["evidence"] as? String).map({ $0.utf8.count <= 1024 }) == true,
              let deciding = shape["deciding_instructions"] as? [[String: Any]], deciding.count <= 64,
              shape["bounds"] is [String: Any] else { throw fail("malformed indirect target shape") }
        var slot: UInt64?
        if let value = shape["slot_offset"], !(value is NSNull) {
            // The producer records the target load's signed offset for every class (ldur sign-extends imm9).
            guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
                  !["f", "d"].contains(String(cString: number.objCType)),
                  number.int64Value >= -0x100, number.int64Value <= 0xffff else { throw fail("malformed shape slot") }
            slot = number.int64Value >= 0 ? UInt64(number.int64Value) : nil
        }
        var words: [UInt64: (word: UInt64, role: String)] = [:]
        for item in deciding {
            guard Set(item.keys) == ["pc", "word", "role"], let pcText = address(item["pc"]), let pc = hex(pcText),
                  let wordText = item["word"] as? String, wordText.hasPrefix("0x"), wordText.utf8.count == 10,
                  let word = UInt64(wordText.dropFirst(2), radix: 16), let role = item["role"] as? String, !role.isEmpty, role.utf8.count <= 64,
                  words.updateValue((word, role), forKey: pc) == nil else { throw fail("malformed shape deciding instruction") }
        }
        guard Set(witness.keys).isSuperset(of: ["model", "admitted", "provenance_kind", "first_failing_condition", "reason",
                  "site_pc", "site_kind", "slot_offset", "claims_callee_behaviour"]),
              witness["model"] as? String == AnalysisModels.swiftValueWitnessAdmission,
              let admitted = boolean(witness["admitted"]),
              boolean(witness["claims_callee_behaviour"]) == false,
              let kind = witness["provenance_kind"] as? String, !kind.isEmpty, kind.utf8.count <= 64,
              let witnessReason = witness["reason"] as? String, !witnessReason.isEmpty, witnessReason.utf8.count <= 256,
              address(witness["site_pc"]) == sitePC else { throw fail("malformed value witness admission") }
        shapes[cls, default: 0] += 1
        if !admitted {
            guard let failing = unsigned(witness["first_failing_condition"]), (1...3).contains(failing),
                  reason != admittedReason else {
                throw fail("refused admission without a failing condition or with the admitted reason")
            }
            admissions["refused", default: 0] += 1
            conditions[String(failing), default: 0] += 1
            return
        }
        // Admitted: the recorded provenance must satisfy design section 2 tier 2 on its own.
        guard reason == admittedReason, admission?["status"] as? String == "declined",
              witness["first_failing_condition"] is NSNull, witnessReason == "meets_tier2_conditions",
              cls == "value_witness", let slot, valueWitnessSlots.contains(slot),
              unsigned(witness["slot_offset"]) == slot,
              ["metadata_accessor_call", "imported_metadata_accessor_call", "runtime_metadata_call"].contains(kind),
              let register = witness["metadata_register"] as? String, register.hasPrefix("x"),
              let registerNumber = Int(register.dropFirst()), (0...30).contains(registerNumber),
              let symbol = witness["symbol"] as? String, !symbol.isEmpty, symbol.utf8.count <= 4096,
              symbol.unicodeScalars.allSatisfy({ $0.value > 0x20 && $0.value < 0x7f }),
              let calleeText = address(witness["metadata_callee_pc"]), let callee = hex(calleeText) else {
            throw fail("admitted value witness lacks tier 2 provenance")
        }
        let canonical = symbol.hasPrefix("_") ? String(symbol.dropFirst()) : symbol
        if kind == "runtime_metadata_call" {
            guard runtimeMetadataFunctions.contains(canonical) else { throw fail("admitted runtime function is not allowlisted") }
        } else {
            guard (canonical.hasPrefix("$s") || canonical.hasPrefix("$S")), canonical.hasSuffix("Ma"), canonical.utf8.count > 4 else {
                throw fail("admitted symbol is not a metadata accessor")
            }
        }
        // The metadata is x0 from a direct bl recorded as the deciding metadata_call_result, possibly
        // carried through a recorded chain of mov / add #0 copies that ends in the named register.
        let copies = words.filter { $0.value.role == "metadata_copy" }.sorted { $0.key < $1.key }
        var carried = 0
        for copy in copies {
            let w = copy.value.word
            let isMov = w & 0xffe0_ffe0 == 0xaa00_03e0           // orr xd, xzr, xm
            let isAddZero = w & 0xffff_fc00 == 0x9100_0000        // add xd, xn, #0 (no shift)
            guard isMov || isAddZero, copy.key % 4 == 0 else { throw fail("admitted metadata copy is not a mov") }
            let source = isMov ? Int((w >> 16) & 0x1f) : Int((w >> 5) & 0x1f)
            guard source == carried, w & 0x1f != 31, source != 31 else { throw fail("admitted metadata copy chain is broken") }
            carried = Int(w & 0x1f)
        }
        guard registerNumber == carried, copies.isEmpty == (registerNumber == 0) else {
            throw fail("admitted metadata register is not the recorded copy of x0")
        }
        let calls = words.filter { $0.value.role == "metadata_call_result" }
        guard calls.count == 1, let found = calls.first, found.value.word & 0xfc00_0000 == 0x9400_0000, found.key % 4 == 0 else {
            throw fail("admitted site lacks a recorded direct metadata call")
        }
        var imm = Int64(found.value.word & 0x03ff_ffff)
        if imm & 0x0200_0000 != 0 { imm -= 0x0400_0000 }
        let target = Int64(bitPattern: found.key) &+ imm &* 4
        guard target >= 0, UInt64(target) == callee else { throw fail("admitted metadata callee does not match the recorded call") }
        admissions["admitted", default: 0] += 1
    }

    /// Checks bounded recorded shape only; no input bytes or callee behavior are established.
    private static func validateCallerErrorTest(
        _ row: [String: Any], call: UInt64, caller: UInt64,
        boolean: (Any?) -> Bool?, address: (Any?) -> String?,
        shapes: inout [String: Int], declines: inout [String: Int], v4: Bool = false
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
        if !v4 {
            let declarationIdentity = declaration["identity"] as? [String: Any]
            let nonthrowing = declaration["status"] as? String == "syntax_admitted"
                && boolean(declarationIdentity?["throws"]) == false
            if nonthrowing {
                guard shape == "swifterror_idiom", reason == "declaration_caller_disagreement",
                      ["bl", "blr_got"].contains(admission["call_kind"] as? String ?? "") else { throw fail() }
            } else if reason != "imported_callee_abi_unqualified" { throw fail() }
        }
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
        nonclaims: (Any) -> Bool, allowDisagreement: Bool = false, v4: Bool = false
    ) throws -> [String] {
        func fail(_ message: String) -> SwiftFlowReportError { .invalid("broad-v1: " + message) }
        let disagreement = allowDisagreement && !v4 && admission["reason"] as? String == "declaration_caller_disagreement"
        let v4Reason = v4 && v4RowReasons.values.contains(admission["reason"] as? String ?? "")
        guard row["candidate"] is NSNull, row["validation"] is NSNull,
              admission["status"] as? String == "unresolved",
              (admission["reason"] as? String == "imported_callee_abi_unqualified" || disagreement || v4Reason),
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
              v4 ? Set(declaration.keys) == Set(v4RecordKeys) : Set(declaration.keys) == Set(["status", "identity", "reason"]),
              let declarationStatus = v4 ? declaration["decision"] as? String : declaration["status"] as? String else {
            throw fail("invalid import declaration")
        }
        let declarationFact: String
        if v4 {
            // The compact record is checked by the v4 report rules; here it is only described.
            let why = declaration["reason"] as? String
            declarationFact = "Declaration record: " + declarationStatus + (why.map { " · " + $0 } ?? "")
                + " (decided from the symbol name; the callee is not shown to behave so)"
        } else {
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

    // MARK: - broad-extended-v4

    private static let v4Model = "swift-broad-error-flow-extended-v4"
    private static let v4ProfileName = "broad-extended-v4"
    private static let v4EffectModel = "swift-import-effect-admission-v1"
    private static let v4GrammarModel = "swift-declaration-syntax-v2"
    private static let v4GroupNames = ["capabilities", "limits", "omission_causes", "omitted_by_kind", "unselected_call_counts",
        "scan", "import_calls", "decision_by_shape", "decision_summary"]
    /// Every top-level key a v4 report may carry: the v3 report fields, the GOT envelope the engine records beside them,
    /// and the nine v4 groups. Any other key is refused.
    private static let v4TopLevelKeys: Set<String> = [
        "analysis_work", "call_details_complete", "call_return_proven", "caller_error_test_counts",
        "caller_error_test_decline_counts", "calls", "capabilities", "chained_fixups_model",
        "chained_fixups_status", "decision_by_shape", "decision_summary", "got_binding_model",
        "got_binding_reason", "got_bindings_complete", "got_counts", "got_decline_counts",
        "got_slot_decline_counts", "got_window_model", "identity", "import_calls", "import_stub_counts",
        "import_stub_model", "import_stub_reason", "import_stubs_complete", "indirect_target_shape_counts",
        "indirect_target_shape_model", "limitations", "limits", "model_version", "observed_call_instructions",
        "omission_causes", "omitted_by_kind", "omitted_calls", "outcome_witnesses_complete", "profile",
        "reason_counts", "research_only", "runtime_reachability_proven", "scan", "scanned_words",
        "selected_call_candidates", "status_counts", "unselected_call_counts", "validation_model_version",
        "value_witness_admission_counts", "value_witness_admission_model",
        "value_witness_refusal_condition_counts", "witness_model_version", "word_scan_complete"]
    private static let v4Premises = ["symbol_name_carries_effects", "no_silgen_name_override", "name_only_attribution",
        "binding_not_proven", "grammar_pinned"]
    private static let v4NotClaimed = ["callee_returns", "dyld_binding", "runtime_callee", "arguments_and_results",
        "error_value_at_runtime"]
    private static let v4LimitKeys = ["max_total_evidence", "max_observations_per_function", "max_instructions_per_function",
        "max_total_instructions", "analysis_work_ceiling", "output_budget_bytes", "import_table_entries",
        "import_table_byte_reserve"]
    private static let v4Causes = ["analysis_work_budget", "per_function_limit", "total_row_limit", "output_budget"]
    private static let v4Kinds = ["import_stub", "import_got", "local_swift_direct", "indirect"]
    private static let v4Buckets = ["skipped_non_throwing", "non_swift_import", "declined_stub",
        "direct_target_not_swift_function", "direct_target_unattributed"]
    private static let v4Decisions = ["non_throwing", "throwing", "async", "undecided"]
    private static let v4Shapes = ["swifterror_idiom", "postcall_test_only", "precall_zero_only", "none"]
    private static let v4ScanKeys = ["words_total", "words_scanned", "words_unscanned_per_function_ceiling",
        "words_unscanned_total_ceiling", "words_excluded_boundary", "functions_total", "functions_excluded_boundary",
        "functions_truncated", "candidates_in_unscanned_words", "candidates_in_unscanned_words_reason"]
    private static let v4EntryKeys = ["symbol", "decision", "reason", "calls", "stub_calls", "got_calls", "retained",
        "skipped_non_throwing", "not_swift_calls", "omitted"]
    private static let v4ResidualKeys = ["symbols", "calls", "retained", "skipped_non_throwing", "not_swift_calls", "omitted"]
    private static let v4RecordKeys = ["syntax_model", "decision", "reason", "entity", "throws", "is_async", "typed_throws",
        "identity_sha256"]
    /// The closed reason list of the declaration grammar. Read from the record only; the grammar is never run here.
    private static let v4Reasons: Set<String> = ["invalid_input", "thunk_or_specialization", "unknown_substitution", "truncated",
        "malformed_symbol", "trailing_input", "unsupported_production", "limit_exceeded", "typed_throws", "accessor",
        "not_function_entity"]
    /// Entity names the grammar gives accessors; a record naming one is undecided with reason accessor (finding 6).
    private static let v4AccessorEntities: Set<String> = ["Getter", "Setter", "MaterializeForSet", "GlobalGetter", "WillSet",
        "DidSet", "ReadAccessor", "ModifyAccessor", "YieldingMutateAccessor", "YieldingBorrowAccessor", "BorrowAccessor",
        "MutateAccessor", "InitAccessor", "UnsafeMutableAddressor", "OwningMutableAddressor", "NativeOwningMutableAddressor",
        "NativePinningMutableAddressor", "UnsafeAddressor", "OwningAddressor", "NativeOwningAddressor",
        "NativePinningAddressor"]
    private static let v4Licences = ["no_error_exit", "declared_error_exit", "refused_unsupported_effect", "none"]
    private static let v4Relations = ["conflict", "corroborated", "no_signal", "not_applicable"]
    private static let v4RowReasons: [String: String] = [
        "no_error_exit": "declaration_caller_disagreement",
        "declared_error_exit": "imported_callee_outcome_unmodeled",
        "refused_unsupported_effect": "imported_callee_effect_unsupported",
        "none": "imported_callee_abi_unqualified"]
    private static let v4ScanMarkers: Set<String> = ["excluded_boundary"]
    private static let v4RetentionLimit = 8192

    /// The recorded licence and caller relation of one import row, as view facts.
    private static func v4Facts(_ row: [String: Any]) -> [String] {
        guard let effect = row["effect_admission"] as? [String: Any],
              let licence = effect["licence_class"] as? String, let relation = effect["caller_relation"] as? String else { return [] }
        return ["Licence class: \(licence) · caller relation: \(relation) (recorded; the call stays unresolved)"]
    }

    private static func v4Fail(_ rule: String, _ text: String) -> SwiftFlowReportError { .invalid(rule + ": " + text) }

    /// The licence class that a compact declaration record gives, by the table of contract 4.3.
    private static func v4LicenceClass(decision: String, isAsync: Bool?, typedThrows: String?) -> String {
        switch decision {
        case "non_throwing": return "no_error_exit"
        case "throwing":
            return (isAsync == true || (typedThrows != nil && typedThrows != "none")) ? "refused_unsupported_effect" : "declared_error_exit"
        case "async": return "refused_unsupported_effect"
        default: return "none"
        }
    }

    /// The caller relation the tables of 4.4 give; nil means no retained row may exist for that case.
    private static func v4ExpectedRelation(licence: String, shape: String, tail: Bool) -> String? {
        switch licence {
        case "no_error_exit": return shape == "swifterror_idiom" && !tail ? "conflict" : nil
        case "declared_error_exit": return tail ? "not_applicable" : (shape == "swifterror_idiom" ? "corroborated" : "no_signal")
        default: return "not_applicable"
        }
    }

    private static func v4Canonical(_ value: Any) -> Data? {
        try? JSONSerialization.data(withJSONObject: value, options: [.sortedKeys, .fragmentsAllowed])
    }

    /// The v4 report rules of the design contract, with the rule id leading every message. Shape and arithmetic only:
    /// the grammar, the digest and the demangler are never recomputed here. Applies only to the v4 pair; any other
    /// report that names the v4 identity or carries a v4 group is refused (E2).
    private static func validateV4Report(_ object: [String: Any]) throws {
        let model = object["model_version"] as? String, profile = object["profile"] as? String
        let pair = model == v4Model && profile == v4ProfileName
        let present = v4GroupNames.filter { object[$0] != nil }
        guard pair else {
            if model == v4Model || profile == v4ProfileName || !present.isEmpty {
                throw v4Fail("E2", "v4 identity or fields appear outside the v4 pair")
            }
            if let rows = object["calls"] as? [[String: Any]], rows.contains(where: { $0["effect_admission"] != nil }) {
                throw v4Fail("E2", "a row effect_admission appears outside the v4 pair")
            }
            return
        }
        let missing = v4GroupNames.filter { object[$0] == nil }
        guard missing.isEmpty else { throw v4Fail("E2", "a v4 report requires every v4 group; missing \(missing)") }
        guard Set(object.keys).isSubset(of: v4TopLevelKeys) else {
            throw v4Fail("E2", "unknown top-level key \(Set(object.keys).subtracting(v4TopLevelKeys).sorted())")
        }
        func integer(_ rule: String, _ value: Any?, _ what: String) throws -> Int {
            guard let number = value as? NSNumber, CFGetTypeID(number) != CFBooleanGetTypeID(),
                  !["f", "d"].contains(String(cString: number.objCType)), number.doubleValue >= 0,
                  number.uint64Value <= UInt64(Int.max) else { throw v4Fail(rule, "\(what) must be a non-negative integer") }
            return Int(number.uint64Value)
        }
        func flag(_ rule: String, _ value: Any?, _ what: String) throws -> Bool {
            guard let number = value as? NSNumber, CFGetTypeID(number) == CFBooleanGetTypeID() else {
                throw v4Fail(rule, "\(what) must be a boolean")
            }
            return number.boolValue
        }
        func add(_ rule: String, _ left: Int, _ right: Int) throws -> Int {
            let (sum, overflow) = left.addingReportingOverflow(right)
            guard !overflow else { throw v4Fail(rule, "integer overflow in a sum") }
            return sum
        }
        func total(_ rule: String, _ values: [Int]) throws -> Int { try values.reduce(0) { try add(rule, $0, $1) } }
        func mapping(_ rule: String, _ value: Any?, _ what: String, _ keys: [String]) throws -> [String: Any] {
            guard let dict = value as? [String: Any], Set(dict.keys) == Set(keys) else {
                throw v4Fail(rule, "\(what) must be an object with exactly the keys \(keys)")
            }
            return dict
        }
        func counts(_ rule: String, _ value: Any?, _ what: String, _ keys: [String]) throws -> [String: Int] {
            let dict = try mapping(rule, value, what, keys)
            var result: [String: Int] = [:]
            for key in keys { result[key] = try integer(rule, dict[key], "\(what).\(key)") }
            return result
        }

        // E1: capabilities and limits.
        let expectedText: [String: String] = ["report_model": v4Model, "effect_admission_model": v4EffectModel,
            "declaration_syntax_model": v4GrammarModel, "grammar_pin": "swift-6.4.2-RELEASE",
            "caller_error_test_model": AnalysisModels.swiftCallerErrorTest]
        guard let capabilities = object["capabilities"] as? [String: Any],
              Set(capabilities.keys) == Set(expectedText.keys).union(["premises", "not_claimed"]),
              expectedText.allSatisfy({ capabilities[$0.key] as? String == $0.value }),
              capabilities["premises"] as? [String] == v4Premises,
              capabilities["not_claimed"] as? [String] == v4NotClaimed else {
            throw v4Fail("E1", "capabilities must equal the fixed strings")
        }
        let limits = try counts("E1", object["limits"], "limits", v4LimitKeys)

        guard let rows = object["calls"] as? [[String: Any]] else { throw v4Fail("A1", "calls must be an array of objects") }
        // The existing row bound keeps its existing message.
        guard rows.count <= 8192 else { throw SwiftFlowReportError.invalid("broad-v1: invalid report shape, identity or accounting") }

        // A1 to A6.
        let selected = try integer("A1", object["selected_call_candidates"], "selected_call_candidates")
        let omitted = try integer("A1", object["omitted_calls"], "omitted_calls")
        guard omitted <= selected, rows.count == selected - omitted else {
            throw v4Fail("A1", "len(calls) \(rows.count) != selected_call_candidates \(selected) - omitted_calls \(omitted)")
        }
        let causes = try counts("A2", object["omission_causes"], "omission_causes", v4Causes)
        let kinds = try counts("A2", object["omitted_by_kind"], "omitted_by_kind", v4Kinds)
        let causeSum = try total("A2", v4Causes.map { causes[$0] ?? 0 }), kindSum = try total("A2", v4Kinds.map { kinds[$0] ?? 0 })
        guard omitted == causeSum, omitted == kindSum else {
            throw v4Fail("A2", "omitted_calls \(omitted), sum of omission_causes \(causeSum), sum of omitted_by_kind \(kindSum) must be equal")
        }
        if omitted > 0 {
            for key in ["call_details_complete", "outcome_witnesses_complete"] where try flag("A3", object[key], key) {
                throw v4Fail("A3", "omitted_calls > 0 requires \(key) to be false")
            }
        }
        var statusSum = 0, reasonSum = 0
        for (key, name) in [("reason_counts", "reason"), ("status_counts", "status")] {
            guard let group = object[key] as? [String: Any] else { throw v4Fail("A4", "\(key) must be an object") }
            var sum = 0
            for (item, value) in group { sum = try add("A4", sum, try integer("A4", value, "\(key)[\(item)]")) }
            if name == "reason" {
                reasonSum = sum
                if let marker = group.keys.first(where: { v4ScanMarkers.contains($0) }) {
                    throw v4Fail("A4", "reason_counts carries the internal scan marker \(marker)")
                }
            } else { statusSum = sum }
        }
        guard reasonSum == rows.count else { throw v4Fail("A4", "sum(reason_counts) \(reasonSum) != len(calls) \(rows.count)") }
        guard statusSum == rows.count else { throw v4Fail("A4", "sum(status_counts) \(statusSum) != len(calls) \(rows.count)") }
        let unselected = try counts("A5", object["unselected_call_counts"], "unselected_call_counts", v4Buckets + ["other"])
        let observed = try integer("A5", object["observed_call_instructions"], "observed_call_instructions")
        let named = try total("A5", v4Buckets.map { unselected[$0] ?? 0 })
        guard observed == (try add("A5", selected, named)) else {
            throw v4Fail("A5", "observed_call_instructions \(observed) != selected \(selected) + unselected buckets \(named)")
        }
        guard unselected["other"] == 0 else { throw v4Fail("A5", "unselected_call_counts.other must be 0") }
        let maxEvidence = limits["max_total_evidence"] ?? 0, maxPerFunction = limits["max_observations_per_function"] ?? 0
        guard maxEvidence == v4RetentionLimit else {
            throw v4Fail("A6", "limits.max_total_evidence is \(maxEvidence), the retention limit is \(v4RetentionLimit)")
        }
        guard rows.count <= maxEvidence else { throw v4Fail("A6", "len(calls) exceeds limits.max_total_evidence") }
        if (causes["total_row_limit"] ?? 0) > 0, rows.count != maxEvidence {
            throw v4Fail("A6", "total_row_limit omissions with len(calls) \(rows.count) below limits.max_total_evidence \(maxEvidence)")
        }
        var perCaller: [String: Int] = [:]
        for row in rows {
            guard let caller = row["caller_pc"] as? String else { throw v4Fail("A6", "a row has no caller_pc") }
            perCaller[caller, default: 0] += 1
        }
        let busiest = perCaller.values.max() ?? 0
        guard busiest <= maxPerFunction else { throw v4Fail("A6", "a caller_pc has \(busiest) rows, above limits.max_observations_per_function") }
        if (causes["per_function_limit"] ?? 0) > 0, busiest != maxPerFunction {
            throw v4Fail("A6", "per_function_limit omissions but no caller_pc has exactly \(maxPerFunction) rows")
        }

        // B1 to B3.
        func scanBlock(_ rule: String) throws -> [String: Any] { try mapping(rule, object["scan"], "scan", v4ScanKeys) }
        func scanCounts(_ rule: String) throws -> [String: Int] {
            let scan = try scanBlock(rule)
            var result: [String: Int] = [:]
            for key in v4ScanKeys.prefix(8) { result[key] = try integer(rule, scan[key], "scan.\(key)") }
            return result
        }
        let scan1 = try scanCounts("B1")
        let scanParts = try total("B1", ["words_scanned", "words_unscanned_per_function_ceiling",
            "words_unscanned_total_ceiling", "words_excluded_boundary"].map { scan1[$0] ?? 0 })
        guard scan1["words_total"] == scanParts else { throw v4Fail("B1", "words_total != scanned + unscanned + excluded") }
        let scannedWords = try integer("B1", object["scanned_words"], "scanned_words")
        guard scan1["words_scanned"] == scannedWords else { throw v4Fail("B1", "words_scanned != scanned_words") }
        let scan2 = try scanCounts("B2")
        let wordComplete = try flag("B2", object["word_scan_complete"], "word_scan_complete")
        let truncated = scan2["functions_truncated"] ?? 0, excluded = scan2["functions_excluded_boundary"] ?? 0
        guard wordComplete == (truncated == 0 && excluded == 0) else {
            throw v4Fail("B2", "word_scan_complete \(wordComplete) with functions_truncated \(truncated) and functions_excluded_boundary \(excluded)")
        }
        let ceilingUnscanned = try add("B2", scan2["words_unscanned_per_function_ceiling"] ?? 0, scan2["words_unscanned_total_ceiling"] ?? 0)
        guard (truncated == 0) == (ceilingUnscanned == 0) else {
            throw v4Fail("B2", "functions_truncated \(truncated) does not agree with the unscanned word counts \(ceilingUnscanned)")
        }
        guard try add("B2", truncated, excluded) <= (scan2["functions_total"] ?? 0) else {
            throw v4Fail("B2", "functions_truncated + functions_excluded_boundary exceeds functions_total")
        }
        let scan3 = try scanCounts("B3"), scanBlock3 = try scanBlock("B3")
        let notDecoded = try add("B3", ceilingUnscanned, scan3["words_excluded_boundary"] ?? 0)
        let candidates = scanBlock3["candidates_in_unscanned_words"], candidateReason = scanBlock3["candidates_in_unscanned_words_reason"]
        if notDecoded == 0 {
            guard let value = candidates, !(value is NSNull), (try integer("B3", value, "candidates_in_unscanned_words")) == 0,
                  candidateReason is NSNull else {
                throw v4Fail("B3", "with no undecoded words candidates_in_unscanned_words must be 0 with a null reason")
            }
        } else {
            guard candidates is NSNull, candidateReason as? String == "words_not_decoded" else {
                throw v4Fail("B3", "with undecoded words candidates_in_unscanned_words must be null with reason words_not_decoded")
            }
        }

        // C1 to C7.
        func importBlock(_ rule: String) throws -> (complete: Bool, attributed: Int, swiftCalls: Int, distinct: Int,
                                                      entries: [[String: Any]], residual: [String: Int]) {
            let block = try mapping(rule, object["import_calls"], "import_calls",
                ["complete", "attributed_calls", "attributed_swift_calls", "distinct_symbols", "entries", "residual"])
            let complete = try flag(rule, block["complete"], "import_calls.complete")
            guard let entries = block["entries"] as? [[String: Any]] else { throw v4Fail(rule, "import_calls.entries must be an array of objects") }
            for item in entries {
                _ = try mapping(rule, item, "an import call entry", v4EntryKeys)
                guard item["symbol"] is String else { throw v4Fail(rule, "an import call entry needs a string symbol") }
                for key in v4EntryKeys where !["symbol", "decision", "reason"].contains(key) {
                    _ = try integer(rule, item[key], "entry \(key)")
                }
            }
            return (complete, try integer(rule, block["attributed_calls"], "import_calls.attributed_calls"),
                    try integer(rule, block["attributed_swift_calls"], "import_calls.attributed_swift_calls"),
                    try integer(rule, block["distinct_symbols"], "import_calls.distinct_symbols"), entries,
                    try counts(rule, block["residual"], "import_calls.residual", v4ResidualKeys))
        }
        func entryInt(_ item: [String: Any], _ key: String) -> Int { (item[key] as? NSNumber)?.intValue ?? 0 }
        func closes(_ item: [String: Int]) throws -> Bool {
            item["calls"] == (try total("C1", ["retained", "skipped_non_throwing", "not_swift_calls", "omitted"].map { item[$0] ?? 0 }))
        }
        let c1 = try importBlock("C1")
        for item in c1.entries {
            let symbol = item["symbol"] as? String ?? ""
            let calls = entryInt(item, "calls")
            let outcomes = try total("C1", ["retained", "skipped_non_throwing", "not_swift_calls", "omitted"].map { entryInt(item, $0) })
            guard calls == (try add("C1", entryInt(item, "stub_calls"), entryInt(item, "got_calls"))), calls == outcomes else {
                throw v4Fail("C1", "entry \(symbol) does not close: calls, stub + got and the outcomes must be equal")
            }
            guard let decision = item["decision"] as? String, v4Decisions.contains(decision) || decision == "not_swift" else {
                throw v4Fail("C1", "entry \(symbol) has an unknown decision")
            }
            let reason = item["reason"]
            guard reason is NSNull || reason is String, (decision == "undecided") == !(reason is NSNull) else {
                throw v4Fail("C1", "entry \(symbol): reason must be non-null exactly when the decision is undecided")
            }
            if let text = reason as? String, !v4Reasons.contains(text) {
                throw v4Fail("C1", "entry \(symbol) has a reason outside the grammar list")
            }
            guard (decision == "not_swift") == (entryInt(item, "not_swift_calls") == calls) else {
                throw v4Fail("C1", "entry \(symbol): not_swift_calls must equal calls exactly when the decision is not_swift")
            }
        }
        let c2 = try importBlock("C2")
        let symbols = c2.entries.compactMap { $0["symbol"] as? String }
        for index in symbols.indices.dropFirst() where symbols[index - 1] >= symbols[index] {
            throw v4Fail("C2", "entries must be unique and sorted by symbol")
        }
        guard c2.entries.count <= (limits["import_table_entries"] ?? 0) else { throw v4Fail("C2", "\(c2.entries.count) entries exceed limits.import_table_entries") }
        let entryCalls = try total("C2", c2.entries.map { entryInt($0, "calls") })
        guard c2.attributed == (try add("C2", entryCalls, c2.residual["calls"] ?? 0)) else {
            throw v4Fail("C2", "attributed_calls does not equal the entries plus residual.calls")
        }
        guard c2.distinct == (try add("C2", c2.entries.count, c2.residual["symbols"] ?? 0)) else {
            throw v4Fail("C2", "distinct_symbols does not equal len(entries) + residual.symbols")
        }
        let residualOutcomes = try total("C2", ["retained", "skipped_non_throwing", "not_swift_calls", "omitted"].map { c2.residual[$0] ?? 0 })
        guard c2.residual["calls"] == residualOutcomes else { throw v4Fail("C2", "the residual does not close: calls != retained + skipped + not_swift + omitted") }
        _ = try closes(c2.residual)
        let c3 = try importBlock("C3")
        guard c3.complete == (c3.residual["symbols"] == 0 && wordComplete) else {
            throw v4Fail("C3", "complete is \(c3.complete) but residual.symbols == 0 and word_scan_complete is \(wordComplete)")
        }
        let c4 = try importBlock("C4")
        func sumOver(_ rule: String, _ block: (entries: [[String: Any]], residual: [String: Int]), _ key: String) throws -> Int {
            try add(rule, try total(rule, block.entries.map { entryInt($0, key) }), block.residual[key] ?? 0)
        }
        let importRowCount = rows.filter { $0["effect_admission"] != nil }.count
        let retainedSum = try sumOver("C4", (c4.entries, c4.residual), "retained")
        guard retainedSum == importRowCount else { throw v4Fail("C4", "retained sums to \(retainedSum) but \(importRowCount) rows carry effect_admission") }
        guard try sumOver("C4", (c4.entries, c4.residual), "skipped_non_throwing") == unselected["skipped_non_throwing"] else {
            throw v4Fail("C4", "skipped_non_throwing differs from unselected_call_counts.skipped_non_throwing")
        }
        let notSwiftSum = try sumOver("C4", (c4.entries, c4.residual), "not_swift_calls")
        guard notSwiftSum == unselected["non_swift_import"] else { throw v4Fail("C4", "not_swift_calls differs from unselected_call_counts.non_swift_import") }
        guard try sumOver("C4", (c4.entries, c4.residual), "omitted") == (try add("C4", kinds["import_stub"] ?? 0, kinds["import_got"] ?? 0)) else {
            throw v4Fail("C4", "omitted differs from omitted_by_kind.import_stub + import_got")
        }
        let c5 = try importBlock("C5")
        guard notSwiftSum <= c5.attributed, c5.swiftCalls == c5.attributed - notSwiftSum else {
            throw v4Fail("C5", "attributed_swift_calls != attributed_calls - not_swift_calls")
        }
        func grid(_ rule: String) throws -> [String: [String: Int]] {
            let raw = try mapping(rule, object["decision_by_shape"], "decision_by_shape", v4Decisions)
            var result: [String: [String: Int]] = [:]
            for decision in v4Decisions { result[decision] = try counts(rule, raw[decision], "decision_by_shape.\(decision)", v4Shapes) }
            return result
        }
        let grid5 = try grid("C5")
        let cells = try total("C5", v4Decisions.flatMap { decision in v4Shapes.map { grid5[decision]?[$0] ?? 0 } })
        guard cells == c5.swiftCalls else { throw v4Fail("C5", "decision_by_shape sums to \(cells), attributed_swift_calls is \(c5.swiftCalls)") }
        let c6 = try importBlock("C6")
        let summary = try mapping("C6", object["decision_summary"], "decision_summary", ["names", "undecided_by_reason"])
        let names = try counts("C6", summary["names"], "decision_summary.names", v4Decisions)
        let listedSwift = c6.entries.filter { ($0["decision"] as? String) != "not_swift" }.count
        let residualSwiftCalls = (c6.residual["calls"] ?? 0) - (c6.residual["not_swift_calls"] ?? 0)
        let residualOther = c6.residual["not_swift_calls"] ?? 0, residualSymbols = c6.residual["symbols"] ?? 0
        let low = listedSwift + max(residualSwiftCalls > 0 ? 1 : 0, residualSymbols - residualOther)
        let high = listedSwift + min(residualSwiftCalls, residualSymbols - (residualOther > 0 ? 1 : 0))
        let nameSum = try total("C6", v4Decisions.map { names[$0] ?? 0 })
        guard low <= high else { throw v4Fail("C6", "the residual cannot hold any whole number of Swift symbols") }
        guard nameSum >= low, nameSum <= high else {
            throw v4Fail("C6", "decision_summary.names sums to \(nameSum), the distinct Swift symbols number \(low == high ? "\(low)" : "\(low) to \(high)")")
        }
        guard let byReason = summary["undecided_by_reason"] as? [String: Any] else { throw v4Fail("C6", "undecided_by_reason must be an object") }
        var reasonNames = 0, reasonCalls = 0
        for (reason, slot) in byReason {
            guard v4Reasons.contains(reason) else { throw v4Fail("C6", "undecided_by_reason key \(reason) is not in the closed reason list") }
            let parts = try counts("C6", slot, "undecided_by_reason[\(reason)]", ["names", "calls"])
            reasonNames = try add("C6", reasonNames, parts["names"] ?? 0); reasonCalls = try add("C6", reasonCalls, parts["calls"] ?? 0)
        }
        guard reasonNames == names["undecided"] else { throw v4Fail("C6", "undecided_by_reason names do not sum to names.undecided") }
        let grid6 = try grid("C6")
        let undecidedRow = try total("C6", v4Shapes.map { grid6["undecided"]?[$0] ?? 0 })
        guard reasonCalls == undecidedRow else { throw v4Fail("C6", "undecided_by_reason calls do not sum to the undecided row of decision_by_shape") }
        let c7 = try importBlock("C7")
        var entryDecisions: [String: String] = [:]
        for item in c7.entries { if let symbol = item["symbol"] as? String { entryDecisions[symbol] = item["decision"] as? String } }
        for row in rows {
            guard let witness = row["value_witness_admission"] as? [String: Any], (witness["admitted"] as? NSNumber).map({ CFGetTypeID($0) == CFBooleanGetTypeID() && $0.boolValue }) == true,
                  let symbol = witness["symbol"] as? String, let decision = entryDecisions[symbol] else { continue }
            // Contract 4.5, amended 10: a C runtime metadata function is not a Swift declaration and is listed not_swift;
            // a Swift metadata accessor is listed non_throwing.
            let kind = witness["provenance_kind"] as? String
            let expected = kind == "runtime_metadata_call" ? "not_swift" : "non_throwing"
            guard decision != expected else { continue }
            throw v4Fail("C7", "metadata symbol \(symbol) is admitted by the value-witness check as \(kind ?? "unknown") but listed \(decision)")
        }

        // D1 to D4, over the rows that carry effect_admission. A row with an import or GOT callsite model must carry it.
        let importModels: Set<String> = ["swift-broad-import-callsite-v1", "swift-broad-got-callsite-v1"]
        for row in rows {
            let model = (row["admission"] as? [String: Any])?["model_version"] as? String
            let isImport = model.map { importModels.contains($0) } ?? false
            if isImport && row["effect_admission"] == nil { throw v4Fail("D2", "an import row without effect_admission") }
            if !isImport && row["effect_admission"] != nil { throw v4Fail("D2", "effect_admission on a row without an import callsite model") }
        }
        let importRows = rows.filter { $0["effect_admission"] != nil }
        func admission(_ rule: String, _ row: [String: Any]) throws -> [String: Any] {
            guard let value = row["admission"] as? [String: Any] else { throw v4Fail(rule, "an import row needs an admission object") }
            return value
        }
        func recordOf(_ rule: String, _ row: [String: Any]) throws -> [String: Any] {
            try mapping(rule, try admission(rule, row)["declaration"], "the declaration record", v4RecordKeys)
        }
        var firstRecord: [String: Data] = [:]
        for row in importRows {
            let record = try recordOf("D1", row), symbol = try admission("D1", row)["symbol"] as? String
            guard record["syntax_model"] as? String == v4GrammarModel else { throw v4Fail("D1", "declaration syntax_model is not \(v4GrammarModel)") }
            guard let decision = record["decision"] as? String, v4Decisions.contains(decision) else {
                throw v4Fail("D1", "declaration decision is not one of the four")
            }
            let reason = record["reason"]
            if decision == "undecided" {
                guard let text = reason as? String, v4Reasons.contains(text) else { throw v4Fail("D1", "an undecided declaration needs a grammar reason") }
            } else if !(reason is NSNull) { throw v4Fail("D1", "a decided declaration has a null reason") }
            let identityKeys = ["entity", "throws", "is_async", "typed_throws", "identity_sha256"]
            if record["entity"] is NSNull {
                guard identityKeys.allSatisfy({ record[$0] is NSNull }) else {
                    throw v4Fail("D1", "a declared-without-identity record has null entity, throws, is_async, typed_throws and digest")
                }
                // The grammar declines a static accessor with no identity (contract 10, call 7); typed_throws needs an identity.
                guard decision == "undecided", reason as? String != "typed_throws" else {
                    throw v4Fail("D1", "a declaration without an identity is undecided with a decline reason")
                }
            } else {
                guard let entity = record["entity"] as? String, !entity.isEmpty else { throw v4Fail("D1", "declaration entity must be a non-empty string") }
                let throwsFlag = try flag("D1", record["throws"], "declaration throws"), asyncFlag = try flag("D1", record["is_async"], "declaration is_async")
                guard let typed = record["typed_throws"] as? String, ["none", "never", "concrete"].contains(typed) else {
                    throw v4Fail("D1", "declaration typed_throws must be none, never or concrete")
                }
                guard let digest = record["identity_sha256"] as? String, digest.utf8.count == 64,
                      digest.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }) else {
                    throw v4Fail("D1", "declaration identity_sha256 must be 64 lowercase hex characters")
                }
                let expected: (String, String?)
                if reason as? String == "accessor" || v4AccessorEntities.contains(entity) { expected = ("undecided", "accessor") }
                else if typed == "never" { expected = ("undecided", "typed_throws") }
                else if throwsFlag || typed != "none" { expected = ("throwing", nil) }
                else if asyncFlag { expected = ("async", nil) }
                else { expected = ("non_throwing", nil) }
                guard expected.0 == decision, expected.1 == (reason as? String) else {
                    throw v4Fail("D1", "declaration decision \(decision) does not follow from its fields")
                }
            }
            guard let symbol, let canonical = v4Canonical(record) else { throw v4Fail("D1", "an import row needs a string admission.symbol") }
            if let previous = firstRecord[symbol], previous != canonical { throw v4Fail("D1", "rows of \(symbol) carry different declaration records") }
            firstRecord[symbol] = canonical
        }
        func licenceOf(_ rule: String, _ row: [String: Any]) throws -> (claimed: String, relation: String, expected: String) {
            let effect = try mapping(rule, row["effect_admission"], "effect_admission", ["model", "licence_class", "caller_relation"])
            guard effect["model"] as? String == v4EffectModel else { throw v4Fail(rule, "effect_admission.model is not \(v4EffectModel)") }
            let record = try recordOf(rule, row)
            let expected = v4LicenceClass(decision: record["decision"] as? String ?? "", isAsync: record["is_async"] as? Bool,
                                          typedThrows: record["typed_throws"] as? String)
            return (effect["licence_class"] as? String ?? "", effect["caller_relation"] as? String ?? "", expected)
        }
        for row in importRows {
            let licence = try licenceOf("D2", row)
            guard v4Licences.contains(licence.claimed), licence.claimed == licence.expected else {
                throw v4Fail("D2", "licence_class \(licence.claimed), the record produces \(licence.expected)")
            }
        }
        for row in importRows {
            let licence = try licenceOf("D3", row), admitted = try admission("D3", row)
            guard v4Relations.contains(licence.relation) else { throw v4Fail("D3", "unknown caller_relation") }
            guard let shape = (row["caller_error_test"] as? [String: Any])?["shape"] as? String, v4Shapes.contains(shape) else {
                throw v4Fail("D3", "an import row needs a caller error test with a known shape")
            }
            guard let callKind = admitted["call_kind"] as? String, ["bl", "b", "blr_got"].contains(callKind) else {
                throw v4Fail("D3", "an import row needs a call kind of bl, b or blr_got")
            }
            guard let relation = v4ExpectedRelation(licence: licence.expected, shape: shape, tail: callKind == "b") else {
                throw v4Fail("D3", "a retained row with licence no_error_exit needs a bl-kind call and shape swifterror_idiom")
            }
            guard licence.relation == relation else {
                throw v4Fail("D3", "relation \(licence.relation), contract 4.4 gives \(relation) for licence \(licence.expected), shape \(shape), call kind \(callKind)")
            }
            guard admitted["status"] as? String == "unresolved" else { throw v4Fail("D3", "a retained import row stays unresolved") }
            guard admitted["reason"] as? String == v4RowReasons[licence.expected] else {
                throw v4Fail("D3", "row reason does not match licence \(licence.expected)")
            }
        }
        for row in importRows {
            guard row["candidate"] is NSNull, row["validation"] is NSNull else { throw v4Fail("D4", "an import row carries a candidate or a validation") }
            guard row["abi"] == nil, try admission("D4", row)["abi"] == nil else { throw v4Fail("D4", "an import row carries an abi") }
        }
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
