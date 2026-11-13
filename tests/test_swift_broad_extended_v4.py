"""Group C tests: profile broad-extended-v4 end to end (packet P4).

Written from the design contract and its test list (tests C1 to C20); the engine wiring was not read. Images are
synthetic thin ARM64 files assembled by tests/stub_image_helpers.py and tests/got_image_helpers.py, plus the owned
fixture OwnedImports.macho, which is data and is never executed. The owned-fixture tests compare with the
hand-authored expectation expected-v4.json and never regenerate it; the golden report is compared byte for byte and the
test is skipped while the golden is not committed.

Interface assumed (everything below is read from the merged accounting library or from the engine before this change):

    airs.swift_broad_flow          recover_swift_broad_flow(image, limits=None, *, profile=...) with the module
                                   constants REPORT_BYTES, AGGREGATE_WORK, CALLSITE_WORK_RESERVATION and the table
                                   PROFILE_LIMITS / PROFILE_MODELS. A raised limit is refused with InputError code
                                   swift_broad_limit; a lowered limit is allowed.
    airs.swift_broad_accounting    check_broad_v4_report(report) returns None or raises BroadV4ReportError (a
                                   ValueError) whose message starts with the rule id ("A5: ..."), the constants
                                   IMPORT_TABLE_MAX_ENTRIES, IMPORT_TABLE_BYTE_RESERVE, ENTRY_OVERHEAD_BYTES and
                                   RETENTION_LIMIT, split_scan and UnselectedPartition. The engine calls the checker
                                   before it returns a v4 report and fails closed.

Patching rule. A module constant is forced in every loaded airs module that has the name (the engine may import the
constant by name), see forced(). Rule A6 pins limits.max_total_evidence to accounting.RETENTION_LIMIT, so a test that
lowers max_total_evidence also forces RETENTION_LIMIT to the same value; without it no lowered limit could pass the
checker. This is recorded as an open point in the maintainer notes of this test group.

Report fields are named as in contract 5. Where a number comes from a module constant the test says which one.
"""
import contextlib
import copy
import dataclasses
import functools
import json
import re
import struct
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from airs import swift_broad_accounting as accounting  # noqa: E402
from airs import swift_broad_flow as flow_module  # noqa: E402
from airs.macho import parse_macho  # noqa: E402
from airs.report import dumps  # noqa: E402
from airs.swift_broad_flow import (PROFILE_LIMITS, PROFILE_MODELS, recover_swift_broad_flow,  # noqa: E402
                                   recover_swift_broad_flow_path)
from airs.swift_declaration_grammar import parse_declaration as real_parse  # noqa: E402
from airs.types import InputError, Limits  # noqa: E402
from got_image_helpers import GotImport, build_got_image, got_call  # noqa: E402
from shape_word_helpers import blr  # noqa: E402
from stub_image_helpers import BASE, NOP, RET, Import, build_stub_image  # noqa: E402
from stub_image_helpers import patch as patch_bytes  # noqa: E402

PROFILE = 'broad-extended-v4'
MODEL = 'swift-broad-error-flow-extended-v4'
V3_PROFILE = 'broad-extended-v3'
CEILING = PROFILE_LIMITS[PROFILE]
FIXTURE_DIR = Path(__file__).resolve().parents[1] / 'fixtures' / 'swift-error-flow' / 'broad-imports'
FIXTURE = FIXTURE_DIR / 'OwnedImports.macho'
EXPECTED = json.loads((FIXTURE_DIR / 'expected-v4.json').read_text())
GOLDEN = FIXTURE_DIR / 'report-v4.golden.json'

# Symbols the real grammar (swift-declaration-syntax-v2) decides as the names say.
THROWING = '_$s1M1fyyKF'
NON_THROWING = '_$s1M1gyyF'
DECLINED_SWIFT = '_$s1M1dyyKF'
NON_SWIFT = '_malloc'

# Contract 5.2 and the native decoder: the bounds a legal report stays inside.
NODE_LIMIT = 2_000_000
DEPTH_LIMIT = 32
STRING_LIMIT = 65_536
BYTES_LIMIT = 16 * 1024 * 1024
OUTPUT_SLACK = 65_536            # the constant the engine subtracts from REPORT_BYTES before the table reserve

CAUSE_ORDER = ('analysis_work_budget', 'per_function_limit', 'total_row_limit', 'output_budget')
KIND_ORDER = ('import_stub', 'import_got', 'local_swift_direct', 'indirect')


# --- patching ------------------------------------------------------------------------------------------------
def airs_modules(name):
    return [module for key, module in sorted(sys.modules.items())
            if key.startswith('airs.') and module is not None and hasattr(module, name)]


@contextlib.contextmanager
def forced(**constants):
    """Force module constants in every loaded airs module that has the name."""
    with contextlib.ExitStack() as stack:
        for name, value in constants.items():
            targets = airs_modules(name)
            assert targets, 'no airs module has the name %s' % name
            for module in targets:
                stack.enter_context(mock.patch.object(module, name, value))
        yield


def run(data, *, limits=None, profile=PROFILE):
    image = parse_macho(data, limits=PROFILE_LIMITS[profile])
    return recover_swift_broad_flow(image, limits, profile=profile)


def run_forced(data, *, limit_changes=None, constants=None, profile=PROFILE):
    """Run the engine with lowered limits and forced constants, then check the report inside the same patches."""
    changes = dict(limit_changes or {})
    consts = dict(constants or {})
    if 'max_total_evidence' in changes:
        consts['RETENTION_LIMIT'] = changes['max_total_evidence']
    limits = dataclasses.replace(PROFILE_LIMITS[profile], **changes) if changes else None
    with forced(**consts):
        report = run(data, limits=limits, profile=profile)
        accounting.check_broad_v4_report(report)
    return report


