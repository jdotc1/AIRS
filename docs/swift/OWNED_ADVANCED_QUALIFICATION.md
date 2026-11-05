# Owned advanced Swift qualification

The owned source is `fixtures/swift-error-flow/advanced/OwnedAdvanced.swift`.
Apple Swift 6.4.2 (swiftlang-6.4.2.1.9, clang-2100.4.1.1) compiled it for
arm64-apple-macosx14.0 in Swift 6 language mode, separately at -Onone and -O.
The libraries were inspected as data; neither was loaded or executed.

Reproduction (new outputs only; reuse accepted receipts for unchanged outputs):

```sh
storage-guard run -- swiftc -swift-version 6 -target arm64-apple-macosx14.0 \
  -module-name AIRSWitnessFixture -parse-as-library -emit-library -O \
  fixtures/swift-error-flow/advanced/OwnedAdvanced.swift -o OUTPUT.dylib
xcrun llvm-objdump --macho --disassemble --syms OUTPUT.dylib
```

Replace -O with -Onone for the unoptimized qualification build. Generated images
and complete disassemblies reside in private local evidence, not tracked source.

Independent LLVM observations in the optimized build:

* `Counter.parse(Int) throws -> Int`: symbol
  `_$s18AIRSWitnessFixture7CounterV5parseyS2iKF`, entry 0xbc0.
* `handle`: entry 0xdc4; BL at 0xde4, bytes `77 ff ff 97`, targets 0xbc0.
* CBZ x21 at 0xde8, bytes `95 00 00 b4`, targets success 0xdf8;
  error fallthrough is 0xdec.
* Error interval: MOV x0,x21 at 0xdec, opaque BL at 0xdf0,
  MOVN x0,#0 at 0xdf4. The BL is not proven to return.
* Shared restore/return sequence starts at 0xdf8 and ends with RET at 0xe04.
* Struct descriptor symbol `_$s18AIRSWitnessFixture7CounterVMn` at 0x130c.
* Neighbor symbols retain async (`YaKF`), static (`KFZ`), nested (`NestedV`)
  and generic-method (`xxKlF`) spellings and must not enter the method grammar.

These observations qualify a bounded emitted case, not general compiler coverage,
source reconstruction, runtime reachability or universal return behavior.

Additional retained LLVM refusal observations: protocol existential wrapper uses
BLR x8 at0xd3c; virtual wrapper uses BLR x8 at0xdb4. Neither is a direct-call
candidate. Typed throws has suffix `S2iAA7FailureOYKF`, outside the grammar.
GenericBox.parse shares an optimized RET entry with unrelated symbols at0xbbc,
so alias ambiguity independently prevents admission; generic context metadata is
also explicitly refused by the context reader. These neighboring observations
are retained compiler evidence, not claims that all compiler dispatch forms match.
