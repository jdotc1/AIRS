import Foundation
import EntitlementDiffCore

/// Integer tags describe captured representations, not the source language.
public indirect enum SecurityDeltaValue: Codable, Sendable {
    case boolean(Bool)
    case signed(Int64)
    case unsigned(UInt64)
    case normalizedInteger(String)
    case realBits(UInt64)
    case string(String)
    case data(Data)
    case dateBits(UInt64)
    case array([SecurityDeltaValue])
    case dictionary([SecurityDeltaValueEntry])

    private enum Key: String, CodingKey { case type, value }
    public init(from decoder: Decoder) throws {
        let c = try decoder.container(keyedBy: Key.self)
        let type = try c.decode(String.self, forKey: .type)
        switch type {
        case "boolean": self = .boolean(try c.decode(Bool.self, forKey: .value))
        case "signed":
            let text = try c.decode(String.self, forKey: .value)
            guard let value = Int64(text), String(value) == text else { throw InspectionArchiveError.invalid }
            self = .signed(value)
        case "unsigned":
            let text = try c.decode(String.self, forKey: .value)
            guard let value = UInt64(text), String(value) == text else { throw InspectionArchiveError.invalid }
            self = .unsigned(value)
        case "normalizedInteger": self = .normalizedInteger(try c.decode(String.self, forKey: .value))
        case "realBits", "dateBits":
            let text = try c.decode(String.self, forKey: .value)
            guard text.utf8.count == 16, let bits = UInt64(text, radix: 16), String(format: "%016llx", bits) == text else { throw InspectionArchiveError.invalid }
            self = type == "realBits" ? .realBits(bits) : .dateBits(bits)
        case "string": self = .string(try c.decode(String.self, forKey: .value))
        case "data": self = .data(try c.decode(Data.self, forKey: .value))
        case "array": self = .array(try c.decode([Self].self, forKey: .value))
        case "dictionary": self = .dictionary(try c.decode([SecurityDeltaValueEntry].self, forKey: .value))
        default: throw InspectionArchiveError.invalid
        }
    }

    public func encode(to encoder: Encoder) throws {
        var c = encoder.container(keyedBy: Key.self)
        switch self {
        case .boolean(let v): try c.encode("boolean", forKey: .type); try c.encode(v, forKey: .value)
        case .signed(let v): try c.encode("signed", forKey: .type); try c.encode(String(v), forKey: .value)
        case .unsigned(let v): try c.encode("unsigned", forKey: .type); try c.encode(String(v), forKey: .value)
        case .normalizedInteger(let v): try c.encode("normalizedInteger", forKey: .type); try c.encode(v, forKey: .value)
        case .realBits(let v): try c.encode("realBits", forKey: .type); try c.encode(String(format: "%016llx", v), forKey: .value)
        case .dateBits(let v): try c.encode("dateBits", forKey: .type); try c.encode(String(format: "%016llx", v), forKey: .value)
        case .string(let v): try c.encode("string", forKey: .type); try c.encode(v, forKey: .value)
        case .data(let v): try c.encode("data", forKey: .type); try c.encode(v, forKey: .value)
        case .array(let v): try c.encode("array", forKey: .type); try c.encode(v, forKey: .value)
        case .dictionary(let v): try c.encode("dictionary", forKey: .type); try c.encode(v, forKey: .value)
        }
    }

    /// Convert a previously captured EntitlementDiff tree without using its
    /// numeric equality, which intentionally equates some signed/unsigned values.
    public static func from(_ value: EntitlementValue, normalizedIntegers: Bool,
                            maxDepth: Int = 32, maxNodes: Int = 10_000, maxBytes: Int = 65_536) throws -> Self {
        guard (0...32).contains(maxDepth), (1...100_000).contains(maxNodes), (0...8 * 1_048_576).contains(maxBytes) else { throw InspectionArchiveError.invalid }
        var nodes = maxNodes, bytes = maxBytes
        func charge(_ count: Int) throws {
            guard count >= 0, count <= bytes else { throw SecurityDeltaRefusal(.decodedByteLimit) }
            bytes -= count
        }
        func convert(_ value: EntitlementValue, _ depth: Int) throws -> Self {
        guard depth <= maxDepth else { throw SecurityDeltaRefusal(.typedDepthLimit) }
        guard nodes > 0 else { throw SecurityDeltaRefusal(.typedNodeLimit) }
        nodes -= 1
        switch value {
        case .boolean(let v): try charge(1); return .boolean(v)
        case .integer(let v): try charge(normalizedIntegers ? String(v).utf8.count : 8); return normalizedIntegers ? .normalizedInteger(String(v)) : .signed(v)
        case .unsignedInteger(let v): try charge(normalizedIntegers ? String(v).utf8.count : 8); return normalizedIntegers ? .normalizedInteger(String(v)) : .unsigned(v)
        case .real(let v):
            guard v.isFinite else { throw InspectionArchiveError.invalid }
            try charge(8); return .realBits(v.bitPattern)
        case .string(let v): try charge(v.utf8.count); return .string(v)
        case .data(let v): try charge(v.count); return .data(v)
        case .date(let v):
            let seconds = v.timeIntervalSinceReferenceDate
            guard seconds.isFinite else { throw InspectionArchiveError.invalid }
            try charge(8); return .dateBits(seconds.bitPattern)
        case .array(let v):
            guard v.count <= nodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
            return .array(try v.map { try convert($0, depth + 1) })
        case .dictionary(let v):
            guard v.entries.count <= nodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
            return .dictionary(try v.entries.map { entry in
                try charge(entry.key.utf8.count)
                return .init(key: entry.key, value: try convert(entry.value, depth + 1))
            })
        }
        }
        return try convert(value, 0)
    }

    /// Validate after bounded decoding and before a value is admitted or used.
    public func validate(maxDepth: Int = 32, maxNodes: Int = 10_000, maxBytes: Int = 65_536) throws {
        guard (0...32).contains(maxDepth), (1...100_000).contains(maxNodes), (0...8 * 1_048_576).contains(maxBytes) else { throw InspectionArchiveError.invalid }
        var nodes = maxNodes, bytes = maxBytes
        func consume(_ count: Int) throws {
            guard count >= 0, count <= bytes else { throw SecurityDeltaRefusal(.decodedByteLimit) }
            bytes -= count
        }
        func visit(_ value: Self, _ depth: Int) throws {
            guard depth <= maxDepth else { throw SecurityDeltaRefusal(.typedDepthLimit) }
            guard nodes > 0 else { throw SecurityDeltaRefusal(.typedNodeLimit) }
            nodes -= 1
            switch value {
            case .boolean: try consume(1)
            case .signed, .unsigned: try consume(8)
            case .realBits(let bits), .dateBits(let bits):
                guard Double(bitPattern: bits).isFinite else { throw InspectionArchiveError.invalid }
                try consume(8)
            case .normalizedInteger(let value):
                guard value == "0" || (value.first != "+" && value.first != "0" && value != "-0" &&
                    ((Int64(value).map(String.init) == value) || (UInt64(value).map(String.init) == value))) else {
                    throw InspectionArchiveError.invalid
                }
                try consume(value.utf8.count)
            case .string(let value): try consume(value.utf8.count)
            case .data(let value): try consume(value.count)
            case .array(let values):
                guard values.count <= nodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
                for item in values { try visit(item, depth + 1) }
            case .dictionary(let entries):
                guard entries.count <= nodes else { throw SecurityDeltaRefusal(.typedNodeLimit) }
                var previous: Data?
                for entry in entries {
                    let key = Data(entry.key.utf8)
                    if let previous, !previous.lexicographicallyPrecedes(key) { throw InspectionArchiveError.invalid }
                    previous = key
                    try consume(key.count)
                    try visit(entry.value, depth + 1)
                }
            }
        }
        try visit(self, 0)
    }
}

