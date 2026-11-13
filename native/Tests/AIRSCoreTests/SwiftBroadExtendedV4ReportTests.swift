import Foundation
import XCTest
@testable import AIRSCore

// MARK: - Hand-built v4 reports

/// Builds `broad-extended-v4` reports from the design contract alone. Nothing here reads engine output: every counter is
/// derived from a short list of calls by the rules of the contract (accounting 4.7 and 4.8, record 5.3, licence 4.3, relation
/// 4.4, row treatment 4.5), so the native decoder is tested against an independent reading of the contract.
enum V4Fixture {
    static let model = "swift-broad-error-flow-extended-v4"
    static let profile = "broad-extended-v4"
    static let effectModel = "swift-import-effect-admission-v1"
    static let syntaxModel = "swift-declaration-syntax-v2"
    static let digest = String(repeating: "a", count: 64)
    static let witnessSymbol = "_$sSS10FoundationE8EncodingVMa"
    static let groups = ["capabilities", "limits", "omission_causes", "omitted_by_kind", "unselected_call_counts",
                         "scan", "import_calls", "decision_by_shape", "decision_summary"]
    static let decisions = ["non_throwing", "throwing", "async", "undecided"]
    static let shapes = ["swifterror_idiom", "postcall_test_only", "precall_zero_only", "none"]
    static let licences = ["no_error_exit", "declared_error_exit", "refused_unsupported_effect", "none"]
    static let rowReasons: [String: String] = [
        "no_error_exit": "declaration_caller_disagreement",
        "declared_error_exit": "imported_callee_outcome_unmodeled",
        "refused_unsupported_effect": "imported_callee_effect_unsupported",
        "none": "imported_callee_abi_unqualified"]
    static let limitations = ["structural_only", "no_source_or_handler_semantics",
        "unsupported_abi_and_dispatch_remain_unresolved", "recorded_checks_are_historical_when_saved",
        "caller_error_test_does_not_claim_callee_behaviour", "indirect_target_shape_does_not_claim_callee_behaviour",
        "value_witness_admission_by_abi_with_recorded_provenance", "imported_callees_attribution_only",
        "got_callees_attribution_only", "got_window_entry_screen_syntactic"]

    static func hex(_ value: Int) -> String { "0x" + String(value, radix: 16) }

    // MARK: Compact declaration record (contract 5.3)

    struct Record {
        var decision: String
        var reason: Any = NSNull()
        var entity: Any = NSNull()
        var throwsFlag: Any = NSNull()
        var isAsync: Any = NSNull()
        var typedThrows: Any = NSNull()
        var digest: Any = NSNull()
        var syntax: String = V4Fixture.syntaxModel

        var json: [String: Any] {
            var value: [String: Any] = [:]
            value["syntax_model"] = syntax
            value["decision"] = decision
            value["reason"] = reason
            value["entity"] = entity
            value["throws"] = throwsFlag
            value["is_async"] = isAsync
            value["typed_throws"] = typedThrows
            value["identity_sha256"] = digest
            return value
        }

        /// Contract 4.3, restated here and never taken from the decoder.
        var licence: String {
            switch decision {
            case "non_throwing": return "no_error_exit"
            case "throwing":
                let asyncEffect = (isAsync as? Bool) == true
                let typedEffect = ((typedThrows as? String) ?? "none") != "none"
                return asyncEffect || typedEffect ? "refused_unsupported_effect" : "declared_error_exit"
            case "async": return "refused_unsupported_effect"
            default: return "none"
            }
        }

        static func identified(_ decision: String, throwing: Bool = false, isAsync: Bool = false, typed: String = "none",
                               entity: String = "Function", reason: Any = NSNull()) -> Record {
            Record(decision: decision, reason: reason, entity: entity, throwsFlag: throwing, isAsync: isAsync,
                   typedThrows: typed, digest: V4Fixture.digest)
        }

        static func declined(_ reason: Any, decision: String = "undecided") -> Record {
            Record(decision: decision, reason: reason)
        }

        static var nonThrowing: Record { identified("non_throwing") }
        static var throwing: Record { identified("throwing", throwing: true) }
        static var throwingAsync: Record { identified("throwing", throwing: true, isAsync: true) }
        static var throwingConcrete: Record { identified("throwing", throwing: true, typed: "concrete") }
        static var asyncOnly: Record { identified("async", isAsync: true) }
        static var thunk: Record { declined("thunk_or_specialization") }
        static var accessorNoIdentity: Record { declined("accessor") }
        static var accessorWithIdentity: Record { identified("undecided", entity: "Getter", reason: "accessor") }
        static var typedNever: Record { identified("undecided", throwing: true, typed: "never", reason: "typed_throws") }
    }

    /// Contract 4.4. `nil` means that the rules skip the call, so a retained row of that case may not exist.
    static func relation(licence: String, shape: String, kind: String) -> String? {
        let tail = kind == "b"
        switch licence {
        case "no_error_exit": return shape == "swifterror_idiom" && !tail ? "conflict" : nil
        case "declared_error_exit": return tail ? "not_applicable" : (shape == "swifterror_idiom" ? "corroborated" : "no_signal")
        default: return "not_applicable"
        }
    }

    // MARK: Calls

    struct Event {
        var symbol: String
        var record: Record?
        var via = "stub"
        var outcome = "retained"
        var shape = "none"
        var kind = "bl"
        var cause = "output_budget"
        var claimedLicence: String?
        var tableDecision: String?
        var tableReason: Any?

        static func retained(_ symbol: String, _ record: Record, shape: String = "none", kind: String = "bl",
                             claimed: String? = nil, tableDecision: String? = nil, tableReason: Any? = nil) -> Event {
            Event(symbol: symbol, record: record, shape: shape, kind: kind, claimedLicence: claimed,
                  tableDecision: tableDecision, tableReason: tableReason)
        }
        /// A retained call through a GOT slot: call kind blr_got, model swift-broad-got-callsite-v1.
        static func retainedGot(_ symbol: String, _ record: Record, shape: String = "none", claimed: String? = nil,
                                tableDecision: String? = nil, tableReason: Any? = nil) -> Event {
            Event(symbol: symbol, record: record, via: "got", shape: shape, kind: "blr_got", claimedLicence: claimed,
                  tableDecision: tableDecision, tableReason: tableReason)
        }
        static func skipped(_ symbol: String, _ record: Record = .nonThrowing, shape: String = "none", via: String = "stub") -> Event {
            Event(symbol: symbol, record: record, via: via, outcome: "skipped", shape: shape)
        }
        static func omitted(_ symbol: String, _ record: Record, via: String = "stub", shape: String = "none",
                            cause: String = "output_budget") -> Event {
            Event(symbol: symbol, record: record, via: via, outcome: "omitted", shape: shape, cause: cause)
        }
        static func notSwift(_ symbol: String, via: String = "stub") -> Event {
            Event(symbol: symbol, record: nil, via: via, outcome: "not_swift")
        }
    }

    // MARK: Caller error test fact (swift-caller-error-test-v1, unchanged by v4)

    static func callerTest(shape: String, call: Int) -> [String: Any] {
        let before = shape == "swifterror_idiom" || shape == "precall_zero_only"
        let after = shape == "swifterror_idiom" || shape == "postcall_test_only"
        var pre: [String: Any] = [:]
        if before {
            let first: [String: Any] = ["pc": hex(call - 8), "word": "0xaa1f03f5", "kind": "mov"]
            let second: [String: Any] = ["pc": hex(call - 4), "word": "0xd2800000", "kind": "mov"]
            pre["status"] = "x21_zeroed"; pre["zero_pc"] = hex(call - 8); pre["window"] = [first, second]
        } else {
            pre["status"] = "x21_not_zeroed"; pre["window"] = [Any]()
        }
        var post: [String: Any] = [:]
        if after {
            let test = call + 4
            let word: [String: Any] = ["pc": hex(test), "word": "0xb4000015", "kind": "xcbz"]
            post["status"] = "recovered_candidate"; post["test_pc"] = hex(test); post["tested_register"] = "x21"
            post["success_pc"] = hex(test + 0x20); post["error_pc"] = hex(test + 4); post["window"] = [word]
        } else {
            post["reason"] = "postcall_window_exhausted"; post["window"] = [Any]()
        }
        var fact: [String: Any] = [:]
        fact["model"] = "swift-caller-error-test-v1"; fact["shape"] = shape
        fact["precall"] = pre; fact["postcall"] = post; fact["claims_callee_behaviour"] = false
        return fact
    }

    // MARK: Rows

    /// An import row. The stub arithmetic is the recorded ADRP, LDR, BR pattern: stub k sits at 0x100001008 + 12k and its
    /// pointer at 0x100004000 + 8k.
    static func importRow(index i: Int, symbol: String, declaration: [String: Any], shape: String, kind: String,
                          licence: String, relation: String, reason: String) -> [String: Any] {
        let caller = 0x100100000 + 0x1000 * i
        let call = caller + 0x40
        let stub = 0x100001008 + 12 * i
        let words = ["0xf0000010", "0x" + String(0xf9400210 + (i << 10), radix: 16), "0xd61f0200"]
        var recorded: [[String: Any]] = []
        for k in 0..<3 {
            var word: [String: Any] = [:]
            word["pc"] = stub + k * 4
            word["word"] = words[k]
            word["slice_file_offset"] = 0x1008 + i * 12 + k * 4
            word["container_file_offset"] = 0x2008 + i * 12 + k * 4
            recorded.append(word)
        }
        var provenance: [String: Any] = [:]
        provenance["stub_words"] = recorded
        provenance["stub_indirect_entry_offset"] = 0x8038 + i * 4
        provenance["pointer_indirect_entry_offset"] = 0x8040 + i * 4
        provenance["nlist_offset"] = 0x8018 + i * 16
        provenance["stub_model"] = "arm64-import-stub-double-binding-v1"
        provenance["stub_section"] = "__TEXT,__stubs"
        provenance["stub_index"] = i
        provenance["symbol_index"] = i + 1
        provenance["pointer_address"] = 0x100004000 + i * 8
        provenance["pointer_section"] = "__DATA_CONST,__got"
        var admission: [String: Any] = [:]
        admission["model_version"] = "swift-broad-import-callsite-v1"
        admission["status"] = "unresolved"
        admission["reason"] = reason
        admission["call_kind"] = kind
        admission["call_pc"] = call
        admission["caller_start"] = caller
        admission["callee_stub_pc"] = stub
        admission["symbol"] = symbol
        admission["library_ordinal"] = 2
        admission["declaration"] = declaration
        admission["import_provenance"] = provenance
        admission["details_complete"] = true
        admission["call_return_proven"] = false
        admission["syntactic_call_target_admitted"] = false
        admission["import_attribution_admitted"] = true
        admission["work_steps"] = 16 + symbol.utf8.count
        var effect: [String: Any] = [:]
        effect["model"] = effectModel; effect["licence_class"] = licence; effect["caller_relation"] = relation
        var row: [String: Any] = [:]
        row["caller_pc"] = hex(caller)
        row["call_pc"] = hex(call)
        row["admission"] = admission
        row["candidate"] = NSNull()
        row["validation"] = NSNull()
        row["effect_admission"] = effect
        row["caller_error_test"] = callerTest(shape: shape, call: call)
        return row
    }

