"""Group A tests for the imported-callee effect resolver of profile broad-extended-v4.

Written from the design contract alone (sections 4.1 to 4.5, 4.8, 5.2, 5.3 and 7); the module under test did not
exist when these tests were written, and no implementation was read. Section numbers below ("contract 4.3") refer
to that contract. Images are synthetic thin ARM64 files assembled by tests/stub_image_helpers.py and
tests/got_image_helpers.py and are never executed, signed or loaded; the owned fixture is not used here. Every
path that a test drives through a synthetic image is synthetic corroboration, not a compiled example: the owned
fixture has no swifterror_idiom site, so conflict and corroborated cannot be seen there (contract 7).

Public interface assumed (names, signatures and return shapes taken from the contract; a name the contract does
not give is marked "assumed name" and is the maintainer's to confirm before the module is written).

    airs.swift_import_effect_admission                                    (new library, packet P2)

        parse_declaration
            Module-global name bound to airs.swift_declaration_grammar.parse_declaration (contract 4.1: "monkeypatch
            at the name the resolver imports"). Every grammar parse the resolver makes goes through this name.
            Returns a DeclarationResult: .symbol, .identity (DeclarationIdentity or None), .throw_decision
            ('non_throwing' | 'throwing' | 'async' | 'undecided'), .reason ('' or one of the 11 closed reasons).

        licence(decision, effects) -> str                                  (contract 4.3; assumed name licence)
            decision: one of 'non_throwing', 'throwing', 'async', 'undecided'.
            effects: a mapping {'is_async': bool | None, 'typed_throws': 'none' | 'never' | 'concrete' | None},
            the vocabulary of the compact record (5.3); the values are None only when the grammar declined.
            Returns one of 'no_error_exit', 'declared_error_exit', 'refused_unsupported_effect', 'none'.
            Total and pure: never raises for any decision and effects of that vocabulary.

        licence_of_record(record) -> str                                   (contract 5.2 D2; assumed name)
            record: a compact declaration record (below). Returns licence(record['decision'],
            {'is_async': record['is_async'], 'typed_throws': record['typed_throws']}).

        caller_relation(licence_class, shape, call_kind) -> str            (contract 4.4; assumed name)
            licence_class: one of the four classes above.
            shape: 'swifterror_idiom' | 'postcall_test_only' | 'precall_zero_only' | 'none'
                   (the shape of swift-caller-error-test-v1, unchanged).
            call_kind: 'bl' (a call) or 'b' (a tail branch).
            Returns 'conflict' | 'corroborated' | 'no_signal' | 'not_applicable'.

        row_treatment(licence_class, relation) -> Treatment                (contract 4.5; assumed name)
            Treatment is a NamedTuple (retained: bool, status: str | None, reason: str | None).
            retained False means no row is made and the call is counted as skipped for its symbol (status and
            reason are then None). retained True carries status 'unresolved' and the row reason:
                no_error_exit + conflict            -> 'declaration_caller_disagreement'
                declared_error_exit (any relation)  -> 'imported_callee_outcome_unmodeled'
                refused_unsupported_effect          -> 'imported_callee_effect_unsupported'
                none                                -> 'imported_callee_abi_unqualified'
            A Treatment has no field named abi, candidate or validation (contract 5.2 D4).

        compact_declaration(result) -> dict                                (contract 5.3; assumed name)
            result: a DeclarationResult. Returns a dict with exactly the eight keys syntax_model, decision, reason,
            entity, throws, is_async, typed_throws, identity_sha256. syntax_model is 'swift-declaration-syntax-v2'.
            reason is None unless decision is 'undecided'. With an identity: entity is the identity's entity
            string, throws and is_async are bool, typed_throws is 'none' | 'never' | 'concrete' (never when the
            error type is Swift.Never, concrete for any other error type) and identity_sha256 is the SHA-256 (64
            lowercase hex) of the identity's canonical JSON (sorted keys, separators (",", ":"), ASCII). Without
            an identity those five fields are all None.

        identity_digest(identity) -> str                                   (contract 5.3; assumed name)
            The identity_sha256 value for a DeclarationIdentity.

        effect_admission(licence_class, relation) -> dict                  (contract 5.3; assumed name)
            {'model': 'swift-import-effect-admission-v1', 'licence_class': ..., 'caller_relation': ...}.

        class SymbolResolver()                                             (contract 4.1; assumed name)
            .resolve(symbol) -> Resolution, where Resolution is a NamedTuple
                (symbol, is_swift, decision, reason, declaration, licence_class).
            A symbol is Swift when it begins '$s' after optional underscores. A Swift symbol is parsed by
            parse_declaration exactly once for the life of the resolver, whatever the call site kind, and its
            result is cached by symbol string. decision is the grammar decision; reason is None unless decision
            is 'undecided'; declaration is compact_declaration of the cached result; licence_class is
            licence_of_record(declaration). A non-Swift symbol is never parsed and resolves to is_swift False,
            decision 'not_swift', reason None, declaration None, licence_class None.
            .work_steps -> int: the work charged to analysis_work for parses. It grows when the first parse of a
            Swift symbol is made, never when the cache answers, and never for a non-Swift symbol.

        The value-witness admission module (airs.swift_value_witness_admission) keeps its own module-global
        parse_declaration name; a v4 run must not parse a symbol there that the resolver already parsed.

    Engine and checker names read by the image tests (contract 2, 4.8, 5.1 to 5.3, 6.1)

        profile 'broad-extended-v4' is a key of airs.swift_broad_flow.PROFILE_MODELS and PROFILE_LIMITS, and
        recover_swift_broad_flow(image, profile='broad-extended-v4') returns a report with
            report['import_calls']['entries']: list of dicts with symbol, decision, reason, calls, stub_calls,
                got_calls, retained, skipped_non_throwing, not_swift_calls, omitted (symbol as attributed);
            report['decision_by_shape'][decision][shape]: int, all 16 cells present;
            every import row (a calls[] row whose 'admission' has import_attribution_admitted true) carries
                'declaration' (the compact record) and 'effect_admission', at the top of the row or inside
                row['admission'] (the contract says "the row" and does not fix the level; tests accept either);
            row['caller_error_test']['shape'], row['admission']['reason'] and ['status'], row['candidate'] and
                row['validation'] both None, and no 'abi' key in row['admission'].
        airs.swift_broad_accounting.check_broad_v4_report(report) -> list[str]
            Returns the failed rules, empty when the report is consistent; every element begins with its rule id
            of contract 5.2 (for example "C7: ..."). The engine calls it before returning a v4 report and fails
            closed, so an engine run that would produce a failing report raises instead of returning it; a test
            that needs the failure accepts either form and expects the rule id in the message.

Image tests are skipped while profile 'broad-extended-v4' is not registered (packet P4); library tests run from
packet P2 on. Run with: PYTHONPATH=src python3 -m unittest discover -s tests -p test_swift_import_effect_admission.py
"""
import contextlib
import dataclasses
import functools
import hashlib
import importlib.util
import json
import re
import struct
import sys
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

import indirect_v3_image_helpers as helpers  # noqa: E402
from airs import swift_value_witness_admission as witness_module  # noqa: E402
from airs import swift_import_effect_admission as effect  # noqa: E402
from airs.macho import parse_macho  # noqa: E402
from airs.swift_broad_flow import PROFILE_LIMITS, PROFILE_MODELS, recover_swift_broad_flow  # noqa: E402
from airs.swift_caller_error_test import caller_error_test  # noqa: E402
from airs.swift_declaration_grammar import REASONS as GRAMMAR_REASONS  # noqa: E402
from airs.swift_declaration_grammar import parse_declaration as real_parse  # noqa: E402
from got_image_helpers import GotImport, build_got_image, got_call  # noqa: E402
from stub_image_helpers import Import, build_stub_image  # noqa: E402

