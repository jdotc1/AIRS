# Owned declaration grammar sources

Compile these sources with Apple Swift 6.4.2 (upstream tag
`swift-6.4.2-RELEASE`) on macOS 27, into an object file:

```sh
xcrun swiftc -parse-as-library -emit-object -module-name GrammarSynth -swift-version 6 Declarations.swift -o Declarations.o
```

Extract the exported and local Swift symbol names as text with `nm`. Keep only
names beginning with `$s` or `_$s`, sort and deduplicate, and save the resulting
one-name-per-line list as `../synthetic-names.txt`. Only the text name list is
committed as compiled output; object files and other binaries are not committed.
The sources are retained so the name list can be regenerated intentionally with
the pinned toolchain. The tests never read or execute the object file.

The declarations cover contexts, effects, function conventions, parameter
modifiers, containers, existential and dependent types, generic requirements,
packs, opaque results, local/private/operator names and Unicode identifiers.
Accessor examples include throwing, async, async throwing, and throwing subscript
getters. The throwing closure parameter in `closureOnly` does not make the outer
function throwing; `rethrowing` does.

Some ABI productions have no direct Swift source spelling: runtime anonymous
contexts, historical addressors, debugger sugar and type aliases, and arbitrary
substitution-table indexes. Handwritten symbols in the unit tests cover those
forms. Optimizer-dependent thunks and substitutions are not guaranteed to appear
in an unoptimized object. Layout source coverage uses the class constraint;
arbitrary SIL layout constraints and standalone pack types require handwritten
symbols. Compilation and extraction are separate from Python test authoring.

The committed `../synthetic-names.txt` was generated with Apple Swift 6.4.2
(`swiftlang-6.4.2.1.9`) on macOS 27.3 (arm64) by the command above, then
`xcrun nm -j --defined-only Declarations.o`, keeping names that match
`^_?\$s`, sorted bytewise and deduplicated: 224 names. Undefined references to
other modules are not included.