    /// A retained call through a GOT slot, as the engine builds it (got_callsite_admission): the GOT callsite model, call kind
    /// blr_got, the same compact record and the same effect admission as a stub row, a caller fact, and no abi.
    static func gotRow(index i: Int, symbol: String, declaration: [String: Any], shape: String,
                       licence: String, relation: String, reason: String) -> [String: Any] {
        let caller = 0x100100000 + 0x1000 * i
        let call = caller + 0x40
        let slot = 0x100004800 + 8 * i
        var window: [[String: Any]] = []
        let words = ["0xf0000008", "0xf9400108", "0xd63f0100"]
        for k in 0..<3 { window.append(["pc": call - 8 + 4 * k, "word": words[k]]) }
        var binding: [String: Any] = [:]
        binding["slot_index"] = i; binding["symbol_index"] = i + 1; binding["bind_ordinal"] = i
        var provenance: [String: Any] = [:]
        provenance["got_model"] = "arm64-got-blr-two-source-binding-v1"
        provenance["window_words"] = window
        provenance["binding"] = binding
        var admission: [String: Any] = [:]
        admission["model_version"] = "swift-broad-got-callsite-v1"
        admission["status"] = "unresolved"
        admission["reason"] = reason
        admission["call_kind"] = "blr_got"
        admission["call_pc"] = call
        admission["caller_start"] = caller
        admission["register"] = "x8"
        admission["adrp_pc"] = call - 8
        admission["ldr_pc"] = call - 4
        admission["slot_address"] = slot
        admission["slot_section"] = "__DATA_CONST,__got"
        admission["symbol"] = symbol
        admission["library_ordinal"] = 2
        admission["library_path"] = "/usr/lib/swift/libswiftCore.dylib"
        admission["weak_import"] = false
        admission["import_ordinal"] = i
        admission["declaration"] = declaration
        admission["got_provenance"] = provenance
        admission["details_complete"] = true
        admission["call_return_proven"] = false
        admission["syntactic_call_target_admitted"] = false
        admission["import_attribution_admitted"] = true
        admission["work_steps"] = 16 + symbol.utf8.count + 3
        var effect: [String: Any] = [:]
        effect["model"] = effectModel; effect["licence_class"] = licence; effect["caller_relation"] = relation
        var row: [String: Any] = [:]
        row["caller_pc"] = hex(caller)
        row["call_pc"] = hex(call)
        row["admission"] = admission
        row["candidate"] = NSNull()
        row["validation"] = NSNull()
        row["effect_admission"] = effect
        row["caller_error_test"] = callerTest(shape: shape, call: call)
        return row
    }

    /// A row that is not an import row: no effect admission, no declaration, no caller fact.
    static func plainRow(_ j: Int, perCaller: Int) -> [String: Any] {
        let caller = 0x100200000 + 0x1000 * (j / perCaller)
        var admission: [String: Any] = [:]
        admission["status"] = "unresolved"; admission["reason"] = "unqualified"
        var row: [String: Any] = [:]
        row["caller_pc"] = hex(caller)
        row["call_pc"] = hex(caller + 4 + 4 * (j % perCaller))
        row["admission"] = admission
        row["candidate"] = NSNull()
        row["validation"] = NSNull()
        return row
    }

    /// A v3 indirect row whose value-witness admission names `witnessSymbol` (contract 4.6, rule C7).
    static func witnessRow() -> [String: Any] {
        var shape: [String: Any] = [:]
        shape["model"] = "swift-indirect-target-shape-v1"; shape["site_pc"] = "0x100c"; shape["site_kind"] = "blr"
        shape["class"] = "value_witness"; shape["slot_offset"] = 8; shape["unknown_reason"] = NSNull()
        let deciding: [[String: Any]] = [
            ["pc": "0x1000", "word": "0x94000005", "role": "metadata_call_result"],
            ["pc": "0x1004", "word": "0xf85f8008", "role": "table_load"],
            ["pc": "0x1008", "word": "0xf9400508", "role": "target_load"],
            ["pc": "0x100c", "word": "0xd63f0100", "role": "indirect_branch"]]
        shape["deciding_instructions"] = deciding
        shape["evidence"] = "table base loaded from [x0, #-8]"; shape["class_before_join_refusal"] = NSNull()
        shape["slot_address"] = NSNull(); shape["slot_section"] = NSNull(); shape["claims_callee_behaviour"] = false
        let bounds: [String: Any] = ["window_words": 256, "max_register_hops": 6, "max_function_words": 262144]
        shape["bounds"] = bounds
        var witness: [String: Any] = [:]
        witness["model"] = "swift-value-witness-admission-v1"; witness["admitted"] = true
        witness["provenance_kind"] = "imported_metadata_accessor_call"; witness["first_failing_condition"] = NSNull()
        witness["reason"] = "meets_tier2_conditions"; witness["site_pc"] = "0x100c"; witness["site_kind"] = "blr"
        witness["slot_offset"] = 8; witness["metadata_register"] = "x0"; witness["symbol"] = witnessSymbol
        witness["metadata_callee_pc"] = "0x1014"; witness["claims_callee_behaviour"] = false
        witness["abi_basis"] = "value_witness_function_slots_cannot_throw"
        var admission: [String: Any] = [:]
        admission["model_version"] = "swift-broad-callsite-v1"; admission["status"] = "declined"
        admission["reason"] = "value_witness_abi_nonthrowing"; admission["call_pc"] = 4108; admission["details_complete"] = true
        var row: [String: Any] = [:]
        row["caller_pc"] = "0x1000"; row["call_pc"] = "0x100c"; row["admission"] = admission
        row["candidate"] = NSNull(); row["validation"] = NSNull()
        row["indirect_target_shape"] = shape; row["value_witness_admission"] = witness
        return row
    }

    // MARK: Report

    private struct Counter {
        var decision = "", reason: Any = NSNull()
        var calls = 0, stub = 0, got = 0, retained = 0, skipped = 0, notSwift = 0, omitted = 0

        mutating func add(via: String, outcome: String) {
            calls += 1
            if via == "stub" { stub += 1 } else { got += 1 }
            switch outcome {
            case "retained": retained += 1
            case "skipped": skipped += 1
            case "not_swift": notSwift += 1
            default: omitted += 1
            }
        }
    }

    private static func zeroed(_ keys: [String]) -> [String: Any] {
        var value: [String: Any] = [:]
        for key in keys { value[key] = 0 }
        return value
    }

    /// Derives a complete, internally consistent v4 report from `events` plus counts of calls that leave no import entry.
    static func report(_ events: [Event], plain: Int = 0, plainPerCaller: Int = 200, witnessRow withWitness: Bool = false,
                       indirectOmitted: Int = 0, directNotSwift: Int = 0, directUnattributed: Int = 0,
                       maxEntries: Int = 4096, truncatedWords: Int = 0, totalCeilingWords: Int = 0,
                       excludedWords: Int = 0, excludedFunctions: Int = 0) -> [String: Any] {
        var importRows: [[String: Any]] = []
        var table: [String: Counter] = [:]
        var known: [String: (decision: String, reason: Any)] = [:]
        var totalCalls: [String: Int] = [:]
        var residual = Counter()
        var overflowed = Set<String>()
        var grid: [String: [String: Int]] = [:]
        var callerShapes: [String: Int] = [:], callerDeclines: [String: Int] = [:]
        var causes: [String: Int] = ["analysis_work_budget": 0, "per_function_limit": 0, "total_row_limit": 0, "output_budget": 0]
        var kinds: [String: Int] = ["import_stub": 0, "import_got": 0, "local_swift_direct": 0, "indirect": 0]
        var skipped = 0, notSwift = 0, stubSkipped = 0, stubNotSwift = 0, gotSkipped = 0, gotNotSwift = 0
        var omittedStub = 0, omittedGot = 0, stubSymbols = Set<String>(), gotCalls = 0, retainedStub = 0, retainedGot = 0
        for event in events {
            var decision = "not_swift"
            var reason: Any = NSNull()
            if let record = event.record {
                decision = event.tableDecision ?? record.decision
                reason = event.tableReason ?? (decision == "undecided" ? record.reason : NSNull())
            }
            let outcome = event.record == nil ? "not_swift" : event.outcome
            if known[event.symbol] == nil {
                known[event.symbol] = (decision, reason)
                if table.count < maxEntries { table[event.symbol] = Counter(decision: decision, reason: reason) }
                else { overflowed.insert(event.symbol) }
            }
            totalCalls[event.symbol, default: 0] += 1
            if event.record != nil { grid[decision, default: [:]][event.shape, default: 0] += 1 }
            if table[event.symbol] != nil { table[event.symbol]!.add(via: event.via, outcome: outcome) }
            else { residual.add(via: event.via, outcome: outcome) }
            if event.via == "stub" { stubSymbols.insert(event.symbol) } else { gotCalls += 1 }
            switch outcome {
            case "retained":
                let record = event.record!
                let licence = event.claimedLicence ?? record.licence
                let related = relation(licence: licence, shape: event.shape, kind: event.kind) ?? "no_signal"
                if event.via == "stub" {
                    importRows.append(importRow(index: importRows.count, symbol: event.symbol, declaration: record.json,
                                                shape: event.shape, kind: event.kind, licence: licence, relation: related,
                                                reason: rowReasons[licence]!))
                    retainedStub += 1
                } else {
                    importRows.append(gotRow(index: importRows.count, symbol: event.symbol, declaration: record.json,
                                             shape: event.shape, licence: licence, relation: related,
                                             reason: rowReasons[licence]!))
                    retainedGot += 1
                }
                callerShapes[event.shape, default: 0] += 1
                if event.shape == "precall_zero_only" || event.shape == "none" { callerDeclines["postcall_window_exhausted", default: 0] += 1 }
            case "skipped":
                skipped += 1
                if event.via == "stub" { stubSkipped += 1 } else { gotSkipped += 1 }
            case "not_swift":
                notSwift += 1
                if event.via == "stub" { stubNotSwift += 1 } else { gotNotSwift += 1 }
            default:
                causes[event.cause, default: 0] += 1
                if event.via == "stub" { kinds["import_stub"]! += 1; omittedStub += 1 }
                else { kinds["import_got"]! += 1; omittedGot += 1 }
            }
        }
        causes["output_budget"]! += indirectOmitted
        kinds["indirect"]! += indirectOmitted
        let omitted = omittedStub + omittedGot + indirectOmitted

        var rows: [[String: Any]] = []
        if withWitness { rows.append(witnessRow()) }
        rows.append(contentsOf: importRows)
        for j in 0..<plain { rows.append(plainRow(j, perCaller: plainPerCaller)) }
        var statusCounts: [String: Int] = [:], reasonCounts: [String: Int] = [:]
        for row in rows {
            let admission = row["admission"] as! [String: Any]
            statusCounts[admission["status"] as! String, default: 0] += 1
            reasonCounts[admission["reason"] as! String, default: 0] += 1
        }
        let selected = rows.count + omitted
        let observed = selected + skipped + notSwift + directNotSwift + directUnattributed

        var entries: [[String: Any]] = []
        for symbol in table.keys.sorted() {
            let counter = table[symbol]!
            var entry: [String: Any] = [:]
            entry["symbol"] = symbol; entry["decision"] = counter.decision; entry["reason"] = counter.reason
            entry["calls"] = counter.calls; entry["stub_calls"] = counter.stub; entry["got_calls"] = counter.got
            entry["retained"] = counter.retained; entry["skipped_non_throwing"] = counter.skipped
            entry["not_swift_calls"] = counter.notSwift; entry["omitted"] = counter.omitted
            entries.append(entry)
        }
        var residualJSON: [String: Any] = [:]
        residualJSON["symbols"] = overflowed.count; residualJSON["calls"] = residual.calls
        residualJSON["retained"] = residual.retained; residualJSON["skipped_non_throwing"] = residual.skipped
        residualJSON["not_swift_calls"] = residual.notSwift; residualJSON["omitted"] = residual.omitted
        let attributed = totalCalls.values.reduce(0, +)
        let ceilingWords = truncatedWords + totalCeilingWords
        let scanComplete = ceilingWords == 0 && excludedFunctions == 0
        let undecodedWords = ceilingWords + excludedWords
        var importCalls: [String: Any] = [:]
        importCalls["complete"] = overflowed.isEmpty && scanComplete
        importCalls["attributed_calls"] = attributed
        importCalls["attributed_swift_calls"] = attributed - notSwift
        importCalls["distinct_symbols"] = known.count
        importCalls["entries"] = entries
        importCalls["residual"] = residualJSON

        var gridJSON: [String: Any] = [:]
        for decision in decisions {
            var line: [String: Any] = [:]
            for shape in shapes { line[shape] = grid[decision]?[shape] ?? 0 }
            gridJSON[decision] = line
        }
        var names = zeroed(decisions)
        var byReason: [String: [String: Any]] = [:]
        for (symbol, entry) in known where entry.decision != "not_swift" {
            names[entry.decision] = ((names[entry.decision] as? Int) ?? 0) + 1
            if entry.decision == "undecided" {
                let key = (entry.reason as? String) ?? "missing"
                var slot = byReason[key] ?? ["names": 0, "calls": 0]
                slot["names"] = (slot["names"] as! Int) + 1
                slot["calls"] = (slot["calls"] as! Int) + totalCalls[symbol]!
                byReason[key] = slot
            }
        }
        var summary: [String: Any] = [:]
        summary["names"] = names; summary["undecided_by_reason"] = byReason

        var unselected: [String: Any] = [:]
        unselected["skipped_non_throwing"] = skipped; unselected["non_swift_import"] = notSwift
        unselected["declined_stub"] = 0; unselected["direct_target_not_swift_function"] = directNotSwift
        unselected["direct_target_unattributed"] = directUnattributed; unselected["other"] = 0

        let scanned = 640
        var scan: [String: Any] = [:]
        scan["words_total"] = scanned + undecodedWords; scan["words_scanned"] = scanned
        scan["words_unscanned_per_function_ceiling"] = truncatedWords; scan["words_unscanned_total_ceiling"] = totalCeilingWords
        scan["words_excluded_boundary"] = excludedWords; scan["functions_total"] = 40
        scan["functions_excluded_boundary"] = excludedFunctions
        scan["functions_truncated"] = ceilingWords == 0 ? 0 : 1
        scan["candidates_in_unscanned_words"] = undecodedWords == 0 ? 0 : NSNull()
        scan["candidates_in_unscanned_words_reason"] = undecodedWords == 0 ? NSNull() : "words_not_decoded"

        var capabilities: [String: Any] = [:]
        capabilities["report_model"] = model; capabilities["effect_admission_model"] = effectModel
        capabilities["declaration_syntax_model"] = syntaxModel; capabilities["grammar_pin"] = "swift-6.4.2-RELEASE"
        capabilities["caller_error_test_model"] = "swift-caller-error-test-v1"
        capabilities["premises"] = ["symbol_name_carries_effects", "no_silgen_name_override", "name_only_attribution",
                                    "binding_not_proven", "grammar_pinned"]
        capabilities["not_claimed"] = ["callee_returns", "dyld_binding", "runtime_callee", "arguments_and_results",
                                       "error_value_at_runtime"]
        var limits: [String: Any] = [:]
        limits["max_total_evidence"] = 8192; limits["max_observations_per_function"] = 256
        limits["max_instructions_per_function"] = 262144; limits["max_total_instructions"] = 2097152
        limits["analysis_work_ceiling"] = 536870912; limits["output_budget_bytes"] = 14614528
        limits["import_table_entries"] = 4096; limits["import_table_byte_reserve"] = 2097152

        var identity: [String: Any] = [:]
        identity["container_sha256"] = String(repeating: "a", count: 64); identity["slice_sha256"] = String(repeating: "b", count: 64)
        identity["architecture"] = "arm64"; identity["cpu_subtype"] = 0; identity["uuid"] = NSNull()
        identity["preferred_base"] = "0x100000000"; identity["slice_index"] = 0; identity["container_slice_count"] = 1
        identity["slice_offset"] = "0x1000"; identity["slice_size"] = "0x10000"

        var stubCounts: [String: Any] = [:]
        stubCounts["attributed_stubs"] = stubSymbols.count; stubCounts["declined_stubs"] = 0; stubCounts["invalid_stub_sections"] = 0
        stubCounts["selected_import_calls"] = retainedStub + omittedStub
        stubCounts["non_throwing_swift_import_calls"] = stubSkipped; stubCounts["non_swift_import_calls"] = stubNotSwift
        stubCounts["declined_stub_calls"] = 0
        var gotCounts: [String: Any] = [:]
        gotCounts["attributed_got_calls"] = gotCalls; gotCounts["agreeing_got_slots"] = max(35, gotCalls); gotCounts["blr_instructions"] = gotCalls
        gotCounts["declined_got_calls"] = 0; gotCounts["declined_got_slots"] = 0; gotCounts["got_candidates"] = gotCalls
        gotCounts["got_slots"] = max(35, gotCalls); gotCounts["non_swift_got_calls"] = gotNotSwift
        gotCounts["non_throwing_swift_got_calls"] = gotSkipped; gotCounts["selected_got_calls"] = retainedGot + omittedGot

        var report: [String: Any] = [:]
        report["model_version"] = model; report["profile"] = profile
        report["witness_model_version"] = "swift-outcome-witness-v2"; report["validation_model_version"] = "swift-outcome-validation-v2"
        report["identity"] = identity
        report["word_scan_complete"] = scanComplete
        report["call_details_complete"] = omitted == 0; report["outcome_witnesses_complete"] = omitted == 0
        report["observed_call_instructions"] = observed; report["selected_call_candidates"] = selected
        report["omitted_calls"] = omitted; report["scanned_words"] = scanned; report["analysis_work"] = 1000
        report["research_only"] = true; report["call_return_proven"] = false; report["runtime_reachability_proven"] = false
        report["status_counts"] = statusCounts; report["reason_counts"] = reasonCounts
        report["calls"] = rows; report["limitations"] = limitations
        report["import_stub_model"] = "arm64-import-stub-double-binding-v1"; report["import_stubs_complete"] = true
        report["import_stub_reason"] = NSNull(); report["import_stub_counts"] = stubCounts
        report["caller_error_test_counts"] = callerShapes; report["caller_error_test_decline_counts"] = callerDeclines
        report["indirect_target_shape_model"] = "swift-indirect-target-shape-v1"
        report["value_witness_admission_model"] = "swift-value-witness-admission-v1"
        report["indirect_target_shape_counts"] = withWitness ? ["value_witness": 1] : [String: Int]()
        report["value_witness_admission_counts"] = ["admitted": withWitness ? 1 : 0, "refused": 0]
        report["value_witness_refusal_condition_counts"] = [String: Int]()
        report["got_binding_model"] = "arm64-got-blr-two-source-binding-v1"; report["got_binding_reason"] = NSNull()
        report["got_bindings_complete"] = true; report["got_counts"] = gotCounts
        report["got_decline_counts"] = [String: Int](); report["got_slot_decline_counts"] = [String: Int]()
        report["got_window_model"] = "adrp-ldr-blr-straight-line-window-v1"
        report["chained_fixups_model"] = "macho-chained-fixups-64-bind-v1"; report["chained_fixups_status"] = "decoded"
        report["capabilities"] = capabilities; report["limits"] = limits; report["omission_causes"] = causes
        report["omitted_by_kind"] = kinds; report["unselected_call_counts"] = unselected; report["scan"] = scan
        report["import_calls"] = importCalls; report["decision_by_shape"] = gridJSON; report["decision_summary"] = summary
        return report
    }

