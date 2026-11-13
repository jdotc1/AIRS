// Owned declarations exercising source-expressible ABI grammar families.
public enum SampleError: Error { case failed }
public protocol ValueProtocol {
    associatedtype Element
    func value(_ input: Element) -> Element
}
public protocol OtherProtocol {}
public struct Box<T> {
    public var value: T
    public init(_ value: T) { self.value = value }
    public func identity<U>(_ input: U) -> U { input }
}
public enum Choice { case first, second }
open class Base {
    public init() {}
    deinit {}
    open func method(_ input: Int) -> Int { input }
}
public final class Child: Base, OtherProtocol {}
public typealias IntegerAlias = Int

public func plain(label: Int, _ other: String) -> (count: Int, text: String) {
    (label, other)
}
public func containers(_ optional: Int?, _ array: [Int], _ dictionary: [String: Int]) -> Int? {
    optional ?? array.first ?? dictionary.values.first
}
public func metatypes(_ concrete: Int.Type, _ existential: (any ValueProtocol).Type) {}
public func existential(_ input: any ValueProtocol) {}
public func composition(_ input: any ValueProtocol & OtherProtocol) {}
public func thick(_ callback: @escaping (Int) -> Int) -> Int { callback(1) }
public func noescape(_ callback: (Int) -> Int) -> Int { callback(2) }
public func thin(_ callback: @convention(thin) (Int) -> Int) -> Int { callback(3) }
public func block(_ callback: @convention(block) (Int) -> Int) -> Int { callback(4) }
public func cFunction(_ callback: @convention(c) (Int) -> Int) -> Int { callback(5) }
public func autoclosure(_ value: @autoclosure () -> Int) -> Int { value() }
public func escapingAutoclosure(_ value: @autoclosure @escaping () -> Int) -> () -> Int { value }
public func variadic(_ values: Int...) -> Int { values.count }
public func inoutValue(_ value: inout Int) { value += 1 }
public func borrowed(_ value: borrowing Box<Int>) -> Int { value.value }
public func consumed(_ value: consuming Box<Int>) -> Int { value.value }
public func sent<T: Sendable>(_ value: sending T) -> sending T { value }
public func isolatedActor<A: Actor>(_ actor: isolated A) {}
@MainActor public func onMainActor() -> Int { 1 }
public func isolatedCallback(_ callback: @escaping @isolated(any) () -> Void) async {
    await callback()
}
public func throwing() throws -> Int { throw SampleError.failed }
public func asynchronous() async -> Int { 1 }
public func bothEffects() async throws -> Int { throw SampleError.failed }
public func typedNever() throws(Never) -> Int { 1 }
public func typedError() throws(SampleError) -> Int { throw .failed }
public func closureOnly(_ callback: () throws -> Int) -> Int { 1 }
public func rethrowing(_ callback: () throws -> Int) rethrows -> Int { try callback() }
public func opaque() -> some Equatable { 1 }
public func pack<each T>(_ value: repeat each T) -> (repeat each T) { (repeat each value) }
public func pairedPacks<each T, each U>(
    _ callback: (repeat (each T, each U)) -> Void,
    _ pairs: repeat (each T, each U)
) { callback(repeat each pairs) }
public func conformance<T: ValueProtocol>(_ value: T, _ item: T.Element) -> T.Element {
    value.value(item)
}
public func sameType<T: ValueProtocol>(_ value: T) where T.Element == Int {}
public func classLayout<T: AnyObject>(_ value: T) {}
public func baseClass<T: Base>(_ value: T) {}
public func inverse<T: ~Copyable>(_ value: borrowing T) {}
extension Box where T: Equatable {
    public func constrained(_ other: T) -> Bool { value == other }
}
extension Box {
    public func unconstrained() -> T { value }
}
extension ValueProtocol {
    public func extensionMethod(_ value: Element) -> Element { value }
}
extension ValueProtocol where Element: Equatable {
    public func equal(_ left: Element, _ right: Element) -> Bool { left == right }
}
extension Array where Element: ValueProtocol {
    public func firstOwned() -> Element? { first }
}
public struct Accessors {
    public init() {}
    public var x: Int { get throws { throw SampleError.failed } }
    public var asyncValue: Int { get async { 1 } }
    public var both: Int { get async throws { throw SampleError.failed } }
    public subscript(_ index: Int) -> Int { get throws { throw SampleError.failed } }
    public var stored: Int = 0 { willSet {} didSet {} }
    public var readModify: Int {
        _read { yield stored }
        _modify { yield &stored }
    }
}
public func outer(_ input: Int) -> Int {
    func local(_ value: Int) -> Int { value + 1 }
    return local(input)
}
private func hidden(_ value: Int) -> Int { value }
public func useHidden(_ value: Int) -> Int { hidden(value) }
public func café(_ value: Int) -> Int { value }
public struct OperatorValue {
    public let value: Int
    public init(_ value: Int) { self.value = value }
    public static prefix func + (value: Self) -> Self { value }
    public static func + (left: Self, right: Self) -> Self { Self(left.value + right.value) }
}
postfix operator +++
public postfix func +++ (value: OperatorValue) -> OperatorValue { value }
