"""Tests for the accounting library and the report checker of profile broad-extended-v4 (group B).

Written from the design contract and its test list alone, before the module exists. Every input is built by hand: no
engine run, no image, no fixture. Run like the other engine tests: PYTHONPATH=src python3 -m unittest.

Interface assumed for airs.swift_broad_accounting
=================================================

Module constants (the builders read these module attributes when they are CONSTRUCTED, so a test patches them with
unittest.mock.patch.object on the module before it builds a table):

    IMPORT_TABLE_MAX_ENTRIES = 4096          # at most this many table entries
    IMPORT_TABLE_BYTE_RESERVE = 2 * 1024 * 1024
    ENTRY_OVERHEAD_BYTES = 512               # an entry reserves ENTRY_OVERHEAD_BYTES + len(symbol.encode('ascii'))

split_scan(functions, per_function_ceiling, total_ceiling) -> dict
    functions: iterable of (size_in_bytes: int, from_function_starts: bool), evaluated in the order given.
    A function is excluded for its boundary when from_function_starts is false, or size <= 0, or size % 4 != 0
    (its words are max(size, 0) // 4). Otherwise, with words = size // 4 and remaining = total_ceiling minus the
    words decoded so far: count = min(words, per_function_ceiling, remaining);
    unscanned_per_function_ceiling = words - min(words, per_function_ceiling);
    unscanned_total_ceiling = min(words, per_function_ceiling) - count.
    Returns a dict with exactly these keys:
        'functions': list, one dict per input function in input order, each with exactly the keys
                     'decoded', 'unscanned_per_function_ceiling', 'unscanned_total_ceiling', 'excluded_boundary'
        'scan': the scan block of contract 5.2, exactly the keys words_total, words_scanned,
                words_unscanned_per_function_ceiling, words_unscanned_total_ceiling, words_excluded_boundary,
                functions_total, functions_excluded_boundary, functions_truncated, candidates_in_unscanned_words,
                candidates_in_unscanned_words_reason
                (functions_truncated counts non-excluded functions with any unscanned word;
                candidates_in_unscanned_words is the integer 0 with reason None when every not-decoded count (both ceilings
                and the boundary-excluded words) is 0, otherwise None with reason 'words_not_decoded')
        'word_scan_complete': bool  (True exactly when functions_truncated == 0 and functions_excluded_boundary == 0)
        'scanned_words': int        (the decoded count, the value of the engine's existing scanned_words counter)

UnselectedPartition()
    .observe()          a call instruction was observed (a branch inside the same function is never observed)
    .classify(outcome)  one observed call was resolved; outcome is 'selected' or one of the five bucket names
                        'skipped_non_throwing', 'non_swift_import', 'declined_stub',
                        'direct_target_not_swift_function', 'direct_target_unattributed';
                        any other outcome raises ValueError
    .counts() -> {'observed_call_instructions': int, 'selected_call_candidates': int,
                  'unselected_call_counts': {the five buckets and 'other'}}
    'other' is the remainder: observed minus selected minus the five buckets. It is never forced to 0, so a call that
    was observed and never classified shows up as other == 1 (the checker then refuses it, rule A5).

ImportCallTable()
    .record(symbol, via, decision, reason, outcome, shape=None)
        symbol: attributed symbol string; via: 'stub' or 'got';
        decision: 'non_throwing', 'throwing', 'async', 'undecided' or 'not_swift';
        reason: None, or the grammar reason when decision is 'undecided';
        outcome: 'retained', 'skipped_non_throwing', 'not_swift' or 'omitted' (any omission cause is 'omitted');
        shape: one of the four caller-error-test shapes for a Swift site, None for a not_swift site.
        One call per attributed call, in scan (address) order. Admission is first-seen while both bounds hold:
        len(entries) < IMPORT_TABLE_MAX_ENTRIES and the running reserve
        (sum of ENTRY_OVERHEAD_BYTES + len(symbol) over admitted entries) <= IMPORT_TABLE_BYTE_RESERVE.
        A symbol that overflowed stays overflowed; its calls go to the residual.
    .import_calls(word_scan_complete) -> dict, the import_calls block of contract 5.2:
        {'complete', 'attributed_calls', 'attributed_swift_calls', 'distinct_symbols', 'entries', 'residual'}
        entries: sorted by symbol (str order); each exactly {symbol, decision, reason, calls, stub_calls, got_calls,
        retained, skipped_non_throwing, not_swift_calls, omitted}
        residual: exactly {symbols, calls, retained, skipped_non_throwing, not_swift_calls, omitted}
        complete: residual['symbols'] == 0 and word_scan_complete
    .decision_by_shape() -> {decision: {shape: count}}, all 16 cells present, counts every Swift site (retained,
        skipped, omitted, listed or residual), never the not_swift sites
    .decision_summary() -> {'names': {the four decisions: distinct Swift symbols}, 'undecided_by_reason':
        {reason: {'names': int, 'calls': int}}}, over all distinct Swift symbols (listed or residual); only reasons
        that occur are keys

check_broad_v4_report(report) -> None
    Failure form chosen for this whole file: it RAISES ValueError (a subclass is allowed) whose message starts with
    the rule id of contract 5.2 followed by a colon and a space, for example "A2: omitted_calls ...". It returns None
    on success and never mutates its argument. Structural presence (E2: v4 groups present exactly under the v4 pair;
    E1: capabilities equal to the fixed strings and limits complete) is checked before the arithmetic rules, so a
    missing group is reported as E2 or E1 and never as KeyError. Then the rules run in the order A1..A6, B1..B3,
    C1..C7, D1..D4 and the first violated rule is the one reported.

Report rows assumed by the hand-built reports (the existing row layout, plus the v4 fields):
    row = {'caller_pc', 'call_pc', 'candidate', 'validation',
           'admission': {'status', 'reason', 'call_kind' ('bl', 'b' for a tail branch, 'blr_got'), 'symbol',
                         'declaration': the 8-key compact record of contract 5.3},
           'caller_error_test': {'shape': ...},
           'effect_admission': {'model', 'licence_class', 'caller_relation'}}
    An import row is a row that carries 'effect_admission'. Rows of other kinds (an indirect candidate, a
    value-witness row with row['value_witness_admission'] = {'admitted', 'symbol', ...}) carry neither
    'effect_admission' nor a compact declaration. D4: an import row with a non-None 'candidate' or 'validation',
    or with an 'abi' key at row level or inside 'admission', is refused.
"""
import contextlib
import copy
import hashlib
import sys
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent))

from airs import swift_broad_accounting as accounting  # noqa: E402
from airs.swift_broad_accounting import (ImportCallTable, UnselectedPartition,  # noqa: E402
                                         check_broad_v4_report, split_scan)

V4_PROFILE = 'broad-extended-v4'
V4_MODEL = 'swift-broad-error-flow-extended-v4'
V3_PROFILE = 'broad-extended-v3'
V3_MODEL = 'swift-broad-error-flow-extended-v3'
SYNTAX_V2 = 'swift-declaration-syntax-v2'
SYNTAX_V1 = 'swift-import-declaration-syntax-v1'
EFFECT_MODEL = 'swift-import-effect-admission-v1'
GRAMMAR_PIN = 'swift-6.4.2-RELEASE'
CALLER_MODEL = 'swift-caller-error-test-v1'
PREMISES = ['symbol_name_carries_effects', 'no_silgen_name_override', 'name_only_attribution',
            'binding_not_proven', 'grammar_pinned']
NOT_CLAIMED = ['callee_returns', 'dyld_binding', 'runtime_callee', 'arguments_and_results',
               'error_value_at_runtime']
CAUSES = ('analysis_work_budget', 'per_function_limit', 'total_row_limit', 'output_budget')
KINDS = ('import_stub', 'import_got', 'local_swift_direct', 'indirect')
BUCKETS = ('skipped_non_throwing', 'non_swift_import', 'declined_stub', 'direct_target_not_swift_function',
           'direct_target_unattributed')
DECISIONS = ('non_throwing', 'throwing', 'async', 'undecided')
SHAPES = ('swifterror_idiom', 'postcall_test_only', 'precall_zero_only', 'none')
UNDECIDED_REASONS = ('invalid_input', 'thunk_or_specialization', 'unknown_substitution', 'truncated',
                     'malformed_symbol', 'trailing_input', 'unsupported_production', 'limit_exceeded',
                     'typed_throws', 'accessor', 'not_function_entity')
V4_GROUPS = ('capabilities', 'limits', 'omission_causes', 'omitted_by_kind', 'unselected_call_counts', 'scan',
             'import_calls', 'decision_by_shape', 'decision_summary')