# --- image builders ------------------------------------------------------------------------------------------
def bl_stub(count, stub=0):
    return tuple(('bl', ('stub', stub)) for _ in range(count))


def stub_image(callers, symbols, declined=()):
    data, layout = build_stub_image(callers=callers, imports=tuple(Import(s) for s in symbols))
    for index in declined:
        data = patch_bytes(data, layout.stub_word_off(index, 2), '<I', NOP)     # stub word 3 is no longer br x16
    return data, layout


def trim_text(data, by=2):
    """Shrink the __text section by `by` bytes so that the last function has a size that is not word aligned."""
    marker = b'__text'.ljust(16, b'\0') + b'__TEXT'.ljust(16, b'\0')
    assert data.count(marker) == 1
    at = data.index(marker)
    (size,) = struct.unpack_from('<Q', data, at + 40)
    return patch_bytes(data, at + 40, '<Q', size - by)


def functions_of(data):
    return parse_macho(data, limits=CEILING).functions


def kinds_stub_image():
    """2 attributed stub calls (throwing), 1 direct call to an in-image $s function, 2 indirect candidates."""
    def build(target):
        first = (('bl', ('stub', 0)), ('bl', ('stub', 0)), ('bl', target), blr(8), blr(9), RET)
        return build_stub_image(callers=(first, (RET,)), imports=(Import(THROWING),))
    _, layout = build(BASE)
    data, _ = build(layout.caller_addrs[1])
    renamed = data.replace(b'_caller1\x00', b'_$s1fyyF\x00')
    assert renamed != data and len(renamed) == len(data)
    return renamed


def kinds_got_image():
    """1 GOT call attributed to a Swift import."""
    return build_got_image(callers=((*got_call(slot=0), RET),), imports=(GotImport(THROWING),))[0]


def partition_image():
    """The B4 image: seven call instructions, two selected, one in each of the five unselected buckets."""
    imports = (Import(NON_THROWING), Import(NON_SWIFT), Import(DECLINED_SWIFT), Import(THROWING))

    def first(target):
        return (('bl', ('stub', 0)), ('bl', ('stub', 1)), ('bl', ('stub', 2)), ('bl', target),
                ('bl', BASE + 0x100), ('bl', ('stub', 3)), ('bl', ('stub', 3)),
                0x14000002,                                    # b +8, inside the same function: not a call
                NOP, NOP, RET)
    _, layout = build_stub_image(callers=(first(BASE), (RET,)), imports=imports)
    data, layout = build_stub_image(callers=(first(layout.caller_addrs[1]), (RET,)), imports=imports)
    return patch_bytes(data, layout.stub_word_off(2, 2), '<I', NOP)


def mixed_image():
    imports = (Import(THROWING), Import(NON_THROWING), Import(NON_SWIFT))
    first = (('bl', ('stub', 0)), ('bl', ('stub', 1)), ('bl', ('stub', 2)), blr(8), RET)
    second = (('bl', ('stub', 0)), RET)
    return build_stub_image(callers=(first, second), imports=imports)[0]


def worst_case_image(symbols=4096):
    names = ['_$s1M5s%04dyyKF' % k for k in range(symbols)]
    callers = tuple((*bl_stub(2, k), RET) for k in range(symbols))
    return build_stub_image(callers=callers, imports=tuple(Import(n) for n in names))[0], names


# --- report accessors ----------------------------------------------------------------------------------------
def norm(symbol):
    return symbol[1:] if symbol.startswith('_') else symbol


def is_import_row(row):
    return row['admission'].get('import_attribution_admitted') is True


def import_rows(report):
    return [row for row in report['calls'] if is_import_row(row)]


def row_field(row, name):
    """The v4 per-row records; the contract does not fix whether they sit on the row or inside its admission."""
    return row[name] if name in row else row['admission'][name]


def entry_for(report, symbol):
    found = [entry for entry in report['import_calls']['entries'] if norm(entry['symbol']) == norm(symbol)]
    assert len(found) == 1, (symbol, [entry['symbol'] for entry in report['import_calls']['entries']])
    return found[0]


def causes(report):
    return {name: report['omission_causes'][name] for name in CAUSE_ORDER}


def kinds(report):
    return {name: report['omitted_by_kind'][name] for name in KIND_ORDER}


def only_cause(name, count):
    return {cause: (count if cause == name else 0) for cause in CAUSE_ORDER}


def pc_of(value):
    return int(value, 16) if isinstance(value, str) else value


def row_cost(row):
    """The engine's byte accounting of one row (v3 formula): indented JSON, four bytes of indent slack per line."""
    text = json.dumps(row, ensure_ascii=True, indent=2, sort_keys=True)
    return len(text) + 4 * (text.count('\n') + 1) + 2


def measure(value):
    """Count every value (objects, arrays, scalars) and every object key, depth and the longest string."""
    values = keys = longest = deepest = 0
    stack = [(value, 0)]
    while stack:
        item, depth = stack.pop()
        values += 1
        deepest = max(deepest, depth)
        if isinstance(item, str):
            longest = max(longest, len(item.encode('utf-8')))
        elif isinstance(item, dict):
            for key, child in item.items():
                keys += 1
                longest = max(longest, len(key.encode('utf-8')))
                stack.append((child, depth + 1))
        elif isinstance(item, list):
            for child in item:
                stack.append((child, depth + 1))
    return dict(values=values, nodes_with_keys=values + keys, depth=deepest, longest_string=longest)


