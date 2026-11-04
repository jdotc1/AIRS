public enum ValidationFailure: Error { case rejected }
@inline(never) public func validate(_ value: Int) throws {
    if value < 0 { throw ValidationFailure.rejected }
}
@inline(never) public func handle(_ value: Int) -> Int {
    do { try validate(value); return 0 } catch { return -1 }
}