ENTRY_KEYS = {'symbol', 'decision', 'reason', 'calls', 'stub_calls', 'got_calls', 'retained',
              'skipped_non_throwing', 'not_swift_calls', 'omitted'}
RESIDUAL_KEYS = {'symbols', 'calls', 'retained', 'skipped_non_throwing', 'not_swift_calls', 'omitted'}

SYM_NONTHROWING = '_$s4Test3bazyyF'
SYM_THROWING = '_$s4Test3fooyS2iKF'
SYM_ACCESSOR = '_$s4Test5ThingV5valueSivg'
SYM_ASYNC = '_$s4Test5fetchyyYaF'
SYM_RUNTIME = '_swift_retain'


# ---------------------------------------------------------------------------------------------------------------
# Hand-built report helpers (contract 5.1 to 5.3 only; no engine output)
# ---------------------------------------------------------------------------------------------------------------

def sha(label):
    return hashlib.sha256(label.encode('ascii')).hexdigest()


def decided_record(decision, label, *, reason=None, entity='function', throws=False, is_async=False,
                   typed_throws='none'):
    return {'syntax_model': SYNTAX_V2, 'decision': decision, 'reason': reason, 'entity': entity,
            'throws': throws, 'is_async': is_async, 'typed_throws': typed_throws,
            'identity_sha256': sha(label)}


def zero_grid():
    return {d: {s: 0 for s in SHAPES} for d in DECISIONS}


def import_row(n, symbol, record, licence, relation, shape, call_kind, reason):
    return {
        'caller_pc': hex(0x100001000 + 0x100 * n), 'call_pc': hex(0x100001010 + 0x100 * n),
        'candidate': None, 'validation': None,
        'admission': {'status': 'unresolved', 'reason': reason, 'call_kind': call_kind, 'symbol': symbol,
                      'declaration': dict(record)},
        'caller_error_test': {'shape': shape},
        'effect_admission': {'model': EFFECT_MODEL, 'licence_class': licence, 'caller_relation': relation},
    }


def indirect_row(caller_pc, call_pc):
    return {'caller_pc': caller_pc, 'call_pc': call_pc, 'candidate': None, 'validation': None,
            'admission': {'status': 'unresolved', 'reason': 'indirect_target_unresolved', 'call_kind': 'blr'}}


def entry(symbol, decision, reason, stub, got, retained, skipped, not_swift, omitted):
    return {'symbol': symbol, 'decision': decision, 'reason': reason, 'calls': stub + got, 'stub_calls': stub,
            'got_calls': got, 'retained': retained, 'skipped_non_throwing': skipped,
            'not_swift_calls': not_swift, 'omitted': omitted}


def blank_report():
    """A valid v4 report with zero rows, zero entries, a zero residual and a complete scan."""
    return {
        'profile': V4_PROFILE, 'model_version': V4_MODEL,
        'calls': [], 'selected_call_candidates': 0, 'omitted_calls': 0, 'observed_call_instructions': 0,
        'call_details_complete': True, 'outcome_witnesses_complete': True, 'word_scan_complete': True,
        'scanned_words': 0, 'reason_counts': {}, 'status_counts': {},
        'capabilities': {'report_model': V4_MODEL, 'effect_admission_model': EFFECT_MODEL,
                         'declaration_syntax_model': SYNTAX_V2, 'grammar_pin': GRAMMAR_PIN,
                         'caller_error_test_model': CALLER_MODEL,
                         'premises': list(PREMISES), 'not_claimed': list(NOT_CLAIMED)},
        # Only max_total_evidence, max_observations_per_function, import_table_entries and
        # import_table_byte_reserve are fixed by the contract; the other values are illustrative.
        'limits': {'max_total_evidence': 8192, 'max_observations_per_function': 256,
                   'max_instructions_per_function': 4096, 'max_total_instructions': 1000000,
                   'analysis_work_ceiling': 2000000, 'output_budget_bytes': 14614528,
                   'import_table_entries': 4096, 'import_table_byte_reserve': 2097152},
        'omission_causes': {k: 0 for k in CAUSES},
        'omitted_by_kind': {k: 0 for k in KINDS},
        'unselected_call_counts': {**{k: 0 for k in BUCKETS}, 'other': 0},
        'scan': {'words_total': 0, 'words_scanned': 0, 'words_unscanned_per_function_ceiling': 0,
                 'words_unscanned_total_ceiling': 0, 'words_excluded_boundary': 0, 'functions_total': 0,
                 'functions_excluded_boundary': 0, 'functions_truncated': 0,
                 'candidates_in_unscanned_words': 0, 'candidates_in_unscanned_words_reason': None},
        'import_calls': {'complete': True, 'attributed_calls': 0, 'attributed_swift_calls': 0,
                         'distinct_symbols': 0, 'entries': [],
                         'residual': {k: 0 for k in sorted(RESIDUAL_KEYS)}},
        'decision_by_shape': zero_grid(),
        'decision_summary': {'names': {d: 0 for d in DECISIONS}, 'undecided_by_reason': {}},
    }


def valid_report():
    """A fully populated valid v4 report: 7 rows (6 import rows, 1 indirect row), 5 entries, residual 0, scan complete.

    Arithmetic, by hand:
      rows 7 = selected 7, omitted 0. Unselected: skipped 3, non_swift 4, declined_stub 1, direct_not_swift 1,
      direct_unattributed 2, other 0. observed = 7 + 3 + 4 + 1 + 1 + 2 = 18.
      Entries (calls): baz 4 (3 stub + 1 got: 1 retained conflict row, 3 skipped), foo 3 (3 retained), Thing 1,
      fetch 1, _swift_retain 4 (not_swift). attributed_calls 13, Swift 9, distinct 5.
      Grid: throwing idiom 1 / none 2; non_throwing idiom 1 / postcall 1 / none 2; async none 1;
      undecided precall_zero_only 1 (sum 9).
    """
    report = blank_report()
    rec_throwing = decided_record('throwing', SYM_THROWING, throws=True)
    rec_nonthrowing = decided_record('non_throwing', SYM_NONTHROWING)
    rec_async = decided_record('async', SYM_ASYNC, is_async=True)
    rec_accessor = decided_record('undecided', SYM_ACCESSOR, reason='accessor', entity='getter')
    unmodeled, disagreement = 'imported_callee_outcome_unmodeled', 'declaration_caller_disagreement'
    report['calls'] = [
        import_row(0, SYM_THROWING, rec_throwing, 'declared_error_exit', 'corroborated', 'swifterror_idiom', 'bl',
                   unmodeled),
        import_row(1, SYM_THROWING, rec_throwing, 'declared_error_exit', 'no_signal', 'none', 'bl', unmodeled),
        import_row(2, SYM_THROWING, rec_throwing, 'declared_error_exit', 'not_applicable', 'none', 'b', unmodeled),
        import_row(3, SYM_NONTHROWING, rec_nonthrowing, 'no_error_exit', 'conflict', 'swifterror_idiom', 'bl',
                   disagreement),
        import_row(4, SYM_ASYNC, rec_async, 'refused_unsupported_effect', 'not_applicable', 'none', 'bl',
                   'imported_callee_effect_unsupported'),
        import_row(5, SYM_ACCESSOR, rec_accessor, 'none', 'not_applicable', 'precall_zero_only', 'bl',
                   'imported_callee_abi_unqualified'),
        indirect_row('0x100009000', '0x100009010'),
    ]
    report['selected_call_candidates'] = 7
    report['observed_call_instructions'] = 18
    report['reason_counts'] = {unmodeled: 3, disagreement: 1, 'imported_callee_effect_unsupported': 1,
                               'imported_callee_abi_unqualified': 1, 'indirect_target_unresolved': 1}
    report['status_counts'] = {'unresolved': 7}
    report['unselected_call_counts'] = {'skipped_non_throwing': 3, 'non_swift_import': 4, 'declined_stub': 1,
                                        'direct_target_not_swift_function': 1,
                                        'direct_target_unattributed': 2, 'other': 0}
    report['scan'].update(words_total=40, words_scanned=40, functions_total=3)
    report['scanned_words'] = 40
    entries = [
        entry(SYM_THROWING, 'throwing', None, 3, 0, 3, 0, 0, 0),
        entry(SYM_NONTHROWING, 'non_throwing', None, 3, 1, 1, 3, 0, 0),
        entry(SYM_ACCESSOR, 'undecided', 'accessor', 1, 0, 1, 0, 0, 0),
        entry(SYM_ASYNC, 'async', None, 1, 0, 1, 0, 0, 0),
        entry(SYM_RUNTIME, 'not_swift', None, 3, 1, 0, 0, 4, 0),
    ]
    report['import_calls'].update(complete=True, attributed_calls=13, attributed_swift_calls=9,
                                  distinct_symbols=5, entries=sorted(entries, key=lambda e: e['symbol']))
    grid = zero_grid()
    grid['throwing'].update(swifterror_idiom=1, none=2)
    grid['non_throwing'].update(swifterror_idiom=1, postcall_test_only=1, none=2)
    grid['async'].update(none=1)
    grid['undecided'].update(precall_zero_only=1)
    report['decision_by_shape'] = grid
    report['decision_summary'] = {'names': {'non_throwing': 1, 'throwing': 1, 'async': 1, 'undecided': 1},
                                  'undecided_by_reason': {'accessor': {'names': 1, 'calls': 1}}}
    return report