    /// The valid report with no rows and no table entries.
    static func makeValidV4Report() -> [String: Any] { report([]) }

    /// Two rows and two entries with a zero residual.
    static func twoRowReport() -> [String: Any] {
        report([.retained("_$sAlpha", .throwing), .retained("_$sBeta", .thunk, shape: "postcall_test_only")])
    }

    /// A report that exercises every counter: all four decisions, every outcome, both call routes, one omission of each kind
    /// that the accounting names, the metadata-accessor admission and the non-Swift import. The arithmetic is by hand:
    /// 7 import rows plus the witness row, 8 selected omissions-free rows, 3 omitted calls, 9 attributed Swift names.
    static func richEvents() -> [Event] {
        [.retained("_$sA", .throwing, shape: "none", kind: "bl"),
         .retained("_$sA", .throwing, shape: "none", kind: "b"),
         .retained("_$sB", .thunk, shape: "postcall_test_only"),
         .skipped("_$sC"), .skipped("_$sC"), .skipped("_$sC"),
         .retained("_$sD", .asyncOnly),
         .retained("_$sE", .throwing, shape: "swifterror_idiom", kind: "bl"),
         .retained("_$sF", .nonThrowing, shape: "swifterror_idiom", kind: "bl"),
         .skipped("_$sF", .nonThrowing, shape: "none"),
         .retained("_$sH", .throwingConcrete, shape: "precall_zero_only"),
         .skipped(witnessSymbol, .nonThrowing),
         .omitted("_$sG", .accessorNoIdentity, via: "got", cause: "analysis_work_budget"),
         .omitted("_$sG", .accessorNoIdentity, via: "got", cause: "analysis_work_budget"),
         .notSwift("_swift_retain"), .notSwift("_swift_retain"), .notSwift("_swift_retain"), .notSwift("_swift_retain")]
    }

    static func rich(maxEntries: Int = 4096, truncatedWords: Int = 0, totalCeilingWords: Int = 0, excludedWords: Int = 0,
                     excludedFunctions: Int = 0) -> [String: Any] {
        report(richEvents(), plain: 2, witnessRow: true, indirectOmitted: 1, directNotSwift: 2, directUnattributed: 1,
               maxEntries: maxEntries, truncatedWords: truncatedWords, totalCeilingWords: totalCeilingWords,
               excludedWords: excludedWords, excludedFunctions: excludedFunctions)
    }

    /// One retained import row through a GOT slot.
    static func singleGot(_ record: Record, shape: String = "swifterror_idiom", claimed: String? = nil) -> [String: Any] {
        report([.retainedGot("_$sOne", record, shape: shape, claimed: claimed)])
    }

    /// One retained import row.
    static func single(_ record: Record, shape: String = "swifterror_idiom", kind: String = "bl", claimed: String? = nil,
                       tableDecision: String? = nil, tableReason: Any? = nil) -> [String: Any] {
        report([.retained("_$sOne", record, shape: shape, kind: kind, claimed: claimed, tableDecision: tableDecision,
                          tableReason: tableReason)])
    }

    // MARK: Path helpers (dotted paths; array indices are numbers)

    static func get(_ node: Any?, _ path: String) -> Any? {
        var current = node
        for key in path.components(separatedBy: ".") {
            if let array = current as? [Any], let index = Int(key), index < array.count { current = array[index] }
            else if let object = current as? [String: Any] { current = object[key] }
            else { return nil }
        }
        return current
    }

    private static func replacing(_ node: Any, _ path: ArraySlice<String>, _ replacement: Any?) -> Any {
        guard let key = path.first else { return replacement ?? NSNull() }
        if var array = node as? [Any], let index = Int(key) {
            if path.count == 1, let replacement { array[index] = replacement }
            else if path.count == 1 { array.remove(at: index) }
            else { array[index] = replacing(array[index], path.dropFirst(), replacement) }
            return array
        }
        var object = node as! [String: Any]
        if path.count == 1 { object[key] = replacement }
        else { object[key] = replacing(object[key]!, path.dropFirst(), replacement) }
        return object
    }

    /// Sets the value at `path`; `nil` removes the key.
    static func changing(_ report: [String: Any], _ path: String, _ replacement: Any?) -> [String: Any] {
        replacing(report, path.components(separatedBy: ".")[...], replacement) as! [String: Any]
    }

    static func adding(_ report: [String: Any], _ path: String, _ delta: Int) -> [String: Any] {
        changing(report, path, (get(report, path) as! Int) + delta)
    }

    static func entryIndex(_ report: [String: Any], _ symbol: String) -> Int {
        let entries = get(report, "import_calls.entries") as! [[String: Any]]
        return entries.firstIndex { $0["symbol"] as? String == symbol }!
    }

    static func rowIndex(_ report: [String: Any], symbol: String, occurrence: Int = 0) -> Int {
        let rows = report["calls"] as! [[String: Any]]
        let matching = rows.indices.filter { (rows[$0]["admission"] as? [String: Any])?["symbol"] as? String == symbol }
        return matching[occurrence]
    }

    // MARK: Mutation catalogue (contract 4.7, 4.8, 5.1 and 5.2)

    typealias Mutation = (name: String, rule: String, apply: ([String: Any]) -> [String: Any])

