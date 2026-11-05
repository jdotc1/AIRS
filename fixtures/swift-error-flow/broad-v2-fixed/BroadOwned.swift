// Owned Swift broad v2: generated, source-only until independently compiled.
public enum BroadError: Error { case rejected(Int) }
public protocol BroadValue: Sendable { var value: Int { get } }
public struct BroadSmall: BroadValue { public let value: Int; public let other: Int; public init(_ value: Int, _ other: Int) { self.value = value; self.other = other } }
public struct BroadLarge: Sendable { public let a,b,c,d,e,f,g,h: Int; public init(_ n: Int) { a=n; b=n &+ 1; c=n &+ 2; d=n &+ 3; e=n &+ 4; f=n &+ 5; g=n &+ 6; h=n &+ 7 } }
public enum BroadPayload: Sendable { case payload(Int); public var value: Int { switch self { case .payload(let n): return n } } }
public enum BroadTag: Sendable, Equatable { case even, odd }
public final class BroadReference: BroadValue { public let value: Int; public init(_ value: Int) { self.value = value } }
@inline(never) public func broad_transform(_ n: Int) throws -> Int { if n == -12345 { throw BroadError.rejected(n) }; return n &* 3 }
@inline(never) public func broad_cleanup(_ value: inout Int) { value &+= 1 }

@inline(never) public func broad_case_0000(_ transform: (Int) throws -> Int) rethrows -> Void {
    var score = 17
    score = try transform(score)
    score = score &+ 3
    return ()
  }
@inline(never) public func broad_caller_0000_0(_ seed: Int) -> Int {
  do { let result = try broad_case_0000(broad_transform); return seed &+ seed } catch { return seed &- 3 }
}
@inline(never) public func broad_caller_0000_1(_ seed: Int) -> Int {
  if let result = try? broad_case_0000(broad_transform) { return seed }; return seed
}

@inline(never) public func broad_case_0001() throws -> Bool {
    var score = 17
    if score < 4 { throw BroadError.rejected(score) }
    score = score &- 4
    return (score & 1) == 0
  }
@inline(never) public func broad_caller_0001_0(_ seed: Int) -> Int {
  if let result = try? broad_case_0001() { return (result ? 1 : 0) }; return seed
}
@inline(never) public func broad_caller_0001_1(_ seed: Int) -> Int {
  let result = try! broad_case_0001(); return (result ? 1 : 0)
}

