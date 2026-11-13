"""Group D tests for profile broad-extended-v4: isolation, registry, generator, CLI, text and documents (packet P4).

Written from the design contract and its test list (tests D1 to D9); the wiring that these tests exercise was not read.
What is read here is the public surface only: the registry source, the generated files, the generator's exit status and
message prefix, the engine tables, the parser's choices, the text renderer's refusal code and the published documents.

Where a test needs a literal that the contract fixes (the seven earlier registry pairs, the licence classes, the stale
sentences of the roadmap) the literal is copied into this file. Strings that the publication rules reject (the maintainer's
name, the vendor names, attribution trailers) are built by concatenation so that this file does not contain them.
"""
import contextlib
import copy
import io
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from collections import Counter
from pathlib import Path
from unittest import mock
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))

import indirect_v3_image_helpers as helpers  # noqa: E402
import test_swift_broad_extended_v3 as v3tests  # noqa: E402
from airs import analysis_models  # noqa: E402
from airs import swift_broad_accounting as accounting  # noqa: E402
from airs import swift_import_effect_admission as effect  # noqa: E402
from airs import swift_value_witness_admission as witness_module  # noqa: E402
from airs.cli import _parser, main  # noqa: E402
from airs.macho import parse_macho  # noqa: E402
from airs.report import dumps  # noqa: E402
from airs.swift_broad_flow import (CALLER_FACT_PROFILES, PROFILE_LIMITS, PROFILE_MODELS,  # noqa: E402
                                   recover_swift_broad_flow)
from airs.swift_broad_text import render_swift_broad_text  # noqa: E402
from airs.types import InputError  # noqa: E402
from stub_image_helpers import RET, Import, build_stub_image  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / 'scripts' / 'generate-model-registries.py'
REGISTRY = ROOT / 'registry' / 'models.json'
OUTPUTS = ('src/airs/analysis_models.py', 'native/Sources/AIRSCore/AnalysisModels.swift')
DOCS = ROOT / 'docs'
FIXTURE = ROOT / 'fixtures' / 'swift-error-flow' / 'broad-imports' / 'OwnedImports.macho'
EXPECTED = json.loads((ROOT / 'fixtures' / 'swift-error-flow' / 'broad-imports' / 'expected-v4.json').read_text())

PROFILE = 'broad-extended-v4'
MODEL = 'swift-broad-error-flow-extended-v4'
EFFECT_MODEL = 'swift-import-effect-admission-v1'
GRAMMAR_MODEL = 'swift-declaration-syntax-v2'
GRAMMAR_PIN = 'swift-6.4.2-RELEASE'
EARLIER = ('broad-v1', 'broad-large-v1', 'broad-extended-v1', 'broad-imports-v1', 'broad-imports-got-v1',
           'broad-extended-v2', 'broad-extended-v3')
ALL_PROFILES = EARLIER + (PROFILE,)
IMPORT_PROFILES = ('broad-imports-v1', 'broad-imports-got-v1', 'broad-extended-v2', 'broad-extended-v3')
REQUIRED = ['--include-outcome-witnesses', '--include-error-regions', '--validate-region-entries',
            '--include-structured-presentation']
LICENCE_CLASSES = ('no_error_exit', 'declared_error_exit', 'refused_unsupported_effect', 'none')
ROW_REASONS = ('declaration_caller_disagreement', 'imported_callee_outcome_unmodeled',
               'imported_callee_effect_unsupported', 'imported_callee_abi_unqualified')

# The pairs of the registry at main a960976 (model, profile, native_admitted); copied, not read from the registry.
BASELINE_PAIRS = (
    ('swift-broad-error-flow-v1', 'broad-v1', True),
    ('swift-broad-error-flow-large-v1', 'broad-large-v1', True),
    ('swift-broad-error-flow-extended-v1', 'broad-extended-v1', True),
    ('swift-broad-error-flow-imports-v1', 'broad-imports-v1', True),
    ('swift-broad-error-flow-imports-got-v1', 'broad-imports-got-v1', False),
    ('swift-broad-error-flow-extended-v2', 'broad-extended-v2', True),
    ('swift-broad-error-flow-extended-v3', 'broad-extended-v3', True),
)
# The native decoder admits the v4 pair, so its registry flag is true and the generated native file lists it.
V4_NATIVE_ADMITTED = True

