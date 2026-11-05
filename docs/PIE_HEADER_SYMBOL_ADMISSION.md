# PIE executable header marker admission

A first native broad-v1 case using the authentic Maccy 2.8.0 release exposed an
admission refusal before analysis: `symbol_address_extent`. Independent bounded
source-range inspection identified the exact N_SECT|N_EXT `__mh_execute_header`
record at the mapped Mach header address, preceding its declared `__TEXT,__text`
section. This is linker metadata, not a function.

LLVM's Mach-O linker documents this PIE representation in
[createSyntheticSymbols](https://llvm.googlesource.com/llvm-project/lld/+/517e171d5bd3f493e5ec99a6a39db5663f6511d5/MachO/SyntheticSections.cpp).

The parser now excludes only that exact metadata record when the image is
MH_EXECUTE with MH_PIE, its unique __TEXT mapping begins at file offset zero and
covers the header/load commands, the symbol type is exactly0x0f, section1 is
__TEXT/__text, its value is the mapped header base, and its bounded name exactly
matches the NUL-terminated marker. It never creates a code name, function entry
or symbol-fallback boundary. All ordinary out-of-section symbols still refuse.
No analysis ceiling, dispatch or ABI eligibility was widened.

Three new owned tests passed in0.001s after the two positive scenarios failed
before the fix. They cover metadata exclusion, fallback-boundary exclusion and
six noncanonical refusal contexts. Independent source review approved the change.
The authentic refusal was independently checked using11,659 bytes of no-follow,
descriptor-relative source ranges; previous archive/container digest receipts
were reused without rehashing. Subsequent native case outcomes remain separately
recorded; this parser correction alone establishes no broad witness eligibility.
