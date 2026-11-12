"""Tests for airs.swift_import_declarations (syntax model swift-import-declaration-syntax-v1).

Expectations derive from the imported-declaration contract and its productions (packets A to E), from the
oracle corpus and from swift-demangle output, all recorded in the tracked fixture
fixtures/swift-error-flow/import-declarations (see its README). No expected value was taken from the
implementation under test. The verdict (admit or decline) and the admitted fields are binding; a decline
reason is checked only against the contract's reason set, except where the contract names the reason
(resource limits, I6). No image is executed.
"""
import csv
import inspect
import json
import re
import sys
import unittest
from dataclasses import FrozenInstanceError, asdict, fields
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from stub_image_helpers import RET, Import, build_stub_image  # noqa: E402
from airs import swift_broad_flow  # noqa: E402
from airs.macho import parse_macho  # noqa: E402
from airs.report import dumps  # noqa: E402
from airs.swift_broad_flow import EXTENDED_BROAD_LIMITS, recover_swift_broad_flow  # noqa: E402
from airs.swift_declaration_profiles import (  # noqa: E402
    BroadDeclarationResult, ParseLimits, SwiftContext, SwiftType, UnsupportedReason, parse_broad_declaration,
)
from airs.swift_import_declarations import (  # noqa: E402
    IMPORT_SYNTAX_MODEL, ImportEntity, ImportedDeclaration, parse_import_declaration,
)

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'swift-error-flow' / 'import-declarations'
MODEL = 'swift-import-declaration-syntax-v1'
OLD_MODEL = 'swift-broad-declaration-syntax-v1'
PROFILE = 'broad-imports-v1'

# CONTRACT "Decline reasons": the new parser introduces no reason value and reuses exactly these.
CONTRACT_REASONS = frozenset({
    'invalid_grammar', 'unsupported_production', 'unknown_substitution', 'unconsumed_suffix',
    'unicode_identifier', 'word_substitution', 'async_context', 'typed_throws', 'thunk_or_specialization',
    'closure_type', 'generic_requirements', 'protocol_context', 'resource_limit', 'invalid_input',
})
ENTITY_VALUES = {'function', 'metadata_accessor', 'initializer', 'allocating_initializer'}
NOMINAL_KINDS = {'struct', 'class', 'enum'}
# README of the fixture: @_silgen_name rows, admitted by any mangled-name grammar, wrong at source level.
SILGEN_RESIDUAL = frozenset({'$s1M4fakeyyF', '$s1M5fakeAyyF'})
ACCESSOR_SHAPE = re.compile(r'getter|setter|modify|read|addressor')
EFFECT_WORD = re.compile(r'\b(throws|rethrows|async)\b')
THROWS_WORD = re.compile(r'\b(throws|rethrows)\b')


def read_table(name):
    with open(FIXTURE / name, encoding='utf-8', newline='') as handle:
        return list(csv.DictReader(handle, delimiter='\t', quoting=csv.QUOTE_NONE))


def table_throws(row):
    return {'true': True, 'false': False}[row['expected_throws']]


# The 19 Swift symbols of fixtures/swift-error-flow/broad-imports (nm spelling, leading underscore).
# Outcomes: CONTRACT "Required per-symbol outcomes"; fields: PRODUCTIONS section 8 (worked parses);
# demangled forms: swift-demangle --compact in the broad-imports evidence.
# (symbol, throws or None for decline, entity, module, name, labels, parameter count, context nominal names)
FIXTURE_19 = (
    ('_$s10Foundation11JSONDecoderC6decode_4fromxxm_AA4DataVtKSeRzlFTj', None),                       # 8.1
    ('_$s10Foundation11JSONDecoderCACycfc', False, 'initializer', 'Foundation', '', (), 0,
     (('JSONDecoder', 'class'),)),                                                                     # 8.2
    ('_$s10Foundation11JSONDecoderCMa', False, 'metadata_accessor', 'Foundation', '', (), 0,
     (('JSONDecoder', 'class'),)),                                                                     # 8.3
    ('_$s10Foundation3URLV15fileURLWithPathACSSh_tcfC', False, 'allocating_initializer', 'Foundation', '',
     ('fileURLWithPath',), 1, (('URL', 'struct'),)),                                                   # 8.4
    ('_$s10Foundation3URLVMa', False, 'metadata_accessor', 'Foundation', '', (), 0, (('URL', 'struct'),)),  # 8.5
    ('_$s10Foundation4DataV10contentsOf7optionsAcA3URLVh_So20NSDataReadingOptionsVtKcfC', True,
     'allocating_initializer', 'Foundation', '', ('contentsOf', 'options'), 2, (('Data', 'struct'),)),   # 8.6
    ('_$sSS10FoundationE8EncodingV4utf8ACvgZ', None),                                                  # 8.7
    ('_$sSS10FoundationE8EncodingVMa', False, 'metadata_accessor', 'Foundation', '', (), 0,
     (('String', 'extension'), ('Encoding', 'struct'))),                                               # 8.8
    ('_$sSy10FoundationE5write2to10atomically8encodingyAA3URLV_SbSSAAE8EncodingVtKF', None),           # 8.9
    ('_$ss11CommandLineO9argumentsSaySSGvgZ', None),                                                   # 8.10
    ('_$ss22KeyedDecodingContainerV6decode_6forKeyS2im_xtKF', None),                                   # 8.11
    ('_$ss27_stringCompareWithSmolCheck__9expectingSbs11_StringGutsV_ADs01_G16ComparisonResultOtF', False,
     'function', 'Swift', '_stringCompareWithSmolCheck', (None, None, 'expecting'), 3, ()),             # 8.12
    ('_$ss5print_9separator10terminatoryypd_S2StF', False, 'function', 'Swift', 'print',
     (None, 'separator', 'terminator'), 3, ()),                                                        # 8.13
    ('_$ss6HasherV5_seedABSi_tcfC', False, 'allocating_initializer', 'Swift', '', ('_seed',), 1,
     (('Hasher', 'struct'),)),                                                                         # 8.14
    ('_$ss6HasherV8_combineyySuF', False, 'function', 'Swift', '_combine', (None,), 1,
     (('Hasher', 'struct'),)),                                                                         # 8.15
    ('_$ss6HasherV9_finalizeSiyF', False, 'function', 'Swift', '_finalize', (), 0,
     (('Hasher', 'struct'),)),                                                                         # 8.16
    ('_$ss7DecoderP9container7keyedBys22KeyedDecodingContainerVyqd__Gqd__m_tKs9CodingKeyRd__lFTj', None),  # 8.17
    ('_$ss9CodingKeyPsE11descriptionSSvg', None),                                                      # 8.18
    ('_$ss9CodingKeyPsE16debugDescriptionSSvg', None),                                                 # 8.19
)
FIXTURE_SYMBOLS = tuple(item[0] for item in FIXTURE_19)
ADMITTED_19 = tuple(item for item in FIXTURE_19 if item[1] is not None)
SKIPPABLE_19 = tuple(item[0] for item in ADMITTED_19 if item[1] is False)
GETTERS_19 = ('_$sSS10FoundationE8EncodingV4utf8ACvgZ', '_$ss11CommandLineO9argumentsSaySSGvgZ',
              '_$ss9CodingKeyPsE11descriptionSSvg', '_$ss9CodingKeyPsE16debugDescriptionSSvg')