@inline(never) public func broad_case_0002() throws -> Int8 {
    var score = 17
    if score > 5 { throw BroadError.rejected(score) }
    score = score ^ 5
    return Int8(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0002_0(_ seed: Int) -> Int {
  let result = try! broad_case_0002(); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0002_1(_ seed: Int) throws -> Int {
  let result = try broad_case_0002(); return Int(truncatingIfNeeded: result) &+ seed
}

@inline(never) public func broad_case_0003() throws -> UInt8 {
    var score = 17
    if score == 6 { throw BroadError.rejected(score) }
    score = score &* 6
    return UInt8(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0003_0(_ seed: Int) throws -> Int {
  let result = try broad_case_0003(); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0003_1(_ seed: Int) -> Int {
  do { _ = try broad_case_0003(); let result = try broad_case_0003(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

@inline(never) public func broad_case_0004() throws -> Int16 {
    var score = 17
    if score < 7 { throw BroadError.rejected(score) }
    score = score &+ 7
    return Int16(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0004_0(_ seed: Int) -> Int {
  do { _ = try broad_case_0004(); let result = try broad_case_0004(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0004_1(_ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0004(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 7 }
}

@inline(never) public func broad_case_0005() throws -> UInt16 {
    var score = 17
    if score > 8 { throw BroadError.rejected(score) }
    score = score &- 8
    return UInt16(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0005_0(_ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0005(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 8 }
}
@inline(never) public func broad_caller_0005_1(_ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0005(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

@inline(never) public func broad_case_0006() throws -> Int32 {
    var score = 17
    if score == 9 { throw BroadError.rejected(score) }
    score = score ^ 9
    return Int32(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0006_0(_ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0006(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0006_1(_ seed: Int) -> Int {
  do { let result = try broad_case_0006(); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

@inline(never) public func broad_case_0007() throws(BroadError) -> UInt32 {
    var score = 17
    if score < 10 { throw BroadError.rejected(score) }
    score = score &* 10
    return UInt32(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0007_0(_ seed: Int) -> Int {
  do { let result = try broad_case_0007(); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0007_1(_ seed: Int) -> Int {
  do { let result = try broad_case_0007(); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

@inline(never) public func broad_case_0008(_ transform: (Int) throws -> Int) rethrows -> Int64 {
    var score = 17
    score = try transform(score)
    score = score &+ 11
    return Int64(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0008_0(_ seed: Int) -> Int {
  do { let result = try broad_case_0008(broad_transform); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0008_1(_ seed: Int) throws -> Int64 {
  return try broad_case_0008(broad_transform)
}

@inline(never) public func broad_case_0009() throws -> UInt64 {
    var score = 17
    if score == 12 { throw BroadError.rejected(score) }
    score = score &- 12
    return UInt64(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0009_0(_ seed: Int) throws -> UInt64 {
  return try broad_case_0009()
}
@inline(never) public func broad_caller_0009_1(_ seed: Int) -> Int {
  do { let result = try broad_case_0009(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 12 }
}

@inline(__always) public func broad_case_0010() throws -> Int {
    var score = 17
    if score < 13 { throw BroadError.rejected(score) }
    score = score ^ 13
    return score
  }
@inline(never) public func broad_caller_0010_0(_ seed: Int) -> Int {
  do { let result = try broad_case_0010(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 13 }
}
@inline(never) public func broad_caller_0010_1(_ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0010(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 13 }
}

@inline(never) public func broad_case_0011() throws -> UInt {
    var score = 17
    if score > 14 { throw BroadError.rejected(score) }
    score = score &* 14
    return UInt(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0011_0(_ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0011(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 14 }
}
@inline(never) public func broad_caller_0011_1(_ seed: Int) -> Int {
  do { let result = try broad_case_0011(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 14 }
}

@inline(never) public func broad_case_0012() throws -> Float {
    var score = 17
    if score == 15 { throw BroadError.rejected(score) }
    score = score &+ 15
    return Float(score) / 3
  }
@inline(never) public func broad_caller_0012_0(_ seed: Int) -> Int {
  do { let result = try broad_case_0012(); return Int(result) &+ seed } catch { return seed &- 15 }
}
@inline(never) public func broad_caller_0012_1(_ seed: Int) -> Int {
  if let result = try? broad_case_0012() { return Int(result) }; return seed
}

@inline(never) public func broad_case_0013() throws -> Double {
    var score = 17
    if score < 16 { throw BroadError.rejected(score) }
    score = score &- 16
    return Double(score) / 3
  }
@inline(never) public func broad_caller_0013_0(_ seed: Int) -> Int {
  if let result = try? broad_case_0013() { return Int(result) }; return seed
}
@inline(never) public func broad_caller_0013_1(_ seed: Int) -> Int {
  let result = try! broad_case_0013(); return Int(result)
}

@inline(never) public func broad_case_0014() throws(BroadError) -> Int? {
    var score = 17
    if score > 17 { throw BroadError.rejected(score) }
    score = score ^ 17
    return score == 0 ? nil : score
  }
@inline(never) public func broad_caller_0014_0(_ seed: Int) -> Int {
  let result = try! broad_case_0014(); return (result ?? seed)
}
@inline(never) public func broad_caller_0014_1(_ seed: Int) throws -> Int {
  let result = try broad_case_0014(); return (result ?? seed) &+ seed
}

@inline(never) public func broad_case_0015() throws -> BroadSmall {
    var score = 17
    if score == 18 { throw BroadError.rejected(score) }
    score = score &* 18
    return BroadSmall(score, score &+ 1)
  }
@inline(never) public func broad_caller_0015_0(_ seed: Int) throws -> Int {
  let result = try broad_case_0015(); return result.value &+ seed
}
@inline(never) public func broad_caller_0015_1(_ seed: Int) -> Int {
  do { _ = try broad_case_0015(); let result = try broad_case_0015(); return result.value &+ seed } catch { return seed }
}

@inline(never) public func broad_case_0016(_ transform: (Int) throws -> Int) rethrows -> BroadLarge {
    var score = 17
    score = try transform(score)
    score = score &+ 19
    return BroadLarge(score)
  }
@inline(never) public func broad_caller_0016_0(_ seed: Int) -> Int {
  do { _ = try broad_case_0016(broad_transform); let result = try broad_case_0016(broad_transform); return result.a &+ result.h &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0016_1(_ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0016(broad_transform); return result.a &+ result.h &+ seed } catch { return seed &- 19 }
}

@inline(never) public func broad_case_0017() throws -> BroadPayload {
    var score = 17
    if score > 20 { throw BroadError.rejected(score) }
    score = score &- 20
    return .payload(score)
  }
@inline(never) public func broad_caller_0017_0(_ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0017(); return result.value &+ seed } catch { return seed &- 20 }
}
@inline(never) public func broad_caller_0017_1(_ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0017(); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

@inline(never) public func broad_case_0018() throws -> BroadTag {
    var score = 17
    if score == 21 { throw BroadError.rejected(score) }
    score = score ^ 21
    return score & 1 == 0 ? .even : .odd
  }
@inline(never) public func broad_caller_0018_0(_ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0018(); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0018_1(_ seed: Int) -> Int {
  do { let result = try broad_case_0018(); return (result == .even ? 2 : 3) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

@inline(never) public func broad_case_0019() throws -> (Int, Bool) {
    var score = 17
    if score < 22 { throw BroadError.rejected(score) }
    score = score &* 22
    return (score, score > 0)
  }
@inline(never) public func broad_caller_0019_0(_ seed: Int) -> Int {
  do { let result = try broad_case_0019(); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0019_1(_ seed: Int) -> Int {
  do { let result = try broad_case_0019(); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

@inline(never) public func broad_case_0020() throws -> BroadReference {
    var score = 17
    if score > 23 { throw BroadError.rejected(score) }
    score = score &+ 23
    return BroadReference(score)
  }
@inline(never) public func broad_caller_0020_0(_ seed: Int) -> Int {
  do { let result = try broad_case_0020(); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0020_1(_ seed: Int) throws -> BroadReference {
  return try broad_case_0020()
}

@inline(never) public func broad_case_0021() throws(BroadError) -> String {
    var score = 17
    if score == 24 { throw BroadError.rejected(score) }
    score = score &- 24
    return String(score, radix: 16)
  }
@inline(never) public func broad_caller_0021_0(_ seed: Int) throws -> String {
  return try broad_case_0021()
}
@inline(never) public func broad_caller_0021_1(_ seed: Int) -> Int {
  do { let result = try broad_case_0021(); return result.utf8.count &+ seed } catch { return seed &- 24 }
}

@inline(__always) public func broad_case_0022() throws -> any BroadValue {
    var score = 17
    if score < 25 { throw BroadError.rejected(score) }
    score = score ^ 25
    return BroadSmall(score, 1)
  }
@inline(never) public func broad_caller_0022_0(_ seed: Int) -> Int {
  do { let result = try broad_case_0022(); return result.value &+ seed } catch { return seed &- 25 }
}
@inline(never) public func broad_caller_0022_1(_ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0022(); return result.value &+ seed } catch { return seed &- 25 }
}

@inline(never) public func broad_case_0023(_ input: Int) throws -> Void {
    var score = input
    if score > 26 { throw BroadError.rejected(score) }
    score = score &* 26
    return ()
  }
@inline(never) public func broad_caller_0023_0(_ input: Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0023(input); return seed &+ seed } catch { return seed &- 26 }
}
@inline(never) public func broad_caller_0023_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0023(input); return seed &+ seed } catch { return seed &- 26 }
}

@inline(never) public func broad_case_0024(_ input: Int, _ transform: (Int) throws -> Int) rethrows -> Bool {
    var score = input
    score = try transform(score)
    score = score &+ 27
    return (score & 1) == 0
  }
@inline(never) public func broad_caller_0024_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0024(input, broad_transform); return (result ? 1 : 0) &+ seed } catch { return seed &- 27 }
}
@inline(never) public func broad_caller_0024_1(_ input: Int, _ seed: Int) -> Int {
  if let result = try? broad_case_0024(input, broad_transform) { return (result ? 1 : 0) }; return seed
}

@inline(never) public func broad_case_0025(_ input: Int) throws -> Int8 {
    var score = input
    if score < 28 { throw BroadError.rejected(score) }
    score = score &- 28
    return Int8(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0025_0(_ input: Int, _ seed: Int) -> Int {
  if let result = try? broad_case_0025(input) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0025_1(_ input: Int, _ seed: Int) -> Int {
  let result = try! broad_case_0025(input); return Int(truncatingIfNeeded: result)
}

@inline(never) public func broad_case_0026(_ input: Int) throws -> UInt8 {
    var score = input
    if score > 29 { throw BroadError.rejected(score) }
    score = score ^ 29
    return UInt8(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0026_0(_ input: Int, _ seed: Int) -> Int {
  let result = try! broad_case_0026(input); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0026_1(_ input: Int, _ seed: Int) throws -> Int {
  let result = try broad_case_0026(input); return Int(truncatingIfNeeded: result) &+ seed
}

@inline(never) public func broad_case_0027(_ input: Int) throws -> Int16 {
    var score = input
    if score == 30 { throw BroadError.rejected(score) }
    score = score &* 30
    return Int16(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0027_0(_ input: Int, _ seed: Int) throws -> Int {
  let result = try broad_case_0027(input); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0027_1(_ input: Int, _ seed: Int) -> Int {
  do { _ = try broad_case_0027(input); let result = try broad_case_0027(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

@inline(never) public func broad_case_0028(_ input: Int) throws(BroadError) -> UInt16 {
    var score = input
    if score < 31 { throw BroadError.rejected(score) }
    score = score &+ 31
    return UInt16(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0028_0(_ input: Int, _ seed: Int) -> Int {
  do { _ = try broad_case_0028(input); let result = try broad_case_0028(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0028_1(_ input: Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0028(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 31 }
}

@inline(never) public func broad_case_0029(_ input: Int) throws -> Int32 {
    var score = input
    if score > 32 { throw BroadError.rejected(score) }
    score = score &- 32
    return Int32(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0029_0(_ input: Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0029(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 32 }
}
@inline(never) public func broad_caller_0029_1(_ input: Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0029(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

@inline(never) public func broad_case_0030(_ input: Int) throws -> UInt32 {
    var score = input
    if score == 33 { throw BroadError.rejected(score) }
    score = score ^ 33
    return UInt32(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0030_0(_ input: Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0030(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0030_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0030(input); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

@inline(never) public func broad_case_0031(_ input: Int) throws -> Int64 {
    var score = input
    if score < 34 { throw BroadError.rejected(score) }
    score = score &* 34
    return Int64(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0031_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0031(input); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0031_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0031(input); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

@inline(never) public func broad_case_0032(_ input: Int, _ transform: (Int) throws -> Int) rethrows -> UInt64 {
    var score = input
    score = try transform(score)
    score = score &+ 35
    return UInt64(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0032_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0032(input, broad_transform); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0032_1(_ input: Int, _ seed: Int) throws -> UInt64 {
  return try broad_case_0032(input, broad_transform)
}

@inline(never) public func broad_case_0033(_ input: Int) throws -> Int {
    var score = input
    if score == 36 { throw BroadError.rejected(score) }
    score = score &- 36
    return score
  }
@inline(never) public func broad_caller_0033_0(_ input: Int, _ seed: Int) throws -> Int {
  return try broad_case_0033(input)
}
@inline(never) public func broad_caller_0033_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0033(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 36 }
}

@inline(__always) public func broad_case_0034(_ input: Int) throws -> UInt {
    var score = input
    if score < 37 { throw BroadError.rejected(score) }
    score = score ^ 37
    return UInt(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0034_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0034(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 37 }
}
@inline(never) public func broad_caller_0034_1(_ input: Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0034(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 37 }
}

@inline(never) public func broad_case_0035(_ input: Int) throws(BroadError) -> Float {
    var score = input
    if score > 38 { throw BroadError.rejected(score) }
    score = score &* 38
    return Float(score) / 3
  }
@inline(never) public func broad_caller_0035_0(_ input: Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0035(input); return Int(result) &+ seed } catch { return seed &- 38 }
}
@inline(never) public func broad_caller_0035_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0035(input); return Int(result) &+ seed } catch { return seed &- 38 }
}

@inline(never) public func broad_case_0036(_ input: Int) throws -> Double {
    var score = input
    if score == 39 { throw BroadError.rejected(score) }
    score = score &+ 39
    return Double(score) / 3
  }
@inline(never) public func broad_caller_0036_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0036(input); return Int(result) &+ seed } catch { return seed &- 39 }
}
@inline(never) public func broad_caller_0036_1(_ input: Int, _ seed: Int) -> Int {
  if let result = try? broad_case_0036(input) { return Int(result) }; return seed
}

@inline(never) public func broad_case_0037(_ input: Int) throws -> Int? {
    var score = input
    if score < 40 { throw BroadError.rejected(score) }
    score = score &- 40
    return score == 0 ? nil : score
  }
@inline(never) public func broad_caller_0037_0(_ input: Int, _ seed: Int) -> Int {
  if let result = try? broad_case_0037(input) { return result }; return seed
}
@inline(never) public func broad_caller_0037_1(_ input: Int, _ seed: Int) -> Int {
  let result = try! broad_case_0037(input); return (result ?? seed)
}

@inline(never) public func broad_case_0038(_ input: Int) throws -> BroadSmall {
    var score = input
    if score > 41 { throw BroadError.rejected(score) }
    score = score ^ 41
    return BroadSmall(score, score &+ 1)
  }
@inline(never) public func broad_caller_0038_0(_ input: Int, _ seed: Int) -> Int {
  let result = try! broad_case_0038(input); return result.value
}
@inline(never) public func broad_caller_0038_1(_ input: Int, _ seed: Int) throws -> Int {
  let result = try broad_case_0038(input); return result.value &+ seed
}

@inline(never) public func broad_case_0039(_ input: Int) throws -> BroadLarge {
    var score = input
    if score == 42 { throw BroadError.rejected(score) }
    score = score &* 42
    return BroadLarge(score)
  }
@inline(never) public func broad_caller_0039_0(_ input: Int, _ seed: Int) throws -> Int {
  let result = try broad_case_0039(input); return result.a &+ result.h &+ seed
}
@inline(never) public func broad_caller_0039_1(_ input: Int, _ seed: Int) -> Int {
  do { _ = try broad_case_0039(input); let result = try broad_case_0039(input); return result.a &+ result.h &+ seed } catch { return seed }
}

@inline(never) public func broad_case_0040(_ input: Int, _ transform: (Int) throws -> Int) rethrows -> BroadPayload {
    var score = input
    score = try transform(score)
    score = score &+ 43
    return .payload(score)
  }
@inline(never) public func broad_caller_0040_0(_ input: Int, _ seed: Int) -> Int {
  do { _ = try broad_case_0040(input, broad_transform); let result = try broad_case_0040(input, broad_transform); return result.value &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0040_1(_ input: Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0040(input, broad_transform); return result.value &+ seed } catch { return seed &- 43 }
}

@inline(never) public func broad_case_0041(_ input: Int) throws -> BroadTag {
    var score = input
    if score > 44 { throw BroadError.rejected(score) }
    score = score &- 44
    return score & 1 == 0 ? .even : .odd
  }
@inline(never) public func broad_caller_0041_0(_ input: Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0041(input); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 44 }
}
@inline(never) public func broad_caller_0041_1(_ input: Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0041(input); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

@inline(never) public func broad_case_0042(_ input: Int) throws(BroadError) -> (Int, Bool) {
    var score = input
    if score == 45 { throw BroadError.rejected(score) }
    score = score ^ 45
    return (score, score > 0)
  }
@inline(never) public func broad_caller_0042_0(_ input: Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0042(input); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0042_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0042(input); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

@inline(never) public func broad_case_0043(_ input: Int) throws -> BroadReference {
    var score = input
    if score < 46 { throw BroadError.rejected(score) }
    score = score &* 46
    return BroadReference(score)
  }
@inline(never) public func broad_caller_0043_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0043(input); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0043_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0043(input); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}

@inline(never) public func broad_case_0044(_ input: Int) throws -> String {
    var score = input
    if score > 47 { throw BroadError.rejected(score) }
    score = score &+ 47
    return String(score, radix: 16)
  }
@inline(never) public func broad_caller_0044_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0044(input); return result.utf8.count &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0044_1(_ input: Int, _ seed: Int) throws -> String {
  return try broad_case_0044(input)
}

@inline(never) public func broad_case_0045(_ input: Int) throws -> any BroadValue {
    var score = input
    if score == 48 { throw BroadError.rejected(score) }
    score = score &- 48
    return BroadSmall(score, 1)
  }
@inline(never) public func broad_caller_0045_0(_ input: Int, _ seed: Int) throws -> any BroadValue {
  return try broad_case_0045(input)
}
@inline(never) public func broad_caller_0045_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0045(input); return result.value &+ seed } catch { return seed &- 48 }
}

@inline(__always) public func broad_case_0046(_ flag: Bool, _ narrow: UInt8) throws -> Void {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 49 { throw BroadError.rejected(score) }
    score = score ^ 49
    return ()
  }
@inline(never) public func broad_caller_0046_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0046(flag, narrow); return seed &+ seed } catch { return seed &- 49 }
}
@inline(never) public func broad_caller_0046_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0046(flag, narrow); return seed &+ seed } catch { return seed &- 49 }
}

@inline(never) public func broad_case_0047(_ flag: Bool, _ narrow: UInt8) throws -> Bool {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 50 { throw BroadError.rejected(score) }
    score = score &* 50
    return (score & 1) == 0
  }
@inline(never) public func broad_caller_0047_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0047(flag, narrow); return (result ? 1 : 0) &+ seed } catch { return seed &- 50 }
}
@inline(never) public func broad_caller_0047_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0047(flag, narrow); return (result ? 1 : 0) &+ seed } catch { return seed &- 50 }
}

@inline(never) public func broad_case_0048(_ flag: Bool, _ narrow: UInt8, _ transform: (Int) throws -> Int) rethrows -> Int8 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    score = try transform(score)
    score = score &+ 51
    return Int8(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0048_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0048(flag, narrow, broad_transform); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 51 }
}
@inline(never) public func broad_caller_0048_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if let result = try? broad_case_0048(flag, narrow, broad_transform) { return Int(truncatingIfNeeded: result) }; return seed
}

@inline(never) public func broad_case_0049(_ flag: Bool, _ narrow: UInt8) throws(BroadError) -> UInt8 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 52 { throw BroadError.rejected(score) }
    score = score &- 52
    return UInt8(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0049_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if let result = try? broad_case_0049(flag, narrow) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0049_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  let result = try! broad_case_0049(flag, narrow); return Int(truncatingIfNeeded: result)
}

@inline(never) public func broad_case_0050(_ flag: Bool, _ narrow: UInt8) throws -> Int16 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 53 { throw BroadError.rejected(score) }
    score = score ^ 53
    return Int16(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0050_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  let result = try! broad_case_0050(flag, narrow); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0050_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  let result = try broad_case_0050(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed
}

@inline(never) public func broad_case_0051(_ flag: Bool, _ narrow: UInt8) throws -> UInt16 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 54 { throw BroadError.rejected(score) }
    score = score &* 54
    return UInt16(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0051_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  let result = try broad_case_0051(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0051_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { _ = try broad_case_0051(flag, narrow); let result = try broad_case_0051(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

@inline(never) public func broad_case_0052(_ flag: Bool, _ narrow: UInt8) throws -> Int32 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 55 { throw BroadError.rejected(score) }
    score = score &+ 55
    return Int32(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0052_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { _ = try broad_case_0052(flag, narrow); let result = try broad_case_0052(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0052_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0052(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 55 }
}

@inline(never) public func broad_case_0053(_ flag: Bool, _ narrow: UInt8) throws -> UInt32 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 56 { throw BroadError.rejected(score) }
    score = score &- 56
    return UInt32(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0053_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0053(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 56 }
}
@inline(never) public func broad_caller_0053_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0053(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

@inline(never) public func broad_case_0054(_ flag: Bool, _ narrow: UInt8) throws -> Int64 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 57 { throw BroadError.rejected(score) }
    score = score ^ 57
    return Int64(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0054_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0054(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0054_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0054(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

@inline(never) public func broad_case_0055(_ flag: Bool, _ narrow: UInt8) throws -> UInt64 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 58 { throw BroadError.rejected(score) }
    score = score &* 58
    return UInt64(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0055_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0055(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0055_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0055(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

@inline(never) public func broad_case_0056(_ flag: Bool, _ narrow: UInt8, _ transform: (Int) throws -> Int) rethrows -> Int {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    score = try transform(score)
    score = score &+ 59
    return score
  }
@inline(never) public func broad_caller_0056_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0056(flag, narrow, broad_transform); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0056_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  return try broad_case_0056(flag, narrow, broad_transform)
}

@inline(never) public func broad_case_0057(_ flag: Bool, _ narrow: UInt8) throws -> UInt {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 60 { throw BroadError.rejected(score) }
    score = score &- 60
    return UInt(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0057_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> UInt {
  return try broad_case_0057(flag, narrow)
}
@inline(never) public func broad_caller_0057_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0057(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 60 }
}

@inline(__always) public func broad_case_0058(_ flag: Bool, _ narrow: UInt8) throws -> Float {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 61 { throw BroadError.rejected(score) }
    score = score ^ 61
    return Float(score) / 3
  }
@inline(never) public func broad_caller_0058_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0058(flag, narrow); return Int(result) &+ seed } catch { return seed &- 61 }
}
@inline(never) public func broad_caller_0058_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0058(flag, narrow); return Int(result) &+ seed } catch { return seed &- 61 }
}

@inline(never) public func broad_case_0059(_ flag: Bool, _ narrow: UInt8) throws -> Double {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 62 { throw BroadError.rejected(score) }
    score = score &* 62
    return Double(score) / 3
  }
@inline(never) public func broad_caller_0059_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0059(flag, narrow); return Int(result) &+ seed } catch { return seed &- 62 }
}
@inline(never) public func broad_caller_0059_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0059(flag, narrow); return Int(result) &+ seed } catch { return seed &- 62 }
}

@inline(never) public func broad_case_0060(_ flag: Bool, _ narrow: UInt8) throws -> Int? {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 63 { throw BroadError.rejected(score) }
    score = score &+ 63
    return score == 0 ? nil : score
  }
@inline(never) public func broad_caller_0060_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0060(flag, narrow); return (result ?? seed) &+ seed } catch { return seed &- 63 }
}
@inline(never) public func broad_caller_0060_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if let result = try? broad_case_0060(flag, narrow) { return result }; return seed
}

@inline(never) public func broad_case_0061(_ flag: Bool, _ narrow: UInt8) throws -> BroadSmall {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 64 { throw BroadError.rejected(score) }
    score = score &- 64
    return BroadSmall(score, score &+ 1)
  }
@inline(never) public func broad_caller_0061_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if let result = try? broad_case_0061(flag, narrow) { return result.value }; return seed
}
@inline(never) public func broad_caller_0061_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  let result = try! broad_case_0061(flag, narrow); return result.value
}

@inline(never) public func broad_case_0062(_ flag: Bool, _ narrow: UInt8) throws -> BroadLarge {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 65 { throw BroadError.rejected(score) }
    score = score ^ 65
    return BroadLarge(score)
  }
@inline(never) public func broad_caller_0062_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  let result = try! broad_case_0062(flag, narrow); return result.a &+ result.h
}
@inline(never) public func broad_caller_0062_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  let result = try broad_case_0062(flag, narrow); return result.a &+ result.h &+ seed
}

@inline(never) public func broad_case_0063(_ flag: Bool, _ narrow: UInt8) throws(BroadError) -> BroadPayload {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 66 { throw BroadError.rejected(score) }
    score = score &* 66
    return .payload(score)
  }
@inline(never) public func broad_caller_0063_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  let result = try broad_case_0063(flag, narrow); return result.value &+ seed
}
@inline(never) public func broad_caller_0063_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { _ = try broad_case_0063(flag, narrow); let result = try broad_case_0063(flag, narrow); return result.value &+ seed } catch { return seed }
}

@inline(never) public func broad_case_0064(_ flag: Bool, _ narrow: UInt8, _ transform: (Int) throws -> Int) rethrows -> BroadTag {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    score = try transform(score)
    score = score &+ 67
    return score & 1 == 0 ? .even : .odd
  }
@inline(never) public func broad_caller_0064_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { _ = try broad_case_0064(flag, narrow, broad_transform); let result = try broad_case_0064(flag, narrow, broad_transform); return (result == .even ? 2 : 3) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0064_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0064(flag, narrow, broad_transform); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 67 }
}

@inline(never) public func broad_case_0065(_ flag: Bool, _ narrow: UInt8) throws -> (Int, Bool) {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 68 { throw BroadError.rejected(score) }
    score = score &- 68
    return (score, score > 0)
  }
@inline(never) public func broad_caller_0065_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0065(flag, narrow); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 68 }
}
@inline(never) public func broad_caller_0065_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0065(flag, narrow); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

@inline(never) public func broad_case_0066(_ flag: Bool, _ narrow: UInt8) throws -> BroadReference {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 69 { throw BroadError.rejected(score) }
    score = score ^ 69
    return BroadReference(score)
  }
@inline(never) public func broad_caller_0066_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0066(flag, narrow); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0066_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0066(flag, narrow); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

@inline(never) public func broad_case_0067(_ flag: Bool, _ narrow: UInt8) throws -> String {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 70 { throw BroadError.rejected(score) }
    score = score &* 70
    return String(score, radix: 16)
  }
@inline(never) public func broad_caller_0067_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0067(flag, narrow); return result.utf8.count &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0067_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0067(flag, narrow); return result.utf8.count &+ seed } catch { fatalError("owned broad v2 rejected") }
}

@inline(never) public func broad_case_0068(_ flag: Bool, _ narrow: UInt8) throws -> any BroadValue {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 71 { throw BroadError.rejected(score) }
    score = score &+ 71
    return BroadSmall(score, 1)
  }
@inline(never) public func broad_caller_0068_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try broad_case_0068(flag, narrow); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0068_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> any BroadValue {
  return try broad_case_0068(flag, narrow)
}

@inline(never) public func broad_case_0069(_ input: inout Int) throws -> Void {
    var score = input
    if score == 72 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 72
    return ()
  }
@inline(never) public func broad_caller_0069_0(_ input: inout Int, _ seed: Int) throws -> Void {
  return try broad_case_0069(&input)
}
@inline(never) public func broad_caller_0069_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0069(&input); return seed &+ seed } catch { return seed &- 72 }
}

@inline(__always) public func broad_case_0070(_ input: inout Int) throws(BroadError) -> Bool {
    var score = input
    if score < 73 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 73
    return (score & 1) == 0
  }
@inline(never) public func broad_caller_0070_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0070(&input); return (result ? 1 : 0) &+ seed } catch { return seed &- 73 }
}
@inline(never) public func broad_caller_0070_1(_ input: inout Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0070(&input); return (result ? 1 : 0) &+ seed } catch { return seed &- 73 }
}

@inline(never) public func broad_case_0071(_ input: inout Int) throws -> Int8 {
    var score = input
    if score > 74 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 74
    return Int8(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0071_0(_ input: inout Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try broad_case_0071(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 74 }
}
@inline(never) public func broad_caller_0071_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0071(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 74 }
}

@inline(never) public func broad_case_0072(_ input: inout Int, _ transform: (Int) throws -> Int) rethrows -> UInt8 {
    var score = input
    score = try transform(score)
    input &+= 1
    score = score &+ 75
    return UInt8(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0072_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0072(&input, broad_transform); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 75 }
}
@inline(never) public func broad_caller_0072_1(_ input: inout Int, _ seed: Int) -> Int {
  if let result = try? broad_case_0072(&input, broad_transform) { return Int(truncatingIfNeeded: result) }; return seed
}

@inline(never) public func broad_case_0073(_ input: inout Int) throws -> Int16 {
    var score = input
    if score < 76 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 76
    return Int16(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0073_0(_ input: inout Int, _ seed: Int) -> Int {
  if let result = try? broad_case_0073(&input) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0073_1(_ input: inout Int, _ seed: Int) -> Int {
  let result = try! broad_case_0073(&input); return Int(truncatingIfNeeded: result)
}

@inline(never) public func broad_case_0074(_ input: inout Int) throws -> UInt16 {
    var score = input
    if score > 77 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 77
    return UInt16(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0074_0(_ input: inout Int, _ seed: Int) -> Int {
  let result = try! broad_case_0074(&input); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0074_1(_ input: inout Int, _ seed: Int) throws -> Int {
  let result = try broad_case_0074(&input); return Int(truncatingIfNeeded: result) &+ seed
}

@inline(never) public func broad_case_0075(_ input: inout Int) throws -> Int32 {
    var score = input
    if score == 78 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 78
    return Int32(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0075_0(_ input: inout Int, _ seed: Int) throws -> Int {
  let result = try broad_case_0075(&input); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0075_1(_ input: inout Int, _ seed: Int) -> Int {
  do { _ = try broad_case_0075(&input); let result = try broad_case_0075(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

@inline(never) public func broad_case_0076(_ input: inout Int) throws -> UInt32 {
    var score = input
    if score < 79 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 79
    return UInt32(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0076_0(_ input: inout Int, _ seed: Int) -> Int {
  do { _ = try broad_case_0076(&input); let result = try broad_case_0076(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0076_1(_ input: inout Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0076(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 79 }
}

@inline(never) public func broad_case_0077(_ input: inout Int) throws(BroadError) -> Int64 {
    var score = input
    if score > 80 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 80
    return Int64(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0077_0(_ input: inout Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try broad_case_0077(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 80 }
}
@inline(never) public func broad_caller_0077_1(_ input: inout Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0077(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

@inline(never) public func broad_case_0078(_ input: inout Int) throws -> UInt64 {
    var score = input
    if score == 81 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 81
    return UInt64(truncatingIfNeeded: score)
  }
@inline(never) public func broad_caller_0078_0(_ input: inout Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try broad_case_0078(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0078_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0078(&input); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

@inline(never) public func broad_case_0079(_ input: inout Int) throws -> Int {
    var score = input
    if score < 82 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 82
    return score
  }
@inline(never) public func broad_caller_0079_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0079(&input); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0079_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try broad_case_0079(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0080 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0080(_ input: inout Int) throws -> UInt {
    var score = input &+ bias
    if score > 83 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 83
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0080_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0080(seed)
  do { let result = try receiver.broad_case_0080(&input); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0080_1(_ input: inout Int, _ seed: Int) throws -> UInt {
  var receiver = BroadOwner0080(seed)
  return try receiver.broad_case_0080(&input)
}

public struct BroadOwner0081 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0081(_ input: inout Int) throws -> Float {
    var score = input &+ bias
    if score == 84 { throw BroadError.rejected(score) }
    input &+= 1
    bias &+= 1
    score = score &- 84
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0081_0(_ input: inout Int, _ seed: Int) throws -> Float {
  var receiver = BroadOwner0081(seed)
  return try receiver.broad_case_0081(&input)
}
@inline(never) public func broad_caller_0081_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0081(seed)
  do { let result = try receiver.broad_case_0081(&input); return Int(result) &+ seed } catch { return seed &- 84 }
}

public struct BroadOwner0082 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0082(_ input: inout Int) throws -> Double {
    var score = input &+ bias
    if score < 85 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 85
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0082_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0082(seed)
  do { let result = try receiver.broad_case_0082(&input); return Int(result) &+ seed } catch { return seed &- 85 }
}
@inline(never) public func broad_caller_0082_1(_ input: inout Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0082(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0082(&input); return Int(result) &+ seed } catch { return seed &- 85 }
}

public struct BroadOwner0083 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0083(_ input: inout Int) throws -> Int? {
    var score = input &+ bias
    if score > 86 { throw BroadError.rejected(score) }
    input &+= 1
    bias &+= 1
    score = score &* 86
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0083_0(_ input: inout Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0083(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0083(&input); return (result ?? seed) &+ seed } catch { return seed &- 86 }
}
@inline(never) public func broad_caller_0083_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0083(seed)
  do { let result = try receiver.broad_case_0083(&input); return (result ?? seed) &+ seed } catch { return seed &- 86 }
}

public struct BroadOwner0084 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0084(_ input: inout Int) throws(BroadError) -> BroadSmall {
    var score = input &+ bias
    if score == 87 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 87
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0084_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0084(seed)
  do { let result = try receiver.broad_case_0084(&input); return result.value &+ seed } catch { return seed &- 87 }
}
@inline(never) public func broad_caller_0084_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0084(seed)
  if let result = try? receiver.broad_case_0084(&input) { return result.value }; return seed
}

public struct BroadOwner0085 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0085(_ input: inout Int) throws -> BroadLarge {
    var score = input &+ bias
    if score < 88 { throw BroadError.rejected(score) }
    input &+= 1
    bias &+= 1
    score = score &- 88
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0085_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0085(seed)
  if let result = try? receiver.broad_case_0085(&input) { return result.a &+ result.h }; return seed
}
@inline(never) public func broad_caller_0085_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0085(seed)
  let result = try! receiver.broad_case_0085(&input); return result.a &+ result.h
}

public struct BroadOwner0086 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0086(_ input: inout Int) throws -> BroadPayload {
    var score = input &+ bias
    if score > 89 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 89
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0086_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0086(seed)
  let result = try! receiver.broad_case_0086(&input); return result.value
}
@inline(never) public func broad_caller_0086_1(_ input: inout Int, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0086(seed)
  let result = try receiver.broad_case_0086(&input); return result.value &+ seed
}

public struct BroadOwner0087 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0087(_ input: inout Int) throws -> BroadTag {
    var score = input &+ bias
    if score == 90 { throw BroadError.rejected(score) }
    input &+= 1
    bias &+= 1
    score = score &* 90
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0087_0(_ input: inout Int, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0087(seed)
  let result = try receiver.broad_case_0087(&input); return (result == .even ? 2 : 3) &+ seed
}
@inline(never) public func broad_caller_0087_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0087(seed)
  do { _ = try receiver.broad_case_0087(&input); let result = try receiver.broad_case_0087(&input); return (result == .even ? 2 : 3) &+ seed } catch { return seed }
}

public struct BroadOwner0088 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0088(_ input: inout Int) throws -> (Int, Bool) {
    var score = input &+ bias
    if score < 91 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 91
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0088_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0088(seed)
  do { _ = try receiver.broad_case_0088(&input); let result = try receiver.broad_case_0088(&input); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0088_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0088(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0088(&input); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 91 }
}

public struct BroadOwner0089 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0089(_ input: inout Int) throws -> BroadReference {
    var score = input &+ bias
    if score > 92 { throw BroadError.rejected(score) }
    input &+= 1
    bias &+= 1
    score = score &- 92
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0089_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0089(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0089(&input); return result.value &+ seed } catch { return seed &- 92 }
}
@inline(never) public func broad_caller_0089_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0089(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0089(&input); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0090 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0090(_ input: inout Int) throws -> String {
    var score = input &+ bias
    if score == 93 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 93
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0090_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0090(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0090(&input); return result.utf8.count &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0090_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0090(seed)
  do { let result = try receiver.broad_case_0090(&input); return result.utf8.count &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0091 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0091(_ input: inout Int) throws(BroadError) -> any BroadValue {
    var score = input &+ bias
    if score < 94 { throw BroadError.rejected(score) }
    input &+= 1
    bias &+= 1
    score = score &* 94
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0091_0(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0091(seed)
  do { let result = try receiver.broad_case_0091(&input); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0091_1(_ input: inout Int, _ seed: Int) -> Int {
  var receiver = BroadOwner0091(seed)
  do { let result = try receiver.broad_case_0091(&input); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0092 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0092(_ text: String, _ values: [Int]) throws -> Void {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 95 { throw BroadError.rejected(score) }
    score = score &+ 95
    return ()
  }
}
@inline(never) public func broad_caller_0092_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0092(seed)
  do { let result = try receiver.broad_case_0092(text, values); return seed &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0092_1(_ text: String, _ values: [Int], _ seed: Int) throws -> Void {
  var receiver = BroadOwner0092(seed)
  return try receiver.broad_case_0092(text, values)
}

public struct BroadOwner0093 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0093(_ text: String, _ values: [Int]) throws -> Bool {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 96 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 96
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0093_0(_ text: String, _ values: [Int], _ seed: Int) throws -> Bool {
  var receiver = BroadOwner0093(seed)
  return try receiver.broad_case_0093(text, values)
}
@inline(never) public func broad_caller_0093_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0093(seed)
  do { let result = try receiver.broad_case_0093(text, values); return (result ? 1 : 0) &+ seed } catch { return seed &- 96 }
}

public struct BroadOwner0094 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0094(_ text: String, _ values: [Int]) throws -> Int8 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 97 { throw BroadError.rejected(score) }
    score = score ^ 97
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0094_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0094(seed)
  do { let result = try receiver.broad_case_0094(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 97 }
}
@inline(never) public func broad_caller_0094_1(_ text: String, _ values: [Int], _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0094(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0094(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 97 }
}

public struct BroadOwner0095 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0095(_ text: String, _ values: [Int]) throws -> UInt8 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 98 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 98
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0095_0(_ text: String, _ values: [Int], _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0095(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0095(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 98 }
}
@inline(never) public func broad_caller_0095_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0095(seed)
  do { let result = try receiver.broad_case_0095(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 98 }
}

public struct BroadOwner0096 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0096(_ text: String, _ values: [Int]) throws -> Int16 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 99 { throw BroadError.rejected(score) }
    score = score &+ 99
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0096_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0096(seed)
  do { let result = try receiver.broad_case_0096(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 99 }
}
@inline(never) public func broad_caller_0096_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0096(seed)
  if let result = try? receiver.broad_case_0096(text, values) { return Int(truncatingIfNeeded: result) }; return seed
}

public struct BroadOwner0097 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0097(_ text: String, _ values: [Int]) throws -> UInt16 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 100 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 100
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0097_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0097(seed)
  if let result = try? receiver.broad_case_0097(text, values) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0097_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0097(seed)
  let result = try! receiver.broad_case_0097(text, values); return Int(truncatingIfNeeded: result)
}

public struct BroadOwner0098 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0098(_ text: String, _ values: [Int]) throws(BroadError) -> Int32 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 101 { throw BroadError.rejected(score) }
    score = score ^ 101
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0098_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0098(seed)
  let result = try! receiver.broad_case_0098(text, values); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0098_1(_ text: String, _ values: [Int], _ seed: Int) throws -> Int {
  var receiver = BroadOwner0098(seed)
  let result = try receiver.broad_case_0098(text, values); return Int(truncatingIfNeeded: result) &+ seed
}

public struct BroadOwner0099 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0099(_ text: String, _ values: [Int]) throws -> UInt32 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 102 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 102
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0099_0(_ text: String, _ values: [Int], _ seed: Int) throws -> Int {
  var receiver = BroadOwner0099(seed)
  let result = try receiver.broad_case_0099(text, values); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0099_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0099(seed)
  do { _ = try receiver.broad_case_0099(text, values); let result = try receiver.broad_case_0099(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public struct BroadOwner0100 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0100(_ text: String, _ values: [Int]) throws -> Int64 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 103 { throw BroadError.rejected(score) }
    score = score &+ 103
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0100_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0100(seed)
  do { _ = try receiver.broad_case_0100(text, values); let result = try receiver.broad_case_0100(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0100_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0100(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0100(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 103 }
}

public struct BroadOwner0101 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0101(_ text: String, _ values: [Int]) throws -> UInt64 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 104 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 104
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0101_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0101(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0101(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 104 }
}
@inline(never) public func broad_caller_0101_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0101(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0101(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0102 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0102(_ text: String, _ values: [Int]) throws -> Int {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 105 { throw BroadError.rejected(score) }
    score = score ^ 105
    return score
  }
}
@inline(never) public func broad_caller_0102_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0102(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0102(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0102_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0102(seed)
  do { let result = try receiver.broad_case_0102(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0103 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0103(_ text: String, _ values: [Int]) throws -> UInt {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 106 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 106
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0103_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0103(seed)
  do { let result = try receiver.broad_case_0103(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0103_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0103(seed)
  do { let result = try receiver.broad_case_0103(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0104 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0104(_ text: String, _ values: [Int]) throws -> Float {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 107 { throw BroadError.rejected(score) }
    score = score &+ 107
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0104_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0104(seed)
  do { let result = try receiver.broad_case_0104(text, values); return Int(result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0104_1(_ text: String, _ values: [Int], _ seed: Int) throws -> Float {
  var receiver = BroadOwner0104(seed)
  return try receiver.broad_case_0104(text, values)
}

public struct BroadOwner0105 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0105(_ text: String, _ values: [Int]) throws(BroadError) -> Double {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 108 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 108
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0105_0(_ text: String, _ values: [Int], _ seed: Int) throws -> Double {
  var receiver = BroadOwner0105(seed)
  return try receiver.broad_case_0105(text, values)
}
@inline(never) public func broad_caller_0105_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0105(seed)
  do { let result = try receiver.broad_case_0105(text, values); return Int(result) &+ seed } catch { return seed &- 108 }
}

public struct BroadOwner0106 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0106(_ text: String, _ values: [Int]) throws -> Int? {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 109 { throw BroadError.rejected(score) }
    score = score ^ 109
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0106_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0106(seed)
  do { let result = try receiver.broad_case_0106(text, values); return (result ?? seed) &+ seed } catch { return seed &- 109 }
}
@inline(never) public func broad_caller_0106_1(_ text: String, _ values: [Int], _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0106(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0106(text, values); return (result ?? seed) &+ seed } catch { return seed &- 109 }
}

public struct BroadOwner0107 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0107(_ text: String, _ values: [Int]) throws -> BroadSmall {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 110 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 110
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0107_0(_ text: String, _ values: [Int], _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0107(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0107(text, values); return result.value &+ seed } catch { return seed &- 110 }
}
@inline(never) public func broad_caller_0107_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0107(seed)
  do { let result = try receiver.broad_case_0107(text, values); return result.value &+ seed } catch { return seed &- 110 }
}

public struct BroadOwner0108 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0108(_ text: String, _ values: [Int]) throws -> BroadLarge {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 111 { throw BroadError.rejected(score) }
    score = score &+ 111
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0108_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0108(seed)
  do { let result = try receiver.broad_case_0108(text, values); return result.a &+ result.h &+ seed } catch { return seed &- 111 }
}
@inline(never) public func broad_caller_0108_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0108(seed)
  if let result = try? receiver.broad_case_0108(text, values) { return result.a &+ result.h }; return seed
}

public struct BroadOwner0109 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0109(_ text: String, _ values: [Int]) throws -> BroadPayload {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 112 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 112
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0109_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0109(seed)
  if let result = try? receiver.broad_case_0109(text, values) { return result.value }; return seed
}
@inline(never) public func broad_caller_0109_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0109(seed)
  let result = try! receiver.broad_case_0109(text, values); return result.value
}

public struct BroadOwner0110 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0110(_ text: String, _ values: [Int]) throws -> BroadTag {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 113 { throw BroadError.rejected(score) }
    score = score ^ 113
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0110_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0110(seed)
  let result = try! receiver.broad_case_0110(text, values); return (result == .even ? 2 : 3)
}
@inline(never) public func broad_caller_0110_1(_ text: String, _ values: [Int], _ seed: Int) throws -> Int {
  var receiver = BroadOwner0110(seed)
  let result = try receiver.broad_case_0110(text, values); return (result == .even ? 2 : 3) &+ seed
}

public struct BroadOwner0111 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0111(_ text: String, _ values: [Int]) throws -> (Int, Bool) {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 114 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 114
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0111_0(_ text: String, _ values: [Int], _ seed: Int) throws -> Int {
  var receiver = BroadOwner0111(seed)
  let result = try receiver.broad_case_0111(text, values); return result.0 &+ (result.1 ? 1 : 0) &+ seed
}
@inline(never) public func broad_caller_0111_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0111(seed)
  do { _ = try receiver.broad_case_0111(text, values); let result = try receiver.broad_case_0111(text, values); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed }
}

public struct BroadOwner0112 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0112(_ text: String, _ values: [Int]) throws(BroadError) -> BroadReference {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 115 { throw BroadError.rejected(score) }
    score = score &+ 115
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0112_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0112(seed)
  do { _ = try receiver.broad_case_0112(text, values); let result = try receiver.broad_case_0112(text, values); return result.value &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0112_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0112(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0112(text, values); return result.value &+ seed } catch { return seed &- 115 }
}

public struct BroadOwner0113 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0113(_ text: String, _ values: [Int]) throws -> String {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 116 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 116
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0113_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0113(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0113(text, values); return result.utf8.count &+ seed } catch { return seed &- 116 }
}
@inline(never) public func broad_caller_0113_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0113(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0113(text, values); return result.utf8.count &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0114 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0114(_ text: String, _ values: [Int]) throws -> any BroadValue {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 117 { throw BroadError.rejected(score) }
    score = score ^ 117
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0114_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0114(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0114(text, values); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0114_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  var receiver = BroadOwner0114(seed)
  do { let result = try receiver.broad_case_0114(text, values); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0115 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0115(_ single: Float, _ double: Double) throws -> Void {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 118 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 118
    return ()
  }
}
@inline(never) public func broad_caller_0115_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0115(seed)
  do { let result = try receiver.broad_case_0115(single, double); return seed &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0115_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0115(seed)
  do { let result = try receiver.broad_case_0115(single, double); return seed &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0116 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0116(_ single: Float, _ double: Double) throws -> Bool {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 119 { throw BroadError.rejected(score) }
    score = score &+ 119
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0116_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0116(seed)
  do { let result = try receiver.broad_case_0116(single, double); return (result ? 1 : 0) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0116_1(_ single: Float, _ double: Double, _ seed: Int) throws -> Bool {
  var receiver = BroadOwner0116(seed)
  return try receiver.broad_case_0116(single, double)
}

public struct BroadOwner0117 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0117(_ single: Float, _ double: Double) throws -> Int8 {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 120 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 120
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0117_0(_ single: Float, _ double: Double, _ seed: Int) throws -> Int8 {
  var receiver = BroadOwner0117(seed)
  return try receiver.broad_case_0117(single, double)
}
@inline(never) public func broad_caller_0117_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0117(seed)
  do { let result = try receiver.broad_case_0117(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 120 }
}

public struct BroadOwner0118 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0118(_ single: Float, _ double: Double) throws -> UInt8 {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 121 { throw BroadError.rejected(score) }
    score = score ^ 121
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0118_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0118(seed)
  do { let result = try receiver.broad_case_0118(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 121 }
}
@inline(never) public func broad_caller_0118_1(_ single: Float, _ double: Double, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0118(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0118(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 121 }
}

public struct BroadOwner0119 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0119(_ single: Float, _ double: Double) throws(BroadError) -> Int16 {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 122 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 122
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0119_0(_ single: Float, _ double: Double, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0119(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0119(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 122 }
}
@inline(never) public func broad_caller_0119_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0119(seed)
  do { let result = try receiver.broad_case_0119(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 122 }
}

public struct BroadOwner0120 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0120(_ single: Float, _ double: Double) throws -> UInt16 {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 123 { throw BroadError.rejected(score) }
    score = score &+ 123
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0120_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0120(seed)
  do { let result = try receiver.broad_case_0120(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 123 }
}
@inline(never) public func broad_caller_0120_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0120(seed)
  if let result = try? receiver.broad_case_0120(single, double) { return Int(truncatingIfNeeded: result) }; return seed
}

public struct BroadOwner0121 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0121(_ single: Float, _ double: Double) throws -> Int32 {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 124 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 124
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0121_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0121(seed)
  if let result = try? receiver.broad_case_0121(single, double) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0121_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0121(seed)
  let result = try! receiver.broad_case_0121(single, double); return Int(truncatingIfNeeded: result)
}

public struct BroadOwner0122 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0122(_ single: Float, _ double: Double) throws -> UInt32 {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 125 { throw BroadError.rejected(score) }
    score = score ^ 125
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0122_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0122(seed)
  let result = try! receiver.broad_case_0122(single, double); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0122_1(_ single: Float, _ double: Double, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0122(seed)
  let result = try receiver.broad_case_0122(single, double); return Int(truncatingIfNeeded: result) &+ seed
}

public struct BroadOwner0123 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0123(_ single: Float, _ double: Double) throws -> Int64 {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 126 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 126
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0123_0(_ single: Float, _ double: Double, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0123(seed)
  let result = try receiver.broad_case_0123(single, double); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0123_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0123(seed)
  do { _ = try receiver.broad_case_0123(single, double); let result = try receiver.broad_case_0123(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public struct BroadOwner0124 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0124(_ single: Float, _ double: Double) throws -> UInt64 {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 127 { throw BroadError.rejected(score) }
    score = score &+ 127
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0124_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0124(seed)
  do { _ = try receiver.broad_case_0124(single, double); let result = try receiver.broad_case_0124(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0124_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0124(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0124(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 127 }
}

public struct BroadOwner0125 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0125(_ single: Float, _ double: Double) throws -> Int {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 128 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 128
    return score
  }
}
@inline(never) public func broad_caller_0125_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0125(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0125(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 128 }
}
@inline(never) public func broad_caller_0125_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0125(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0125(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0126 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0126(_ single: Float, _ double: Double) throws(BroadError) -> UInt {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 129 { throw BroadError.rejected(score) }
    score = score ^ 129
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0126_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0126(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0126(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0126_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0126(seed)
  do { let result = try receiver.broad_case_0126(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0127 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0127(_ single: Float, _ double: Double) throws -> Float {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 130 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 130
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0127_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0127(seed)
  do { let result = try receiver.broad_case_0127(single, double); return Int(result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0127_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0127(seed)
  do { let result = try receiver.broad_case_0127(single, double); return Int(result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0128 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0128(_ single: Float, _ double: Double) throws -> Double {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 131 { throw BroadError.rejected(score) }
    score = score &+ 131
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0128_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0128(seed)
  do { let result = try receiver.broad_case_0128(single, double); return Int(result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0128_1(_ single: Float, _ double: Double, _ seed: Int) throws -> Double {
  var receiver = BroadOwner0128(seed)
  return try receiver.broad_case_0128(single, double)
}

public struct BroadOwner0129 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0129(_ single: Float, _ double: Double) throws -> Int? {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 132 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 132
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0129_0(_ single: Float, _ double: Double, _ seed: Int) throws -> Int? {
  var receiver = BroadOwner0129(seed)
  return try receiver.broad_case_0129(single, double)
}
@inline(never) public func broad_caller_0129_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0129(seed)
  do { let result = try receiver.broad_case_0129(single, double); return (result ?? seed) &+ seed } catch { return seed &- 132 }
}

public struct BroadOwner0130 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0130(_ single: Float, _ double: Double) throws -> BroadSmall {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 133 { throw BroadError.rejected(score) }
    score = score ^ 133
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0130_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0130(seed)
  do { let result = try receiver.broad_case_0130(single, double); return result.value &+ seed } catch { return seed &- 133 }
}
@inline(never) public func broad_caller_0130_1(_ single: Float, _ double: Double, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0130(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0130(single, double); return result.value &+ seed } catch { return seed &- 133 }
}

public struct BroadOwner0131 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0131(_ single: Float, _ double: Double) throws -> BroadLarge {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 134 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 134
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0131_0(_ single: Float, _ double: Double, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0131(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0131(single, double); return result.a &+ result.h &+ seed } catch { return seed &- 134 }
}
@inline(never) public func broad_caller_0131_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0131(seed)
  do { let result = try receiver.broad_case_0131(single, double); return result.a &+ result.h &+ seed } catch { return seed &- 134 }
}

public struct BroadOwner0132 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0132(_ single: Float, _ double: Double) throws -> BroadPayload {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 135 { throw BroadError.rejected(score) }
    score = score &+ 135
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0132_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0132(seed)
  do { let result = try receiver.broad_case_0132(single, double); return result.value &+ seed } catch { return seed &- 135 }
}
@inline(never) public func broad_caller_0132_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0132(seed)
  if let result = try? receiver.broad_case_0132(single, double) { return result.value }; return seed
}

public struct BroadOwner0133 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0133(_ single: Float, _ double: Double) throws(BroadError) -> BroadTag {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 136 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 136
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0133_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0133(seed)
  if let result = try? receiver.broad_case_0133(single, double) { return (result == .even ? 2 : 3) }; return seed
}
@inline(never) public func broad_caller_0133_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0133(seed)
  let result = try! receiver.broad_case_0133(single, double); return (result == .even ? 2 : 3)
}

public struct BroadOwner0134 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0134(_ single: Float, _ double: Double) throws -> (Int, Bool) {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 137 { throw BroadError.rejected(score) }
    score = score ^ 137
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0134_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0134(seed)
  let result = try! receiver.broad_case_0134(single, double); return result.0 &+ (result.1 ? 1 : 0)
}
@inline(never) public func broad_caller_0134_1(_ single: Float, _ double: Double, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0134(seed)
  let result = try receiver.broad_case_0134(single, double); return result.0 &+ (result.1 ? 1 : 0) &+ seed
}

public struct BroadOwner0135 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0135(_ single: Float, _ double: Double) throws -> BroadReference {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 138 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 138
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0135_0(_ single: Float, _ double: Double, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0135(seed)
  let result = try receiver.broad_case_0135(single, double); return result.value &+ seed
}
@inline(never) public func broad_caller_0135_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0135(seed)
  do { _ = try receiver.broad_case_0135(single, double); let result = try receiver.broad_case_0135(single, double); return result.value &+ seed } catch { return seed }
}

public struct BroadOwner0136 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0136(_ single: Float, _ double: Double) throws -> String {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 139 { throw BroadError.rejected(score) }
    score = score &+ 139
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0136_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0136(seed)
  do { _ = try receiver.broad_case_0136(single, double); let result = try receiver.broad_case_0136(single, double); return result.utf8.count &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0136_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0136(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0136(single, double); return result.utf8.count &+ seed } catch { return seed &- 139 }
}

public struct BroadOwner0137 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0137(_ single: Float, _ double: Double) throws -> any BroadValue {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 140 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 140
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0137_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0137(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0137(single, double); return result.value &+ seed } catch { return seed &- 140 }
}
@inline(never) public func broad_caller_0137_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  var receiver = BroadOwner0137(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0137(single, double); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0138 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0138(_ maybe: Int?) throws -> Void {
    var score = (maybe ?? -1) &+ bias
    if score == 141 { throw BroadError.rejected(score) }
    score = score ^ 141
    return ()
  }
}
@inline(never) public func broad_caller_0138_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0138(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0138(maybe); return seed &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0138_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0138(seed)
  do { let result = try receiver.broad_case_0138(maybe); return seed &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0139 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0139(_ maybe: Int?) throws -> Bool {
    var score = (maybe ?? -1) &+ bias
    if score < 142 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 142
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0139_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0139(seed)
  do { let result = try receiver.broad_case_0139(maybe); return (result ? 1 : 0) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0139_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0139(seed)
  do { let result = try receiver.broad_case_0139(maybe); return (result ? 1 : 0) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0140 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0140(_ maybe: Int?) throws(BroadError) -> Int8 {
    var score = (maybe ?? -1) &+ bias
    if score > 143 { throw BroadError.rejected(score) }
    score = score &+ 143
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0140_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0140(seed)
  do { let result = try receiver.broad_case_0140(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0140_1(_ maybe: Int?, _ seed: Int) throws -> Int8 {
  var receiver = BroadOwner0140(seed)
  return try receiver.broad_case_0140(maybe)
}

public struct BroadOwner0141 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0141(_ maybe: Int?) throws -> UInt8 {
    var score = (maybe ?? -1) &+ bias
    if score == 144 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 144
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0141_0(_ maybe: Int?, _ seed: Int) throws -> UInt8 {
  var receiver = BroadOwner0141(seed)
  return try receiver.broad_case_0141(maybe)
}
@inline(never) public func broad_caller_0141_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0141(seed)
  do { let result = try receiver.broad_case_0141(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 144 }
}

public struct BroadOwner0142 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0142(_ maybe: Int?) throws -> Int16 {
    var score = (maybe ?? -1) &+ bias
    if score < 145 { throw BroadError.rejected(score) }
    score = score ^ 145
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0142_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0142(seed)
  do { let result = try receiver.broad_case_0142(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 145 }
}
@inline(never) public func broad_caller_0142_1(_ maybe: Int?, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0142(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0142(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 145 }
}

public struct BroadOwner0143 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0143(_ maybe: Int?) throws -> UInt16 {
    var score = (maybe ?? -1) &+ bias
    if score > 146 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 146
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0143_0(_ maybe: Int?, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0143(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0143(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 146 }
}
@inline(never) public func broad_caller_0143_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0143(seed)
  do { let result = try receiver.broad_case_0143(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 146 }
}

public struct BroadOwner0144 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0144(_ maybe: Int?) throws -> Int32 {
    var score = (maybe ?? -1) &+ bias
    if score == 147 { throw BroadError.rejected(score) }
    score = score &+ 147
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0144_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0144(seed)
  do { let result = try receiver.broad_case_0144(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 147 }
}
@inline(never) public func broad_caller_0144_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0144(seed)
  if let result = try? receiver.broad_case_0144(maybe) { return Int(truncatingIfNeeded: result) }; return seed
}

public struct BroadOwner0145 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0145(_ maybe: Int?) throws -> UInt32 {
    var score = (maybe ?? -1) &+ bias
    if score < 148 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 148
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0145_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0145(seed)
  if let result = try? receiver.broad_case_0145(maybe) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0145_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0145(seed)
  let result = try! receiver.broad_case_0145(maybe); return Int(truncatingIfNeeded: result)
}

public struct BroadOwner0146 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0146(_ maybe: Int?) throws -> Int64 {
    var score = (maybe ?? -1) &+ bias
    if score > 149 { throw BroadError.rejected(score) }
    score = score ^ 149
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0146_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0146(seed)
  let result = try! receiver.broad_case_0146(maybe); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0146_1(_ maybe: Int?, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0146(seed)
  let result = try receiver.broad_case_0146(maybe); return Int(truncatingIfNeeded: result) &+ seed
}

public struct BroadOwner0147 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0147(_ maybe: Int?) throws(BroadError) -> UInt64 {
    var score = (maybe ?? -1) &+ bias
    if score == 150 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 150
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0147_0(_ maybe: Int?, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0147(seed)
  let result = try receiver.broad_case_0147(maybe); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0147_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0147(seed)
  do { _ = try receiver.broad_case_0147(maybe); let result = try receiver.broad_case_0147(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public struct BroadOwner0148 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0148(_ maybe: Int?) throws -> Int {
    var score = (maybe ?? -1) &+ bias
    if score < 151 { throw BroadError.rejected(score) }
    score = score &+ 151
    return score
  }
}
@inline(never) public func broad_caller_0148_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0148(seed)
  do { _ = try receiver.broad_case_0148(maybe); let result = try receiver.broad_case_0148(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0148_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0148(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0148(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 151 }
}

public struct BroadOwner0149 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0149(_ maybe: Int?) throws -> UInt {
    var score = (maybe ?? -1) &+ bias
    if score > 152 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 152
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0149_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0149(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0149(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 152 }
}
@inline(never) public func broad_caller_0149_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0149(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0149(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0150 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0150(_ maybe: Int?) throws -> Float {
    var score = (maybe ?? -1) &+ bias
    if score == 153 { throw BroadError.rejected(score) }
    score = score ^ 153
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0150_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0150(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0150(maybe); return Int(result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0150_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0150(seed)
  do { let result = try receiver.broad_case_0150(maybe); return Int(result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0151 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0151(_ maybe: Int?) throws -> Double {
    var score = (maybe ?? -1) &+ bias
    if score < 154 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 154
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0151_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0151(seed)
  do { let result = try receiver.broad_case_0151(maybe); return Int(result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0151_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0151(seed)
  do { let result = try receiver.broad_case_0151(maybe); return Int(result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0152 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0152(_ maybe: Int?) throws -> Int? {
    var score = (maybe ?? -1) &+ bias
    if score > 155 { throw BroadError.rejected(score) }
    score = score &+ 155
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0152_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0152(seed)
  do { let result = try receiver.broad_case_0152(maybe); return (result ?? seed) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0152_1(_ maybe: Int?, _ seed: Int) throws -> Int? {
  var receiver = BroadOwner0152(seed)
  return try receiver.broad_case_0152(maybe)
}

public struct BroadOwner0153 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0153(_ maybe: Int?) throws -> BroadSmall {
    var score = (maybe ?? -1) &+ bias
    if score == 156 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 156
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0153_0(_ maybe: Int?, _ seed: Int) throws -> BroadSmall {
  var receiver = BroadOwner0153(seed)
  return try receiver.broad_case_0153(maybe)
}
@inline(never) public func broad_caller_0153_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0153(seed)
  do { let result = try receiver.broad_case_0153(maybe); return result.value &+ seed } catch { return seed &- 156 }
}

public struct BroadOwner0154 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0154(_ maybe: Int?) throws(BroadError) -> BroadLarge {
    var score = (maybe ?? -1) &+ bias
    if score < 157 { throw BroadError.rejected(score) }
    score = score ^ 157
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0154_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0154(seed)
  do { let result = try receiver.broad_case_0154(maybe); return result.a &+ result.h &+ seed } catch { return seed &- 157 }
}
@inline(never) public func broad_caller_0154_1(_ maybe: Int?, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0154(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0154(maybe); return result.a &+ result.h &+ seed } catch { return seed &- 157 }
}

public struct BroadOwner0155 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0155(_ maybe: Int?) throws -> BroadPayload {
    var score = (maybe ?? -1) &+ bias
    if score > 158 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 158
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0155_0(_ maybe: Int?, _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0155(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0155(maybe); return result.value &+ seed } catch { return seed &- 158 }
}
@inline(never) public func broad_caller_0155_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0155(seed)
  do { let result = try receiver.broad_case_0155(maybe); return result.value &+ seed } catch { return seed &- 158 }
}

public struct BroadOwner0156 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0156(_ maybe: Int?) throws -> BroadTag {
    var score = (maybe ?? -1) &+ bias
    if score == 159 { throw BroadError.rejected(score) }
    score = score &+ 159
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0156_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0156(seed)
  do { let result = try receiver.broad_case_0156(maybe); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 159 }
}
@inline(never) public func broad_caller_0156_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0156(seed)
  if let result = try? receiver.broad_case_0156(maybe) { return (result == .even ? 2 : 3) }; return seed
}

public struct BroadOwner0157 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0157(_ maybe: Int?) throws -> (Int, Bool) {
    var score = (maybe ?? -1) &+ bias
    if score < 160 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 160
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0157_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0157(seed)
  if let result = try? receiver.broad_case_0157(maybe) { return result.0 &+ (result.1 ? 1 : 0) }; return seed
}
@inline(never) public func broad_caller_0157_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0157(seed)
  let result = try! receiver.broad_case_0157(maybe); return result.0 &+ (result.1 ? 1 : 0)
}

public struct BroadOwner0158 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0158(_ maybe: Int?) throws -> BroadReference {
    var score = (maybe ?? -1) &+ bias
    if score > 161 { throw BroadError.rejected(score) }
    score = score ^ 161
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0158_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0158(seed)
  let result = try! receiver.broad_case_0158(maybe); return result.value
}
@inline(never) public func broad_caller_0158_1(_ maybe: Int?, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0158(seed)
  let result = try receiver.broad_case_0158(maybe); return result.value &+ seed
}

public struct BroadOwner0159 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0159(_ maybe: Int?) throws -> String {
    var score = (maybe ?? -1) &+ bias
    if score == 162 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 162
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0159_0(_ maybe: Int?, _ seed: Int) throws -> Int {
  var receiver = BroadOwner0159(seed)
  let result = try receiver.broad_case_0159(maybe); return result.utf8.count &+ seed
}
@inline(never) public func broad_caller_0159_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0159(seed)
  do { _ = try receiver.broad_case_0159(maybe); let result = try receiver.broad_case_0159(maybe); return result.utf8.count &+ seed } catch { return seed }
}

public struct BroadOwner0160 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0160(_ maybe: Int?) throws -> any BroadValue {
    var score = (maybe ?? -1) &+ bias
    if score < 163 { throw BroadError.rejected(score) }
    score = score &+ 163
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0160_0(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0160(seed)
  do { _ = try receiver.broad_case_0160(maybe); let result = try receiver.broad_case_0160(maybe); return result.value &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0160_1(_ maybe: Int?, _ seed: Int) -> Int {
  var receiver = BroadOwner0160(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0160(maybe); return result.value &+ seed } catch { return seed &- 163 }
}

public struct BroadOwner0161 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0161(_ pair: (Int, Bool)) throws(BroadError) -> Void {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score > 164 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 164
    return ()
  }
}
@inline(never) public func broad_caller_0161_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0161(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0161(pair); return seed &+ seed } catch { return seed &- 164 }
}
@inline(never) public func broad_caller_0161_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0161(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0161(pair); return seed &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0162 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0162(_ pair: (Int, Bool)) throws -> Bool {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score == 165 { throw BroadError.rejected(score) }
    score = score ^ 165
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0162_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0162(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0162(pair); return (result ? 1 : 0) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0162_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0162(seed)
  do { let result = try receiver.broad_case_0162(pair); return (result ? 1 : 0) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0163 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0163(_ pair: (Int, Bool)) throws -> Int8 {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score < 166 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 166
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0163_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0163(seed)
  do { let result = try receiver.broad_case_0163(pair); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0163_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0163(seed)
  do { let result = try receiver.broad_case_0163(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0164 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0164(_ pair: (Int, Bool)) throws -> UInt8 {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score > 167 { throw BroadError.rejected(score) }
    score = score &+ 167
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0164_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0164(seed)
  do { let result = try receiver.broad_case_0164(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0164_1(_ pair: (Int, Bool), _ seed: Int) throws -> UInt8 {
  var receiver = BroadOwner0164(seed)
  return try receiver.broad_case_0164(pair)
}

public struct BroadOwner0165 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0165(_ pair: (Int, Bool)) throws -> Int16 {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score == 168 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 168
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0165_0(_ pair: (Int, Bool), _ seed: Int) throws -> Int16 {
  var receiver = BroadOwner0165(seed)
  return try receiver.broad_case_0165(pair)
}
@inline(never) public func broad_caller_0165_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0165(seed)
  do { let result = try receiver.broad_case_0165(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 168 }
}

public struct BroadOwner0166 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0166(_ pair: (Int, Bool)) throws -> UInt16 {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score < 169 { throw BroadError.rejected(score) }
    score = score ^ 169
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0166_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0166(seed)
  do { let result = try receiver.broad_case_0166(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 169 }
}
@inline(never) public func broad_caller_0166_1(_ pair: (Int, Bool), _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0166(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0166(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 169 }
}

public struct BroadOwner0167 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0167(_ pair: (Int, Bool)) throws -> Int32 {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score > 170 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 170
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0167_0(_ pair: (Int, Bool), _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0167(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0167(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 170 }
}
@inline(never) public func broad_caller_0167_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0167(seed)
  do { let result = try receiver.broad_case_0167(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 170 }
}

public struct BroadOwner0168 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0168(_ pair: (Int, Bool)) throws(BroadError) -> UInt32 {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score == 171 { throw BroadError.rejected(score) }
    score = score &+ 171
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0168_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0168(seed)
  do { let result = try receiver.broad_case_0168(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 171 }
}
@inline(never) public func broad_caller_0168_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0168(seed)
  if let result = try? receiver.broad_case_0168(pair) { return Int(truncatingIfNeeded: result) }; return seed
}

public struct BroadOwner0169 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0169(_ pair: (Int, Bool)) throws -> Int64 {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score < 172 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 172
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0169_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0169(seed)
  if let result = try? receiver.broad_case_0169(pair) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0169_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0169(seed)
  let result = try! receiver.broad_case_0169(pair); return Int(truncatingIfNeeded: result)
}

public struct BroadOwner0170 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0170(_ pair: (Int, Bool)) throws -> UInt64 {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score > 173 { throw BroadError.rejected(score) }
    score = score ^ 173
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0170_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0170(seed)
  let result = try! receiver.broad_case_0170(pair); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0170_1(_ pair: (Int, Bool), _ seed: Int) throws -> Int {
  var receiver = BroadOwner0170(seed)
  let result = try receiver.broad_case_0170(pair); return Int(truncatingIfNeeded: result) &+ seed
}

public struct BroadOwner0171 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0171(_ pair: (Int, Bool)) throws -> Int {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score == 174 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 174
    return score
  }
}
@inline(never) public func broad_caller_0171_0(_ pair: (Int, Bool), _ seed: Int) throws -> Int {
  var receiver = BroadOwner0171(seed)
  let result = try receiver.broad_case_0171(pair); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0171_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0171(seed)
  do { _ = try receiver.broad_case_0171(pair); let result = try receiver.broad_case_0171(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public struct BroadOwner0172 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0172(_ pair: (Int, Bool)) throws -> UInt {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score < 175 { throw BroadError.rejected(score) }
    score = score &+ 175
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0172_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0172(seed)
  do { _ = try receiver.broad_case_0172(pair); let result = try receiver.broad_case_0172(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0172_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0172(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0172(pair); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 175 }
}

public struct BroadOwner0173 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0173(_ pair: (Int, Bool)) throws -> Float {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score > 176 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 176
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0173_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0173(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0173(pair); return Int(result) &+ seed } catch { return seed &- 176 }
}
@inline(never) public func broad_caller_0173_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0173(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0173(pair); return Int(result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0174 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0174(_ pair: (Int, Bool)) throws -> Double {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score == 177 { throw BroadError.rejected(score) }
    score = score ^ 177
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0174_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0174(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0174(pair); return Int(result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0174_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0174(seed)
  do { let result = try receiver.broad_case_0174(pair); return Int(result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0175 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0175(_ pair: (Int, Bool)) throws(BroadError) -> Int? {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score < 178 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 178
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0175_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0175(seed)
  do { let result = try receiver.broad_case_0175(pair); return (result ?? seed) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0175_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0175(seed)
  do { let result = try receiver.broad_case_0175(pair); return (result ?? seed) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0176 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0176(_ pair: (Int, Bool)) throws -> BroadSmall {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score > 179 { throw BroadError.rejected(score) }
    score = score &+ 179
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0176_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0176(seed)
  do { let result = try receiver.broad_case_0176(pair); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0176_1(_ pair: (Int, Bool), _ seed: Int) throws -> BroadSmall {
  var receiver = BroadOwner0176(seed)
  return try receiver.broad_case_0176(pair)
}

public struct BroadOwner0177 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0177(_ pair: (Int, Bool)) throws -> BroadLarge {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score == 180 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &- 180
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0177_0(_ pair: (Int, Bool), _ seed: Int) throws -> BroadLarge {
  var receiver = BroadOwner0177(seed)
  return try receiver.broad_case_0177(pair)
}
@inline(never) public func broad_caller_0177_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0177(seed)
  do { let result = try receiver.broad_case_0177(pair); return result.a &+ result.h &+ seed } catch { return seed &- 180 }
}

public struct BroadOwner0178 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0178(_ pair: (Int, Bool)) throws -> BroadPayload {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score < 181 { throw BroadError.rejected(score) }
    score = score ^ 181
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0178_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0178(seed)
  do { let result = try receiver.broad_case_0178(pair); return result.value &+ seed } catch { return seed &- 181 }
}
@inline(never) public func broad_caller_0178_1(_ pair: (Int, Bool), _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0178(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0178(pair); return result.value &+ seed } catch { return seed &- 181 }
}

public struct BroadOwner0179 { public var bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public mutating func broad_case_0179(_ pair: (Int, Bool)) throws -> BroadTag {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score > 182 { throw BroadError.rejected(score) }
    bias &+= 1
    score = score &* 182
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0179_0(_ pair: (Int, Bool), _ seed: Int, _ cleanup: inout Int) -> Int {
  var receiver = BroadOwner0179(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0179(pair); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 182 }
}
@inline(never) public func broad_caller_0179_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  var receiver = BroadOwner0179(seed)
  do { let result = try receiver.broad_case_0179(pair); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 182 }
}

public enum BroadOwner0180 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0180(_ pair: (Int, Bool)) throws -> (Int, Bool) {
    var score = pair.0 &+ (pair.1 ? 1 : 0)
    if score == 183 { throw BroadError.rejected(score) }
    score = score &+ 183
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0180_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  do { let result = try BroadOwner0180.broad_case_0180(pair); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 183 }
}
@inline(never) public func broad_caller_0180_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  if let result = try? BroadOwner0180.broad_case_0180(pair) { return result.0 &+ (result.1 ? 1 : 0) }; return seed
}

public enum BroadOwner0181 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0181(_ pair: (Int, Bool)) throws -> BroadReference {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score < 184 { throw BroadError.rejected(score) }
    score = score &- 184
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0181_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  if let result = try? BroadOwner0181.value(seed).broad_case_0181(pair) { return result.value }; return seed
}
@inline(never) public func broad_caller_0181_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  let result = try! BroadOwner0181.value(seed).broad_case_0181(pair); return result.value
}

public enum BroadOwner0182 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0182(_ pair: (Int, Bool)) throws(BroadError) -> String {
    var score = pair.0 &+ (pair.1 ? 1 : 0) &+ bias
    if score > 185 { throw BroadError.rejected(score) }
    score = score ^ 185
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0182_0(_ pair: (Int, Bool), _ seed: Int) -> Int {
  let result = try! BroadOwner0182.empty.broad_case_0182(pair); return result.utf8.count
}
@inline(never) public func broad_caller_0182_1(_ pair: (Int, Bool), _ seed: Int) throws -> Int {
  let result = try BroadOwner0182.empty.broad_case_0182(pair); return result.utf8.count &+ seed
}

public enum BroadOwner0183 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0183(_ pair: (Int, Bool)) throws -> any BroadValue {
    var score = pair.0 &+ (pair.1 ? 1 : 0)
    if score == 186 { throw BroadError.rejected(score) }
    score = score &* 186
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0183_0(_ pair: (Int, Bool), _ seed: Int) throws -> Int {
  let result = try BroadOwner0183.broad_case_0183(pair); return result.value &+ seed
}
@inline(never) public func broad_caller_0183_1(_ pair: (Int, Bool), _ seed: Int) -> Int {
  do { _ = try BroadOwner0183.broad_case_0183(pair); let result = try BroadOwner0183.broad_case_0183(pair); return result.value &+ seed } catch { return seed }
}

public enum BroadOwner0184 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0184(_ small: BroadSmall) throws -> Void {
    var score = small.value &+ small.other &+ bias
    if score < 187 { throw BroadError.rejected(score) }
    score = score &+ 187
    return ()
  }
}
@inline(never) public func broad_caller_0184_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { _ = try BroadOwner0184.value(seed).broad_case_0184(small); let result = try BroadOwner0184.value(seed).broad_case_0184(small); return seed &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0184_1(_ small: BroadSmall, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0184.value(seed).broad_case_0184(small); return seed &+ seed } catch { return seed &- 187 }
}

public enum BroadOwner0185 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0185(_ small: BroadSmall) throws -> Bool {
    var score = small.value &+ small.other &+ bias
    if score > 188 { throw BroadError.rejected(score) }
    score = score &- 188
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0185_0(_ small: BroadSmall, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0185.empty.broad_case_0185(small); return (result ? 1 : 0) &+ seed } catch { return seed &- 188 }
}
@inline(never) public func broad_caller_0185_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0185.empty.broad_case_0185(small); return (result ? 1 : 0) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public enum BroadOwner0186 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0186(_ small: BroadSmall) throws -> Int8 {
    var score = small.value &+ small.other
    if score == 189 { throw BroadError.rejected(score) }
    score = score ^ 189
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0186_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0186.broad_case_0186(small); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0186_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0186.broad_case_0186(small); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public enum BroadOwner0187 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0187(_ small: BroadSmall) throws -> UInt8 {
    var score = small.value &+ small.other &+ bias
    if score < 190 { throw BroadError.rejected(score) }
    score = score &* 190
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0187_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0187.value(seed).broad_case_0187(small); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0187_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0187.value(seed).broad_case_0187(small); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public enum BroadOwner0188 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0188(_ small: BroadSmall) throws -> Int16 {
    var score = small.value &+ small.other &+ bias
    if score > 191 { throw BroadError.rejected(score) }
    score = score &+ 191
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0188_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0188.empty.broad_case_0188(small); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0188_1(_ small: BroadSmall, _ seed: Int) throws -> Int16 {
  return try BroadOwner0188.empty.broad_case_0188(small)
}

public enum BroadOwner0189 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0189(_ small: BroadSmall) throws(BroadError) -> UInt16 {
    var score = small.value &+ small.other
    if score == 192 { throw BroadError.rejected(score) }
    score = score &- 192
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0189_0(_ small: BroadSmall, _ seed: Int) throws -> UInt16 {
  return try BroadOwner0189.broad_case_0189(small)
}
@inline(never) public func broad_caller_0189_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0189.broad_case_0189(small); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 192 }
}

public enum BroadOwner0190 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(__always) public func broad_case_0190(_ small: BroadSmall) throws -> Int32 {
    var score = small.value &+ small.other &+ bias
    if score < 193 { throw BroadError.rejected(score) }
    score = score ^ 193
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0190_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0190.value(seed).broad_case_0190(small); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 193 }
}
@inline(never) public func broad_caller_0190_1(_ small: BroadSmall, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0190.value(seed).broad_case_0190(small); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 193 }
}

public enum BroadOwner0191 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0191(_ small: BroadSmall) throws -> UInt32 {
    var score = small.value &+ small.other &+ bias
    if score > 194 { throw BroadError.rejected(score) }
    score = score &* 194
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0191_0(_ small: BroadSmall, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0191.empty.broad_case_0191(small); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 194 }
}
@inline(never) public func broad_caller_0191_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0191.empty.broad_case_0191(small); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 194 }
}

public enum BroadOwner0192 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0192(_ small: BroadSmall) throws -> Int64 {
    var score = small.value &+ small.other
    if score == 195 { throw BroadError.rejected(score) }
    score = score &+ 195
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0192_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0192.broad_case_0192(small); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 195 }
}
@inline(never) public func broad_caller_0192_1(_ small: BroadSmall, _ seed: Int) -> Int {
  if let result = try? BroadOwner0192.broad_case_0192(small) { return Int(truncatingIfNeeded: result) }; return seed
}

public enum BroadOwner0193 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0193(_ small: BroadSmall) throws -> UInt64 {
    var score = small.value &+ small.other &+ bias
    if score < 196 { throw BroadError.rejected(score) }
    score = score &- 196
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0193_0(_ small: BroadSmall, _ seed: Int) -> Int {
  if let result = try? BroadOwner0193.value(seed).broad_case_0193(small) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0193_1(_ small: BroadSmall, _ seed: Int) -> Int {
  let result = try! BroadOwner0193.value(seed).broad_case_0193(small); return Int(truncatingIfNeeded: result)
}

public enum BroadOwner0194 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0194(_ small: BroadSmall) throws -> Int {
    var score = small.value &+ small.other &+ bias
    if score > 197 { throw BroadError.rejected(score) }
    score = score ^ 197
    return score
  }
}
@inline(never) public func broad_caller_0194_0(_ small: BroadSmall, _ seed: Int) -> Int {
  let result = try! BroadOwner0194.empty.broad_case_0194(small); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0194_1(_ small: BroadSmall, _ seed: Int) throws -> Int {
  let result = try BroadOwner0194.empty.broad_case_0194(small); return Int(truncatingIfNeeded: result) &+ seed
}

public enum BroadOwner0195 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0195(_ small: BroadSmall) throws -> UInt {
    var score = small.value &+ small.other
    if score == 198 { throw BroadError.rejected(score) }
    score = score &* 198
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0195_0(_ small: BroadSmall, _ seed: Int) throws -> Int {
  let result = try BroadOwner0195.broad_case_0195(small); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0195_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { _ = try BroadOwner0195.broad_case_0195(small); let result = try BroadOwner0195.broad_case_0195(small); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public enum BroadOwner0196 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0196(_ small: BroadSmall) throws(BroadError) -> Float {
    var score = small.value &+ small.other &+ bias
    if score < 199 { throw BroadError.rejected(score) }
    score = score &+ 199
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0196_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { _ = try BroadOwner0196.value(seed).broad_case_0196(small); let result = try BroadOwner0196.value(seed).broad_case_0196(small); return Int(result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0196_1(_ small: BroadSmall, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0196.value(seed).broad_case_0196(small); return Int(result) &+ seed } catch { return seed &- 199 }
}

public enum BroadOwner0197 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0197(_ small: BroadSmall) throws -> Double {
    var score = small.value &+ small.other &+ bias
    if score > 200 { throw BroadError.rejected(score) }
    score = score &- 200
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0197_0(_ small: BroadSmall, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0197.empty.broad_case_0197(small); return Int(result) &+ seed } catch { return seed &- 200 }
}
@inline(never) public func broad_caller_0197_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0197.empty.broad_case_0197(small); return Int(result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public enum BroadOwner0198 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0198(_ small: BroadSmall) throws -> Int? {
    var score = small.value &+ small.other
    if score == 201 { throw BroadError.rejected(score) }
    score = score ^ 201
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0198_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0198.broad_case_0198(small); return (result ?? seed) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0198_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0198.broad_case_0198(small); return (result ?? seed) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public enum BroadOwner0199 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0199(_ small: BroadSmall) throws -> BroadSmall {
    var score = small.value &+ small.other &+ bias
    if score < 202 { throw BroadError.rejected(score) }
    score = score &* 202
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0199_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0199.value(seed).broad_case_0199(small); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0199_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0199.value(seed).broad_case_0199(small); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public enum BroadOwner0200 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0200(_ small: BroadSmall) throws -> BroadLarge {
    var score = small.value &+ small.other &+ bias
    if score > 203 { throw BroadError.rejected(score) }
    score = score &+ 203
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0200_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0200.empty.broad_case_0200(small); return result.a &+ result.h &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0200_1(_ small: BroadSmall, _ seed: Int) throws -> BroadLarge {
  return try BroadOwner0200.empty.broad_case_0200(small)
}

public enum BroadOwner0201 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0201(_ small: BroadSmall) throws -> BroadPayload {
    var score = small.value &+ small.other
    if score == 204 { throw BroadError.rejected(score) }
    score = score &- 204
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0201_0(_ small: BroadSmall, _ seed: Int) throws -> BroadPayload {
  return try BroadOwner0201.broad_case_0201(small)
}
@inline(never) public func broad_caller_0201_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0201.broad_case_0201(small); return result.value &+ seed } catch { return seed &- 204 }
}

public enum BroadOwner0202 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(__always) public func broad_case_0202(_ small: BroadSmall) throws -> BroadTag {
    var score = small.value &+ small.other &+ bias
    if score < 205 { throw BroadError.rejected(score) }
    score = score ^ 205
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0202_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0202.value(seed).broad_case_0202(small); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 205 }
}
@inline(never) public func broad_caller_0202_1(_ small: BroadSmall, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0202.value(seed).broad_case_0202(small); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 205 }
}

public enum BroadOwner0203 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0203(_ small: BroadSmall) throws(BroadError) -> (Int, Bool) {
    var score = small.value &+ small.other &+ bias
    if score > 206 { throw BroadError.rejected(score) }
    score = score &* 206
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0203_0(_ small: BroadSmall, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0203.empty.broad_case_0203(small); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 206 }
}
@inline(never) public func broad_caller_0203_1(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0203.empty.broad_case_0203(small); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 206 }
}

public enum BroadOwner0204 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0204(_ small: BroadSmall) throws -> BroadReference {
    var score = small.value &+ small.other
    if score == 207 { throw BroadError.rejected(score) }
    score = score &+ 207
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0204_0(_ small: BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0204.broad_case_0204(small); return result.value &+ seed } catch { return seed &- 207 }
}
@inline(never) public func broad_caller_0204_1(_ small: BroadSmall, _ seed: Int) -> Int {
  if let result = try? BroadOwner0204.broad_case_0204(small) { return result.value }; return seed
}

public enum BroadOwner0205 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0205(_ small: BroadSmall) throws -> String {
    var score = small.value &+ small.other &+ bias
    if score < 208 { throw BroadError.rejected(score) }
    score = score &- 208
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0205_0(_ small: BroadSmall, _ seed: Int) -> Int {
  if let result = try? BroadOwner0205.value(seed).broad_case_0205(small) { return result.utf8.count }; return seed
}
@inline(never) public func broad_caller_0205_1(_ small: BroadSmall, _ seed: Int) -> Int {
  let result = try! BroadOwner0205.value(seed).broad_case_0205(small); return result.utf8.count
}

public enum BroadOwner0206 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0206(_ small: BroadSmall) throws -> any BroadValue {
    var score = small.value &+ small.other &+ bias
    if score > 209 { throw BroadError.rejected(score) }
    score = score ^ 209
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0206_0(_ small: BroadSmall, _ seed: Int) -> Int {
  let result = try! BroadOwner0206.empty.broad_case_0206(small); return result.value
}
@inline(never) public func broad_caller_0206_1(_ small: BroadSmall, _ seed: Int) throws -> Int {
  let result = try BroadOwner0206.empty.broad_case_0206(small); return result.value &+ seed
}

public enum BroadOwner0207 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0207(_ reference: borrowing BroadReference) throws -> Void {
    var score = reference.value
    if score == 210 { throw BroadError.rejected(score) }
    score = score &* 210
    return ()
  }
}
@inline(never) public func broad_caller_0207_0(_ reference: borrowing BroadReference, _ seed: Int) throws -> Int {
  let result = try BroadOwner0207.broad_case_0207(reference); return seed &+ seed
}
@inline(never) public func broad_caller_0207_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { _ = try BroadOwner0207.broad_case_0207(reference); let result = try BroadOwner0207.broad_case_0207(reference); return seed &+ seed } catch { return seed }
}

public enum BroadOwner0208 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0208(_ reference: borrowing BroadReference) throws -> Bool {
    var score = reference.value &+ bias
    if score < 211 { throw BroadError.rejected(score) }
    score = score &+ 211
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0208_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { _ = try BroadOwner0208.value(seed).broad_case_0208(reference); let result = try BroadOwner0208.value(seed).broad_case_0208(reference); return (result ? 1 : 0) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0208_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0208.value(seed).broad_case_0208(reference); return (result ? 1 : 0) &+ seed } catch { return seed &- 211 }
}

public enum BroadOwner0209 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0209(_ reference: borrowing BroadReference) throws -> Int8 {
    var score = reference.value &+ bias
    if score > 212 { throw BroadError.rejected(score) }
    score = score &- 212
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0209_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0209.empty.broad_case_0209(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 212 }
}
@inline(never) public func broad_caller_0209_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0209.empty.broad_case_0209(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public enum BroadOwner0210 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0210(_ reference: borrowing BroadReference) throws(BroadError) -> UInt8 {
    var score = reference.value
    if score == 213 { throw BroadError.rejected(score) }
    score = score ^ 213
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0210_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0210.broad_case_0210(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0210_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0210.broad_case_0210(reference); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public enum BroadOwner0211 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0211(_ reference: borrowing BroadReference) throws -> Int16 {
    var score = reference.value &+ bias
    if score < 214 { throw BroadError.rejected(score) }
    score = score &* 214
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0211_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0211.value(seed).broad_case_0211(reference); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0211_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0211.value(seed).broad_case_0211(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public enum BroadOwner0212 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0212(_ reference: borrowing BroadReference) throws -> UInt16 {
    var score = reference.value &+ bias
    if score > 215 { throw BroadError.rejected(score) }
    score = score &+ 215
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0212_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0212.empty.broad_case_0212(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0212_1(_ reference: borrowing BroadReference, _ seed: Int) throws -> UInt16 {
  return try BroadOwner0212.empty.broad_case_0212(reference)
}

public enum BroadOwner0213 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0213(_ reference: borrowing BroadReference) throws -> Int32 {
    var score = reference.value
    if score == 216 { throw BroadError.rejected(score) }
    score = score &- 216
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0213_0(_ reference: borrowing BroadReference, _ seed: Int) throws -> Int32 {
  return try BroadOwner0213.broad_case_0213(reference)
}
@inline(never) public func broad_caller_0213_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0213.broad_case_0213(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 216 }
}

public enum BroadOwner0214 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(__always) public func broad_case_0214(_ reference: borrowing BroadReference) throws -> UInt32 {
    var score = reference.value &+ bias
    if score < 217 { throw BroadError.rejected(score) }
    score = score ^ 217
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0214_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0214.value(seed).broad_case_0214(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 217 }
}
@inline(never) public func broad_caller_0214_1(_ reference: borrowing BroadReference, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0214.value(seed).broad_case_0214(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 217 }
}

public enum BroadOwner0215 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0215(_ reference: borrowing BroadReference) throws -> Int64 {
    var score = reference.value &+ bias
    if score > 218 { throw BroadError.rejected(score) }
    score = score &* 218
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0215_0(_ reference: borrowing BroadReference, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0215.empty.broad_case_0215(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 218 }
}
@inline(never) public func broad_caller_0215_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0215.empty.broad_case_0215(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 218 }
}

public enum BroadOwner0216 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0216(_ reference: borrowing BroadReference) throws -> UInt64 {
    var score = reference.value
    if score == 219 { throw BroadError.rejected(score) }
    score = score &+ 219
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0216_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0216.broad_case_0216(reference); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 219 }
}
@inline(never) public func broad_caller_0216_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  if let result = try? BroadOwner0216.broad_case_0216(reference) { return Int(truncatingIfNeeded: result) }; return seed
}

public enum BroadOwner0217 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0217(_ reference: borrowing BroadReference) throws(BroadError) -> Int {
    var score = reference.value &+ bias
    if score < 220 { throw BroadError.rejected(score) }
    score = score &- 220
    return score
  }
}
@inline(never) public func broad_caller_0217_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  if let result = try? BroadOwner0217.value(seed).broad_case_0217(reference) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0217_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  let result = try! BroadOwner0217.value(seed).broad_case_0217(reference); return Int(truncatingIfNeeded: result)
}

public enum BroadOwner0218 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0218(_ reference: borrowing BroadReference) throws -> UInt {
    var score = reference.value &+ bias
    if score > 221 { throw BroadError.rejected(score) }
    score = score ^ 221
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0218_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  let result = try! BroadOwner0218.empty.broad_case_0218(reference); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0218_1(_ reference: borrowing BroadReference, _ seed: Int) throws -> Int {
  let result = try BroadOwner0218.empty.broad_case_0218(reference); return Int(truncatingIfNeeded: result) &+ seed
}

public enum BroadOwner0219 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0219(_ reference: borrowing BroadReference) throws -> Float {
    var score = reference.value
    if score == 222 { throw BroadError.rejected(score) }
    score = score &* 222
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0219_0(_ reference: borrowing BroadReference, _ seed: Int) throws -> Int {
  let result = try BroadOwner0219.broad_case_0219(reference); return Int(result) &+ seed
}
@inline(never) public func broad_caller_0219_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { _ = try BroadOwner0219.broad_case_0219(reference); let result = try BroadOwner0219.broad_case_0219(reference); return Int(result) &+ seed } catch { return seed }
}

public enum BroadOwner0220 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0220(_ reference: borrowing BroadReference) throws -> Double {
    var score = reference.value &+ bias
    if score < 223 { throw BroadError.rejected(score) }
    score = score &+ 223
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0220_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { _ = try BroadOwner0220.value(seed).broad_case_0220(reference); let result = try BroadOwner0220.value(seed).broad_case_0220(reference); return Int(result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0220_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0220.value(seed).broad_case_0220(reference); return Int(result) &+ seed } catch { return seed &- 223 }
}

public enum BroadOwner0221 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0221(_ reference: borrowing BroadReference) throws -> Int? {
    var score = reference.value &+ bias
    if score > 224 { throw BroadError.rejected(score) }
    score = score &- 224
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0221_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0221.empty.broad_case_0221(reference); return (result ?? seed) &+ seed } catch { return seed &- 224 }
}
@inline(never) public func broad_caller_0221_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0221.empty.broad_case_0221(reference); return (result ?? seed) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public enum BroadOwner0222 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0222(_ reference: borrowing BroadReference) throws -> BroadSmall {
    var score = reference.value
    if score == 225 { throw BroadError.rejected(score) }
    score = score ^ 225
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0222_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0222.broad_case_0222(reference); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0222_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0222.broad_case_0222(reference); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public enum BroadOwner0223 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0223(_ reference: borrowing BroadReference) throws -> BroadLarge {
    var score = reference.value &+ bias
    if score < 226 { throw BroadError.rejected(score) }
    score = score &* 226
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0223_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0223.value(seed).broad_case_0223(reference); return result.a &+ result.h &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0223_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0223.value(seed).broad_case_0223(reference); return result.a &+ result.h &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public enum BroadOwner0224 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0224(_ reference: borrowing BroadReference) throws(BroadError) -> BroadPayload {
    var score = reference.value &+ bias
    if score > 227 { throw BroadError.rejected(score) }
    score = score &+ 227
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0224_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0224.empty.broad_case_0224(reference); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0224_1(_ reference: borrowing BroadReference, _ seed: Int) throws -> BroadPayload {
  return try BroadOwner0224.empty.broad_case_0224(reference)
}

public enum BroadOwner0225 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0225(_ reference: borrowing BroadReference) throws -> BroadTag {
    var score = reference.value
    if score == 228 { throw BroadError.rejected(score) }
    score = score &- 228
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0225_0(_ reference: borrowing BroadReference, _ seed: Int) throws -> BroadTag {
  return try BroadOwner0225.broad_case_0225(reference)
}
@inline(never) public func broad_caller_0225_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0225.broad_case_0225(reference); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 228 }
}

public enum BroadOwner0226 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(__always) public func broad_case_0226(_ reference: borrowing BroadReference) throws -> (Int, Bool) {
    var score = reference.value &+ bias
    if score < 229 { throw BroadError.rejected(score) }
    score = score ^ 229
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0226_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0226.value(seed).broad_case_0226(reference); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 229 }
}
@inline(never) public func broad_caller_0226_1(_ reference: borrowing BroadReference, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0226.value(seed).broad_case_0226(reference); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 229 }
}

public enum BroadOwner0227 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0227(_ reference: borrowing BroadReference) throws -> BroadReference {
    var score = reference.value &+ bias
    if score > 230 { throw BroadError.rejected(score) }
    score = score &* 230
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0227_0(_ reference: borrowing BroadReference, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0227.empty.broad_case_0227(reference); return result.value &+ seed } catch { return seed &- 230 }
}
@inline(never) public func broad_caller_0227_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0227.empty.broad_case_0227(reference); return result.value &+ seed } catch { return seed &- 230 }
}

public enum BroadOwner0228 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0228(_ reference: borrowing BroadReference) throws -> String {
    var score = reference.value
    if score == 231 { throw BroadError.rejected(score) }
    score = score &+ 231
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0228_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  do { let result = try BroadOwner0228.broad_case_0228(reference); return result.utf8.count &+ seed } catch { return seed &- 231 }
}
@inline(never) public func broad_caller_0228_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  if let result = try? BroadOwner0228.broad_case_0228(reference) { return result.utf8.count }; return seed
}

public enum BroadOwner0229 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0229(_ reference: borrowing BroadReference) throws -> any BroadValue {
    var score = reference.value &+ bias
    if score < 232 { throw BroadError.rejected(score) }
    score = score &- 232
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0229_0(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  if let result = try? BroadOwner0229.value(seed).broad_case_0229(reference) { return result.value }; return seed
}
@inline(never) public func broad_caller_0229_1(_ reference: borrowing BroadReference, _ seed: Int) -> Int {
  let result = try! BroadOwner0229.value(seed).broad_case_0229(reference); return result.value
}

public enum BroadOwner0230 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0230(_ owned: consuming BroadSmall) throws -> Void {
    var score = owned.value &+ owned.other &+ bias
    if score > 233 { throw BroadError.rejected(score) }
    score = score ^ 233
    return ()
  }
}
@inline(never) public func broad_caller_0230_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  let result = try! BroadOwner0230.empty.broad_case_0230(owned); return seed
}
@inline(never) public func broad_caller_0230_1(_ owned: consuming BroadSmall, _ seed: Int) throws -> Int {
  let result = try BroadOwner0230.empty.broad_case_0230(owned); return seed &+ seed
}

public enum BroadOwner0231 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0231(_ owned: consuming BroadSmall) throws(BroadError) -> Bool {
    var score = owned.value &+ owned.other
    if score == 234 { throw BroadError.rejected(score) }
    score = score &* 234
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0231_0(_ owned: consuming BroadSmall, _ seed: Int) throws -> Int {
  let result = try BroadOwner0231.broad_case_0231(owned); return (result ? 1 : 0) &+ seed
}
@inline(never) public func broad_caller_0231_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  let firstOwned = BroadSmall(owned.value, owned.other); do { _ = try BroadOwner0231.broad_case_0231(firstOwned); let result = try BroadOwner0231.broad_case_0231(owned); return (result ? 1 : 0) &+ seed } catch { return seed }
}

public enum BroadOwner0232 { case value(Int); public var bias: Int { switch self { case .value(let n): return n } }
  @inline(never) public func broad_case_0232(_ owned: consuming BroadSmall) throws -> Int8 {
    var score = owned.value &+ owned.other &+ bias
    if score < 235 { throw BroadError.rejected(score) }
    score = score &+ 235
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0232_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  let firstOwned = BroadSmall(owned.value, owned.other); do { _ = try BroadOwner0232.value(seed).broad_case_0232(firstOwned); let result = try BroadOwner0232.value(seed).broad_case_0232(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0232_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0232.value(seed).broad_case_0232(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 235 }
}

public enum BroadOwner0233 { case empty; public var bias: Int { 0 }
  @inline(never) public func broad_case_0233(_ owned: consuming BroadSmall) throws -> UInt8 {
    var score = owned.value &+ owned.other &+ bias
    if score > 236 { throw BroadError.rejected(score) }
    score = score &- 236
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0233_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0233.empty.broad_case_0233(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 236 }
}
@inline(never) public func broad_caller_0233_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0233.empty.broad_case_0233(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public enum BroadOwner0234 { case empty; public var bias: Int { 0 }
  @inline(never) public static func broad_case_0234(_ owned: consuming BroadSmall) throws -> Int16 {
    var score = owned.value &+ owned.other
    if score == 237 { throw BroadError.rejected(score) }
    score = score ^ 237
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0234_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0234.broad_case_0234(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0234_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0234.broad_case_0234(owned); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public final class BroadOwner0235 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0235(_ owned: consuming BroadSmall) throws -> UInt16 {
    var score = owned.value &+ owned.other &+ bias
    if score < 238 { throw BroadError.rejected(score) }
    score = score &* 238
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0235_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0235(seed).broad_case_0235(owned); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0235_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0235(seed).broad_case_0235(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0236 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0236(_ owned: consuming BroadSmall) throws -> Int32 {
    var score = owned.value &+ owned.other &+ bias
    if score > 239 { throw BroadError.rejected(score) }
    score = score &+ 239
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0236_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0236(seed).broad_case_0236(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0236_1(_ owned: consuming BroadSmall, _ seed: Int) throws -> Int32 {
  return try BroadOwner0236(seed).broad_case_0236(owned)
}

public final class BroadOwner0237 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0237(_ owned: consuming BroadSmall) throws -> UInt32 {
    var score = owned.value &+ owned.other &+ bias
    if score == 240 { throw BroadError.rejected(score) }
    score = score &- 240
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0237_0(_ owned: consuming BroadSmall, _ seed: Int) throws -> UInt32 {
  return try BroadOwner0237(seed).broad_case_0237(owned)
}
@inline(never) public func broad_caller_0237_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0237(seed).broad_case_0237(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 240 }
}

public class BroadOwner0238 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0238(_ owned: consuming BroadSmall) throws(BroadError) -> Int64 {
    var score = owned.value &+ owned.other &+ bias
    if score < 241 { throw BroadError.rejected(score) }
    score = score ^ 241
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0238_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0238(seed).broad_case_0238(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 241 }
}
@inline(never) public func broad_caller_0238_1(_ owned: consuming BroadSmall, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0238(seed).broad_case_0238(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 241 }
}

public final class BroadOwner0239 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0239(_ owned: consuming BroadSmall) throws -> UInt64 {
    var score = owned.value &+ owned.other &+ bias
    if score > 242 { throw BroadError.rejected(score) }
    score = score &* 242
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0239_0(_ owned: consuming BroadSmall, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0239(seed).broad_case_0239(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 242 }
}
@inline(never) public func broad_caller_0239_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0239(seed).broad_case_0239(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 242 }
}

public class BroadOwner0240 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0240(_ owned: consuming BroadSmall) throws -> Int {
    var score = owned.value &+ owned.other &+ bias
    if score == 243 { throw BroadError.rejected(score) }
    score = score &+ 243
    return score
  }
}
@inline(never) public func broad_caller_0240_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0240(seed).broad_case_0240(owned); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 243 }
}
@inline(never) public func broad_caller_0240_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  if let result = try? BroadOwner0240(seed).broad_case_0240(owned) { return Int(truncatingIfNeeded: result) }; return seed
}

public final class BroadOwner0241 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0241(_ owned: consuming BroadSmall) throws -> UInt {
    var score = owned.value &+ owned.other &+ bias
    if score < 244 { throw BroadError.rejected(score) }
    score = score &- 244
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0241_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  if let result = try? BroadOwner0241(seed).broad_case_0241(owned) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0241_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  let result = try! BroadOwner0241(seed).broad_case_0241(owned); return Int(truncatingIfNeeded: result)
}

public class BroadOwner0242 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0242(_ owned: consuming BroadSmall) throws -> Float {
    var score = owned.value &+ owned.other &+ bias
    if score > 245 { throw BroadError.rejected(score) }
    score = score ^ 245
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0242_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  let result = try! BroadOwner0242(seed).broad_case_0242(owned); return Int(result)
}
@inline(never) public func broad_caller_0242_1(_ owned: consuming BroadSmall, _ seed: Int) throws -> Int {
  let result = try BroadOwner0242(seed).broad_case_0242(owned); return Int(result) &+ seed
}

public final class BroadOwner0243 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0243(_ owned: consuming BroadSmall) throws -> Double {
    var score = owned.value &+ owned.other &+ bias
    if score == 246 { throw BroadError.rejected(score) }
    score = score &* 246
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0243_0(_ owned: consuming BroadSmall, _ seed: Int) throws -> Int {
  let result = try BroadOwner0243(seed).broad_case_0243(owned); return Int(result) &+ seed
}
@inline(never) public func broad_caller_0243_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  let firstOwned = BroadSmall(owned.value, owned.other); do { _ = try BroadOwner0243(seed).broad_case_0243(firstOwned); let result = try BroadOwner0243(seed).broad_case_0243(owned); return Int(result) &+ seed } catch { return seed }
}

public class BroadOwner0244 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0244(_ owned: consuming BroadSmall) throws -> Int? {
    var score = owned.value &+ owned.other &+ bias
    if score < 247 { throw BroadError.rejected(score) }
    score = score &+ 247
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0244_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  let firstOwned = BroadSmall(owned.value, owned.other); do { _ = try BroadOwner0244(seed).broad_case_0244(firstOwned); let result = try BroadOwner0244(seed).broad_case_0244(owned); return (result ?? seed) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0244_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0244(seed).broad_case_0244(owned); return (result ?? seed) &+ seed } catch { return seed &- 247 }
}

public final class BroadOwner0245 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0245(_ owned: consuming BroadSmall) throws(BroadError) -> BroadSmall {
    var score = owned.value &+ owned.other &+ bias
    if score > 248 { throw BroadError.rejected(score) }
    score = score &- 248
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0245_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0245(seed).broad_case_0245(owned); return result.value &+ seed } catch { return seed &- 248 }
}
@inline(never) public func broad_caller_0245_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0245(seed).broad_case_0245(owned); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public class BroadOwner0246 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0246(_ owned: consuming BroadSmall) throws -> BroadLarge {
    var score = owned.value &+ owned.other &+ bias
    if score == 249 { throw BroadError.rejected(score) }
    score = score ^ 249
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0246_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0246(seed).broad_case_0246(owned); return result.a &+ result.h &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0246_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0246(seed).broad_case_0246(owned); return result.a &+ result.h &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public final class BroadOwner0247 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0247(_ owned: consuming BroadSmall) throws -> BroadPayload {
    var score = owned.value &+ owned.other &+ bias
    if score < 250 { throw BroadError.rejected(score) }
    score = score &* 250
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0247_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0247(seed).broad_case_0247(owned); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0247_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0247(seed).broad_case_0247(owned); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0248 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0248(_ owned: consuming BroadSmall) throws -> BroadTag {
    var score = owned.value &+ owned.other &+ bias
    if score > 251 { throw BroadError.rejected(score) }
    score = score &+ 251
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0248_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0248(seed).broad_case_0248(owned); return (result == .even ? 2 : 3) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0248_1(_ owned: consuming BroadSmall, _ seed: Int) throws -> BroadTag {
  return try BroadOwner0248(seed).broad_case_0248(owned)
}

public final class BroadOwner0249 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0249(_ owned: consuming BroadSmall) throws -> (Int, Bool) {
    var score = owned.value &+ owned.other &+ bias
    if score == 252 { throw BroadError.rejected(score) }
    score = score &- 252
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0249_0(_ owned: consuming BroadSmall, _ seed: Int) throws -> (Int, Bool) {
  return try BroadOwner0249(seed).broad_case_0249(owned)
}
@inline(never) public func broad_caller_0249_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0249(seed).broad_case_0249(owned); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 252 }
}

public class BroadOwner0250 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0250(_ owned: consuming BroadSmall) throws -> BroadReference {
    var score = owned.value &+ owned.other &+ bias
    if score < 253 { throw BroadError.rejected(score) }
    score = score ^ 253
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0250_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0250(seed).broad_case_0250(owned); return result.value &+ seed } catch { return seed &- 253 }
}
@inline(never) public func broad_caller_0250_1(_ owned: consuming BroadSmall, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0250(seed).broad_case_0250(owned); return result.value &+ seed } catch { return seed &- 253 }
}

public final class BroadOwner0251 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0251(_ owned: consuming BroadSmall) throws -> String {
    var score = owned.value &+ owned.other &+ bias
    if score > 254 { throw BroadError.rejected(score) }
    score = score &* 254
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0251_0(_ owned: consuming BroadSmall, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0251(seed).broad_case_0251(owned); return result.utf8.count &+ seed } catch { return seed &- 254 }
}
@inline(never) public func broad_caller_0251_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0251(seed).broad_case_0251(owned); return result.utf8.count &+ seed } catch { return seed &- 254 }
}

public class BroadOwner0252 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0252(_ owned: consuming BroadSmall) throws(BroadError) -> any BroadValue {
    var score = owned.value &+ owned.other &+ bias
    if score == 255 { throw BroadError.rejected(score) }
    score = score &+ 255
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0252_0(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  do { let result = try BroadOwner0252(seed).broad_case_0252(owned); return result.value &+ seed } catch { return seed &- 255 }
}
@inline(never) public func broad_caller_0252_1(_ owned: consuming BroadSmall, _ seed: Int) -> Int {
  if let result = try? BroadOwner0252(seed).broad_case_0252(owned) { return result.value }; return seed
}

public final class BroadOwner0253 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0253(_ large: BroadLarge, _ word: UInt64) throws -> Void {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score < 256 { throw BroadError.rejected(score) }
    score = score &- 256
    return ()
  }
}
@inline(never) public func broad_caller_0253_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  if let result = try? BroadOwner0253(seed).broad_case_0253(large, word) { return seed }; return seed
}
@inline(never) public func broad_caller_0253_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  let result = try! BroadOwner0253(seed).broad_case_0253(large, word); return seed
}

public class BroadOwner0254 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0254(_ large: BroadLarge, _ word: UInt64) throws -> Bool {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score > 257 { throw BroadError.rejected(score) }
    score = score ^ 257
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0254_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  let result = try! BroadOwner0254(seed).broad_case_0254(large, word); return (result ? 1 : 0)
}
@inline(never) public func broad_caller_0254_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) throws -> Int {
  let result = try BroadOwner0254(seed).broad_case_0254(large, word); return (result ? 1 : 0) &+ seed
}

public final class BroadOwner0255 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0255(_ large: BroadLarge, _ word: UInt64) throws -> Int8 {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score == 258 { throw BroadError.rejected(score) }
    score = score &* 258
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0255_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) throws -> Int {
  let result = try BroadOwner0255(seed).broad_case_0255(large, word); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0255_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { _ = try BroadOwner0255(seed).broad_case_0255(large, word); let result = try BroadOwner0255(seed).broad_case_0255(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public class BroadOwner0256 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0256(_ large: BroadLarge, _ word: UInt64) throws -> UInt8 {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score < 259 { throw BroadError.rejected(score) }
    score = score &+ 259
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0256_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { _ = try BroadOwner0256(seed).broad_case_0256(large, word); let result = try BroadOwner0256(seed).broad_case_0256(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0256_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0256(seed).broad_case_0256(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 259 }
}

public final class BroadOwner0257 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0257(_ large: BroadLarge, _ word: UInt64) throws -> Int16 {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score > 260 { throw BroadError.rejected(score) }
    score = score &- 260
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0257_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0257(seed).broad_case_0257(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 260 }
}
@inline(never) public func broad_caller_0257_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0257(seed).broad_case_0257(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public class BroadOwner0258 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0258(_ large: BroadLarge, _ word: UInt64) throws -> UInt16 {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score == 261 { throw BroadError.rejected(score) }
    score = score ^ 261
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0258_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0258(seed).broad_case_0258(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0258_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0258(seed).broad_case_0258(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public final class BroadOwner0259 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0259(_ large: BroadLarge, _ word: UInt64) throws(BroadError) -> Int32 {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score < 262 { throw BroadError.rejected(score) }
    score = score &* 262
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0259_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0259(seed).broad_case_0259(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0259_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0259(seed).broad_case_0259(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0260 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0260(_ large: BroadLarge, _ word: UInt64) throws -> UInt32 {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score > 263 { throw BroadError.rejected(score) }
    score = score &+ 263
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0260_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0260(seed).broad_case_0260(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0260_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) throws -> UInt32 {
  return try BroadOwner0260(seed).broad_case_0260(large, word)
}

public final class BroadOwner0261 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0261(_ large: BroadLarge, _ word: UInt64) throws -> Int64 {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score == 264 { throw BroadError.rejected(score) }
    score = score &- 264
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0261_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) throws -> Int64 {
  return try BroadOwner0261(seed).broad_case_0261(large, word)
}
@inline(never) public func broad_caller_0261_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0261(seed).broad_case_0261(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 264 }
}

public class BroadOwner0262 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0262(_ large: BroadLarge, _ word: UInt64) throws -> UInt64 {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score < 265 { throw BroadError.rejected(score) }
    score = score ^ 265
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0262_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0262(seed).broad_case_0262(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 265 }
}
@inline(never) public func broad_caller_0262_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0262(seed).broad_case_0262(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 265 }
}

public final class BroadOwner0263 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0263(_ large: BroadLarge, _ word: UInt64) throws -> Int {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score > 266 { throw BroadError.rejected(score) }
    score = score &* 266
    return score
  }
}
@inline(never) public func broad_caller_0263_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0263(seed).broad_case_0263(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 266 }
}
@inline(never) public func broad_caller_0263_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0263(seed).broad_case_0263(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 266 }
}

public class BroadOwner0264 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0264(_ large: BroadLarge, _ word: UInt64) throws -> UInt {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score == 267 { throw BroadError.rejected(score) }
    score = score &+ 267
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0264_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0264(seed).broad_case_0264(large, word); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 267 }
}
@inline(never) public func broad_caller_0264_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  if let result = try? BroadOwner0264(seed).broad_case_0264(large, word) { return Int(truncatingIfNeeded: result) }; return seed
}

public final class BroadOwner0265 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0265(_ large: BroadLarge, _ word: UInt64) throws -> Float {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score < 268 { throw BroadError.rejected(score) }
    score = score &- 268
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0265_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  if let result = try? BroadOwner0265(seed).broad_case_0265(large, word) { return Int(result) }; return seed
}
@inline(never) public func broad_caller_0265_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  let result = try! BroadOwner0265(seed).broad_case_0265(large, word); return Int(result)
}

public class BroadOwner0266 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0266(_ large: BroadLarge, _ word: UInt64) throws(BroadError) -> Double {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score > 269 { throw BroadError.rejected(score) }
    score = score ^ 269
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0266_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  let result = try! BroadOwner0266(seed).broad_case_0266(large, word); return Int(result)
}
@inline(never) public func broad_caller_0266_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) throws -> Int {
  let result = try BroadOwner0266(seed).broad_case_0266(large, word); return Int(result) &+ seed
}

public final class BroadOwner0267 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0267(_ large: BroadLarge, _ word: UInt64) throws -> Int? {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score == 270 { throw BroadError.rejected(score) }
    score = score &* 270
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0267_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) throws -> Int {
  let result = try BroadOwner0267(seed).broad_case_0267(large, word); return (result ?? seed) &+ seed
}
@inline(never) public func broad_caller_0267_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { _ = try BroadOwner0267(seed).broad_case_0267(large, word); let result = try BroadOwner0267(seed).broad_case_0267(large, word); return (result ?? seed) &+ seed } catch { return seed }
}

public class BroadOwner0268 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0268(_ large: BroadLarge, _ word: UInt64) throws -> BroadSmall {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score < 271 { throw BroadError.rejected(score) }
    score = score &+ 271
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0268_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { _ = try BroadOwner0268(seed).broad_case_0268(large, word); let result = try BroadOwner0268(seed).broad_case_0268(large, word); return result.value &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0268_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0268(seed).broad_case_0268(large, word); return result.value &+ seed } catch { return seed &- 271 }
}

public final class BroadOwner0269 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0269(_ large: BroadLarge, _ word: UInt64) throws -> BroadLarge {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score > 272 { throw BroadError.rejected(score) }
    score = score &- 272
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0269_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0269(seed).broad_case_0269(large, word); return result.a &+ result.h &+ seed } catch { return seed &- 272 }
}
@inline(never) public func broad_caller_0269_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0269(seed).broad_case_0269(large, word); return result.a &+ result.h &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public class BroadOwner0270 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0270(_ large: BroadLarge, _ word: UInt64) throws -> BroadPayload {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score == 273 { throw BroadError.rejected(score) }
    score = score ^ 273
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0270_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0270(seed).broad_case_0270(large, word); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0270_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0270(seed).broad_case_0270(large, word); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public final class BroadOwner0271 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0271(_ large: BroadLarge, _ word: UInt64) throws -> BroadTag {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score < 274 { throw BroadError.rejected(score) }
    score = score &* 274
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0271_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0271(seed).broad_case_0271(large, word); return (result == .even ? 2 : 3) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0271_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0271(seed).broad_case_0271(large, word); return (result == .even ? 2 : 3) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0272 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0272(_ large: BroadLarge, _ word: UInt64) throws -> (Int, Bool) {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score > 275 { throw BroadError.rejected(score) }
    score = score &+ 275
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0272_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0272(seed).broad_case_0272(large, word); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0272_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) throws -> (Int, Bool) {
  return try BroadOwner0272(seed).broad_case_0272(large, word)
}

public final class BroadOwner0273 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0273(_ large: BroadLarge, _ word: UInt64) throws(BroadError) -> BroadReference {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score == 276 { throw BroadError.rejected(score) }
    score = score &- 276
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0273_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) throws -> BroadReference {
  return try BroadOwner0273(seed).broad_case_0273(large, word)
}
@inline(never) public func broad_caller_0273_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0273(seed).broad_case_0273(large, word); return result.value &+ seed } catch { return seed &- 276 }
}

public class BroadOwner0274 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0274(_ large: BroadLarge, _ word: UInt64) throws -> String {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score < 277 { throw BroadError.rejected(score) }
    score = score ^ 277
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0274_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0274(seed).broad_case_0274(large, word); return result.utf8.count &+ seed } catch { return seed &- 277 }
}
@inline(never) public func broad_caller_0274_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0274(seed).broad_case_0274(large, word); return result.utf8.count &+ seed } catch { return seed &- 277 }
}

public final class BroadOwner0275 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0275(_ large: BroadLarge, _ word: UInt64) throws -> any BroadValue {
    var score = large.a &+ large.h &+ Int(truncatingIfNeeded: word) &+ bias
    if score > 278 { throw BroadError.rejected(score) }
    score = score &* 278
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0275_0(_ large: BroadLarge, _ word: UInt64, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0275(seed).broad_case_0275(large, word); return result.value &+ seed } catch { return seed &- 278 }
}
@inline(never) public func broad_caller_0275_1(_ large: BroadLarge, _ word: UInt64, _ seed: Int) -> Int {
  do { let result = try BroadOwner0275(seed).broad_case_0275(large, word); return result.value &+ seed } catch { return seed &- 278 }
}

public class BroadOwner0276 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0276() throws -> Void {
    var score = 17 &+ bias
    if score == 279 { throw BroadError.rejected(score) }
    score = score &+ 279
    return ()
  }
}
@inline(never) public func broad_caller_0276_0(_ seed: Int) -> Int {
  do { let result = try BroadOwner0276(seed).broad_case_0276(); return seed &+ seed } catch { return seed &- 279 }
}
@inline(never) public func broad_caller_0276_1(_ seed: Int) -> Int {
  if let result = try? BroadOwner0276(seed).broad_case_0276() { return seed }; return seed
}

public final class BroadOwner0277 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0277() throws -> Bool {
    var score = 17 &+ bias
    if score < 280 { throw BroadError.rejected(score) }
    score = score &- 280
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0277_0(_ seed: Int) -> Int {
  if let result = try? BroadOwner0277(seed).broad_case_0277() { return (result ? 1 : 0) }; return seed
}
@inline(never) public func broad_caller_0277_1(_ seed: Int) -> Int {
  let result = try! BroadOwner0277(seed).broad_case_0277(); return (result ? 1 : 0)
}

public class BroadOwner0278 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0278() throws -> Int8 {
    var score = 17 &+ bias
    if score > 281 { throw BroadError.rejected(score) }
    score = score ^ 281
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0278_0(_ seed: Int) -> Int {
  let result = try! BroadOwner0278(seed).broad_case_0278(); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0278_1(_ seed: Int) throws -> Int {
  let result = try BroadOwner0278(seed).broad_case_0278(); return Int(truncatingIfNeeded: result) &+ seed
}

public final class BroadOwner0279 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0279() throws -> UInt8 {
    var score = 17 &+ bias
    if score == 282 { throw BroadError.rejected(score) }
    score = score &* 282
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0279_0(_ seed: Int) throws -> Int {
  let result = try BroadOwner0279(seed).broad_case_0279(); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0279_1(_ seed: Int) -> Int {
  do { _ = try BroadOwner0279(seed).broad_case_0279(); let result = try BroadOwner0279(seed).broad_case_0279(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public class BroadOwner0280 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0280() throws(BroadError) -> Int16 {
    var score = 17 &+ bias
    if score < 283 { throw BroadError.rejected(score) }
    score = score &+ 283
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0280_0(_ seed: Int) -> Int {
  do { _ = try BroadOwner0280(seed).broad_case_0280(); let result = try BroadOwner0280(seed).broad_case_0280(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0280_1(_ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0280(seed).broad_case_0280(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 283 }
}

public final class BroadOwner0281 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0281() throws -> UInt16 {
    var score = 17 &+ bias
    if score > 284 { throw BroadError.rejected(score) }
    score = score &- 284
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0281_0(_ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0281(seed).broad_case_0281(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 284 }
}
@inline(never) public func broad_caller_0281_1(_ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0281(seed).broad_case_0281(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public class BroadOwner0282 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0282() throws -> Int32 {
    var score = 17 &+ bias
    if score == 285 { throw BroadError.rejected(score) }
    score = score ^ 285
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0282_0(_ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0282(seed).broad_case_0282(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0282_1(_ seed: Int) -> Int {
  do { let result = try BroadOwner0282(seed).broad_case_0282(); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public final class BroadOwner0283 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0283() throws -> UInt32 {
    var score = 17 &+ bias
    if score < 286 { throw BroadError.rejected(score) }
    score = score &* 286
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0283_0(_ seed: Int) -> Int {
  do { let result = try BroadOwner0283(seed).broad_case_0283(); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0283_1(_ seed: Int) -> Int {
  do { let result = try BroadOwner0283(seed).broad_case_0283(); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0284 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0284() throws -> Int64 {
    var score = 17 &+ bias
    if score > 287 { throw BroadError.rejected(score) }
    score = score &+ 287
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0284_0(_ seed: Int) -> Int {
  do { let result = try BroadOwner0284(seed).broad_case_0284(); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0284_1(_ seed: Int) throws -> Int64 {
  return try BroadOwner0284(seed).broad_case_0284()
}

public final class BroadOwner0285 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0285() throws -> UInt64 {
    var score = 17 &+ bias
    if score == 288 { throw BroadError.rejected(score) }
    score = score &- 288
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0285_0(_ seed: Int) throws -> UInt64 {
  return try BroadOwner0285(seed).broad_case_0285()
}
@inline(never) public func broad_caller_0285_1(_ seed: Int) -> Int {
  do { let result = try BroadOwner0285(seed).broad_case_0285(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 288 }
}

public class BroadOwner0286 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0286() throws -> Int {
    var score = 17 &+ bias
    if score < 289 { throw BroadError.rejected(score) }
    score = score ^ 289
    return score
  }
}
@inline(never) public func broad_caller_0286_0(_ seed: Int) -> Int {
  do { let result = try BroadOwner0286(seed).broad_case_0286(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 289 }
}
@inline(never) public func broad_caller_0286_1(_ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0286(seed).broad_case_0286(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 289 }
}

public final class BroadOwner0287 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0287() throws(BroadError) -> UInt {
    var score = 17 &+ bias
    if score > 290 { throw BroadError.rejected(score) }
    score = score &* 290
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0287_0(_ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0287(seed).broad_case_0287(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 290 }
}
@inline(never) public func broad_caller_0287_1(_ seed: Int) -> Int {
  do { let result = try BroadOwner0287(seed).broad_case_0287(); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 290 }
}

public class BroadOwner0288 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0288() throws -> Float {
    var score = 17 &+ bias
    if score == 291 { throw BroadError.rejected(score) }
    score = score &+ 291
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0288_0(_ seed: Int) -> Int {
  do { let result = try BroadOwner0288(seed).broad_case_0288(); return Int(result) &+ seed } catch { return seed &- 291 }
}
@inline(never) public func broad_caller_0288_1(_ seed: Int) -> Int {
  if let result = try? BroadOwner0288(seed).broad_case_0288() { return Int(result) }; return seed
}

public final class BroadOwner0289 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0289() throws -> Double {
    var score = 17 &+ bias
    if score < 292 { throw BroadError.rejected(score) }
    score = score &- 292
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0289_0(_ seed: Int) -> Int {
  if let result = try? BroadOwner0289(seed).broad_case_0289() { return Int(result) }; return seed
}
@inline(never) public func broad_caller_0289_1(_ seed: Int) -> Int {
  let result = try! BroadOwner0289(seed).broad_case_0289(); return Int(result)
}

public class BroadOwner0290 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0290() throws -> Int? {
    var score = 17 &+ bias
    if score > 293 { throw BroadError.rejected(score) }
    score = score ^ 293
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0290_0(_ seed: Int) -> Int {
  let result = try! BroadOwner0290(seed).broad_case_0290(); return (result ?? seed)
}
@inline(never) public func broad_caller_0290_1(_ seed: Int) throws -> Int {
  let result = try BroadOwner0290(seed).broad_case_0290(); return (result ?? seed) &+ seed
}

public final class BroadOwner0291 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0291() throws -> BroadSmall {
    var score = 17 &+ bias
    if score == 294 { throw BroadError.rejected(score) }
    score = score &* 294
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0291_0(_ seed: Int) throws -> Int {
  let result = try BroadOwner0291(seed).broad_case_0291(); return result.value &+ seed
}
@inline(never) public func broad_caller_0291_1(_ seed: Int) -> Int {
  do { _ = try BroadOwner0291(seed).broad_case_0291(); let result = try BroadOwner0291(seed).broad_case_0291(); return result.value &+ seed } catch { return seed }
}

public class BroadOwner0292 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0292() throws -> BroadLarge {
    var score = 17 &+ bias
    if score < 295 { throw BroadError.rejected(score) }
    score = score &+ 295
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0292_0(_ seed: Int) -> Int {
  do { _ = try BroadOwner0292(seed).broad_case_0292(); let result = try BroadOwner0292(seed).broad_case_0292(); return result.a &+ result.h &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0292_1(_ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0292(seed).broad_case_0292(); return result.a &+ result.h &+ seed } catch { return seed &- 295 }
}

public final class BroadOwner0293 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0293() throws -> BroadPayload {
    var score = 17 &+ bias
    if score > 296 { throw BroadError.rejected(score) }
    score = score &- 296
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0293_0(_ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0293(seed).broad_case_0293(); return result.value &+ seed } catch { return seed &- 296 }
}
@inline(never) public func broad_caller_0293_1(_ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0293(seed).broad_case_0293(); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public class BroadOwner0294 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0294() throws(BroadError) -> BroadTag {
    var score = 17 &+ bias
    if score == 297 { throw BroadError.rejected(score) }
    score = score ^ 297
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0294_0(_ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0294(seed).broad_case_0294(); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0294_1(_ seed: Int) -> Int {
  do { let result = try BroadOwner0294(seed).broad_case_0294(); return (result == .even ? 2 : 3) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0295 {
  @inline(never) public static func broad_case_0295() throws -> (Int, Bool) {
    var score = 17
    if score < 298 { throw BroadError.rejected(score) }
    score = score &* 298
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0295_0(_ seed: Int) -> Int {
  do { let result = try BroadOwner0295.broad_case_0295(); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0295_1(_ seed: Int) -> Int {
  do { let result = try BroadOwner0295.broad_case_0295(); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0296 {
  @inline(never) public class func broad_case_0296() throws -> BroadReference {
    var score = 17
    if score > 299 { throw BroadError.rejected(score) }
    score = score &+ 299
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0296_0(_ seed: Int) -> Int {
  do { let result = try BroadOwner0296.broad_case_0296(); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0296_1(_ seed: Int) throws -> BroadReference {
  return try BroadOwner0296.broad_case_0296()
}

public struct BroadOwner0297 { public init() {} }
public extension BroadOwner0297 {
  @inline(never) func broad_case_0297() throws -> String {
    var score = 17
    if score == 300 { throw BroadError.rejected(score) }
    score = score &- 300
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0297_0(_ seed: Int) throws -> String {
  return try BroadOwner0297().broad_case_0297()
}
@inline(never) public func broad_caller_0297_1(_ seed: Int) -> Int {
  do { let result = try BroadOwner0297().broad_case_0297(); return result.utf8.count &+ seed } catch { return seed &- 300 }
}

public struct BroadOwner0298 {
  @inline(__always) public static func broad_case_0298() throws -> any BroadValue {
    var score = 17
    if score < 301 { throw BroadError.rejected(score) }
    score = score ^ 301
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0298_0(_ seed: Int) -> Int {
  do { let result = try BroadOwner0298.broad_case_0298(); return result.value &+ seed } catch { return seed &- 301 }
}
@inline(never) public func broad_caller_0298_1(_ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0298.broad_case_0298(); return result.value &+ seed } catch { return seed &- 301 }
}

public class BroadOwner0299 {
  @inline(never) public class func broad_case_0299(_ input: Int) throws -> Void {
    var score = input
    if score > 302 { throw BroadError.rejected(score) }
    score = score &* 302
    return ()
  }
}
@inline(never) public func broad_caller_0299_0(_ input: Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0299.broad_case_0299(input); return seed &+ seed } catch { return seed &- 302 }
}
@inline(never) public func broad_caller_0299_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0299.broad_case_0299(input); return seed &+ seed } catch { return seed &- 302 }
}

public struct BroadOwner0300 { public init() {} }
public extension BroadOwner0300 {
  @inline(never) func broad_case_0300(_ input: Int) throws -> Bool {
    var score = input
    if score == 303 { throw BroadError.rejected(score) }
    score = score &+ 303
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0300_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0300().broad_case_0300(input); return (result ? 1 : 0) &+ seed } catch { return seed &- 303 }
}
@inline(never) public func broad_caller_0300_1(_ input: Int, _ seed: Int) -> Int {
  if let result = try? BroadOwner0300().broad_case_0300(input) { return (result ? 1 : 0) }; return seed
}

public struct BroadOwner0301 {
  @inline(never) public static func broad_case_0301(_ input: Int) throws(BroadError) -> Int8 {
    var score = input
    if score < 304 { throw BroadError.rejected(score) }
    score = score &- 304
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0301_0(_ input: Int, _ seed: Int) -> Int {
  if let result = try? BroadOwner0301.broad_case_0301(input) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0301_1(_ input: Int, _ seed: Int) -> Int {
  let result = try! BroadOwner0301.broad_case_0301(input); return Int(truncatingIfNeeded: result)
}

public class BroadOwner0302 {
  @inline(never) public class func broad_case_0302(_ input: Int) throws -> UInt8 {
    var score = input
    if score > 305 { throw BroadError.rejected(score) }
    score = score ^ 305
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0302_0(_ input: Int, _ seed: Int) -> Int {
  let result = try! BroadOwner0302.broad_case_0302(input); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0302_1(_ input: Int, _ seed: Int) throws -> Int {
  let result = try BroadOwner0302.broad_case_0302(input); return Int(truncatingIfNeeded: result) &+ seed
}

public struct BroadOwner0303 { public init() {} }
public extension BroadOwner0303 {
  @inline(never) func broad_case_0303(_ input: Int) throws -> Int16 {
    var score = input
    if score == 306 { throw BroadError.rejected(score) }
    score = score &* 306
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0303_0(_ input: Int, _ seed: Int) throws -> Int {
  let result = try BroadOwner0303().broad_case_0303(input); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0303_1(_ input: Int, _ seed: Int) -> Int {
  do { _ = try BroadOwner0303().broad_case_0303(input); let result = try BroadOwner0303().broad_case_0303(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public struct BroadOwner0304 {
  @inline(never) public static func broad_case_0304(_ input: Int) throws -> UInt16 {
    var score = input
    if score < 307 { throw BroadError.rejected(score) }
    score = score &+ 307
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0304_0(_ input: Int, _ seed: Int) -> Int {
  do { _ = try BroadOwner0304.broad_case_0304(input); let result = try BroadOwner0304.broad_case_0304(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0304_1(_ input: Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0304.broad_case_0304(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 307 }
}

public class BroadOwner0305 {
  @inline(never) public class func broad_case_0305(_ input: Int) throws -> Int32 {
    var score = input
    if score > 308 { throw BroadError.rejected(score) }
    score = score &- 308
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0305_0(_ input: Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0305.broad_case_0305(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 308 }
}
@inline(never) public func broad_caller_0305_1(_ input: Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0305.broad_case_0305(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0306 { public init() {} }
public extension BroadOwner0306 {
  @inline(never) func broad_case_0306(_ input: Int) throws -> UInt32 {
    var score = input
    if score == 309 { throw BroadError.rejected(score) }
    score = score ^ 309
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0306_0(_ input: Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0306().broad_case_0306(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0306_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0306().broad_case_0306(input); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0307 {
  @inline(never) public static func broad_case_0307(_ input: Int) throws -> Int64 {
    var score = input
    if score < 310 { throw BroadError.rejected(score) }
    score = score &* 310
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0307_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0307.broad_case_0307(input); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0307_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0307.broad_case_0307(input); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0308 {
  @inline(never) public class func broad_case_0308(_ input: Int) throws(BroadError) -> UInt64 {
    var score = input
    if score > 311 { throw BroadError.rejected(score) }
    score = score &+ 311
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0308_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0308.broad_case_0308(input); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0308_1(_ input: Int, _ seed: Int) throws -> UInt64 {
  return try BroadOwner0308.broad_case_0308(input)
}

public struct BroadOwner0309 { public init() {} }
public extension BroadOwner0309 {
  @inline(never) func broad_case_0309(_ input: Int) throws -> Int {
    var score = input
    if score == 312 { throw BroadError.rejected(score) }
    score = score &- 312
    return score
  }
}
@inline(never) public func broad_caller_0309_0(_ input: Int, _ seed: Int) throws -> Int {
  return try BroadOwner0309().broad_case_0309(input)
}
@inline(never) public func broad_caller_0309_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0309().broad_case_0309(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 312 }
}

public struct BroadOwner0310 {
  @inline(__always) public static func broad_case_0310(_ input: Int) throws -> UInt {
    var score = input
    if score < 313 { throw BroadError.rejected(score) }
    score = score ^ 313
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0310_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0310.broad_case_0310(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 313 }
}
@inline(never) public func broad_caller_0310_1(_ input: Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0310.broad_case_0310(input); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 313 }
}

public class BroadOwner0311 {
  @inline(never) public class func broad_case_0311(_ input: Int) throws -> Float {
    var score = input
    if score > 314 { throw BroadError.rejected(score) }
    score = score &* 314
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0311_0(_ input: Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0311.broad_case_0311(input); return Int(result) &+ seed } catch { return seed &- 314 }
}
@inline(never) public func broad_caller_0311_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0311.broad_case_0311(input); return Int(result) &+ seed } catch { return seed &- 314 }
}

public struct BroadOwner0312 { public init() {} }
public extension BroadOwner0312 {
  @inline(never) func broad_case_0312(_ input: Int) throws -> Double {
    var score = input
    if score == 315 { throw BroadError.rejected(score) }
    score = score &+ 315
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0312_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0312().broad_case_0312(input); return Int(result) &+ seed } catch { return seed &- 315 }
}
@inline(never) public func broad_caller_0312_1(_ input: Int, _ seed: Int) -> Int {
  if let result = try? BroadOwner0312().broad_case_0312(input) { return Int(result) }; return seed
}

public struct BroadOwner0313 {
  @inline(never) public static func broad_case_0313(_ input: Int) throws -> Int? {
    var score = input
    if score < 316 { throw BroadError.rejected(score) }
    score = score &- 316
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0313_0(_ input: Int, _ seed: Int) -> Int {
  if let result = try? BroadOwner0313.broad_case_0313(input) { return result }; return seed
}
@inline(never) public func broad_caller_0313_1(_ input: Int, _ seed: Int) -> Int {
  let result = try! BroadOwner0313.broad_case_0313(input); return (result ?? seed)
}

public class BroadOwner0314 {
  @inline(never) public class func broad_case_0314(_ input: Int) throws -> BroadSmall {
    var score = input
    if score > 317 { throw BroadError.rejected(score) }
    score = score ^ 317
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0314_0(_ input: Int, _ seed: Int) -> Int {
  let result = try! BroadOwner0314.broad_case_0314(input); return result.value
}
@inline(never) public func broad_caller_0314_1(_ input: Int, _ seed: Int) throws -> Int {
  let result = try BroadOwner0314.broad_case_0314(input); return result.value &+ seed
}

public struct BroadOwner0315 { public init() {} }
public extension BroadOwner0315 {
  @inline(never) func broad_case_0315(_ input: Int) throws(BroadError) -> BroadLarge {
    var score = input
    if score == 318 { throw BroadError.rejected(score) }
    score = score &* 318
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0315_0(_ input: Int, _ seed: Int) throws -> Int {
  let result = try BroadOwner0315().broad_case_0315(input); return result.a &+ result.h &+ seed
}
@inline(never) public func broad_caller_0315_1(_ input: Int, _ seed: Int) -> Int {
  do { _ = try BroadOwner0315().broad_case_0315(input); let result = try BroadOwner0315().broad_case_0315(input); return result.a &+ result.h &+ seed } catch { return seed }
}

public struct BroadOwner0316 {
  @inline(never) public static func broad_case_0316(_ input: Int) throws -> BroadPayload {
    var score = input
    if score < 319 { throw BroadError.rejected(score) }
    score = score &+ 319
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0316_0(_ input: Int, _ seed: Int) -> Int {
  do { _ = try BroadOwner0316.broad_case_0316(input); let result = try BroadOwner0316.broad_case_0316(input); return result.value &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0316_1(_ input: Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0316.broad_case_0316(input); return result.value &+ seed } catch { return seed &- 319 }
}

public class BroadOwner0317 {
  @inline(never) public class func broad_case_0317(_ input: Int) throws -> BroadTag {
    var score = input
    if score > 320 { throw BroadError.rejected(score) }
    score = score &- 320
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0317_0(_ input: Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0317.broad_case_0317(input); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 320 }
}
@inline(never) public func broad_caller_0317_1(_ input: Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0317.broad_case_0317(input); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0318 { public init() {} }
public extension BroadOwner0318 {
  @inline(never) func broad_case_0318(_ input: Int) throws -> (Int, Bool) {
    var score = input
    if score == 321 { throw BroadError.rejected(score) }
    score = score ^ 321
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0318_0(_ input: Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0318().broad_case_0318(input); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0318_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0318().broad_case_0318(input); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0319 {
  @inline(never) public static func broad_case_0319(_ input: Int) throws -> BroadReference {
    var score = input
    if score < 322 { throw BroadError.rejected(score) }
    score = score &* 322
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0319_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0319.broad_case_0319(input); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0319_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0319.broad_case_0319(input); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0320 {
  @inline(never) public class func broad_case_0320(_ input: Int) throws -> String {
    var score = input
    if score > 323 { throw BroadError.rejected(score) }
    score = score &+ 323
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0320_0(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0320.broad_case_0320(input); return result.utf8.count &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0320_1(_ input: Int, _ seed: Int) throws -> String {
  return try BroadOwner0320.broad_case_0320(input)
}

public struct BroadOwner0321 { public init() {} }
public extension BroadOwner0321 {
  @inline(never) func broad_case_0321(_ input: Int) throws -> any BroadValue {
    var score = input
    if score == 324 { throw BroadError.rejected(score) }
    score = score &- 324
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0321_0(_ input: Int, _ seed: Int) throws -> any BroadValue {
  return try BroadOwner0321().broad_case_0321(input)
}
@inline(never) public func broad_caller_0321_1(_ input: Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0321().broad_case_0321(input); return result.value &+ seed } catch { return seed &- 324 }
}

public struct BroadOwner0322 {
  @inline(__always) public static func broad_case_0322(_ flag: Bool, _ narrow: UInt8) throws(BroadError) -> Void {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 325 { throw BroadError.rejected(score) }
    score = score ^ 325
    return ()
  }
}
@inline(never) public func broad_caller_0322_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0322.broad_case_0322(flag, narrow); return seed &+ seed } catch { return seed &- 325 }
}
@inline(never) public func broad_caller_0322_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0322.broad_case_0322(flag, narrow); return seed &+ seed } catch { return seed &- 325 }
}

public class BroadOwner0323 {
  @inline(never) public class func broad_case_0323(_ flag: Bool, _ narrow: UInt8) throws -> Bool {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 326 { throw BroadError.rejected(score) }
    score = score &* 326
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0323_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0323.broad_case_0323(flag, narrow); return (result ? 1 : 0) &+ seed } catch { return seed &- 326 }
}
@inline(never) public func broad_caller_0323_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0323.broad_case_0323(flag, narrow); return (result ? 1 : 0) &+ seed } catch { return seed &- 326 }
}

public struct BroadOwner0324 { public init() {} }
public extension BroadOwner0324 {
  @inline(never) func broad_case_0324(_ flag: Bool, _ narrow: UInt8) throws -> Int8 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 327 { throw BroadError.rejected(score) }
    score = score &+ 327
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0324_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0324().broad_case_0324(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 327 }
}
@inline(never) public func broad_caller_0324_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if let result = try? BroadOwner0324().broad_case_0324(flag, narrow) { return Int(truncatingIfNeeded: result) }; return seed
}

public struct BroadOwner0325 {
  @inline(never) public static func broad_case_0325(_ flag: Bool, _ narrow: UInt8) throws -> UInt8 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 328 { throw BroadError.rejected(score) }
    score = score &- 328
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0325_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if let result = try? BroadOwner0325.broad_case_0325(flag, narrow) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0325_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  let result = try! BroadOwner0325.broad_case_0325(flag, narrow); return Int(truncatingIfNeeded: result)
}

public class BroadOwner0326 {
  @inline(never) public class func broad_case_0326(_ flag: Bool, _ narrow: UInt8) throws -> Int16 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 329 { throw BroadError.rejected(score) }
    score = score ^ 329
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0326_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  let result = try! BroadOwner0326.broad_case_0326(flag, narrow); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0326_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  let result = try BroadOwner0326.broad_case_0326(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed
}

public struct BroadOwner0327 { public init() {} }
public extension BroadOwner0327 {
  @inline(never) func broad_case_0327(_ flag: Bool, _ narrow: UInt8) throws -> UInt16 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 330 { throw BroadError.rejected(score) }
    score = score &* 330
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0327_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  let result = try BroadOwner0327().broad_case_0327(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0327_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { _ = try BroadOwner0327().broad_case_0327(flag, narrow); let result = try BroadOwner0327().broad_case_0327(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public struct BroadOwner0328 {
  @inline(never) public static func broad_case_0328(_ flag: Bool, _ narrow: UInt8) throws -> Int32 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 331 { throw BroadError.rejected(score) }
    score = score &+ 331
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0328_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { _ = try BroadOwner0328.broad_case_0328(flag, narrow); let result = try BroadOwner0328.broad_case_0328(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0328_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0328.broad_case_0328(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 331 }
}

public class BroadOwner0329 {
  @inline(never) public class func broad_case_0329(_ flag: Bool, _ narrow: UInt8) throws(BroadError) -> UInt32 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 332 { throw BroadError.rejected(score) }
    score = score &- 332
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0329_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0329.broad_case_0329(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 332 }
}
@inline(never) public func broad_caller_0329_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0329.broad_case_0329(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0330 { public init() {} }
public extension BroadOwner0330 {
  @inline(never) func broad_case_0330(_ flag: Bool, _ narrow: UInt8) throws -> Int64 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 333 { throw BroadError.rejected(score) }
    score = score ^ 333
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0330_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0330().broad_case_0330(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0330_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0330().broad_case_0330(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0331 {
  @inline(never) public static func broad_case_0331(_ flag: Bool, _ narrow: UInt8) throws -> UInt64 {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 334 { throw BroadError.rejected(score) }
    score = score &* 334
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0331_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0331.broad_case_0331(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0331_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0331.broad_case_0331(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public class BroadOwner0332 {
  @inline(never) public class func broad_case_0332(_ flag: Bool, _ narrow: UInt8) throws -> Int {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 335 { throw BroadError.rejected(score) }
    score = score &+ 335
    return score
  }
}
@inline(never) public func broad_caller_0332_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0332.broad_case_0332(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0332_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  return try BroadOwner0332.broad_case_0332(flag, narrow)
}

public struct BroadOwner0333 { public init() {} }
public extension BroadOwner0333 {
  @inline(never) func broad_case_0333(_ flag: Bool, _ narrow: UInt8) throws -> UInt {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 336 { throw BroadError.rejected(score) }
    score = score &- 336
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0333_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> UInt {
  return try BroadOwner0333().broad_case_0333(flag, narrow)
}
@inline(never) public func broad_caller_0333_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0333().broad_case_0333(flag, narrow); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 336 }
}

public struct BroadOwner0334 {
  @inline(__always) public static func broad_case_0334(_ flag: Bool, _ narrow: UInt8) throws -> Float {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 337 { throw BroadError.rejected(score) }
    score = score ^ 337
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0334_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0334.broad_case_0334(flag, narrow); return Int(result) &+ seed } catch { return seed &- 337 }
}
@inline(never) public func broad_caller_0334_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0334.broad_case_0334(flag, narrow); return Int(result) &+ seed } catch { return seed &- 337 }
}

public class BroadOwner0335 {
  @inline(never) public class func broad_case_0335(_ flag: Bool, _ narrow: UInt8) throws -> Double {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 338 { throw BroadError.rejected(score) }
    score = score &* 338
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0335_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0335.broad_case_0335(flag, narrow); return Int(result) &+ seed } catch { return seed &- 338 }
}
@inline(never) public func broad_caller_0335_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0335.broad_case_0335(flag, narrow); return Int(result) &+ seed } catch { return seed &- 338 }
}

public struct BroadOwner0336 { public init() {} }
public extension BroadOwner0336 {
  @inline(never) func broad_case_0336(_ flag: Bool, _ narrow: UInt8) throws(BroadError) -> Int? {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 339 { throw BroadError.rejected(score) }
    score = score &+ 339
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0336_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0336().broad_case_0336(flag, narrow); return (result ?? seed) &+ seed } catch { return seed &- 339 }
}
@inline(never) public func broad_caller_0336_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if let result = try? BroadOwner0336().broad_case_0336(flag, narrow) { return result }; return seed
}

public struct BroadOwner0337 {
  @inline(never) public static func broad_case_0337(_ flag: Bool, _ narrow: UInt8) throws -> BroadSmall {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score < 340 { throw BroadError.rejected(score) }
    score = score &- 340
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0337_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if let result = try? BroadOwner0337.broad_case_0337(flag, narrow) { return result.value }; return seed
}
@inline(never) public func broad_caller_0337_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  let result = try! BroadOwner0337.broad_case_0337(flag, narrow); return result.value
}

public class BroadOwner0338 {
  @inline(never) public class func broad_case_0338(_ flag: Bool, _ narrow: UInt8) throws -> BroadLarge {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score > 341 { throw BroadError.rejected(score) }
    score = score ^ 341
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0338_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  let result = try! BroadOwner0338.broad_case_0338(flag, narrow); return result.a &+ result.h
}
@inline(never) public func broad_caller_0338_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  let result = try BroadOwner0338.broad_case_0338(flag, narrow); return result.a &+ result.h &+ seed
}

public struct BroadOwner0339 { public init() {} }
public extension BroadOwner0339 {
  @inline(never) func broad_case_0339(_ flag: Bool, _ narrow: UInt8) throws -> BroadPayload {
    var score = (flag ? 1 : 0) &+ Int(narrow)
    if score == 342 { throw BroadError.rejected(score) }
    score = score &* 342
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0339_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> Int {
  let result = try BroadOwner0339().broad_case_0339(flag, narrow); return result.value &+ seed
}
@inline(never) public func broad_caller_0339_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { _ = try BroadOwner0339().broad_case_0339(flag, narrow); let result = try BroadOwner0339().broad_case_0339(flag, narrow); return result.value &+ seed } catch { return seed }
}

public struct BroadOwner0340 {
  @inline(never) public static func broad_case_0340<T: BinaryInteger>(_ flag: Bool, _ narrow: UInt8, _ genericValue: T) throws -> BroadTag {
    var score = (flag ? 1 : 0) &+ Int(narrow) &+ Int(truncatingIfNeeded: genericValue)
    if score < 343 { throw BroadError.rejected(score) }
    score = score &+ 343
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0340_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { _ = try BroadOwner0340.broad_case_0340(flag, narrow, seed); let result = try BroadOwner0340.broad_case_0340(flag, narrow, seed); return (result == .even ? 2 : 3) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0340_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0340.broad_case_0340(flag, narrow, seed); return (result == .even ? 2 : 3) &+ seed } catch { return seed &- 343 }
}

public struct BroadOwner0341 {
  @inline(never) public static func broad_case_0341<T: BinaryInteger>(_ flag: Bool, _ narrow: UInt8, _ genericValue: T) throws -> (Int, Bool) {
    var score = (flag ? 1 : 0) &+ Int(narrow) &+ Int(truncatingIfNeeded: genericValue)
    if score > 344 { throw BroadError.rejected(score) }
    score = score &- 344
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0341_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0341.broad_case_0341(flag, narrow, seed); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 344 }
}
@inline(never) public func broad_caller_0341_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0341.broad_case_0341(flag, narrow, seed); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0342 {
  @inline(never) public static func broad_case_0342<T: BinaryInteger>(_ flag: Bool, _ narrow: UInt8, _ genericValue: T) throws -> BroadReference {
    var score = (flag ? 1 : 0) &+ Int(narrow) &+ Int(truncatingIfNeeded: genericValue)
    if score == 345 { throw BroadError.rejected(score) }
    score = score ^ 345
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0342_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0342.broad_case_0342(flag, narrow, seed); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0342_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0342.broad_case_0342(flag, narrow, seed); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0343 {
  @inline(never) public static func broad_case_0343<T: BinaryInteger>(_ flag: Bool, _ narrow: UInt8, _ genericValue: T) throws(BroadError) -> String {
    var score = (flag ? 1 : 0) &+ Int(narrow) &+ Int(truncatingIfNeeded: genericValue)
    if score < 346 { throw BroadError.rejected(score) }
    score = score &* 346
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0343_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0343.broad_case_0343(flag, narrow, seed); return result.utf8.count &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0343_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0343.broad_case_0343(flag, narrow, seed); return result.utf8.count &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0344 {
  @inline(never) public static func broad_case_0344<T: BinaryInteger>(_ flag: Bool, _ narrow: UInt8, _ genericValue: T) throws -> any BroadValue {
    var score = (flag ? 1 : 0) &+ Int(narrow) &+ Int(truncatingIfNeeded: genericValue)
    if score > 347 { throw BroadError.rejected(score) }
    score = score &+ 347
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0344_0(_ flag: Bool, _ narrow: UInt8, _ seed: Int) -> Int {
  do { let result = try BroadOwner0344.broad_case_0344(flag, narrow, seed); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0344_1(_ flag: Bool, _ narrow: UInt8, _ seed: Int) throws -> any BroadValue {
  return try BroadOwner0344.broad_case_0344(flag, narrow, seed)
}

public struct BroadOwner0345 {
  @inline(never) public static func broad_case_0345<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Void {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score == 348 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 348
    return ()
  }
}
@inline(never) public func broad_caller_0345_0(_ input: inout Int, _ seed: Int) throws -> Void {
  return try BroadOwner0345.broad_case_0345(&input, seed)
}
@inline(never) public func broad_caller_0345_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0345.broad_case_0345(&input, seed); return seed &+ seed } catch { return seed &- 348 }
}

public struct BroadOwner0346 {
  @inline(__always) public static func broad_case_0346<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Bool {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score < 349 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 349
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0346_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0346.broad_case_0346(&input, seed); return (result ? 1 : 0) &+ seed } catch { return seed &- 349 }
}
@inline(never) public func broad_caller_0346_1(_ input: inout Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0346.broad_case_0346(&input, seed); return (result ? 1 : 0) &+ seed } catch { return seed &- 349 }
}

public struct BroadOwner0347 {
  @inline(never) public static func broad_case_0347<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Int8 {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score > 350 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 350
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0347_0(_ input: inout Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0347.broad_case_0347(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 350 }
}
@inline(never) public func broad_caller_0347_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0347.broad_case_0347(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 350 }
}

public struct BroadOwner0348 {
  @inline(never) public static func broad_case_0348<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> UInt8 {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score == 351 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 351
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0348_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0348.broad_case_0348(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 351 }
}
@inline(never) public func broad_caller_0348_1(_ input: inout Int, _ seed: Int) -> Int {
  if let result = try? BroadOwner0348.broad_case_0348(&input, seed) { return Int(truncatingIfNeeded: result) }; return seed
}

public struct BroadOwner0349 {
  @inline(never) public static func broad_case_0349<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Int16 {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score < 352 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 352
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0349_0(_ input: inout Int, _ seed: Int) -> Int {
  if let result = try? BroadOwner0349.broad_case_0349(&input, seed) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0349_1(_ input: inout Int, _ seed: Int) -> Int {
  let result = try! BroadOwner0349.broad_case_0349(&input, seed); return Int(truncatingIfNeeded: result)
}

public struct BroadOwner0350 {
  @inline(never) public static func broad_case_0350<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws(BroadError) -> UInt16 {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score > 353 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 353
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0350_0(_ input: inout Int, _ seed: Int) -> Int {
  let result = try! BroadOwner0350.broad_case_0350(&input, seed); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0350_1(_ input: inout Int, _ seed: Int) throws -> Int {
  let result = try BroadOwner0350.broad_case_0350(&input, seed); return Int(truncatingIfNeeded: result) &+ seed
}

public struct BroadOwner0351 {
  @inline(never) public static func broad_case_0351<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Int32 {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score == 354 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 354
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0351_0(_ input: inout Int, _ seed: Int) throws -> Int {
  let result = try BroadOwner0351.broad_case_0351(&input, seed); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0351_1(_ input: inout Int, _ seed: Int) -> Int {
  do { _ = try BroadOwner0351.broad_case_0351(&input, seed); let result = try BroadOwner0351.broad_case_0351(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public struct BroadOwner0352 {
  @inline(never) public static func broad_case_0352<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> UInt32 {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score < 355 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 355
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0352_0(_ input: inout Int, _ seed: Int) -> Int {
  do { _ = try BroadOwner0352.broad_case_0352(&input, seed); let result = try BroadOwner0352.broad_case_0352(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0352_1(_ input: inout Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0352.broad_case_0352(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 355 }
}

public struct BroadOwner0353 {
  @inline(never) public static func broad_case_0353<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Int64 {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score > 356 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 356
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0353_0(_ input: inout Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0353.broad_case_0353(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 356 }
}
@inline(never) public func broad_caller_0353_1(_ input: inout Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0353.broad_case_0353(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0354 {
  @inline(never) public static func broad_case_0354<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> UInt64 {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score == 357 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 357
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0354_0(_ input: inout Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0354.broad_case_0354(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0354_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0354.broad_case_0354(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0355 {
  @inline(never) public static func broad_case_0355<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Int {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score < 358 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 358
    return score
  }
}
@inline(never) public func broad_caller_0355_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0355.broad_case_0355(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0355_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0355.broad_case_0355(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0356 {
  @inline(never) public static func broad_case_0356<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> UInt {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score > 359 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 359
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0356_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0356.broad_case_0356(&input, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0356_1(_ input: inout Int, _ seed: Int) throws -> UInt {
  return try BroadOwner0356.broad_case_0356(&input, seed)
}

public struct BroadOwner0357 {
  @inline(never) public static func broad_case_0357<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws(BroadError) -> Float {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score == 360 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 360
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0357_0(_ input: inout Int, _ seed: Int) throws -> Float {
  return try BroadOwner0357.broad_case_0357(&input, seed)
}
@inline(never) public func broad_caller_0357_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0357.broad_case_0357(&input, seed); return Int(result) &+ seed } catch { return seed &- 360 }
}

public struct BroadOwner0358 {
  @inline(__always) public static func broad_case_0358<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Double {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score < 361 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 361
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0358_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0358.broad_case_0358(&input, seed); return Int(result) &+ seed } catch { return seed &- 361 }
}
@inline(never) public func broad_caller_0358_1(_ input: inout Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0358.broad_case_0358(&input, seed); return Int(result) &+ seed } catch { return seed &- 361 }
}

public struct BroadOwner0359 {
  @inline(never) public static func broad_case_0359<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> Int? {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score > 362 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 362
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0359_0(_ input: inout Int, _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0359.broad_case_0359(&input, seed); return (result ?? seed) &+ seed } catch { return seed &- 362 }
}
@inline(never) public func broad_caller_0359_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0359.broad_case_0359(&input, seed); return (result ?? seed) &+ seed } catch { return seed &- 362 }
}

public struct BroadOwner0360 {
  @inline(never) public static func broad_case_0360<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> BroadSmall {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score == 363 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 363
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0360_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0360.broad_case_0360(&input, seed); return result.value &+ seed } catch { return seed &- 363 }
}
@inline(never) public func broad_caller_0360_1(_ input: inout Int, _ seed: Int) -> Int {
  if let result = try? BroadOwner0360.broad_case_0360(&input, seed) { return result.value }; return seed
}

public struct BroadOwner0361 {
  @inline(never) public static func broad_case_0361<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> BroadLarge {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score < 364 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 364
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0361_0(_ input: inout Int, _ seed: Int) -> Int {
  if let result = try? BroadOwner0361.broad_case_0361(&input, seed) { return result.a &+ result.h }; return seed
}
@inline(never) public func broad_caller_0361_1(_ input: inout Int, _ seed: Int) -> Int {
  let result = try! BroadOwner0361.broad_case_0361(&input, seed); return result.a &+ result.h
}

public struct BroadOwner0362 {
  @inline(never) public static func broad_case_0362<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> BroadPayload {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score > 365 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 365
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0362_0(_ input: inout Int, _ seed: Int) -> Int {
  let result = try! BroadOwner0362.broad_case_0362(&input, seed); return result.value
}
@inline(never) public func broad_caller_0362_1(_ input: inout Int, _ seed: Int) throws -> Int {
  let result = try BroadOwner0362.broad_case_0362(&input, seed); return result.value &+ seed
}

public struct BroadOwner0363 {
  @inline(never) public static func broad_case_0363<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> BroadTag {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score == 366 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 366
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0363_0(_ input: inout Int, _ seed: Int) throws -> Int {
  let result = try BroadOwner0363.broad_case_0363(&input, seed); return (result == .even ? 2 : 3) &+ seed
}
@inline(never) public func broad_caller_0363_1(_ input: inout Int, _ seed: Int) -> Int {
  do { _ = try BroadOwner0363.broad_case_0363(&input, seed); let result = try BroadOwner0363.broad_case_0363(&input, seed); return (result == .even ? 2 : 3) &+ seed } catch { return seed }
}

public struct BroadOwner0364 {
  @inline(never) public static func broad_case_0364<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws(BroadError) -> (Int, Bool) {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score < 367 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &+ 367
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0364_0(_ input: inout Int, _ seed: Int) -> Int {
  do { _ = try BroadOwner0364.broad_case_0364(&input, seed); let result = try BroadOwner0364.broad_case_0364(&input, seed); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0364_1(_ input: inout Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0364.broad_case_0364(&input, seed); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed &- 367 }
}

public struct BroadOwner0365 {
  @inline(never) public static func broad_case_0365<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> BroadReference {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score > 368 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &- 368
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0365_0(_ input: inout Int, _ seed: Int) -> Int {
  if seed == 0 { return 7 }; do { let result = try BroadOwner0365.broad_case_0365(&input, seed); return result.value &+ seed } catch { return seed &- 368 }
}
@inline(never) public func broad_caller_0365_1(_ input: inout Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0365.broad_case_0365(&input, seed); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public struct BroadOwner0366 {
  @inline(never) public static func broad_case_0366<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> String {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score == 369 { throw BroadError.rejected(score) }
    input &+= 1
    score = score ^ 369
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0366_0(_ input: inout Int, _ seed: Int) -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try BroadOwner0366.broad_case_0366(&input, seed); return result.utf8.count &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0366_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0366.broad_case_0366(&input, seed); return result.utf8.count &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public struct BroadOwner0367 {
  @inline(never) public static func broad_case_0367<T: BinaryInteger>(_ input: inout Int, _ genericValue: T) throws -> any BroadValue {
    var score = input &+ Int(truncatingIfNeeded: genericValue)
    if score < 370 { throw BroadError.rejected(score) }
    input &+= 1
    score = score &* 370
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0367_0(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0367.broad_case_0367(&input, seed); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0367_1(_ input: inout Int, _ seed: Int) -> Int {
  do { let result = try BroadOwner0367.broad_case_0367(&input, seed); return result.value &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public struct BroadOwner0368 {
  @inline(never) public static func broad_case_0368<T: BinaryInteger>(_ text: String, _ values: [Int], _ genericValue: T) throws -> Void {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ Int(truncatingIfNeeded: genericValue)
    if score > 371 { throw BroadError.rejected(score) }
    score = score &+ 371
    return ()
  }
}
@inline(never) public func broad_caller_0368_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  do { let result = try BroadOwner0368.broad_case_0368(text, values, seed); return seed &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0368_1(_ text: String, _ values: [Int], _ seed: Int) throws -> Void {
  return try BroadOwner0368.broad_case_0368(text, values, seed)
}

public struct BroadOwner0369 {
  @inline(never) public static func broad_case_0369<T: BinaryInteger>(_ text: String, _ values: [Int], _ genericValue: T) throws -> Bool {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ Int(truncatingIfNeeded: genericValue)
    if score == 372 { throw BroadError.rejected(score) }
    score = score &- 372
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0369_0(_ text: String, _ values: [Int], _ seed: Int) throws -> Bool {
  return try BroadOwner0369.broad_case_0369(text, values, seed)
}
@inline(never) public func broad_caller_0369_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  do { let result = try BroadOwner0369.broad_case_0369(text, values, seed); return (result ? 1 : 0) &+ seed } catch { return seed &- 372 }
}

public struct BroadOwner0370 {
  @inline(__always) public static func broad_case_0370<T: BinaryInteger>(_ text: String, _ values: [Int], _ genericValue: T) throws -> Int8 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ Int(truncatingIfNeeded: genericValue)
    if score < 373 { throw BroadError.rejected(score) }
    score = score ^ 373
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0370_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  do { let result = try BroadOwner0370.broad_case_0370(text, values, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 373 }
}
@inline(never) public func broad_caller_0370_1(_ text: String, _ values: [Int], _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0370.broad_case_0370(text, values, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 373 }
}

public struct BroadOwner0371 {
  @inline(never) public static func broad_case_0371<T: BinaryInteger>(_ text: String, _ values: [Int], _ genericValue: T) throws(BroadError) -> UInt8 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ Int(truncatingIfNeeded: genericValue)
    if score > 374 { throw BroadError.rejected(score) }
    score = score &* 374
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0371_0(_ text: String, _ values: [Int], _ seed: Int, _ cleanup: inout Int) -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try BroadOwner0371.broad_case_0371(text, values, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 374 }
}
@inline(never) public func broad_caller_0371_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  do { let result = try BroadOwner0371.broad_case_0371(text, values, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 374 }
}

public struct BroadOwner0372 {
  @inline(never) public static func broad_case_0372<T: BinaryInteger>(_ text: String, _ values: [Int], _ genericValue: T) throws -> Int16 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ Int(truncatingIfNeeded: genericValue)
    if score == 375 { throw BroadError.rejected(score) }
    score = score &+ 375
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0372_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  do { let result = try BroadOwner0372.broad_case_0372(text, values, seed); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 375 }
}
@inline(never) public func broad_caller_0372_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  if let result = try? BroadOwner0372.broad_case_0372(text, values, seed) { return Int(truncatingIfNeeded: result) }; return seed
}

public struct BroadOwner0373 {
  @inline(never) public static func broad_case_0373<T: BinaryInteger>(_ text: String, _ values: [Int], _ genericValue: T) throws -> UInt16 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ Int(truncatingIfNeeded: genericValue)
    if score < 376 { throw BroadError.rejected(score) }
    score = score &- 376
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0373_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  if let result = try? BroadOwner0373.broad_case_0373(text, values, seed) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0373_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let result = try! BroadOwner0373.broad_case_0373(text, values, seed); return Int(truncatingIfNeeded: result)
}

public struct BroadOwner0374 {
  @inline(never) public static func broad_case_0374<T: BinaryInteger>(_ text: String, _ values: [Int], _ genericValue: T) throws -> Int32 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ Int(truncatingIfNeeded: genericValue)
    if score > 377 { throw BroadError.rejected(score) }
    score = score ^ 377
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0374_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let result = try! BroadOwner0374.broad_case_0374(text, values, seed); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0374_1(_ text: String, _ values: [Int], _ seed: Int) throws -> Int {
  let result = try BroadOwner0374.broad_case_0374(text, values, seed); return Int(truncatingIfNeeded: result) &+ seed
}

public protocol BroadOwner0375Protocol { func broad_case_0375(_ text: String, _ values: [Int]) throws -> UInt32 }
public struct BroadOwner0375: BroadOwner0375Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0375(_ text: String, _ values: [Int]) throws -> UInt32 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 378 { throw BroadError.rejected(score) }
    score = score &* 378
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0375_0(_ text: String, _ values: [Int], _ seed: Int) throws -> Int {
  let receiver: any BroadOwner0375Protocol = BroadOwner0375(seed)
  let result = try receiver.broad_case_0375(text, values); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0375_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0375Protocol = BroadOwner0375(seed)
  do { _ = try receiver.broad_case_0375(text, values); let result = try receiver.broad_case_0375(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public protocol BroadOwner0376Protocol { func broad_case_0376(_ text: String, _ values: [Int]) throws -> Int64 }
public struct BroadOwner0376: BroadOwner0376Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0376(_ text: String, _ values: [Int]) throws -> Int64 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 379 { throw BroadError.rejected(score) }
    score = score &+ 379
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0376_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0376Protocol = BroadOwner0376(seed)
  do { _ = try receiver.broad_case_0376(text, values); let result = try receiver.broad_case_0376(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0376_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0376Protocol = BroadOwner0376(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0376(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 379 }
}

public protocol BroadOwner0377Protocol { func broad_case_0377(_ text: String, _ values: [Int]) throws -> UInt64 }
public struct BroadOwner0377: BroadOwner0377Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0377(_ text: String, _ values: [Int]) throws -> UInt64 {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 380 { throw BroadError.rejected(score) }
    score = score &- 380
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0377_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0377Protocol = BroadOwner0377(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0377(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 380 }
}
@inline(never) public func broad_caller_0377_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0377Protocol = BroadOwner0377(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0377(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public protocol BroadOwner0378Protocol { func broad_case_0378(_ text: String, _ values: [Int]) throws(BroadError) -> Int }
public struct BroadOwner0378: BroadOwner0378Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0378(_ text: String, _ values: [Int]) throws(BroadError) -> Int {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 381 { throw BroadError.rejected(score) }
    score = score ^ 381
    return score
  }
}
@inline(never) public func broad_caller_0378_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0378Protocol = BroadOwner0378(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0378(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0378_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0378Protocol = BroadOwner0378(seed)
  do { let result = try receiver.broad_case_0378(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public protocol BroadOwner0379Protocol { func broad_case_0379(_ text: String, _ values: [Int]) throws -> UInt }
public struct BroadOwner0379: BroadOwner0379Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0379(_ text: String, _ values: [Int]) throws -> UInt {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 382 { throw BroadError.rejected(score) }
    score = score &* 382
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0379_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0379Protocol = BroadOwner0379(seed)
  do { let result = try receiver.broad_case_0379(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0379_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0379Protocol = BroadOwner0379(seed)
  do { let result = try receiver.broad_case_0379(text, values); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public protocol BroadOwner0380Protocol { func broad_case_0380(_ text: String, _ values: [Int]) throws -> Float }
public struct BroadOwner0380: BroadOwner0380Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0380(_ text: String, _ values: [Int]) throws -> Float {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 383 { throw BroadError.rejected(score) }
    score = score &+ 383
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0380_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0380Protocol = BroadOwner0380(seed)
  do { let result = try receiver.broad_case_0380(text, values); return Int(result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0380_1(_ text: String, _ values: [Int], _ seed: Int) throws -> Float {
  let receiver: any BroadOwner0380Protocol = BroadOwner0380(seed)
  return try receiver.broad_case_0380(text, values)
}

public protocol BroadOwner0381Protocol { func broad_case_0381(_ text: String, _ values: [Int]) throws -> Double }
public struct BroadOwner0381: BroadOwner0381Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0381(_ text: String, _ values: [Int]) throws -> Double {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 384 { throw BroadError.rejected(score) }
    score = score &- 384
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0381_0(_ text: String, _ values: [Int], _ seed: Int) throws -> Double {
  let receiver: any BroadOwner0381Protocol = BroadOwner0381(seed)
  return try receiver.broad_case_0381(text, values)
}
@inline(never) public func broad_caller_0381_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0381Protocol = BroadOwner0381(seed)
  do { let result = try receiver.broad_case_0381(text, values); return Int(result) &+ seed } catch { return seed &- 384 }
}

public protocol BroadOwner0382Protocol { func broad_case_0382(_ text: String, _ values: [Int]) throws -> Int? }
public struct BroadOwner0382: BroadOwner0382Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0382(_ text: String, _ values: [Int]) throws -> Int? {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 385 { throw BroadError.rejected(score) }
    score = score ^ 385
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0382_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0382Protocol = BroadOwner0382(seed)
  do { let result = try receiver.broad_case_0382(text, values); return (result ?? seed) &+ seed } catch { return seed &- 385 }
}
@inline(never) public func broad_caller_0382_1(_ text: String, _ values: [Int], _ seed: Int, _ cleanup: inout Int) -> Int {
  let receiver: any BroadOwner0382Protocol = BroadOwner0382(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0382(text, values); return (result ?? seed) &+ seed } catch { return seed &- 385 }
}

public protocol BroadOwner0383Protocol { func broad_case_0383(_ text: String, _ values: [Int]) throws -> BroadSmall }
public struct BroadOwner0383: BroadOwner0383Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0383(_ text: String, _ values: [Int]) throws -> BroadSmall {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 386 { throw BroadError.rejected(score) }
    score = score &* 386
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0383_0(_ text: String, _ values: [Int], _ seed: Int, _ cleanup: inout Int) -> Int {
  let receiver: any BroadOwner0383Protocol = BroadOwner0383(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0383(text, values); return result.value &+ seed } catch { return seed &- 386 }
}
@inline(never) public func broad_caller_0383_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0383Protocol = BroadOwner0383(seed)
  do { let result = try receiver.broad_case_0383(text, values); return result.value &+ seed } catch { return seed &- 386 }
}

public protocol BroadOwner0384Protocol { func broad_case_0384(_ text: String, _ values: [Int]) throws -> BroadLarge }
public struct BroadOwner0384: BroadOwner0384Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0384(_ text: String, _ values: [Int]) throws -> BroadLarge {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 387 { throw BroadError.rejected(score) }
    score = score &+ 387
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0384_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0384Protocol = BroadOwner0384(seed)
  do { let result = try receiver.broad_case_0384(text, values); return result.a &+ result.h &+ seed } catch { return seed &- 387 }
}
@inline(never) public func broad_caller_0384_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0384Protocol = BroadOwner0384(seed)
  if let result = try? receiver.broad_case_0384(text, values) { return result.a &+ result.h }; return seed
}

public protocol BroadOwner0385Protocol { func broad_case_0385(_ text: String, _ values: [Int]) throws(BroadError) -> BroadPayload }
public struct BroadOwner0385: BroadOwner0385Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0385(_ text: String, _ values: [Int]) throws(BroadError) -> BroadPayload {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 388 { throw BroadError.rejected(score) }
    score = score &- 388
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0385_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0385Protocol = BroadOwner0385(seed)
  if let result = try? receiver.broad_case_0385(text, values) { return result.value }; return seed
}
@inline(never) public func broad_caller_0385_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0385Protocol = BroadOwner0385(seed)
  let result = try! receiver.broad_case_0385(text, values); return result.value
}

public protocol BroadOwner0386Protocol { func broad_case_0386(_ text: String, _ values: [Int]) throws -> BroadTag }
public struct BroadOwner0386: BroadOwner0386Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0386(_ text: String, _ values: [Int]) throws -> BroadTag {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 389 { throw BroadError.rejected(score) }
    score = score ^ 389
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0386_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0386Protocol = BroadOwner0386(seed)
  let result = try! receiver.broad_case_0386(text, values); return (result == .even ? 2 : 3)
}
@inline(never) public func broad_caller_0386_1(_ text: String, _ values: [Int], _ seed: Int) throws -> Int {
  let receiver: any BroadOwner0386Protocol = BroadOwner0386(seed)
  let result = try receiver.broad_case_0386(text, values); return (result == .even ? 2 : 3) &+ seed
}

public protocol BroadOwner0387Protocol { func broad_case_0387(_ text: String, _ values: [Int]) throws -> (Int, Bool) }
public struct BroadOwner0387: BroadOwner0387Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0387(_ text: String, _ values: [Int]) throws -> (Int, Bool) {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 390 { throw BroadError.rejected(score) }
    score = score &* 390
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0387_0(_ text: String, _ values: [Int], _ seed: Int) throws -> Int {
  let receiver: any BroadOwner0387Protocol = BroadOwner0387(seed)
  let result = try receiver.broad_case_0387(text, values); return result.0 &+ (result.1 ? 1 : 0) &+ seed
}
@inline(never) public func broad_caller_0387_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0387Protocol = BroadOwner0387(seed)
  do { _ = try receiver.broad_case_0387(text, values); let result = try receiver.broad_case_0387(text, values); return result.0 &+ (result.1 ? 1 : 0) &+ seed } catch { return seed }
}

public protocol BroadOwner0388Protocol { func broad_case_0388(_ text: String, _ values: [Int]) throws -> BroadReference }
public struct BroadOwner0388: BroadOwner0388Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0388(_ text: String, _ values: [Int]) throws -> BroadReference {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score < 391 { throw BroadError.rejected(score) }
    score = score &+ 391
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0388_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0388Protocol = BroadOwner0388(seed)
  do { _ = try receiver.broad_case_0388(text, values); let result = try receiver.broad_case_0388(text, values); return result.value &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0388_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0388Protocol = BroadOwner0388(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0388(text, values); return result.value &+ seed } catch { return seed &- 391 }
}

public protocol BroadOwner0389Protocol { func broad_case_0389(_ text: String, _ values: [Int]) throws -> String }
public struct BroadOwner0389: BroadOwner0389Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0389(_ text: String, _ values: [Int]) throws -> String {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score > 392 { throw BroadError.rejected(score) }
    score = score &- 392
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0389_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0389Protocol = BroadOwner0389(seed)
  if seed == 0 { return 7 }; do { let result = try receiver.broad_case_0389(text, values); return result.utf8.count &+ seed } catch { return seed &- 392 }
}
@inline(never) public func broad_caller_0389_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0389Protocol = BroadOwner0389(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0389(text, values); return result.utf8.count &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public protocol BroadOwner0390Protocol { func broad_case_0390(_ text: String, _ values: [Int]) throws -> any BroadValue }
public struct BroadOwner0390: BroadOwner0390Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0390(_ text: String, _ values: [Int]) throws -> any BroadValue {
    var score = text.utf8.count &+ values.reduce(0, &+) &+ bias
    if score == 393 { throw BroadError.rejected(score) }
    score = score ^ 393
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0390_0(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0390Protocol = BroadOwner0390(seed)
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try receiver.broad_case_0390(text, values); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0390_1(_ text: String, _ values: [Int], _ seed: Int) -> Int {
  let receiver: any BroadOwner0390Protocol = BroadOwner0390(seed)
  do { let result = try receiver.broad_case_0390(text, values); return result.value &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public protocol BroadOwner0391Protocol { func broad_case_0391(_ single: Float, _ double: Double) throws -> Void }
public struct BroadOwner0391: BroadOwner0391Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0391(_ single: Float, _ double: Double) throws -> Void {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 394 { throw BroadError.rejected(score) }
    score = score &* 394
    return ()
  }
}
@inline(never) public func broad_caller_0391_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0391Protocol = BroadOwner0391(seed)
  do { let result = try receiver.broad_case_0391(single, double); return seed &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0391_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0391Protocol = BroadOwner0391(seed)
  do { let result = try receiver.broad_case_0391(single, double); return seed &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public protocol BroadOwner0392Protocol { func broad_case_0392(_ single: Float, _ double: Double) throws(BroadError) -> Bool }
public struct BroadOwner0392: BroadOwner0392Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0392(_ single: Float, _ double: Double) throws(BroadError) -> Bool {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 395 { throw BroadError.rejected(score) }
    score = score &+ 395
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0392_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0392Protocol = BroadOwner0392(seed)
  do { let result = try receiver.broad_case_0392(single, double); return (result ? 1 : 0) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0392_1(_ single: Float, _ double: Double, _ seed: Int) throws -> Bool {
  let receiver: any BroadOwner0392Protocol = BroadOwner0392(seed)
  return try receiver.broad_case_0392(single, double)
}

public protocol BroadOwner0393Protocol { func broad_case_0393(_ single: Float, _ double: Double) throws -> Int8 }
public struct BroadOwner0393: BroadOwner0393Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0393(_ single: Float, _ double: Double) throws -> Int8 {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 396 { throw BroadError.rejected(score) }
    score = score &- 396
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0393_0(_ single: Float, _ double: Double, _ seed: Int) throws -> Int8 {
  let receiver: any BroadOwner0393Protocol = BroadOwner0393(seed)
  return try receiver.broad_case_0393(single, double)
}
@inline(never) public func broad_caller_0393_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0393Protocol = BroadOwner0393(seed)
  do { let result = try receiver.broad_case_0393(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 396 }
}

public protocol BroadOwner0394Protocol { func broad_case_0394(_ single: Float, _ double: Double) throws -> UInt8 }
public struct BroadOwner0394: BroadOwner0394Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0394(_ single: Float, _ double: Double) throws -> UInt8 {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 397 { throw BroadError.rejected(score) }
    score = score ^ 397
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0394_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0394Protocol = BroadOwner0394(seed)
  do { let result = try receiver.broad_case_0394(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 397 }
}
@inline(never) public func broad_caller_0394_1(_ single: Float, _ double: Double, _ seed: Int, _ cleanup: inout Int) -> Int {
  let receiver: any BroadOwner0394Protocol = BroadOwner0394(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0394(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 397 }
}

public protocol BroadOwner0395Protocol { func broad_case_0395(_ single: Float, _ double: Double) throws -> Int16 }
public struct BroadOwner0395: BroadOwner0395Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0395(_ single: Float, _ double: Double) throws -> Int16 {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 398 { throw BroadError.rejected(score) }
    score = score &* 398
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0395_0(_ single: Float, _ double: Double, _ seed: Int, _ cleanup: inout Int) -> Int {
  let receiver: any BroadOwner0395Protocol = BroadOwner0395(seed)
  defer { broad_cleanup(&cleanup) }; do { let result = try receiver.broad_case_0395(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 398 }
}
@inline(never) public func broad_caller_0395_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0395Protocol = BroadOwner0395(seed)
  do { let result = try receiver.broad_case_0395(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 398 }
}

public protocol BroadOwner0396Protocol { func broad_case_0396(_ single: Float, _ double: Double) throws -> UInt16 }
public struct BroadOwner0396: BroadOwner0396Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0396(_ single: Float, _ double: Double) throws -> UInt16 {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 399 { throw BroadError.rejected(score) }
    score = score &+ 399
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0396_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0396Protocol = BroadOwner0396(seed)
  do { let result = try receiver.broad_case_0396(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 399 }
}
@inline(never) public func broad_caller_0396_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0396Protocol = BroadOwner0396(seed)
  if let result = try? receiver.broad_case_0396(single, double) { return Int(truncatingIfNeeded: result) }; return seed
}

public protocol BroadOwner0397Protocol { func broad_case_0397(_ single: Float, _ double: Double) throws -> Int32 }
public struct BroadOwner0397: BroadOwner0397Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0397(_ single: Float, _ double: Double) throws -> Int32 {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 400 { throw BroadError.rejected(score) }
    score = score &- 400
    return Int32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0397_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0397Protocol = BroadOwner0397(seed)
  if let result = try? receiver.broad_case_0397(single, double) { return Int(truncatingIfNeeded: result) }; return seed
}
@inline(never) public func broad_caller_0397_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0397Protocol = BroadOwner0397(seed)
  let result = try! receiver.broad_case_0397(single, double); return Int(truncatingIfNeeded: result)
}

public protocol BroadOwner0398Protocol { func broad_case_0398(_ single: Float, _ double: Double) throws -> UInt32 }
public struct BroadOwner0398: BroadOwner0398Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0398(_ single: Float, _ double: Double) throws -> UInt32 {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 401 { throw BroadError.rejected(score) }
    score = score ^ 401
    return UInt32(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0398_0(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0398Protocol = BroadOwner0398(seed)
  let result = try! receiver.broad_case_0398(single, double); return Int(truncatingIfNeeded: result)
}
@inline(never) public func broad_caller_0398_1(_ single: Float, _ double: Double, _ seed: Int) throws -> Int {
  let receiver: any BroadOwner0398Protocol = BroadOwner0398(seed)
  let result = try receiver.broad_case_0398(single, double); return Int(truncatingIfNeeded: result) &+ seed
}

public protocol BroadOwner0399Protocol { func broad_case_0399(_ single: Float, _ double: Double) throws(BroadError) -> Int64 }
public struct BroadOwner0399: BroadOwner0399Protocol { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0399(_ single: Float, _ double: Double) throws(BroadError) -> Int64 {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 402 { throw BroadError.rejected(score) }
    score = score &* 402
    return Int64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0399_0(_ single: Float, _ double: Double, _ seed: Int) throws -> Int {
  let receiver: any BroadOwner0399Protocol = BroadOwner0399(seed)
  let result = try receiver.broad_case_0399(single, double); return Int(truncatingIfNeeded: result) &+ seed
}
@inline(never) public func broad_caller_0399_1(_ single: Float, _ double: Double, _ seed: Int) -> Int {
  let receiver: any BroadOwner0399Protocol = BroadOwner0399(seed)
  do { _ = try receiver.broad_case_0399(single, double); let result = try receiver.broad_case_0399(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}

public actor BroadOwner0400 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0400(_ single: Float, _ double: Double) async throws -> UInt64 {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 403 { throw BroadError.rejected(score) }
    score = score &+ 403
    return UInt64(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0400_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { _ = try await BroadOwner0400(seed).broad_case_0400(single, double); let result = try await BroadOwner0400(seed).broad_case_0400(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0400_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  if seed == 0 { return 7 }; do { let result = try await BroadOwner0400(seed).broad_case_0400(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 403 }
}

public actor BroadOwner0401 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0401(_ single: Float, _ double: Double) async throws -> Int {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 404 { throw BroadError.rejected(score) }
    score = score &- 404
    return score
  }
}
@inline(never) public func broad_caller_0401_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  if seed == 0 { return 7 }; do { let result = try await BroadOwner0401(seed).broad_case_0401(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 404 }
}
@inline(never) public func broad_caller_0401_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try await BroadOwner0401(seed).broad_case_0401(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public actor BroadOwner0402 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0402(_ single: Float, _ double: Double) async throws -> UInt {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 405 { throw BroadError.rejected(score) }
    score = score ^ 405
    return UInt(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0402_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try await BroadOwner0402(seed).broad_case_0402(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0402_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0402(seed).broad_case_0402(single, double); return Int(truncatingIfNeeded: result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public actor BroadOwner0403 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0403(_ single: Float, _ double: Double) async throws -> Float {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 406 { throw BroadError.rejected(score) }
    score = score &* 406
    return Float(score) / 3
  }
}
@inline(never) public func broad_caller_0403_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0403(seed).broad_case_0403(single, double); return Int(result) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0403_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0403(seed).broad_case_0403(single, double); return Int(result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public actor BroadOwner0404 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0404(_ single: Float, _ double: Double) async throws -> Double {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 407 { throw BroadError.rejected(score) }
    score = score &+ 407
    return Double(score) / 3
  }
}
@inline(never) public func broad_caller_0404_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0404(seed).broad_case_0404(single, double); return Int(result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0404_1(_ single: Float, _ double: Double, _ seed: Int) async throws -> Double {
  return try await BroadOwner0404(seed).broad_case_0404(single, double)
}

public actor BroadOwner0405 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0405(_ single: Float, _ double: Double) async throws -> Int? {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 408 { throw BroadError.rejected(score) }
    score = score &- 408
    return score == 0 ? nil : score
  }
}
@inline(never) public func broad_caller_0405_0(_ single: Float, _ double: Double, _ seed: Int) async throws -> Int? {
  return try await BroadOwner0405(seed).broad_case_0405(single, double)
}
@inline(never) public func broad_caller_0405_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0405(seed).broad_case_0405(single, double); return (result ?? seed) &+ seed } catch { return seed &- 408 }
}

public actor BroadOwner0406 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0406(_ single: Float, _ double: Double) async throws(BroadError) -> BroadSmall {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 409 { throw BroadError.rejected(score) }
    score = score ^ 409
    return BroadSmall(score, score &+ 1)
  }
}
@inline(never) public func broad_caller_0406_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0406(seed).broad_case_0406(single, double); return result.value &+ seed } catch { return seed &- 409 }
}
@inline(never) public func broad_caller_0406_1(_ single: Float, _ double: Double, _ seed: Int, _ cleanup: inout Int) async -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try await BroadOwner0406(seed).broad_case_0406(single, double); return result.value &+ seed } catch { return seed &- 409 }
}

public actor BroadOwner0407 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0407(_ single: Float, _ double: Double) async throws -> BroadLarge {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 410 { throw BroadError.rejected(score) }
    score = score &* 410
    return BroadLarge(score)
  }
}
@inline(never) public func broad_caller_0407_0(_ single: Float, _ double: Double, _ seed: Int, _ cleanup: inout Int) async -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try await BroadOwner0407(seed).broad_case_0407(single, double); return result.a &+ result.h &+ seed } catch { return seed &- 410 }
}
@inline(never) public func broad_caller_0407_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0407(seed).broad_case_0407(single, double); return result.a &+ result.h &+ seed } catch { return seed &- 410 }
}

public actor BroadOwner0408 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0408(_ single: Float, _ double: Double) async throws -> BroadPayload {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 411 { throw BroadError.rejected(score) }
    score = score &+ 411
    return .payload(score)
  }
}
@inline(never) public func broad_caller_0408_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0408(seed).broad_case_0408(single, double); return result.value &+ seed } catch { return seed &- 411 }
}
@inline(never) public func broad_caller_0408_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  if let result = try? await BroadOwner0408(seed).broad_case_0408(single, double) { return result.value }; return seed
}

public actor BroadOwner0409 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0409(_ single: Float, _ double: Double) async throws -> BroadTag {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 412 { throw BroadError.rejected(score) }
    score = score &- 412
    return score & 1 == 0 ? .even : .odd
  }
}
@inline(never) public func broad_caller_0409_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  if let result = try? await BroadOwner0409(seed).broad_case_0409(single, double) { return (result == .even ? 2 : 3) }; return seed
}
@inline(never) public func broad_caller_0409_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  let result = try! await BroadOwner0409(seed).broad_case_0409(single, double); return (result == .even ? 2 : 3)
}

public actor BroadOwner0410 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0410(_ single: Float, _ double: Double) async throws -> (Int, Bool) {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 413 { throw BroadError.rejected(score) }
    score = score ^ 413
    return (score, score > 0)
  }
}
@inline(never) public func broad_caller_0410_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  let result = try! await BroadOwner0410(seed).broad_case_0410(single, double); return result.0 &+ (result.1 ? 1 : 0)
}
@inline(never) public func broad_caller_0410_1(_ single: Float, _ double: Double, _ seed: Int) async throws -> Int {
  let result = try await BroadOwner0410(seed).broad_case_0410(single, double); return result.0 &+ (result.1 ? 1 : 0) &+ seed
}

public actor BroadOwner0411 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0411(_ single: Float, _ double: Double) async throws -> BroadReference {
    var score = Int(single) &+ Int(double) &+ bias
    if score == 414 { throw BroadError.rejected(score) }
    score = score &* 414
    return BroadReference(score)
  }
}
@inline(never) public func broad_caller_0411_0(_ single: Float, _ double: Double, _ seed: Int) async throws -> Int {
  let result = try await BroadOwner0411(seed).broad_case_0411(single, double); return result.value &+ seed
}
@inline(never) public func broad_caller_0411_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { _ = try await BroadOwner0411(seed).broad_case_0411(single, double); let result = try await BroadOwner0411(seed).broad_case_0411(single, double); return result.value &+ seed } catch { return seed }
}

public actor BroadOwner0412 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0412(_ single: Float, _ double: Double) async throws -> String {
    var score = Int(single) &+ Int(double) &+ bias
    if score < 415 { throw BroadError.rejected(score) }
    score = score &+ 415
    return String(score, radix: 16)
  }
}
@inline(never) public func broad_caller_0412_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { _ = try await BroadOwner0412(seed).broad_case_0412(single, double); let result = try await BroadOwner0412(seed).broad_case_0412(single, double); return result.utf8.count &+ seed } catch { return seed }
}
@inline(never) public func broad_caller_0412_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  if seed == 0 { return 7 }; do { let result = try await BroadOwner0412(seed).broad_case_0412(single, double); return result.utf8.count &+ seed } catch { return seed &- 415 }
}

public actor BroadOwner0413 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0413(_ single: Float, _ double: Double) async throws(BroadError) -> any BroadValue {
    var score = Int(single) &+ Int(double) &+ bias
    if score > 416 { throw BroadError.rejected(score) }
    score = score &- 416
    return BroadSmall(score, 1)
  }
}
@inline(never) public func broad_caller_0413_0(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  if seed == 0 { return 7 }; do { let result = try await BroadOwner0413(seed).broad_case_0413(single, double); return result.value &+ seed } catch { return seed &- 416 }
}
@inline(never) public func broad_caller_0413_1(_ single: Float, _ double: Double, _ seed: Int) async -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try await BroadOwner0413(seed).broad_case_0413(single, double); return result.value &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}

public actor BroadOwner0414 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0414(_ maybe: Int?) async throws -> Void {
    var score = (maybe ?? -1) &+ bias
    if score == 417 { throw BroadError.rejected(score) }
    score = score ^ 417
    return ()
  }
}
@inline(never) public func broad_caller_0414_0(_ maybe: Int?, _ seed: Int) async -> Int {
  do { if seed < 0 { throw BroadError.rejected(seed) }; do { let result = try await BroadOwner0414(seed).broad_case_0414(maybe); return seed &+ seed } catch { return seed &- 1 } } catch { return seed &+ 2 }
}
@inline(never) public func broad_caller_0414_1(_ maybe: Int?, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0414(seed).broad_case_0414(maybe); return seed &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}

public actor BroadOwner0415 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0415(_ maybe: Int?) async throws -> Bool {
    var score = (maybe ?? -1) &+ bias
    if score < 418 { throw BroadError.rejected(score) }
    score = score &* 418
    return (score & 1) == 0
  }
}
@inline(never) public func broad_caller_0415_0(_ maybe: Int?, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0415(seed).broad_case_0415(maybe); return (result ? 1 : 0) &+ seed } catch let error as BroadError { switch error { case .rejected(let n): return n } } catch { return seed }
}
@inline(never) public func broad_caller_0415_1(_ maybe: Int?, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0415(seed).broad_case_0415(maybe); return (result ? 1 : 0) &+ seed } catch { fatalError("owned broad v2 rejected") }
}

public actor BroadOwner0416 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0416(_ maybe: Int?) async throws -> Int8 {
    var score = (maybe ?? -1) &+ bias
    if score > 419 { throw BroadError.rejected(score) }
    score = score &+ 419
    return Int8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0416_0(_ maybe: Int?, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0416(seed).broad_case_0416(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { fatalError("owned broad v2 rejected") }
}
@inline(never) public func broad_caller_0416_1(_ maybe: Int?, _ seed: Int) async throws -> Int8 {
  return try await BroadOwner0416(seed).broad_case_0416(maybe)
}

public actor BroadOwner0417 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0417(_ maybe: Int?) async throws -> UInt8 {
    var score = (maybe ?? -1) &+ bias
    if score == 420 { throw BroadError.rejected(score) }
    score = score &- 420
    return UInt8(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0417_0(_ maybe: Int?, _ seed: Int) async throws -> UInt8 {
  return try await BroadOwner0417(seed).broad_case_0417(maybe)
}
@inline(never) public func broad_caller_0417_1(_ maybe: Int?, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0417(seed).broad_case_0417(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 420 }
}

public actor BroadOwner0418 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(__always) public func broad_case_0418(_ maybe: Int?) async throws -> Int16 {
    var score = (maybe ?? -1) &+ bias
    if score < 421 { throw BroadError.rejected(score) }
    score = score ^ 421
    return Int16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0418_0(_ maybe: Int?, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0418(seed).broad_case_0418(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 421 }
}
@inline(never) public func broad_caller_0418_1(_ maybe: Int?, _ seed: Int, _ cleanup: inout Int) async -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try await BroadOwner0418(seed).broad_case_0418(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 421 }
}

public actor BroadOwner0419 { public let bias: Int; public init(_ n: Int) { bias=n }
  @inline(never) public func broad_case_0419(_ maybe: Int?) async throws -> UInt16 {
    var score = (maybe ?? -1) &+ bias
    if score > 422 { throw BroadError.rejected(score) }
    score = score &* 422
    return UInt16(truncatingIfNeeded: score)
  }
}
@inline(never) public func broad_caller_0419_0(_ maybe: Int?, _ seed: Int, _ cleanup: inout Int) async -> Int {
  defer { broad_cleanup(&cleanup) }; do { let result = try await BroadOwner0419(seed).broad_case_0419(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 422 }
}
@inline(never) public func broad_caller_0419_1(_ maybe: Int?, _ seed: Int) async -> Int {
  do { let result = try await BroadOwner0419(seed).broad_case_0419(maybe); return Int(truncatingIfNeeded: result) &+ seed } catch { return seed &- 422 }
}