public struct SecurityDeltaValueEntry: Codable, Sendable {
    public let key: String
    public let value: SecurityDeltaValue
    public init(key: String, value: SecurityDeltaValue) { self.key = key; self.value = value }
}

public enum SecurityDeltaValueComparison: String, Codable, Sendable {
    case equal, different, representationUnresolved
}

extension SecurityDeltaValue {
    /// Exact string/key bytes and numeric tags are used throughout. A legacy
    /// normalized integer can establish a numeric difference, but cannot prove
    /// that an equal explicitly tagged integer had the same representation.
    public func compare(to other: Self) throws -> SecurityDeltaValueComparison {
        try validate(maxNodes: 100_000, maxBytes: 8 * 1_048_576)
        try other.validate(maxNodes: 100_000, maxBytes: 8 * 1_048_576)
        return compareValidated(to: other)
    }

    private func compareValidated(to other: Self) -> SecurityDeltaValueComparison {
        func combine(_ lhs: SecurityDeltaValueComparison, _ rhs: SecurityDeltaValueComparison) -> SecurityDeltaValueComparison {
            if lhs == .different || rhs == .different { return .different }
            if lhs == .representationUnresolved || rhs == .representationUnresolved { return .representationUnresolved }
            return .equal
        }
        func compareSequence<T>(_ lhs: [T], _ rhs: [T], _ item: (T, T) -> SecurityDeltaValueComparison) -> SecurityDeltaValueComparison {
            guard lhs.count == rhs.count else { return .different }
            return zip(lhs, rhs).reduce(.equal) { combine($0, item($1.0, $1.1)) }
        }
        switch (self, other) {
        case let (.boolean(a), .boolean(b)): return a == b ? .equal : .different
        case let (.signed(a), .signed(b)): return a == b ? .equal : .different
        case let (.unsigned(a), .unsigned(b)): return a == b ? .equal : .different
        case let (.normalizedInteger(a), .normalizedInteger(b)):
            return a.utf8.elementsEqual(b.utf8) ? .representationUnresolved : .different
        case let (.normalizedInteger(a), .signed(b)), let (.signed(b), .normalizedInteger(a)):
            return a.utf8.elementsEqual(String(b).utf8) ? .representationUnresolved : .different
        case let (.normalizedInteger(a), .unsigned(b)), let (.unsigned(b), .normalizedInteger(a)):
            return a.utf8.elementsEqual(String(b).utf8) ? .representationUnresolved : .different
        case let (.realBits(a), .realBits(b)), let (.dateBits(a), .dateBits(b)):
            return a == b ? .equal : .different
        case let (.string(a), .string(b)): return a.utf8.elementsEqual(b.utf8) ? .equal : .different
        case let (.data(a), .data(b)): return a == b ? .equal : .different
        case let (.array(a), .array(b)): return compareSequence(a, b) { $0.compareValidated(to: $1) }
        case let (.dictionary(a), .dictionary(b)):
            return compareSequence(a, b) { left, right in
                guard left.key.utf8.elementsEqual(right.key.utf8) else { return .different }
                return left.value.compareValidated(to: right.value)
            }
        default: return .different
        }
    }
}