PROFILE = 'broad-extended-v4'
ENGINE_READY = PROFILE in PROFILE_MODELS and PROFILE in PROFILE_LIMITS
ENGINE_SKIP = 'packet P4 has not registered profile broad-extended-v4 yet'
ACCOUNTING_READY = importlib.util.find_spec('airs.swift_broad_accounting') is not None

SYNTAX_MODEL = 'swift-declaration-syntax-v2'
FIRST_GENERATION_MODEL = 'swift-import-declaration-syntax-v1'
EFFECT_MODEL = 'swift-import-effect-admission-v1'
DECLARATION_KEYS = {'syntax_model', 'decision', 'reason', 'entity', 'throws', 'is_async', 'typed_throws',
                    'identity_sha256'}

DECISIONS = ('non_throwing', 'throwing', 'async', 'undecided')
CLASSES = ('no_error_exit', 'declared_error_exit', 'refused_unsupported_effect', 'none')
SHAPES = ('swifterror_idiom', 'postcall_test_only', 'precall_zero_only', 'none')
KINDS = ('bl', 'b')
RELATIONS = frozenset({'conflict', 'corroborated', 'no_signal', 'not_applicable'})
# Contract 4.1: the closed list of grammar decline reasons, retyped here so a change to the grammar's list is noticed.
CLOSED_REASONS = ('invalid_input', 'thunk_or_specialization', 'unknown_substitution', 'truncated', 'malformed_symbol',
                  'trailing_input', 'unsupported_production', 'limit_exceeded', 'typed_throws', 'accessor',
                  'not_function_entity')
TYPED_THROWS = ('none', 'never', 'concrete')
REASON_DISAGREEMENT = 'declaration_caller_disagreement'
REASON_OUTCOME = 'imported_callee_outcome_unmodeled'
REASON_UNSUPPORTED = 'imported_callee_effect_unsupported'
REASON_UNQUALIFIED = 'imported_callee_abi_unqualified'

# Symbols chosen so that the real grammar (swift-declaration-syntax-v2) decides them as the comments say. The
# test class GrammarPremiseTests states each decision, so a change in the grammar fails there first.
SYMBOLS = dict(
    non_throwing='_$s1M1gyyF',
    throwing='_$s1M1fyyKF',
    # A function taking a throwing closure and throwing: how a rethrows function is mangled (contract 4.3: the
    # grammar records rethrows as throws).
    rethrowing='_$s1M1ryyyyKXEKF',
    async_='_$s1M1hyyYaF',
    async_throws='_$s1M1iyyYaKF',
    typed_concrete='_$s1M1kyy1M1EVYKF',
    typed_never='_$s1M1jyys5NeverOYKF',
    accessor='_$s1M1SV1xSivg',
    malformed='_$sZZZ',
)
SYM_A, SYM_B, SYM_C = '_$s1M1ayyF', '_$s1M1byyKF', '_$s1M1cyyKF'
NON_SWIFT = ('_malloc', '_swift_retain')

NOP, RET = 0xd503201f, 0xd65f03c0
ZERO = 0xaa1f03f5                 # mov x21, xzr (the word swift-caller-error-test-v1 recognises)
CBZ = 0xb4000055                  # cbz x21, +8 (a forward error successor)


# --- image builders -------------------------------------------------------------------------------------------
def site_words(zero, kind, test):
    """One caller: [mov x21, xzr], call or tail branch to stub 0, [cbz x21], nop, ret. The call is word 4."""
    return (NOP, NOP, NOP, ZERO if zero else NOP, (kind, ('stub', 0)), CBZ if test else RET, NOP, RET)


def build_site(symbol, *, kind='bl', zero=True, test=True):
    return build_stub_image(callers=(site_words(zero, kind, test),), imports=(Import(symbol),))


def site_image(symbol, **options):
    return build_site(symbol, **options)[0]


def multi_image():
    """Stub calls: SYM_A x4, SYM_B x2, SYM_C x1, _malloc x5, _swift_retain x5, plus a value-witness caller whose
    metadata accessor is also an attributed import (so the import path and the value-witness check both see it)."""
    imports = (Import(SYM_A), Import(SYM_B), Import(SYM_C), Import(NON_SWIFT[0]), Import(NON_SWIFT[1]),
               Import(helpers.IMPORTED_ACCESSOR))
    order = [0] * 4 + [1] * 2 + [2] + [3] * 5 + [4] * 5
    first = tuple(('bl', ('stub', index)) for index in order) + (RET,)
    second = (('bl', ('stub', 5)), *helpers.WITNESS_TAIL)
    return build_stub_image(callers=(first, second), imports=imports)[0]


def many_symbols_image(symbols):
    """One caller per symbol, each a bare call (no x21 zeroing, no error test): rows only where the licence keeps them."""
    callers = tuple((NOP, NOP, NOP, NOP, ('bl', ('stub', k)), RET, NOP, RET) for k in range(len(symbols)))
    return build_stub_image(callers=callers, imports=tuple(Import(s) for s in symbols))[0]


def got_image():
    """GOT-attributed calls: SYM_B x3 (slot 0), SYM_C x1 (slot 1), _malloc x2 (slot 2); one call per caller."""
    imports = (GotImport(SYM_B), GotImport(SYM_C), GotImport(NON_SWIFT[0]))
    callers = tuple((*got_call(slot=slot), RET) for slot in (0, 0, 0, 1, 2, 2))
    return build_got_image(callers=callers, imports=imports)[0]


def non_swift_image():
    imports = (Import(NON_SWIFT[0]), Import(NON_SWIFT[1]))
    first = tuple(('bl', ('stub', k)) for k in (0, 0, 0, 1, 1)) + (RET,)
    return build_stub_image(callers=(first,), imports=imports)[0]
# --- end image builders ---------------------------------------------------------------------------------------


def named_images():
    images = {'multi': multi_image, 'witness': lambda: helpers.imported_metadata(helpers.IMPORTED_ACCESSOR),
              'got': got_image, 'non_swift': non_swift_image,
              'bare_all': lambda: many_symbols_image([s for s in SYMBOLS.values()])}
    for name, symbol in SYMBOLS.items():
        images[name + '/idiom'] = functools.partial(site_image, symbol, zero=True, test=True)
        images[name + '/precall_only'] = functools.partial(site_image, symbol, zero=True, test=False)
        images[name + '/postcall_only'] = functools.partial(site_image, symbol, zero=False, test=True)
        images[name + '/bare'] = functools.partial(site_image, symbol, zero=False, test=False)
        images[name + '/tail'] = functools.partial(site_image, symbol, kind='b', zero=True, test=True)
    return images


IMAGES = named_images()


def flow(data):
    return recover_swift_broad_flow(parse_macho(data, limits=PROFILE_LIMITS[PROFILE]), profile=PROFILE)


@functools.lru_cache(maxsize=None)
def report(key):
    return flow(IMAGES[key]())


# --- report accessors -----------------------------------------------------------------------------------------
def norm(symbol):
    return symbol[1:] if symbol.startswith('_') else symbol


