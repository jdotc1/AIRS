public enum ValidationFailure: Error { case rejected }
nonisolated(unsafe) public var shouldFail = false

@inline(never)
public func validate() throws {
    if shouldFail { throw ValidationFailure.rejected }
}

@inline(never)
public func handleWords() -> Int {
    do { try validate(); return 0x89abcdef }
    catch { return 0x12345678 }
}

@inline(never)
public func handleWidth() -> Int {
    do { try validate(); return 0xffffffff }
    catch { return -1 }
}
