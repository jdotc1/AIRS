import Foundation

public extension ComparisonReport {
    /// Checks producer key order without sorting or claiming complete output.
    func validateCanonicalRowOrder(baselineData: Data, currentData: Data) throws {
        try validateUnselectedOffsetNames(baselineData: baselineData, currentData: currentData)
        for index in changes.indices.dropFirst() {
            // UTF-8 lexical order preserves Unicode scalar order. String ordering
            // can erase distinctions between canonically equivalent spellings.
            guard changes[index - 1].key.utf8.lexicographicallyPrecedes(changes[index].key.utf8) else {
                throw ReportError.invalidContents("Comparison rows are not in canonical key order.")
            }
        }
    }
}