def table_entry(rep, symbol):
    found = [e for e in rep['import_calls']['entries'] if norm(e['symbol']) == norm(symbol)]
    assert len(found) == 1, (symbol, [e['symbol'] for e in rep['import_calls']['entries']])
    return found[0]


def is_import_row(row):
    return row['admission'].get('import_attribution_admitted') is True


def import_rows(rep):
    return [row for row in rep['calls'] if is_import_row(row)]


def row_field(row, name):
    """The v4 per-row record; the contract does not fix whether it sits on the row or inside its admission."""
    if name in row:
        return row[name]
    return row['admission'][name]


def rows_for(rep, symbol):
    return [row for row in import_rows(rep) if norm(row['admission']['symbol']) == norm(symbol)]


def grid_total(rep):
    return sum(sum(cells.values()) for cells in rep['decision_by_shape'].values())


def digest_of(identity):
    text = json.dumps(identity.to_json(), sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    return hashlib.sha256(text.encode('ascii')).hexdigest()


class ParseSpy:
    """Counts parse_declaration calls by symbol, optionally forcing a decision for named symbols."""

    def __init__(self, force=None):
        self.calls, self.force = [], dict(force or {})

    def __call__(self, symbol, *args, **kwargs):
        self.calls.append(symbol)
        result = real_parse(symbol, *args, **kwargs)
        forced = self.force.get(norm(symbol))
        return dataclasses.replace(result, throw_decision=forced) if forced else result

    def counts(self):
        return Counter(norm(symbol) for symbol in self.calls)


@contextlib.contextmanager
def patched(spy):
    with mock.patch.object(effect, 'parse_declaration', spy), \
            mock.patch.object(witness_module, 'parse_declaration', spy):
        yield spy


def record(decision, reason=None, *, is_async=False, typed_throws='none', identity=True):
    """A compact record for the licence tests; entity and digest are placeholders where an identity is implied."""
    return dict(syntax_model=SYNTAX_MODEL, decision=decision, reason=reason,
                entity='Function' if identity else None,
                throws=(decision == 'throwing' and typed_throws == 'none') if identity else None,
                is_async=is_async if identity else None, typed_throws=typed_throws if identity else None,
                identity_sha256='0' * 64 if identity else None)


# --- expectations written out from the tables of the contract -------------------------------------------------
def expected_licence(decision, is_async, typed_throws):
    """Contract 4.3, top to bottom."""
    if decision == 'non_throwing':
        return 'no_error_exit'
    if decision == 'throwing':
        return 'declared_error_exit' if (not is_async and typed_throws == 'none') else 'refused_unsupported_effect'
    if decision == 'async':
        return 'refused_unsupported_effect'
    return 'none'


def expected_relation(licence_class, shape, kind):
    """Contract 4.4, row by row."""
    if licence_class == 'no_error_exit':
        if shape == 'swifterror_idiom':
            return 'conflict' if kind == 'bl' else 'not_applicable'
        return 'no_signal'
    if licence_class == 'declared_error_exit':
        if kind == 'b':
            return 'not_applicable'
        return 'corroborated' if shape == 'swifterror_idiom' else 'no_signal'
    return 'not_applicable'


class GrammarPremiseTests(unittest.TestCase):
    """The decisions the other tests assume for their symbols come from the pinned grammar, not from the resolver."""

    def test_closed_reason_list_is_the_contract_list(self):
        self.assertEqual(set(CLOSED_REASONS), set(GRAMMAR_REASONS))
        self.assertEqual(len(CLOSED_REASONS), 11)

    def test_symbol_decisions(self):
        expected = dict(non_throwing=('non_throwing', ''), throwing=('throwing', ''), rethrowing=('throwing', ''),
                        async_=('async', ''), async_throws=('throwing', ''), typed_concrete=('throwing', ''),
                        typed_never=('undecided', 'typed_throws'), accessor=('undecided', 'accessor'),
                        malformed=('undecided', 'malformed_symbol'))
        self.assertEqual(set(expected), set(SYMBOLS))
        for name, (decision, reason) in expected.items():
            with self.subTest(symbol=name):
                result = real_parse(SYMBOLS[name])
                self.assertEqual((result.throw_decision, result.reason), (decision, reason))
        self.assertTrue(real_parse(SYMBOLS['async_throws']).identity.effects.is_async)
        self.assertEqual(real_parse(SYMBOLS['typed_concrete']).identity.effects.typed_throws.name, 'M.E')


class LicenceTests(unittest.TestCase):
    """A1, A2: the licence table of contract 4.3."""
    ROWS = [('non_throwing', False, 'none', 'no_error_exit'),
            ('throwing', False, 'none', 'declared_error_exit'),
            ('throwing', True, 'none', 'refused_unsupported_effect'),
            ('throwing', False, 'concrete', 'refused_unsupported_effect'),
            ('throwing', True, 'concrete', 'refused_unsupported_effect'),
            # typed_throws "never" cannot come from the grammar; here it fails closed.
            ('throwing', False, 'never', 'refused_unsupported_effect'),
            ('async', False, 'none', 'refused_unsupported_effect'),
            ('async', True, 'none', 'refused_unsupported_effect')]

    def test_a1_table_rows(self):
        for decision, is_async, typed, expected in self.ROWS:
            with self.subTest(decision=decision, is_async=is_async, typed_throws=typed):
                self.assertEqual(effect.licence(decision, {'is_async': is_async, 'typed_throws': typed}), expected)
                self.assertEqual(effect.licence_of_record(record(decision, is_async=is_async, typed_throws=typed)),
                                 expected)

    def test_a1_undecided_is_none_for_every_reason_of_the_closed_list(self):
        effects_seen = ({'is_async': None, 'typed_throws': None}, {'is_async': False, 'typed_throws': 'none'},
                        {'is_async': True, 'typed_throws': 'none'}, {'is_async': False, 'typed_throws': 'never'},
                        {'is_async': True, 'typed_throws': 'concrete'})
        for reason in CLOSED_REASONS:
            for effects in effects_seen:
                with self.subTest(reason=reason, effects=effects):
                    self.assertEqual(effect.licence('undecided', effects), 'none')
                    rec = record('undecided', reason, is_async=effects['is_async'], typed_throws=effects['typed_throws'],
                                 identity=effects['is_async'] is not None)
                    self.assertEqual(effect.licence_of_record(rec), 'none')

    def test_a1_real_grammar_results_reach_the_table(self):
        expected = dict(non_throwing='no_error_exit', throwing='declared_error_exit',
                        rethrowing='declared_error_exit', async_='refused_unsupported_effect',
                        async_throws='refused_unsupported_effect', typed_concrete='refused_unsupported_effect',
                        typed_never='none', accessor='none', malformed='none')
        for name, licence_class in expected.items():
            with self.subTest(symbol=name):
                rec = effect.compact_declaration(real_parse(SYMBOLS[name]))
                self.assertEqual(effect.licence_of_record(rec), licence_class)

    def test_a2_total_pure_and_never_anything_but_none_for_undecided(self):
        for decision in DECISIONS:
            for is_async in (False, True):
                for typed in TYPED_THROWS:
                    effects = {'is_async': is_async, 'typed_throws': typed}
                    with self.subTest(decision=decision, is_async=is_async, typed_throws=typed):
                        first = effect.licence(decision, effects)
                        self.assertIn(first, CLASSES)
                        self.assertEqual(effect.licence(decision, dict(effects)), first)
                        self.assertEqual(first, expected_licence(decision, is_async, typed))
                        if decision == 'undecided':
                            self.assertEqual(first, 'none')
        for reason in CLOSED_REASONS:
            for is_async in (False, True):
                for typed in TYPED_THROWS:
                    with self.subTest(reason=reason, is_async=is_async, typed_throws=typed):
                        rec = record('undecided', reason, is_async=is_async, typed_throws=typed)
                        self.assertEqual(effect.licence_of_record(rec), 'none')
                        self.assertEqual(effect.licence_of_record(dict(rec)), 'none')


class RelationTests(unittest.TestCase):
    """A3, A4: the caller relation matrix of contract 4.4."""

    def matrix(self):
        return {(c, s, k): effect.caller_relation(c, s, k) for c in CLASSES for s in SHAPES for k in KINDS}

    def test_a3_all_32_cells(self):
        matrix = self.matrix()
        self.assertEqual(len(matrix), 32)
        for (licence_class, shape, kind), relation in matrix.items():
            with self.subTest(licence_class=licence_class, shape=shape, kind=kind):
                self.assertEqual(relation, expected_relation(licence_class, shape, kind))

    def test_a3_named_cells_of_contract_4_4(self):
        r = effect.caller_relation
        self.assertEqual(r('no_error_exit', 'swifterror_idiom', 'bl'), 'conflict')
        self.assertEqual(r('no_error_exit', 'swifterror_idiom', 'b'), 'not_applicable')
        for shape in ('postcall_test_only', 'precall_zero_only', 'none'):
            for kind in KINDS:
                self.assertEqual(r('no_error_exit', shape, kind), 'no_signal')
            self.assertEqual(r('declared_error_exit', shape, 'bl'), 'no_signal')
        self.assertEqual(r('declared_error_exit', 'swifterror_idiom', 'bl'), 'corroborated')
        for shape in SHAPES:
            self.assertEqual(r('declared_error_exit', shape, 'b'), 'not_applicable')
            for licence_class in ('refused_unsupported_effect', 'none'):
                for kind in KINDS:
                    self.assertEqual(r(licence_class, shape, kind), 'not_applicable')

    def test_a3_vocabulary_is_exactly_the_four_relations(self):
        self.assertEqual(set(self.matrix().values()), RELATIONS)

    def test_a4_corroborated_has_one_cell_and_unknown_is_never_agreement(self):
        matrix = self.matrix()
        self.assertEqual([cell for cell, relation in matrix.items() if relation == 'corroborated'],
                         [('declared_error_exit', 'swifterror_idiom', 'bl')])
        for (licence_class, shape, kind), relation in matrix.items():
            if licence_class in ('none', 'refused_unsupported_effect'):
                with self.subTest(licence_class=licence_class, shape=shape, kind=kind):
                    self.assertEqual(relation, 'not_applicable')
                    self.assertNotIn(relation, ('corroborated', 'no_signal'))
        # A shape of "none" is silence, never agreement.
        for licence_class in CLASSES:
            for kind in KINDS:
                self.assertNotEqual(effect.caller_relation(licence_class, 'none', kind), 'corroborated')


class TreatmentTests(unittest.TestCase):
    """A5: row treatment of contract 4.5, over every (class, shape, call kind) the relation function can reach."""

    def cases(self):
        for licence_class in CLASSES:
            for shape in SHAPES:
                for kind in KINDS:
                    yield licence_class, shape, kind, effect.caller_relation(licence_class, shape, kind)

    def test_a5_treatment_table(self):
        for licence_class, shape, kind, relation in self.cases():
            with self.subTest(licence_class=licence_class, shape=shape, kind=kind, relation=relation):
                treatment = effect.row_treatment(licence_class, relation)
                if licence_class == 'no_error_exit':
                    if relation == 'conflict':
                        self.assertEqual((treatment.retained, treatment.status, treatment.reason),
                                         (True, 'unresolved', REASON_DISAGREEMENT))
                    else:
                        self.assertIn(relation, ('no_signal', 'not_applicable'))
                        self.assertIs(treatment.retained, False)
                else:
                    reason = {'declared_error_exit': REASON_OUTCOME, 'refused_unsupported_effect': REASON_UNSUPPORTED,
                              'none': REASON_UNQUALIFIED}[licence_class]
                    self.assertEqual((treatment.retained, treatment.status, treatment.reason),
                                     (True, 'unresolved', reason))

    def test_a5_declared_error_exit_is_the_same_for_every_relation(self):
        for relation in ('corroborated', 'no_signal', 'not_applicable'):
            with self.subTest(relation=relation):
                treatment = effect.row_treatment('declared_error_exit', relation)
                self.assertEqual((treatment.retained, treatment.status, treatment.reason),
                                 (True, 'unresolved', REASON_OUTCOME))

    def test_a5_no_treatment_has_another_status_and_none_attaches_abi_candidate_or_validation(self):
        for licence_class, shape, kind, relation in self.cases():
            treatment = effect.row_treatment(licence_class, relation)
            with self.subTest(licence_class=licence_class, relation=relation):
                if treatment.retained:
                    self.assertEqual(treatment.status, 'unresolved')
                self.assertNotIn(treatment.status, ('declined', 'admitted_callsite', 'admitted', 'resolved'))
                self.assertFalse({'abi', 'candidate', 'validation'} & set(treatment._fields))

    def test_the_model_name_and_the_row_record(self):
        for licence_class in CLASSES:
            for relation in sorted(RELATIONS):
                with self.subTest(licence_class=licence_class, relation=relation):
                    self.assertEqual(effect.effect_admission(licence_class, relation),
                                     {'model': EFFECT_MODEL, 'licence_class': licence_class,
                                      'caller_relation': relation})


class CompactRecordTests(unittest.TestCase):
    """A12, A13 at library level: the eight-key record of contract 5.3 and its digest."""

    def compact(self, name):
        return effect.compact_declaration(real_parse(SYMBOLS[name]))

    def test_a12_throwing(self):
        rec = self.compact('throwing')
        self.assertEqual(set(rec), DECLARATION_KEYS)
        self.assertEqual(rec['syntax_model'], SYNTAX_MODEL)
        self.assertEqual((rec['decision'], rec['reason'], rec['throws'], rec['is_async'], rec['typed_throws']),
                         ('throwing', None, True, False, 'none'))
        self.assertIsInstance(rec['entity'], str)
        self.assertTrue(rec['entity'])
        self.assertEqual(rec['entity'], real_parse(SYMBOLS['throwing']).identity.entity)

    def test_a12_non_throwing(self):
        rec = self.compact('non_throwing')
        self.assertEqual(set(rec), DECLARATION_KEYS)
        self.assertEqual(rec['syntax_model'], SYNTAX_MODEL)
        self.assertEqual((rec['decision'], rec['reason'], rec['throws'], rec['is_async'], rec['typed_throws']),
                         ('non_throwing', None, False, False, 'none'))
        self.assertTrue(rec['entity'])

    def test_a12_accessor_that_returns_an_identity_keeps_it(self):
        rec = self.compact('accessor')
        self.assertEqual(set(rec), DECLARATION_KEYS)
        self.assertEqual((rec['decision'], rec['reason']), ('undecided', 'accessor'))
        self.assertIsNotNone(rec['entity'])
        self.assertEqual(rec['entity'], real_parse(SYMBOLS['accessor']).identity.entity)
        self.assertRegex(rec['identity_sha256'], r'^[0-9a-f]{64}$')

    def test_a12_malformed_has_five_null_fields_and_a_decline_reason(self):
        rec = self.compact('malformed')
        self.assertEqual(set(rec), DECLARATION_KEYS)
        self.assertEqual((rec['syntax_model'], rec['decision']), (SYNTAX_MODEL, 'undecided'))
        self.assertIn(rec['reason'], set(CLOSED_REASONS) - {'accessor', 'typed_throws'})
        for key in ('entity', 'throws', 'is_async', 'typed_throws', 'identity_sha256'):
            self.assertIsNone(rec[key], key)

    def test_a12_a_static_accessor_the_grammar_declines_without_an_identity_stays_undecided_accessor(self):
        # Contract gap, recorded for the contract author: contract 5.3 says a record without an identity has a
        # reason other than accessor, but the grammar declines static accessors (suffix "vgZ") as `accessor` with
        # no identity. The resolver must not invent fields: the record mirrors the grammar and the licence is none.
        symbol = '_$sSS10FoundationE8EncodingV4utf8ACvgZ'
        result = real_parse(symbol)
        self.assertEqual((result.throw_decision, result.reason, result.identity), ('undecided', 'accessor', None))
        rec = effect.compact_declaration(result)
        self.assertEqual(set(rec), DECLARATION_KEYS)
        self.assertEqual((rec['decision'], rec['reason']), ('undecided', 'accessor'))
        for key in ('entity', 'throws', 'is_async', 'typed_throws', 'identity_sha256'):
            self.assertIsNone(rec[key], key)
        self.assertEqual(effect.licence_of_record(rec), 'none')

    def test_a12_effects_are_read_from_the_identity_not_guessed(self):
        expected = dict(
            async_=('async', None, False, True, 'none'),
            async_throws=('throwing', None, True, True, 'none'),
            typed_concrete=('throwing', None, False, False, 'concrete'),
            typed_never=('undecided', 'typed_throws', False, False, 'never'),
            rethrowing=('throwing', None, True, False, 'none'))
        for name, (decision, reason, throws, is_async, typed) in expected.items():
            with self.subTest(symbol=name):
                rec = self.compact(name)
                self.assertEqual(set(rec), DECLARATION_KEYS)
                self.assertEqual((rec['decision'], rec['reason'], rec['throws'], rec['is_async'],
                                  rec['typed_throws']), (decision, reason, throws, is_async, typed))
                self.assertEqual(rec['syntax_model'], SYNTAX_MODEL)
                self.assertEqual(effect.licence_of_record(rec), expected_licence(decision, is_async, typed))

    def test_a13_digest_is_the_sha256_of_the_canonical_identity(self):
        seen = {}
        for name in ('non_throwing', 'throwing', 'rethrowing', 'async_', 'async_throws', 'typed_concrete',
                     'typed_never', 'accessor'):
            with self.subTest(symbol=name):
                result = real_parse(SYMBOLS[name])
                rec = effect.compact_declaration(result)
                expected = digest_of(result.identity)
                self.assertRegex(rec['identity_sha256'], r'^[0-9a-f]{64}$')
                self.assertEqual(rec['identity_sha256'], expected)
                self.assertEqual(effect.identity_digest(result.identity), expected)
                seen[name] = rec['identity_sha256']
        self.assertEqual(len(set(seen.values())), len(seen), 'different identities must give different digests')

    def test_a13_same_symbol_gives_the_same_record_every_time(self):
        for name in ('throwing', 'non_throwing', 'accessor', 'malformed'):
            with self.subTest(symbol=name):
                self.assertEqual(self.compact(name), self.compact(name))


class ResolverTests(unittest.TestCase):
    """A11 at library level, A15 and the Swift-prefix rule of contract 4.1."""

    def test_swift_prefix_is_dollar_s_after_optional_underscores(self):
        resolver = effect.SymbolResolver()
        for symbol, swift in (('$s1M1fyyF', True), ('_$s1M1fyyF', True), ('__$s1M1fyyF', True),
                              ('_swift_retain', False), ('swift_retain', False), ('_malloc', False),
                              ('$S1M1fyyF', False), ('_$S1M1fyyF', False), ('_OBJC_CLASS_$_NSObject', False)):
            with self.subTest(symbol=symbol):
                self.assertIs(resolver.resolve(symbol).is_swift, swift)

    def test_a15_non_swift_symbols_are_never_parsed(self):
        spy = ParseSpy()
        with patched(spy):
            resolver = effect.SymbolResolver()
            for symbol in ('_malloc', '_swift_retain', 'swift_release', '$S1M1fyyF'):
                for _ in range(3):
                    resolution = resolver.resolve(symbol)
                    self.assertEqual((resolution.is_swift, resolution.decision, resolution.reason,
                                      resolution.declaration, resolution.licence_class),
                                     (False, 'not_swift', None, None, None))
            self.assertEqual(resolver.work_steps, 0)
        self.assertEqual(spy.calls, [])

    def test_a11_one_parse_per_distinct_symbol_whatever_the_call_site(self):
        spy = ParseSpy()
        symbols = (SYM_A, SYM_B, SYM_C)
        with patched(spy):
            resolver = effect.SymbolResolver()
            for site in ('stub', 'got', 'stub', 'got', 'stub'):   # one cache for both attribution paths
                for symbol in symbols:
                    resolver.resolve(symbol)
            first = [resolver.resolve(s) for s in symbols]
            second = [resolver.resolve(s) for s in symbols]
        self.assertEqual(spy.counts(), Counter({norm(s): 1 for s in symbols}))
        self.assertEqual(len(spy.calls), 3)
        self.assertEqual(first, second)

    def test_a11_the_cache_is_keyed_by_the_symbol_string(self):
        spy = ParseSpy()
        with patched(spy):
            resolver = effect.SymbolResolver()
            resolver.resolve('_$s1M1fyyKF')
            resolver.resolve('$s1M1fyyKF')
        # Distinct strings are distinct keys; the contract caches by symbol string, so this is two parses.
        self.assertEqual(len(spy.calls), 2)

    def test_resolution_values(self):
        resolver = effect.SymbolResolver()
        expected = dict(non_throwing=('non_throwing', None, 'no_error_exit'),
                        throwing=('throwing', None, 'declared_error_exit'),
                        async_=('async', None, 'refused_unsupported_effect'),
                        async_throws=('throwing', None, 'refused_unsupported_effect'),
                        typed_concrete=('throwing', None, 'refused_unsupported_effect'),
                        typed_never=('undecided', 'typed_throws', 'none'),
                        accessor=('undecided', 'accessor', 'none'),
                        malformed=('undecided', 'malformed_symbol', 'none'))
        for name, (decision, reason, licence_class) in expected.items():
            with self.subTest(symbol=name):
                resolution = resolver.resolve(SYMBOLS[name])
                self.assertIs(resolution.is_swift, True)
                self.assertEqual(resolution.symbol, SYMBOLS[name])
                self.assertEqual((resolution.decision, resolution.reason, resolution.licence_class),
                                 (decision, reason, licence_class))
                self.assertEqual(resolution.declaration, effect.compact_declaration(real_parse(SYMBOLS[name])))
                self.assertEqual(resolution.declaration['decision'], decision)
                self.assertEqual(resolution.declaration['reason'], reason)

    def test_a_double_underscore_symbol_is_swift_and_undecided_because_the_grammar_declines_it(self):
        resolution = effect.SymbolResolver().resolve('__$s1M1fyyF')
        self.assertIs(resolution.is_swift, True)
        self.assertEqual((resolution.decision, resolution.reason, resolution.licence_class),
                         ('undecided', real_parse('__$s1M1fyyF').reason, 'none'))
        self.assertIn(resolution.reason, CLOSED_REASONS)

    def test_the_decision_never_comes_from_anywhere_but_the_grammar_result(self):
        spy = ParseSpy(force={norm(SYM_B): 'async'})
        with patched(spy):
            resolution = effect.SymbolResolver().resolve(SYM_B)
        self.assertEqual((resolution.decision, resolution.licence_class), ('async', 'refused_unsupported_effect'))

    def test_work_is_charged_once_per_distinct_symbol(self):
        resolver = effect.SymbolResolver()
        self.assertEqual(resolver.work_steps, 0)
        resolver.resolve(SYM_A)
        once = resolver.work_steps
        self.assertGreater(once, 0)
        for _ in range(5):
            resolver.resolve(SYM_A)
        self.assertEqual(resolver.work_steps, once)
        resolver.resolve('_malloc')
        self.assertEqual(resolver.work_steps, once)
        resolver.resolve(SYM_B)
        self.assertGreater(resolver.work_steps, once)
        twice = resolver.work_steps
        resolver.resolve(SYM_B)
        self.assertEqual(resolver.work_steps, twice)


@unittest.skipUnless(ENGINE_READY, ENGINE_SKIP)
class SiteOnSyntheticImageTests(unittest.TestCase):
    """A6 to A10: one call site per synthetic image. Synthetic corroboration, not compiled examples."""

    def only_row(self, rep):
        self.assertEqual(len(rep['calls']), 1)
        (row,) = rep['calls']
        self.assertTrue(is_import_row(row))
        return row

    def check_row_shape(self, row):
        # Contract 5.2 D4 and 4.5: imported rows stay unresolved and carry no abi, candidate or validation.
        self.assertEqual(row['admission']['status'], 'unresolved')
        self.assertIsNone(row['candidate'])
        self.assertIsNone(row['validation'])
        self.assertNotIn('abi', row['admission'])
        self.assertEqual(set(row_field(row, 'effect_admission')), {'model', 'licence_class', 'caller_relation'})
        self.assertEqual(row_field(row, 'effect_admission')['model'], EFFECT_MODEL)

    def test_a6_conflict_path(self):
        """Synthetic: mov x21, xzr; bl <stub>; cbz x21, with the stub attributed to a non_throwing symbol."""
        rep = report('non_throwing/idiom')
        row = self.only_row(rep)
        self.check_row_shape(row)
        self.assertEqual(row['admission']['reason'], REASON_DISAGREEMENT)
        self.assertEqual(row['caller_error_test']['shape'], 'swifterror_idiom')
        self.assertEqual(row_field(row, 'effect_admission')['licence_class'], 'no_error_exit')
        self.assertEqual(row_field(row, 'effect_admission')['caller_relation'], 'conflict')
        entry = table_entry(rep, SYMBOLS['non_throwing'])
        self.assertEqual((entry['decision'], entry['reason'], entry['calls'], entry['retained'],
                          entry['skipped_non_throwing'], entry['not_swift_calls'], entry['omitted']),
                         ('non_throwing', None, 1, 1, 0, 0, 0))
        self.assertEqual(rep['decision_by_shape']['non_throwing']['swifterror_idiom'], 1)
        self.assertEqual(grid_total(rep), 1)
        self.assertEqual(rep['reason_counts'], {REASON_DISAGREEMENT: 1})
        self.assertEqual(rep['status_counts'], {'unresolved': 1})

    def test_a7_tail_branch_is_skipped_and_counted(self):
        """Synthetic: the same caller with `b <stub>` in place of `bl`."""
        data, layout = build_site(SYMBOLS['non_throwing'], kind='b', zero=True, test=True)
        rep = report('non_throwing/tail')
        self.assertEqual(rep['calls'], [])
        entry = table_entry(rep, SYMBOLS['non_throwing'])
        self.assertEqual((entry['calls'], entry['retained'], entry['skipped_non_throwing'], entry['omitted']),
                         (1, 0, 1, 0))
        words = struct.unpack_from('<8I', data, layout.caller_addrs[0] - layout.base)
        self.assertEqual(words[4] & 0xfc000000, 0x14000000, 'the site is a tail branch')
        located = [(layout.caller_addrs[0] + 4 * i, word) for i, word in enumerate(words)]
        shape = caller_error_test(located, 4, 0, len(words), ())['shape']
        self.assertNotEqual(shape, 'swifterror_idiom')
        self.assertEqual(rep['decision_by_shape']['non_throwing'][shape], 1)
        self.assertEqual(grid_total(rep), 1)

    def test_a8_corroboration(self):
        """Synthetic: mov x21, xzr; bl <stub>; cbz x21 to a throwing symbol, then the same without the mov."""
        rep = report('throwing/idiom')
        row = self.only_row(rep)
        self.check_row_shape(row)
        self.assertEqual(row['admission']['reason'], REASON_OUTCOME)
        self.assertEqual(row['caller_error_test']['shape'], 'swifterror_idiom')
        self.assertEqual(row_field(row, 'effect_admission')['licence_class'], 'declared_error_exit')
        self.assertEqual(row_field(row, 'effect_admission')['caller_relation'], 'corroborated')
        self.assertEqual(table_entry(rep, SYMBOLS['throwing'])['retained'], 1)
        self.assertEqual(rep['decision_by_shape']['throwing']['swifterror_idiom'], 1)

        rep = report('throwing/postcall_only')
        row = self.only_row(rep)
        self.check_row_shape(row)
        self.assertEqual(row['admission']['reason'], REASON_OUTCOME)
        self.assertEqual(row['caller_error_test']['shape'], 'postcall_test_only')
        self.assertEqual(row_field(row, 'effect_admission')['caller_relation'], 'no_signal')
        self.assertEqual(rep['decision_by_shape']['throwing']['postcall_test_only'], 1)

    def test_a8_declared_error_exit_for_every_shape_and_for_a_tail_branch(self):
        expected = {'idiom': 'corroborated', 'precall_only': 'no_signal', 'postcall_only': 'no_signal',
                    'bare': 'no_signal', 'tail': 'not_applicable'}
        for variant, relation in expected.items():
            for name in ('throwing', 'rethrowing'):
                with self.subTest(symbol=name, variant=variant):
                    rep = report(name + '/' + variant)
                    row = self.only_row(rep)
                    self.check_row_shape(row)
                    self.assertEqual(row['admission']['reason'], REASON_OUTCOME)
                    self.assertEqual(row_field(row, 'effect_admission')['caller_relation'], relation)

    def test_a9_refused_effects_never_conflict_or_corroborate(self):
        """Synthetic: async, async throws and throws(E) symbols, each behind the full swifterror idiom."""
        for name, decision in (('async_', 'async'), ('async_throws', 'throwing'), ('typed_concrete', 'throwing')):
            for variant in ('idiom', 'precall_only', 'postcall_only', 'bare', 'tail'):
                with self.subTest(symbol=name, variant=variant):
                    rep = report(name + '/' + variant)
                    row = self.only_row(rep)
                    self.check_row_shape(row)
                    self.assertEqual(row['admission']['reason'], REASON_UNSUPPORTED)
                    admission = row_field(row, 'effect_admission')
                    self.assertEqual(admission['licence_class'], 'refused_unsupported_effect')
                    self.assertEqual(admission['caller_relation'], 'not_applicable')
                    entry = table_entry(rep, SYMBOLS[name])
                    self.assertEqual((entry['decision'], entry['retained'], entry['skipped_non_throwing']),
                                     (decision, 1, 0))
                    self.assertEqual(rep['reason_counts'], {REASON_UNSUPPORTED: 1})
        idiom = report('async_/idiom')
        self.assertEqual(only(idiom)['caller_error_test']['shape'], 'swifterror_idiom')
        self.assertEqual(idiom['decision_by_shape']['async']['swifterror_idiom'], 1)
        self.assertEqual(report('async_throws/idiom')['decision_by_shape']['throwing']['swifterror_idiom'], 1)

    def test_a10_undecided_accessor_and_throws_never(self):
        for name, reason in (('accessor', 'accessor'), ('typed_never', 'typed_throws')):
            for variant in ('idiom', 'bare', 'tail'):
                with self.subTest(symbol=name, variant=variant):
                    rep = report(name + '/' + variant)
                    row = self.only_row(rep)
                    self.check_row_shape(row)
                    self.assertEqual(row['admission']['reason'], REASON_UNQUALIFIED)
                    admission = row_field(row, 'effect_admission')
                    self.assertEqual(admission['licence_class'], 'none')
                    self.assertEqual(admission['caller_relation'], 'not_applicable')
                    entry = table_entry(rep, SYMBOLS[name])
                    self.assertEqual((entry['decision'], entry['reason'], entry['retained']), ('undecided', reason, 1))
                    self.assertEqual(sum(rep['decision_by_shape']['undecided'].values()), 1)

    def test_undecided_for_a_decline_reason_is_retained_the_same_way(self):
        rep = report('malformed/bare')
        row = self.only_row(rep)
        self.check_row_shape(row)
        self.assertEqual(row['admission']['reason'], REASON_UNQUALIFIED)
        self.assertEqual(row_field(row, 'effect_admission')['licence_class'], 'none')
        entry = table_entry(rep, SYMBOLS['malformed'])
        self.assertEqual((entry['decision'], entry['reason']), ('undecided', 'malformed_symbol'))

    def test_non_throwing_without_a_conflict_leaves_no_row_in_any_shape(self):
        for variant in ('precall_only', 'postcall_only', 'bare', 'tail'):
            with self.subTest(variant=variant):
                rep = report('non_throwing/' + variant)
                self.assertEqual(rep['calls'], [])
                entry = table_entry(rep, SYMBOLS['non_throwing'])
                self.assertEqual((entry['calls'], entry['retained'], entry['skipped_non_throwing']), (1, 0, 1))
                self.assertEqual(rep['status_counts'], {})
                self.assertEqual(rep['reason_counts'], {})
                self.assertEqual(grid_total(rep), 1)

    def test_every_retained_row_in_every_image_is_unresolved(self):
        for key in IMAGES:
            rep = report(key)
            for row in import_rows(rep):
                with self.subTest(image=key, pc=row['call_pc']):
                    self.check_row_shape(row)
                    self.assertIn(row['admission']['reason'], (REASON_DISAGREEMENT, REASON_OUTCOME, REASON_UNSUPPORTED,
                                                               REASON_UNQUALIFIED))
            self.assertEqual(set(rep['status_counts']) - {'unresolved', 'declined'}, set(), key)


def only(rep):
    (row,) = rep['calls']
    return row


@unittest.skipUnless(ENGINE_READY, ENGINE_SKIP)
class RecordsOnRowsTests(unittest.TestCase):
    """A12, A13, A14: the compact declaration carried by each import row."""

    def test_a12_row_declaration_has_the_eight_keys(self):
        cases = dict(throwing='throwing/bare', non_throwing='non_throwing/idiom', accessor='accessor/bare',
                     malformed='malformed/bare')
        for name, key in cases.items():
            with self.subTest(symbol=name):
                rep = report(key)
                (row,) = rep['calls']
                declaration = row_field(row, 'declaration')
                self.assertEqual(set(declaration), DECLARATION_KEYS)
                self.assertEqual(declaration['syntax_model'], SYNTAX_MODEL)
                self.assertEqual(declaration, effect.compact_declaration(real_parse(SYMBOLS[name])))
        throwing = row_field(only(report('throwing/bare')), 'declaration')
        self.assertEqual((throwing['decision'], throwing['reason'], throwing['throws'], throwing['typed_throws']),
                         ('throwing', None, True, 'none'))
        self.assertTrue(throwing['entity'])
        plain = row_field(only(report('non_throwing/idiom')), 'declaration')
        self.assertEqual((plain['decision'], plain['reason'], plain['throws'], plain['is_async']),
                         ('non_throwing', None, False, False))
        accessor = row_field(only(report('accessor/bare')), 'declaration')
        self.assertEqual((accessor['decision'], accessor['reason']), ('undecided', 'accessor'))
        self.assertIsNotNone(accessor['entity'])
        broken = row_field(only(report('malformed/bare')), 'declaration')
        self.assertEqual(broken['decision'], 'undecided')
        self.assertIn(broken['reason'], set(CLOSED_REASONS) - {'accessor', 'typed_throws'})
        for key in ('entity', 'throws', 'is_async', 'typed_throws', 'identity_sha256'):
            self.assertIsNone(broken[key], key)

    def test_a13_row_digest_and_identical_records_for_one_symbol(self):
        for name in ('throwing', 'async_throws', 'typed_concrete', 'accessor'):
            with self.subTest(symbol=name):
                (row,) = report(name + '/bare')['calls']
                declaration = row_field(row, 'declaration')
                self.assertRegex(declaration['identity_sha256'], r'^[0-9a-f]{64}$')
                self.assertEqual(declaration['identity_sha256'], digest_of(real_parse(SYMBOLS[name]).identity))
        # Two sites of one symbol, with different shapes and call kinds, carry identical declaration records.
        data = build_stub_image(callers=(site_words(True, 'bl', True), site_words(False, 'b', False)),
                                imports=(Import(SYMBOLS['throwing']),))[0]
        data = patch_second_caller_to_stub_zero(data)
        rep = flow(data)
        rows = rows_for(rep, SYMBOLS['throwing'])
        self.assertEqual(len(rows), 2)
        self.assertEqual(row_field(rows[0], 'declaration'), row_field(rows[1], 'declaration'))
        self.assertNotEqual(row_field(rows[0], 'effect_admission')['caller_relation'],
                            row_field(rows[1], 'effect_admission')['caller_relation'])
        # Different identities give different digests.
        digests = {row_field(only(report(n + '/bare')), 'declaration')['identity_sha256']
                   for n in ('throwing', 'async_throws', 'typed_concrete', 'accessor')}
        self.assertEqual(len(digests), 4)

    def test_a14_the_first_generation_model_never_appears_on_an_import_row(self):
        checked = 0
        for key in IMAGES:
            for row in import_rows(report(key)):
                with self.subTest(image=key, pc=row['call_pc']):
                    checked += 1
                    declaration = row_field(row, 'declaration')
                    self.assertEqual(declaration['syntax_model'], SYNTAX_MODEL)
                    self.assertNotIn(FIRST_GENERATION_MODEL, json.dumps(declaration))
                    self.assertNotIn(FIRST_GENERATION_MODEL, json.dumps(row, sort_keys=True))
        self.assertGreater(checked, 20)

    def test_the_declaration_is_not_the_full_grammar_identity(self):
        for key in ('throwing/bare', 'async_throws/bare', 'accessor/bare'):
            with self.subTest(image=key):
                declaration = row_field(only(report(key)), 'declaration')
                self.assertEqual(set(declaration), DECLARATION_KEYS)
                for value in declaration.values():
                    self.assertNotIsInstance(value, (dict, list))


def patch_second_caller_to_stub_zero(data):
    """Both callers of the two-site image already name stub 0 (site_words uses ('stub', 0)); nothing to patch.

    Kept as a named step so the two-site image reads as built from the same helper."""
    return data


@unittest.skipUnless(ENGINE_READY, ENGINE_SKIP)
class NonSwiftTests(unittest.TestCase):
    def test_a15_non_swift_stubs_make_no_row_and_no_parse(self):
        spy = ParseSpy()
        with patched(spy):
            rep = flow(non_swift_image())
        self.assertEqual(spy.calls, [])
        self.assertEqual(rep['calls'], [])
        self.assertEqual(rep['status_counts'], {})
        for symbol, calls in (('_malloc', 3), ('_swift_retain', 2)):
            with self.subTest(symbol=symbol):
                entry = table_entry(rep, symbol)
                self.assertEqual(entry['decision'], 'not_swift')
                self.assertIsNone(entry['reason'])
                self.assertEqual((entry['calls'], entry['stub_calls'], entry['got_calls']), (calls, calls, 0))
                self.assertEqual(entry['not_swift_calls'], entry['calls'])
                self.assertEqual((entry['retained'], entry['skipped_non_throwing'], entry['omitted']), (0, 0, 0))
        self.assertEqual(grid_total(rep), 0)


@unittest.skipUnless(ENGINE_READY, ENGINE_SKIP)
class OneParsePerSymbolOnImagesTests(unittest.TestCase):
    """A11 on synthetic images, with parse_declaration replaced by a counting spy."""

    def test_stub_path_and_value_witness_check_share_one_parse(self):
        spy = ParseSpy()
        with patched(spy):
            rep = flow(multi_image())
        expected = Counter({norm(SYM_A): 1, norm(SYM_B): 1, norm(SYM_C): 1, norm(helpers.IMPORTED_ACCESSOR): 1})
        self.assertEqual(spy.counts(), expected,
                         'each distinct $s symbol is parsed exactly once, including the value-witness accessor')
        self.assertEqual(len(spy.calls), 4)
        for symbol in NON_SWIFT:
            self.assertNotIn(norm(symbol), spy.counts())
        # The call counts that make the parse count meaningful (contract 4.8): calls do not drive parses.
        self.assertEqual(table_entry(rep, SYM_A)['calls'], 4)
        self.assertEqual(table_entry(rep, SYM_B)['calls'], 2)
        self.assertEqual(table_entry(rep, SYM_C)['calls'], 1)
        self.assertEqual(table_entry(rep, NON_SWIFT[0])['calls'], 5)
        self.assertEqual(table_entry(rep, NON_SWIFT[1])['calls'], 5)
        self.assertEqual(table_entry(rep, helpers.IMPORTED_ACCESSOR)['calls'], 1)
        witness_rows = [row for row in rep['calls'] if 'value_witness_admission' in row]
        self.assertEqual([r['value_witness_admission']['admitted'] for r in witness_rows], [True])
        self.assertEqual(witness_rows[0]['value_witness_admission']['symbol'], helpers.IMPORTED_ACCESSOR)

    def test_got_path_parses_each_symbol_once(self):
        spy = ParseSpy()
        with patched(spy):
            rep = flow(got_image())
        self.assertEqual(spy.counts(), Counter({norm(SYM_B): 1, norm(SYM_C): 1}))
        self.assertEqual(len(spy.calls), 2)
        self.assertEqual(table_entry(rep, SYM_B)['got_calls'], 3)
        self.assertEqual(table_entry(rep, SYM_C)['got_calls'], 1)
        self.assertEqual(table_entry(rep, NON_SWIFT[0])['decision'], 'not_swift')

    def test_the_parse_count_does_not_depend_on_the_number_of_calls(self):
        few, many = ParseSpy(), ParseSpy()
        with patched(few):
            flow(many_symbols_image([SYM_A, SYM_B]))
        with patched(many):
            flow(multi_image())
        self.assertEqual(few.counts(), Counter({norm(SYM_A): 1, norm(SYM_B): 1}))
        self.assertEqual(max(many.counts().values()), 1)

    def test_a11_the_resolver_charges_the_work_once(self):
        # Work is analysis_work; a symbol called many times must cost no more parse work than one called once.
        once = flow(many_symbols_image([SYM_A]))['analysis_work']
        for calls in (4, 8):
            first = tuple(('bl', ('stub', 0)) for _ in range(calls)) + (RET,)
            data = build_stub_image(callers=(first,), imports=(Import(SYM_A),))[0]
            rep = flow(data)
            self.assertEqual(table_entry(rep, SYM_A)['calls'], calls)
            # Calls skipped as non-throwing add no row work, so the totals differ only by the scanned words.
            self.assertLessEqual(rep['analysis_work'] - once, 4 * calls, calls)


@unittest.skipUnless(ENGINE_READY and ACCOUNTING_READY, ENGINE_SKIP + ' or packet P3 (swift_broad_accounting) is absent')
class ValueWitnessRuleTests(unittest.TestCase):
    """A16: a symbol the value-witness admission accepts as a metadata accessor must be non_throwing in the table (C7)."""

    def checker(self):
        from airs.swift_broad_accounting import check_broad_v4_report
        return check_broad_v4_report

    def test_a16_real_decision_passes(self):
        rep = report('witness')
        accepted = [row['value_witness_admission'] for row in rep['calls']
                    if row.get('value_witness_admission', {}).get('admitted')]
        self.assertEqual([w['symbol'] for w in accepted], [helpers.IMPORTED_ACCESSOR])
        self.assertEqual(table_entry(rep, helpers.IMPORTED_ACCESSOR)['decision'], 'non_throwing')
        self.assertEqual(self.checker()(rep), [])

    def test_a16_a_throwing_decision_for_that_symbol_fails_rule_c7(self):
        spy = ParseSpy(force={norm(helpers.IMPORTED_ACCESSOR): 'throwing'})
        with patched(spy):
            try:
                rep = flow(helpers.imported_metadata(helpers.IMPORTED_ACCESSOR))
            except Exception as error:        # the engine fails closed on a report its own checker rejects (6.1)
                self.assertIn('C7', str(error))
                return
        failures = self.checker()(rep)
        self.assertTrue(failures)
        for failure in failures:
            self.assertTrue(failure.startswith('C7'), failure)


if __name__ == '__main__':
    unittest.main()


class StaticAccessorRecordTests(unittest.TestCase):
    def test_static_getter_is_declined_as_accessor_without_identity(self):
        # Contract 5.3 as amended (section 10): the grammar declines a static getter with reason `accessor` and no
        # identity; the compact record carries that reason with the five identity fields null, licence `none`.
        from airs.swift_declaration_grammar import parse_declaration
        from airs.swift_import_effect_admission import compact_declaration, licence_of_record
        record = compact_declaration(parse_declaration('$ss11CommandLineO9argumentsSaySSGvgZ'))
        self.assertEqual((record['decision'], record['reason']), ('undecided', 'accessor'))
        for key in ('entity', 'throws', 'is_async', 'typed_throws', 'identity_sha256'):
            self.assertIsNone(record[key], key)
        self.assertEqual(licence_of_record(record), 'none')
