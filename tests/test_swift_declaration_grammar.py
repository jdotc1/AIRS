"""Independent declaration examples from swift-6.4.2-RELEASE Mangling.rst."""
import dataclasses
import json
import random
import unittest
from pathlib import Path

from airs.swift_declaration_grammar import (
    ENTITY_KINDS, PINNED_TOOLCHAIN_TAG, REASONS, SYNTAX_MODEL,
    GrammarLimits, parse_declaration,
)

ROOT = Path(__file__).resolve().parents[1]

# Source effects are separate from admissibility: dispatch thunks and accessors
# remain undecided even when the source declaration's effects are known.
# OwnedImports.swift: loadData, decodeItem, writeText, Item.init(from:), and
# standard-library calls made by those declarations and the top-level statements.
FIXTURE_CASES = {
    '_$s10Foundation3URLVMa': (False, 'non_throwing', ''),
    # CommandLine.arguments is a static getter; all accessors remain undecided.
    '_$ss11CommandLineO9argumentsSaySSGvgZ': (False, 'undecided', 'accessor'),
    '_$s10Foundation3URLV15fileURLWithPathACSSh_tcfC': (False, 'non_throwing', ''),
    '_$ss5print_9separator10terminatoryypd_S2StF': (False, 'non_throwing', ''),
    '_$s10Foundation4DataV10contentsOf7optionsAcA3URLVh_So20NSDataReadingOptionsVtKcfC': (True, 'throwing', ''),
    '_$s10Foundation11JSONDecoderCMa': (False, 'non_throwing', ''),
    '_$s10Foundation11JSONDecoderCACycfc': (False, 'non_throwing', ''),
    # JSONDecoder.decode ends in the dispatch-thunk operator Tj.
    '_$s10Foundation11JSONDecoderC6decode_4fromxxm_AA4DataVtKSeRzlFTj': (True, 'undecided', 'thunk_or_specialization'),
    '_$sSS10FoundationE8EncodingVMa': (False, 'non_throwing', ''),
    # String.Encoding.utf8 is a static getter, hence an accessor.
    '_$sSS10FoundationE8EncodingV4utf8ACvgZ': (False, 'undecided', 'accessor'),
    '_$sSy10FoundationE5write2to10atomically8encodingyAA3URLV_SbSSAAE8EncodingVtKF': (True, 'throwing', ''),
    '_$ss6HasherV5_seedABSi_tcfC': (False, 'non_throwing', ''),
    '_$ss6HasherV8_combineyySuF': (False, 'non_throwing', ''),
    '_$ss6HasherV9_finalizeSiyF': (False, 'non_throwing', ''),
    '_$ss27_stringCompareWithSmolCheck__9expectingSbs11_StringGutsV_ADs01_G16ComparisonResultOtF': (False, 'non_throwing', ''),
    # CodingKey.debugDescription is a getter, hence an accessor.
    '_$ss9CodingKeyPsE16debugDescriptionSSvg': (False, 'undecided', 'accessor'),
    # CodingKey.description is also a getter, hence an accessor.
    '_$ss9CodingKeyPsE11descriptionSSvg': (False, 'undecided', 'accessor'),
    # Decoder.container ends in the dispatch-thunk operator Tj.
    '_$ss7DecoderP9container7keyedBys22KeyedDecodingContainerVyqd__Gqd__m_tKs9CodingKeyRd__lFTj': (True, 'undecided', 'thunk_or_specialization'),
    '_$ss22KeyedDecodingContainerV6decode_6forKeyS2im_xtKF': (True, 'throwing', ''),
}

