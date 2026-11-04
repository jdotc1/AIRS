import Foundation
import EntitlementDiffCore

/// Static declaration comparison. It does not resolve paths or load libraries.
enum ComponentSecurityDeltaLoader {
    struct Change {
        let command: String
        let path: String
        let previousCount: Int
        let currentCount: Int
    }
    private struct Key: Hashable {
        let command: Data
        let path: Data
    }
    private struct Group {
        let command: String
        let path: String
        var rows: [Data]
    }
    static func changes(previous: EntitlementDictionary, current: EntitlementDictionary, architecture: String) throws -> [Change] {
        let encoder = JSONEncoder(); encoder.outputFormatting = [.sortedKeys, .withoutEscapingSlashes]
        var encodedBytesRemaining = 16 * 1_048_576
        func versionIsCanonical(_ text: String) -> Bool {
            let parts = text.split(separator: ".", omittingEmptySubsequences: false)
            guard parts.count == 3 else { return false }
            let maxima = [UInt32(65_535), 255, 255]
            return zip(parts, maxima).allSatisfy { part, maximum in
                guard let n = UInt32(part), n <= maximum else { return false }
                return String(n).utf8.elementsEqual(part.utf8)
            }
        }
        func groups(_ dictionary: EntitlementDictionary) throws -> [Key: Group] {
            _ = try SecurityDeltaValue.from(.dictionary(dictionary), normalizedIntegers: true)
            guard case .array(let rows)? = dictionary["commands"], rows.count <= 4096 else { throw InspectionArchiveError.invalid }
            var result: [Key: Group] = [:]
            for row in rows {
                try Task.checkCancellation()
                guard case .dictionary(let fields) = row,
                      case .string(let command)? = fields["command"],
                      case .string(let path)? = fields["path"], !path.isEmpty, path.utf8.count <= 4096,
                      case .string(let slice)? = fields["architecture"], slice.utf8.elementsEqual(architecture.utf8),
                      ["load", "weak", "reexport", "upward", "lazy", "installName", "rpath"].contains(where: { $0.utf8.elementsEqual(command.utf8) }) else {
                    throw InspectionArchiveError.invalid
                }
                let allowed = ["architecture", "command", "path", "currentVersion", "compatibilityVersion", "useFlags"]
                guard fields.entries.allSatisfy({ entry in allowed.contains { $0.utf8.elementsEqual(entry.key.utf8) } }) else { throw InspectionArchiveError.invalid }
                for name in ["currentVersion", "compatibilityVersion"] {
                    if let value = fields[name] {
                        guard !command.utf8.elementsEqual("rpath".utf8), case .string(let text) = value,
                              versionIsCanonical(text) else { throw InspectionArchiveError.invalid }
                    }
                }
                if let flags = fields["useFlags"] {
                    guard ["load", "weak"].contains(where: { $0.utf8.elementsEqual(command.utf8) }) else { throw InspectionArchiveError.invalid }
                    switch flags {
                    case .integer(let value): guard value >= 0, value <= Int64(UInt32.max) else { throw InspectionArchiveError.invalid }
                    case .unsignedInteger(let value): guard value <= UInt64(UInt32.max) else { throw InspectionArchiveError.invalid }
                    default: throw InspectionArchiveError.invalid
                    }
                }
                if command.utf8.elementsEqual("installName".utf8) || command.utf8.elementsEqual("rpath".utf8) { continue }
                let key = Key(command: Data(command.utf8), path: Data(path.utf8))
                let encoded = try encoder.encode(SecurityDeltaValue.from(row, normalizedIntegers: true))
                guard encoded.count <= encodedBytesRemaining else { throw InspectionArchiveError.limit }
                encodedBytesRemaining -= encoded.count
                if result[key] == nil { result[key] = Group(command: command, path: path, rows: []) }
                result[key]?.rows.append(encoded)
            }
            return result
        }
        let a = try groups(previous), b = try groups(current)
        try Task.checkCancellation()
        let keys = Set(a.keys).union(b.keys).sorted { x, y in
            if x.command != y.command { return x.command.lexicographicallyPrecedes(y.command) }
            return x.path.lexicographicallyPrecedes(y.path)
        }
        return keys.compactMap { key in
            let old = (a[key]?.rows ?? []).sorted { $0.lexicographicallyPrecedes($1) }
            let new = (b[key]?.rows ?? []).sorted { $0.lexicographicallyPrecedes($1) }
            guard old != new, let item = a[key] ?? b[key] else { return nil }
            return Change(command: item.command, path: item.path, previousCount: old.count, currentCount: new.count)
        }
    }
}