def parse(symbol, limits=None):
    if limits is None:
        return parse_import_declaration(symbol)
    return parse_import_declaration(symbol, limits=limits)


class ImportDeclarationCase(unittest.TestCase):
    def assertAdmit(self, symbol, throws, limits=None):
        result = parse(symbol, limits)
        self.assertIsInstance(result, BroadDeclarationResult)
        self.assertTrue(result.supported, (symbol, result.unsupported_reason, result.detail, result.offset))
        self.assertIsNone(result.unsupported_reason)
        identity = result.identity
        self.assertIsInstance(identity, ImportedDeclaration)
        self.assertIs(identity.throws, throws, symbol)
        self.assertEqual(identity.symbol, symbol)
        self.assertEqual(identity.syntax_model, MODEL)
        self.assertIsInstance(identity.entity, ImportEntity)
        return identity

    def assertDecline(self, symbol, reason=None, limits=None):
        result = parse(symbol, limits)
        self.assertIsInstance(result, BroadDeclarationResult)
        self.assertFalse(result.supported, symbol)
        self.assertIsNone(result.identity, symbol)          # I3: no partial identity
        self.assertIsInstance(result.unsupported_reason, UnsupportedReason)
        self.assertIn(result.unsupported_reason.value, CONTRACT_REASONS)
        self.assertIsInstance(result.detail, str)
        self.assertIsInstance(result.offset, int)
        if reason is not None:
            self.assertEqual(result.unsupported_reason.value, reason, symbol)
        return result

    def assertSkippable(self, symbol):
        result = parse(symbol)
        self.assertFalse(result.supported and not result.identity.throws, symbol)


class ModuleShapeTests(ImportDeclarationCase):
    def test_model_identity(self):
        self.assertEqual(IMPORT_SYNTAX_MODEL, MODEL)
        self.assertNotEqual(IMPORT_SYNTAX_MODEL, OLD_MODEL)
        for near in ('swift-import-declaration-syntax-v2', 'swift-import-declaration-syntax', OLD_MODEL, MODEL + ' '):
            with self.subTest(near=near):
                self.assertNotEqual(IMPORT_SYNTAX_MODEL, near)

    def test_entity_vocabulary_is_closed(self):
        # CONTRACT: no getter, setter, modify, read, subscript or other accessor entity exists (I4).
        self.assertTrue(issubclass(ImportEntity, str))
        self.assertEqual({member.value for member in ImportEntity}, ENTITY_VALUES)
        self.assertEqual({member.name for member in ImportEntity},
                         {'FUNCTION', 'METADATA_ACCESSOR', 'INITIALIZER', 'ALLOCATING_INITIALIZER'})

    def test_reasons_exist_unchanged(self):
        values = {reason.value for reason in UnsupportedReason}
        self.assertLessEqual(CONTRACT_REASONS, values)

    def test_declaration_dataclass_shape(self):
        self.assertEqual([field.name for field in fields(ImportedDeclaration)],
                         ['symbol', 'module', 'context', 'entity', 'name', 'parameter_labels', 'parameter_types',
                          'result_type', 'throws', 'syntax_model'])
        identity = self.assertAdmit('_$ss6HasherV8_combineyySuF', False)
        self.assertFalse(hasattr(identity, '__dict__'))          # slots
        with self.assertRaises(FrozenInstanceError):
            identity.throws = True
        with self.assertRaises(FrozenInstanceError):
            identity.symbol = 'x'
        self.assertIsInstance(identity.context, tuple)
        self.assertIsInstance(identity.parameter_labels, tuple)
        self.assertIsInstance(identity.parameter_types, tuple)
        for context in identity.context:
            self.assertIsInstance(context, SwiftContext)
        for value in identity.parameter_types:
            self.assertIsInstance(value, SwiftType)

    def test_result_type_reuses_old_module(self):
        result = parse('$s1M1fyyF')
        self.assertIs(type(result), BroadDeclarationResult)
        self.assertIs(type(result.unsupported_reason), type(None))
        declined = parse('$s1M1fyyKYaF')
        self.assertIs(type(declined.unsupported_reason), UnsupportedReason)

    def test_asdict_and_report_json(self):
        for symbol in ('_$s10Foundation11JSONDecoderCACycfc', '_$s10Foundation3URLVMa',
                       '_$ss5print_9separator10terminatoryypd_S2StF',
                       '_$s10Foundation4DataV10contentsOf7optionsAcA3URLVh_So20NSDataReadingOptionsVtKcfC'):
            with self.subTest(symbol=symbol):
                identity = parse(symbol).identity
                plain = json.loads(dumps(asdict(identity)))
                self.assertEqual(set(plain), {field.name for field in fields(ImportedDeclaration)})
                self.assertIs(type(plain['entity']), str)
                self.assertIn(plain['entity'], ENTITY_VALUES)
                self.assertEqual(plain['entity'], identity.entity.value)
                self.assertIs(type(plain['throws']), bool)
                self.assertEqual(plain['symbol'], symbol)
                self.assertEqual(plain['syntax_model'], MODEL)
                self.assertLessEqual(value_depth(plain), MAX_IDENTITY_VALUE_DEPTH)
                self.assertEqual(json.loads(json.dumps(asdict(identity))), plain)