# Each return type is embedded in entity-spec/function-signature with no arguments.
# Entries cite the relevant Mangling.rst production name, never a v1 parser.
RETURN_TYPES = (
    ('Si', 'nominal', 'Swift.Int'),                 # standard-substitutions
    ('ScM', 'nominal', 'Swift.MainActor'),           # KNOWN-TYPE-KIND-2
    ('1M1SV', 'nominal', 'M.S'),                    # any-generic-type
    ('SaySiG', 'bound_generic', 'Swift.Array'),     # bound-generic-type
    ('SiSg', 'bound_generic', 'Swift.Optional'),    # type (optional shortcut)
    ('SiXSq', 'bound_generic', 'Swift.Optional'),   # type (sugared optional)
    ('SiXSa', 'bound_generic', 'Swift.Array'),      # type (sugared array)
    ('SiSSXSD', 'bound_generic', 'Swift.Dictionary'), # type (sugared dictionary)
    ('SDySiSSG', 'bound_generic', 'Swift.Dictionary'), # bound-generic-type
    ('Si1a_SS1bt', 'tuple', None),                  # type-list/list-type
    ('Sim', 'metatype', None),                     # type (metatype)
    ('SiXMt', 'metatype', None),                   # METATYPE-REPR
    ('SiXMo', 'metatype', None),                   # METATYPE-REPR
    ('1M1P_pXp', 'existential_metatype', None),     # type (existential metatype)
    ('1M1P_pXmT', 'existential_metatype', None),    # METATYPE-REPR
    ('1M1P_p', 'existential', None),               # existential-layout
    ('1M1P_1M1Qp', 'composition', None),           # protocol-list
    ('Si_SSQP', 'pack', None),                     # pack-element-list
    ('yyc', 'function', None),                    # type/function-signature
    ('yyXf', 'function', None),                   # FUNCTION-KIND
    ('yyXE', 'function', None),                   # FUNCTION-KIND
    ('yyXB', 'function', None),                   # FUNCTION-KIND
    ('yyXC', 'function', None),                   # FUNCTION-KIND
    ('yyXA', 'function', None),                   # FUNCTION-KIND
    ('yyXK', 'function', None),                   # FUNCTION-KIND
    ('yyXU', 'function', None),                   # FUNCTION-KIND
    ('yyXL', 'function', None),                   # FUNCTION-KIND
    ('yyXzC3foo', 'function', None),              # FUNCTION-KIND / C-TYPE
    ('yyXzB3foo', 'function', None),              # FUNCTION-KIND / C-TYPE
)

# symbol, context, name, labels. entity-spec, context, decl-name, identifier,
# OPERATOR-FIXITY, substitution and standard-substitutions respectively.
FUNCTIONS = (
    ('$s1M1fyyF', [['module', 'M']], 'f', []),
    ('$s4Word0A0yyF', [['module', 'Word']], 'Word', []),
    ('$s1M007caf_dmayyF', [['module', 'M']], 'café', []),
    ('$s1M1popyS2iF', [['module', 'M']], '+', [None]),
    ('$s1M1poPyS2iF', [['module', 'M']], '+', [None]),
    ('$s1M1poiySiSi_SitF', [['module', 'M']], '+', [None, None]),
    ('$s1M1fL_yyF', [['module', 'M']], 'f', []),
    ('$s1M1f1dLLyyF', [['module', 'M']], 'f', []),
    ('$s1M1SV1fyyF', [['module', 'M'], ['struct', 'S']], 'f', []),
    ('$s1M1EO1fyyF', [['module', 'M'], ['enum', 'E']], 'f', []),
    ('$s1M1CC1fyyF', [['module', 'M'], ['class', 'C']], 'f', []),
    ('$s1M1PP1fyyF', [['module', 'M'], ['protocol', 'P']], 'f', []),
    ('$s1M1Aa1fyyF', [['module', 'M'], ['type_alias', 'A']], 'f', []),
    ('$sSi1ME1fyyF', [['extension', 'M'], ['module', 'Swift'], ['struct', 'Int']], 'f', []),
    ('$s1M1SV1dyXZ1fyyF', [['module', 'M'], ['struct', 'S'], ['anonymous', 'd']], 'f', []),
    ('$s1M1fyyF1gyyF', [['module', 'M'], ['local', 'f']], 'g', []),
    ('$s1M1SV1fyyAC_ACtF', [['module', 'M'], ['struct', 'S']], 'f', [None, None]),
    ('$s1M1SV1fyyAC_A2CtF', [['module', 'M'], ['struct', 'S']], 'f', [None, None, None]),
    ('$s1M1f1aySiF', [['module', 'M']], 'f', ['a']),
)

# ACCESSOR / ADDRESSOR-KIND; storage-only 'p' is not an accessor entity.
ACCESSORS = {
    'g': 'Getter', 's': 'Setter', 'm': 'MaterializeForSet',
    'G': 'GlobalGetter', 'w': 'WillSet', 'W': 'DidSet',
    'r': 'ReadAccessor', 'M': 'ModifyAccessor', 'x': 'YieldingMutateAccessor',
    'y': 'YieldingBorrowAccessor', 'b': 'BorrowAccessor', 'z': 'MutateAccessor',
    'i': 'InitAccessor', 'au': 'UnsafeMutableAddressor',
    'aO': 'OwningMutableAddressor', 'ao': 'NativeOwningMutableAddressor',
    'aP': 'NativePinningMutableAddressor', 'lu': 'UnsafeAddressor',
    'lO': 'OwningAddressor', 'lo': 'NativeOwningAddressor',
    'lp': 'NativePinningAddressor',
}

