# Bounded broad Swift declaration syntax

`airs.swift_declaration_profiles.parse_broad_declaration(symbol, *, limits=ParseLimits())`
returns an immutable `BroadDeclarationResult`. On success its `identity` is an
immutable `SwiftCallableIdentity`; on refusal `identity` is absent and
`unsupported_reason`, `detail`, and the parser's `offset` explain the boundary.
The accepted external prefixes are `$s` and Mach-O's `_$s`.

This module is separate from `swift_throwing_declarations.py`. It does not
change the historical narrow grammar, method profile, model labels, or report
behavior. No broad production admission is implied by importing this parser.

## Public data contract

- `CallableKind` distinguishes free functions, struct/enum/class instance
  methods, static methods, and bounded generic specializations. A static spelling in a class context does not
  distinguish `static` from `class` source dispatch.
- `SwiftCallableIdentity` records the original symbol, module, ordered nominal
  context, function name, labels, parameter type ASTs, result type AST,
  syntactic throws marker, and supported generic parameter counts.
- `SwiftType` retains type names, nested arguments, inout, optional tuple labels,
  and generic depth/index. Tuple arguments preserve nested tuple structure;
  only the outer formal parameter tuple is exposed as the parameter sequence.
- `ParseLimits` bounds symbol/identifier lengths, contexts, AST nodes,
  substitution table, parameters, type depth, and generic parameters.
- Refusals are typed by `UnsupportedReason`. Details are diagnostic text, not
  a stable admission criterion. Unsupported input returns no partial identity.

A successful identity has no ABI support flag, error-register assignment,
calling convention, address, image identity, exclusive-entry claim, exact target
claim, or lowering classification. `throws=True` describes the syntax marker;
it establishes neither synchronous x21 error transport nor source `rethrows`
semantics. A caller must bind metadata, exact bytes, image identity and callsite
facts independently before admitting any ABI interpretation.

## Implemented grammar subset

The parser consumes the complete declaration with a bounded operand stack and
postfix operators, rather than matching a small collection of signature suffixes:

- ASCII length-prefixed and word-substituted module, declaration and parameter-label identifiers;
  nested nominal `V`, `O`, `C` contexts; function `F` and optional static `Z`.
- Standard `Si`, `Su`, `Sb`, `Sf`, `Sd`, `SS` type substitutions, including
  bounded repeat forms such as `S2i`; Swift `Int8/16/32/64` and
  `UInt8/16/32/64` nominal spellings.
- Void/zero parameters, labeled or unlabeled formal parameters, nested tuple
  types, optional `Sg`, parameter inout `z`, and `Say...G` array types.
- Generic parameter `x` and indexed `q` spellings, `Swift.BinaryInteger`
  conformance `SzRz` requirements, unconstrained `l` / bounded
  `r...l` signatures, with every generic reference checked against the supported
  binding signature. Generic parent contexts without such bindings decline.
- The official 26-entry word dictionary, populated only from eligible literal
  words of at least two characters. Lowercase/uppercase references and their
  zero/final-literal terminators are consumed explicitly; absent word indices,
  malformed termination and overlong expansions decline.
- A bounded table of identifier/module/nominal/optional/array entries, with
  uppercase single-index `A` substitutions and bounded repeat counts.
  Missing entries and entries used in the wrong grammatical role decline.
- Untyped `K` throws, only after result/parameter type operands. Extra type
  operands after annotations, invalid label arity, trailing symbols, and
  incomplete declarations decline.

This is not the complete Swift mangling language. Encoded Unicode/Punycode identifiers, extended/multi-substitution
runs, arbitrary bound generics, other generic requirements/associated types,
protocol/existential contexts, closures/function types, async/isolation markers,
typed throws, function-signature specializations and other unsupported thunks
remain explicit refusals. The supported concrete generic specialization subset
is described below. Symbols may
encounter an earlier unsupported production before a later marker is reachable;
refusal reasons describe the first encountered boundary, not a source diagnosis.

Closure/rethrows, protocol dispatch, generic parent thunks, actor/async, typed
error, specialization, and witness paths must receive independent implementation
and emitted evidence before production admission. The owned fixture generator's
source categories and signature counts are not evidence that emitted symbols or
ABI lowerings are parsed or qualified.

## Sources and scoped verification