@functools.lru_cache(maxsize=None)
def fixture_report(profile):
    return run(FIXTURE.read_bytes(), profile=profile)


@functools.lru_cache(maxsize=None)
def worst_case_report():
    data, names = worst_case_image()
    return run(data), names


# --- tests ---------------------------------------------------------------------------------------------------
class LimitAndCauseTests(unittest.TestCase):
    def test_c01_per_function_and_total_row_limits(self):
        """F1 has 5 attributed throwing stub calls, F2 has 3; limits 2 per function and 3 in total."""
        data, _ = stub_image((bl_stub(5) + (RET,), bl_stub(3) + (RET,)), [THROWING])
        rep = run_forced(data, limit_changes=dict(max_observations_per_function=2, max_total_evidence=3))
        self.assertEqual(len(rep['calls']), 3)
        self.assertEqual(rep['omitted_calls'], 5)
        self.assertEqual(causes(rep), dict(analysis_work_budget=0, per_function_limit=3, total_row_limit=2,
                                           output_budget=0))
        self.assertEqual(kinds(rep), dict(import_stub=5, import_got=0, local_swift_direct=0, indirect=0))
        self.assertIs(rep['call_details_complete'], False)
        per_caller = [row['caller_pc'] for row in rep['calls']]
        self.assertEqual(per_caller[0], per_caller[1])
        self.assertNotEqual(per_caller[1], per_caller[2])            # F1 retains 2, F2 retains 1
        entry = entry_for(rep, THROWING)
        self.assertEqual((entry['calls'], entry['retained'], entry['omitted']), (8, 3, 5))

    def test_c02_per_function_limit_is_charged_before_the_total_limit(self):
        """One function, two calls, both limits 1: the second call exceeds both and is charged per function."""
        data, _ = stub_image((bl_stub(2) + (RET,),), [THROWING])
        rep = run_forced(data, limit_changes=dict(max_observations_per_function=1, max_total_evidence=1))
        self.assertEqual(len(rep['calls']), 1)
        self.assertEqual(causes(rep), dict(analysis_work_budget=0, per_function_limit=1, total_row_limit=0,
                                           output_budget=0))

    def test_c03_analysis_work_is_charged_before_the_row_limits(self):
        """Derivation of the forced AGGREGATE_WORK.

        The engine refuses a candidate when the work already spent, plus the work still reserved for caller scans,
        plus the per-candidate reservations (CALLSITE_WORK_RESERVATION and the module's other reservation
        constants), exceeds AGGREGATE_WORK. Every admitted row adds its own work, so the smallest AGGREGATE_WORK
        that admits exactly the first 2 of 5 candidates is found by bisection over AGGREGATE_WORK itself, and the
        test asserts that one unit less admits only 1. As a sanity bound the value must be at least
        CALLSITE_WORK_RESERVATION. Then the limits are lowered to 2 rows as well: candidates 3 to 5 are refused by
        both, and the cause is the work budget because it is evaluated first.
        """
        data, _ = stub_image((bl_stub(1) + (RET,),) * 5, [THROWING])

        def report_at(work, **changes):
            return run_forced(data, limit_changes=changes, constants=dict(AGGREGATE_WORK=work))

        low, high = 0, flow_module.AGGREGATE_WORK
        self.assertEqual(len(report_at(low)['calls']), 0)
        self.assertEqual(len(report_at(high)['calls']), 5)
        while high - low > 1:
            middle = (low + high) // 2
            if len(report_at(middle)['calls']) >= 2:
                high = middle
            else:
                low = middle
        work = high
        reservation = getattr(flow_module, 'CALLSITE_WORK_RESERVATION', None)
        if reservation is not None:
            self.assertGreaterEqual(work, reservation)
        at, below = report_at(work), report_at(work - 1)
        self.assertEqual((len(at['calls']), len(below['calls'])), (2, 1), 'no AGGREGATE_WORK admits exactly 2')
        self.assertEqual(at['omitted_calls'], 3)
        self.assertEqual(causes(at), only_cause('analysis_work_budget', 3))
        both = report_at(work, max_total_evidence=2)
        self.assertEqual(len(both['calls']), 2)
        self.assertEqual(both['omitted_calls'], 3)
        self.assertEqual(causes(both), only_cause('analysis_work_budget', 3))

    def test_c04_output_budget_cause(self):
        """REPORT_BYTES is forced so that exactly k = 3 of 8 rows fit.

        One measured row size gives k: the rows of an unrestricted run are costed with the engine's row formula,
        and the forced budget is the cost of the first three rows plus half of the smallest row. The engine takes
        the budget as REPORT_BYTES - 65536 - IMPORT_TABLE_BYTE_RESERVE, so REPORT_BYTES adds both back.
        """
        data, _ = stub_image((bl_stub(1) + (RET,),) * 8, [THROWING])
        costs = [row_cost(row) for row in run_forced(data)['calls']]
        self.assertEqual(len(costs), 8)
        k = 3
        budget = sum(costs[:k]) + min(costs) // 2
        reserve = accounting.IMPORT_TABLE_BYTE_RESERVE
        report_bytes = budget + OUTPUT_SLACK + reserve
        rep = run_forced(data, constants=dict(REPORT_BYTES=report_bytes))
        self.assertEqual(len(rep['calls']), k)
        self.assertEqual(rep['omitted_calls'], 8 - k)
        self.assertEqual(causes(rep), only_cause('output_budget', 8 - k))
        self.assertEqual(kinds(rep)['import_stub'], 8 - k)
        self.assertIs(rep['call_details_complete'], False)
        self.assertEqual(rep['limits']['output_budget_bytes'], report_bytes - OUTPUT_SLACK - reserve)
        self.assertLessEqual(len(dumps(rep, maximum_bytes=report_bytes).encode()), report_bytes)

    def test_c05_omitted_by_kind(self):
        """Every candidate omitted by the lowest row limit (max_total_evidence 0), counted per kind.

        A stub image and a GOT image cannot be mixed, so the contract's 6 omitted calls are split over two images:
        the stub image holds 2 attributed stub calls, 1 direct call to an in-image $s function and 2 indirect
        candidates; the GOT image holds 1 GOT call attributed to an import. The sum is asserted at the end.
        """
        stub = run_forced(kinds_stub_image(), limit_changes=dict(max_total_evidence=0))
        got = run_forced(kinds_got_image(), limit_changes=dict(max_total_evidence=0))
        self.assertEqual(kinds(stub), dict(import_stub=2, import_got=0, local_swift_direct=1, indirect=2))
        self.assertEqual(kinds(got), dict(import_stub=0, import_got=1, local_swift_direct=0, indirect=0))
        self.assertEqual((stub['omitted_calls'], got['omitted_calls']), (5, 1))
        self.assertEqual((len(stub['calls']), len(got['calls'])), (0, 0))
        total = {name: stub['omitted_by_kind'][name] + got['omitted_by_kind'][name] for name in KIND_ORDER}
        self.assertEqual(total, dict(import_stub=2, import_got=1, local_swift_direct=1, indirect=2))
        self.assertEqual(sum(total.values()), 6)
        for rep in (stub, got):
            self.assertEqual(causes(rep), only_cause('total_row_limit', rep['omitted_calls']))

    def test_c06_kind_is_known_without_the_limited_work(self):
        """The images of C5 with the analysis-work budget exhausted for every candidate: same kinds."""
        for name, data in (('stub', kinds_stub_image()), ('got', kinds_got_image())):
            with self.subTest(image=name):
                limited = run_forced(data, limit_changes=dict(max_total_evidence=0))
                exhausted = run_forced(data, constants=dict(AGGREGATE_WORK=0))
                self.assertEqual(kinds(exhausted), kinds(limited))
                self.assertEqual(exhausted['omitted_calls'], limited['omitted_calls'])
                self.assertEqual(causes(exhausted), only_cause('analysis_work_budget', exhausted['omitted_calls']))
                self.assertEqual(len(exhausted['calls']), 0)

    def test_c07_reason_counts_is_a_partition(self):
        """One function excluded for its boundary (a last function of 10 bytes): no marker in v4, marker in v3."""
        data, _ = stub_image((bl_stub(2) + (NOP, RET), (NOP, NOP, RET)), [THROWING])
        data = trim_text(data)
        self.assertEqual([f.size for f in functions_of(data)], [16, 10])
        rep = run_forced(data)
        self.assertNotIn('excluded_boundary', rep['reason_counts'])
        self.assertEqual(sum(rep['reason_counts'].values()), len(rep['calls']))
        self.assertEqual(len(rep['calls']), 2)
        self.assertEqual(rep['scan']['functions_excluded_boundary'], 1)
        self.assertIs(rep['word_scan_complete'], False)
        older = run(data, profile=V3_PROFILE)
        self.assertEqual(older['reason_counts'].get('excluded_boundary'), 1)


