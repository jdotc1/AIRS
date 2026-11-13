import Foundation
import AIRSCore

public struct CoverageSelectionMetadata: Decodable, Sendable {
    public struct Reasons: Decodable, Sendable {
        public let requested: [String]
        public let matched: [String]
        public let unmatched: [String]
    }
    public struct Frequency: Decodable, Sendable {
        public let minimum_count: Int
        public let input_count: Int
        public let selected_count: Int
        public let omitted_count: Int
    }
    public let reason_selection: Reasons?
    public let reason_frequency_selection: Frequency?
    public let reason_order: String?
    public let reason_limit: SavedDetailLimit?

    static let keys = ["reason_selection", "reason_frequency_selection", "reason_order", "reason_limit"]
    func validate(root: CoverageJSONIdentity, rows: [CoverageInventory.Reason]) throws {
        try ProjectionAdmission.rejectNull(root, keys: Self.keys)
        if let selection = reason_selection {
            try ProjectionAdmission.keys(root["reason_selection"], required: ["requested", "matched", "unmatched"])
            try ProjectionAdmission.codes(selection.requested)
            try ProjectionAdmission.codes(selection.matched)
            try ProjectionAdmission.codes(selection.unmatched)
            guard Set(selection.matched).isDisjoint(with: selection.unmatched),
                  (selection.matched + selection.unmatched).sorted() == selection.requested,
                  rows.allSatisfy({ selection.matched.contains($0.reason) }) else { throw InspectionArchiveError.invalid }
        }
        var count = reason_selection?.matched.count
        if let frequency = reason_frequency_selection {
            try ProjectionAdmission.keys(root["reason_frequency_selection"], required: ["minimum_count", "input_count", "selected_count", "omitted_count"])
            try ProjectionAdmission.integers(root["reason_frequency_selection"], keys: ["minimum_count", "input_count", "selected_count", "omitted_count"])
            try ProjectionAdmission.stage(input: frequency.input_count, selected: frequency.selected_count, omitted: frequency.omitted_count)
            guard frequency.minimum_count > 0, count.map({ $0 == frequency.input_count }) ?? true,
                  rows.allSatisfy({ $0.count >= frequency.minimum_count }) else { throw InspectionArchiveError.invalid }
            count = frequency.selected_count
        }
        if let reason_order, reason_order != "reason" { throw InspectionArchiveError.invalid }
        if let limit = reason_limit {
            try ProjectionAdmission.keys(root["reason_limit"], required: SavedDetailLimit.keys)
            try ProjectionAdmission.integers(root["reason_limit"], keys: SavedDetailLimit.keys)
            try limit.validate(returned: rows.count, selected: count)
            count = limit.returned_count
        }
        guard count.map({ $0 == rows.count }) ?? true else { throw InspectionArchiveError.invalid }
        // Base admission is unchanged. Projections must retain the emitter's ordering.
        if Self.keys.contains(where: { root[$0] != nil }) {
            let sorted = rows.sorted {
                if reason_order == "reason" || $0.count == $1.count { return $0.reason.utf8.lexicographicallyPrecedes($1.reason.utf8) }
                return $0.count > $1.count
            }
            guard rows.map(\.id) == sorted.map(\.id) else { throw InspectionArchiveError.invalid }
        }
    }
}

public struct SavedDetailLimit: Decodable, Sendable {
    public let maximum: Int
    public let returned_count: Int
    public let omitted_count: Int
    public let selected_count: Int
    static let keys = ["maximum", "returned_count", "omitted_count", "selected_count"]
    func validate(returned: Int, selected: Int?) throws {
        try ProjectionAdmission.stage(input: selected_count, selected: returned_count, omitted: omitted_count)
        guard (0...200_000).contains(maximum), returned_count == returned,
              returned_count == min(maximum, selected_count), selected.map({ $0 == selected_count }) ?? true else {
            throw InspectionArchiveError.invalid
        }
    }
}

enum ProjectionAdmission {
    static func keys(_ value: CoverageJSONIdentity?, required: [String], optional: [String] = []) throws {
        guard case .object(let object) = value else { throw InspectionArchiveError.invalid }
        let actual = Set(object.keys), needed = Set(required.map { Data($0.utf8) })
        guard needed.isSubset(of: actual), actual.isSubset(of: needed.union(optional.map { Data($0.utf8) })) else { throw InspectionArchiveError.invalid }
    }
    static func integers(_ value: CoverageJSONIdentity?, keys: [String]) throws {
        for key in keys {
            guard case .number(let number) = value?[key], number.hasPrefix("integer:") else { throw InspectionArchiveError.invalid }
        }
    }
    static func rejectNull(_ value: CoverageJSONIdentity, keys: [String]) throws {
        guard keys.allSatisfy({ value[$0] != .null }) else { throw InspectionArchiveError.invalid }
    }
    static func codes(_ values: [String]) throws {
        if values.isEmpty { return }
        guard try SavedReportOptionValidation.reasons(values) == values else { throw InspectionArchiveError.invalid }
    }
    static func stage(input: Int, selected: Int, omitted: Int) throws {
        guard [input, selected, omitted].allSatisfy({ (0...200_000).contains($0) }), selected <= input, omitted == input - selected else { throw InspectionArchiveError.invalid }
    }
    static func same(_ a: String, _ b: String) -> Bool { a.utf8.elementsEqual(b.utf8) }
}