    /// Each mutation breaks one rule of the accounting and leaves the others, so the expected rule id is the only reason.
    static func accountingMutations(_ base: [String: Any]) -> [Mutation] {
        let entryA = "import_calls.entries.\(entryIndex(base, "_$sA"))"
        let entryB = "import_calls.entries.\(entryIndex(base, "_$sB"))"
        let entryF = "import_calls.entries.\(entryIndex(base, "_swift_retain"))"
        let entryW = "import_calls.entries.\(entryIndex(base, witnessSymbol))"
        let secondA = rowIndex(base, symbol: "_$sA", occurrence: 1)
        var list: [Mutation] = []
        func add(_ name: String, _ rule: String, _ apply: @escaping ([String: Any]) -> [String: Any]) {
            list.append((name, rule, apply))
        }
        // A1: rows equal selected minus omitted.
        add("A1 selected without a row", "A1") { adding(adding($0, "selected_call_candidates", 1), "observed_call_instructions", 1) }
        // A2: omitted equals the sum of the causes equals the sum of the kinds.
        add("A2 kind sum above omitted", "A2") { adding($0, "omitted_by_kind.indirect", 1) }
        add("A2 cause sum below omitted", "A2") { adding($0, "omission_causes.output_budget", -1) }
        // A3: omissions mean the details and witnesses are not complete.
        add("A3 details complete with omissions", "A3") { changing($0, "call_details_complete", true) }
        add("A3 witnesses complete with omissions", "A3") { changing($0, "outcome_witnesses_complete", true) }
        // A4: reason and status counts cover the rows, with no scan marker.
        add("A4 reason counts above the rows", "A4") { adding($0, "reason_counts.imported_callee_abi_unqualified", 1) }
        add("A4 status counts below the rows", "A4") { adding($0, "status_counts.unresolved", -1) }
        add("A4 scan marker as a reason", "A4") {
            changing(adding($0, "reason_counts.imported_callee_abi_unqualified", -1), "reason_counts.excluded_boundary", 1)
        }
        // A5: observed equals selected plus the unselected buckets, and other is 0.
        add("A5 bucket without an observed call", "A5") { adding($0, "unselected_call_counts.skipped_non_throwing", 1) }
        add("A5 other is not zero", "A5") { changing($0, "unselected_call_counts.other", 1) }
        // A6: the row limit and the per-function limit.
        add("A6 retention limit changed", "A6") { changing($0, "limits.max_total_evidence", 8191) }
        add("A6 per-function omissions without a full caller", "A6") {
            adding(adding($0, "omission_causes.per_function_limit", 1), "omission_causes.output_budget", -1)
        }
        add("A6 row-limit omissions below the row limit", "A6") {
            adding(adding($0, "omission_causes.total_row_limit", 1), "omission_causes.output_budget", -1)
        }
        // B1 to B3: the scan arithmetic.
        add("B1 words_total above the parts", "B1") { adding($0, "scan.words_total", 1) }
        add("B1 scanned_words differs from scan.words_scanned", "B1") { adding($0, "scanned_words", 1) }
        add("B2 truncated function without unscanned words", "B2") { changing($0, "scan.functions_truncated", 1) }
        add("B2 incomplete scan without a truncated function", "B2") { changing($0, "word_scan_complete", false) }
        add("B3 candidates counted with no unscanned words", "B3") { changing($0, "scan.candidates_in_unscanned_words", 1) }
        add("B3 reason with no unscanned words", "B3") { changing($0, "scan.candidates_in_unscanned_words_reason", "words_not_decoded") }
        // C1 to C7: the import table.
        add("C1 entry calls above its parts", "C1") { adding(adding($0, "\(entryA).calls", 1), "\(entryA).stub_calls", 1) }
        add("C1 undecided entry without a reason", "C1") { changing($0, "\(entryB).reason", NSNull()) }
        add("C1 reason outside the closed list", "C1") { changing($0, "\(entryB).reason", "mystery") }
        add("C1 not_swift flag disagrees with the counts", "C1") { changing($0, "\(entryF).decision", "throwing") }
        add("C2 entries out of order", "C2") {
            var entries = get($0, "import_calls.entries") as! [Any]
            entries.swapAt(0, 1)
            return changing($0, "import_calls.entries", entries)
        }
        add("C2 duplicate symbol", "C2") {
            var entries = get($0, "import_calls.entries") as! [Any]
            entries[1] = entries[0]
            return changing($0, "import_calls.entries", entries)
        }
        add("C2 more entries than the limit", "C2") { changing($0, "limits.import_table_entries", 1) }
        add("C2 distinct_symbols without the residual", "C2") { adding($0, "import_calls.residual.symbols", 1) }
        add("C2 attributed_calls above the entries", "C2") { adding($0, "import_calls.attributed_calls", 1) }
        add("C2 residual does not close", "C2") { adding($0, "import_calls.residual.calls", 1) }
        add("C3 complete false with a zero residual", "C3") { changing($0, "import_calls.complete", false) }
        add("C4 retained differs from the rows", "C4") { adding(adding($0, "\(entryA).retained", -1), "\(entryA).skipped_non_throwing", 1) }
        add("C4 skipped differs from the unselected bucket", "C4") {
            adding(adding($0, "unselected_call_counts.skipped_non_throwing", 1), "observed_call_instructions", 1)
        }
        add("C4 not_swift differs from the unselected bucket", "C4") {
            adding(adding($0, "unselected_call_counts.non_swift_import", 1), "observed_call_instructions", 1)
        }
        add("C4 omitted differs from the import kinds", "C4") {
            adding(adding($0, "omitted_by_kind.import_got", -1), "omitted_by_kind.indirect", 1)
        }
        add("C5 attributed_swift_calls above the table", "C5") { adding($0, "import_calls.attributed_swift_calls", 1) }
        add("C5 grid above the Swift calls", "C5") { adding($0, "decision_by_shape.throwing.none", 1) }
        add("C6 names above the distinct Swift symbols", "C6") { adding($0, "decision_summary.names.throwing", 1) }
        add("C6 undecided reason outside the closed list", "C6") {
            var by = get($0, "decision_summary.undecided_by_reason") as! [String: Any]
            by["mystery"] = by.removeValue(forKey: "accessor")
            return changing($0, "decision_summary.undecided_by_reason", by)
        }
        add("C6 undecided names differ from the reasons", "C6") { adding($0, "decision_summary.undecided_by_reason.accessor.names", 1) }
        add("C6 undecided calls differ from the grid", "C6") { adding($0, "decision_summary.undecided_by_reason.accessor.calls", 1) }
        add("C7 admitted metadata accessor listed as throwing", "C7") { changing($0, "\(entryW).decision", "throwing") }
        // D1: one symbol, one record.
        add("D1 two rows of one symbol with different records", "D1") {
            changing($0, "calls.\(secondA).admission.declaration.entity", "Method")
        }
        // E1: capabilities and limits.
        add("E1 report model in capabilities", "E1") { changing($0, "capabilities.report_model", "swift-broad-error-flow-extended-v3") }
        add("E1 premises reordered", "E1") {
            changing($0, "capabilities.premises", Array((get($0, "capabilities.premises") as! [Any]).reversed()))
        }
        add("E1 not_claimed shortened", "E1") {
            changing($0, "capabilities.not_claimed", Array((get($0, "capabilities.not_claimed") as! [Any]).dropLast()))
        }
        add("E1 capabilities with an extra key", "E1") { changing($0, "capabilities.extra", "x") }
        add("E1 limit missing", "E1") { changing($0, "limits.max_total_instructions", nil) }
        add("E1 limit negative", "E1") { changing($0, "limits.analysis_work_ceiling", -1) }
        add("E1 limit a boolean", "E1") { changing($0, "limits.import_table_entries", true) }
        return list
    }
}

// MARK: - Tests

final class SwiftBroadExtendedV4ReportTests: XCTestCase {
    typealias F = V4Fixture

    // MARK: Helpers

    private func serialized(_ value: [String: Any]) throws -> Data {
        try JSONSerialization.data(withJSONObject: value, options: [.sortedKeys])
    }

    /// Serializes, parses again (so numbers and booleans take their decoded form) and hands the parsed object to the decoder.
    private func decode(_ value: [String: Any]) throws -> SwiftFlowReport {
        let raw = try serialized(value)
        let parsed = try XCTUnwrap(JSONSerialization.jsonObject(with: raw) as? [String: Any])
        return try SwiftBroadFlowReport.decode(parsed, data: raw)
    }

    private func reasonText(_ error: Error) -> String {
        if let report = error as? SwiftFlowReportError, case .invalid(let reason) = report { return reason }
        return String(describing: error)
    }

    /// The refusal message, or nil when the report decodes.
    private func refusal(_ value: [String: Any]) -> String? {
        do { _ = try decode(value); return nil } catch { return reasonText(error) }
    }

    /// Removes one optional decoder prefix such as "broad-extended-v4: " so that the rule id leads the text.
    private func ruleText(_ message: String) -> String {
        guard let range = message.range(of: ": ") else { return message }
        let head = message[..<range.lowerBound]
        if head.count > 3 && !head.contains(" ") { return String(message[range.upperBound...]) }
        return message
    }

    @discardableResult
    private func accept(_ value: [String: Any], _ note: String = "", file: StaticString = #filePath,
                        line: UInt = #line) -> SwiftFlowReport? {
        do {
            let report = try decode(value)
            XCTAssertTrue(report.supportsInterpretation, "Not interpretable: \(note)", file: file, line: line)
            return report
        } catch {
            XCTFail("Refused \(note): \(reasonText(error))", file: file, line: line)
            return nil
        }
    }

    private func assertRefused(_ value: [String: Any], rule: String, _ note: String = "", file: StaticString = #filePath,
                               line: UInt = #line) {
        guard let message = refusal(value) else {
            XCTFail("Accepted, expected \(rule): \(note)", file: file, line: line)
            return
        }
        XCTAssertTrue(ruleText(message).hasPrefix(rule + ":"), "Expected \(rule) for \(note), got: \(message)", file: file, line: line)
    }

    private func assertRefusedAnyway(_ value: [String: Any], _ note: String, file: StaticString = #filePath, line: UInt = #line) {
        XCTAssertNotNil(refusal(value), "Accepted: \(note)", file: file, line: line)
    }

    private func same(_ left: Any?, _ right: Any?) -> Bool {
        guard let left = left as? NSObject, let right = right as? NSObject else { return left == nil && right == nil }
        return left.isEqual(right)
    }

    private func repoFile(_ relative: String, file: String = #filePath) -> URL {
        var url = URL(fileURLWithPath: file)
        for _ in 0..<4 { url.deleteLastPathComponent() }
        return url.appendingPathComponent(relative)
    }

    /// The same report as a v3 report: no v4 group, v3 pair.
    private func v3Report(_ base: [String: Any] = F.makeValidV4Report()) -> [String: Any] {
        var value = base
        for group in F.groups { value.removeValue(forKey: group) }
        value["model_version"] = "swift-broad-error-flow-extended-v3"
        value["profile"] = "broad-extended-v3"
        return value
    }

    private func v1Declaration() -> [String: Any] {
        var declaration: [String: Any] = [:]
        declaration["status"] = "syntax_unresolved"; declaration["identity"] = NSNull(); declaration["reason"] = "unsupported_syntax"
        return declaration
    }

    private func distinctSkipped(_ count: Int) -> [F.Event] {
        (0..<count).map { index in
            let digits = String(index)
            return F.Event.skipped("_$sN" + String(repeating: "0", count: 5 - digits.count) + digits)
        }
    }

    // MARK: E1 and E2

    func testE1AcceptsZeroRowAndTwoRowReports() throws {
        let empty = try XCTUnwrap(accept(F.makeValidV4Report(), "zero rows"))
        XCTAssertEqual(empty.calls.count, 0)
        XCTAssertEqual(empty.modelVersion, F.model)
        XCTAssertEqual(empty.omittedCallCount, 0)
        XCTAssertTrue(empty.wordScanComplete); XCTAssertTrue(empty.callDetailsComplete); XCTAssertTrue(empty.witnessesComplete)

        let two = try XCTUnwrap(accept(F.twoRowReport(), "two rows"))
        XCTAssertEqual(two.calls.count, 2)
        XCTAssertEqual(Set(two.calls.map(\.calleeSymbol)), ["_$sAlpha", "_$sBeta"])
        XCTAssertTrue(two.calls.allSatisfy { $0.status == "unresolved" })

        // Every decision, every outcome, both call routes, one omission of each kind, the metadata accessor and the non-Swift import.
        let rich = try XCTUnwrap(accept(F.rich(), "rich report"))
        XCTAssertEqual(rich.calls.count, 10)
        XCTAssertEqual(rich.omittedCallCount, 3)
        XCTAssertFalse(rich.callDetailsComplete); XCTAssertFalse(rich.witnessesComplete)
        XCTAssertTrue(rich.wordScanComplete)
    }

    func testE2PairListHasSevenDistinctEntries() {
        let pairs = AnalysisModels.swiftBroadNativePairs.map { $0.model + "|" + $0.profile }
        XCTAssertEqual(pairs, [
            "swift-broad-error-flow-v1|broad-v1", "swift-broad-error-flow-large-v1|broad-large-v1",
            "swift-broad-error-flow-extended-v1|broad-extended-v1", "swift-broad-error-flow-imports-v1|broad-imports-v1",
            "swift-broad-error-flow-extended-v2|broad-extended-v2", "swift-broad-error-flow-extended-v3|broad-extended-v3",
            F.model + "|" + F.profile])
        XCTAssertEqual(pairs.count, 7)
        XCTAssertEqual(Set(pairs).count, pairs.count, "a duplicate pair")
        XCTAssertEqual(Set(AnalysisModels.swiftBroadNativePairs.map(\.model)).count, 7, "a model on two pairs")
        XCTAssertEqual(Set(AnalysisModels.swiftBroadNativePairs.map(\.profile)).count, 7, "a profile on two pairs")
    }