# The native report reader allows 32 nesting levels and an identity object sits at
# level 5 of a broad-imports report, so 27 levels remain below the identity.
NATIVE_NESTING_LIMIT = 32
MAX_IDENTITY_VALUE_DEPTH = 27


def value_depth(value):
    """Levels below `value` of its deepest member or element, scalars included (the native reader's count)."""
    if isinstance(value, dict):
        return max((1 + value_depth(item) for item in value.values()), default=0)
    if isinstance(value, list):
        return max((1 + value_depth(item) for item in value), default=0)
    return 0


def proven_keys(value, path=()):
    if isinstance(value, dict):
        for key, item in value.items():
            if key.endswith('_proven'):
                yield path + (key,), item
            yield from proven_keys(item, path + (key,))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            yield from proven_keys(item, path + (index,))


class FixtureSymbolTests(ImportDeclarationCase):
    """CONTRACT required outcomes: 10 admit non-throwing, 1 admit throwing, 8 decline."""

    def test_census(self):
        self.assertEqual(len(FIXTURE_19), 19)
        self.assertEqual(len(set(FIXTURE_SYMBOLS)), 19)
        self.assertEqual(len(SKIPPABLE_19), 10)
        self.assertEqual(len(ADMITTED_19), 11)
        admitted = [symbol for symbol in FIXTURE_SYMBOLS if parse(symbol).supported]
        self.assertEqual(admitted, [item[0] for item in ADMITTED_19])
        skippable = [symbol for symbol in FIXTURE_SYMBOLS
                     if parse(symbol).supported and not parse(symbol).identity.throws]
        self.assertEqual(skippable, list(SKIPPABLE_19))

    def test_declined_symbols(self):
        for item in FIXTURE_19:
            if item[1] is None:
                with self.subTest(symbol=item[0]):
                    self.assertDecline(item[0])

    def test_getters_decline(self):
        # I4: the four getter symbols stay rows; their effects are invisible in the mangled name.
        for symbol in GETTERS_19:
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_admitted_fields(self):
        for symbol, throws, entity, module, name, labels, count, context in ADMITTED_19:
            with self.subTest(symbol=symbol):
                identity = self.assertAdmit(symbol, throws)
                self.assertIs(identity.entity, ImportEntity(entity))
                self.assertEqual(identity.module, module)
                self.assertEqual(identity.name, name)
                self.assertEqual(identity.parameter_labels, labels)
                self.assertEqual(len(identity.parameter_types), count)
                self.assertEqual(len(identity.context), len(context))
                for actual, (nominal, kind) in zip(identity.context, context):
                    if kind == 'extension':
                        # The extension entry's representation is not fixed beyond "not a nominal".
                        self.assertNotIn(actual.kind, NOMINAL_KINDS)
                        self.assertIn(nominal, actual.name + ' ' + actual.kind)
                    else:
                        self.assertTrue(actual.name.endswith(nominal), actual)
                        self.assertEqual(actual.kind, kind)
                if entity == 'metadata_accessor':
                    self.assertIsNone(identity.result_type)
                else:
                    self.assertIsInstance(identity.result_type, SwiftType)
                if entity.endswith('initializer'):
                    self.assertIn(context[-1][0], identity.result_type.name)

    def test_result_and_parameter_names(self):
        # PRODUCTIONS 8.12, 8.15, 8.16.
        compare = parse(FIXTURE_19[11][0]).identity
        self.assertIn('Bool', compare.result_type.name)
        self.assertIn('_StringGuts', compare.parameter_types[0].name)
        self.assertIn('_StringGuts', compare.parameter_types[1].name)
        self.assertIn('_StringComparisonResult', compare.parameter_types[2].name)
        self.assertIn('UInt', parse('_$ss6HasherV8_combineyySuF').identity.parameter_types[0].name)
        self.assertIn('Int', parse('_$ss6HasherV9_finalizeSiyF').identity.result_type.name)
        self.assertIn('Int', parse('_$ss6HasherV5_seedABSi_tcfC').identity.parameter_types[0].name)
        self.assertIn('String', parse(FIXTURE_19[3][0]).identity.parameter_types[0].name)

    def test_raw_symbol_and_one_underscore(self):
        # I6: exactly one leading underscore is stripped; identity.symbol stays raw.
        for item in ADMITTED_19:
            with self.subTest(symbol=item[0]):
                self.assertAdmit(item[0][1:], item[1])
                self.assertDecline('_' + item[0])


