// Owned native broad-profile integration probe. Inspect the compiled image as data only.
public enum NativeBroadProbeFailure: Error { case negative }
@inline(never) public func nativeBroadProbeCallee(_ value: Int) throws -> Int {
    if value < 0 { throw NativeBroadProbeFailure.negative }
    return value &+ 3
}
@inline(never) public func nativeBroadProbeCaller(_ value: Int) -> Int {
    do { return try nativeBroadProbeCallee(value) }
    catch { return -11 }
}
