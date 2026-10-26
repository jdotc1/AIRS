public enum OwnedFailure: Error { case rejected }
@inline(never) public func parse(_ value: Int) throws -> Int {
    if value < 0 { throw OwnedFailure.rejected }
    return value &+ 1
}
@inline(never) public func handle(_ value: Int) -> Int {
    do { return try parse(value) } catch { return -1 }
}
