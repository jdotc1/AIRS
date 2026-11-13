"""Accounting library and report checker for profile broad-extended-v4.

Three pieces, none of which reads an image or runs the engine:

* split_scan: classes every word of every function once (decoded, not decoded for the per-function ceiling, not
  decoded because the total ceiling ran out, or in a function excluded for its boundary).
* UnselectedPartition and ImportCallTable: the counters the engine feeds while it scans (the five unselected buckets
  with their remainder, and the bounded per-symbol import call table with its decision grid and summary).
* check_broad_v4_report: applies the invariants of the design contract (rule ids A1 to E2) to a finished report. It
  raises ValueError whose message starts with the rule id and a colon, and never mutates its input.

The module mints no identity and imports nothing from the engine; it only reads the closed grammar reason list.
"""
from collections import Counter
import re

from .swift_declaration_grammar import REASONS as GRAMMAR_REASONS, _ACCESSORS

IMPORT_TABLE_MAX_ENTRIES = 4096
IMPORT_TABLE_BYTE_RESERVE = 2 * 1024 * 1024
ENTRY_OVERHEAD_BYTES = 512
RETENTION_LIMIT = 8192          # limits.max_total_evidence for this profile (the retention limit is not raised)

PROFILE = 'broad-extended-v4'
MODEL = 'swift-broad-error-flow-extended-v4'
V3_PROFILE = 'broad-extended-v3'
V3_MODEL = 'swift-broad-error-flow-extended-v3'
EFFECT_ADMISSION_MODEL = 'swift-import-effect-admission-v1'
DECLARATION_SYNTAX_MODEL = 'swift-declaration-syntax-v2'
GRAMMAR_PIN = 'swift-6.4.2-RELEASE'
CALLER_ERROR_TEST_MODEL = 'swift-caller-error-test-v1'
PREMISES = ('symbol_name_carries_effects', 'no_silgen_name_override', 'name_only_attribution',
            'binding_not_proven', 'grammar_pinned')
NOT_CLAIMED = ('callee_returns', 'dyld_binding', 'runtime_callee', 'arguments_and_results',
               'error_value_at_runtime')
CAPABILITIES = {'report_model': MODEL, 'effect_admission_model': EFFECT_ADMISSION_MODEL,
                'declaration_syntax_model': DECLARATION_SYNTAX_MODEL, 'grammar_pin': GRAMMAR_PIN,
                'caller_error_test_model': CALLER_ERROR_TEST_MODEL,
                'premises': list(PREMISES), 'not_claimed': list(NOT_CLAIMED)}
LIMIT_KEYS = ('max_total_evidence', 'max_observations_per_function', 'max_instructions_per_function',
              'max_total_instructions', 'analysis_work_ceiling', 'output_budget_bytes',
              'import_table_entries', 'import_table_byte_reserve')
V4_GROUPS = ('capabilities', 'limits', 'omission_causes', 'omitted_by_kind', 'unselected_call_counts', 'scan',
             'import_calls', 'decision_by_shape', 'decision_summary')

CAUSES = ('analysis_work_budget', 'per_function_limit', 'total_row_limit', 'output_budget')
KINDS = ('import_stub', 'import_got', 'local_swift_direct', 'indirect')
BUCKETS = ('skipped_non_throwing', 'non_swift_import', 'declined_stub', 'direct_target_not_swift_function',
           'direct_target_unattributed')
UNSELECTED_KEYS = BUCKETS + ('other',)
DECISIONS = ('non_throwing', 'throwing', 'async', 'undecided')
SHAPES = ('swifterror_idiom', 'postcall_test_only', 'precall_zero_only', 'none')
NOT_SWIFT = 'not_swift'
OUTCOMES = ('retained', 'skipped_non_throwing', 'not_swift', 'omitted')
VIAS = ('stub', 'got')
SCAN_KEYS = ('words_total', 'words_scanned', 'words_unscanned_per_function_ceiling',
             'words_unscanned_total_ceiling', 'words_excluded_boundary', 'functions_total',
             'functions_excluded_boundary', 'functions_truncated', 'candidates_in_unscanned_words',
             'candidates_in_unscanned_words_reason')
UNSCANNED_REASON = 'words_not_decoded'
ENTRY_KEYS = frozenset({'symbol', 'decision', 'reason', 'calls', 'stub_calls', 'got_calls', 'retained',
                        'skipped_non_throwing', 'not_swift_calls', 'omitted'})
RESIDUAL_KEYS = frozenset({'symbols', 'calls', 'retained', 'skipped_non_throwing', 'not_swift_calls', 'omitted'})
IMPORT_CALLS_KEYS = frozenset({'complete', 'attributed_calls', 'attributed_swift_calls', 'distinct_symbols',
                               'entries', 'residual'})
RECORD_KEYS = frozenset({'syntax_model', 'decision', 'reason', 'entity', 'throws', 'is_async', 'typed_throws',
                         'identity_sha256'})