The grammar follows Swift's primary
[Mangling specification](https://github.com/swiftlang/swift/blob/main/docs/ABI/Mangling.rst)
(entities, function signatures, tuple/type lists, generics, identifiers and
substitutions). The separation between formal declaration syntax and physical
lowering follows Swift's
[Calling Convention document](https://github.com/swiftlang/swift/blob/main/docs/ABI/CallingConvention.rst).
No private source or symbol was sent to documentation services.

`tests/test_swift_broad_declarations.py` exercises the public immutable result,
all implemented callable context families, primitive/fixed-width and nested types,
labels, arrays, generic bindings, substitution indices, resource boundaries,
malformed annotation order, full-consumption refusal, and the excluded families.
Development used focused red/green runs only. Some handcrafted spellings were
checked with local `xcrun swift-demangle` as an offline diagnostic; runtime parser
code never invokes it. These focused tests do not replace compiled corpus
qualification, independent semantic review, or ABI and callsite validation.


## Recorded initial compiler-index syntax observation

Before the subsequent generic-binding/context review fixes, a single bounded
syntax-only pass read existing recorded compiler-index targets
and `nm` symbols from the initial owned source fixture compilation. It did not
read/decode binary instructions, compile, rerun provenance checks, or qualify ABI
behavior. Of 963 unique recorded broad-case symbols, 334 parsed successfully.
The 484 unique confirmed-target symbols comprised 334 syntax successes, 61 typed
throws refusals, 69 thunk/specialization refusals, and 20 closure-type refusals.

Successful syntax counts by the independent source-family labels were free 60,
struct 86, enum 47, class 51, static/type/extension 39, generic 30, and concrete
protocol implementations 21. All 142 actor/async recorded spellings declined at
async/isolation annotations. These are unique symbol counts across modes, not
unique source declarations, callsite counts, or supported ABI lowerings. Protocol
witness and nested closure symbols additionally meet conservative context/suffix
boundaries. Source-family labels do not establish emitted dispatch semantics.

The focused tests retain actual raw symbols for the seven synchronous source
families, a recorded typed-error declaration and a concrete generic
specialization. The generic base identity retains an immutable
`SwiftGenericRequirement`; at the time of this historical observation the
specialization was explicitly refused. Subsequent syntax support is described
below and does not update these historical counts. Word extraction
and termination additionally follow the primary Swift
[demangler implementation](https://github.com/swiftlang/swift/blob/main/lib/Demangling/Demangler.cpp)
and its
[word-boundary definitions](https://github.com/swiftlang/swift/blob/main/include/swift/Demangling/ManglingUtils.h).


## Review corrections and changed-input verification

Generic signatures now reject a second `l` or `r...l` signature rather than
replacing a previously parsed binding. Every retained generic requirement is
checked against its final depth/count binding, including signatures with zero
parameters. `SwiftType.nominal_kind` preserves the structural role of a nominal
type; tuple, generic-parameter, inout and bound-generic types cannot be flattened
into a nominal declaration context. An ordinary nominal substitution can still
form a nested nominal context without discarding type information.

Three new focused review regression methods passed after these changes. They
cover duplicate signatures, an unbound `BinaryInteger` requirement with a zero
parameter count, invalid structural nominal contexts, and a valid nested nominal
control. The earlier 12 methods and recorded corpus syntax observation were not
repeated. The observation above remains the explicitly historical pre-correction
syntax count, not a newly verified post-correction count.

Following explicit authorization for the changed parser inputs, the complete
current parser test module ran once at implementation commit `4f5e5bc`:
`PYTHONPATH=src python -m unittest discover -s tests -p test_swift_broad_declarations.py`.
All 15 methods passed in 0.006 seconds. This supersedes the split focused test
coverage for the current parser source only. No recorded-index syntax scan,
demangler diagnostic, compiler, binary decoder, hash or ABI qualification was
repeated. Historical corpus counts remain historical; concrete specialization
production support remains a separate ABI-admission gate.


## Concrete generic specialization syntax

The parser now consumes the bounded production `type '_' type* 'T' dropped-arg*
('g' | 'G' | 'B') SPEC-INFO`. Supported replacement types are standard scalar and
String types, the fixed-width integer nominal types listed above, and optional
wrappers. Other replacement productions explicitly decline. A single supported
generic environment must have exactly as many parameters as replacement types;
partial or parent-environment correspondence is never guessed.

`CallableKind.GENERIC_SPECIALIZATION` identifies this syntax, while
`original_callable_kind` retains the template's free/instance/static kind.
`SwiftSpecialization` retains the template symbol, reabstracted/not-reabstracted/
resilient kind, single pass digit, ordered serialized/async-removed/representation-
changed flags, exact dropped-argument ordinals, immutable depth/index/replacement
bindings, and substituted **source** parameter/result ASTs. The identity's
ordinary parameter/result fields retain the template AST. Unknown flags,
malformed lists, missing/extra pass digits, duplicate dropped ordinals, unmatched
bindings and extra suffixes decline without a partial identity.

The actual `Si_Tt3g5` spelling records a Swift.Int replacement, generic
reabstracted kind, pass 5 and a raw `DroppedArgument` ordinal of 4. That ordinal
is the Swift demangler's numbering. It is not treated as a source-parameter
index, and the substituted source AST retains all four source parameters.
Physical arguments, metadata transport, removals, register locations and ABI
support require the independent admission layer. A pure `Si_Tg5` specialization
has no dropped-argument markers; it still confers no ABI admission.

Function-signature specializations such as `Tf4nnnd_n` can change argument or
result ABI and explicitly decline with that diagnostic. Partial apply,
reabstraction, partial generic specialization, combined specialization chains,
and unknown specialization forms also remain refused. These forms cannot be
silently stripped to expose a template identity.

The syntax follows the primary [Swift specialization grammar](https://github.com/swiftlang/swift/blob/main/docs/ABI/Mangling.rst)
and [demangler implementation](https://github.com/swiftlang/swift/blob/main/lib/Demangling/Demangler.cpp).
A single offline expanded demangler diagnostic for the newly supported recorded
`Si_Tt3g5` production confirmed its attribute tree; runtime code invokes no
external demangler. Existing corpus observations, disassembly, compilation and
hash evidence were not repeated.

Three new focused specialization methods first reproduced the missing behavior
and then passed. The changed parser's full 18-method module passed once in 0.012
seconds. One additional new attribute/binding-scope method then passed separately
in 0.005 seconds, covering all retained ordered flags, raw drop ordinals,
fixed-width replacement, and refusal of unbound/parent-environment replacements.
This supplies 19 current methods with the explicitly split receipts; the earlier
historical corpus counts were not rerun or inflated. Fresh review and ABI
admission remain required before production qualification.