class AccountingTests(unittest.TestCase):
    def test_c08_scan_accounting_in_the_engine(self):
        """B1 with the functions that one synthetic image can hold, ceilings 10 per function and 25 in total.

        B1's F5 (a boundary source other than the function starts) and F7 (size 0) cannot be made in one image of
        function-starts functions, so F5 and F7 are left out and F6 (10 bytes, not word aligned) is the last
        function. Words: F1 16, F2 8, F3 12, F4 4, F6 2 (10 bytes divided by 4).
        """
        body = lambda words: (NOP,) * (words - 1) + (RET,)               # noqa: E731
        data, _ = build_stub_image(callers=(body(16), body(8), body(12), body(4), body(3)), imports=())
        data = trim_text(data)
        functions = functions_of(data)
        self.assertEqual([f.size for f in functions], [64, 32, 48, 16, 10])
        self.assertTrue(all(f.boundary_source == 'lc_function_starts' for f in functions))
        rep = run_forced(data, limit_changes=dict(max_instructions_per_function=10, max_total_instructions=25))
        self.assertEqual(rep['scan'], dict(
            words_total=42, words_scanned=25, words_unscanned_per_function_ceiling=8,
            words_unscanned_total_ceiling=7, words_excluded_boundary=2, functions_total=5,
            functions_excluded_boundary=1, functions_truncated=3, candidates_in_unscanned_words=None,
            candidates_in_unscanned_words_reason='words_not_decoded'))
        self.assertIs(rep['word_scan_complete'], False)
        self.assertEqual(rep['scanned_words'], 25)
        self.assertIs(rep['import_calls']['complete'], False)
        per_function = accounting.split_scan([(f.size, True) for f in functions], 10, 25)['functions']
        self.assertEqual([(r['decoded'], r['unscanned_per_function_ceiling'], r['unscanned_total_ceiling'],
                           r['excluded_boundary']) for r in per_function],
                         [(10, 6, 0, 0), (8, 0, 0, 0), (7, 2, 3, 0), (0, 0, 4, 0), (0, 0, 0, 2)])

    def test_c09_unselected_partition_in_the_engine(self):
        rep = run_forced(partition_image())
        self.assertEqual(rep['observed_call_instructions'], 7)
        self.assertEqual(rep['selected_call_candidates'], 2)
        self.assertEqual(rep['unselected_call_counts'], dict(
            skipped_non_throwing=1, non_swift_import=1, declined_stub=1, direct_target_not_swift_function=1,
            direct_target_unattributed=1, other=0))
        self.assertEqual(len(rep['calls']), 2)
        self.assertEqual({norm(row['admission']['symbol']) for row in rep['calls']}, {norm(THROWING)})

    def test_c10_table_overflow_in_the_engine(self):
        """IMPORT_TABLE_MAX_ENTRIES 2 and four attributed symbols first seen in the order z, y, a, b."""
        z, y, a, b = ('_$s1M1%syyKF' % letter for letter in 'zyab')
        data, _ = stub_image(tuple((*bl_stub(1, k), RET) for k in range(4)), [z, y, a, b])
        rep = run_forced(data, constants=dict(IMPORT_TABLE_MAX_ENTRIES=2))
        table = rep['import_calls']
        self.assertEqual([norm(e['symbol']) for e in table['entries']], [norm(y), norm(z)])    # first two, sorted
        self.assertEqual((table['residual']['symbols'], table['residual']['calls']), (2, 2))
        self.assertEqual(table['residual']['retained'], 2)
        self.assertIs(table['complete'], False)
        self.assertEqual((table['distinct_symbols'], table['attributed_calls']), (4, 4))
        self.assertEqual(rep['limits']['import_table_entries'], 2)
        self.assertEqual(len(rep['calls']), 4)