# Build the strings the publication rules reject, so that this file does not spell them out.
MAINTAINER = re.compile(r'\bJe' + r'ff\b', re.I)
VENDOR = re.compile(r'\b(?:Cla' + r'ude|Anthro' + r'pic)\b', re.I)
TRAILERS = (re.compile(r'Co-' + r'Authored-By', re.I), re.compile(r'Generated ' + r'with', re.I))


# --- helpers -------------------------------------------------------------------------------------------------
def airs_modules(name):
    return [module for key, module in sorted(sys.modules.items())
            if key.startswith('airs.') and module is not None and hasattr(module, name)]


@contextlib.contextmanager
def forced(**constants):
    with contextlib.ExitStack() as stack:
        for name, value in constants.items():
            targets = airs_modules(name)
            assert targets, 'no airs module has the name %s' % name
            for module in targets:
                stack.enter_context(mock.patch.object(module, name, value))
        yield


def flow(data, profile=PROFILE):
    return recover_swift_broad_flow(parse_macho(data, limits=PROFILE_LIMITS[profile]), profile=profile)


def norm(symbol):
    return symbol[1:] if symbol.startswith('_') else symbol


class CountingSpy:
    """Counts calls by symbol and delegates to the real function."""

    def __init__(self, real):
        self.real, self.calls = real, []

    def __call__(self, symbol, *args, **kwargs):
        self.calls.append(symbol)
        return self.real(symbol, *args, **kwargs)

    def counts(self):
        return Counter(norm(symbol) for symbol in self.calls)


@contextlib.contextmanager
def spied():
    """Spies on the first-generation parser (wherever it is bound) and on both second-generation entry points."""
    first = CountingSpy(next(iter(airs_modules('parse_import_declaration'))).parse_import_declaration)
    in_effect, in_witness = CountingSpy(effect.parse_declaration), CountingSpy(witness_module.parse_declaration)
    with contextlib.ExitStack() as stack:
        for module in airs_modules('parse_import_declaration'):
            stack.enter_context(mock.patch.object(module, 'parse_import_declaration', first))
        stack.enter_context(mock.patch.object(effect, 'parse_declaration', in_effect))
        stack.enter_context(mock.patch.object(witness_module, 'parse_declaration', in_witness))
        yield first, in_effect, in_witness


def stub_image_with_throwing_symbols(count):
    names = ['_$s1M1%syyKF' % 'abcdefgh'[k] for k in range(count)]
    callers = tuple(((('bl', ('stub', k)), RET)) for k in range(count))
    return build_stub_image(callers=callers, imports=tuple(Import(n) for n in names))[0]


