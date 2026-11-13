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

The frozen identity includes context, declaration name and discriminator,
parameter labels and types, result, generic signature and effects. Canonical
JSON includes every field and uses sorted keys, compact separators and ASCII
escaping. Historical declaration parsers and their consumers are independent.

`GrammarLimits` bounds symbol length (4096), identifier length (256), context
levels (16), retained type nodes (256), substitutions (128), parameters (64),
type depth (16), generic parameters (32), and generic requirements (64).
Serialized identities cannot exceed depth 27. Parsing uses an iterative stack;
substitution expansion and retained occurrences are bounded independently.

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

The pinned demangler takes precedence when the reference grammar differs:
standard floating types use `Swift.Double` and `Swift.Float`, `ScM` is a class,
`Yu` is the sending parameter modifier, and layout-substitution requirements use
`RL`. Punycode decoding translates both the Swift delimiter and digit alphabet.
