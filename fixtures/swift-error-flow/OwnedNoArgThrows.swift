public enum ValidationFailure: Error { case rejected }
nonisolated(unsafe) public var shouldFail = false

@inline(never)
public func validate() throws {
    if shouldFail { throw ValidationFailure.rejected }
}

@inline(never)
public func handle() -> Int {
    do {
        try validate()
        return 0
    } catch {
        return -1
    }
}
