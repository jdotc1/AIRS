"""Imported-callee effect resolver (fact model swift-import-effect-admission-v1).

An imported callee is a call whose target stub or GOT slot is already attributed to a symbol. This module decides, from
the declaration grammar's result for that symbol alone, what the declaration licenses at the call site. It is a library:
it does no I/O, reads no image, and adds no profile. It has five parts.

1. `SymbolResolver`: one grammar parse per distinct Swift symbol for the life of the resolver, cached by symbol string.
   The parse goes through the module-global name `parse_declaration`, so a run that wants to count parses patches that
   name. A symbol that does not begin `$s` after optional underscores is never parsed.
2. `licence`: the licence class, a function of the grammar decision and the recorded effects only (contract 4.3).
   `none` and `refused_unsupported_effect` never become agreement.
3. `caller_relation`: the relation between the licence and the caller fact of `swift-caller-error-test-v1`
   (contract 4.4). The caller fact itself is not computed here and is unchanged.
4. `row_treatment`: whether the call keeps a row, and the status and reason the row takes (contract 4.5). Status is
   always `unresolved`; a treatment carries no abi, candidate or validation.
5. `compact_declaration` and `identity_digest`: the fixed-key declaration record that import rows carry in place of the
   full grammar identity (contract 5.3), and `effect_admission`, the per-row licence record.

Claims made: what a decided declaration licenses by name. Claims not made: that the callee returns, which definition
the name binds to at run time, any argument or result, or that an error occurs.
"""
import hashlib
from typing import NamedTuple

from .swift_declaration_grammar import SYNTAX_MODEL, parse_declaration

MODEL = 'swift-import-effect-admission-v1'

DECISIONS = ('non_throwing', 'throwing', 'async', 'undecided')
NOT_SWIFT = 'not_swift'
CLASSES = ('no_error_exit', 'declared_error_exit', 'refused_unsupported_effect', 'none')
SHAPES = ('swifterror_idiom', 'postcall_test_only', 'precall_zero_only', 'none')
CALL_KINDS = ('bl', 'b')
RELATIONS = ('conflict', 'corroborated', 'no_signal', 'not_applicable')
TYPED_THROWS = ('none', 'never', 'concrete')

REASON_DISAGREEMENT = 'declaration_caller_disagreement'
REASON_OUTCOME_UNMODELED = 'imported_callee_outcome_unmodeled'
REASON_EFFECT_UNSUPPORTED = 'imported_callee_effect_unsupported'
REASON_ABI_UNQUALIFIED = 'imported_callee_abi_unqualified'

# Work charged to analysis_work for the first parse of a distinct Swift symbol: a fixed base plus the symbol length,
# the same shape the first-generation import declaration admission charges. The cache answers at no cost.
PARSE_WORK_BASE = 16

_NEVER_TYPE = 'Swift.Never'


class Resolution(NamedTuple):
    symbol: str
    is_swift: bool
    decision: str
    reason: str | None
    declaration: dict | None
    licence_class: str | None


class Treatment(NamedTuple):
    retained: bool
    status: str | None
    reason: str | None


def is_swift_symbol(symbol):
    """True when the symbol begins `$s` after any number of leading underscores."""
    return isinstance(symbol, str) and symbol.lstrip('_').startswith('$s')


def licence(decision, effects):
    """Licence class for a grammar decision and its recorded effects (contract 4.3). Total and pure.

    `effects` maps `is_async` (bool or None) and `typed_throws` ('none', 'never', 'concrete' or None). A throwing
    declaration is licensed as an untyped x21 error exit only when it is neither async nor typed; anything else
    (including a value outside the vocabulary) fails closed to `refused_unsupported_effect`. An unknown decision gives
    `none`, the class that claims nothing.
    """
    if decision == 'non_throwing':
        return 'no_error_exit'
    if decision == 'throwing':
        try:
            plain = effects['is_async'] is False and effects['typed_throws'] == 'none'
        except (KeyError, TypeError, IndexError):
            plain = False
        return 'declared_error_exit' if plain else 'refused_unsupported_effect'
    if decision == 'async':
        return 'refused_unsupported_effect'
    return 'none'


def licence_of_record(record):
    """The licence class recomputed from a compact declaration record (contract 5.2 D2)."""
    return licence(record['decision'], {'is_async': record['is_async'], 'typed_throws': record['typed_throws']})