def load_gate():
    script = ROOT / 'scripts' / 'publication_gate.py'
    sys.path.insert(0, str(script.parent))
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location('publication_gate_for_v4_tests', script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.remove(str(script.parent))


def run_cli(args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        code = main(args)
    return code, out.getvalue(), err.getvalue()


# --- D1, D2, D3: isolation -----------------------------------------------------------------------------------
class IsolationTests(unittest.TestCase):
    def test_d01_earlier_profiles_are_byte_identical_to_the_recorded_baseline(self):
        """The six earlier profiles equal the digests recorded in the v3 test module (cited, not recomputed).

        The recorded table has no digest for broad-extended-v3 (that module's own profile), so v3 is covered by the
        structural checks in the next test and by the field-by-field comparison with v4 in group C.
        """
        recorded = [profile for profile in EARLIER if any(key.startswith(profile + '/') for key in v3tests.BASELINE)]
        self.assertEqual(recorded, [p for p in v3tests.EARLIER])
        for profile in recorded:
            for key in ('fixture', *helpers.IMAGES):
                with self.subTest(profile=profile, image=key):
                    self.assertEqual(v3tests.digest(profile, key), v3tests.BASELINE[profile + '/' + key])

    def test_d01_no_v4_group_appears_in_any_older_report(self):
        for profile in EARLIER:
            for key in ('fixture', 'mixed'):
                with self.subTest(profile=profile, image=key):
                    rep = v3tests.report(profile, key)
                    for group in accounting.V4_GROUPS:
                        self.assertNotIn(group, rep)
                    self.assertNotIn(MODEL, json.dumps(rep))
                    self.assertNotIn(EFFECT_MODEL, json.dumps(rep))
        fresh = v3tests.report(PROFILE, 'fixture') if PROFILE in PROFILE_LIMITS else None
        self.assertIsNotNone(fresh)
        for group in accounting.V4_GROUPS:
            self.assertIn(group, fresh)

    def test_d01_the_v4_name_belongs_to_the_v4_model_only(self):
        self.assertEqual(PROFILE_MODELS[PROFILE], MODEL)
        self.assertEqual(sorted(p for p, m in PROFILE_MODELS.items() if m == MODEL), [PROFILE])
        self.assertEqual({p: PROFILE_MODELS[p] for p in EARLIER},
                         {profile: model for model, profile, _ in BASELINE_PAIRS})

    def test_d02_older_profiles_keep_the_first_generation_resolver(self):
        """Fixture (stub and GOT calls): older profiles use no effect resolver; the import profiles still use theirs."""
        data = FIXTURE.read_bytes()
        for profile in EARLIER:
            with self.subTest(profile=profile), spied() as (first, in_effect, in_witness):
                flow(data, profile)
                self.assertEqual(in_effect.calls, [])
                if profile != 'broad-extended-v3':
                    self.assertEqual(in_witness.calls, [])
                if profile in IMPORT_PROFILES:
                    self.assertGreater(len(first.calls), 0)

    def test_d02_v4_resolves_stub_and_got_calls_with_the_second_generation_parser_once_per_symbol(self):
        data = FIXTURE.read_bytes()
        routes = {route for symbol in EXPECTED['symbols'] for route in (s['route'] for s in symbol['call_sites'])}
        self.assertEqual(routes, {'stub', 'got'})
        with spied() as (first, in_effect, _):
            flow(data)
        self.assertEqual(first.calls, [])
        counts = in_effect.counts()
        for symbol in EXPECTED['symbols']:
            if symbol['swift']:
                with self.subTest(symbol=symbol['symbol']):
                    self.assertEqual(counts[norm(symbol['symbol'])], 1)

    def test_d03_caller_fact_profiles_and_indirect_facts_switch(self):
        self.assertEqual(set(CALLER_FACT_PROFILES), {'broad-extended-v2', 'broad-extended-v3', PROFILE})
        self.assertEqual(len(CALLER_FACT_PROFILES), len(set(CALLER_FACT_PROFILES)))
        v3 = v3tests.report('broad-extended-v3', 'imported')
        v4 = flow(helpers.IMAGES['imported']())
        for key in ('indirect_target_shape_model', 'value_witness_admission_model',
                    'indirect_target_shape_counts', 'value_witness_admission_counts'):
            with self.subTest(field=key):
                self.assertIn(key, v4)
                self.assertEqual(v4[key], v3[key])
        rows = lambda rep: {row['call_pc']: row.get('indirect_target_shape') for row in rep['calls']  # noqa: E731
                            if 'indirect_target_shape' in row}
        self.assertEqual(rows(v4), rows(v3))
        self.assertGreater(len(rows(v3)), 0)


# --- D4, D5: registry and generator --------------------------------------------------------------------------
class RegistryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.source = json.loads(REGISTRY.read_text())

    def pairs(self):
        return [(item['model'], item['profile'], item['native_admitted']) for item in self.source['swift_broad_pairs']]

    def test_d04_the_v4_pair_and_its_native_flag(self):
        pairs = {profile: (model, admitted) for model, profile, admitted in self.pairs()}
        self.assertEqual(pairs[PROFILE], (MODEL, V4_NATIVE_ADMITTED))

    def test_d04_effect_model_key(self):
        self.assertEqual(self.source['swift_import_effect_admission_model'], EFFECT_MODEL)
        self.assertEqual(analysis_models.SWIFT_IMPORT_EFFECT_ADMISSION_MODEL, EFFECT_MODEL)
        self.assertEqual(effect.MODEL, EFFECT_MODEL)

    def test_d04_names_are_unique(self):
        pairs = self.pairs()
        self.assertEqual(len({profile for _, profile, _ in pairs}), len(pairs))
        self.assertEqual(len({model for model, _, _ in pairs}), len(pairs))

    def test_d04_the_existing_pairs_are_unchanged(self):
        pairs = self.pairs()
        self.assertEqual([pair for pair in pairs if pair[1] != PROFILE], list(BASELINE_PAIRS))
        self.assertEqual(len(pairs), len(BASELINE_PAIRS) + 1)

    def test_d04_engine_tables_agree_with_the_registry(self):
        self.assertIn((MODEL, PROFILE), analysis_models.SWIFT_BROAD_PAIRS)
        self.assertEqual({(PROFILE_MODELS[p], p) for p in PROFILE_LIMITS}, set(analysis_models.SWIFT_BROAD_PAIRS))


class GeneratorTests(unittest.TestCase):
    def run_generator(self, root, *flags):
        return subprocess.run([sys.executable, '-I', '-B', str(GENERATOR), *flags, '--root', str(root)],
                              capture_output=True, text=True)

    def tree(self, directory):
        root = Path(directory)
        for name in ('registry/models.json', *OUTPUTS):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, root / name)
        return root

    def mutated(self, change):
        source = json.loads(REGISTRY.read_text())
        change(source)
        return json.dumps(source)

    def refused(self, text):
        with tempfile.TemporaryDirectory() as directory:
            root = self.tree(directory)
            (root / 'registry/models.json').write_text(text)
            before = {name: (root / name).read_bytes() for name in OUTPUTS}
            result = self.run_generator(root, '--check')
            self.assertEqual(result.returncode, 1, result.stderr)
            self.assertIn('model registry:', result.stderr)
            self.assertEqual(before, {name: (root / name).read_bytes() for name in OUTPUTS})

    def test_d05_the_checked_in_source_and_outputs_are_accepted(self):
        result = self.run_generator(ROOT, '--check')
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_d05_missing_effect_model_key_is_refused(self):
        self.refused(self.mutated(lambda s: s.pop('swift_import_effect_admission_model')))

    def test_d05_unknown_top_level_key_is_refused(self):
        self.refused(self.mutated(lambda s: s.__setitem__('swift_unknown_model', 'swift-unknown-v1')))

    def test_d05_repeated_profile_name_is_refused(self):
        def repeat(source):
            source['swift_broad_pairs'][-1]['profile'] = source['swift_broad_pairs'][0]['profile']
        self.refused(self.mutated(repeat))

    def test_d05_effect_model_may_not_repeat_another_model(self):
        self.refused(self.mutated(lambda s: s.__setitem__('swift_import_effect_admission_model',
                                                          s['swift_caller_error_test_model'])))

    def test_d05_regeneration_is_idempotent_and_equals_the_checked_in_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'registry').mkdir()
            shutil.copyfile(REGISTRY, root / 'registry/models.json')
            for name in OUTPUTS:
                (root / name).parent.mkdir(parents=True, exist_ok=True)
            first = self.run_generator(root)
            self.assertEqual(first.returncode, 0, first.stderr)
            one = {name: (root / name).read_bytes() for name in OUTPUTS}
            second = self.run_generator(root)
            self.assertEqual(second.returncode, 0, second.stderr)
            self.assertEqual(one, {name: (root / name).read_bytes() for name in OUTPUTS})
            for name in OUTPUTS:
                with self.subTest(file=name):
                    self.assertEqual(one[name], (ROOT / name).read_bytes(), 'checked-in file differs from generation')

    def test_d05_both_generated_files_carry_the_effect_model(self):
        python_text = (ROOT / OUTPUTS[0]).read_text()
        swift_text = (ROOT / OUTPUTS[1]).read_text()
        self.assertRegex(python_text, r'(?m)^SWIFT_IMPORT_EFFECT_ADMISSION_MODEL\s*=\s*[\'"]%s[\'"]\s*$' % EFFECT_MODEL)
        self.assertRegex(swift_text, r'(?m)^\s*(?:public\s+)?static\s+let\s+\w+\s*(?::\s*\w+\s*)?=\s*"%s"\s*$'
                         % EFFECT_MODEL)
        self.assertEqual(python_text.count(EFFECT_MODEL), 1)
        self.assertEqual(swift_text.count(EFFECT_MODEL), 1)

    def test_d05_generated_files_list_the_v4_pair(self):
        # The native file lists only native-admitted pairs; the v4 pair is native-admitted, so both files list it.
        self.assertTrue(V4_NATIVE_ADMITTED)
        for output in OUTPUTS:
            with self.subTest(output=output):
                text = (ROOT / output).read_text()
                self.assertIn(MODEL, text)
                self.assertIn(PROFILE, text)