    func testE2PairMismatchIsRefusedAsE2() {
        let v3Model = "swift-broad-error-flow-extended-v3"
        // The v4 model with another profile, the v4 profile with another model, and a v4 identity half present.
        let mismatches: [(String?, String?)] = [
            (F.model, "broad-extended-v3"), (v3Model, F.profile), (F.model, "broad-extended-v2"), (F.model, "broad-large-v1"),
            ("swift-broad-error-flow-extended-v2", F.profile), (F.model, nil), (nil, F.profile)]
        for (model, profile) in mismatches {
            let label = "\(model ?? "no model") with \(profile ?? "no profile")"
            // Carrying every v4 group: refused as E2.
            var full = F.makeValidV4Report()
            if let model { full["model_version"] = model } else { full.removeValue(forKey: "model_version") }
            if let profile { full["profile"] = profile } else { full.removeValue(forKey: "profile") }
            assertRefused(full, rule: "E2", "v4 groups, \(label)")
            // A v3-shaped report with no v4 group at all still names the v4 identity: refused as E2, not read as unsupported.
            var bare = v3Report()
            if let model { bare["model_version"] = model } else { bare.removeValue(forKey: "model_version") }
            if let profile { bare["profile"] = profile } else { bare.removeValue(forKey: "profile") }
            assertRefused(bare, rule: "E2", "no v4 groups, \(label)")
        }
        // The v3 report itself, and the v4 report itself, stay accepted.
        accept(v3Report(), "v3 pair, no v4 groups")
        accept(F.makeValidV4Report(), "v4 pair, every group")
    }

    func testE3RemovingAnyV4GroupIsRefusedAsE2() {
        for base in [F.makeValidV4Report(), F.rich()] {
            accept(base, "baseline")
            for group in F.groups {
                assertRefused(F.changing(base, group, nil), rule: "E2", "missing \(group)")
            }
        }
    }

    func testE3UnknownTopLevelKeyUnderV4IsRefused() {
        var value = F.makeValidV4Report()
        value["unexpected_top_level_key"] = 1
        assertRefusedAnyway(value, "unknown top-level key under the v4 pair")
        var nested = F.makeValidV4Report()
        nested = F.changing(nested, "scan.unexpected_scan_key", 1)
        assertRefusedAnyway(nested, "unknown key in a v4 group")
    }

    func testE3V4GroupOnV3ReportIsRefusedAsE2() {
        let base = v3Report()
        accept(base, "v3 without v4 groups")
        let full = F.makeValidV4Report()
        for group in F.groups {
            var value = base
            value[group] = full[group]
            assertRefused(value, rule: "E2", "\(group) present under the v3 pair")
        }
    }

    // MARK: E4

    func testE4IntegerDisciplineRefusesWithTheArithmeticRuleAndDoesNotCrash() {
        let base = F.rich()
        accept(base, "baseline")
        let cases: [(String, Any, String)] = [
            ("omission_causes.output_budget", -1, "A2"),
            ("omission_causes.output_budget", 1e30, "A2"),
            ("omission_causes.analysis_work_budget", Int.max, "A2"),
            ("omitted_by_kind.import_stub", true, "A2"),
            ("unselected_call_counts.skipped_non_throwing", 1.5, "A5"),
            ("unselected_call_counts.skipped_non_throwing", Int.max, "A5"),
            ("scan.words_unscanned_total_ceiling", Int.max, "B1"),
            ("import_calls.residual.calls", Int.max, "C2")]
        for (path, replacement, rule) in cases {
            assertRefused(F.changing(base, path, replacement), rule: rule, "\(path) = \(replacement)")
        }
    }

    func testE4ExplicitNullsRemainAccepted() throws {
        // A truncated scan has null candidates and a reason, and an incomplete table has a residual.
        let truncated = F.rich(truncatedWords: 4)
        XCTAssertTrue(F.get(truncated, "scan.candidates_in_unscanned_words") is NSNull)
        let report = try XCTUnwrap(accept(truncated, "truncated scan"))
        XCTAssertFalse(report.wordScanComplete)
        // Decided entries carry an explicit null reason; unset record fields are explicit nulls.
        let base = F.rich()
        let entryIndex = F.entryIndex(base, "_$sA")
        XCTAssertTrue(F.get(base, "import_calls.entries.\(entryIndex).reason") is NSNull)
        accept(base, "explicit nulls")
    }

    // MARK: E5 and E6

    func testE5InconsistentCompactRecordsAreRefusedAsD1() {
        let prefix = "calls.0.admission.declaration."
        let throwingBase = F.single(.throwing)
        accept(throwingBase, "throwing baseline")
        let identified: [(String, String, Any?)] = [
            ("throws false but decision throwing", "throws", false),
            ("typed_throws never but decision throwing", "typed_throws", "never"),
            ("accessor entity but decision throwing", "entity", "Getter"),
            ("accessor reason but decision throwing", "reason", "accessor"),
            ("older syntax model", "syntax_model", "swift-declaration-syntax-v1"),
            ("digest in capitals", "identity_sha256", String(repeating: "A", count: 64)),
            ("digest too short", "identity_sha256", String(repeating: "a", count: 63)),
            ("digest too long", "identity_sha256", String(repeating: "a", count: 65)),
            ("digest of 64 non-hex letters", "identity_sha256", String(repeating: "g", count: 64)),
            ("digest of 64 letters just past f", "identity_sha256", String(repeating: "z", count: 64)),
            ("digest with one non-hex last character", "identity_sha256", String(repeating: "a", count: 63) + "g"),
            ("digest with one capital among lower case", "identity_sha256", String(repeating: "a", count: 31) + "F" + String(repeating: "a", count: 32)),
            ("digest of 64 bytes with a two-byte character", "identity_sha256", String(repeating: "a", count: 62) + "\u{e9}"),
            ("digest with a colon in the digit range", "identity_sha256", String(repeating: "a", count: 63) + ":"),
            ("digest as a number", "identity_sha256", 7),
            ("digest missing but throws present", "identity_sha256", NSNull()),
            ("throws missing but digest present", "throws", NSNull()),
            ("decision outside the four", "decision", "maybe"),
            ("missing key", "entity", nil),
            ("extra key", "unexpected", 1)]
        for (name, key, replacement) in identified {
            assertRefused(F.changing(throwingBase, prefix + key, replacement), rule: "D1", name)
        }

        let thunkBase = F.single(.thunk, shape: "postcall_test_only")
        accept(thunkBase, "no-identity baseline")
        let anonymous: [(String, String, Any?)] = [
            ("no identity cannot be non_throwing", "decision", "non_throwing"),
            ("no identity cannot be throwing", "decision", "throwing"),
            ("no identity cannot be async", "decision", "async"),
            ("no identity cannot give typed_throws", "reason", "typed_throws"),
            ("no identity needs a reason", "reason", NSNull()),
            ("reason outside the closed list", "reason", "mystery")]
        for (name, key, replacement) in anonymous {
            assertRefused(F.changing(thunkBase, prefix + key, replacement), rule: "D1", name)
        }
        // A v1 declaration is not a compact record.
        assertRefused(F.changing(throwingBase, "calls.0.admission.declaration", v1Declaration()), rule: "D1", "v1 declaration under v4")
        // Entity in the accessor list is recomputed as an accessor, so a non_throwing claim is refused.
        // async without throws is recomputed as async, so a throwing claim is refused (throws takes precedence when both are set).
        let asyncOnly = F.Record.identified("throwing", throwing: false, isAsync: true)
        assertRefused(F.single(asyncOnly), rule: "D1", "throwing claimed for an async function that does not throw")
        let getter = F.Record.identified("non_throwing", entity: "Getter")
        assertRefused(F.single(getter), rule: "D1", "non_throwing claimed for a Getter")
    }

    /// The decision a record's fields give, restated from contract finding 6 (accessor, typed Never, throws or typed throws,
    /// async, otherwise non_throwing) for an entity that is not an accessor.
    private func expectedDecision(throwing: Bool, isAsync: Bool, typed: String) -> (decision: String, reason: Any) {
        if typed == "never" { return ("undecided", "typed_throws") }
        if throwing || typed != "none" { return ("throwing", NSNull()) }
        if isAsync { return ("async", NSNull()) }
        return ("non_throwing", NSNull())
    }

    func testE5DecisionMustFollowTheEffectFieldsForEveryCombination() {
        var accepted = 0, refused = 0
        for throwing in [false, true] {
            for isAsync in [false, true] {
                for typed in ["none", "never", "concrete"] {
                    let expected = expectedDecision(throwing: throwing, isAsync: isAsync, typed: typed)
                    let name = "throws \(throwing) async \(isAsync) typed \(typed)"
                    // Every claim the four decisions allow, with the reasons an undecided claim could carry.
                    let claims: [(String, Any)] = [("non_throwing", NSNull()), ("throwing", NSNull()), ("async", NSNull()),
                        ("undecided", "typed_throws"), ("undecided", "thunk_or_specialization")]
                    for (decision, reason) in claims {
                        let record = F.Record(decision: decision, reason: reason, entity: "Function", throwsFlag: throwing,
                                              isAsync: isAsync, typedThrows: typed, digest: F.digest)
                        if decision == expected.decision && (reason as? String) == (expected.reason as? String) {
                            accept(F.single(record), "\(name) claims \(decision)")
                            accepted += 1
                        } else {
                            assertRefused(F.single(record), rule: "D1", "\(name) claims \(decision) \(reason)")
                            refused += 1
                        }
                    }
                }
            }
        }
        XCTAssertEqual(accepted, 12)
        XCTAssertGreaterThan(refused, 40)
        // The two failures the contract names outright.
        assertRefused(F.single(F.Record.identified("non_throwing", throwing: true)), rule: "D1", "non_throwing with throws true")
        assertRefused(F.single(F.Record.identified("non_throwing", isAsync: true)), rule: "D1", "non_throwing with is_async true")
    }

    func testE5ConsistentRecordsAreAccepted() {
        let cases: [(String, F.Record, String)] = [
            ("non_throwing", .nonThrowing, "swifterror_idiom"),
            ("throwing", .throwing, "swifterror_idiom"),
            ("throwing and async", .throwingAsync, "none"),
            ("throwing with a concrete typed error", .throwingConcrete, "precall_zero_only"),
            ("async", .asyncOnly, "none"),
            ("thunk without identity", .thunk, "postcall_test_only"),
            // Contract section 10, amendment 7: a record without identity may be undecided with reason accessor.
            ("accessor without identity", .accessorNoIdentity, "none"),
            ("accessor with identity", .accessorWithIdentity, "none"),
            ("typed_throws never", .typedNever, "none")]
        for (name, record, shape) in cases { accept(F.single(record, shape: shape), name) }
    }

    func testE6NativeDoesNotRecomputeTheGrammar() {
        // The digest and the entity are taken as recorded: neither is derived again from the symbol.
        accept(F.single(F.Record(decision: "throwing", reason: NSNull(), entity: "Struct", throwsFlag: true, isAsync: false,
                                 typedThrows: "none", digest: String(repeating: "0", count: 64))), "entity not matching the mangling")
        accept(F.single(F.Record(decision: "throwing", reason: NSNull(), entity: "NotInAnyList", throwsFlag: true, isAsync: false,
                                 typedThrows: "none", digest: String(repeating: "f", count: 64))), "unlisted entity")
        let odd = F.report([.retained("_$sZZZZnotamangling", .throwing)])
        accept(odd, "symbol the grammar could not parse")
    }

    // MARK: E7 and E8

    func testE7LicenceRecomputationOverEveryTableRow() {
        let table: [(F.Record, String)] = [
            (.nonThrowing, "no_error_exit"), (.throwing, "declared_error_exit"),
            (.throwingAsync, "refused_unsupported_effect"), (.throwingConcrete, "refused_unsupported_effect"),
            (.asyncOnly, "refused_unsupported_effect"), (.thunk, "none"),
            (.accessorWithIdentity, "none"), (.typedNever, "none")]
        for (record, licence) in table {
            XCTAssertEqual(record.licence, licence)
            let good = F.single(record)
            accept(good, "licence \(licence)")
            XCTAssertEqual(F.get(good, "calls.0.effect_admission.licence_class") as? String, licence)
            for claimed in F.licences where claimed != licence {
                assertRefused(F.single(record, claimed: claimed), rule: "D2", "\(licence) claimed as \(claimed)")
            }
        }
    }