def caller_relation(licence_class, shape, call_kind):
    """Relation of a licence class to the caller fact at one site (contract 4.4)."""
    if licence_class not in CLASSES:
        raise ValueError('unknown licence class %r' % (licence_class,))
    if shape not in SHAPES:
        raise ValueError('unknown caller shape %r' % (shape,))
    if call_kind not in CALL_KINDS:
        raise ValueError('unknown call kind %r' % (call_kind,))
    if licence_class == 'no_error_exit':
        if shape == 'swifterror_idiom':
            return 'conflict' if call_kind == 'bl' else 'not_applicable'
        return 'no_signal'
    if licence_class == 'declared_error_exit':
        if call_kind == 'b':
            return 'not_applicable'
        return 'corroborated' if shape == 'swifterror_idiom' else 'no_signal'
    return 'not_applicable'


def row_treatment(licence_class, relation):
    """Whether the call keeps a row and what the row says (contract 4.5). Never a status other than `unresolved`."""
    if licence_class not in CLASSES:
        raise ValueError('unknown licence class %r' % (licence_class,))
    if relation not in RELATIONS:
        raise ValueError('unknown caller relation %r' % (relation,))
    if licence_class == 'no_error_exit':
        if relation == 'conflict':
            return Treatment(True, 'unresolved', REASON_DISAGREEMENT)
        return Treatment(False, None, None)
    reason = {'declared_error_exit': REASON_OUTCOME_UNMODELED,
              'refused_unsupported_effect': REASON_EFFECT_UNSUPPORTED,
              'none': REASON_ABI_UNQUALIFIED}[licence_class]
    return Treatment(True, 'unresolved', reason)


def effect_admission(licence_class, relation):
    """The per-row licence record."""
    return {'model': MODEL, 'licence_class': licence_class, 'caller_relation': relation}


def identity_digest(identity):
    """SHA-256 (64 lowercase hex) of the identity's canonical JSON: sorted keys, compact separators, ASCII."""
    return hashlib.sha256(identity.serialize()).hexdigest()


def _typed_throws(effects):
    error_type = effects.typed_throws
    if error_type is None:
        return 'none'
    return 'never' if error_type.name == _NEVER_TYPE else 'concrete'


def compact_declaration(result):
    """The fixed-key declaration record of a grammar result (contract 5.3). All eight keys are always present.

    With an identity, `entity`, `throws`, `is_async`, `typed_throws` and `identity_sha256` are read from it (an
    accessor or `throws(Never)` keeps its identity). Without one the five fields are null. The decision and the reason
    are the grammar's own; the reason is null unless the decision is `undecided`.
    """
    decision = result.throw_decision
    record = {'syntax_model': SYNTAX_MODEL, 'decision': decision,
              'reason': (result.reason or None) if decision == 'undecided' else None,
              'entity': None, 'throws': None, 'is_async': None, 'typed_throws': None, 'identity_sha256': None}
    identity = result.identity
    if identity is not None:
        effects = identity.effects
        record.update(entity=identity.entity, throws=bool(effects.throws), is_async=bool(effects.is_async),
                      typed_throws=_typed_throws(effects), identity_sha256=identity_digest(identity))
    return record


class SymbolResolver:
    """Resolves attributed import symbols; one grammar parse per distinct Swift symbol, cached by symbol string.

    The same resolver serves the stub path, the GOT path and any other consumer of a symbol's declaration in one run,
    so a second parse of the same symbol is not made. `work_steps` is the work to charge to `analysis_work`: it grows
    on the first parse of a Swift symbol and never when the cache answers or for a non-Swift symbol.
    """

    def __init__(self):
        self._cache = {}
        self.work_steps = 0

    def resolve(self, symbol):
        if type(symbol) is not str:
            return Resolution(symbol, False, NOT_SWIFT, None, None, None)
        cached = self._cache.get(symbol)
        if cached is not None:
            return cached
        if not is_swift_symbol(symbol):
            resolution = Resolution(symbol, False, NOT_SWIFT, None, None, None)
        else:
            result = parse_declaration(symbol)
            declaration = compact_declaration(result)
            resolution = Resolution(symbol, True, declaration['decision'], declaration['reason'], declaration,
                                    licence_of_record(declaration))
            self.work_steps += PARSE_WORK_BASE + len(symbol)
        self._cache[symbol] = resolution
        return resolution