class OracleTableTests(ImportDeclarationCase):
    """Oracle corpus (symbols.tsv): verdicts from the grammar, truth from source.swift."""

    @classmethod
    def setUpClass(cls):
        cls.rows = read_table('symbols.tsv')

    def test_table_shape(self):
        self.assertEqual(len(self.rows), 494)
        self.assertEqual(list(self.rows[0]), ['mangled', 'demangled', 'entity_shape', 'source_truth_throws',
                                              'source_truth_async', 'expected_decision', 'expected_reason',
                                              'expected_throws'])
        self.assertEqual(len({row['mangled'] for row in self.rows}), 494)
        counts = {}
        for row in self.rows:
            key = (row['expected_decision'], row['expected_throws'])
            counts[key] = counts.get(key, 0) + 1
            self.assertIn(row['source_truth_throws'], {'yes', 'no', 'rethrows'})
            self.assertIn(row['source_truth_async'], {'yes', 'no'})
            if row['expected_decision'] == 'decline':
                self.assertIn(row['expected_reason'], CONTRACT_REASONS)
        self.assertEqual(counts, {('admit', 'false'): 101, ('admit', 'true'): 39, ('decline', ''): 354})
        source = (FIXTURE / 'source.swift').read_text(encoding='utf-8')
        self.assertIn('public func freeKeyKnockQ370()', source)

    def test_table_is_self_consistent(self):
        # The table's own expectations satisfy the differential bar (guards the fixture itself).
        for row in self.rows:
            if row['expected_decision'] == 'admit' and row['expected_throws'] == 'false':
                self.assertEqual((row['source_truth_throws'], row['source_truth_async']), ('no', 'no'), row)
                self.assertIsNone(EFFECT_WORD.search(row['demangled']), row)

    def test_every_row_verdict(self):
        for row in self.rows:
            with self.subTest(symbol=row['mangled']):
                if row['expected_decision'] == 'admit':
                    identity = self.assertAdmit(row['mangled'], table_throws(row))
                    self.assertEqual(identity.module, 'OracleLib')
                    self.assertLessEqual(value_depth(json.loads(json.dumps(asdict(identity)))), MAX_IDENTITY_VALUE_DEPTH)
                else:
                    self.assertDecline(row['mangled'])

    def test_differential_bar(self):
        # I7: admitted with throws == False implies source truth throws == no and async == no. Zero exceptions.
        violations = []
        for row in self.rows:
            result = parse(row['mangled'])
            if result.supported and result.identity.throws is False:
                if (row['source_truth_throws'], row['source_truth_async']) != ('no', 'no'):
                    violations.append(row['mangled'])
            if result.supported and result.identity.throws is True:
                self.assertNotEqual(row['source_truth_throws'], 'no', row['mangled'])
        self.assertEqual(violations, [])

    def test_rethrows_never_skippable(self):
        # I2/H2: rethrows mangles as throws, so it is either declined or admitted with throws == True.
        rows = [row for row in self.rows if row['source_truth_throws'] == 'rethrows']
        self.assertGreater(len(rows), 0)
        for row in rows:
            with self.subTest(symbol=row['mangled']):
                self.assertSkippable(row['mangled'])

    def test_accessors_decline(self):
        # I4/H1: every accessor-family symbol declines, whatever its source effects.
        rows = [row for row in self.rows if ACCESSOR_SHAPE.search(row['entity_shape'])]
        self.assertGreaterEqual(len(rows), 100)
        truths = {(row['source_truth_throws'], row['source_truth_async']) for row in rows}
        self.assertIn(('yes', 'yes'), truths)
        self.assertIn(('no', 'no'), truths)
        for row in rows:
            with self.subTest(symbol=row['mangled']):
                self.assertDecline(row['mangled'])

    def test_async_rows_never_admitted(self):
        # I5: no symbol of an async declaration is admitted at all.
        for row in self.rows:
            if row['source_truth_async'] == 'yes':
                with self.subTest(symbol=row['mangled']):
                    self.assertDecline(row['mangled'])

    def test_naive_k_scan_counterexamples(self):
        # H3: K inside identifiers is identifier text (admitted, throws False); throwing rows without a
        # visible entity-level K (accessors) decline. A K-in-tail scan gets both sets wrong.
        k_in_name = [row for row in self.rows if row['expected_decision'] == 'admit'
                     and row['expected_throws'] == 'false' and 'K' in row['mangled'][2:]]
        self.assertEqual({row['mangled'] for row in k_in_name},
                         {'$s9OracleLib12freeYaKFQ371yyF', '$s9OracleLib16freeKeyKnockQ370yyF'})
        for row in k_in_name:
            self.assertAdmit(row['mangled'], False)
        self.assertAdmit('$s1M4KKKKyyF', False)
        self.assertAdmit('$s1M4KKKKyyKF', True)
        hidden = [row for row in self.rows if row['source_truth_throws'] != 'no' and 'K' not in row['mangled'][12:]]
        self.assertGreaterEqual(len(hidden), 20)
        for row in hidden:
            with self.subTest(symbol=row['mangled']):
                self.assertDecline(row['mangled'])
        closure_k = [row for row in self.rows if 'KXE' in row['mangled'] and row['source_truth_throws'] == 'no']
        self.assertTrue(closure_k)
        for row in closure_k:
            with self.subTest(symbol=row['mangled']):
                self.assertDecline(row['mangled'])

    def test_never_forms(self):
        # I5: throws(Never) and Never-returning functions mangle plain and are admitted as non-throwing.
        self.assertAdmit('$s9OracleLib20typedThrowsNeverQ251yyF', False)
        self.assertAdmit('$s9OracleLib13freeNeverQ153s0D0OyF', False)
        self.assertAdmit('$s1M3fooyys5NeverOF', False)