    func testE8RelationStatusAndReasonRulesAsD3() {
        // Literal expectations from the relation table.
        let corroborated = F.single(.throwing, shape: "swifterror_idiom", kind: "bl")
        XCTAssertEqual(F.get(corroborated, "calls.0.effect_admission.caller_relation") as? String, "corroborated")
        accept(corroborated, "declared, idiom, bl")
        let noSignal = F.single(.throwing, shape: "none", kind: "bl")
        XCTAssertEqual(F.get(noSignal, "calls.0.effect_admission.caller_relation") as? String, "no_signal")
        accept(noSignal, "declared, no shape, bl")
        let tail = F.single(.throwing, shape: "swifterror_idiom", kind: "b")
        XCTAssertEqual(F.get(tail, "calls.0.effect_admission.caller_relation") as? String, "not_applicable")
        accept(tail, "declared, idiom, tail b")
        let conflict = F.single(.nonThrowing, shape: "swifterror_idiom", kind: "bl")
        XCTAssertEqual(F.get(conflict, "calls.0.effect_admission.caller_relation") as? String, "conflict")
        XCTAssertEqual(F.get(conflict, "calls.0.admission.reason") as? String, "declaration_caller_disagreement")
        accept(conflict, "no_error_exit, idiom, bl")

        // Every retained combination the table allows is accepted.
        for record in [F.Record.throwing, .throwingConcrete, .asyncOnly, .thunk] {
            for shape in F.shapes {
                for kind in ["bl", "b"] { accept(F.single(record, shape: shape, kind: kind), "\(record.decision) \(shape) \(kind)") }
            }
        }
        // A non_throwing call is retained only with the idiom and bl; everything else is skipped, so a retained row is invalid.
        for shape in F.shapes {
            for kind in ["bl", "b"] where !(shape == "swifterror_idiom" && kind == "bl") {
                assertRefused(F.single(.nonThrowing, shape: shape, kind: kind), rule: "D3", "retained non_throwing \(shape) \(kind)")
            }
        }

        for relation in ["corroborated", "conflict", "not_applicable", "mystery"] {
            assertRefused(F.changing(noSignal, "calls.0.effect_admission.caller_relation", relation), rule: "D3", "relation \(relation) for no_signal")
        }
        for relation in ["corroborated", "no_signal", "conflict"] {
            assertRefused(F.changing(tail, "calls.0.effect_admission.caller_relation", relation), rule: "D3", "relation \(relation) for a tail call")
        }
        for reason in ["imported_callee_abi_unqualified", "imported_callee_effect_unsupported", "declaration_caller_disagreement"] {
            assertRefused(F.changing(noSignal, "calls.0.admission.reason", reason), rule: "D3", "reason \(reason) for a declared licence")
        }
        var declined = F.changing(noSignal, "calls.0.admission.status", "declined")
        declined = F.changing(declined, "status_counts", ["declined": 1])
        assertRefused(declined, rule: "D3", "status other than unresolved")
        assertRefusedAnyway(F.changing(noSignal, "calls.0.effect_admission.model", "swift-import-effect-admission-v2"), "unknown effect model")
    }

    /// One retained row of every licence class, through a stub and through a GOT slot, with the literal relation and reason
    /// contract 4.4 and 4.5 give it.
    private func classBases() -> [(name: String, base: [String: Any], relation: String, reason: String)] {
        [("no_error_exit via stub", F.single(.nonThrowing), "conflict", "declaration_caller_disagreement"),
         ("no_error_exit via GOT", F.singleGot(.nonThrowing), "conflict", "declaration_caller_disagreement"),
         ("declared_error_exit via stub", F.single(.throwing), "corroborated", "imported_callee_outcome_unmodeled"),
         ("declared_error_exit via GOT", F.singleGot(.throwing), "corroborated", "imported_callee_outcome_unmodeled"),
         ("refused_unsupported_effect via stub", F.single(.asyncOnly), "not_applicable", "imported_callee_effect_unsupported"),
         ("refused_unsupported_effect via GOT", F.singleGot(.asyncOnly), "not_applicable", "imported_callee_effect_unsupported"),
         ("none via stub", F.single(.thunk), "not_applicable", "imported_callee_abi_unqualified"),
         ("none via GOT", F.singleGot(.thunk), "not_applicable", "imported_callee_abi_unqualified")]
    }

    func testE8EveryClassRefusesEveryWrongRelationAndReasonAsD3() {
        let relations = ["conflict", "corroborated", "no_signal", "not_applicable"]
        let reasons = ["declaration_caller_disagreement", "imported_callee_outcome_unmodeled",
                       "imported_callee_effect_unsupported", "imported_callee_abi_unqualified"]
        for item in classBases() {
            XCTAssertEqual(F.get(item.base, "calls.0.effect_admission.caller_relation") as? String, item.relation, item.name)
            XCTAssertEqual(F.get(item.base, "calls.0.admission.reason") as? String, item.reason, item.name)
            accept(item.base, item.name)
            // The relation of the class, and no other, for the shape and call kind the base has.
            for relation in relations where relation != item.relation {
                assertRefused(F.changing(item.base, "calls.0.effect_admission.caller_relation", relation), rule: "D3",
                              "\(item.name) with relation \(relation)")
            }
            assertRefused(F.changing(item.base, "calls.0.effect_admission.caller_relation", "mystery"), rule: "D3",
                          "\(item.name) with an unknown relation")
            assertRefused(F.changing(item.base, "calls.0.effect_admission.caller_relation", NSNull()), rule: "D3",
                          "\(item.name) with a null relation")
            // The reason of the class, and no other.
            for reason in reasons where reason != item.reason {
                assertRefused(F.changing(item.base, "calls.0.admission.reason", reason), rule: "D3",
                              "\(item.name) with reason \(reason)")
            }
            assertRefused(F.changing(item.base, "calls.0.admission.reason", "unqualified"), rule: "D3",
                          "\(item.name) with the plain-row reason")
            // Status stays unresolved on a retained import row.
            for status in ["declined", "admitted_callsite", "invalid"] {
                assertRefused(F.changing(item.base, "calls.0.admission.status", status), rule: "D3",
                              "\(item.name) with status \(status)")
            }
        }
        // Classes none and refused_unsupported_effect keep not_applicable for every shape and for tail calls.
        for record in [F.Record.thunk, .asyncOnly, .throwingAsync, .throwingConcrete, .accessorWithIdentity, .typedNever] {
            for shape in F.shapes {
                for kind in ["bl", "b"] {
                    let base = F.single(record, shape: shape, kind: kind)
                    XCTAssertEqual(F.get(base, "calls.0.effect_admission.caller_relation") as? String, "not_applicable")
                    accept(base, "\(record.licence) \(shape) \(kind)")
                    for relation in ["conflict", "corroborated", "no_signal"] {
                        assertRefused(F.changing(base, "calls.0.effect_admission.caller_relation", relation), rule: "D3",
                                      "\(record.licence) \(shape) \(kind) with relation \(relation)")
                    }
                }
            }
        }
        // A non-throwing row with the relation of another case: no_signal is what a skipped call would have, never a row.
        let conflict = F.single(.nonThrowing)
        assertRefused(F.changing(conflict, "calls.0.effect_admission.caller_relation", "no_signal"), rule: "D3",
                      "no_error_exit with no_signal")
        assertRefused(F.changing(conflict, "calls.0.effect_admission.caller_relation", "corroborated"), rule: "D3",
                      "no_error_exit with corroborated")
    }

    // MARK: Retained GOT rows (contract 4.4, 4.8, 5.2 D1 to D4 and C4)

    func testGotRowsAreAcceptedForEveryClassAndShape() throws {
        for record in [F.Record.nonThrowing, .throwing, .throwingAsync, .throwingConcrete, .asyncOnly, .thunk,
                       .accessorNoIdentity, .accessorWithIdentity, .typedNever] {
            for shape in F.shapes {
                let retained = record.decision == "non_throwing" && shape != "swifterror_idiom" ? false : true
                let report = F.singleGot(record, shape: shape)
                if retained {
                    let decoded = try XCTUnwrap(accept(report, "GOT \(record.licence) \(shape)"))
                    XCTAssertEqual(decoded.calls.count, 1)
                    XCTAssertEqual(decoded.calls.first?.status, "unresolved")
                    XCTAssertEqual(F.get(report, "calls.0.admission.call_kind") as? String, "blr_got")
                    XCTAssertEqual(F.get(report, "calls.0.admission.model_version") as? String, "swift-broad-got-callsite-v1")
                    XCTAssertEqual(F.get(report, "calls.0.effect_admission.licence_class") as? String, record.licence)
                } else {
                    // Contract 4.4: a retained non_throwing row exists only with the idiom and a linking call.
                    assertRefused(report, rule: "D3", "retained GOT non_throwing \(shape)")
                }
            }
        }
        // The relation of a GOT call is the relation of a bl call: it has a post-call window.
        XCTAssertEqual(F.get(F.singleGot(.throwing), "calls.0.effect_admission.caller_relation") as? String, "corroborated")
        XCTAssertEqual(F.get(F.singleGot(.throwing, shape: "none"), "calls.0.effect_admission.caller_relation") as? String, "no_signal")
        XCTAssertEqual(F.get(F.singleGot(.nonThrowing), "calls.0.effect_admission.caller_relation") as? String, "conflict")
    }

    func testGotAndStubRowsShareTheTableAndTheRecordOfOneSymbol() throws {
        let events: [F.Event] = [
            .retained("_$sBoth", .throwing, shape: "swifterror_idiom"),
            .retainedGot("_$sBoth", .throwing, shape: "none"),
            .retainedGot("_$sGotOnly", .nonThrowing, shape: "swifterror_idiom"),
            .retainedGot("_$sRefused", .asyncOnly),
            .omitted("_$sGotOnly", .nonThrowing, via: "got", shape: "none", cause: "per_function_limit")]
        let report = F.report(events, plain: 256, plainPerCaller: 256)
        let decoded = try XCTUnwrap(accept(report, "stub and GOT rows of one symbol"))
        XCTAssertEqual(decoded.calls.count, 256 + 3 + 1)
        let entry = try XCTUnwrap((F.get(report, "import_calls.entries") as? [[String: Any]])?.first { $0["symbol"] as? String == "_$sBoth" })
        XCTAssertEqual(entry["stub_calls"] as? Int, 1); XCTAssertEqual(entry["got_calls"] as? Int, 1)
        XCTAssertEqual(entry["retained"] as? Int, 2)
        // C4 counts retained rows by effect_admission, GOT rows included.
        let index = F.entryIndex(report, "_$sBoth")
        assertRefused(F.adding(F.adding(report, "import_calls.entries.\(index).retained", -1),
                               "import_calls.entries.\(index).skipped_non_throwing", 1), rule: "C4", "a retained GOT row not counted")
        // D1: the two routes of one symbol carry one record.
        let gotRow = F.rowIndex(report, symbol: "_$sBoth", occurrence: 1)
        assertRefused(F.changing(report, "calls.\(gotRow).admission.declaration.entity", "Method"), rule: "D1",
                      "GOT row with another record than the stub row")
    }

