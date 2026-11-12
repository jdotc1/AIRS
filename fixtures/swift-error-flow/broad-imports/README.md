# broad-imports fixture

OwnedImports.swift is a tiny owned Swift program (Foundation: Data, JSONDecoder, String.write) whose
stripped arm64 Mach-O, OwnedImports.macho, has a __TEXT,__stubs section with 29 imported-symbol stubs
(chained fixups, pointers in __DATA_CONST,__got). The binary is never executed.

Build (thin arm64, macOS 13 target):
    xcrun swiftc -O -target arm64-apple-macos13 OwnedImports.swift -o OwnedImports
    xcrun strip -x OwnedImports
    cp OwnedImports OwnedImports.macho

expected.json was derived with Apple tools only (otool -Iv, otool -s __TEXT __stubs -v, objdump -d,
swift-demangle --compact), independently of any AIRS code. It lists every stub, its pointer slot, and
every bl/b in __text that targets a stub. "demangled_throws" is only a hint from the demangled text.