class ProbeTableTests(ImportDeclarationCase):
    """Grammar probes for packets A to E (probes.tsv)."""

    @classmethod
    def setUpClass(cls):
        cls.rows = read_table('probes.tsv')

    def test_table_shape(self):
        self.assertEqual(len(self.rows), 675)
        packets = {row['packet'] for row in self.rows}
        self.assertLessEqual({'A-module', 'A-subst', 'A-subst-type', 'A-subst-proto', 'A-subst-Sc', 'B-getter',
                              'B-spec', 'C-init', 'D-free', 'E-meth', 'COMPILED', 'FIX'}, packets)
        for packet in packets:
            decisions = {row['expected_decision'] for row in self.rows if row['packet'] == packet}
            if packet not in ('B-getter', 'B-spec', 'A-subst-proto', 'A-subst-Sc'):
                self.assertEqual(decisions, {'admit', 'decline'}, packet)   # positive and refusal evidence
            else:
                self.assertEqual(decisions, {'decline'}, packet)   # refusal-only packets (getters, protocols)

    def test_every_probe_verdict(self):
        for row in self.rows:
            with self.subTest(packet=row['packet'], symbol=row['input']):
                if row['expected_decision'] == 'admit':
                    identity = self.assertAdmit(row['input'], table_throws(row))
                    self.assertLessEqual(value_depth(json.loads(json.dumps(asdict(identity)))), MAX_IDENTITY_VALUE_DEPTH)
                else:
                    self.assertDecline(row['input'])

    def test_probe_differential_against_demangler(self):
        # I7 over the probe set: an admitted non-throwing string never demangles with an effect word.
        violations = []
        for row in self.rows:
            result = parse(row['input'])
            if result.supported and not result.identity.throws and row['input'] not in SILGEN_RESIDUAL:
                if EFFECT_WORD.search(row['demangled']):
                    violations.append(row['input'])
            if result.supported and result.identity.throws:
                self.assertRegex(row['demangled'], THROWS_WORD)
        self.assertEqual(violations, [])

    def test_silgen_residual_documented(self):
        # CONTRACT residual: these plain-looking symbols are admitted; no grammar can see their effects.
        for symbol in SILGEN_RESIDUAL:
            self.assertAdmit(symbol, False)