def entry_of(report, symbol):
    return next(e for e in report['import_calls']['entries'] if e['symbol'] == symbol)


def rows_of(report, symbol):
    return [r for r in report['calls'] if r['admission'].get('symbol') == symbol]


def add_indirect_rows(report, n, caller_pc='0x300000', per_caller=None):
    """Append n indirect rows, keeping every counter that the rows feed consistent."""
    for i in range(n):
        pc = caller_pc if per_caller is None else hex(0x400000 + (i // per_caller) * 0x1000)
        report['calls'].append(indirect_row(pc, hex(0x500000 + 4 * i)))
    report['selected_call_candidates'] += n
    report['observed_call_instructions'] += n
    report['reason_counts']['indirect_target_unresolved'] += n
    report['status_counts']['unresolved'] += n


def omit_one(report, cause='output_budget', kind='indirect', flags_false=True):
    """Add one omitted indirect candidate with its cause and kind, keeping every other rule consistent."""
    report['omitted_calls'] += 1
    report['omission_causes'][cause] += 1
    report['omitted_by_kind'][kind] += 1
    report['selected_call_candidates'] += 1
    report['observed_call_instructions'] += 1
    if flags_false:
        report['call_details_complete'] = False
        report['outcome_witnesses_complete'] = False


def make_scan_incomplete(report):
    """Valid incomplete scan: 40 words, 30 decoded, 6 + 4 unscanned, 2 of 3 functions truncated."""
    report['scan'].update(words_total=40, words_scanned=30, words_unscanned_per_function_ceiling=6,
                          words_unscanned_total_ceiling=4, words_excluded_boundary=0, functions_total=3,
                          functions_truncated=2, functions_excluded_boundary=0,
                          candidates_in_unscanned_words=None,
                          candidates_in_unscanned_words_reason='words_not_decoded')
    report['scanned_words'] = 30
    report['word_scan_complete'] = False
    report['call_details_complete'] = False
    report['outcome_witnesses_complete'] = False
    report['import_calls']['complete'] = False


def make_boundary_excluded(report):
    """Valid scan whose only gap is one function excluded for its boundary: no ceiling binds, 2 words not decoded."""
    report['scan'].update(words_total=42, words_scanned=40, words_unscanned_per_function_ceiling=0,
                          words_unscanned_total_ceiling=0, words_excluded_boundary=2, functions_total=4,
                          functions_truncated=0, functions_excluded_boundary=1,
                          candidates_in_unscanned_words=None,
                          candidates_in_unscanned_words_reason='words_not_decoded')
    report['word_scan_complete'] = False
    report['call_details_complete'] = False
    report['outcome_witnesses_complete'] = False
    report['import_calls']['complete'] = False


def with_residual(report, calls=2):
    """Valid table overflow: one extra Swift symbol (non_throwing, none shape) in the residual, all skipped."""
    ic = report['import_calls']
    ic['residual'] = {'symbols': 1, 'calls': calls, 'retained': 0, 'skipped_non_throwing': calls,
                      'not_swift_calls': 0, 'omitted': 0}
    ic['attributed_calls'] += calls
    ic['attributed_swift_calls'] += calls
    ic['distinct_symbols'] += 1
    ic['complete'] = False
    report['unselected_call_counts']['skipped_non_throwing'] += calls
    report['observed_call_instructions'] += calls
    report['decision_by_shape']['non_throwing']['none'] += calls
    report['decision_summary']['names']['non_throwing'] += 1


class CheckerCase(unittest.TestCase):
    def assertRule(self, rule, report):
        with self.assertRaises(ValueError) as caught:
            check_broad_v4_report(report)
        message = str(caught.exception)
        self.assertTrue(message.startswith(rule + ': '), 'expected rule %s, got %r' % (rule, message))

    def assertValid(self, report):
        self.assertIsNone(check_broad_v4_report(report))


@contextlib.contextmanager
def table_constants(entries=None, reserve=None, overhead=None):
    patches = []
    if entries is not None:
        patches.append(mock.patch.object(accounting, 'IMPORT_TABLE_MAX_ENTRIES', entries))
    if reserve is not None:
        patches.append(mock.patch.object(accounting, 'IMPORT_TABLE_BYTE_RESERVE', reserve))
    if overhead is not None:
        patches.append(mock.patch.object(accounting, 'ENTRY_OVERHEAD_BYTES', overhead))
    with contextlib.ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        yield


def build_table(calls):
    """calls: (symbol, via, decision, reason, outcome, shape) tuples, in scan order."""
    table = ImportCallTable()
    for symbol, via, decision, reason, outcome, shape in calls:
        table.record(symbol, via, decision, reason, outcome, shape)
    return table


def swift_call(symbol, outcome='skipped_non_throwing', via='stub', decision='non_throwing', reason=None,
               shape='none'):
    return (symbol, via, decision, reason, outcome, shape)


# ---------------------------------------------------------------------------------------------------------------
# B1 to B3: scan split
# ---------------------------------------------------------------------------------------------------------------

class ScanSplitTests(unittest.TestCase):
    B1_FUNCTIONS = [(64, True), (32, True), (48, True), (16, True), (40, False), (10, True), (0, True)]
    # decoded, unscanned by per-function ceiling, unscanned by total ceiling, excluded
    B1_TABLE = [(10, 6, 0, 0), (8, 0, 0, 0), (7, 2, 3, 0), (0, 0, 4, 0), (0, 0, 0, 10), (0, 0, 0, 2), (0, 0, 0, 0)]

    def test_b1_worked_example(self):
        """Per-function ceiling 10 words, total ceiling 25 words; F6 excludes 10 // 4 = 2 words."""
        result = split_scan(self.B1_FUNCTIONS, 10, 25)
        keys = ('decoded', 'unscanned_per_function_ceiling', 'unscanned_total_ceiling', 'excluded_boundary')
        self.assertEqual(len(result['functions']), 7)
        for index, (function, expected) in enumerate(zip(result['functions'], self.B1_TABLE), 1):
            with self.subTest(function='F%d' % index):
                self.assertEqual(set(function), set(keys))
                self.assertEqual(tuple(function[k] for k in keys), expected)
        scan = result['scan']
        self.assertEqual(scan, {
            'words_total': 52, 'words_scanned': 25, 'words_unscanned_per_function_ceiling': 8,
            'words_unscanned_total_ceiling': 7, 'words_excluded_boundary': 12, 'functions_total': 7,
            'functions_excluded_boundary': 3, 'functions_truncated': 3, 'candidates_in_unscanned_words': None,
            'candidates_in_unscanned_words_reason': 'words_not_decoded'})
        self.assertIs(result['word_scan_complete'], False)
        # Rule B1 holds: 25 + 8 + 7 + 12 = 52.
        self.assertEqual(scan['words_scanned'] + scan['words_unscanned_per_function_ceiling']
                         + scan['words_unscanned_total_ceiling'] + scan['words_excluded_boundary'],
                         scan['words_total'])

    def test_b1_every_word_is_classed_once_per_function(self):
        result = split_scan(self.B1_FUNCTIONS, 10, 25)
        for (size, _), function in zip(self.B1_FUNCTIONS, result['functions']):
            with self.subTest(size=size):
                self.assertEqual(sum(function.values()), size // 4)

    def test_b2_complete_scan(self):
        result = split_scan([(32, True)], 100, 100)
        scan = result['scan']
        self.assertEqual(result['functions'], [{'decoded': 8, 'unscanned_per_function_ceiling': 0,
                                                'unscanned_total_ceiling': 0, 'excluded_boundary': 0}])
        self.assertEqual((scan['words_total'], scan['words_scanned']), (8, 8))
        for key in ('words_unscanned_per_function_ceiling', 'words_unscanned_total_ceiling',
                    'words_excluded_boundary', 'functions_truncated', 'functions_excluded_boundary'):
            self.assertEqual(scan[key], 0, key)
        self.assertEqual(scan['functions_total'], 1)
        self.assertIs(result['word_scan_complete'], True)
        self.assertEqual(scan['candidates_in_unscanned_words'], 0)
        self.assertNotIsInstance(scan['candidates_in_unscanned_words'], bool)
        self.assertIsNone(scan['candidates_in_unscanned_words_reason'])

    def test_candidates_in_boundary_excluded_words_are_unknown(self):
        """Contract 4.7: words in a boundary-excluded function are not decoded, so candidates there are null."""
        for functions in ([(7, True)], [(8, False)], [(10, True), (32, True)], [(6, True), (8, False)]):
            with self.subTest(functions=functions):
                result = split_scan(functions, 100, 100)
                scan = result['scan']
                self.assertEqual(scan['functions_truncated'], 0)
                self.assertEqual((scan['words_unscanned_per_function_ceiling'],
                                  scan['words_unscanned_total_ceiling']), (0, 0))
                self.assertGreater(scan['functions_excluded_boundary'], 0)
                self.assertIs(result['word_scan_complete'], False)
                self.assertIsNone(scan['candidates_in_unscanned_words'])
                self.assertEqual(scan['candidates_in_unscanned_words_reason'], 'words_not_decoded')

    def test_b3_words_scanned_equals_the_decoded_counter(self):
        for name, functions, per_fn, total in (('b1', self.B1_FUNCTIONS, 10, 25), ('b2', [(32, True)], 100, 100)):
            with self.subTest(case=name):
                result = split_scan(functions, per_fn, total)
                decoded = sum(f['decoded'] for f in result['functions'])
                self.assertEqual(result['scan']['words_scanned'], result['scanned_words'])
                self.assertEqual(result['scanned_words'], decoded)

    def test_negative_size_is_excluded_with_zero_words(self):
        """Contract 4.7: an excluded function's words are max(size, 0) // 4."""
        result = split_scan([(-8, True), (8, True)], 10, 10)
        self.assertEqual(result['functions'][0], {'decoded': 0, 'unscanned_per_function_ceiling': 0,
                                                  'unscanned_total_ceiling': 0, 'excluded_boundary': 0})
        self.assertEqual(result['scan']['functions_excluded_boundary'], 1)
        self.assertEqual(result['scan']['words_total'], 2)
        self.assertIs(result['word_scan_complete'], False)


# ---------------------------------------------------------------------------------------------------------------
# B4, B5 (library side): unselected partition
# ---------------------------------------------------------------------------------------------------------------

class PartitionTests(unittest.TestCase):
    def test_b4_hand_built_partition(self):
        instructions = [
            ('call', 'skipped_non_throwing'),   # a non-throwing Swift import
            ('call', 'non_swift_import'),
            ('call', 'declined_stub'),
            ('call', 'direct_target_not_swift_function'),
            ('call', 'direct_target_unattributed'),
            ('call', 'selected'),
            ('call', 'selected'),
            ('branch', None),                   # a branch to an address inside the same function: not a call
        ]
        partition = UnselectedPartition()
        for kind, outcome in instructions:
            if kind == 'call':
                partition.observe()
                partition.classify(outcome)
        counts = partition.counts()
        self.assertEqual(counts['observed_call_instructions'], 7)
        self.assertEqual(counts['selected_call_candidates'], 2)
        self.assertEqual(counts['unselected_call_counts'],
                         {'skipped_non_throwing': 1, 'non_swift_import': 1, 'declined_stub': 1,
                          'direct_target_not_swift_function': 1, 'direct_target_unattributed': 1, 'other': 0})
        # The intra-function branch appears in no counter: 7 calls = 2 selected + 5 buckets.
        self.assertEqual(sum(counts['unselected_call_counts'].values()) + counts['selected_call_candidates'], 7)

    def test_b5_an_unclassified_call_is_other_not_hidden(self):
        partition = UnselectedPartition()
        partition.observe()
        partition.classify('selected')
        partition.observe()   # a call site that reached a continue without a counter
        counts = partition.counts()
        self.assertEqual(counts['observed_call_instructions'], 2)
        self.assertEqual(counts['unselected_call_counts']['other'], 1)

    def test_unknown_outcome_is_refused(self):
        partition = UnselectedPartition()
        partition.observe()
        with self.assertRaises(ValueError):
            partition.classify('somewhere_else')


# ---------------------------------------------------------------------------------------------------------------
# B6 to B12: import call table, grid, summary
# ---------------------------------------------------------------------------------------------------------------

class ImportTableTests(unittest.TestCase):
    def test_b6_entry_closure(self):
        """Symbol S: 3 stub and 2 GOT calls; 1 retained, 2 skipped, 1 omitted for the row limit, 1 for output."""
        s = '_$s4Test1SyyF'
        table = build_table([
            swift_call(s, 'retained', 'stub', shape='swifterror_idiom'),
            swift_call(s, 'skipped_non_throwing', 'stub'),
            swift_call(s, 'omitted', 'stub'),          # row limit
            swift_call(s, 'skipped_non_throwing', 'got'),
            swift_call(s, 'omitted', 'got'),           # output budget
        ])
        block = table.import_calls(True)
        (got,) = block['entries']
        self.assertEqual(set(got), ENTRY_KEYS)
        self.assertEqual(got, {'symbol': s, 'decision': 'non_throwing', 'reason': None, 'calls': 5,
                               'stub_calls': 3, 'got_calls': 2, 'retained': 1, 'skipped_non_throwing': 2,
                               'not_swift_calls': 0, 'omitted': 2})
        self.assertEqual(got['calls'], got['stub_calls'] + got['got_calls'])
        self.assertEqual(got['calls'], got['retained'] + got['skipped_non_throwing'] + got['not_swift_calls']
                         + got['omitted'])

    def test_b6_non_swift_symbol(self):
        table = build_table([(SYM_RUNTIME, 'stub', 'not_swift', None, 'not_swift', None)] * 4)
        (got,) = table.import_calls(True)['entries']
        self.assertEqual(got, {'symbol': SYM_RUNTIME, 'decision': 'not_swift', 'reason': None, 'calls': 4,
                               'stub_calls': 4, 'got_calls': 0, 'retained': 0, 'skipped_non_throwing': 0,
                               'not_swift_calls': 4, 'omitted': 0})

    def test_undecided_entry_carries_the_grammar_reason(self):
        table = build_table([swift_call(SYM_ACCESSOR, 'retained', decision='undecided', reason='accessor')])
        (got,) = table.import_calls(True)['entries']
        self.assertEqual((got['decision'], got['reason']), ('undecided', 'accessor'))

    def test_b7_overflow_by_entry_count(self):
        sequence = ['z1', 'a2', 'm3', 'b4', 'c5', 'c5', 'd6', 'z1', 'c5']
        with table_constants(entries=4):
            table = ImportCallTable()
            for symbol in sequence:
                outcome = 'retained' if symbol == 'd6' else 'skipped_non_throwing'
                table.record(symbol, 'stub', 'non_throwing', None, outcome, 'none')
            block = table.import_calls(True)
        self.assertEqual([e['symbol'] for e in block['entries']], ['a2', 'b4', 'm3', 'z1'])
        self.assertEqual({e['symbol']: e['calls'] for e in block['entries']},
                         {'a2': 1, 'b4': 1, 'm3': 1, 'z1': 2})   # the re-seen z1 increments its own entry
        residual = block['residual']
        self.assertEqual(set(residual), RESIDUAL_KEYS)
        self.assertEqual((residual['symbols'], residual['calls']), (2, 4))   # c5 x3 plus d6 x1
        self.assertEqual((residual['retained'], residual['skipped_non_throwing'],
                          residual['not_swift_calls'], residual['omitted']), (1, 3, 0, 0))
        self.assertEqual(block['distinct_symbols'], 6)
        self.assertEqual(block['attributed_calls'], sum(e['calls'] for e in block['entries']) + 4)
        self.assertEqual(block['attributed_calls'], len(sequence))
        self.assertIs(block['complete'], False)

    def test_b8_overflow_by_byte_reserve(self):
        s1, s2, s3 = 'sym_one_aa', 'sym_two_bbbb', 'sym_three_cccc'   # ASCII; len(s3) >= len(s2)
        l1, l2 = len(s1), len(s2)
        for reserve, admitted in ((1024 + l1 + l2, [s1, s2]), (1024 + l1 + l2 - 1, [s1])):
            with self.subTest(reserve_minus=(1024 + l1 + l2) - reserve):
                with table_constants(entries=1000, reserve=reserve, overhead=512):
                    table = build_table([swift_call(s) for s in (s1, s2, s3)])
                    block = table.import_calls(True)
                self.assertEqual([e['symbol'] for e in block['entries']], sorted(admitted))
                self.assertEqual(block['residual']['symbols'], 3 - len(admitted))
                self.assertEqual(block['residual']['calls'], 3 - len(admitted))

    def test_b8_presentation_order_decides_admission(self):
        x, y, z = 'sym_x_aaaa', 'sym_y_bbbbbb', 'sym_z_cccccccc'   # lengths 10, 12, 14
        with table_constants(entries=1000, reserve=1024 + len(x) + len(y), overhead=512):
            first = build_table([swift_call(s) for s in (x, y, z)]).import_calls(True)
            second = build_table([swift_call(s) for s in (z, x, y)]).import_calls(True)
        # After z (526 bytes) only 520 bytes remain, below the 522 bytes that x needs (y needs 524), so nothing else fits.
        self.assertEqual([e['symbol'] for e in first['entries']], [x, y])
        self.assertEqual(first['residual']['symbols'], 1)
        self.assertEqual([e['symbol'] for e in second['entries']], [z])
        self.assertEqual(second['residual']['symbols'], 2)

    def test_b9_complete(self):
        calls = [swift_call('a1'), swift_call('b2')]
        with table_constants(entries=1):
            overflowed = build_table(calls).import_calls(True)
        fits = build_table(calls)
        self.assertIs(fits.import_calls(True)['complete'], True)
        self.assertIs(fits.import_calls(False)['complete'], False)
        self.assertEqual(overflowed['residual']['symbols'], 1)
        self.assertIs(overflowed['complete'], False)

    def test_b10_calls_do_not_depend_on_the_row_limit(self):
        def calls(outcome):
            return [swift_call(SYM_THROWING, outcome, 'stub', 'throwing', shape='none'),
                    swift_call(SYM_THROWING, outcome, 'stub', 'throwing', shape='swifterror_idiom'),
                    swift_call(SYM_THROWING, outcome, 'got', 'throwing', shape='none'),
                    swift_call(SYM_NONTHROWING, 'skipped_non_throwing' if outcome == 'retained' else 'omitted'),
                    (SYM_RUNTIME, 'stub', 'not_swift', None, 'not_swift', None)]
        kept = build_table(calls('retained')).import_calls(True)['entries']
        dropped = build_table(calls('omitted')).import_calls(True)['entries']
        self.assertEqual(len(kept), len(dropped))
        for a, b in zip(kept, dropped):
            with self.subTest(symbol=a['symbol']):
                for key in ('symbol', 'decision', 'reason', 'calls', 'stub_calls', 'got_calls', 'not_swift_calls'):
                    self.assertEqual(a[key], b[key], key)
                for entry_ in (a, b):
                    self.assertEqual(entry_['calls'], entry_['stub_calls'] + entry_['got_calls'])
                    self.assertEqual(entry_['calls'], entry_['retained'] + entry_['skipped_non_throwing']
                                     + entry_['not_swift_calls'] + entry_['omitted'])
        throwing_kept = next(e for e in kept if e['symbol'] == SYM_THROWING)
        throwing_dropped = next(e for e in dropped if e['symbol'] == SYM_THROWING)
        self.assertEqual((throwing_kept['retained'], throwing_kept['omitted']), (3, 0))
        self.assertEqual((throwing_dropped['retained'], throwing_dropped['omitted']), (0, 3))

    B11_SITES = [
        ('a', 'stub', 'non_throwing', None, 'skipped_non_throwing', 'none'),
        ('b', 'stub', 'throwing', None, 'retained', 'swifterror_idiom'),
        ('c', 'got', 'async', None, 'omitted', 'postcall_test_only'),
        ('d', 'stub', 'undecided', 'accessor', 'retained', 'precall_zero_only'),
        ('e', 'stub', 'non_throwing', None, 'skipped_non_throwing', 'none'),
        ('_f', 'stub', 'not_swift', None, 'not_swift', None),   # not a Swift site: in no cell
    ]

    def test_b11_decision_grid(self):
        placed = {('non_throwing', 'none'): 2, ('throwing', 'swifterror_idiom'): 1,
                  ('async', 'postcall_test_only'): 1, ('undecided', 'precall_zero_only'): 1}
        grids = []
        for cap, outcome in ((4096, None), (1, None), (4096, 'omitted'), (1, 'omitted')):
            with self.subTest(cap=cap, outcome=outcome):
                sites = [s if outcome is None or s[4] == 'not_swift' else s[:4] + (outcome,) + s[5:]
                         for s in self.B11_SITES]
                with table_constants(entries=cap):
                    table = build_table(sites)
                    grid = table.decision_by_shape()
                    block = table.import_calls(True)
                self.assertEqual(set(grid), set(DECISIONS))
                for decision in DECISIONS:
                    self.assertEqual(set(grid[decision]), set(SHAPES))
                    for shape in SHAPES:
                        self.assertEqual(grid[decision][shape], placed.get((decision, shape), 0))
                self.assertEqual(sum(v for row in grid.values() for v in row.values()), 5)
                self.assertEqual(block['attributed_swift_calls'], 5)
                grids.append(grid)
        self.assertTrue(all(g == grids[0] for g in grids))

    def test_b12_decision_summary(self):
        calls = ([swift_call('n1')] * 2 + [swift_call('n2'), swift_call('n3')]
                 + [swift_call('t1', decision='throwing', outcome='retained')]
                 + [swift_call('t2', decision='throwing', outcome='retained')] * 3
                 + [swift_call('a1', decision='async', outcome='retained')]
                 + [swift_call('acc', decision='undecided', reason='accessor', outcome='retained')] * 2
                 + [swift_call('th', decision='undecided', reason='thunk_or_specialization',
                               outcome='retained')] * 4)
        for cap in (4096, 2):
            with self.subTest(cap=cap):
                with table_constants(entries=cap):
                    summary = build_table(calls).decision_summary()
                self.assertEqual(summary['names'], {'non_throwing': 3, 'throwing': 2, 'async': 1, 'undecided': 2})
                self.assertEqual(sum(summary['names'].values()), 8)
                self.assertEqual(summary['undecided_by_reason'],
                                 {'accessor': {'names': 1, 'calls': 2},
                                  'thunk_or_specialization': {'names': 1, 'calls': 4}})
                self.assertTrue(set(summary['undecided_by_reason']) <= set(UNDECIDED_REASONS))


# ---------------------------------------------------------------------------------------------------------------
# B13, B15: the checker accepts valid reports and leaves them alone
# ---------------------------------------------------------------------------------------------------------------

class CheckerAcceptTests(CheckerCase):
    def test_b13_valid_report_passes(self):
        report = valid_report()
        self.assertGreaterEqual(len(report['calls']), 2)
        self.assertGreaterEqual(len(report['import_calls']['entries']), 2)
        self.assertEqual(report['import_calls']['residual']['symbols'], 0)
        self.assertValid(report)

    def test_empty_valid_report_passes(self):
        self.assertValid(blank_report())

    def test_valid_incomplete_scan_passes(self):
        report = valid_report()
        make_scan_incomplete(report)
        self.assertValid(report)

    def test_valid_table_overflow_passes(self):
        report = valid_report()
        with_residual(report)
        self.assertValid(report)

    def test_valid_omissions_pass(self):
        for cause in ('analysis_work_budget', 'output_budget'):
            with self.subTest(cause=cause):
                report = valid_report()
                omit_one(report, cause)
                self.assertValid(report)

    def test_valid_per_function_limit_needs_a_caller_at_the_limit(self):
        report = valid_report()
        add_indirect_rows(report, 256)
        omit_one(report, 'per_function_limit')
        self.assertValid(report)

    def test_valid_total_row_limit_needs_the_row_limit_reached(self):
        report = valid_report()
        add_indirect_rows(report, 8192 - len(report['calls']), per_caller=128)
        omit_one(report, 'total_row_limit')
        self.assertEqual(len(report['calls']), report['limits']['max_total_evidence'])
        self.assertValid(report)

    def test_b15_checker_does_not_mutate_its_input(self):
        for name, report in (('valid', valid_report()), ('blank', blank_report())):
            with self.subTest(report=name):
                before = copy.deepcopy(report)
                check_broad_v4_report(report)
                self.assertEqual(report, before)
        bad = valid_report()
        bad['unselected_call_counts']['other'] = 1
        before = copy.deepcopy(bad)
        with self.assertRaises(ValueError):
            check_broad_v4_report(bad)
        self.assertEqual(bad, before)

    def test_checker_is_repeatable(self):
        report = valid_report()
        self.assertIsNone(check_broad_v4_report(report))
        self.assertIsNone(check_broad_v4_report(report))


# ---------------------------------------------------------------------------------------------------------------
# B5, B14: one mutation of the valid report per rule
# ---------------------------------------------------------------------------------------------------------------

class CheckerRuleTests(CheckerCase):
    # ---- A: row, cause, partition and limit arithmetic ----

    def test_a1_dropped_row(self):
        report = valid_report()
        report['calls'].pop()
        self.assertRule('A1', report)

    def test_a2_cause_and_kind_sums(self):
        report = valid_report()
        report['omission_causes']['output_budget'] += 1
        self.assertRule('A2', report)
        report = valid_report()
        report['omitted_by_kind']['indirect'] += 1
        self.assertRule('A2', report)

    def test_a3_omissions_with_complete_flags(self):
        for flag in ('call_details_complete', 'outcome_witnesses_complete'):
            with self.subTest(flag=flag):
                report = valid_report()
                omit_one(report)
                report[flag] = True
                self.assertRule('A3', report)
        report = valid_report()
        omit_one(report, flags_false=False)
        self.assertRule('A3', report)

    def test_a4_reason_counts_is_a_partition(self):
        report = valid_report()
        report['reason_counts']['excluded_boundary'] = 1
        self.assertRule('A4', report)
        report = valid_report()
        report['reason_counts']['indirect_target_unresolved'] += 1
        self.assertRule('A4', report)
        report = valid_report()
        report['status_counts']['unresolved'] += 1
        self.assertRule('A4', report)

    def test_a4_marker_alone_is_refused(self):
        """Move one count onto the marker so the sum still equals len(calls): only the marker is wrong."""
        report = valid_report()
        report['reason_counts']['indirect_target_unresolved'] -= 1
        report['reason_counts']['excluded_boundary'] = 1
        self.assertRule('A4', report)

    def test_a5_partition(self):
        report = valid_report()
        report['unselected_call_counts']['other'] = 1
        self.assertRule('A5', report)
        report = valid_report()
        report['observed_call_instructions'] += 1
        self.assertRule('A5', report)

    def test_b5_partition_negatives(self):
        """B5: the same two mutations, named as in the test list."""
        report = valid_report()
        report['unselected_call_counts']['other'] = 1
        self.assertRule('A5', report)
        report = valid_report()
        report['observed_call_instructions'] += 1
        self.assertRule('A5', report)

    def test_a6_total_row_limit_with_rows_below_the_limit(self):
        report = valid_report()
        omit_one(report, 'total_row_limit')
        self.assertLess(len(report['calls']), report['limits']['max_total_evidence'])
        self.assertRule('A6', report)

    def test_a6_retention_limit_is_not_raised(self):
        report = valid_report()
        report['limits']['max_total_evidence'] = 8193
        self.assertRule('A6', report)

    def test_a6_more_rows_than_the_per_function_limit(self):
        report = valid_report()
        add_indirect_rows(report, 257)
        self.assertRule('A6', report)

    def test_a6_per_function_limit_cause_needs_a_full_caller(self):
        report = valid_report()
        omit_one(report, 'per_function_limit')
        self.assertRule('A6', report)

    # ---- B: scan ----

    def test_b1_words_scanned(self):
        report = valid_report()
        report['scan']['words_scanned'] += 1
        self.assertRule('B1', report)

    def test_b1_words_scanned_must_equal_the_scanned_words_counter(self):
        report = valid_report()
        report['scanned_words'] -= 1     # words_scanned stays 40: the two disagree, the word sum still closes
        self.assertRule('B1', report)

    def test_b2_complete_flag_against_truncation(self):
        report = valid_report()
        report['scan']['functions_truncated'] = 1
        self.assertRule('B2', report)

    def test_b2_other_directions(self):
        report = valid_report()
        make_scan_incomplete(report)
        report['word_scan_complete'] = True      # unscanned words and truncated functions, yet complete
        self.assertRule('B2', report)
        report = valid_report()
        report['scan']['functions_excluded_boundary'] = 1
        self.assertRule('B2', report)
        report = valid_report()
        make_scan_incomplete(report)
        report['scan']['functions_truncated'] = 4   # more truncated functions than functions
        self.assertRule('B2', report)

    def test_b2_truncation_count_against_the_unscanned_ceiling_counts(self):
        """Second clause of B2: functions_truncated == 0 exactly when both unscanned-ceiling counts are 0."""
        report = valid_report()      # complete flag, truncated 0, excluded 0 agree; only the unscanned count differs
        report['scan'].update(words_unscanned_per_function_ceiling=2, words_total=42)
        self.assertRule('B2', report)
        report = valid_report()
        report['scan'].update(words_unscanned_total_ceiling=2, words_total=42)
        self.assertRule('B2', report)
        report = valid_report()      # truncated 1 and complete False agree, yet no word is unscanned
        report['scan']['functions_truncated'] = 1
        report['word_scan_complete'] = False
        self.assertRule('B2', report)

    def test_b3_boundary_excluded_words_are_unknown(self):
        report = valid_report()
        make_boundary_excluded(report)
        self.assertValid(report)
        report['scan']['candidates_in_unscanned_words'] = 0
        report['scan']['candidates_in_unscanned_words_reason'] = None
        self.assertRule('B3', report)
        report = valid_report()
        make_boundary_excluded(report)
        report['scan']['candidates_in_unscanned_words_reason'] = 'wrong_reason'
        self.assertRule('B3', report)

    def test_b3_candidates_in_unscanned_words(self):
        report = valid_report()
        make_scan_incomplete(report)
        report['scan']['candidates_in_unscanned_words'] = 0
        report['scan']['candidates_in_unscanned_words_reason'] = None
        self.assertRule('B3', report)
        report = valid_report()
        report['scan']['candidates_in_unscanned_words'] = None
        report['scan']['candidates_in_unscanned_words_reason'] = 'words_not_decoded'
        self.assertRule('B3', report)

    # ---- C: import table ----

    def test_c1_entry_closure(self):
        report = valid_report()
        entry_of(report, SYM_THROWING)['calls'] += 1
        self.assertRule('C1', report)

    def test_c1_not_swift_calls_below_calls(self):
        report = valid_report()
        entry_of(report, SYM_RUNTIME)['not_swift_calls'] = 3
        self.assertRule('C1', report)

    def test_c1_reason_with_a_decided_entry(self):
        report = valid_report()
        entry_of(report, SYM_NONTHROWING)['reason'] = 'accessor'
        self.assertRule('C1', report)

    def test_c1_reason_is_required_for_an_undecided_entry_and_absent_otherwise(self):
        report = valid_report()
        entry_of(report, SYM_ACCESSOR)['reason'] = None           # undecided with no reason
        self.assertRule('C1', report)
        report = valid_report()
        entry_of(report, SYM_RUNTIME)['reason'] = 'accessor'      # not_swift with a reason
        self.assertRule('C1', report)
        report = valid_report()
        entry_of(report, SYM_THROWING)['reason'] = 'accessor'     # throwing with a reason
        self.assertRule('C1', report)

    def test_c2_table_rules(self):
        report = valid_report()
        entries = report['import_calls']['entries']
        entries[0], entries[1] = entries[1], entries[0]
        self.assertRule('C2', report)                                  # not sorted
        report = valid_report()
        entries = report['import_calls']['entries']
        entries[1]['symbol'] = entries[0]['symbol']
        self.assertRule('C2', report)                                  # duplicate symbol
        report = valid_report()
        report['limits']['import_table_entries'] = len(report['import_calls']['entries']) - 1
        self.assertRule('C2', report)                                  # more entries than the limit
        report = valid_report()
        report['import_calls']['distinct_symbols'] += 1
        self.assertRule('C2', report)
        report = valid_report()
        report['import_calls']['attributed_calls'] += 1
        self.assertRule('C2', report)

    def test_c2_residual_does_not_close(self):
        report = valid_report()
        with_residual(report)
        report['import_calls']['residual']['retained'] = 1           # calls 2 != 1 + 2 + 0 + 0
        self.assertRule('C2', report)
        report = valid_report()
        with_residual(report)
        report['import_calls']['residual']['calls'] += 1
        self.assertRule('C2', report)

    def test_c3_complete_with_a_residual(self):
        report = valid_report()
        with_residual(report)
        report['import_calls']['complete'] = True
        self.assertRule('C3', report)

    def test_c3_complete_with_an_incomplete_scan(self):
        report = valid_report()
        make_scan_incomplete(report)
        report['import_calls']['complete'] = True
        self.assertRule('C3', report)

    def test_c3_incomplete_with_nothing_missing(self):
        report = valid_report()
        report['import_calls']['complete'] = False
        self.assertRule('C3', report)

    def test_c4_retained_against_rows(self):
        report = valid_report()
        del report['calls'][0]['effect_admission']
        self.assertRule('C4', report)

    def test_c4_omitted_against_omitted_by_kind(self):
        report = valid_report()
        omit_one(report)
        report['omitted_by_kind']['indirect'] -= 1
        report['omitted_by_kind']['import_stub'] += 1
        self.assertRule('C4', report)

    def test_c4_skipped_and_not_swift_against_the_unselected_counts(self):
        report = valid_report()
        report['unselected_call_counts']['skipped_non_throwing'] -= 1
        report['unselected_call_counts']['declined_stub'] += 1
        self.assertRule('C4', report)
        report = valid_report()
        report['unselected_call_counts']['non_swift_import'] -= 1
        report['unselected_call_counts']['declined_stub'] += 1
        self.assertRule('C4', report)

    def test_c5_attributed_swift_calls(self):
        report = valid_report()
        report['import_calls']['attributed_swift_calls'] += 1
        self.assertRule('C5', report)

    def test_c5_grid_cell(self):
        report = valid_report()
        report['decision_by_shape']['throwing']['none'] += 1
        self.assertRule('C5', report)

    def test_c6_names_sum(self):
        report = valid_report()
        report['decision_summary']['names']['non_throwing'] -= 1
        self.assertRule('C6', report)

    def test_c6_undecided_reason_outside_the_closed_list(self):
        report = valid_report()
        by_reason = report['decision_summary']['undecided_by_reason']
        by_reason['not_a_grammar_reason'] = by_reason.pop('accessor')
        self.assertRule('C6', report)

    def test_c6_undecided_names_and_calls(self):
        report = valid_report()
        report['decision_summary']['undecided_by_reason']['accessor']['calls'] += 1
        self.assertRule('C6', report)
        report = valid_report()
        report['decision_summary']['undecided_by_reason']['thunk_or_specialization'] = {'names': 1, 'calls': 0}
        self.assertRule('C6', report)

    def _with_value_witness_row(self, symbol, kind='imported_metadata_accessor_call'):
        """A value-witness row (an indirect row admitted as a non-throwing metadata accessor) for `symbol`."""
        report = valid_report()
        row = indirect_row('0x100008000', '0x100008010')
        row['admission'].update(status='declined', reason='value_witness_abi_nonthrowing')
        row['value_witness_admission'] = {'admitted': True, 'symbol': symbol,
                                          'provenance_kind': kind,
                                          'claims_callee_behaviour': False}
        report['calls'].append(row)
        report['selected_call_candidates'] += 1
        report['observed_call_instructions'] += 1
        report['reason_counts']['value_witness_abi_nonthrowing'] = 1
        report['status_counts']['declined'] = 1
        return report

    def test_c7_value_witness_symbol_listed_non_throwing_passes(self):
        self.assertValid(self._with_value_witness_row(SYM_NONTHROWING))

    def test_c7_value_witness_symbol_listed_throwing(self):
        """The admitted accessor's table entry says throwing. The grid and the names move with the entry so that
        only the value-witness rule is violated."""
        report = self._with_value_witness_row(SYM_NONTHROWING)
        entry_of(report, SYM_NONTHROWING)['decision'] = 'throwing'
        grid = report['decision_by_shape']
        for shape in SHAPES:
            grid['throwing'][shape] += grid['non_throwing'][shape]
            grid['non_throwing'][shape] = 0
        names = report['decision_summary']['names']
        names['throwing'] += names['non_throwing']
        names['non_throwing'] = 0
        self.assertRule('C7', report)

    def test_c7_runtime_metadata_symbol_listed_not_swift_passes(self):
        """A C runtime metadata function (Maccy 2.8.0: `_swift_checkMetadataState`) is listed not_swift."""
        self.assertValid(self._with_value_witness_row(SYM_RUNTIME, 'runtime_metadata_call'))

    def test_c7_runtime_metadata_symbol_listed_non_throwing(self):
        self.assertRule('C7', self._with_value_witness_row(SYM_NONTHROWING, 'runtime_metadata_call'))

    def test_c7_swift_accessor_symbol_listed_not_swift(self):
        for kind in ('imported_metadata_accessor_call', 'metadata_accessor_call'):
            with self.subTest(kind=kind):
                self.assertRule('C7', self._with_value_witness_row(SYM_RUNTIME, kind))

    # ---- D: rows ----

    def test_d1_first_generation_model_on_a_row(self):
        report = valid_report()
        rows_of(report, SYM_ASYNC)[0]['admission']['declaration']['syntax_model'] = SYNTAX_V1
        self.assertRule('D1', report)

    def test_d1_two_rows_of_one_symbol_differ(self):
        report = valid_report()
        first, second, _ = rows_of(report, SYM_THROWING)
        self.assertEqual(first['admission']['declaration'], second['admission']['declaration'])
        second['admission']['declaration']['entity'] = 'initializer'
        self.assertRule('D1', report)

    def test_d1_compact_record_shape(self):
        report = valid_report()
        del rows_of(report, SYM_ASYNC)[0]['admission']['declaration']['identity_sha256']
        self.assertRule('D1', report)
        report = valid_report()
        rows_of(report, SYM_ASYNC)[0]['admission']['declaration']['identity_sha256'] = sha('x').upper()
        self.assertRule('D1', report)

    def test_d2_licence_class_the_record_does_not_produce(self):
        classes = ('no_error_exit', 'declared_error_exit', 'refused_unsupported_effect', 'none')
        for symbol, right in ((SYM_THROWING, 'declared_error_exit'), (SYM_NONTHROWING, 'no_error_exit'),
                              (SYM_ASYNC, 'refused_unsupported_effect'), (SYM_ACCESSOR, 'none')):
            for wrong in classes:
                if wrong == right:
                    continue
                with self.subTest(symbol=symbol, wrong=wrong):
                    report = valid_report()
                    for row in rows_of(report, symbol):
                        row['effect_admission']['licence_class'] = wrong
                    self.assertRule('D2', report)

    def _retarget_throwing(self, report, record, licence, relation=None, reason=None):
        for row in rows_of(report, SYM_THROWING):
            row['admission']['declaration'] = copy.deepcopy(record)
            row['effect_admission']['licence_class'] = licence
            if relation is not None:
                row['effect_admission']['caller_relation'] = relation
            if reason is not None:
                row['admission']['reason'] = reason

    def test_d2_throwing_with_an_unsupported_effect_is_not_a_declared_error_exit(self):
        """Contract 4.3: a throwing record that is also async or typed-throws is refused_unsupported_effect."""
        for label, record in (
                ('async throws', decided_record('throwing', 'x', throws=True, is_async=True)),
                ('typed concrete', decided_record('throwing', 'x', throws=True, typed_throws='concrete')),
                ('typed concrete, not throws', decided_record('throwing', 'x', typed_throws='concrete')),
                ('async typed concrete', decided_record('throwing', 'x', throws=True, is_async=True,
                                                        typed_throws='concrete'))):
            with self.subTest(case=label):
                report = valid_report()
                self._retarget_throwing(report, record, 'declared_error_exit')
                self.assertRule('D2', report)
                report = valid_report()
                self._retarget_throwing(report, record, 'refused_unsupported_effect', 'not_applicable',
                                        'imported_callee_effect_unsupported')
                self.assertValid(report)

    def test_d2_throwing_with_an_unsupported_effect_is_not_licensed_as_anything_else(self):
        record = decided_record('throwing', 'x', throws=True, is_async=True)
        for wrong in ('no_error_exit', 'none'):
            with self.subTest(wrong=wrong):
                report = valid_report()
                self._retarget_throwing(report, record, wrong)
                self.assertRule('D2', report)

    def test_d1_decision_must_follow_from_the_fields(self):
        """Contract 5.3: the decision recomputed from the fields, in the order of finding 6, equals decision."""
        cases = (
            ('non_throwing but throws', SYM_NONTHROWING, dict(throws=True)),
            ('non_throwing but async', SYM_NONTHROWING, dict(is_async=True)),
            ('non_throwing but typed concrete', SYM_NONTHROWING, dict(typed_throws='concrete')),
            ('non_throwing but typed never', SYM_NONTHROWING, dict(typed_throws='never')),
            ('non_throwing but accessor entity', SYM_NONTHROWING, dict(entity='Getter')),
            ('throwing but throws false', SYM_THROWING, dict(throws=False)),
            ('throwing but typed never', SYM_THROWING, dict(typed_throws='never')),
            ('throwing but accessor entity', SYM_THROWING, dict(entity='Setter')),
            ('async but throws', SYM_ASYNC, dict(throws=True)),
            ('async but not async', SYM_ASYNC, dict(is_async=False)),
            ('accessor reason recorded as typed_throws', SYM_ACCESSOR, dict(reason='typed_throws')),
            ('accessor decided as throwing', SYM_ACCESSOR, dict(decision='throwing', reason=None)),
        )
        for label, symbol, change in cases:
            with self.subTest(case=label):
                report = valid_report()
                for row in rows_of(report, symbol):
                    row['admission']['declaration'].update(change)
                self.assertRule('D1', report)

    def test_d1_decided_fields_that_agree_are_accepted(self):
        report = valid_report()
        for row in rows_of(report, SYM_NONTHROWING):
            row['admission']['declaration'].update(entity='method')    # still a plain function-like entity
        self.assertValid(report)

    def test_d1_a_record_without_an_identity_is_undecided_with_a_decline_reason(self):
        none_fields = dict(entity=None, throws=None, is_async=None, typed_throws=None, identity_sha256=None)
        cases = (('decided without identity', dict(decision='non_throwing', reason=None)),
                 ('throwing without identity', dict(decision='throwing', reason=None)),
                 ('typed_throws reason without identity', dict(decision='undecided', reason='typed_throws')))
        for label, change in cases:
            with self.subTest(case=label):
                report = valid_report()
                for row in rows_of(report, SYM_ASYNC):
                    row['admission']['declaration'].update(none_fields, **change)
                self.assertRule('D1', report)

    def test_d1_a_declined_record_with_a_decline_reason_is_accepted(self):
        report = valid_report()
        for row in rows_of(report, SYM_ACCESSOR):
            row['admission']['declaration'].update(entity=None, throws=None, is_async=None, typed_throws=None,
                                                   identity_sha256=None, reason='malformed_symbol')
        entry_of(report, SYM_ACCESSOR)['reason'] = 'malformed_symbol'
        report['decision_summary']['undecided_by_reason'] = {'malformed_symbol': {'names': 1, 'calls': 1}}
        self.assertValid(report)

    def test_d1_a_static_accessor_declined_without_an_identity_is_accepted(self):
        # The grammar declines a static getter (trailing `Z`, for example `$ss11CommandLineO9argumentsSaySSGvgZ`) as
        # `accessor` with no identity (contract 5.3 as amended in section 10). That record must be accepted.
        report = valid_report()
        for row in rows_of(report, SYM_ACCESSOR):
            row['admission']['declaration'].update(entity=None, throws=None, is_async=None, typed_throws=None,
                                                   identity_sha256=None, reason='accessor')
        self.assertValid(report)

    def test_d1_a_record_with_an_identity_field_left_over_is_refused_when_entity_is_null(self):
        report = valid_report()
        for row in rows_of(report, SYM_ACCESSOR):
            record = row['admission']['declaration']
            record.update(entity=None, throws=None, is_async=None, typed_throws=None)   # digest left in place
        self.assertRule('D1', report)

    def test_d3_conflict_on_a_declared_error_exit_row(self):
        report = valid_report()
        rows_of(report, SYM_THROWING)[0]['effect_admission']['caller_relation'] = 'conflict'
        self.assertRule('D3', report)

    def test_d3_corroborated_on_a_tail_branch_row(self):
        report = valid_report()
        tail = next(r for r in rows_of(report, SYM_THROWING) if r['admission']['call_kind'] == 'b')
        tail['effect_admission']['caller_relation'] = 'corroborated'
        self.assertRule('D3', report)
        report = valid_report()
        tail = next(r for r in rows_of(report, SYM_THROWING) if r['admission']['call_kind'] == 'b')
        tail['effect_admission']['caller_relation'] = 'corroborated'
        tail['caller_error_test']['shape'] = 'swifterror_idiom'      # the shape alone does not license it on a b
        self.assertRule('D3', report)

    def test_d3_no_error_exit_row_with_no_signal(self):
        report = valid_report()
        rows_of(report, SYM_NONTHROWING)[0]['effect_admission']['caller_relation'] = 'no_signal'
        self.assertRule('D3', report)

    def test_d3_conflict_needs_the_swifterror_shape(self):
        report = valid_report()
        rows_of(report, SYM_NONTHROWING)[0]['caller_error_test']['shape'] = 'postcall_test_only'
        self.assertRule('D3', report)

    def test_d3_status_and_reason_follow_the_class(self):
        report = valid_report()
        rows_of(report, SYM_ACCESSOR)[0]['admission']['status'] = 'declined'
        self.assertRule('D3', report)
        report = valid_report()
        rows_of(report, SYM_ACCESSOR)[0]['admission']['reason'] = 'imported_callee_outcome_unmodeled'
        report['reason_counts']['imported_callee_abi_unqualified'] -= 1
        report['reason_counts']['imported_callee_outcome_unmodeled'] += 1
        self.assertRule('D3', report)

    def test_d3_refused_classes_are_not_applicable(self):
        for symbol in (SYM_ASYNC, SYM_ACCESSOR):
            for relation in ('conflict', 'corroborated', 'no_signal'):
                with self.subTest(symbol=symbol, relation=relation):
                    report = valid_report()
                    rows_of(report, symbol)[0]['effect_admission']['caller_relation'] = relation
                    self.assertRule('D3', report)

    def test_d4_import_row_never_carries_abi_candidate_or_validation(self):
        mutations = {
            'candidate with abi': lambda r: r.__setitem__('candidate', {'call': {'abi': {'x': 1}}}),
            'validation': lambda r: r.__setitem__('validation', {'fact_statuses': {}}),
            'abi at row level': lambda r: r.__setitem__('abi', {'x': 1}),
            'abi in admission': lambda r: r['admission'].__setitem__('abi', {'x': 1}),
        }
        for name, mutate in mutations.items():
            with self.subTest(mutation=name):
                report = valid_report()
                mutate(rows_of(report, SYM_THROWING)[0])
                self.assertRule('D4', report)

    # ---- E: header and pair ----

    def test_e1_premise_altered(self):
        for index in range(len(PREMISES)):
            with self.subTest(premise=index):
                report = valid_report()
                report['capabilities']['premises'][index] += '_x'
                self.assertRule('E1', report)

    def test_e1_not_claimed_altered_or_reordered(self):
        for index in range(len(NOT_CLAIMED)):
            with self.subTest(item=index):
                report = valid_report()
                report['capabilities']['not_claimed'][index] += '_x'
                self.assertRule('E1', report)
        report = valid_report()
        report['capabilities']['premises'].reverse()
        self.assertRule('E1', report)

    def test_e1_capability_strings_altered(self):
        for key in ('report_model', 'effect_admission_model', 'declaration_syntax_model', 'grammar_pin',
                    'caller_error_test_model'):
            with self.subTest(key=key):
                report = valid_report()
                report['capabilities'][key] += '_x'
                self.assertRule('E1', report)

    def test_e1_limits_key_removed(self):
        for key in valid_report()['limits']:
            with self.subTest(key=key):
                report = valid_report()
                del report['limits'][key]
                self.assertRule('E1', report)

    def test_e2_v4_field_under_the_v3_model(self):
        report = valid_report()
        report['profile'], report['model_version'] = V3_PROFILE, V3_MODEL
        self.assertRule('E2', report)

    def test_e2_mismatched_pair(self):
        for profile, model in ((V4_PROFILE, V3_MODEL), (V3_PROFILE, V4_MODEL)):
            with self.subTest(profile=profile, model=model):
                report = valid_report()
                report['profile'], report['model_version'] = profile, model
                self.assertRule('E2', report)

    def test_e2_v4_report_missing_import_calls(self):
        report = valid_report()
        del report['import_calls']
        self.assertRule('E2', report)

    def test_e2_every_v4_group_is_required(self):
        for group in V4_GROUPS:
            with self.subTest(group=group):
                report = valid_report()
                del report[group]
                self.assertRule('E2', report)


if __name__ == '__main__':
    unittest.main()