# global, curry-thunk and specialization. Outlined operations use WO, not T.
SUFFIX_CASES = tuple('$s1M1fyyF' + suffix for suffix in (
    'TA', 'Ta', 'TQ_', 'TY_', 'TwS', 'Tj', 'Tq', 'TO', 'To', 'TD',
    'Td', 'TE', 'TF', 'TI', 'Tu', 'TX', 'Twb', 'TwB', 'Twc', 'Twd',
    'Tc', 'TS', 'Tm', 'Si_Tg5', 'Si_TG5', 'Si_TB5', 'Si_Ts5',
    'Si_Ti5', 'SiTp5', 'SiTP5', 'Tf4n_n',
)) + tuple('$sSiWO' + code for code in 'yersBb cCdDfFhHijg'.replace(' ', '')) + (
    '$s1M1SVAA1PA2A1PP1fyyFTW',  # protocol-conformance / global
    '$s1M1fyyF1M1gyyFTV',       # entity / global
    '$syycyycTR', '$syycyycTr', '$syycyycSiTy', # type / global
    '$syycTC',                                 # type / global
    '$s1M1SV1xSivpSiTK', '$s1M1SV1xSivpSiTk', # entity / global
    '$sSiSQRzlTH', '$sSiSQRzlTh',               # generic-signature / global
    '$s1M1fyyFTJfSpSr', '$s1M1fyyFTJVfSpSr',   # AUTODIFF-FUNCTION-KIND
    '$syycyycTJOf', '$syycTJSfSpSrSP',          # INDEX-SUBSET
    '$sIy_ytTz_', '$sIy_ytTZ_',                # impl-function-type / global
    '$s1M1fyyFTemnn_',                        # bridge-spec
    '$s1M1fyyFTTI', '$s1M1fyyFTx',             # thunk operators in Demangler.cpp
)


def projection(entity='Function', context=None, name='f', labels=()):
    return dict(entity=entity, context=context or [['module', 'M']],
                name=name, labels=list(labels), parameter_count=len(labels))


def depth(value):
    if isinstance(value, dict):
        return max((1 + depth(v) for v in value.values()), default=0)
    if isinstance(value, (list, tuple)):
        return max((1 + depth(v) for v in value), default=0)
    return 0


