public enum Failure: Error { case rejected }
@inline(never) public func ordinary(_ x: Int) -> Int { x &+ 1 }
@inline(never) public func freeInt(_ x: Int) throws -> Int { if x < 0 { throw Failure.rejected }; return x &+ 1 }
@inline(never) public func freeVoid(_ x: Int) throws { if x < 0 { throw Failure.rejected } }
@inline(never) public func freeNoArg() throws -> Int { 4 }
@inline(never) public func freeEmpty() throws { }
public struct Counter {
 public let base: Int
 public init(_ base: Int) { self.base = base }
 @inline(never) public func parse(_ x: Int) throws -> Int { if x < 0 { throw Failure.rejected }; return x &+ base }
 @inline(never) public func store(_ x: Int) throws { if x < base { throw Failure.rejected } }
 @inline(never) public func read() throws -> Int { if base < 0 { throw Failure.rejected }; return base }
 @inline(never) public func generic<T>(_ x: T) throws -> T { x }
 @inline(never) public func asynchronous() async throws -> Int { base }
 @inline(never) public static func staticMethod(_ x: Int) throws -> Int { x }
 public struct Nested { @inline(never) public func parse(_ x: Int) throws -> Int { x } }
}
public struct GenericBox<T> { @inline(never) public func parse(_ x: Int) throws -> Int { x } }
public protocol Reading { func read() throws -> Int }
extension Counter: Reading { }
@inline(never) public func witness(_ value: any Reading) throws -> Int { try value.read() }
open class Base { public init() {} ; @inline(never) open func read() throws -> Int { 1 } }
@inline(never) public func virtual(_ value: Base) throws -> Int { try value.read() }
@inline(never) public func handle(_ value: Counter, _ x: Int) -> Int { do { return try value.parse(x) } catch { return -1 } }
@inline(never) public func multiple(_ value: Counter, _ x: Int) -> Int { do { return try value.parse(x) } catch { do { return try value.read() } catch { return -2 } } }
#if compiler(>=6.0)
@inline(never) public func typed(_ x: Int) throws(Failure) -> Int { if x < 0 { throw .rejected }; return x }
#endif