# --- D6: command line -----------------------------------------------------------------------------------------
class CommandLineTests(unittest.TestCase):
    def test_d06_every_profile_is_accepted_by_the_parser(self):
        for profile in ALL_PROFILES:
            with self.subTest(profile=profile):
                args = _parser().parse_args(['swift-error-flow', 'owned.macho', '--swift-profile', profile])
                self.assertEqual(args.swift_profile, profile)

    def test_d06_unknown_profile_is_refused_as_before(self):
        for bad in ('broad-extended-v5', 'broad-extended-v4 ', 'broad-v4', ''):
            with self.subTest(profile=bad):
                err = io.StringIO()
                with contextlib.redirect_stderr(err), self.assertRaises(SystemExit) as caught:
                    _parser().parse_args(['swift-error-flow', 'owned.macho', '--swift-profile', bad])
                self.assertEqual(caught.exception.code, 2)
                self.assertIn('invalid choice', err.getvalue())

    def test_d06_v4_needs_the_same_options_as_the_other_broad_profiles(self):
        variants = [[], *[[flag for flag in REQUIRED if flag != missing] for missing in REQUIRED],
                    REQUIRED + ['--include-swift-methods']]
        for flags in variants:
            with self.subTest(flags=flags), patch('airs.cli.resolve_input') as resolve:
                code, _, err = run_cli(['swift-error-flow', 'absent.macho', '--swift-profile', PROFILE, *flags])
                self.assertEqual(code, 2)
                self.assertEqual(json.loads(err)['error']['code'], 'swift_broad_options')
                resolve.assert_not_called()

    def test_d06_every_profile_takes_the_broad_path_with_its_own_name(self):
        for profile in ALL_PROFILES:
            with self.subTest(profile=profile), \
                    patch('airs.cli.resolve_input', return_value=Path('owned.macho')), \
                    patch('airs.cli.recover_swift_error_flow_path') as legacy, \
                    patch('airs.cli.recover_swift_broad_flow_path',
                          side_effect=InputError('swift_broad_pipeline_pending', 'pending')) as broad:
                code, _, err = run_cli(['swift-error-flow', 'owned.macho', '--swift-profile', profile, *REQUIRED])
                self.assertEqual(code, 2)
                legacy.assert_not_called()
                broad.assert_called_once()
                call = broad.call_args
                self.assertEqual(call.args, (Path('owned.macho'),))
                self.assertEqual(call.kwargs.get('requested_arch'), 'auto')
                if profile == 'broad-v1':
                    self.assertNotIn('profile', call.kwargs)           # the first profile keeps its historical call
                else:
                    self.assertEqual(call.kwargs.get('profile'), profile)
                self.assertEqual(json.loads(err)['error']['code'], 'swift_broad_pipeline_pending')

    def test_d06_text_uses_the_broad_renderer(self):
        report = flow(FIXTURE.read_bytes())
        with patch('airs.cli.resolve_input', return_value=Path('owned.macho')), \
                patch('airs.cli.recover_swift_broad_flow_path', return_value=report), \
                patch('airs.cli.render_swift_error_text') as legacy:
            code, out, _ = run_cli(['swift-error-flow', 'owned.macho', '--swift-profile', PROFILE, *REQUIRED,
                                    '--format', 'text'])
        self.assertEqual(code, 0)
        legacy.assert_not_called()
        self.assertIn(render_swift_broad_text(report).rstrip('\n'), out)

    def test_d06_json_output_is_the_engine_report(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'owned.macho'
            path.write_bytes(FIXTURE.read_bytes())
            code, out, _ = run_cli(['swift-error-flow', str(path), '--swift-profile', PROFILE, *REQUIRED,
                                    '--format', 'json'])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out), json.loads(dumps(flow(FIXTURE.read_bytes()))))