class HeaderTests(unittest.TestCase):
    def setUp(self):
        self.report = run_forced(stub_image((bl_stub(1) + (RET,),), [THROWING])[0])

    def test_c11_reserve_and_effective_budget(self):
        limits = self.report['limits']
        self.assertEqual(limits['output_budget_bytes'],
                         flow_module.REPORT_BYTES - OUTPUT_SLACK - accounting.IMPORT_TABLE_BYTE_RESERVE)
        self.assertEqual(limits['import_table_entries'], accounting.IMPORT_TABLE_MAX_ENTRIES)
        self.assertEqual(limits['import_table_byte_reserve'], accounting.IMPORT_TABLE_BYTE_RESERVE)

    def test_c12_capabilities_and_limits_header(self):
        rep = self.report
        self.assertEqual((rep['profile'], rep['model_version']), (PROFILE, MODEL))
        capabilities = rep['capabilities']
        self.assertEqual(capabilities['premises'], ['symbol_name_carries_effects', 'no_silgen_name_override',
                                                    'name_only_attribution', 'binding_not_proven', 'grammar_pinned'])
        self.assertEqual(capabilities['not_claimed'], ['callee_returns', 'dyld_binding', 'runtime_callee',
                                                       'arguments_and_results', 'error_value_at_runtime'])
        self.assertEqual(capabilities['report_model'], 'swift-broad-error-flow-extended-v4')
        self.assertEqual(capabilities['effect_admission_model'], 'swift-import-effect-admission-v1')
        self.assertEqual(capabilities['declaration_syntax_model'], 'swift-declaration-syntax-v2')
        self.assertEqual(capabilities['caller_error_test_model'], 'swift-caller-error-test-v1')
        self.assertEqual(capabilities['grammar_pin'], 'swift-6.4.2-RELEASE')
        witness_limits = flow_module.BroadWitnessLimits()
        output_budget = max(0, min(flow_module.REPORT_BYTES, witness_limits.max_aggregate_bytes) - OUTPUT_SLACK)
        self.assertEqual(rep['limits'], dict(
            max_total_evidence=CEILING.max_total_evidence,
            max_observations_per_function=CEILING.max_observations_per_function,
            max_instructions_per_function=CEILING.max_instructions_per_function,
            max_total_instructions=CEILING.max_total_instructions,
            analysis_work_ceiling=flow_module.AGGREGATE_WORK,
            output_budget_bytes=output_budget - accounting.IMPORT_TABLE_BYTE_RESERVE,
            import_table_entries=accounting.IMPORT_TABLE_MAX_ENTRIES,
            import_table_byte_reserve=accounting.IMPORT_TABLE_BYTE_RESERVE))
        self.assertEqual(set(rep['limits']), set(accounting.LIMIT_KEYS))
        self.assertEqual(rep['limits']['max_total_evidence'], 8192)

    def test_c13_retention_limit_is_not_raised(self):
        message = 'Requested limits exceed profile bounds'
        for field in dataclasses.fields(Limits):
            for profile in (PROFILE, V3_PROFILE):
                ceiling_value = getattr(PROFILE_LIMITS[profile], field.name)
                if type(ceiling_value) is not int:
                    continue
                raised = dataclasses.replace(PROFILE_LIMITS[profile], **{field.name: ceiling_value + 1})
                with self.subTest(field=field.name, profile=profile):
                    image = parse_macho(stub_image((bl_stub(1) + (RET,),), [THROWING])[0],
                                        limits=PROFILE_LIMITS[profile])
                    with self.assertRaises(InputError) as caught:
                        recover_swift_broad_flow(image, raised, profile=profile)
                    self.assertEqual((caught.exception.code, str(caught.exception)), ('swift_broad_limit', message))
                    with self.assertRaises(InputError) as caught:       # refused before any input is read
                        recover_swift_broad_flow_path('absent-input.macho', limits=raised, profile=profile)
                    self.assertEqual((caught.exception.code, str(caught.exception)), ('swift_broad_limit', message))
        self.assertEqual(CEILING.max_total_evidence, 8192)


