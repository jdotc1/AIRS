// Owned research challenge fixtures; source alone supplies no emitted acceptance.
// Original measurement input: n, an Int supplied by the caller.
public enum SupplementalOwnedError: Error { case primary(Int), recovery(Int) }

@inline(never) public func supplementPrimary(_ n: Int) throws -> Int {
    if n < 0 { throw SupplementalOwnedError.primary(n) }
    return n &+ 1
}

@inline(never) public func supplementRecovery(_ n: Int) throws -> Int {
    if n == -7 { throw SupplementalOwnedError.recovery(n) }
    return n &- 2
}

// The second throwing call is inside the FIRST call's selected error arm.
// The inner catch handles failure of that second call, not an unrelated test.
@inline(never) public func supplementNested(_ n: Int) throws -> Int {
    do {
        _ = try supplementPrimary(n)
        fatalError("owned supplemental primary success")
    } catch {
        do {
            return try supplementRecovery(n)
        } catch {
            return 42
        }
    }
}

// Declared throwing ABI; locally converts the selected error into literal 42.
// Source alone does not establish emitted x21 clear or transport.
@inline(never) public func supplementConvertConstant(_ n: Int) throws -> Int {
    do {
        return try supplementPrimary(n)
    } catch {
        return 42
    }
}

// Separate ordinary source variant; no instruction spelling is prescribed.
@inline(never) public func supplementConvertRecovery(_ n: Int) throws -> Int {
    do {
        return try supplementRecovery(n)
    } catch {
        return 42
    }
}

// A typed source return variant preserves a distinct observable literal result.
@inline(never) public func supplementConvertNegative(_ n: Int) throws -> Int {
    do {
        return try supplementPrimary(n)
    } catch {
        return -42
    }
}
