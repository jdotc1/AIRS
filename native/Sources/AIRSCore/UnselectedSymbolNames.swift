import Foundation

public extension ComparisonReport {
    /// Binds unselected symbol-group labels after source membership validation.
    /// Unselected exact-offset representative labels retain their existing scope.
    func validateUnselectedSymbolNames(baselineData: Data, currentData: Data) throws {
        try validateSelectedFunctionNames(baselineData: baselineData, currentData: currentData)
        let prefix = Data("symbol:".utf8)
        for row in changes where row.matchBasis == "unique_symbol"
            && row.baselineID == nil && row.currentID == nil {
            let key = Data(row.key.utf8)
            guard key.starts(with: prefix),
                  row.functionName.utf8.elementsEqual(key.dropFirst(prefix.count)) else {
                throw ReportError.invalidContents("Comparison function label contradicts its unselected source-name group.")
            }
        }
    }
}
