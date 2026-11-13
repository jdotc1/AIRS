# Swift declaration syntax v2

`airs.swift_declaration_grammar.parse_declaration` parses ASCII `$s` symbol
text, optionally preceded by one underscore. It is a standard-library-only
library with no input/output operations. Its syntax model is
`swift-declaration-syntax-v2`, pinned to `swift-6.4.2-RELEASE`.

A decision requires a complete function, initializer, deinitializer or metadata
accessor. Only the entity's outer function effects determine `non_throwing`,
`throwing` or `async`; effects of closure parameters remain on those parameters.
Typed `throws(Never)` and all accessors remain undecided. These are syntax
classifications, not claims about runtime behavior or ABI admission.

The frozen identity includes context, declaration name, discriminator and fixity,
parameter labels and types, result, generic signature and effects. Canonical
JSON includes every field and uses sorted keys, compact separators and ASCII
escaping. Every TypeNode has keys `args`, `convention`, `effects`, `kind`,
`labels`, `modifiers`, `name` and `path`. A nominal type's `path` is canonical
ASCII JSON text containing the kind/name pairs from its module through the type
itself. For example, `Si` has path `[["module","Swift"],["struct","Int"]]`.
The value is a JSON string within the serialized identity, preserving nominal
kind without increasing identity depth. Bound generics retain the base nominal
path; Optional, Array and Dictionary sugar use the same paths as explicit forms.
Other kinds, builtins and the implicit `AnyObject` member synthesized by `Xl`
have null paths. Explicit `Xc` nominal operands retain their paths.

A metadata accessor's result is a `metatype` node with the accessed nominal type
as its single argument. Its parameters remain empty; its context, name and
oracle projection are unchanged. Historical declaration parsers and their
consumers are independent.

`fixity` is `prefix`, `postfix` or `infix` for an operator, and null otherwise.
Each context element has `kind`, `name`, `generic_signature` and `enclosing`.
An extension retains its own generic signature; other context kinds have a null
signature. A local context retains the complete enclosing declaration identity,
including accessor kind, parameters and effects; other kinds have null
`enclosing`. The independent oracle projection still uses only context kind and
name. Local, private and related-name discriminators have distinct `local:`,
`private:` and `related:` prefixes.

Function types retain `Yb` as the `sendable` modifier. The modifier belongs to
the nested function type and does not alter the enclosing declaration's effects.
The allowed modifiers are `inout`, `shared`, `owned`, `sending`, `isolated`,
`autoclosure`, `variadic`, `noDerivative` and, on function types, `sendable`.
Metatype representations use `convention` values `thin`, `thick` or `objc`;
an unspecified representation remains null. A function convention with a C type
spelling is encoded as `c:clang:<spelling>` or `block:clang:<spelling>`.
Unconstrained extension type names retain their context as `context:` followed
by a compact JSON array of kind/name pairs. Names containing qualification
delimiters use the same unambiguous encoding.

`GrammarLimits` bounds symbol length (4096), identifier length (256), context
levels (16), retained type nodes (256), substitutions (128), parameters (64),
type depth (16), generic parameters (32), and generic requirements (64).
Serialized identities cannot exceed depth 27. Parsing uses an iterative stack;
substitution expansion and retained occurrences are bounded independently.
Materialized name text, including identifier expansion, qualified names and
escaped paths, has a cumulative budget of 16 times `max_symbol_length`.
Allocations are charged before construction, including word references before
joining an identifier. Exceeding this bound declines with `limit_exceeded` and
`expanded_text` in the detail; no additional limits field is introduced.

Declines have an offset and one of these stable reasons:

- `invalid_input`: invalid input type, encoding or global prefix.
- `limit_exceeded`: a named resource budget or identity depth was exceeded.
- `unknown_substitution`: an unavailable indexed, word or standard substitution.
- `truncated`: input ended within a production.
- `malformed_symbol`: operands or spelling do not fit the grammar.
- `trailing_input`: text remains after an entity.
- `thunk_or_specialization`: a thunk, specialization or outlined operation.
- `unsupported_production`: a recognized production outside the implemented set.
- `not_function_entity`: a global outside the decision entity set.
- `typed_throws`: typed throws with `Swift.Never`.
- `accessor`: an accessor whose effects are not admitted by this model.

The differential test invokes `xcrun swift-demangle --tree-only` on symbol text.
It independently compares entity, context, name, labels and parameter count,
and checks that no `non_throwing` decision has outer throwing or async effects.
Inputs are owned imports, owned synthetic declarations and SDK text stubs.
`AIRS_GRAMMAR_SDK_EVERY=N` selects every Nth sorted SDK symbol; local samples
must contain no more than 1,000 SDK names. `AIRS_GRAMMAR_COVERAGE_OUT` selects
the JSON coverage destination. CI runs the full SDK lists. The test skips with
`swift-demangle unavailable` when the toolchain demangler is absent.

The parser deliberately declines forms that its identity cannot yet represent:
SIL implementation function types (while recognizing their thunk envelopes),
SIL ownership/box and extended existential types, constrained existential `Self`,
generic value markers, qualified opaque types with replacement arguments,
pack-element/SIL-pack types, additional builtin aggregate types, and function
annotations outside the recorded effect/modifier set. Other recognized but
unimplemented special types and function entities also use
`unsupported_production`; the bounded detail identifies the production.
Descriptors, value witnesses, witness tables and static wrappers are outside the
decision set. Static accessors retain the `accessor` decline without an identity.
An arbitrary unknown spelling is not evidence of a supported production.

Every consumed operand must be retained or cause a decline. In particular,
`Ma` requires a plain nominal operand: a bound generic, tuple, function,
existential, modified type or generic wrapper is `unsupported_production`
with detail `metadata_accessor_operand`. A metadata accessor followed by more
text is `malformed_symbol`; it cannot become a local declaration context.

Additional conservative declines prevent information loss where the fixed
identity has no suitable field: protocol-qualified associated types, multiple
nested generic argument groups, nonempty anonymous-context arguments, closure
contexts, nested generic signatures in type operands, and nominal type operands
with local, anonymous or constrained-extension contexts. Decorated names used
as plain module/type names or labels, nested name discriminators, complex
global-actor operands, and labelled or modified outer argument tuples also
decline. Initializer and subscript function wrappers must have the ordinary
thick convention and no outer modifiers. Direct declaration-level `Yb`
declines because only a function TypeNode can carry `sendable`.

The pinned demangler takes precedence when the reference grammar differs:
standard floating types use `Swift.Double` and `Swift.Float`, `ScM` is a class,
`Yu` is the sending parameter modifier, and layout-substitution requirements use
`RL`. Numeric parsing follows the pinned demangler's decimal accumulation and
operand-specific index checks. Generic parameter coordinates require signed
32-bit range after their index offsets; generic signature counts remain subject
to the generic-parameter budget. Local discriminators, layout dimensions, inverse
indexes and opaque ordinals retain the pinned toolchain's widened index values.
Substitution repeats are limited to 2048; an explicit zero denotes one reference.
Sized integer and floating builtins require sizes from 1 through 4096, inclusive;
floating builtins use `Builtin.FPIEEE<N>`. Vector sizes receive the same range
check before the existing unsupported-vector decline.

Punycode uses `_` as delimiter and only `a`–`z` and `A`–`J` as encoded digits.
Invalid digits, decoder arithmetic overflow and out-of-range Unicode scalars
are malformed. Reserved surrogate encodings remain unsupported rather than
receiving a guessed character mapping. Decimal overflow, generic coordinate
overflow and invalid builtin sizes likewise decline as `malformed_symbol`.
