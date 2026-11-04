public enum ReadFailure: Error { case rejected }
nonisolated(unsafe) public var shouldFail = false
nonisolated(unsafe) public var suppliedValue = 42

@inline(never)
public func readValue() throws -> Int {
    if shouldFail { throw ReadFailure.rejected }
    return suppliedValue
}

@inline(never)
public func handleIncrement() -> Int {
    do { return try readValue() &+ 5 }
    catch { return -7 }
}
