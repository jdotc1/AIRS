# Complete declaration grammar: contract

Status: contract for roadmap section 4.3 item 3. Nothing here is implemented yet.
This page says what the grammar must do, what it may claim, and how it is checked,
before any production is written.

## Why a new grammar

`swift-import-declaration-syntax-v1` (see [SWIFT_IMPORT_DECLARATIONS.md](../SWIFT_IMPORT_DECLARATIONS.md))
admits a closed list of productions and declines everything else. On Maccy it admits
4 of 5,123 imported Swift symbols. Adding productions one at a time has not changed
that share. The new grammar parses the whole function-entity part of the Swift
mangling, including substitutions and generic signatures, and decides the effects of
the entity only after the whole symbol is consumed.

## Identity

- New syntax model: `swift-declaration-grammar-v2`. It is a new semantic, so it gets a
  new identity; `swift-import-declaration-syntax-v1` and every existing profile stay
  admitted and byte-identical.
- It is used only by the second-generation broad profile that carries roadmap section
  4.3 items 2 to 5 together. It does not ship as an interim profile.
- That profile is admitted natively in the same change that adds it (section 4.5
  item 3: the engine stays at most one capability ahead of the application).

## Input

- Accepted prefixes: `$s` and `_$s` (the current mangling). Everything else, including
  `$S`, `_T0` and `$e`, declines with `invalid_input`.
- Symbol names from the import and symbol tables only. Symbolic-reference bytes
  (0x01 to 0x1F) cannot occur there; any such byte declines with `invalid_input`.
- The existing `ParseLimits` apply unchanged. Exceeding any limit declines with
  `resource_limit`, never a partial result.

## What the grammar covers

The function-entity productions of the mangling and everything they can contain,
taken from the mangling specification of the Swift release that the recorded
toolchain ships (the implementation's evidence names that release):

1. Contexts: modules (literal, `So`, `SC`, word-substituted), nominal types of every
   kind in the mangling specification, extensions with and without generic
   signatures, local and private discriminators, and anonymous contexts.
2. Entities: functions, initializers and allocating initializers, deinitializers,
   accessors of every kind in the specification (subscript forms included), metadata
   accessors (`Ma`) and default argument initializers.
3. Types: every type production, including function types of every convention,
   tuples with labels and variadics, metatypes and existential metatypes, protocol
   compositions, existentials with primary associated types, packs and pack
   expansions, opaque result types, ownership and parameter flags.
4. Generic signatures: generic parameters (`x`, `q_`, `d`), requirements of every
   kind (conformance, same-type, base-class, layout, pack), and dependent member types.
5. Substitutions: the whole substitution table, including known-type (`S`, `Sc`),
   word substitutions in every position (modules included) and repeat counts.
6. Suffix operators: thunks, specializations and attribute suffixes are parsed so the
   symbol is consumed. Their effects are not inferred (see Classification).

A production the grammar does not have declines with `unsupported_production` and the
exact offset. The decline is counted by reason; the goal is that the differential
check below finds none for symbols the toolchain demangler parses.

## Classification

The parse result carries the entity kind and two effect fields, each with three
values: `throws` is `yes`, `no` or `not_encoded`; `async` is `yes`, `no` or
`not_encoded`.

- Effects come only from the function type of the entity itself, never from a nested
  function type, a parameter, a context or an identifier.
- `throws` is `yes` for `K` and for typed throws (`YK`, any error type, `Never`
  included). Typed `throws(Never)` stays a row: this grammar does not reason about
  error types.
- `async` is `yes` for `Ya`. Isolation and sendability annotations are recorded and
  do not change either field.
- `not_encoded` is used where the mangling does not carry the effect: every accessor
  (the accessor mangles the property's type, not a function type), every thunk, every
  specialization and every suffix operator. `not_encoded` never becomes `no`.
- A call is skipped as non-throwing only when the whole symbol is consumed, the
  entity is a function, initializer, deinitializer or metadata accessor, `throws` is
  `no` and `async` is `no`. Everything else stays a row. Unknown never becomes
  agreement; unresolved stays in the denominator.
- `rethrows` mangles as `throws` and stays a row.

## Known hazard

`@_silgen_name` can give a throwing or async function a plain-looking symbol, and
the symbol cannot reveal this. The hazard stays documented; no check here removes it.

## Checks

1. **Owned source truth.** The existing 494-symbol corpus compiled from owned Swift
   source is extended with sources for every entity kind and effect combination above.
   Exit: no symbol classified as non-throwing whose source can throw or is async.
2. **Differential against the toolchain demangler**, on owned inputs: the corpus,
   the fixture symbols, generated strings and mutations. For each string, the
   demangler's tree (`swift-demangle --tree-only`, toolchain version recorded) is
   reduced to: parses or not, entity kind, throws annotation (plain or typed), async
   annotation. Exit:
   - no string the grammar classifies as non-throwing for which the demangler shows
     throws or async (a blocker);
   - no string the grammar parses that the demangler rejects (a blocker);
   - every string the demangler parses and the grammar declines is listed by reason
     (a completeness gap, not a blocker, reported as a count).
   The demangler's node names for these annotations are confirmed from its output on
   the first owned run and recorded with that run; they are not assumed.
3. **Panel differential**: the same comparison over every imported Swift symbol name
   in the 12 panel applications, with the admitted share reported for each (today 4
   of 5,123 on Maccy). This is corpus-scale. It needs an explicit yes before it runs
   and is tied to the panel measurement of section 4.3 item 1.
4. **Existing reports.** Reports under every existing profile are byte-identical
   before and after the change, compared once.

Inspected binaries are never loaded or executed in any of these checks; symbol names
are read as data.

## Order of work

1. This contract.
2. The grammar with its owned corpus and the owned differential (checks 1 and 2).
3. The second-generation profile, with items 2, 4 and 5, its native admission, and
   check 4.
4. Check 3, after the yes.