# --- D7: text -------------------------------------------------------------------------------------------------
class TextTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = flow(FIXTURE.read_bytes())
        cls.text = render_swift_broad_text(cls.report)

    def test_d07_header_names_model_profile_effect_model_and_grammar(self):
        for needle in (MODEL, PROFILE, EFFECT_MODEL, GRAMMAR_MODEL, GRAMMAR_PIN):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.text)

    def test_d07_accounting_and_table_sections_are_present(self):
        lower = self.text.lower()
        for word in ('omit', 'import', 'complete', 'residual'):
            with self.subTest(word=word):
                self.assertIn(word, lower)
        table = self.report['import_calls']
        self.assertIn(str(table['attributed_calls']), self.text)
        self.assertIn(str(table['distinct_symbols']), self.text)
        for entry in table['entries'][:3]:
            self.assertIn(entry['symbol'], self.text)

    def test_d07_incomplete_table_states_complete_false_and_the_residual(self):
        with forced(IMPORT_TABLE_MAX_ENTRIES=2):
            report = flow(stub_image_with_throwing_symbols(4))
        self.assertIs(report['import_calls']['complete'], False)
        text = render_swift_broad_text(report)
        self.assertRegex(text, r'(?i)complete\W{0,8}(?:false|no)\b')
        self.assertRegex(text, r'(?i)residual[^\n]*\b2\b')

    def test_d07_complete_table_does_not_say_incomplete(self):
        self.assertIs(self.report['import_calls']['complete'], True)
        self.assertNotRegex(self.text, r'(?i)complete\W{0,8}(?:false|no)\b')

    def test_d07_wrong_model_for_the_v4_profile_is_refused(self):
        for model in (PROFILE_MODELS['broad-extended-v3'], 'swift-broad-error-flow-extended-v9', ''):
            with self.subTest(model=model):
                bad = copy.deepcopy(self.report)
                bad['model_version'] = model
                with self.assertRaises(InputError) as caught:
                    render_swift_broad_text(bad)
                self.assertEqual(caught.exception.code, 'swift_broad_text_model')

    def test_d07_v4_model_under_another_profile_is_refused(self):
        bad = copy.deepcopy(self.report)
        bad['profile'] = 'broad-extended-v3'
        with self.assertRaises(InputError) as caught:
            render_swift_broad_text(bad)
        self.assertEqual(caught.exception.code, 'swift_broad_text_model')

    def test_d07_older_profiles_render_without_the_new_vocabulary(self):
        for profile in EARLIER:
            with self.subTest(profile=profile):
                text = render_swift_broad_text(v3tests.report(profile, 'fixture'))
                self.assertNotIn(EFFECT_MODEL, text)
                self.assertNotIn(MODEL, text)


