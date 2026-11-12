// AIRS imported-decl-coverage oracle. Public declarations only; never executed. Unique token Qnnn per declaration.
// Truth is the trailing comment: <shape> [throws|rethrows] [async] [typed] (absent = no). Container types: type.
public enum HelperErrQ900: Error {  // type
    case bad
}
public protocol HelperProtoQ901 {}  // type
public struct HelperValQ902 {}  // type
public class HelperObjQ903 {}  // type
public struct StructPlainQ001 {}  // type
public struct StructStoredQ002 {  // type
    public var storedVarQ003: Int  // stored_property
    public let storedLetQ004: Int  // stored_property
}
public struct StructGenericQ005<T> {  // type
    public var genericStoredQ006: T  // stored_property
}
public class ClassPlainQ007 {}  // type
public class ClassSubQ008: ClassPlainQ007 {}  // type
public final class ClassFinalQ009 {  // type
    public var finalVarQ010: Int = 0  // stored_property
}
public class ClassGenericQ011<T> {}  // type
public enum EnumPlainQ012 {  // type
    case a
    case b
}
public enum EnumPayloadQ013 {  // type
    case i(Int)
    case s(String)
}
public indirect enum EnumIndirectQ014 {  // type
    case leaf
    case node(EnumIndirectQ014)
}
public enum EnumGenericQ015<T> {  // type
    case some(T)
    case none
}
public enum EnumRawQ016: Int {  // type
    case zero = 0
}
public enum EnumNoCaseQ017 {}  // type
public actor ActorPlainQ018 {}  // type
public protocol ProtoPlainQ019 {}  // type
public struct PropHostQ020 {  // type
    public var getterOnlyQ021: Int { 1 }  // property
    public static var staticGetQ022: Int { 2 }  // static_property
    public var getSetQ023: Int {  // property
        get { 1 }
        set {}
    }
    public static var staticGetSetQ024: Int {  // static_property
        get { 1 }
        set {}
    }
    public var observedQ025: Int = 0 { didSet {} }  // stored_property
    public var willObservedQ026: Int = 0 { willSet {} }  // stored_property
    public var modifyQ027: Int {  // property
        get { 1 }
        set {}
        _modify { var x = 1; yield &x }
    }
    public var readQ028: Int {  // property
        _read { yield 1 }
    }
    public var closureThrowsQ029: () throws -> Void = {}  // stored_property
    public var closureAsyncQ030: () async -> Void = {}  // stored_property
    public var closureOptQ031: (() throws -> Int)? = nil  // stored_property
    public static var staticStoredQ032 = 1  // static_stored_property
    public static let staticLetQ033 = 1  // static_stored_property
}
public var globalVarQ034: Int = 2  // global_variable
public let globalLetQ035 = "s"  // global_variable
public var globalComputedQ036: Int { 1 }  // global_property
public var globalGetThrowsQ037: Int { get throws { 1 } }  // global_property throws
public var globalGetAsyncQ038: Int { get async { 1 } }  // global_property async
public var globalGetAsyncThrowsQ039: Int { get async throws { 1 } }  // global_property throws async
extension String {
    public var extStringGetQ040: Int { 1 }  // property
    public static var extStringStaticQ041: Int { 2 }  // static_property
    public func extStringFnQ042() {}  // method
    public func extStringThrowsQ043() throws {}  // method throws
    public mutating func extStringMutQ044() {}  // mutating_method
    public var extStringGetThrowsQ045: Int { get throws { 1 } }  // property throws
    public var extStringGetAsyncQ046: Int { get async { 1 } }  // property async
    public func extStringAsyncQ047() async {}  // method async
}
extension Array {
    public var extArrayGetQ050: Int { 1 }  // property
    public func extArrayThrowsQ051() throws {}  // method throws
    public static var extArrayStaticQ052: Int { 1 }  // static_property
    public mutating func extArrayMutThrowsQ053() throws {}  // mutating_method throws
}
extension Array where Element: Equatable {
    public func extArrayEquatableQ054() {}  // method
    public func extArrayEquatableThrowsQ055() throws {}  // method throws
}
extension Int {
    public var extIntGetQ056: Int { 1 }  // property
    public static func extIntStaticFnQ057() {}  // static_method
    public init(Q058 x: String) throws { self = 0 }  // init throws
    public init?(Q059 x: Double) { self = 0 }  // init_failable
    public func extIntRethrowsQ060(_ f: () throws -> Void) rethrows { try f() }  // method rethrows
}
extension Optional {
    public func extOptionalThrowsQ061() throws {}  // method throws
}
public protocol ProtoReqQ062 {  // type
    func reqPlainQ063()  // requirement
    func reqThrowsQ064() throws  // requirement throws
    func reqAsyncQ065() async  // requirement async
    func reqAsyncThrowsQ066() async throws  // requirement throws async
    var reqGetQ067: Int { get }  // requirement_property
    var reqGetSetQ068: Int { get set }  // requirement_property
    var reqGetThrowsQ069: Int { get throws }  // requirement_property throws
    var reqGetAsyncQ070: Int { get async }  // requirement_property async
    var reqGetAsyncThrowsQ071: Int { get async throws }  // requirement_property throws async
    init(Q072 x: Int) throws  // requirement throws
    static func reqStaticQ073() throws  // requirement throws
    static var reqStaticGetQ074: Int { get throws }  // requirement_property throws
    subscript(Q075 i: Int) -> Int { get throws }  // requirement_subscript throws
    func reqRethrowsQ076(_ f: () throws -> Void) rethrows  // requirement rethrows
    func reqTypedQ077() throws(HelperErrQ900)  // requirement throws typed
}
extension ProtoReqQ062 {
    public func protoExtFnQ078() {}  // method
    public func protoExtThrowsQ079() throws {}  // method throws
    public func protoExtAsyncQ080() async {}  // method async
    public var protoExtGetQ081: Int { 1 }  // property
    public var protoExtGetThrowsQ082: Int { get throws { 1 } }  // property throws
    public static var protoExtStaticGetQ083: Int { 1 }  // static_property
    public static func protoExtStaticFnQ084() throws {}  // static_method throws
    public func protoExtRethrowsQ085(_ f: () throws -> Void) rethrows { try f() }  // method rethrows
    public func protoExtGenericQ086<T: HelperProtoQ901>(_ t: T) throws {}  // method throws
    public subscript(protoExtQ087 i: Int) -> Int { 1 }  // subscript
}
public struct InitNoArgQ090 {  // type
    public init() {}  // init
}
public struct InitNoArgThrowsQ091 {  // type
    public init() throws {}  // init throws
}
public class InitNoArgClassQ092 {  // type
    public init() {}  // init
}
public class InitNoArgThrowsClassQ093 {  // type
    public init() throws {}  // init throws
}
public struct InitStructQ094 {  // type
    public init(Q095 a: Int) {}  // init
    public init(Q096 a: Int) throws {}  // init throws
    public init?(Q097 a: Int) {}  // init_failable
    public init?(Q098 a: Int) throws {}  // init_failable throws
    public init(Q099 a: Int) async {}  // init async
    public init(Q100 a: Int) async throws {}  // init throws async
    public init<T>(Q101 a: T) {}  // init
    public init(Q102 a: Int) throws(HelperErrQ900) {}  // init throws typed
    public init(Q103 a: Int = 0, b: String = "") {}  // init
    public init(Q104 a: Int...) {}  // init
}
public class InitClassQ105 {  // type
    public init(Q106 a: Int) {}  // init
    public init(Q107 a: Int) throws {}  // init throws
    public init?(Q108 a: Int) {}  // init_failable
    public init?(Q109 a: Int) throws {}  // init_failable throws
    public convenience init(Q110 a: String) { self.init(Q106: 1) }  // convenience_init
    public convenience init(Q111 a: String) throws { try self.init(Q107: 1) }  // convenience_init throws
    public convenience init?(Q112 a: String) { self.init(Q106: 1) }  // convenience_init_failable
    public required init(Q113 a: Double) {}  // required_init
    public required init(Q114 a: Float) throws {}  // required_init throws
    public init(Q115 a: Int) async {}  // init async
    public init(Q116 a: Int) async throws {}  // init throws async
    public convenience init(Q117 a: Int) async throws { try await self.init(Q116: 1) }  // convenience_init throws async
}
public class InitSubClassQ118: InitClassQ105 {  // type
    public convenience init(Q119 b: Int) { self.init(Q106: b) }  // convenience_init
}
public enum InitEnumQ122 {  // type
    case a
    public init(Q123 x: Int) { self = .a }  // init
    public init(Q124 x: String) throws { self = .a }  // init throws
}
public func freePlainQ130() {}  // free_function
public func freeThrowsQ131() throws {}  // free_function throws
public func freeAsyncQ132() async {}  // free_function async
public func freeAsyncThrowsQ133() async throws {}  // free_function throws async
public func freeParamsQ134(_ a: Int, _ b: String) -> Int { 0 }  // free_function
public func freeThrowsParamsQ135(_ a: Int) throws -> String { "" }  // free_function throws
public func freeVariadicAnyQ136(_ items: Any...) {}  // free_function
public func freeVariadicAnyThrowsQ137(_ items: Any...) throws {}  // free_function throws
public func freeVariadicIntQ138(_ items: Int...) {}  // free_function
public func freeLabelledQ139(first a: Int, second b: Int) {}  // free_function
public func freeDefaultsQ140(_ a: Int = 1, b: String = "x") {}  // free_function
public func freeDefaultsThrowsQ141(_ a: Int = 1) throws {}  // free_function throws
public func freeInoutQ142(_ a: inout Int) {}  // free_function
public func freeReturnsThrowingClosureQ143() -> () throws -> Void { {} }  // free_function
public func freeReturnsAsyncClosureQ144() -> () async -> Void { {} }  // free_function
public func freeReturnsTupleQ145() -> (Int, String) { (0, "") }  // free_function
public func freeGenericQ146<T>(_ a: T) {}  // free_function
public func freeGenericThrowsQ147<T>(_ a: T) throws {}  // free_function throws
public func freeGenericReqQ148<T: HelperProtoQ901>(_ a: T) {}  // free_function
public func freeGenericWhereQ149<T, U>(_ a: T, _ b: U) where T: Equatable, U: Collection, U.Element == T {}  // free_function
public func freeGenericReqThrowsQ150<T: HelperProtoQ901 & Equatable>(_ a: T) throws {}  // free_function throws
public func freeGenericAsyncQ151<T: Sendable>(_ a: T) async {}  // free_function async
public func freeOptionalQ152(_ a: Int?) -> Int? { a }  // free_function
public func freeNeverQ153() -> Never { fatalError() }  // free_function
public func freeNeverThrowsQ154() throws -> Never { throw HelperErrQ900.bad }  // free_function throws
@MainActor public func freeMainActorQ155() {}  // free_function
public func freeSendableParamQ156(_ f: @Sendable () -> Void) {}  // free_function
public func freeOpaqueQ157() -> some Equatable { 1 }  // free_function
public func freeExistentialQ158(_ p: any HelperProtoQ901) {}  // free_function
public func freeThrowsTupleQ159() throws -> (Int, Int) { (0, 0) }  // free_function throws
public func freeThrowsVariadicTrailQ160(a: Int, _ rest: Int...) throws {}  // free_function throws
public func freeConsumingParamQ161(_ a: consuming HelperValQ902) {}  // free_function
public func freeBorrowingParamQ162(_ a: borrowing HelperValQ902) {}  // free_function
public func freeIsolatedParamQ163(_ a: isolated ActorPlainQ018) {}  // free_function
public func freeResultReturnQ164() -> Result<Int, HelperErrQ900> { .success(1) }  // free_function
public func freeTakesErrorQ165(_ e: any Error) {}  // free_function
public func freeThrowsOptionalQ166() throws -> Int? { nil }  // free_function throws
public func freeAsyncReturnsQ167() async -> Int { 1 }  // free_function async
@inlinable public func freeInlinableThrowsQ168() throws {}  // free_function throws
@discardableResult public func freeDiscardableQ169() -> Int { 1 }  // free_function
public func freeDefaultClosureQ170(_ f: () -> Void = {}) {}  // free_function
public func freeDefaultThrowsClosureQ171(_ f: () throws -> Void = {}) throws {}  // free_function throws
@concurrent public func freeConcurrentQ172() async {}  // free_function async
nonisolated(nonsending) public func freeNonsendingQ173() async {}  // free_function async
public struct MethodStructQ180 {  // type
    public func instancePlainQ181() {}  // method
    public func instanceThrowsQ182() throws {}  // method throws
    public func instanceAsyncQ183() async {}  // method async
    public func instanceAsyncThrowsQ184() async throws {}  // method throws async
    public static func staticPlainQ185() {}  // static_method
    public static func staticThrowsQ186() throws {}  // static_method throws
    public static func staticAsyncQ187() async {}  // static_method async
    public mutating func mutatingPlainQ188() {}  // mutating_method
    public mutating func mutatingThrowsQ189() throws {}  // mutating_method throws
    public mutating func mutatingAsyncThrowsQ190() async throws {}  // mutating_method throws async
    public func methodReturnsQ191() -> Int { 1 }  // method
    public func genericMethodQ192<T>(_ a: T) throws {}  // method throws
    public consuming func consumingMethodQ193() {}  // method
    public func methodRethrowsQ194(_ f: () throws -> Void) rethrows { try f() }  // method rethrows
    public func methodDefaultsQ195(a: Int = 1, b: Int = 2) throws {}  // method throws
    public func methodTypedThrowsQ196() throws(HelperErrQ900) {}  // method throws typed
    public static func staticRethrowsQ197(_ f: () throws -> Void) rethrows { try f() }  // static_method rethrows
}
public func closureNoEscapeQ200(_ f: () -> Void) {}  // free_function
public func closureEscapingQ201(_ f: @escaping () -> Void) {}  // free_function
public func closureThrowingNoEscapeQ202(_ f: () throws -> Void) {}  // free_function
public func closureThrowingEscapingQ203(_ f: @escaping () throws -> Void) {}  // free_function
public func closureRethrowsQ204(_ f: () throws -> Void) rethrows { try f() }  // free_function rethrows
public func closureRethrowsEscapingQ205(_ f: @escaping () throws -> Void) rethrows { try f() }  // free_function rethrows
public func closureThrowsTakesThrowingQ206(_ f: () throws -> Void) throws { try f() }  // free_function throws
public func closureAsyncParamQ207(_ f: () async -> Void) async { await f() }  // free_function async
public func closureAsyncThrowsParamQ208(_ f: () async throws -> Void) async throws { try await f() }  // free_function throws async
public func closureAsyncRethrowsQ209(_ f: () async throws -> Void) async rethrows { try await f() }  // free_function rethrows async
public func closureAsyncParamSyncFnQ210(_ f: @escaping () async throws -> Void) {}  // free_function
public func closureMainActorParamQ211(_ f: @MainActor () -> Void) {}  // free_function
public func closureReturningValueQ212(_ f: (Int) throws -> Int) rethrows -> Int { try f(1) }  // free_function rethrows
public func closureTypedThrowsQ213(_ f: () throws(HelperErrQ900) -> Void) throws(HelperErrQ900) { try f() }  // free_function throws typed
public func closureTwoQ214(_ a: () throws -> Void, _ b: () -> Void) rethrows { try a() }  // free_function rethrows
public func closureOptionalQ215(_ f: (() throws -> Void)?) {}  // free_function
public func closureTwoThrowingQ216(_ f: () throws -> Void, _ g: () throws -> Void) rethrows { try f(); try g() }  // free_function rethrows
public func closureSendableThrowsQ217(_ f: @Sendable @escaping () throws -> Void) {}  // free_function
public func closureTypedParamUntypedFnQ218(_ f: () throws(HelperErrQ900) -> Void) {}  // free_function
public func closureNestedQ219(_ f: (() throws -> Void) throws -> Void) {}  // free_function
public func closureNestedThrowsQ220(_ f: (() -> Void) -> Void) throws {}  // free_function throws
public func closureInoutQ221(_ f: (inout Int) throws -> Void) rethrows { var x = 0; try f(&x) }  // free_function rethrows
public func closureGenericQ222<T>(_ f: (T) throws -> T, _ v: T) rethrows -> T { try f(v) }  // free_function rethrows
public func closureGenericTypedQ223<E: Error>(_ f: () throws(E) -> Void) throws(E) { try f() }  // free_function throws typed
public func closureGenericTypedNoThrowQ224<E: Error>(_ f: () throws(E) -> Void) {}  // free_function
public func closureIsolatedParamQ225(_ f: (isolated ActorPlainQ018) async -> Void) {}  // free_function
public actor ActorHostQ230 {  // type
    public init(Q231 x: Int) {}  // init
    public func actorPlainQ232() {}  // method
    public func actorThrowsQ233() throws {}  // method throws
    public func actorAsyncQ234() async {}  // method async
    public nonisolated func actorNonisolatedQ235() {}  // method
    public var actorPropQ236: Int { 1 }  // property
    public nonisolated var actorNonisoPropQ237: Int { 1 }  // property
    public var actorGetAsyncThrowsQ238: Int { get async throws { 1 } }  // property throws async
}
@MainActor public struct MainActorStructQ239 {  // type
    public func mainActorMethodQ240() {}  // method
    public var mainActorPropQ241: Int { 1 }  // property
}
public func typedThrowsFreeQ250() throws(HelperErrQ900) {}  // free_function throws typed
public func typedThrowsNeverQ251() throws(Never) {}  // free_function typed neverthrows
public func typedThrowsAnyErrorQ252() throws(any Error) {}  // free_function throws typed
public func typedThrowsAsyncQ253() async throws(HelperErrQ900) {}  // free_function throws async typed
public func typedThrowsReturnQ254() throws(HelperErrQ900) -> Int { 1 }  // free_function throws typed
public func typedThrowsStdlibErrorQ255() throws(CancellationError) {}  // free_function throws typed
public func typedThrowsGenericQ256<E: Error>(_ e: E.Type) throws(E) {}  // free_function throws typed
public struct EffectfulHostQ260 {  // type
    public var getThrowsQ261: Int { get throws { 1 } }  // property throws
    public var getAsyncQ262: Int { get async { 1 } }  // property async
    public var getAsyncThrowsQ263: Int { get async throws { 1 } }  // property throws async
    public static var staticGetThrowsQ264: Int { get throws { 1 } }  // static_property throws
    public static var staticGetAsyncQ265: Int { get async { 1 } }  // static_property async
    public static var staticGetAsyncThrowsQ266: Int { get async throws { 1 } }  // static_property throws async
    public var getTypedThrowsQ267: Int { get throws(HelperErrQ900) { 1 } }  // property throws typed
    public subscript(Q268 i: Int) -> Int { get throws { i } }  // subscript throws
    public subscript(Q269 i: Int) -> Int { get async { i } }  // subscript async
    public subscript(Q270 i: Int) -> Int { get async throws { i } }  // subscript throws async
    public subscript(Q271 i: Int) -> Int { i }  // subscript
    public subscript(Q272 i: Int) -> Int {  // subscript
        get { i }
        set {}
    }
    public subscript(Q273 i: Int) -> Int {  // subscript
        get { i }
        set {}
        _modify { var x = i; yield &x }
    }
    public static subscript(Q274 i: Int) -> Int { get throws { i } }  // static_subscript throws
    public subscript<T>(Q275 t: T) -> Int { get throws { 1 } }  // subscript throws
    public subscript(Q276 i: Int, _ j: Int) -> Int { get async throws { i } }  // subscript throws async
    public subscript(Q277 i: Int) -> Int { get throws(HelperErrQ900) { i } }  // subscript throws typed
    public subscript(Q278 i: Int) -> () throws -> Void { { } }  // subscript
    public var getThrowsClosureQ279: () throws -> Void { {} }  // property
}
open class OpenClassQ290 {  // type
    public init(Q291 x: Int) {}  // init
    open func openMethodQ292() {}  // class_method
    open func openThrowsQ293() throws {}  // class_method throws
    open var openVarQ294: Int { 1 }  // class_property
    open class func openClassFuncQ295() {}  // class_static_method
    public final func finalMethodQ296() {}  // final_method
    open func openAsyncQ297() async {}  // class_method async
    open var openStoredQ298: Int = 0  // class_stored_property
    open subscript(Q299 i: Int) -> Int { get throws { i } }  // class_subscript throws
    open class var openClassVarQ300: Int { 1 }  // class_static_property
    open func openRethrowsQ301(_ f: () throws -> Void) rethrows { try f() }  // class_method rethrows
    open var openGetAsyncThrowsQ302: Int { get async throws { 1 } }  // class_property throws async
}
public struct OuterQ310 {  // type
    public struct InnerStructQ311 {  // type
        public func innerFnQ312() throws {}  // method throws
    }
    public class InnerClassQ313 {  // type
        public func innerClsFnQ314() {}  // method
    }
    public enum InnerEnumQ315 {  // type
        case x
    }
    public struct InnerGenericQ316<T> {  // type
        public func innerGenFnQ317() async throws {}  // method throws async
    }
}
public struct OuterGenericQ318<T> {  // type
    public struct InnerQ319 {  // type
        public func innerOfGenericFnQ320() throws {}  // method throws
    }
    public func outerGenFnQ321() {}  // method
}
extension OuterQ310.InnerStructQ311 {
    public func innerExtQ322() {}  // method
}
extension StructGenericQ005 where T: Equatable {
    public func extGenericQ323() throws {}  // method throws
}
public struct GenericHostQ330<T: Equatable> {  // type
    public func genMethodQ331() {}  // method
    public func genMethodThrowsQ332() throws {}  // method throws
    public func genMethodTQ333(_ t: T) throws -> T { t }  // method throws
    public func genMethodExtraQ334<U: HelperProtoQ901>(_ u: U) {}  // method
    public var genPropQ335: Int { 1 }  // property
    public static func genStaticQ336() async throws {}  // static_method throws async
    public init(Q337 t: T) throws {}  // init throws
    public var genPropThrowsQ338: T { get throws { fatalError() } }  // property throws
}
public class GenericClassHostQ340<T> {  // type
    public init(Q341 t: T) {}  // init
    public func genClsMethodQ342() throws {}  // method throws
    public var genClsPropQ343: T? { nil }  // property
}
public protocol ProtoAssocQ350 {  // type
    associatedtype Item
    func assocFnQ351(_ i: Item) throws -> Item  // requirement throws
}
public struct DefaultsHostQ360 {  // type
    public init(Q361 a: Int = 5) {}  // init
    public func defaultsMethodQ362(a: Int = 1, b: String = "z") {}  // method
    public static func defaultsStaticQ363(a: Int = 1) throws {}  // static_method throws
    public func defaultsGenericQ364<T>(a: T? = nil) {}  // method
}
public func freeKeyKnockQ370() {}  // free_function
public func freeYaKFQ371() {}  // free_function
public func freeKFThrowsQ372() throws {}  // free_function throws
public class LazyHostQ373 {  // type
    public lazy var lazyVarQ374: Int = 3  // lazy_property
}
public func freePackQ376<each T>(_ v: repeat each T) {}  // free_function
public func freePackThrowsQ377<each T>(_ v: repeat each T) throws {}  // free_function throws
public struct NoncopyableQ378: ~Copyable {}  // type
public func freeNoncopyableQ379<T: ~Copyable>(_ v: borrowing T) throws {}  // free_function throws
public struct GenInitQ380 {  // type
    public init<T>(Q381 a: T) throws {}  // init throws
    public init<T>(Q382 a: T) async throws where T: HelperProtoQ901 {}  // init throws async
}
public func typedThrowsGenericAsyncQ383<E: Error>(_ e: E.Type) async throws(E) {}  // free_function throws async typed
