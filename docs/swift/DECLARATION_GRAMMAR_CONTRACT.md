# Contract: a complete Swift declaration grammar (roadmap 4.3 item 3)

Status: contract only; nothing here is implemented yet. Written 2026-11-12 against main c4e9131.
Tests are written from this contract by someone who has not seen the implementation.

## 1. Problem

On the Maccy 2.8.0 measurement the imports profile retained 5,123 rows for imported Swift callees, and the
declaration grammar decided 4 of them. The declines were generic requirements (1,742), unknown substitutions
(1,679), unsupported productions (1,129), protocol contexts (438) and four smaller classes (131). The two
existing parsers add productions one at a time: `src/airs/swift_declaration_profiles.py` (model
`swift-broad-declaration-syntax-v1`, used by the broad profiles, the ABI profiles and two validators) and
`src/airs/swift_import_declarations.py` (model `swift-import-declaration-syntax-v1`, four entities). Neither
can be widened, because the published profiles and validators depend on their exact output.

## 2. Decision

1. A new module, `src/airs/swift_declaration_grammar.py`, with syntax model `swift-declaration-syntax-v2`.
   It parses the whole `$s` global-symbol grammar of the pinned toolchain for function-like entities. It does
   not import either v1 parser, and neither v1 parser changes: every existing report stays byte-identical.
2. It lands first as a library with its own tests and the differential check (section 6). No profile, report
   or validator uses it in that pull request, so no model identity is minted.
3. The second-generation broad profile (roadmap 4.3, items 2 to 5 under one new identity) is its first user.

## 3. What the grammar must parse

Cite, for every production, the section of `docs/ABI/Mangling.rst` at the tag of the pinned toolchain (record
the tag in the module docstring). Where this list and that document differ, the document wins and the
difference is written down.

- **Global forms:** `$s` symbols only. `_T0`, `$S`, `$e` and anything else is declined (`invalid_input`).
  Suffix operators (`T…`: thunks, dispatch thunks, method descriptors, outlined copies, specializations,
  merged functions, protocol witnesses) are recognised and declined with reason `thunk_or_specialization`.
  They are recognised, not mistaken for a trailing suffix.
- **Identifiers:** plain length-prefixed, word substitutions (`0` and the word-reference forms), Punycode
  (`00`) decoded to its Unicode name, operator identifiers with their fixity, local and private
  discriminators.
- **Substitutions:** indexed (`A…`), standard (`S` and one letter), the two-letter standard forms including
  the concurrency set (`Sc…`), and repeated substitutions. The substitution table is complete for the pinned
  toolchain. An index outside the table is `unknown_substitution`.
- **Contexts:** module, struct, enum, class, protocol, extension (with an optional generic signature),
  type alias, anonymous and local contexts. A protocol context is parsed, not declined.
- **Entities:** function, initializer (allocating and non-allocating), deinitializer, the accessor family
  (getter, setter, modify, read, and the others in the document) for variables and subscripts, and the type
  metadata accessor.
- **Types:** nominal, bound generic, tuple (labelled and variadic), optional, array and dictionary sugar,
  function types of every convention (thick, thin, no-escape, block, C), metatypes, existentials and
  compositions, dependent generic parameters at any depth, dependent members and associated types, opaque
  result types, pack and pack-expansion types, and the parameter modifiers (inout, shared, owned, sending,
  isolated, autoclosure, variadic).
- **Generic signatures:** parameter counts and every requirement kind: conformance, same type, layout, base
  class, packs.
- **Effects** on every function type: throws, typed throws with its error type, async, and global-actor or
  isolated-any isolation.

Limits: keep the `ParseLimits` fields and values, and add a budget for generic-signature size. The native
reader's nesting limit still applies: no value inside a serialised identity more than 27 levels below the
identity (see `_MAX_IDENTITY_VALUE_DEPTH` in the import parser).

## 4. Result

A frozen result with:

- `identity`: entity kind, context path, name, labels, parameter types, result type, generic signature, and
  the effects of the outer function type. Present only when the whole symbol is consumed.
- `throw_decision`, one of `non_throwing`, `throwing`, `async`, `undecided`.
- `reason`: empty for `non_throwing`, `throwing` and `async`; otherwise one stable reason code. Keep the v1
  codes that still apply, and add codes for anything new. Every code is listed in the module and in the
  report documentation.
- `offset`: where parsing stopped, for every decline.

## 5. Soundness rule (the reason for the item)

`non_throwing` is returned only when all of these hold:

1. The whole symbol is consumed, with no suffix operator.
2. The entity is a function, an initializer, a deinitializer or the metadata accessor.
3. The outer function type is found by the grammar: the type of the entity itself, looking through a
   generic signature. Its own effects carry no throws, no typed throws and no async.