    func testGotRowRulesD1ToD4() {
        let base = F.singleGot(.throwing)
        accept(base, "GOT baseline")
        // D2: a GOT row must carry effect_admission, with the class its record gives.
        // The table counts retained rows by their effect_admission, and C4 is checked before D2.
        assertRefused(F.changing(base, "calls.0.effect_admission", nil), rule: "C4", "GOT row without effect_admission")
        for claimed in F.licences where claimed != "declared_error_exit" {
            assertRefused(F.singleGot(.throwing, claimed: claimed), rule: "D2", "GOT throwing claimed as \(claimed)")
        }
        // D2: effect_admission is for the two import callsite models only.
        assertRefused(F.changing(base, "calls.0.admission.model_version", "swift-broad-callsite-v1"), rule: "D2",
                      "GOT row renamed to the base callsite model keeps effect_admission")
        // D1: the compact record, never the first-generation declaration.
        assertRefused(F.changing(base, "calls.0.admission.declaration", v1Declaration()), rule: "D1", "v1 declaration on a GOT row")
        assertRefused(F.changing(base, "calls.0.admission.declaration.syntax_model", "swift-declaration-syntax-v1"), rule: "D1",
                      "older syntax model on a GOT row")
        assertRefused(F.changing(base, "calls.0.admission.declaration.identity_sha256", String(repeating: "g", count: 64)), rule: "D1",
                      "non-hex digest on a GOT row")
        // D3: the call kind of a GOT row is blr_got; a name outside the call kinds is refused.
        accept(F.changing(base, "calls.0.admission.call_kind", "blr_got"), "GOT row with call kind blr_got")
        for kind in ["blx", "call", "", "BLR_GOT"] {
            assertRefused(F.changing(base, "calls.0.admission.call_kind", kind), rule: "D3", "GOT row with call kind '\(kind)'")
        }
        assertRefused(F.changing(base, "calls.0.admission.call_kind", NSNull()), rule: "D3", "GOT row with a null call kind")
        assertRefused(F.changing(base, "calls.0.admission.status", "declined"), rule: "D3", "GOT row with another status")
        assertRefused(F.changing(base, "calls.0.effect_admission.caller_relation", "conflict"), rule: "D3", "GOT row with relation conflict")
        // D4: no abi, candidate or validation on a GOT row.
        var abi: [String: Any] = [:]
        abi["status"] = "admitted"; abi["error_register"] = "x21"
        assertRefused(F.changing(base, "calls.0.admission.abi", abi), rule: "D4", "abi on a GOT row")
        assertRefused(F.changing(base, "calls.0.abi", abi), rule: "D4", "abi beside a GOT row")
        let record: [String: Any] = ["status": "unresolved"]
        assertRefused(F.changing(base, "calls.0.candidate", record), rule: "D4", "candidate on a GOT row")
        assertRefused(F.changing(base, "calls.0.validation", record), rule: "D4", "validation on a GOT row")
    }

    func testE8ImportRowWithAbiCandidateOrValidationIsRefusedAsD4() {
        let base = F.single(.throwing)
        accept(base, "baseline")
        var abi: [String: Any] = [:]
        abi["status"] = "admitted"; abi["profile"] = "swift6-arm64-sync-untyped-stable-research-v2"; abi["error_register"] = "x21"
        assertRefused(F.changing(base, "calls.0.admission.abi", abi), rule: "D4", "abi on an import row")
        let record: [String: Any] = ["status": "unresolved"]
        assertRefused(F.changing(base, "calls.0.candidate", record), rule: "D4", "candidate on an import row")
        assertRefused(F.changing(base, "calls.0.validation", record), rule: "D4", "validation on an import row")

        // A row that is not an import row has no effect admission.
        let rich = F.rich()
        let plain = (rich["calls"] as! [Any]).count - 1
        var effect: [String: Any] = [:]
        effect["model"] = F.effectModel; effect["licence_class"] = "none"; effect["caller_relation"] = "not_applicable"
        assertRefusedAnyway(F.changing(rich, "calls.\(plain).effect_admission", effect), "effect admission on a plain row")
    }

    // MARK: E9

    func testE9AccountingMutationsAreRefusedWithTheirRuleId() {
        let base = F.rich()
        accept(base, "rich baseline")
        let mutations = F.accountingMutations(base)
        XCTAssertGreaterThanOrEqual(mutations.count, 45)
        for mutation in mutations {
            assertRefused(mutation.apply(base), rule: mutation.rule, mutation.name)
        }
        // Every rule family of sections 4.7 and 4.8 is exercised.
        let rules = Set(mutations.map(\.rule))
        for rule in ["A1", "A2", "A3", "A4", "A5", "A6", "B1", "B2", "B3", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "D1", "E1"] {
            XCTAssertTrue(rules.contains(rule), rule)
        }
    }

    func testE9PerCallerRowLimitAndSymbolSameness() {
        // At most 256 rows share a caller.
        accept(F.report([], plain: 256, plainPerCaller: 1000), "256 rows on one caller")
        assertRefused(F.report([], plain: 257, plainPerCaller: 1000), rule: "A6", "257 rows on one caller")
        // Per-function omissions need a caller with exactly 256 rows.
        let perFunction = [F.Event.omitted("_$sLimit", .throwing, cause: "per_function_limit")]
        accept(F.report(perFunction, plain: 256, plainPerCaller: 1000), "per_function_limit with a full caller")
        assertRefused(F.report(perFunction, plain: 255, plainPerCaller: 1000), rule: "A6", "per_function_limit without a full caller")
        // Total-row omissions need exactly 8192 rows.
        let totalRows = [F.Event.omitted("_$sLimit", .throwing, cause: "total_row_limit")]
        accept(F.report(totalRows, plain: 8192, plainPerCaller: 256), "total_row_limit at 8192 rows")
        assertRefused(F.report(totalRows, plain: 8191, plainPerCaller: 256), rule: "A6", "total_row_limit below 8192 rows")
        // One symbol means one record; the same record twice is fine.
        let twice = F.report([.retained("_$sSame", .throwing), .retained("_$sSame", .throwing, shape: "postcall_test_only")])
        accept(twice, "same symbol, same record")
        let different = F.changing(twice, "calls.1.admission.declaration", F.Record.thunk.json)
        assertRefused(different, rule: "D1", "same symbol, different record")
    }

    func testE9AcceptanceEdgeCases() throws {
        // No omissions: details and witnesses complete.
        let empty = try XCTUnwrap(accept(F.makeValidV4Report(), "omitted 0"))
        XCTAssertTrue(empty.callDetailsComplete)
        XCTAssertEqual(F.get(F.makeValidV4Report(), "import_calls.complete") as? Bool, true)
        // Exactly 4,096 entries, zero residual, complete.
        let full = F.report(distinctSkipped(4096))
        XCTAssertEqual((F.get(full, "import_calls.entries") as? [Any])?.count, 4096)
        XCTAssertEqual(F.get(full, "import_calls.complete") as? Bool, true)
        accept(full, "4096 entries")
        // One symbol over the limit goes to the residual and the table is incomplete.
        let over = F.report(distinctSkipped(4097))
        XCTAssertEqual(F.get(over, "import_calls.residual.symbols") as? Int, 1)
        XCTAssertEqual(F.get(over, "import_calls.complete") as? Bool, false)
        accept(over, "4097 symbols")
        // A smaller entry limit moved into the residual along with its calls.
        let residual = F.rich(maxEntries: 3)
        XCTAssertEqual((F.get(residual, "import_calls.entries") as? [Any])?.count, 3)
        accept(residual, "residual from a small table")
        // An incomplete scan.
        accept(F.rich(truncatedWords: 4), "truncated scan")
    }

    // MARK: Scan classes (contract 4.7 and 5.2 B1 to B3): excluded boundary and the total ceiling

    func testScanClassesAreAcceptedWhenTheyAddUp() throws {
        // Words of a function excluded for its boundary: undecoded, so the scan is incomplete and the candidates are unknown.
        let excluded = F.rich(excludedWords: 4, excludedFunctions: 1)
        XCTAssertEqual(F.get(excluded, "scan.words_total") as? Int, 644)
        XCTAssertEqual(F.get(excluded, "scan.words_excluded_boundary") as? Int, 4)
        XCTAssertEqual(F.get(excluded, "scan.functions_truncated") as? Int, 0)
        XCTAssertEqual(F.get(excluded, "word_scan_complete") as? Bool, false)
        XCTAssertTrue(F.get(excluded, "scan.candidates_in_unscanned_words") is NSNull)
        XCTAssertEqual(F.get(excluded, "scan.candidates_in_unscanned_words_reason") as? String, "words_not_decoded")
        XCTAssertEqual(F.get(excluded, "import_calls.complete") as? Bool, false)
        let decoded = try XCTUnwrap(accept(excluded, "excluded boundary words"))
        XCTAssertFalse(decoded.wordScanComplete)

        // A function excluded for its boundary with no words (size not positive): incomplete, yet no word is undecoded, so the
        // candidate count is the integer 0 with a null reason.
        let emptyExcluded = F.rich(excludedFunctions: 1)
        XCTAssertEqual(F.get(emptyExcluded, "scan.words_total") as? Int, 640)
        XCTAssertEqual(F.get(emptyExcluded, "scan.candidates_in_unscanned_words") as? Int, 0)
        let emptyDecoded = try XCTUnwrap(accept(emptyExcluded, "excluded function without words"))
        XCTAssertFalse(emptyDecoded.wordScanComplete)

        // The total ceiling alone, and every class together.
        let ceiling = F.rich(totalCeilingWords: 8)
        XCTAssertEqual(F.get(ceiling, "scan.words_unscanned_total_ceiling") as? Int, 8)
        XCTAssertEqual(F.get(ceiling, "scan.functions_truncated") as? Int, 1)
        XCTAssertFalse(try XCTUnwrap(accept(ceiling, "total ceiling words")).wordScanComplete)
        let every = F.rich(truncatedWords: 3, totalCeilingWords: 8, excludedWords: 4, excludedFunctions: 2)
        XCTAssertEqual(F.get(every, "scan.words_total") as? Int, 655)
        XCTAssertFalse(try XCTUnwrap(accept(every, "every word class")).wordScanComplete)
        accept(F.report([], excludedWords: 4, excludedFunctions: 1), "excluded boundary words, zero rows")
    }

    func testB1ExcludedBoundaryWordsAreCountedInTheTotal() {
        let base = F.rich(excludedWords: 4, excludedFunctions: 1)
        accept(base, "baseline")
        assertRefused(F.adding(base, "scan.words_total", -4), rule: "B1", "words_total leaves out the excluded words")
        assertRefused(F.adding(base, "scan.words_total", 1), rule: "B1", "words_total above the parts")
        assertRefused(F.adding(base, "scan.words_excluded_boundary", 1), rule: "B1", "excluded words above the total")
        assertRefused(F.adding(base, "scan.words_excluded_boundary", -1), rule: "B1", "excluded words below the total")
        assertRefused(F.changing(base, "scan.words_excluded_boundary", Int.max), rule: "B1", "excluded words overflowing the sum")
        assertRefused(F.changing(base, "scan.words_excluded_boundary", -4), rule: "B1", "negative excluded words")
        // The total ceiling and the per-function ceiling are counted too.
        let ceiling = F.rich(truncatedWords: 3, totalCeilingWords: 8)
        accept(ceiling, "both ceilings")
        assertRefused(F.adding(ceiling, "scan.words_total", -8), rule: "B1", "words_total leaves out the total-ceiling words")
        assertRefused(F.adding(ceiling, "scan.words_total", -3), rule: "B1", "words_total leaves out the per-function words")
    }

    func testB2WordScanCompleteFollowsTruncatedAndExcludedFunctions() {
        // The report of the contract's own example: four excluded words, one excluded function, complete claimed everywhere.
        var claimed = F.rich(excludedWords: 4, excludedFunctions: 1)
        claimed = F.changing(claimed, "word_scan_complete", true)
        claimed = F.changing(claimed, "import_calls.complete", true)
        assertRefused(claimed, rule: "B2", "word_scan_complete true with an excluded function")
        // An excluded function with no words is still an incomplete scan.
        assertRefused(F.changing(F.rich(excludedFunctions: 1), "word_scan_complete", true), rule: "B2",
                      "word_scan_complete true with an excluded function that has no words")
        // A scan that is complete has no excluded function.
        let complete = F.rich()
        accept(complete, "baseline")
        assertRefused(F.changing(complete, "scan.functions_excluded_boundary", 1), rule: "B2",
                      "an excluded function with word_scan_complete true")
        // A false word_scan_complete needs a truncated or an excluded function.
        assertRefused(F.changing(complete, "word_scan_complete", false), rule: "B2", "incomplete with nothing truncated or excluded")
        // Truncation follows the two ceiling counts, in both directions.
        assertRefused(F.changing(F.adding(complete, "scan.words_total", 8), "scan.words_unscanned_total_ceiling", 8), rule: "B2",
                      "total-ceiling words with no truncated function")
        assertRefused(F.changing(F.adding(complete, "scan.words_total", 3), "scan.words_unscanned_per_function_ceiling", 3), rule: "B2",
                      "per-function words with no truncated function")
        let ceiling = F.rich(truncatedWords: 3, totalCeilingWords: 8)
        accept(ceiling, "truncated baseline")
        assertRefused(F.changing(ceiling, "scan.functions_truncated", 0), rule: "B2", "truncated function count 0 with unscanned words")
        // A function is truncated or excluded, never counted outside the function total.
        let many = F.changing(F.rich(truncatedWords: 3, excludedWords: 4, excludedFunctions: 1), "scan.functions_total", 1)
        assertRefused(many, rule: "B2", "truncated plus excluded above functions_total")
        accept(F.changing(F.rich(truncatedWords: 3, excludedWords: 4, excludedFunctions: 1), "scan.functions_total", 2),
               "truncated plus excluded equal to functions_total")
    }