class FailClosedTests(unittest.TestCase):
    def test_c14_unselected_partition_undercount_fails_closed(self):
        """The partition counter forgets its first unselected call: A5, and no report is returned."""
        imports = (Import(NON_SWIFT), Import(THROWING))
        data = build_stub_image(callers=((('bl', ('stub', 0)), ('bl', ('stub', 1)), RET),), imports=imports)[0]
        real = accounting.UnselectedPartition.classify
        state = {'skipped': False}

        def classify(partition, outcome):
            if outcome != 'selected' and not state['skipped']:
                state['skipped'] = True
                return None
            return real(partition, outcome)

        with mock.patch.object(accounting.UnselectedPartition, 'classify', classify):
            with self.assertRaises(Exception) as caught:
                run(data)
        self.assertTrue(state['skipped'], 'the patched counter was never reached')
        self.assertRegex(str(caught.exception), r'^A5\b')

    def test_c14_cause_ledger_overcount_fails_closed(self):
        """The cause ledger is one too high when the engine hands the report to the checker: A2."""
        data = stub_image((bl_stub(1) + (RET,),), [THROWING])[0]
        real = accounting.check_broad_v4_report

        def overcount(report):
            bad = copy.deepcopy(report)
            bad['omission_causes']['analysis_work_budget'] += 1
            return real(bad)

        with contextlib.ExitStack() as stack:
            targets = airs_modules('check_broad_v4_report')
            self.assertTrue(targets)
            for module in targets:
                stack.enter_context(mock.patch.object(module, 'check_broad_v4_report', overcount))
            with self.assertRaises(Exception) as caught:
                run(data)
        self.assertRegex(str(caught.exception), r'^A2\b')

    def test_c15_determinism(self):
        for name, data in (('stub', mixed_image()), ('got', kinds_got_image()), ('partition', partition_image())):
            with self.subTest(image=name):
                first, second = dumps(run(data)), dumps(run(data))
                self.assertEqual(first.encode(), second.encode())