class PacketTests(ImportDeclarationCase):
    """Hand-picked positive and refusal cases per packet (PRODUCTIONS sections 2 to 6)."""

    def test_word_origin_cannot_become_module(self):
        for symbol in ('$sSS10FoundationE4dataSSSg0B04DataV_tcfC',
                       '$s3Foo3BarV0aB0E1myyF',
                       '$s3Foo0A0VABE1myyF', '$s3Foo0A0yyAB1BVF'):
            # In the last two strings, AB reuses word-origin identifier sub B
            # as an extension module or as a parameter nominal's module.
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol, 'word_substitution')
        # Fixture 8.12 uses a word run as the nominal name _StringComparisonResult.
        identity = self.assertAdmit(FIXTURE_19[11][0], False)
        self.assertEqual(identity.parameter_types[2].name, 'Swift._StringComparisonResult')

    def test_context_and_type_restrictions(self):
        cases = (
            ('$s1M1fySiXfF', 'closure_type'),
            ('$s1M1fSihyF', 'invalid_grammar'),  # h modifies parameters, never the result.
            ('$s1M1fyyhF', 'invalid_grammar'),  # Void is not a shared parameter operand.
            ('$s1M1fyydF', 'invalid_grammar'),  # A variadic needs a non-void tuple element.
            ('$s1M1fyyTyF', 'thunk_or_specialization'),
            ('$s1M1AV1NE1BV1OE1fyyF', 'unsupported_production'),
            ('$s1M001fyyF', 'unicode_identifier'),
            ('$s1M1fySgyF', 'invalid_grammar'),  # Optional requires a non-void type.
        )
        for symbol, reason in cases:
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol, reason)
        self.assertEqual(self.assertAdmit('$sSo1AV1fyyF', False).module, '__C')

    def test_packet_a_frame(self):
        self.assertAdmit('$s1M1AVMa', False)
        self.assertAdmit('$s1M1AOMa', False)
        self.assertAdmit('$s1M1ACMa', False)
        identity = self.assertAdmit('$s1M1AV1BV1fyyF', False)
        self.assertEqual([context.kind for context in identity.context], ['struct', 'struct'])
        self.assertEqual(identity.module, 'M')
        self.assertAdmit('$s1M1fyySbF', False)
        for symbol in ('$s1M1fyySaF', '$s1M1AVMn', '$s1M1AVMaMa', '$s1M1APMa', '$s00abc1fyyF', '$s1M004abcd1fyyF',
                       '$s1M01fyyF', '$S1M1fyyF', '_T01M1fyyF', '$e1M1fyyF', '$s', '$s1M'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_packet_b_getters(self):
        for symbol in ('$s1M1AV1xSivg', '$s1M1AV1xSivgZ', '$s1M1AV1xSivs', '$s1M1AV1xSivM', '$s1M1AVyS2icig',
                       '$s1M1xSivg'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_packet_c_initializers(self):
        identity = self.assertAdmit('$s1M1AVACycfc', False)
        self.assertIs(identity.entity, ImportEntity.INITIALIZER)
        self.assertEqual(identity.name, '')
        identity = self.assertAdmit('$s1M1AVACyKcfC', True)
        self.assertIs(identity.entity, ImportEntity.ALLOCATING_INITIALIZER)
        for symbol in ('$s1M1AVACycfCx', '$s1M1AVACycfcfc', '$s1M1AVACyc', '$s1M1AVACycf', '$s1M1AVACyYacfC',
                       '$s1M1AVACyKKcfC'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_packet_d_free_functions(self):
        self.assertAdmit('$s1M4freeyyF', False)
        self.assertAdmit('$s1M4freeyyKF', True)
        self.assertAdmit('$s1M1fypyF', False)
        identity = self.assertAdmit('$s1M1fyySi_SitF', False)
        self.assertEqual(identity.parameter_labels, (None, None))
        self.assertIs(identity.entity, ImportEntity.FUNCTION)
        for symbol in ('$s1M1fyyFZ', '$s1M3fooyyyycF', '$s1M3fooyyyyKcF', '$s1M3fooyyFTj', '$s1M3fooyyFTq',
                       '$s1M1fyypyF'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_packet_e_struct_methods(self):
        self.assertEqual(len(self.assertAdmit('$s1M1AV1fyyF', False).context), 1)
        self.assertAdmit('$s1M1AV1fyyFZ', False)
        self.assertAdmit('$s1M1AV1fyyKFZ', True)
        self.assertAdmit('$s1M1AV1fyyKF', True)
        for symbol in ('$s1M1AV1fyyFZZ', '$s1M1AV1fyyYaFZ', '$s1M1AV1fyyKFTj', '$s1M1AP1fyyF'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)


class InvariantTests(ImportDeclarationCase):
    def test_i1_prefixes_decline(self):
        for item in ADMITTED_19:
            symbol = item[0]
            for end in range(len(symbol)):
                with self.subTest(prefix=symbol[:end]):
                    self.assertFalse(parse(symbol[:end]).supported)

    def test_i1_trailing_garbage_declines(self):
        suffixes = ('0', '_', 'x', '$', ' ', '\x00', 'TA', 'Tj', 'Tq', 'K', 'Ma', 'y', 'F', 'Sg', 'cfC', '\n')
        for item in ADMITTED_19:
            for suffix in suffixes:
                with self.subTest(symbol=item[0], suffix=suffix):
                    self.assertDecline(item[0] + suffix)
        self.assertDecline('$s1M3fooyyF' + 'x' * 100)

    def test_i2_throws_position(self):
        self.assertDecline('$s1M1fKyySbF', 'invalid_grammar')
        self.assertAdmit('$s1M3fooyyF', False)
        self.assertAdmit('$s1M3fooyyKF', True)
        self.assertAdmit('$s1M1AVACyKcfC', True)
        self.assertAdmit('$s1M1AV1fyyKFZ', True)
        self.assertAdmit('$s1M4KKKKyyF', False)                 # K in identifier text
        for symbol in ('$s1M3fooyyKKF', '$s1M3fooyyKYaF', '$s1M3fooyyyyKcF', '$s1M3fooyyyyKcKF'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_i5_effects(self):
        self.assertDecline('$s1M3fooyyYaF', 'async_context')
        self.assertDecline('$s1M3fooyyYaKF', 'async_context')
        self.assertDecline('$s1M3fooyys5NeverOYKF', 'typed_throws')
        for symbol in ('$s1M3fooyyYbF', '$s1M3fooyyYiF', '$s1M1AVACyYacfC'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_i3_unknown_x_production(self):
        self.assertDecline('$s1M1fXzyySbF', 'unsupported_production')

    def test_i6_repeat_counts(self):
        self.assertDecline('$s1M1fyS02iF', 'invalid_grammar')
        self.assertDecline('$s1M1fyyS65i_F', 'resource_limit')
        identity = self.assertAdmit('$s1M1fyySi_S63itF', False)
        self.assertEqual(len(identity.parameter_types), 64)
        self.assertAdmit('$s1M1fyySi_S2itF', False)
        self.assertDecline('$s1M1fyySi_S64itF', 'resource_limit')
        for symbol in ('$s1M1fyySi_S0itF', '$s1M1fyySi_S1itF', '$s1M1fyySi_S01itF'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_i6_identifiers(self):
        # I6 caps the length field at six digits even with larger byte limits.
        self.assertDecline('$s1M' + '1000000' + 'A' * 1000000 + 'yyF', 'resource_limit',
                           limits=ParseLimits(max_symbol_length=2000000, max_identifier_length=2000000))
        self.assertAdmit('$s1M256' + 'a' * 256 + 'yyF', False)
        self.assertDecline('$s1M257' + 'a' * 257 + 'yyF', 'resource_limit')
        self.assertDecline('$s1M1234567fyyF')
        for bad in ('.', ' ', '-', 'é', '\x01'):
            with self.subTest(character=bad):
                self.assertDecline('$s1M3a' + bad + 'byyF')
        self.assertAdmit('$s1M3a$byyF', False)
        self.assertDecline('$s1M3$abyyF')

    def test_i6_custom_limits(self):
        cases = (
            (ParseLimits(max_identifier_length=2), '$s1M2foyyF', '$s1M3fooyyF'),
            (ParseLimits(max_context_depth=1), '$s1M1AV1fyyF', '$s1M1AV1BV1fyyF'),
            (ParseLimits(max_parameters=3), '$s1M1fyySi_S2itF', '$s1M1fyySi_S3itF'),
            (ParseLimits(max_symbol_length=12), '$s1M3fooyyF', '$s1M1AVACycfc'),
            (ParseLimits(max_substitutions=4),
             '$s1M3fooyyF', '_$s10Foundation4DataV10contentsOf7optionsAcA3URLVh_So20NSDataReadingOptionsVtKcfC'),
            (ParseLimits(max_type_depth=4), '$s1M1fyySiF', '$s1M1fyy' + 'Say' * 8 + 'Si' + 'G' * 8 + 'F'),
        )
        for limits, within, beyond in cases:
            with self.subTest(limits=limits):
                self.assertAdmit(within, False, limits=limits)
                self.assertDecline(beyond, 'resource_limit', limits=limits)

    def test_i6_default_depth_limits(self):
        self.assertAdmit('$s1M1fyy' + 'Say' * 8 + 'Si' + 'G' * 8 + 'F', False)
        self.assertDecline('$s1M1fyy' + 'Say' * 40 + 'Si' + 'G' * 40 + 'F', 'resource_limit')
        self.assertDecline('$s1M' + '1AV' * 30 + '1fyyF', 'resource_limit')
        self.assertAdmit('$s1M' + '1AV' * 4 + '1fyyF', False)

    def test_serialised_depth_boundaries(self):
        shapes = (
            (lambda n: '$s1M1fyySi' + 'Sg' * n + 'F', False, 27),
            (lambda n: '$s1M1fyy' + 'Say' * n + 'Si' + 'G' * n + 'F', False, 27),
            (lambda n: '$s1M1fSi' + 'Sg' * n + 'yF', False, 26),
            (lambda n: '$s1M1fyySi' + 'Sg' * n + 'KF', True, 27),
        )
        for symbol_for_depth, throws, expected_depth in shapes:
            with self.subTest(symbol=symbol_for_depth(12)):
                identity = self.assertAdmit(symbol_for_depth(12), throws)
                depth = value_depth(json.loads(json.dumps(asdict(identity))))
                self.assertEqual(depth, expected_depth)
                self.assertLessEqual(depth, MAX_IDENTITY_VALUE_DEPTH)
                self.assertDecline(symbol_for_depth(13), 'resource_limit')

    def test_malformed_input(self):
        for symbol in ('', '_', '__', '$', '$s', '_$s', '__$s1M1fyyF', '$s1', '$s1M', '$s1M1', '$s1M1f', '$s1M1fy',
                       '$s1M1fyy', '\x00', '$s1M1fyyF\x00', '☃', '$s1M1féyyF', '$s1M\ud800yyF',
                       ' $s1M1fyyF', '$s1M1fyyF ', '$s1M9fyyF', '$s1M999999fyyF', '$s1M99999999999999999999fyyF'):
            with self.subTest(symbol=symbol):
                self.assertDecline(symbol)

    def test_huge_and_deep_input_is_bounded(self):
        self.assertDecline('$s1M3fooyyF' + 'x' * 5000, 'resource_limit')
        self.assertDecline('$s' + 'x' * 100000, 'resource_limit')
        roomy = ParseLimits(max_symbol_length=1 << 20)
        deep = (
            '$s1M1fyy' + 'Say' * 3000 + 'Si' + 'G' * 3000 + 'F',
            '$s1M1fyySi' + 'Sg' * 3000 + 'F',
            '$s1M' + '1AV' * 3000 + '1fyyF',
            '$s1M1fyy' + 'Si_' * 3000 + 'tF',
            '$s1M1fyy' + 'y' * 3000 + 'F',
        )
        for symbol in deep:
            with self.subTest(symbol=symbol[:24], length=len(symbol)):
                self.assertDecline(symbol, limits=roomy)

    def test_non_string_input_declines(self):
        for value in (None, b'$s1M1fyyF', 7, ['$s1M1fyyF']):
            with self.subTest(value=value):
                result = parse_import_declaration(value)
                self.assertFalse(result.supported)
                self.assertIsNone(result.identity)
                self.assertIsInstance(result.unsupported_reason, UnsupportedReason)


class IsolationTests(ImportDeclarationCase):
    """I8: the old entry point and the non-import call path are untouched."""

    def test_old_parser_results_recorded(self):
        rows = read_table('old-parser.tsv')
        self.assertEqual(len(rows), 494 + 19)
        self.assertEqual([row['mangled'] for row in rows[494:]], list(FIXTURE_SYMBOLS))
        self.assertEqual(sum(row['supported'] == 'true' for row in rows), 56)
        for row in rows:
            with self.subTest(symbol=row['mangled']):
                result = parse_broad_declaration(row['mangled'])
                self.assertEqual(('true' if result.supported else 'false',
                                  '' if result.unsupported_reason is None else result.unsupported_reason.value,
                                  str(result.offset), result.detail),
                                 (row['supported'], row['reason'], row['offset'], row['detail']))
                identity = '' if result.identity is None else json.dumps(asdict(result.identity), sort_keys=True,
                                                                         separators=(',', ':'))
                self.assertEqual(identity, row['identity_json'])

    def test_fixture_symbols_declined_by_old_parser(self):
        # census at the base commit: the old parser supports none of the 19.
        for symbol in FIXTURE_SYMBOLS:
            with self.subTest(symbol=symbol):
                self.assertFalse(parse_broad_declaration(symbol).supported)

    def test_old_model_unchanged(self):
        identity = parse_broad_declaration('$s4Test3fooyS2iF').identity
        self.assertEqual(identity.syntax_model, OLD_MODEL)
        self.assertIsNot(parse_broad_declaration, parse_import_declaration)
        self.assertNotIsInstance(identity, ImportedDeclaration)

    def test_abi_path_keeps_old_parser(self):
        source = inspect.getsource(swift_broad_flow._abi)
        self.assertIn('parse_broad_declaration(', source)
        self.assertNotIn('parse_import_declaration', source)
        flow_source = inspect.getsource(swift_broad_flow)
        # Two callers, both for imported callees: the stub path and the GOT path.
        self.assertEqual(flow_source.count('parse_import_declaration('), 2)
        self.assertIn('parse_import_declaration(', inspect.getsource(swift_broad_flow._got_site))


def image_of(data):
    return parse_macho(data, limits=EXTENDED_BROAD_LIMITS)


def flow_report(*symbols):
    calls = tuple(('bl', ('stub', index)) for index in range(len(symbols)))
    data, _ = build_stub_image(callers=(calls + (RET,),), imports=tuple(Import(symbol, 2) for symbol in symbols))
    report = recover_swift_broad_flow(image_of(data), None, profile=PROFILE)
    return json.loads(dumps(report))


class IntegrationTests(ImportDeclarationCase):
    """The one integration point: broad-imports-v1 declaration cache (CONTRACT)."""

    def assertNativeStable(self, declaration, symbol):
        self.assertEqual(set(declaration), {'status', 'identity', 'reason'})
        if declaration['status'] == 'syntax_admitted':
            self.assertIsNotNone(declaration['identity'])
            self.assertIsNone(declaration['reason'])
            identity = declaration['identity']
            self.assertEqual(identity['symbol'], symbol)
            self.assertIs(type(identity['throws']), bool)
            self.assertEqual(identity['syntax_model'], MODEL)
            self.assertIs(type(identity['entity']), str)
            self.assertLessEqual(value_depth(identity), MAX_IDENTITY_VALUE_DEPTH)
        else:
            self.assertEqual(declaration['status'], 'syntax_unresolved')
            self.assertIsNone(declaration['identity'])
            self.assertIs(type(declaration['reason']), str)
            self.assertIn(declaration['reason'], CONTRACT_REASONS)
        for path, value in proven_keys(declaration):
            self.assertIs(value, False, path)

    def test_non_throwing_import_is_skipped(self):
        for symbol in SKIPPABLE_19:
            with self.subTest(symbol=symbol):
                report = flow_report(symbol)
                counts = report['import_stub_counts']
                self.assertEqual((counts['attributed_stubs'], counts['non_throwing_swift_import_calls'],
                                  counts['selected_import_calls']), (1, 1, 0))
                self.assertEqual(report['calls'], [])

    def test_throwing_admitted_import_stays_row(self):
        symbol = '_$s10Foundation4DataV10contentsOf7optionsAcA3URLVh_So20NSDataReadingOptionsVtKcfC'
        report = flow_report(symbol)
        counts = report['import_stub_counts']
        self.assertEqual((counts['non_throwing_swift_import_calls'], counts['selected_import_calls']), (0, 1))
        self.assertEqual(len(report['calls']), 1)
        admission = report['calls'][0]['admission']
        self.assertEqual((admission['status'], admission['reason']), ('unresolved', 'imported_callee_abi_unqualified'))
        declaration = admission['declaration']
        self.assertEqual(declaration['status'], 'syntax_admitted')
        self.assertIs(declaration['identity']['throws'], True)
        self.assertEqual(declaration['identity']['entity'], 'allocating_initializer')
        self.assertNativeStable(declaration, symbol)

    def test_deepest_admitted_identity_keeps_report_inside_native_nesting_limit(self):
        deepest = '_$s1M1fyySi' + 'Sg' * 12 + 'KF'
        deeper = '_$s1M1fyySi' + 'Sg' * 13 + 'KF'
        report = flow_report(deepest, deeper)
        rows = {row['admission']['symbol']: row['admission']['declaration'] for row in report['calls']}
        self.assertEqual(set(rows), {deepest, deeper})
        self.assertEqual(rows[deepest]['status'], 'syntax_admitted')
        self.assertIs(rows[deepest]['identity']['throws'], True)
        self.assertEqual(value_depth(rows[deepest]['identity']), MAX_IDENTITY_VALUE_DEPTH)
        self.assertEqual((rows[deeper]['status'], rows[deeper]['reason']), ('syntax_unresolved', 'resource_limit'))
        # Counted as the native reader counts (report object at level 0), the whole report is at the limit.
        self.assertEqual(value_depth(report), NATIVE_NESTING_LIMIT)

    def test_declined_imports_stay_rows(self):
        for item in FIXTURE_19:
            if item[1] is not None:
                continue
            with self.subTest(symbol=item[0]):
                report = flow_report(item[0])
                self.assertEqual(report['import_stub_counts']['non_throwing_swift_import_calls'], 0)
                self.assertEqual(len(report['calls']), 1)
                declaration = report['calls'][0]['admission']['declaration']
                self.assertEqual(declaration['status'], 'syntax_unresolved')
                self.assertNativeStable(declaration, item[0])

    def test_all_19_in_one_image(self):
        report = flow_report(*FIXTURE_SYMBOLS)
        counts = report['import_stub_counts']
        self.assertEqual((counts['attributed_stubs'], counts['non_throwing_swift_import_calls'],
                          counts['selected_import_calls']), (19, 10, 9))
        rows = {row['admission']['symbol']: row['admission']['declaration'] for row in report['calls']}
        self.assertEqual(set(rows), set(FIXTURE_SYMBOLS) - set(SKIPPABLE_19))
        for symbol, declaration in rows.items():
            with self.subTest(symbol=symbol):
                self.assertNativeStable(declaration, symbol)

    def test_abi_profiles_ignore_new_parser(self):
        # broad-extended-v1 never consults the import declaration path: no import counts are produced.
        data, _ = build_stub_image(imports=(Import('_$ss6HasherV8_combineyySuF', 2),))
        report = json.loads(dumps(recover_swift_broad_flow(image_of(data), None, profile='broad-extended-v1')))
        self.assertNotIn('import_stub_counts', report)
        self.assertNotIn(MODEL, json.dumps(report))


if __name__ == '__main__':
    unittest.main()
