public enum ReadFailure: Error { case rejected }
nonisolated(unsafe) public var shouldFail = false
nonisolated(unsafe) public var suppliedValue = 42

@inline(never)
public func read() throws -> Int {
    if shouldFail { throw ReadFailure.rejected }
    return suppliedValue
}

@inline(never)
public func handle() -> Int {
    do { return try read() }
    catch { return -1 }
}

@inline(never)
public func handleConstant() -> Int {
    do { _ = try read(); return 0 }
    catch { return -2 }
}