class DeclarationGrammarTests(unittest.TestCase):
    def invariant(self, result):
        self.assertIn(result.throw_decision, ('non_throwing', 'throwing', 'async', 'undecided'))
        self.assertEqual(result.syntax_model, SYNTAX_MODEL)
        self.assertEqual(result.reason == '', result.throw_decision != 'undecided')
        self.assertEqual(result.offset is None, result.reason == '')
        if result.reason:
            self.assertIn(result.reason, REASONS)
            self.assertIsInstance(result.offset, int)
            self.assertGreaterEqual(result.offset, 0)
            self.assertLessEqual(result.offset, len(result.symbol))
        if result.identity is not None:
            self.assertIn(result.identity.entity, ENTITY_KINDS)
            self.assertLessEqual(depth(result.identity.to_json()), 27)
            self.assertEqual(result.identity.serialize(), json.dumps(
                result.identity.to_json(), sort_keys=True,
                separators=(',', ':'), ensure_ascii=True).encode('ascii'))
            if result.reason:
                self.assertEqual(result.offset, len(result.symbol))
        if result.reason == 'thunk_or_specialization' or (
                result.offset is not None and result.offset < len(result.symbol)):
            self.assertIsNone(result.identity)

    def positive(self, symbol, expected, decision='non_throwing', reason='', limits=None):
        kwargs = {'limits': limits} if limits else {}
        result = parse_declaration(symbol, **kwargs)
        repeated = parse_declaration(symbol, **kwargs)
        self.assertEqual(result, repeated)
        self.invariant(result)
        self.assertEqual((result.throw_decision, result.reason), (decision, reason), symbol)
        self.assertIsNotNone(result.identity, symbol)
        self.assertEqual(result.identity.serialize(), repeated.identity.serialize())
        self.assertEqual(result.identity.oracle_projection(), expected, symbol)
        return result.identity

    def test_constants_and_defaults(self):
        self.assertEqual(SYNTAX_MODEL, 'swift-declaration-syntax-v2')
        self.assertEqual(PINNED_TOOLCHAIN_TAG, 'swift-6.4.2-RELEASE')
        self.assertIsInstance(REASONS, frozenset)
        self.assertIsInstance(ENTITY_KINDS, frozenset)
        self.assertEqual(dataclasses.asdict(GrammarLimits()), dict(
            max_symbol_length=4096, max_identifier_length=256,
            max_context_depth=16, max_nodes=256, max_substitutions=128,
            max_parameters=64, max_type_depth=16, max_generic_parameters=32,
            max_generic_requirements=64))

    def test_frozen_results(self):
        limits = GrammarLimits()
        with self.assertRaises(dataclasses.FrozenInstanceError):
            limits.max_nodes = 1
        result = parse_declaration('$s1M1fyyF')
        self.assertTrue(dataclasses.is_dataclass(result))
        self.assertFalse(hasattr(result, '__dict__'))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.reason = 'changed'
        self.assertIsNotNone(result.identity)
        self.assertFalse(hasattr(result.identity, '__dict__'))
        with self.assertRaises(dataclasses.FrozenInstanceError):
            result.identity.name = 'changed'

    def test_functions_identifiers_contexts_substitutions(self):
        for symbol, context, name, labels in FUNCTIONS:
            with self.subTest(symbol=symbol):
                identity = self.positive(symbol, projection(context=context, name=name, labels=labels))
                if 'L_' in symbol or 'LL' in symbol:
                    self.assertIsNotNone(identity.name_discriminator)

    def test_return_type_productions(self):
        identity = self.positive('$s1M1fyyF', projection()) # empty-list
        self.assertEqual(identity.result.kind, 'void')
        for spelling, kind, name in RETURN_TYPES:
            with self.subTest(type=spelling):
                identity = self.positive('$s1M1fy' + spelling + 'yF', projection())
                self.assertEqual(identity.result.kind, kind)
                if name:
                    self.assertEqual(identity.result.name, name)
        for spelling, convention in (
            ('c', 'thick'), ('Xf', 'thin'), ('XE', 'noescape'),
            ('XB', 'block'), ('XC', 'c'), ('XA', 'escaping_autoclosure'),
        ):  # FUNCTION-KIND
            identity = self.positive('$s1M1fyyy' + spelling + 'yF', projection())
            self.assertEqual(identity.result.convention, convention)

    def test_parameter_modifiers(self):
        for code, modifier in (
            ('z', 'inout'), ('h', 'shared'), ('n', 'owned'),
            ('Yu', 'sending'), ('Yi', 'isolated'), ('Yk', 'noDerivative'),
        ):  # params-type / list-type; sending is Demangler.cpp's Yu operator.
            with self.subTest(modifier=modifier):
                identity = self.positive('$s1M1fyySi' + code + 'F', projection(labels=[None]))
                self.assertEqual(identity.parameters[0].kind, 'nominal')
                self.assertIn(modifier, identity.parameters[0].modifiers)
        identity = self.positive('$s1M1fyySid_tF', projection(labels=[None])) # list-type
        self.assertIn('variadic', identity.parameters[0].modifiers)
        identity = self.positive('$s1M1fyyyyXKF', projection(labels=[None])) # FUNCTION-KIND
        self.assertIn('autoclosure', identity.parameters[0].modifiers)
        identity = self.positive('$s1M1fyySi1a_SS1bt_tF', projection(labels=[None])) # type-list
        self.assertEqual(identity.parameters[0].kind, 'tuple')
        self.assertEqual(identity.parameters[0].labels, ('a', 'b'))

    def test_generic_parameters_members_opaque_and_packs(self):
        cases = (
            ('$s1M1fyxylF', 'generic_param', 'τ_0_0'),  # type
            ('$s1M1fyqd__yrz_lF', 'generic_param', 'τ_1_0'), # GENERIC-PARAM-INDEX
            ('$s1M1fyqd0__yrzz_lF', 'generic_param', 'τ_2_0'), # GENERIC-PARAM-INDEX
            ('$s1M1fyqd1__yrzzz_lF', 'generic_param', 'τ_3_0'), # GENERIC-PARAM-INDEX
            ('$s1M1fy1AQzylF', 'dependent_member', None), # assoc-type-name
            ('$s1M1fyx1AQaylF', 'dependent_member', None), # associated-type
            ('$s1M1fyQryF', 'opaque', None), # type / opaque result
            ('$s1M1fyxq_QpyRvzRv_r0_lF', 'pack_expansion', None), # type / generic-param-marker
        )
        for symbol, kind, name in cases:
            with self.subTest(symbol=symbol):
                identity = self.positive(symbol, projection())
                self.assertEqual(identity.result.kind, kind)
                if name:
                    self.assertEqual(identity.result.name, name)

    def test_large_index_substitution(self):
        # substitution / INDEX: thirteen nominal contexts create substitution
        # 26, addressed by A_. Each identifier and nominal type enters the table.
        symbol = '$s1M1AV1BV1CV1DV1EV1FV1GV1HV1IV1JV1KV1LV1MV1fyA_yF'
        context = [['module', 'M']] + [['struct', name] for name in 'ABCDEFGHIJKLM']
        identity = self.positive(symbol, projection(context=context))
        self.assertEqual(identity.result.kind, 'nominal')
        self.assertEqual(identity.result.name, 'M.A.B.C.D.E.F.G.H.I.J.K.L.M')

    def test_generic_requirement_kinds(self):
        for signature, kinds, counts in (
            ('SQRzl', ['conformance'], (1,)),
            ('SiRszl', ['same_type'], (1,)),
            ('RlzCl', ['layout'], (1,)),
            ('1M1CCRbzl', ['base_class'], (1,)),
            ('Rvzl', ['pack_marker'], (1,)),
            ('q_RhzRvzRv_r0_l', ['same_shape', 'pack_marker', 'pack_marker'], (2,)),
            ('Ri_zl', ['inverse'], (1,)),
        ):  # requirement / generic-signature / generic-param-pack-marker
            with self.subTest(signature=signature):
                identity = self.positive('$s1M1fyy' + signature + 'F', projection())
                self.assertEqual(identity.generic_signature.parameter_counts, counts)
                self.assertCountEqual([r.kind for r in identity.generic_signature.requirements], kinds)
        # context / generic-signature: constrained extension of Array.
        self.positive('$sSa1MSQRzlE1fyyF', projection(
            context=[['extension', 'M'], ['module', 'Swift'], ['struct', 'Array']]))

    def test_effects(self):
        cases = (
            ('$s1M1fyyKF', 'throwing', '', True, False, None, 0),
            ('$s1M1fyyYaF', 'async', '', False, True, None, 0),
            ('$s1M1fyyYaKF', 'throwing', '', True, True, None, 0),
            ('$s1M1fyy1M1EOYKF', 'throwing', '', False, False, None, 0),
            ('$s1M1fyys5NeverOYKF', 'undecided', 'typed_throws', False, False, None, 0),
            ('$s1M1fyyYas5NeverOYKF', 'undecided', 'typed_throws', False, True, None, 0),
            ('$s1M1fyyyyKXEF', 'non_throwing', '', False, False, None, 1),
            ('$s1M1fyyyyKXEKF', 'throwing', '', True, False, None, 1),
            ('$s1M1fyyScMYcF', 'non_throwing', '', False, False, 'global_actor:Swift.MainActor', 0),
            ('$s1M1fyyYAF', 'non_throwing', '', False, False, 'isolated_any', 0),
        )  # function-signature / throws / async / function-isolation
        for symbol, decision, reason, throws, is_async, isolation, count in cases:
            with self.subTest(symbol=symbol):
                identity = self.positive(symbol, projection(labels=[None] * count), decision, reason)
                self.assertEqual(identity.effects.throws, throws)
                self.assertEqual(identity.effects.is_async, is_async)
                self.assertEqual(identity.effects.isolation, isolation)
                if 'YK' in symbol:
                    self.assertEqual(identity.effects.typed_throws.kind, 'nominal')
                    self.assertEqual(identity.effects.typed_throws.name,
                                     'Swift.Never' if 'Never' in symbol else 'M.E')
                if count:
                    self.assertTrue(identity.parameters[0].effects.throws)
        # function-isolation nested in a closure does not isolate the outer type.
        identity = self.positive('$s1M1fyyyyYAXEF', projection(labels=[None]))
        self.assertIsNone(identity.effects.isolation)
        self.assertEqual(identity.parameters[0].effects.isolation, 'isolated_any')
        # list-type (isolated parameter).
        identity = self.positive('$s1M1fyyScAYiF', projection(labels=[None]))
        self.assertEqual(identity.effects.isolation, 'isolated_parameter')

    def test_accessors(self):
        for code, entity in ACCESSORS.items():
            with self.subTest(accessor=code):
                self.positive('$s1M1SV1xSiv' + code, projection(
                    entity, [['module', 'M'], ['struct', 'S']], 'x'), 'undecided', 'accessor')
        # entity-spec / subscript; its function type has one parameter.
        self.positive('$s1M1SVyS2icig', projection(
            'Getter', [['module', 'M'], ['struct', 'S']], 'subscript', [None]),
            'undecided', 'accessor')

    def test_initializers_destructors_metadata(self):
        # entity-spec (fC/fc/fd/fD), global (Ma).
        for symbol, entity, context, name in (
            ('$s1M1SVACycfC', 'Allocator', [['module', 'M'], ['struct', 'S']], 'init'),
            ('$s1M1SVACycfc', 'Constructor', [['module', 'M'], ['struct', 'S']], 'init'),
            ('$s1M1CCfd', 'Destructor', [['module', 'M'], ['class', 'C']], 'deinit'),
            ('$s1M1CCfD', 'Deallocator', [['module', 'M'], ['class', 'C']], 'deinit'),
            ('$s1M1SVMa', 'TypeMetadataAccessFunction', [['module', 'M']], 'S'),
        ):
            with self.subTest(entity=entity):
                identity = self.positive(symbol, projection(entity, context, name))
                if entity in {'Allocator', 'Constructor'}:
                    self.assertEqual(identity.result.kind, 'nominal')
                    self.assertEqual(identity.result.name, 'M.S')
                else:
                    self.assertEqual(identity.parameters, ())
                    self.assertIsNone(identity.result)

    def test_nonfunction_and_unconsumed_input(self):
        # entity (nominal-type), global (type descriptor), ACCESSOR (storage).
        for symbol in ('$s1M1SV', '$s1M1SVMn', '$s1M1SV1xSivp'):
            result = parse_declaration(symbol)
            self.invariant(result)
            self.assertEqual(result.reason, 'not_function_entity')
        for symbol in ('$s1M1fyyF?', '_$s1M1fyyF?'):
            result = parse_declaration(symbol)
            self.invariant(result)
            self.assertEqual(result.reason, 'trailing_input')
            self.assertEqual(result.offset, len(symbol) - 1)
            self.assertIsNone(result.identity)

    def test_fixture_decisions(self):
        fixture = json.loads((ROOT / 'fixtures/swift-error-flow/broad-imports/expected.json').read_text())
        symbols = {row['symbol'] for row in fixture['stub_calls'] if row['symbol'].startswith('_$s')}
        self.assertEqual(symbols, set(FIXTURE_CASES))
        self.assertEqual(sum(row[0] for row in FIXTURE_CASES.values()), 5)
        self.assertEqual(len(FIXTURE_CASES), 19)
        self.assertEqual({decision: sum(row[1] == decision for row in FIXTURE_CASES.values())
                          for decision in ('throwing', 'non_throwing', 'undecided')},
                         {'throwing': 3, 'non_throwing': 10, 'undecided': 6})
        for symbol, (_, decision, reason) in FIXTURE_CASES.items():
            with self.subTest(symbol=symbol):
                result = parse_declaration(symbol)
                self.invariant(result)
                self.assertEqual((result.throw_decision, result.reason), (decision, reason))

    def test_suffix_families(self):
        for symbol in SUFFIX_CASES:
            with self.subTest(symbol=symbol):
                result = parse_declaration(symbol)
                self.invariant(result)
                self.assertEqual(result.reason, 'thunk_or_specialization')
                self.assertIsNone(result.identity)

    def test_invalid_inputs(self):
        for value in ('_T01M1fyyF', '$S1M1fyyF', '$e1M1fyyF', '', 'é', b'\xff',
                      None, 42, [], {}, object(), '__$s1M1fyyF'):
            with self.subTest(value=repr(value)):
                result = parse_declaration(value)
                self.invariant(result)
                self.assertEqual(result.reason, 'invalid_input')
                self.assertEqual(result.offset, 0)
        for value in ('$s1M1fyyF', '_$s1M1fyyF', b'$s1M1fyyF'):
            self.positive(value, projection())

    def test_every_truncation(self):
        # entity-spec: free function, nominal method, nested local function.
        examples = ('$s1M1fyyKF', '$s1M1SV1fyySi_SStF', '$s1M1fyyF1gyyF')
        complete_prefixes = {'$s1M1fyyF': ('non_throwing', '', projection()),
                             '$s1M1SV': ('undecided', 'not_function_entity', None)}
        for symbol in examples:
            for end in range(len(symbol)):
                prefix = symbol[:end]
                with self.subTest(symbol=symbol, end=end):
                    if prefix in complete_prefixes:
                        decision, reason, expected = complete_prefixes[prefix]
                        if expected is not None:
                            self.positive(prefix, expected, decision, reason)
                        else:
                            result = parse_declaration(prefix)
                            self.invariant(result)
                            self.assertEqual((result.throw_decision, result.reason), (decision, reason))
                    else:
                        result = parse_declaration(prefix)
                        self.invariant(result)
                        self.assertEqual(result.throw_decision, 'undecided')
                        self.assertIsNone(result.identity)

    def test_unknown_substitutions(self):
        for code in ('AZ', 'A_', 'A999_', 'ScZ'):
            result = parse_declaration('$s1M1fyy' + code + 'F') # substitution
            self.invariant(result)
            self.assertEqual(result.reason, 'unknown_substitution')

    def limit_pair(self, symbol, field, needed):
        # Same valid input: exactly its required budget, then one unit short.
        allowed = dataclasses.replace(GrammarLimits(), **{field: needed})
        accepted = parse_declaration(symbol, limits=allowed)
        self.invariant(accepted)
        self.assertEqual(accepted.throw_decision, 'non_throwing', symbol)
        self.assertIsNotNone(accepted.identity)
        denied = parse_declaration(symbol, limits=dataclasses.replace(allowed, **{field: needed - 1}))
        self.invariant(denied)
        self.assertEqual(denied.reason, 'limit_exceeded')
        self.assertIn(field, denied.detail)
        if field == 'max_symbol_length':
            self.assertEqual(denied.offset, 0)

    def test_defined_limit_boundaries(self):
        # identifier / context / params-type / generic-signature / requirement.
        for symbol, field, needed in (
            ('$s1M1fyyF', 'max_symbol_length', 9),
            ('_$s1M1fyyF', 'max_symbol_length', 10),
            ('$s1M4longyyF', 'max_identifier_length', 4),
            ('$s1M1SV1fyyF', 'max_context_depth', 2),
            ('$s1M1fyySi_SStF', 'max_parameters', 2),
            ('$s1M1fyy r0_lF'.replace(' ', ''), 'max_generic_parameters', 2),
            ('$s1M1fyySQRzSHRzlF', 'max_generic_requirements', 2),
        ):
            with self.subTest(field=field):
                self.limit_pair(symbol, field, needed)

    def test_node_substitution_and_type_depth_boundaries(self):
        # type (optional shortcut): result Optional<Int> contains exactly two
        # TypeNodes: bound_generic and nominal. No outer function node counts.
        self.limit_pair('$s1M1fySiSgyF', 'max_nodes', 2)
        # identifier / entity-spec: M and f each add one identifier entry;
        # empty parameter/result tuples and the function add no substitutions.
        self.limit_pair('$s1M1fyyF', 'max_substitutions', 2)
        # type (optional shortcut): Int has depth 1, Optional<Int> depth 2.
        self.limit_pair('$s1M1fySiSgyF', 'max_type_depth', 2)

    def test_identity_depth_exact_boundary(self):
        # type (optional shortcut) / params-type / function-signature.
        # parameters array is at 1, its optional node at 2. Twelve args/element
        # pairs add 24: Int is at 26 and its scalar name is at 27.
        limits = dataclasses.replace(GrammarLimits(), max_type_depth=32)
        allowed = '$s1M1fyySi' + 'Sg' * 12 + 'F'
        identity = self.positive(allowed, projection(labels=[None]), limits=limits)
        self.assertEqual(depth(identity.to_json()), 27)
        # result starts at 1; thirteen pairs put Int at 27, its name at 28.
        # Type depth is only 14, below the explicitly supplied budget of 32.
        denied = '$s1M1fySi' + 'Sg' * 13 + 'yF'
        result = parse_declaration(denied, limits=limits)
        self.invariant(result)
        self.assertEqual((result.throw_decision, result.reason), ('undecided', 'limit_exceeded'))
        self.assertIn('identity_depth', result.detail)
        self.assertEqual(result.offset, len(denied))
        self.assertIsNone(result.identity)

    def test_literal_serialization(self):
        # entity-spec/function-signature, standard-substitutions, global (Ma).
        # Hand-written canonical objects: every dataclass field is present;
        # keys sorted, tuples arrays, None null, and no JSON whitespace.
        cases = (
            ('$s1M1fyyF', projection(),
             b'{"context":[{"enclosing":null,"generic_signature":null,"kind":"module","name":"M"}],"effects":{"is_async":false,"isolation":null,"throws":false,"typed_throws":null},"entity":"Function","fixity":null,"generic_signature":null,"labels":[],"name":"f","name_discriminator":null,"parameters":[],"result":{"args":[],"convention":null,"effects":null,"kind":"void","labels":[],"modifiers":[],"name":""}}'),
            ('$s1M1fySiyF', projection(),
             b'{"context":[{"enclosing":null,"generic_signature":null,"kind":"module","name":"M"}],"effects":{"is_async":false,"isolation":null,"throws":false,"typed_throws":null},"entity":"Function","fixity":null,"generic_signature":null,"labels":[],"name":"f","name_discriminator":null,"parameters":[],"result":{"args":[],"convention":null,"effects":null,"kind":"nominal","labels":[],"modifiers":[],"name":"Swift.Int"}}'),
            ('$s1M1SVMa', projection('TypeMetadataAccessFunction', name='S'),
             b'{"context":[{"enclosing":null,"generic_signature":null,"kind":"module","name":"M"}],"effects":{"is_async":false,"isolation":null,"throws":false,"typed_throws":null},"entity":"TypeMetadataAccessFunction","fixity":null,"generic_signature":null,"labels":[],"name":"S","name_discriminator":null,"parameters":[],"result":null}'),
        )
        for symbol, expected_projection, expected_bytes in cases:
            with self.subTest(symbol=symbol):
                identity = self.positive(symbol, expected_projection)
                self.assertEqual(identity.serialize(), expected_bytes)
                self.assertEqual(identity.to_json(), json.loads(expected_bytes))

    def test_distinct_declarations_have_distinct_identities(self):
        pairs = (
            ('$sSa4mainSiRszlE3sumSiyF', '$sSa4mainSdRszlE3sumSiyF'),
            ('$s4main2ppopyySizF', '$s4main2ppoPyySizF'),
            ('$s4main3fooyyF3barL_yyF', '$s4main3foo1aySi_tF3barL_yyF'),
            ('$s4main1xSivg3barL_yyF', '$s4main1xSivs3barL_yyF'),
            ('$s4main1fyyyyYbXEF', '$s4main1fyyyyXEF'),
        )
        for left, right in pairs:
            with self.subTest(left=left, right=right):
                first, second = parse_declaration(left), parse_declaration(right)
                for result in (first, second):
                    self.invariant(result)
                    self.assertNotEqual(result.throw_decision, 'undecided')
                    self.assertIsNotNone(result.identity)
                self.assertNotEqual(first.identity.serialize(), second.identity.serialize())
        for code, fixity in (('op', 'prefix'), ('oP', 'postfix'), ('oi', 'infix')):
            symbol = next(row[0] for row in FUNCTIONS if '1p' + code in row[0])
            self.assertEqual(parse_declaration(symbol).identity.fixity, fixity)
        extension = next(c for c in parse_declaration(pairs[0][0]).identity.context
                         if c.kind == 'extension')
        self.assertIsNotNone(extension.generic_signature)
        self.assertEqual([r.kind for r in extension.generic_signature.requirements], ['same_type'])
        local = next(c for c in parse_declaration(pairs[2][0]).identity.context
                     if c.kind == 'local')
        self.assertIsNotNone(local.enclosing)
        self.assertEqual((local.enclosing.entity, local.enclosing.name), ('Function', 'foo'))
        parameter = parse_declaration(pairs[4][0]).identity.parameters[0]
        self.assertEqual(parameter.kind, 'function')
        self.assertIn('sendable', parameter.modifiers)

    def test_non_entity_global_cannot_be_context(self):
        for symbol in ('$s4main1SVMa3fooyyF', '$s4main1SVMaAByyF'):
            with self.subTest(symbol=symbol):
                result = parse_declaration(symbol)
                self.invariant(result)
                self.assertEqual((result.throw_decision, result.reason),
                                 ('undecided', 'malformed_symbol'))
                self.assertIsNone(result.identity)

    def test_metadata_accessor_operand(self):
        result = parse_declaration('$s4main1SVySiGMa')
        self.invariant(result)
        self.assertEqual((result.throw_decision, result.reason),
                         ('undecided', 'unsupported_production'))
        self.assertIsNone(result.identity)
        self.positive('$s4main1SVMa', projection('TypeMetadataAccessFunction',
                                              [['module', 'main']], 'S'))

    def test_totality_and_determinism(self):
        rng = random.Random(20261113)
        inputs = [bytes(rng.randrange(256) for _ in range(rng.randrange(257))) for _ in range(2000)]
        positives = [row[0] for row in FUNCTIONS] + [
            '$s1M1fy' + spelling + 'yF' for spelling, _, _ in RETURN_TYPES]
        for symbol in positives:
            inputs.append(symbol)
            for _ in range(8):
                raw = bytearray(symbol.encode('ascii'))
                index = rng.randrange(len(raw))
                operation = rng.randrange(3)
                if operation == 0:
                    raw[index] = rng.randrange(256)
                elif operation == 1:
                    del raw[index]
                else:
                    raw.insert(index, rng.randrange(256))
                inputs.append(bytes(raw))
        for value in inputs:
            with self.subTest(value=value):
                first, second = parse_declaration(value), parse_declaration(value)
                self.invariant(first)
                self.assertEqual(first, second)
                if first.identity is not None:
                    self.assertEqual(first.identity.serialize(), second.identity.serialize())


if __name__ == '__main__':
    unittest.main()
