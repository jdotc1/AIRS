public enum ValidationFailure: Error { case rejected }
nonisolated(unsafe) public var shouldFail = false

@inline(never)
public func validate() throws {
    if shouldFail { throw ValidationFailure.rejected }
}
