# Imported Swift declaration syntax

`parse_import_declaration` uses syntax model `swift-import-declaration-syntax-v1` for the imports path of `broad-imports-v1`. `parse_broad_declaration` and the `broad-v1`, `broad-large-v1` and `broad-extended-v1` profiles are unchanged.

## Admission

The closed grammar admits plain functions, struct instance and static methods, type metadata accessors, initializers and allocating initializers. It supports literal modules, Swift and Objective-C module forms, nominal and supported extension contexts, known-type and identifier substitutions, bounded repeat substitutions, optional and array types, parameter tuples, `Any`, shared parameters and variadic parameters within those productions. Word-substituted identifiers are supported within the grammar; word-substituted module identifiers decline. Class and enum methods decline. A generic parent can be invisible in the symbol; an explicit generic signature is outside the grammar.

A symbol is treated as unable to throw only when the exact grammar consumes the whole symbol and the entity-level function type carries no throws marker. Metadata accessors have their own exact `Ma` production. A `K` inside an identifier or nested type does not establish entity-level throws. `rethrows` mangles as `throws` and stays a row. `throws(Never)` and Never-returning functions can have plain non-throwing forms.

Every accessor declines: getter, setter, modify, read and subscript manglings carry no throws or async marker. Their absence cannot establish a non-throwing accessor.

Word-origin identifiers used as modules decline with `word_substitution`, including later substitution-table references to those identifiers.
An identity with any member or element, scalar or container, more than 27 levels below the identity object declines with `resource_limit`. The native report reader allows 32 nesting levels in a whole report and an identity object sits at level 5 of a `broad-imports-v1` report, so every admitted identity fits.

Declines retain no partial identity. Reasons use the existing report vocabulary:

| Unsupported input | Reason |
|---|---|
| Accessors, unlisted productions, class or enum methods, metatypes and unsupported ownership forms | `unsupported_production` |
| Async, isolation and sendability annotations | `async_context` |
| Typed throws | `typed_throws` |
| Closures and nested function types | `closure_type` |
| Thunks and specializations | `thunk_or_specialization` |
| Explicit generic requirements or dependent generic types | `generic_requirements` |
| Unsupported protocol contexts | `protocol_context` |
| Unknown substitutions | `unknown_substitution` |
| Unsupported Unicode or word-substitution forms | `unicode_identifier`, `word_substitution` |
| Unconsumed suffix | `unconsumed_suffix` |
| Malformed grammar or invalid input | `invalid_grammar`, `invalid_input` |
| Bounded parsing limit exceeded | `resource_limit` |

A symbol with several unsupported features can decline at the first one encountered. Async, typed throws, closures, thunks, specializations and anything unconsumed decline.

## Rows and identity

Admitted non-throwing calls increment `non_throwing_swift_import_calls` and are skipped. Admitted throwing calls remain rows with declaration status `syntax_admitted` and `throws: true`. The fixture's `Data.init(contentsOf:options:)` is such a row. Declined symbols remain rows with declaration status `syntax_unresolved`. All retained import rows remain `unresolved` with reason `imported_callee_abi_unqualified`. Attribution and declaration syntax establish neither the callee's ABI nor which library is bound.

The outer identities remain `broad-imports-v1` and `swift-broad-error-flow-imports-v1`. This profile is on main but unreleased, and the native app does not admit it yet, so its content can still settle. A later change after native admission would need a new identity.

## Evidence and limits

The source-truth oracle contains 494 symbols compiled from owned Swift source: 101 admitted as non-throwing, 39 admitted as throwing and 354 declined. No admitted non-throwing symbol in that corpus has source truth that can throw or is async. Of 675 production probes, 194 admit; every admitted probe agrees with the demangler on throws.

The 19 fixture symbols split into 10 admitted non-throwing, 1 admitted throwing and 8 declined. Their 27 Swift stub call sites previously produced 27 rows and 0 skipped calls; they now produce 12 rows and 15 skipped calls. Expectations derive from recorded Apple-tool text and the closed grammar, independently of AIRS output. Fixture source-level effects were not separately verified against SDK source.

A differential over 1,999 strings, comprising corpus and fixture symbols plus 1,548 mutations, found 0 disagreements between two independently written implementations. Apple's `swift-demangle` agrees on throws for all 201 admitted strings. These are bounded syntax results, not runtime or native-app qualification. Analysed binaries are never executed.

A separate generated-input check ran 3,816 strings from two generators: 660 admitted as non-throwing, 178 admitted as throwing and 2,962 declined. All 838 admitted strings were compared with `swift-demangle` output and the admitted fields agree. The differential and this check ran before two later changes that only narrow admission: the word-origin module rule and the identity nesting limit above. Neither was repeated afterwards. The differential did not exercise word-substituted module identifiers; `swift-demangle` accepts them, and this grammar declines them by rule.

The reports of the four owned binaries under `broad-v1`, `broad-large-v1` and `broad-extended-v1` (12 reports) were compared once with the reports from before this change and are byte-identical. In the owned imports fixture's `broad-imports-v1` report the only differences are the declaration records on retained rows, the 15 removed rows and the counters derived from the row count.

A residual hazard remains: `@_silgen_name` can give a throwing or async function a plain-looking `$s` symbol. The symbol cannot reveal this override. This hazard is documented, not solved; the source-truth corpus result does not eliminate it.