For the metadata accessor, whose mangling carries no function type, rule 3 holds vacuously and only for that entity.

Effects of a closure parameter's type are part of the parameter, not of the outer function. A `rethrows`
function mangles as throwing and is `throwing`. Typed `throws(Never)` is `undecided` with reason
`typed_throws` in this model. That keeps the exit test in section 7 exact; a later model may decide it.

**Accessors are `undecided` until an owned compiled example shows how an effectful accessor is mangled**
(`var x: Int { get throws }`, `get async`, a throwing subscript). The implementer writes that example, records
the toolchain demangler's tree for it, and only then decides whether accessors can be `non_throwing`, under
the same rule. If it is not settled in the library pull request, accessors stay `undecided` there.

Isolation markers do not change the throw decision. They are recorded in the identity.

## 6. Independent check: the toolchain demangler

The oracle is `xcrun swift-demangle --tree-only`. It runs on symbol *text* only, never on an image, and is
found through `xcrun`, never a fixed path. For each symbol, project its node tree to:

- the entity node kind directly under `Global`;
- the outer function type: the `Type` child of the entity, through any `DependentGenericType`, down to the
  first `FunctionType` (or `NoEscapeFunctionType` and the others), and its direct effect children
  (`ThrowsAnnotation`, `TypedThrowsAnnotation`, `AsyncAnnotation`). Effect nodes inside an `ArgumentTuple`
  belong to a parameter and are not the outer function's;
- for every symbol AIRS decides: the context path, the entity name, the label list and the parameter count.

Rules:

- **Soundness:** no symbol AIRS calls `non_throwing` may show a throws, typed-throws or async annotation on
  its outer function in the oracle. The allowed count is zero, and one disagreement blocks the merge.
- **Identity:** every symbol AIRS decides must match the oracle's context path, name, labels, parameter count
  and entity kind. Any mismatch is a defect to fix before merge.
- **Coverage, reported and not gated:** the share of symbols decided, the share of decided symbols that are
  `non_throwing`, and counts by reason for the rest.

## 7. Inputs and where they run

1. **Owned fixture.** The 19 `$s` symbols of `fixtures/swift-error-flow/broad-imports/` (5 throw, 14 do not).
   Expected decisions are recorded per symbol.
2. **Owned synthetic set.** Swift sources written for this item, one or more declarations per production in
   section 3, compiled with the pinned toolchain. Symbol names are read with `nm` from the owned build output.
   Commit the sources and the extracted name list (text), not the binaries.
3. **SDK symbol lists.** The text stubs of the macOS SDK, found through `xcrun --show-sdk-path`:
   `usr/lib/swift/libswiftCore.tbd` (14,919 `$s` names as of this writing),
   `usr/lib/swift/libswift_Concurrency.tbd`, and
   `System/Library/Frameworks/Foundation.framework/Foundation.tbd` (40,300). These are text files listing
   exported names. Nothing is loaded or executed.

The differential runs as a test in CI on the hosted macOS 27 runner, over all three inputs. Locally, run it
on inputs 1 and 2 and a fixed sample of input 3 of no more than 1,000 names (every Nth name, N recorded)
while developing; the full SDK pass is the CI job. Report the measured coverage in the pull request.

The exit measure on the panel ("the admitted share reported, today 4 of 5,123 on Maccy") belongs to item 1,
the panel measurement. It runs only after explicit approval because it is corpus-scale. This item's exit is the zero-
disagreement result on inputs 1 to 3 plus the coverage numbers.

## 8. Tests the independent author writes from this contract

- One positive case per production in section 3, with the expected identity and decision.
- Effects: outer throws, outer async, outer typed throws, typed `throws(Never)`, a throwing closure parameter
  on a non-throwing function (expected `non_throwing`), `rethrows` (expected `throwing`), an isolated
  function.
- Declines: each suffix operator family; old manglings; truncated symbols at every byte of three
  representative symbols; out-of-range substitution indexes; each limit reached exactly and exceeded by one.
- Totality: no exception escapes for any input, including random byte strings of bounded length from a fixed
  seed.
- Determinism: the same input gives an equal result, and the serialised identity is byte-identical across
  runs and across Python 3.11 and the newest supported version.
- Isolation: a test that the v1 parsers' outputs are unchanged for the owned fixture and the synthetic set.

## 9. Not in this item

- Using the grammar in any profile or validator (that is the second-generation profile).
- ABI admission of imported callees (roadmap 4.3 item 5b) and any claim about what a callee does.
- The panel run.
- Changing either v1 parser.

## 10. Review

A reviewer who did not implement it reads the module against `Mangling.rst` and this contract and lists only
merge-blocking problems. The soundness rule in section 5 and the projection in section 6 get the closest
reading: a wrong `non_throwing` hides a call that can raise.