# --- D8, D9: documents ----------------------------------------------------------------------------------------
def published_files():
    names = [DOCS / 'ROADMAP.md', DOCS / 'SWIFT_BROAD_EXTENDED_V4_PROFILE.md']
    names += sorted(path for path in DOCS.rglob('*.md') if 'v4' in path.name.lower() and path not in names)
    names += [Path(__file__).resolve(), Path(__file__).resolve().with_name('test_swift_broad_extended_v4.py')]
    return names


class HygieneTests(unittest.TestCase):
    def test_d08_published_files_exist(self):
        for path in published_files():
            with self.subTest(path=path.name):
                self.assertTrue(path.is_file())

    def test_d08_publication_gate_accepts_every_published_file(self):
        gate = load_gate()
        for path in published_files():
            with self.subTest(path=path.name):
                try:
                    gate.inspect_bytes(path.read_bytes(), path.name)
                except gate.GateError as error:
                    self.fail('publication gate rejected %s: %s' % (path.name, error))

    def test_d08_no_maintainer_name_vendor_name_or_attribution_trailer(self):
        for path in published_files():
            text = path.read_text(encoding='utf-8')
            with self.subTest(path=path.name):
                self.assertIsNone(MAINTAINER.search(text))
                self.assertIsNone(VENDOR.search(text))
                for trailer in TRAILERS:
                    self.assertIsNone(trailer.search(text))


class DocumentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.roadmap = (DOCS / 'ROADMAP.md').read_text(encoding='utf-8')
        page = DOCS / 'SWIFT_BROAD_EXTENDED_V4_PROFILE.md'
        cls.page_path = page
        cls.page = page.read_text(encoding='utf-8') if page.is_file() else ''
        cls.plain = cls.page.lower().replace('_', ' ')

    def test_d09_roadmap_no_longer_carries_the_stale_statements(self):
        self.assertNotRegex(self.roadmap, r'(?i)no\s+profile\s+uses\s+it\s+yet')
        self.assertNotRegex(self.roadmap, r'(?i)\bfive\s+(?:named|existing)\b[^.]{0,40}\bprofile')

    def test_d09_roadmap_states_the_registered_and_native_counts(self):
        text = re.sub(r'\s+', ' ', self.roadmap)
        self.assertRegex(text, r'(?i)\b(?:seven|eight)\b[^.]{0,60}\b(?:registered|named|names)\b|'
                               r'\b(?:registered|named)\b[^.]{0,60}\b(?:seven|eight)\b')
        self.assertRegex(text, r'(?i)\bseven\b[^.]{0,60}\beight\b[^.]{0,120}\bnative')
        self.assertNotRegex(text, r'(?i)\bsix\b[^.]{0,120}native')
        self.assertNotRegex(text, r'(?i)\bonce\b[^.]{0,40}\bnative validator\b')

    def test_d09_profile_page_exists_and_names_the_identity(self):
        self.assertTrue(self.page_path.is_file())
        for needle in (PROFILE, MODEL, EFFECT_MODEL, GRAMMAR_MODEL, GRAMMAR_PIN):
            with self.subTest(needle=needle):
                self.assertIn(needle, self.page)

    def test_d09_profile_page_reproduces_the_licence_table(self):
        for name in LICENCE_CLASSES + ROW_REASONS:
            with self.subTest(name=name):
                self.assertIn(name.replace('_', ' '), self.plain)

    def test_d09_profile_page_lists_premises_and_not_claimed_items(self):
        self.assertEqual(len(accounting.PREMISES), 5)
        self.assertEqual(len(accounting.NOT_CLAIMED), 5)
        for name in tuple(accounting.PREMISES) + tuple(accounting.NOT_CLAIMED):
            with self.subTest(name=name):
                self.assertIn(name.replace('_', ' '), self.plain)

    def test_d09_profile_page_says_5b_gives_no_witness_to_any_import(self):
        text = re.sub(r'\s+', ' ', self.page)
        self.assertRegex(text, r'(?i)\b5b\b[^.]{0,120}\bno\s+(?:\w+\s+){0,3}witness|'
                               r'\b5b\b[^.]{0,120}witness[^.]{0,80}\b(?:no|not|none)\b')
        self.assertRegex(text, r'(?i)\bimport')

    def test_d09_profile_page_links_the_grammar_and_the_5a_contract(self):
        links = re.findall(r'\[([^\]]*)\]\(([^)\s]+)\)', self.page)
        self.assertTrue(any('DECLARATION_GRAMMAR' in target for _, target in links))
        self.assertTrue(any(re.search(r'(?i)5a|effect[-_ ]admission|import[-_ ]effect', text + ' ' + target)
                            for text, target in links))
        for text, target in links:
            if re.match(r'[a-z]+:', target) or target.startswith('#'):
                continue
            with self.subTest(link=target):
                self.assertTrue((self.page_path.parent / target.split('#')[0]).exists())


if __name__ == '__main__':
    unittest.main()