EFFECT_KEYS = frozenset({'model', 'licence_class', 'caller_relation'})
TYPED_THROWS = ('none', 'never', 'concrete')
LICENCES = ('no_error_exit', 'declared_error_exit', 'refused_unsupported_effect', 'none')
RELATIONS = ('conflict', 'corroborated', 'no_signal', 'not_applicable')
ROW_REASONS = {'no_error_exit': 'declaration_caller_disagreement',
               'declared_error_exit': 'imported_callee_outcome_unmodeled',
               'refused_unsupported_effect': 'imported_callee_effect_unsupported',
               'none': 'imported_callee_abi_unqualified'}
SCAN_MARKERS = frozenset({'excluded_boundary'})     # internal scan markers, never a row reason
ACCESSOR_ENTITIES = frozenset(_ACCESSORS.values())
_SHA256 = re.compile(r'[0-9a-f]{64}')


def _plain_int(value):
    return type(value) is int


def _check_ceiling(name, value):
    if not _plain_int(value) or value < 0:
        raise ValueError('%s must be a non-negative integer' % name)


# ---------------------------------------------------------------------------------------------------------------
# Scan split (rules B1 to B3 are checked against this block)
# ---------------------------------------------------------------------------------------------------------------

def split_scan(functions, per_function_ceiling, total_ceiling):
    """Class every word of every function once; functions are (size_in_bytes, from_function_starts) pairs."""
    _check_ceiling('per_function_ceiling', per_function_ceiling)
    _check_ceiling('total_ceiling', total_ceiling)
    rows = []
    decoded_total = 0
    excluded_functions = 0
    for size, from_starts in functions:
        if not _plain_int(size):
            raise ValueError('function size must be an integer')
        if size <= 0 or size % 4 or not from_starts:
            excluded_functions += 1
            rows.append({'decoded': 0, 'unscanned_per_function_ceiling': 0, 'unscanned_total_ceiling': 0,
                         'excluded_boundary': max(size, 0) // 4})
            continue
        words = size // 4
        remaining = total_ceiling - decoded_total
        capped = min(words, per_function_ceiling)
        count = min(capped, remaining)
        decoded_total += count
        rows.append({'decoded': count, 'unscanned_per_function_ceiling': words - capped,
                     'unscanned_total_ceiling': capped - count, 'excluded_boundary': 0})
    per_function = sum(r['unscanned_per_function_ceiling'] for r in rows)
    total = sum(r['unscanned_total_ceiling'] for r in rows)
    excluded_words = sum(r['excluded_boundary'] for r in rows)
    truncated = sum(1 for r in rows if r['unscanned_per_function_ceiling'] or r['unscanned_total_ceiling'])
    # Words of a boundary-excluded function are never decoded either (contract 4.7): candidates there are unknown.
    known = per_function == 0 and total == 0 and excluded_words == 0
    scan = {'words_total': decoded_total + per_function + total + excluded_words,
            'words_scanned': decoded_total,
            'words_unscanned_per_function_ceiling': per_function,
            'words_unscanned_total_ceiling': total,
            'words_excluded_boundary': excluded_words,
            'functions_total': len(rows),
            'functions_excluded_boundary': excluded_functions,
            'functions_truncated': truncated,
            'candidates_in_unscanned_words': 0 if known else None,
            'candidates_in_unscanned_words_reason': None if known else UNSCANNED_REASON}
    return {'functions': rows, 'scan': scan,
            'word_scan_complete': truncated == 0 and excluded_functions == 0, 'scanned_words': decoded_total}


# ---------------------------------------------------------------------------------------------------------------
# Unselected partition
# ---------------------------------------------------------------------------------------------------------------

class UnselectedPartition:
    """Counts observed call instructions and where each one went; `other` is the remainder, never forced to 0."""

    def __init__(self):
        self._observed = 0
        self._selected = 0
        self._buckets = {key: 0 for key in BUCKETS}

    def observe(self):
        self._observed += 1

    def classify(self, outcome):
        if outcome == 'selected':
            self._selected += 1
        elif outcome in self._buckets:
            self._buckets[outcome] += 1
        else:
            raise ValueError('unknown call outcome: %r' % (outcome,))

    def counts(self):
        unselected = dict(self._buckets)
        unselected['other'] = self._observed - self._selected - sum(self._buckets.values())
        return {'observed_call_instructions': self._observed, 'selected_call_candidates': self._selected,
                'unselected_call_counts': unselected}


# ---------------------------------------------------------------------------------------------------------------
# Import call table
# ---------------------------------------------------------------------------------------------------------------

class ImportCallTable:
    """Per-symbol call counts that do not depend on the row limit, bounded by entries and by a byte reserve."""

    def __init__(self):
        # Read when constructed, so a test patches the module constants before it builds a table.
        self._max_entries = IMPORT_TABLE_MAX_ENTRIES
        self._byte_reserve = IMPORT_TABLE_BYTE_RESERVE
        self._overhead = ENTRY_OVERHEAD_BYTES
        self._symbols = {}          # symbol -> (decision, reason), every distinct symbol listed or not
        self._calls = {}            # symbol -> total calls, every distinct symbol
        self._entries = {}          # admitted symbol -> counter dict
        self._reserved = 0
        self._residual = {key: 0 for key in ('calls', 'retained', 'skipped_non_throwing', 'not_swift_calls',
                                             'omitted')}
        self._overflowed = set()
        self._grid = Counter()

    def record(self, symbol, via, decision, reason, outcome, shape=None):
        self._validate(symbol, via, decision, reason, outcome, shape)
        known = self._symbols.get(symbol)
        if known is None:
            self._symbols[symbol] = (decision, reason)
            self._calls[symbol] = 0
            self._admit(symbol, decision, reason)
        elif known != (decision, reason):
            raise ValueError('symbol %r recorded with two decisions' % (symbol,))
        self._calls[symbol] += 1
        if decision != NOT_SWIFT:
            self._grid[(decision, shape)] += 1
        entry = self._entries.get(symbol)
        if entry is not None:
            entry['calls'] += 1
            entry['stub_calls' if via == 'stub' else 'got_calls'] += 1
            target = entry
        else:
            self._residual['calls'] += 1
            target = self._residual
        target[{'retained': 'retained', 'skipped_non_throwing': 'skipped_non_throwing',
                'not_swift': 'not_swift_calls', 'omitted': 'omitted'}[outcome]] += 1

    @staticmethod
    def _validate(symbol, via, decision, reason, outcome, shape):
        if type(symbol) is not str or not symbol:
            raise ValueError('symbol must be a non-empty string')
        if via not in VIAS:
            raise ValueError('unknown via: %r' % (via,))
        if decision not in DECISIONS + (NOT_SWIFT,):
            raise ValueError('unknown decision: %r' % (decision,))
        if outcome not in OUTCOMES:
            raise ValueError('unknown outcome: %r' % (outcome,))
        if decision == 'undecided':
            if reason not in GRAMMAR_REASONS:
                raise ValueError('an undecided symbol needs a grammar reason, got %r' % (reason,))
        elif reason is not None:
            raise ValueError('only an undecided symbol carries a reason')
        if decision == NOT_SWIFT:
            if outcome != 'not_swift' or shape is not None:
                raise ValueError('a non-Swift call has outcome not_swift and no shape')
            return
        if outcome == 'not_swift':
            raise ValueError('a Swift call cannot have outcome not_swift')
        if outcome == 'skipped_non_throwing' and decision != 'non_throwing':
            raise ValueError('only a non-throwing call is skipped as non-throwing')
        if shape not in SHAPES:
            raise ValueError('unknown caller shape: %r' % (shape,))

    def _admit(self, symbol, decision, reason):
        cost = self._overhead + len(symbol.encode('utf-8'))
        if len(self._entries) < self._max_entries and self._reserved + cost <= self._byte_reserve:
            self._reserved += cost
            self._entries[symbol] = {'symbol': symbol, 'decision': decision, 'reason': reason, 'calls': 0,
                                     'stub_calls': 0, 'got_calls': 0, 'retained': 0, 'skipped_non_throwing': 0,
                                     'not_swift_calls': 0, 'omitted': 0}
        else:
            self._overflowed.add(symbol)

    def import_calls(self, word_scan_complete):
        if type(word_scan_complete) is not bool:
            raise ValueError('word_scan_complete must be a bool')
        entries = [dict(self._entries[symbol]) for symbol in sorted(self._entries)]
        residual = {'symbols': len(self._overflowed), **self._residual}
        attributed = sum(self._calls.values())
        not_swift = sum(e['not_swift_calls'] for e in entries) + residual['not_swift_calls']
        return {'complete': residual['symbols'] == 0 and word_scan_complete,
                'attributed_calls': attributed, 'attributed_swift_calls': attributed - not_swift,
                'distinct_symbols': len(self._symbols), 'entries': entries, 'residual': residual}

    def decision_by_shape(self):
        return {decision: {shape: self._grid[(decision, shape)] for shape in SHAPES} for decision in DECISIONS}

    def decision_summary(self):
        names = {decision: 0 for decision in DECISIONS}
        by_reason = {}
        for symbol, (decision, reason) in self._symbols.items():
            if decision == NOT_SWIFT:
                continue
            names[decision] += 1
            if decision == 'undecided':
                slot = by_reason.setdefault(reason, {'names': 0, 'calls': 0})
                slot['names'] += 1
                slot['calls'] += self._calls[symbol]
        return {'names': names, 'undecided_by_reason': {k: by_reason[k] for k in sorted(by_reason)}}


# ---------------------------------------------------------------------------------------------------------------
# Checker
# ---------------------------------------------------------------------------------------------------------------

class BroadV4ReportError(ValueError):
    """A v4 report breaks an invariant; the message starts with the rule id and a colon."""


def _fail(rule, text):
    raise BroadV4ReportError('%s: %s' % (rule, text))


def _count(rule, value, what):
    if not _plain_int(value) or value < 0:
        _fail(rule, '%s must be a non-negative integer, got %r' % (what, value))
    return value


def _mapping(rule, value, what, keys):
    if not isinstance(value, dict) or set(value) != set(keys):
        _fail(rule, '%s must be an object with exactly the keys %s' % (what, sorted(keys)))
    return value


def _counts(rule, value, what, keys):
    _mapping(rule, value, what, keys)
    for key in keys:
        _count(rule, value[key], '%s.%s' % (what, key))
    return value


def _rows(rule, report):
    calls = report['calls']
    if not isinstance(calls, list) or any(not isinstance(row, dict) for row in calls):
        _fail(rule, 'calls must be a list of objects')
    return calls


def _import_rows(rule, report):
    return [row for row in _rows(rule, report) if 'effect_admission' in row]


def _limits(report):
    return report['limits']


# ---- E2, E1 ----

def _check_presence(report):
    if not isinstance(report, dict):
        _fail('E2', 'the report must be an object')
    present = [group for group in V4_GROUPS if group in report]
    pair = (report.get('profile'), report.get('model_version'))
    if pair == (PROFILE, MODEL):
        missing = [group for group in V4_GROUPS if group not in report]
        if missing:
            _fail('E2', 'a v4 report requires every v4 group; missing %s' % missing)
    elif present:
        _fail('E2', 'v4 fields %s appear under the pair %r, which is not the v4 pair' % (present, pair))
    else:
        _fail('E2', 'the pair %r is not the v4 pair' % (pair,))


def _check_capabilities(report):
    capabilities = report['capabilities']
    if not isinstance(capabilities, dict) or capabilities != CAPABILITIES:
        _fail('E1', 'capabilities must equal the fixed strings')
    limits = report['limits']
    _counts('E1', limits, 'limits', LIMIT_KEYS)


# ---- A ----

def _a1(report):
    calls = _rows('A1', report)
    selected = _count('A1', report['selected_call_candidates'], 'selected_call_candidates')
    omitted = _count('A1', report['omitted_calls'], 'omitted_calls')
    if len(calls) != selected - omitted:
        _fail('A1', 'len(calls) %d != selected_call_candidates %d - omitted_calls %d'
              % (len(calls), selected, omitted))


def _a2(report):
    omitted = _count('A2', report['omitted_calls'], 'omitted_calls')
    causes = sum(_counts('A2', report['omission_causes'], 'omission_causes', CAUSES).values())
    kinds = sum(_counts('A2', report['omitted_by_kind'], 'omitted_by_kind', KINDS).values())
    if not omitted == causes == kinds:
        _fail('A2', 'omitted_calls %d, sum of omission_causes %d, sum of omitted_by_kind %d must be equal'
              % (omitted, causes, kinds))


def _a3(report):
    if report['omitted_calls'] > 0:
        for flag in ('call_details_complete', 'outcome_witnesses_complete'):
            if report[flag] is not False:
                _fail('A3', 'omitted_calls > 0 requires %s to be false' % flag)


def _a4(report):
    rows = len(_rows('A4', report))
    reasons = report['reason_counts']
    statuses = report['status_counts']
    if not isinstance(reasons, dict) or not isinstance(statuses, dict):
        _fail('A4', 'reason_counts and status_counts must be objects')
    for name, group in (('reason_counts', reasons), ('status_counts', statuses)):
        for key, value in group.items():
            _count('A4', value, '%s[%r]' % (name, key))
    marker = sorted(set(reasons) & SCAN_MARKERS)
    if marker:
        _fail('A4', 'reason_counts carries the internal scan marker %s' % marker)
    if sum(reasons.values()) != rows:
        _fail('A4', 'sum(reason_counts) %d != len(calls) %d' % (sum(reasons.values()), rows))
    if sum(statuses.values()) != rows:
        _fail('A4', 'sum(status_counts) %d != len(calls) %d' % (sum(statuses.values()), rows))


def _a5(report):
    unselected = _counts('A5', report['unselected_call_counts'], 'unselected_call_counts', UNSELECTED_KEYS)
    observed = _count('A5', report['observed_call_instructions'], 'observed_call_instructions')
    selected = _count('A5', report['selected_call_candidates'], 'selected_call_candidates')
    named = sum(unselected[key] for key in BUCKETS)
    if observed != selected + named:
        _fail('A5', 'observed_call_instructions %d != selected %d + unselected buckets %d'
              % (observed, selected, named))
    if unselected['other'] != 0:
        _fail('A5', 'unselected_call_counts.other is %d, it must be 0' % unselected['other'])


def _a6(report):
    calls = _rows('A6', report)
    limits = _limits(report)
    if limits['max_total_evidence'] != RETENTION_LIMIT:
        _fail('A6', 'limits.max_total_evidence is %d, the retention limit is %d'
              % (limits['max_total_evidence'], RETENTION_LIMIT))
    if len(calls) > limits['max_total_evidence']:
        _fail('A6', 'len(calls) %d exceeds limits.max_total_evidence' % len(calls))
    if report['omission_causes']['total_row_limit'] > 0 and len(calls) != limits['max_total_evidence']:
        _fail('A6', 'total_row_limit omissions with len(calls) %d below limits.max_total_evidence %d'
              % (len(calls), limits['max_total_evidence']))
    per_caller = Counter(row['caller_pc'] for row in calls)
    busiest = max(per_caller.values(), default=0)
    if busiest > limits['max_observations_per_function']:
        _fail('A6', 'a caller_pc has %d rows, above limits.max_observations_per_function' % busiest)
    if report['omission_causes']['per_function_limit'] > 0 and busiest != limits['max_observations_per_function']:
        _fail('A6', 'per_function_limit omissions but no caller_pc has exactly %d rows'
              % limits['max_observations_per_function'])


# ---- B ----

def _scan(report, rule):
    scan = _mapping(rule, report['scan'], 'scan', SCAN_KEYS)
    for key in SCAN_KEYS[:8]:
        _count(rule, scan[key], 'scan.' + key)
    return scan


def _b1(report):
    scan = _scan(report, 'B1')
    parts = (scan['words_scanned'] + scan['words_unscanned_per_function_ceiling']
             + scan['words_unscanned_total_ceiling'] + scan['words_excluded_boundary'])
    if scan['words_total'] != parts:
        _fail('B1', 'words_total %d != scanned + unscanned + excluded %d' % (scan['words_total'], parts))
    if scan['words_scanned'] != _count('B1', report['scanned_words'], 'scanned_words'):
        _fail('B1', 'words_scanned %d != scanned_words %d' % (scan['words_scanned'], report['scanned_words']))


def _b2(report):
    scan = _scan(report, 'B2')
    complete = report['word_scan_complete']
    if type(complete) is not bool:
        _fail('B2', 'word_scan_complete must be a bool')
    truncated, excluded = scan['functions_truncated'], scan['functions_excluded_boundary']
    if complete != (truncated == 0 and excluded == 0):
        _fail('B2', 'word_scan_complete %r with functions_truncated %d and functions_excluded_boundary %d'
              % (complete, truncated, excluded))
    unscanned = scan['words_unscanned_per_function_ceiling'] + scan['words_unscanned_total_ceiling']
    if (truncated == 0) != (unscanned == 0):
        _fail('B2', 'functions_truncated %d does not agree with the unscanned word counts %d'
              % (truncated, unscanned))
    if truncated + excluded > scan['functions_total']:
        _fail('B2', 'functions_truncated + functions_excluded_boundary exceeds functions_total')


def _b3(report):
    scan = _scan(report, 'B3')
    unscanned = (scan['words_unscanned_per_function_ceiling'] + scan['words_unscanned_total_ceiling']
                 + scan['words_excluded_boundary'])     # every word that was not decoded (contract 4.7)
    candidates = scan['candidates_in_unscanned_words']
    reason = scan['candidates_in_unscanned_words_reason']
    if unscanned == 0:
        if not (_plain_int(candidates) and candidates == 0 and reason is None):
            _fail('B3', 'with no undecoded words candidates_in_unscanned_words must be 0 with a null reason')
    elif candidates is not None or reason != UNSCANNED_REASON:
        _fail('B3', 'with undecoded words candidates_in_unscanned_words must be null with reason %s'
              % UNSCANNED_REASON)


# ---- C ----

def _import_block(report, rule):
    block = _mapping(rule, report['import_calls'], 'import_calls', IMPORT_CALLS_KEYS)
    if type(block['complete']) is not bool:
        _fail(rule, 'import_calls.complete must be a bool')
    for key in ('attributed_calls', 'attributed_swift_calls', 'distinct_symbols'):
        _count(rule, block[key], 'import_calls.' + key)
    if not isinstance(block['entries'], list):
        _fail(rule, 'import_calls.entries must be a list')
    for item in block['entries']:
        _mapping(rule, item, 'an import call entry', ENTRY_KEYS)
        if type(item['symbol']) is not str:
            _fail(rule, 'an import call entry needs a string symbol')
        for key in ENTRY_KEYS - {'symbol', 'decision', 'reason'}:
            _count(rule, item[key], 'entry %r %s' % (item['symbol'], key))
    _counts(rule, block['residual'], 'import_calls.residual', RESIDUAL_KEYS)
    return block


def _closes(item):
    return (item['calls'] == item['retained'] + item['skipped_non_throwing'] + item['not_swift_calls']
            + item['omitted'])


def _c1(report):
    for item in _import_block(report, 'C1')['entries']:
        symbol = item['symbol']
        if item['calls'] != item['stub_calls'] + item['got_calls'] or not _closes(item):
            _fail('C1', 'entry %r does not close: calls %d, stub %d + got %d, outcomes sum to %d'
                  % (symbol, item['calls'], item['stub_calls'], item['got_calls'],
                     item['retained'] + item['skipped_non_throwing'] + item['not_swift_calls'] + item['omitted']))
        decision, reason = item['decision'], item['reason']
        if decision not in DECISIONS + (NOT_SWIFT,):
            _fail('C1', 'entry %r has unknown decision %r' % (symbol, decision))
        if (decision == 'undecided') != (reason is not None):
            _fail('C1', 'entry %r: reason must be non-null exactly when the decision is undecided' % symbol)
        if reason is not None and reason not in GRAMMAR_REASONS:
            _fail('C1', 'entry %r has a reason outside the grammar list: %r' % (symbol, reason))
        if (decision == NOT_SWIFT) != (item['not_swift_calls'] == item['calls']):
            _fail('C1', 'entry %r: not_swift_calls must equal calls exactly when the decision is not_swift'
                  % symbol)


def _c2(report):
    block = _import_block(report, 'C2')
    entries, residual = block['entries'], block['residual']
    symbols = [item['symbol'] for item in entries]
    if any(a >= b for a, b in zip(symbols, symbols[1:])):
        _fail('C2', 'entries must be unique and sorted by symbol')
    if len(entries) > report['limits']['import_table_entries']:
        _fail('C2', '%d entries exceed limits.import_table_entries' % len(entries))
    if block['attributed_calls'] != sum(item['calls'] for item in entries) + residual['calls']:
        _fail('C2', 'attributed_calls does not equal the entries plus residual.calls')
    if block['distinct_symbols'] != len(entries) + residual['symbols']:
        _fail('C2', 'distinct_symbols does not equal len(entries) + residual.symbols')
    if not _closes(residual):
        _fail('C2', 'the residual does not close: calls != retained + skipped + not_swift + omitted')


def _c3(report):
    block = _import_block(report, 'C3')
    expected = block['residual']['symbols'] == 0 and report['word_scan_complete'] is True
    if block['complete'] != expected:
        _fail('C3', 'complete is %r but residual.symbols == 0 and word_scan_complete is %r'
              % (block['complete'], expected))


def _totals(block, key):
    return sum(item[key] for item in block['entries']) + block['residual'][key]


def _c4(report):
    block = _import_block(report, 'C4')
    unselected = report['unselected_call_counts']
    kinds = report['omitted_by_kind']
    rows = len(_import_rows('C4', report))
    if _totals(block, 'retained') != rows:
        _fail('C4', 'retained sums to %d but %d rows carry effect_admission' % (_totals(block, 'retained'), rows))
    if _totals(block, 'skipped_non_throwing') != unselected['skipped_non_throwing']:
        _fail('C4', 'skipped_non_throwing differs from unselected_call_counts.skipped_non_throwing')
    if _totals(block, 'not_swift_calls') != unselected['non_swift_import']:
        _fail('C4', 'not_swift_calls differs from unselected_call_counts.non_swift_import')
    if _totals(block, 'omitted') != kinds['import_stub'] + kinds['import_got']:
        _fail('C4', 'omitted differs from omitted_by_kind.import_stub + import_got')


def _grid(report, rule):
    grid = _mapping(rule, report['decision_by_shape'], 'decision_by_shape', DECISIONS)
    for decision in DECISIONS:
        _counts(rule, grid[decision], 'decision_by_shape.' + decision, SHAPES)
    return grid


def _c5(report):
    block = _import_block(report, 'C5')
    expected = block['attributed_calls'] - _totals(block, 'not_swift_calls')
    if block['attributed_swift_calls'] != expected:
        _fail('C5', 'attributed_swift_calls %d != attributed_calls - not_swift_calls %d'
              % (block['attributed_swift_calls'], expected))
    cells = sum(sum(row.values()) for row in _grid(report, 'C5').values())
    if cells != block['attributed_swift_calls']:
        _fail('C5', 'decision_by_shape sums to %d, attributed_swift_calls is %d'
              % (cells, block['attributed_swift_calls']))


def _distinct_swift_range(block):
    """Bounds on the number of distinct Swift symbols; exact when the residual is empty or one kind."""
    listed = sum(1 for item in block['entries'] if item['decision'] != NOT_SWIFT)
    residual = block['residual']
    swift_calls = residual['calls'] - residual['not_swift_calls']
    other_calls = residual['not_swift_calls']
    symbols = residual['symbols']
    low = max(1 if swift_calls else 0, symbols - other_calls)
    high = min(swift_calls, symbols - (1 if other_calls else 0))
    return listed + low, listed + high


def _c6(report):
    block = _import_block(report, 'C6')
    summary = _mapping('C6', report['decision_summary'], 'decision_summary', ('names', 'undecided_by_reason'))
    names = _counts('C6', summary['names'], 'decision_summary.names', DECISIONS)
    low, high = _distinct_swift_range(block)
    if low > high:
        _fail('C6', 'the residual cannot hold any whole number of Swift symbols')
    if not low <= sum(names.values()) <= high:
        _fail('C6', 'decision_summary.names sums to %d, the distinct Swift symbols number %s'
              % (sum(names.values()), low if low == high else '%d to %d' % (low, high)))
    by_reason = summary['undecided_by_reason']
    if not isinstance(by_reason, dict):
        _fail('C6', 'undecided_by_reason must be an object')
    for reason, slot in by_reason.items():
        if reason not in GRAMMAR_REASONS:
            _fail('C6', 'undecided_by_reason key %r is not in the closed reason list' % (reason,))
        _counts('C6', slot, 'undecided_by_reason[%r]' % (reason,), ('names', 'calls'))
    if sum(slot['names'] for slot in by_reason.values()) != names['undecided']:
        _fail('C6', 'undecided_by_reason names do not sum to names.undecided')
    if sum(slot['calls'] for slot in by_reason.values()) != sum(_grid(report, 'C6')['undecided'].values()):
        _fail('C6', 'undecided_by_reason calls do not sum to the undecided row of decision_by_shape')


def _c7(report):
    """An admitted value-witness symbol that the import table lists must agree with it (contract 4.5, amended 10).

    A Swift metadata accessor (`metadata_accessor_call`, `imported_metadata_accessor_call`) is a Swift declaration
    and must be listed `non_throwing`. A `runtime_metadata_call` names one of the fixed C runtime metadata functions,
    which is not a Swift declaration and must be listed `not_swift`.
    """
    decisions = {item['symbol']: item['decision'] for item in _import_block(report, 'C7')['entries']}
    for row in _rows('C7', report):
        witness = row.get('value_witness_admission')
        if isinstance(witness, dict) and witness.get('admitted') is True:
            symbol = witness.get('symbol')
            expected = 'not_swift' if witness.get('provenance_kind') == 'runtime_metadata_call' else 'non_throwing'
            if symbol in decisions and decisions[symbol] != expected:
                _fail('C7', 'metadata symbol %r is admitted by the value-witness check as %s but listed %s'
                      % (symbol, witness.get('provenance_kind'), decisions[symbol]))


# ---- D ----

def _expected_decision(record):
    """Recompute the grammar decision from the record fields in the order of the grammar (finding 6)."""
    if record['reason'] == 'accessor' or record['entity'] in ACCESSOR_ENTITIES:
        return 'undecided', 'accessor'
    if record['typed_throws'] == 'never':
        return 'undecided', 'typed_throws'
    if record['throws'] or record['typed_throws'] != 'none':
        return 'throwing', None
    if record['is_async']:
        return 'async', None
    return 'non_throwing', None


def _check_record(record):
    _mapping('D1', record, 'the declaration record', RECORD_KEYS)
    if record['syntax_model'] != DECLARATION_SYNTAX_MODEL:
        _fail('D1', 'declaration syntax_model is %r, not %s' % (record['syntax_model'], DECLARATION_SYNTAX_MODEL))
    decision, reason = record['decision'], record['reason']
    if decision not in DECISIONS:
        _fail('D1', 'declaration decision %r is not one of the four' % (decision,))
    if decision == 'undecided':
        if reason not in GRAMMAR_REASONS:
            _fail('D1', 'an undecided declaration needs a grammar reason, got %r' % (reason,))
    elif reason is not None:
        _fail('D1', 'a decided declaration has a null reason')
    fields = ('entity', 'throws', 'is_async', 'typed_throws', 'identity_sha256')
    if record['entity'] is None:
        if any(record[key] is not None for key in fields):
            _fail('D1', 'a declined declaration has null entity, throws, is_async, typed_throws and digest')
        # The grammar declines a static accessor (trailing `Z`) as `accessor` with no identity (contract 5.3 as
        # amended in section 10); `typed_throws` is only decided with an identity.
        if decision != 'undecided' or reason == 'typed_throws':
            _fail('D1', 'a declaration without an identity is undecided with a decline reason')
        return
    if type(record['entity']) is not str or not record['entity']:
        _fail('D1', 'declaration entity must be a non-empty string')
    if type(record['throws']) is not bool or type(record['is_async']) is not bool:
        _fail('D1', 'declaration throws and is_async must be booleans')
    if record['typed_throws'] not in TYPED_THROWS:
        _fail('D1', 'declaration typed_throws must be none, never or concrete')
    digest = record['identity_sha256']
    if type(digest) is not str or not _SHA256.fullmatch(digest):
        _fail('D1', 'declaration identity_sha256 must be 64 lowercase hex characters')
    if _expected_decision(record) != (decision, reason):
        _fail('D1', 'declaration decision %s/%s does not follow from its fields' % (decision, reason))


def _d1(report):
    seen = {}
    for row in _import_rows('D1', report):
        admission = row['admission']
        record = admission['declaration']
        _check_record(record)
        symbol = admission['symbol']
        if type(symbol) is not str:
            _fail('D1', 'an import row needs a string admission.symbol')
        if seen.setdefault(symbol, record) != record:
            _fail('D1', 'rows of %r carry different declaration records' % symbol)


def _licence_class(record):
    decision = record['decision']
    if decision == 'non_throwing':
        return 'no_error_exit'
    if decision == 'throwing':
        if record['is_async'] or record['typed_throws'] != 'none':
            return 'refused_unsupported_effect'
        return 'declared_error_exit'
    if decision == 'async':
        return 'refused_unsupported_effect'
    return 'none'


def _effect(row, rule):
    return _mapping(rule, row['effect_admission'], 'effect_admission', EFFECT_KEYS)


def _d2(report):
    for row in _import_rows('D2', report):
        effect = _effect(row, 'D2')
        if effect['model'] != EFFECT_ADMISSION_MODEL:
            _fail('D2', 'effect_admission.model is %r' % (effect['model'],))
        expected = _licence_class(row['admission']['declaration'])
        if effect['licence_class'] != expected:
            _fail('D2', 'licence_class %r, the record produces %r (symbol %r)'
                  % (effect['licence_class'], expected, row['admission']['symbol']))


def _expected_relation(licence, shape, tail):
    """The relation of contract 4.4; None means no retained row may exist for the case."""
    if licence == 'no_error_exit':
        return 'conflict' if shape == 'swifterror_idiom' and not tail else None
    if licence == 'declared_error_exit':
        if tail:
            return 'not_applicable'
        return 'corroborated' if shape == 'swifterror_idiom' else 'no_signal'
    return 'not_applicable'


def _d3(report):
    for row in _import_rows('D3', report):
        effect = _effect(row, 'D3')
        admission = row['admission']
        licence, relation = effect['licence_class'], effect['caller_relation']
        if relation not in RELATIONS:
            _fail('D3', 'unknown caller_relation %r' % (relation,))
        shape = row['caller_error_test']['shape']
        if shape not in SHAPES:
            _fail('D3', 'unknown caller shape %r' % (shape,))
        expected = _expected_relation(licence, shape, admission['call_kind'] == 'b')
        if expected is None:
            _fail('D3', 'a retained row with licence no_error_exit needs a bl-kind call and shape swifterror_idiom')
        if relation != expected:
            _fail('D3', 'relation %s, contract 4.4 gives %s for licence %s, shape %s, call kind %s'
                  % (relation, expected, licence, shape, admission['call_kind']))
        if admission['status'] != 'unresolved':
            _fail('D3', 'a retained import row stays unresolved, got status %r' % (admission['status'],))
        if admission['reason'] != ROW_REASONS[licence]:
            _fail('D3', 'row reason %r, licence %s gives %s' % (admission['reason'], licence, ROW_REASONS[licence]))


def _d4(report):
    for row in _import_rows('D4', report):
        if row.get('candidate') is not None:
            _fail('D4', 'an import row carries a candidate')
        if row.get('validation') is not None:
            _fail('D4', 'an import row carries a validation')
        if 'abi' in row or 'abi' in row['admission']:
            _fail('D4', 'an import row carries an abi')


_RULES = (('A1', _a1), ('A2', _a2), ('A3', _a3), ('A4', _a4), ('A5', _a5), ('A6', _a6),
          ('B1', _b1), ('B2', _b2), ('B3', _b3),
          ('C1', _c1), ('C2', _c2), ('C3', _c3), ('C4', _c4), ('C5', _c5), ('C6', _c6), ('C7', _c7),
          ('D1', _d1), ('D2', _d2), ('D3', _d3), ('D4', _d4))


def check_broad_v4_report(report):
    """Apply every invariant of the design contract to a finished v4 report; return None or raise ValueError.

    Structure first (E2, then E1), then A1 to A6, B1 to B3, C1 to C7, D1 to D4; the first violated rule is the one
    reported. A malformed field is reported under the rule that was reading it, never as KeyError or TypeError.
    The report is only read.
    """
    for rule, check in (('E2', _check_presence), ('E1', _check_capabilities)):
        _guarded(rule, check, report)
    for rule, check in _RULES:
        _guarded(rule, check, report)


def _guarded(rule, check, report):
    try:
        check(report)
    except BroadV4ReportError:
        raise
    except (KeyError, TypeError, AttributeError, IndexError, ValueError) as error:
        raise BroadV4ReportError('%s: malformed report (%s: %s)' % (rule, type(error).__name__, error)) from None
