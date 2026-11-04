import Foundation

public extension ComparisonReport {
    /// Checks recorded row accounting only, not source coverage or matching truth.
    /// Explicit opt-in keeps legacy decoding and app workflows unchanged.
    func validateRowAccounting() throws {
        guard changes.count <= 100_000 else {
            throw ReportError.invalidContents("Comparison row limit of 100,000 exceeded.")
        }
        var keys = Set<Data>(), oldIDs = Set<String>(), newIDs = Set<String>()
        var matched = 0, changed = 0, unchanged = 0, added = 0, removed = 0, ambiguous = 0
        for row in changes {
            guard !row.key.isEmpty, keys.insert(Data(row.key.utf8)).inserted else {
                throw ReportError.invalidContents("Comparison row keys must be nonempty and unique.")
            }
            let before = try accountEndpoint(row.baselineID, verdict: row.beforeVerdict, scope: row.beforeScope, seen: &oldIDs)
            let after = try accountEndpoint(row.currentID, verdict: row.afterVerdict, scope: row.afterScope, seen: &newIDs)
            switch row.change {
            case "changed", "unchanged":
                guard before && after else {
                    throw ReportError.invalidContents("Changed and unchanged rows require both selected endpoints.")
                }
                if row.change == "changed" { changed += 1 } else { unchanged += 1 }
            case "added":
                guard !before && after else {
                    throw ReportError.invalidContents("An added row requires only a current endpoint.")
                }
                added += 1
            case "removed":
                guard before && !after else {
                    throw ReportError.invalidContents("A removed row requires only a baseline endpoint.")
                }
                removed += 1
            case "ambiguous":
                // Duplicate candidate groups may expose zero or one selected
                // endpoint; only a selected pair contributes a matched count.
                ambiguous += 1
            default:
                throw ReportError.invalidContents("Unknown comparison change category cannot be counted.")
            }
            if before && after { matched += 1 }
        }
        // Compare each count directly. Never sum untrusted declared Int values.
        let observed = [matched, changed, unchanged, added, removed, ambiguous]
        let declared = [summary.matchedCount, summary.changedCount, summary.unchangedCount,
                        summary.addedCount, summary.removedCount, summary.ambiguousCount]
        guard declared == observed else {
            throw ReportError.invalidContents("Comparison summary counts do not match the recorded rows.")
        }
    }
}

private func accountEndpoint(_ id: String?, verdict: AuditVerdict?, scope: String?, seen: inout Set<String>) throws -> Bool {
    guard let id else {
        guard verdict == nil && scope == nil else {
            throw ReportError.invalidContents("Comparison facts cannot name an absent endpoint.")
        }
        return false
    }
    let suffix = id.dropFirst("airsf-".count)
    guard id.hasPrefix("airsf-"), suffix.utf8.count == 64,
          suffix.utf8.allSatisfy({ (48...57).contains($0) || (97...102).contains($0) }),
          seen.insert(id).inserted else {
        throw ReportError.invalidContents("Comparison endpoints require unique AIRS identifiers on each side.")
    }
    guard verdict != nil, let scope, !scope.isEmpty else {
        throw ReportError.invalidContents("A selected comparison endpoint requires verdict and scope facts.")
    }
    return true
}