class SizeTests(unittest.TestCase):
    def test_c16_worst_case_size(self):
        """The largest legal report the engine builds from 4096 callers making 2 calls each to 4096 distinct symbols.

        The contract's counts cannot all be reached together: 8192 rows of this size cost more than the output
        budget (REPORT_BYTES less the slack and the table reserve), and 4096 table entries of 512 bytes of overhead
        plus the symbol exceed the 2 MiB reserve. The test therefore asserts what the engine owes at the edge:
        every candidate is retained or omitted, only output_budget may omit, the table holds exactly the symbols
        that fit the byte reserve in first-seen order, and the encoded report stays inside every bound of the native
        decoder. The decoder counts every value and every key as a node, with the root at depth 0 and children and
        keys one deeper, so the asserted node total includes keys; the contract's count without keys is reported
        beside it. The totals found are printed once for the record.
        """
        rep, names = worst_case_report()
        selected = rep['selected_call_candidates']
        self.assertEqual(selected, 8192)
        self.assertEqual(len(rep['calls']) + rep['omitted_calls'], selected)
        self.assertEqual(rep['omission_causes']['total_row_limit'], 0)
        self.assertEqual(rep['omission_causes']['per_function_limit'], 0)
        self.assertEqual(rep['omission_causes']['analysis_work_budget'], 0)
        self.assertEqual(rep['omission_causes']['output_budget'], rep['omitted_calls'])
        table = rep['import_calls']
        symbol_cost = accounting.ENTRY_OVERHEAD_BYTES + len(table['entries'][0]['symbol'].encode('utf-8'))
        admitted = min(accounting.IMPORT_TABLE_MAX_ENTRIES, accounting.IMPORT_TABLE_BYTE_RESERVE // symbol_cost)
        self.assertEqual(len(table['entries']), admitted)
        self.assertEqual({norm(e['symbol']) for e in table['entries']}, {norm(n) for n in names[:admitted]})
        self.assertEqual((table['residual']['symbols'], table['distinct_symbols']), (4096 - admitted, 4096))
        self.assertEqual(table['attributed_calls'], 8192)
        self.assertIs(table['complete'], admitted == 4096)
        encoded = dumps(rep).encode('utf-8')
        found = measure(rep)
        sys.stderr.write('C16 record: rows %d, omitted %d, entries %d, nodes %d (with keys %d), depth %d, '
                         'longest string %d, bytes %d\n' % (len(rep['calls']), rep['omitted_calls'], admitted,
                                                            found['values'], found['nodes_with_keys'],
                                                            found['depth'], found['longest_string'], len(encoded)))
        self.assertLessEqual(found['nodes_with_keys'], NODE_LIMIT, found)
        self.assertLessEqual(found['values'], NODE_LIMIT, found)
        self.assertLessEqual(found['depth'], DEPTH_LIMIT, found)
        self.assertLessEqual(found['longest_string'], STRING_LIMIT, found)
        self.assertLessEqual(len(encoded), BYTES_LIMIT)

    def test_c17_compact_record_is_why_the_budget_holds(self):
        """Informational: rows carrying the full grammar identity are larger than the compact rows.

        Asserts only that the compact variant is smaller than the full-identity variant, in nodes and in bytes
        (factor above 1.0); the ratios are in the failure message and the test does not claim a specific failure.
        """
        rep, _ = worst_case_report()
        full = copy.deepcopy(rep)
        for row in full['calls']:
            holder = row if 'declaration' in row else row['admission']
            identity = real_parse(row['admission']['symbol']).identity
            holder['declaration'] = identity.to_json() if identity is not None else None
        compact_size, full_size = measure(rep), measure(full)
        compact_bytes = len(json.dumps(rep, sort_keys=True, indent=2, ensure_ascii=True))
        full_bytes = len(json.dumps(full, sort_keys=True, indent=2, ensure_ascii=True))
        message = 'nodes %s -> %s, bytes %d -> %d' % (compact_size['nodes_with_keys'], full_size['nodes_with_keys'],
                                                      compact_bytes, full_bytes)
        self.assertGreater(full_size['nodes_with_keys'], compact_size['nodes_with_keys'], message)
        self.assertGreater(full_bytes, compact_bytes, message)


class OwnedFixtureTests(unittest.TestCase):
    """The owned fixture against the independent expectation expected-v4.json; the expectation is never regenerated."""

    @classmethod
    def setUpClass(cls):
        cls.report = fixture_report(PROFILE)
        cls.expected = EXPECTED

    def expected_entry(self, symbol):
        sites = symbol['call_sites']
        calls = len(sites)
        base = dict(symbol=symbol['symbol'], calls=calls, stub_calls=sum(s['route'] == 'stub' for s in sites),
                    got_calls=sum(s['route'] == 'got' for s in sites), omitted=0)
        if not symbol['swift']:
            return dict(base, decision='not_swift', reason=None, retained=0, skipped_non_throwing=0,
                        not_swift_calls=calls)
        skipped = calls if symbol['decision'] == 'non_throwing' else 0
        return dict(base, decision=symbol['decision'], reason=symbol['reason'], retained=calls - skipped,
                    skipped_non_throwing=skipped, not_swift_calls=0)

    def test_c18_owned_fixture_against_the_independent_expectation(self):
        rep, exp = self.report, self.expected
        with self.subTest('envelope'):
            self.assertEqual((rep['profile'], rep['model_version']), (exp['profile'], exp['report_model_version']))
            self.assertEqual(rep['capabilities']['effect_admission_model'], exp['effect_admission_model'])
            self.assertEqual((rep['capabilities']['declaration_syntax_model'], rep['capabilities']['grammar_pin']),
                             (exp['grammar']['model'], exp['grammar']['pin']))
        with self.subTest('scan'):
            for key in accounting.SCAN_KEYS:
                self.assertEqual(rep['scan'][key], exp['scan'][key], key)
            self.assertIs(rep['word_scan_complete'], exp['scan']['word_scan_complete'])
            self.assertEqual(rep['scanned_words'], exp['scan']['scanned_words'])
            self.assertEqual(rep['scan']['functions_excluded_boundary'], exp['scan']['functions_excluded_boundary'])
        with self.subTest('counters'):
            for key in ('observed_call_instructions', 'selected_call_candidates', 'unselected_call_counts',
                        'omission_causes', 'omitted_calls', 'omitted_by_kind'):
                self.assertEqual(rep[key], exp[key], key)
            self.assertEqual(rep['unselected_call_counts']['other'], 0)
            self.assertIs(rep['call_details_complete'], exp['call_details_complete_from_omission'])
            self.assertEqual(len(rep['calls']), exp['calls_rows_expected'])
        with self.subTest('table'):
            table = rep['import_calls']
            self.assertEqual((table['complete'], table['attributed_calls'], table['attributed_swift_calls'],
                              table['distinct_symbols']),
                             (True, exp['counts']['attributed_calls'], exp['counts']['attributed_swift_calls'],
                              exp['counts']['distinct_symbols_attributed']))
            self.assertEqual(table['residual']['symbols'], 0)
            self.assertEqual(table['residual']['calls'], 0)
            self.assertEqual([e['symbol'] for e in table['entries']], [s['symbol'] for s in exp['symbols']])
            derived = [self.expected_entry(s) for s in exp['symbols']]
            self.assertEqual(sum(e['retained'] for e in derived), exp['counts']['retained_import_rows'])
            self.assertEqual(sum(e['skipped_non_throwing'] for e in derived), exp['counts']['skipped_non_throwing'])
            for entry, want in zip(table['entries'], derived):
                with self.subTest(symbol=want['symbol']):
                    self.assertEqual(entry, want)
            swift = [e for e in table['entries'] if e['decision'] != 'not_swift']
            self.assertEqual(len(swift), exp['counts']['distinct_swift_symbols'])
            self.assertEqual(sum(e['stub_calls'] for e in swift if e['decision'] != 'not_swift'
                                 ) + sum(e['got_calls'] for e in swift), exp['counts']['attributed_swift_calls'])
        with self.subTest('grid and summary'):
            self.assertEqual(rep['decision_by_shape'], exp['decision_by_shape'])
            self.assertEqual(rep['decision_summary'], dict(names=exp['decision_summary']['names'],
                                                           undecided_by_reason=exp['decision_summary'][
                                                               'undecided_by_reason']))
            totals = {shape: sum(cells[shape] for cells in rep['decision_by_shape'].values())
                      for shape in accounting.SHAPES}
            self.assertEqual(totals, dict(swifterror_idiom=0, postcall_test_only=2, precall_zero_only=0, none=25))
            # conflict and corroborated stay 0 here because the fixture has no swifterror_idiom site.
            relations = [row_field(row, 'effect_admission')['caller_relation'] for row in import_rows(rep)]
            self.assertEqual(relations.count('conflict') + relations.count('corroborated'), 0)
        with self.subTest('rows'):
            rows = import_rows(rep)
            self.assertEqual(len(rows), exp['calls_rows_import'])
            by_pc = {pc_of(row['call_pc']): row for row in rows}
            self.assertEqual(set(by_pc), {int(r['call_pc'], 16) for r in exp['import_rows']})
            symbols = {s['symbol']: s for s in exp['symbols']}
            for want in exp['import_rows']:
                with self.subTest(pc=want['call_pc']):
                    row = by_pc[int(want['call_pc'], 16)]
                    admission = row['admission']
                    self.assertEqual(admission['call_kind'], want['call_kind'])
                    self.assertEqual(norm(admission['symbol']), norm(want['symbol']))
                    if 'callee_stub_pc' in admission:
                        self.assertEqual(pc_of(admission['callee_stub_pc']), int(want['callee_stub_pc'], 16))
                    self.assertEqual(row['caller_error_test']['shape'], want['shape'])
                    self.assertEqual((admission['status'], admission['reason']), (want['status'], want['reason']))
                    effect = row_field(row, 'effect_admission')
                    self.assertEqual(effect, dict(model=exp['effect_admission_model'],
                                                  licence_class=want['licence_class'],
                                                  caller_relation=want['caller_relation']))
                    self.assertIsNone(row.get('candidate'))
                    self.assertIsNone(row.get('validation'))
                    self.assertNotEqual(symbols[want['symbol']]['decision'], 'non_throwing')
                    self.check_declaration(row_field(row, 'declaration'), symbols[want['symbol']])
            reasons = {}
            for row in rows:
                reasons[row['admission']['reason']] = reasons.get(row['admission']['reason'], 0) + 1
            self.assertEqual(reasons, {k: v for k, v in exp['reason_counts_import_rows'].items() if v})
            self.assertEqual({row['admission']['status'] for row in rows}, {'unresolved'})

    def check_declaration(self, declaration, symbol):
        wanted = symbol['expected_compact_declaration']
        self.assertEqual(declaration['syntax_model'], 'swift-declaration-syntax-v2')
        self.assertEqual(declaration['decision'], symbol['decision'])
        self.assertEqual(declaration['reason'], symbol['reason'])
        for key in ('entity', 'throws', 'is_async', 'typed_throws'):
            self.assertEqual(declaration[key], wanted[key], key)
        if wanted['identity_sha256'] is None:
            self.assertIsNone(declaration['identity_sha256'])
        else:                                    # the expectation does not record the digest (open question Q5)
            self.assertRegex(declaration['identity_sha256'], r'^[0-9a-f]{64}$')

    def test_c19_golden_report_byte_for_byte(self):
        if not GOLDEN.is_file():
            self.skipTest('report-v4.golden.json is not committed yet (the integrator supplies it)')
        self.assertEqual(dumps(self.report).encode(), GOLDEN.read_bytes())

    def test_c20_existing_counters_are_unchanged_against_v3(self):
        """Every v3 field has its v3 value in v4, except the fields the contract changes.

        Allowed differences: profile and model_version, the v4-only groups (not present in v3), on import rows the
        declaration (first-generation record in v3, compact record in v4) and effect_admission, and three changes the
        contract itself makes (integration fix: the first version of this test allowed only the marker):
        analysis_work gains the parse charge, once per distinct Swift symbol (contract 4.1, 16 plus the symbol length
        each); a declared_error_exit row gets the reason imported_callee_outcome_unmodeled in place of
        imported_callee_abi_unqualified (contract 4.5 table); and reason_counts moves accordingly, without the
        excluded_boundary marker. Compared per top-level key and per row so that a failure names the field.
        """
        v3, v4 = fixture_report(V3_PROFILE), self.report
        self.assertEqual(set(v3) - set(v4), set())
        for key in sorted(v3):
            if key in ('profile', 'model_version', 'calls', 'analysis_work', 'reason_counts'):
                continue
            with self.subTest(field=key):
                self.assertEqual(v4[key], v3[key])
        swift = {entry['symbol'] for entry in v4['import_calls']['entries'] if norm(entry['symbol']).startswith('$s')}
        with self.subTest(field='analysis_work'):
            self.assertEqual(len(swift), EXPECTED['counts']['distinct_swift_symbols'])
            self.assertEqual(v4['analysis_work'] - v3['analysis_work'], sum(16 + len(sym) for sym in swift))
        self.assertEqual(len(v4['calls']), len(v3['calls']))
        moved = 0
        for old, new in zip(v3['calls'], v4['calls']):
            with self.subTest(pc=old['call_pc']):
                left, right = copy.deepcopy(old), copy.deepcopy(new)
                effect = new.get('effect_admission') or new['admission'].get('effect_admission')   # indirect rows have none
                declared = effect is not None and effect['licence_class'] == 'declared_error_exit'
                for row in (left, right):
                    row.pop('declaration', None)
                    row.pop('effect_admission', None)
                    row['admission'].pop('declaration', None)
                    row['admission'].pop('effect_admission', None)
                if declared:
                    self.assertEqual(left['admission']['reason'], 'imported_callee_abi_unqualified')
                    self.assertEqual(right['admission']['reason'], 'imported_callee_outcome_unmodeled')
                    left['admission']['reason'] = right['admission']['reason']
                    moved += 1
                self.assertEqual(right, left)
        with self.subTest(field='reason_counts'):
            wanted = dict(v3['reason_counts'])
            wanted.pop('excluded_boundary', None)
            if moved:
                wanted['imported_callee_abi_unqualified'] -= moved
                wanted['imported_callee_outcome_unmodeled'] = moved
            self.assertEqual(moved, EXPECTED['licence_counts']['by_call']['declared_error_exit'])
            self.assertEqual(v4['reason_counts'], wanted)


if __name__ == '__main__':
    unittest.main()