    func testB3CandidatesAreUnknownWhenAnyWordIsUndecoded() {
        // Excluded words alone make the candidates unknown.
        let excluded = F.rich(excludedWords: 4, excludedFunctions: 1)
        assertRefused(F.changing(F.changing(excluded, "scan.candidates_in_unscanned_words", 0),
                                 "scan.candidates_in_unscanned_words_reason", NSNull()), rule: "B3",
                      "candidates 0 with excluded words")
        assertRefused(F.changing(excluded, "scan.candidates_in_unscanned_words", 0), rule: "B3", "candidates 0 with a reason")
        assertRefused(F.changing(excluded, "scan.candidates_in_unscanned_words_reason", NSNull()), rule: "B3",
                      "null candidates without a reason")
        assertRefused(F.changing(excluded, "scan.candidates_in_unscanned_words_reason", "other"), rule: "B3", "another reason")
        assertRefused(F.changing(excluded, "scan.candidates_in_unscanned_words", 7), rule: "B3", "a number for unknown candidates")
        // The same for each ceiling.
        for base in [F.rich(truncatedWords: 3), F.rich(totalCeilingWords: 8)] {
            assertRefused(F.changing(F.changing(base, "scan.candidates_in_unscanned_words", 0),
                                     "scan.candidates_in_unscanned_words_reason", NSNull()), rule: "B3", "candidates 0 with unscanned words")
        }
        // An excluded function with no words decodes nothing wrong: candidates are 0, and null is refused.
        let empty = F.rich(excludedFunctions: 1)
        assertRefused(F.changing(F.changing(empty, "scan.candidates_in_unscanned_words", NSNull()),
                                 "scan.candidates_in_unscanned_words_reason", "words_not_decoded"), rule: "B3",
                      "null candidates with no undecoded word")
    }

    // MARK: E10

    private func extra(_ extra: Any, rows: Int = 1) -> [String: Any] {
        F.changing(F.report([], plain: rows), "calls.0.admission.extra", extra)
    }

    func testE10RowBoundary() {
        accept(F.report([], plain: 8192, plainPerCaller: 256), "8192 rows")
        assertRefusedAnyway(F.report([], plain: 8193, plainPerCaller: 256), "8193 rows")
    }

    func testE10StringBoundary() {
        let limit = "evidence string limit exceeded"
        // A string of exactly 65,536 bytes decodes: the report is otherwise valid.
        accept(extra(String(repeating: "a", count: 65_536)), "string of 65,536 bytes")
        let over = refusal(extra(String(repeating: "a", count: 65_537)))
        XCTAssertNotNil(over)
        XCTAssertTrue((over ?? "").contains(limit), over ?? "accepted")
    }

    func testE10DepthBoundary() {
        func chain(_ depth: Int) -> Any {
            var node: Any = "leaf"
            for _ in 0..<depth { node = ["k": node] }
            return node
        }
        let limit = "nested evidence limit exceeded"
        // The leaf of a chain of 28 objects under calls.0.admission.extra sits at depth 32: the report decodes.
        accept(extra(chain(28)), "nesting depth 32")
        let over = refusal(extra(chain(29)))
        XCTAssertNotNil(over)
        XCTAssertTrue((over ?? "").contains(limit) || (over ?? "").contains("malformed or duplicate JSON object key"), over ?? "accepted")
    }

    func testE10NodeLimit() {
        let over = refusal(extra([Int](repeating: 0, count: 2_000_001)))
        XCTAssertNotNil(over)
        // The wire preflight enforces the same 2,000,000 node bound first and words it as a malformed-key refusal.
        XCTAssertTrue((over ?? "").contains("nested evidence limit exceeded") || (over ?? "").contains("malformed or duplicate JSON object key"), over ?? "accepted")
    }

    func testE10DocumentSizeLimit() throws {
        let value = F.makeValidV4Report()
        let limit = 16 * 1024 * 1024
        do {
            _ = try SwiftBroadFlowReport.decode(value, data: Data(count: limit + 1))
            XCTFail("Accepted a document over 16 MiB")
        } catch {
            XCTAssertTrue(reasonText(error).contains("16 MiB"), reasonText(error))
        }
        do {
            _ = try SwiftBroadFlowReport.decode(value, data: Data(count: limit))
        } catch {
            XCTAssertFalse(reasonText(error).contains("16 MiB"), reasonText(error))
        }
    }

    // MARK: E11

    func testE11GoldenReportDecodesAndMatchesExpectation() throws {
        let directory = "fixtures/swift-error-flow/broad-imports/"
        let goldenData = try Data(contentsOf: repoFile(directory + "report-v4.golden.json"))
        let expectedData = try Data(contentsOf: repoFile(directory + "expected-v4.json"))
        let golden = try XCTUnwrap(JSONSerialization.jsonObject(with: goldenData) as? [String: Any])
        let expected = try XCTUnwrap(JSONSerialization.jsonObject(with: expectedData) as? [String: Any])

        let report = try SwiftFlowReport.decode(goldenData)
        XCTAssertTrue(report.supportsInterpretation)
        XCTAssertEqual(report.modelVersion, F.model)
        XCTAssertEqual(report.calls.count, expected["calls_rows_expected"] as? Int)
        XCTAssertEqual(report.omittedCallCount, expected["omitted_calls"] as? Int)
        XCTAssertTrue(report.wordScanComplete); XCTAssertTrue(report.callDetailsComplete); XCTAssertTrue(report.witnessesComplete)

        for key in ["import_calls", "decision_by_shape", "unselected_call_counts", "omission_causes", "omitted_by_kind",
                    "observed_call_instructions", "selected_call_candidates", "omitted_calls"] {
            XCTAssertTrue(same(golden[key], expected[key]), "golden differs from the expectation at \(key)")
        }
        let goldenScan = try XCTUnwrap(golden["scan"] as? [String: Any])
        let expectedScan = try XCTUnwrap(expected["scan"] as? [String: Any])
        for (key, value) in goldenScan { XCTAssertTrue(same(value, expectedScan[key]), "scan.\(key)") }
        XCTAssertTrue(same(golden["word_scan_complete"], expectedScan["word_scan_complete"]))
        XCTAssertTrue(same(golden["scanned_words"], expectedScan["scanned_words"]))
        let goldenSummary = try XCTUnwrap(golden["decision_summary"] as? [String: Any])
        let expectedSummary = try XCTUnwrap(expected["decision_summary"] as? [String: Any])
        for (key, value) in expectedSummary where key != "undecided_by_reason_note" {
            XCTAssertTrue(same(goldenSummary[key], value), "decision_summary.\(key)")
        }

        let rows = try XCTUnwrap(golden["calls"] as? [[String: Any]])
        let expectedRows = try XCTUnwrap(expected["import_rows"] as? [[String: Any]])
        XCTAssertEqual(expectedRows.count, expected["calls_rows_import"] as? Int)
        for item in expectedRows {
            let callPC = try XCTUnwrap(item["call_pc"] as? String)
            let row = try XCTUnwrap(rows.first { $0["call_pc"] as? String == callPC }, callPC)
            let admission = try XCTUnwrap(row["admission"] as? [String: Any])
            let effect = try XCTUnwrap(row["effect_admission"] as? [String: Any])
            let test = try XCTUnwrap(row["caller_error_test"] as? [String: Any])
            XCTAssertEqual(admission["call_kind"] as? String, item["call_kind"] as? String, callPC)
            XCTAssertEqual((admission["callee_stub_pc"] as? Int).map(F.hex), item["callee_stub_pc"] as? String, callPC)
            XCTAssertEqual(admission["symbol"] as? String, item["symbol"] as? String, callPC)
            XCTAssertEqual(test["shape"] as? String, item["shape"] as? String, callPC)
            XCTAssertEqual(effect["licence_class"] as? String, item["licence_class"] as? String, callPC)
            XCTAssertEqual(effect["caller_relation"] as? String, item["caller_relation"] as? String, callPC)
            XCTAssertEqual(admission["status"] as? String, item["status"] as? String, callPC)
            XCTAssertEqual(admission["reason"] as? String, item["reason"] as? String, callPC)
            let call = try XCTUnwrap(report.calls.first { $0.callPC == callPC }, callPC)
            XCTAssertEqual(call.calleeSymbol, item["symbol"] as? String, callPC)
            XCTAssertEqual(call.status, item["status"] as? String, callPC)
            XCTAssertEqual(call.reason, item["reason"] as? String, callPC)
        }
    }

    // MARK: E12 and E13

    func testE12OlderProfilesKeepTheirBranches() throws {
        // A v3 report without v4 groups decodes under the v3 rules.
        let empty = try XCTUnwrap(accept(v3Report(), "v3 zero rows"))
        XCTAssertEqual(empty.modelVersion, "swift-broad-error-flow-extended-v3")

        // A v3 import row carries the v1 declaration and no effect admission.
        var withRow = v3Report(F.single(.throwing))
        var rows = withRow["calls"] as! [[String: Any]]
        var row = rows[0]
        row.removeValue(forKey: "effect_admission")
        var admission = row["admission"] as! [String: Any]
        admission["reason"] = "imported_callee_abi_unqualified"
        admission["declaration"] = v1Declaration()
        row["admission"] = admission
        rows[0] = row
        withRow["calls"] = rows
        withRow["reason_counts"] = ["imported_callee_abi_unqualified": 1]
        let report = try XCTUnwrap(accept(withRow, "v3 import row"))
        XCTAssertEqual(report.calls.count, 1)

        // The compact v4 record is not a v3 declaration, and an effect admission is not a v3 field.
        assertRefusedAnyway(F.changing(withRow, "calls.0.admission.declaration", F.Record.throwing.json), "compact record under v3")
        var effect: [String: Any] = [:]
        effect["model"] = F.effectModel; effect["licence_class"] = "none"; effect["caller_relation"] = "not_applicable"
        assertRefusedAnyway(F.changing(withRow, "calls.0.effect_admission", effect), "effect admission under v3")

        // Under v4 the v1 declaration is refused as a record.
        assertRefused(F.changing(F.single(.throwing), "calls.0.admission.declaration", v1Declaration()), rule: "D1", "v1 declaration under v4")
    }

    func testE13PickerListsV4AndRoutesToTheV4Branch() throws {
        let matches = SwiftFlowProfile.allCases.filter { $0.broadArgument == F.profile }
        XCTAssertEqual(matches.count, 1)
        let profile = try XCTUnwrap(matches.first)
        XCTAssertEqual(profile.broadModel, F.model)
        XCTAssertFalse(profile.title.isEmpty)
        // The other profiles keep their order and arguments.
        let others = SwiftFlowProfile.allCases.filter { $0 != profile }.map { $0.broadArgument ?? "standard" }
        XCTAssertEqual(others, ["standard", "broad-v1", "broad-large-v1", "broad-extended-v1", "broad-extended-v2",
                                "broad-extended-v3", "broad-imports-v1"])
        let options = SwiftFlowOptions(includeMethods: true, includeWitnesses: false, profile: profile)
        let arguments = options.arguments(input: URL(fileURLWithPath: "/owned/input"), output: URL(fileURLWithPath: "/owned/out"))
        let at = try XCTUnwrap(arguments.firstIndex(of: "--swift-profile"))
        XCTAssertEqual(arguments[at + 1], F.profile)

        // The router sends a v4 report to the v4 rules: a valid report decodes, a broken one is refused with a rule id.
        let good = try SwiftFlowReport.decode(serialized(F.makeValidV4Report()))
        XCTAssertTrue(good.supportsInterpretation)
        XCTAssertEqual(good.modelVersion, F.model)
        do {
            _ = try SwiftFlowReport.decode(serialized(F.changing(F.makeValidV4Report(), "capabilities", nil)))
            XCTFail("Accepted a v4 report without capabilities")
        } catch {
            XCTAssertTrue(ruleText(reasonText(error)).hasPrefix("E2:"), reasonText(error))
        }
    }
}
