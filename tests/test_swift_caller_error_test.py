"""Independent caller evidence expectations from the contract and Apple disassembly.

No fixture is executed. Interface assumptions are documented with the test
handoff. Frozen report bytes are reused without hashing their inputs.
"""
import json
from collections import Counter
from pathlib import Path
import unittest

from airs.macho import parse_macho
from airs.report import dumps
from airs.swift_broad_flow import PROFILE_LIMITS, recover_swift_broad_flow
from airs.swift_caller_error_test import caller_error_test, precall_x21_zero
from airs.swift_error_flow import recover_swift_error_flow
from stub_image_helpers import Import, build_stub_image
from got_image_helpers import GotImport, build_got_image, got_call


ROOT = Path(__file__).resolve().parents[1] / 'fixtures/swift-error-flow'
FIXTURE = ROOT / 'broad-imports'
PROFILE = 'broad-extended-v2'
MODEL = 'swift-caller-error-test-v1'
NOP = 0xd503201f
RET = 0xd65f03c0
ZERO = 0xaa1f03f5                 # MOV X21, XZR, not MOVZ X21, #0.
BL = 0x94000020
CBNZ = 0xb5000055                # CBNZ X21, PC+8.
CBZ = 0xb4000055                 # CBZ X21, PC+8.
THROWING = '_$s4Test3fooyS2iKF'
NON_THROWING = '_$s4Test3fooyS2iF'
UNRESOLVED = '_$sZZZ'
BASE = 0x100001000


def located(words, base=BASE):
    return [(base + 4 * index, word) for index, word in enumerate(words)]


def fact(words, call_index=4, start=0, entries=()):
    return caller_error_test(located(words), call_index, start, len(words), entries)


def flow(data, profile=PROFILE):
    return recover_swift_broad_flow(
        parse_macho(data, limits=PROFILE_LIMITS[profile]), profile=profile)


class PrecallWindowTests(unittest.TestCase):
    def check(self, prefix, status, *, start=0, entries=(), zero_index=None):
        result = precall_x21_zero(located([*prefix, BL]), len(prefix), start, entries)
        self.assertEqual(result['status'], status)
        self.assertIsInstance(result['window'], list)
        for row in result['window']:
            self.assertTrue({'pc', 'word', 'kind'} <= row.keys())
        self.assertLessEqual(len(result['window']), 4)
        if zero_index is not None:
            self.assertEqual(result['zero_pc'], hex(BASE + 4 * zero_index))
        return result

    def test_zero_at_distance_one_and_four(self):
        for distance in (1, 4):
            with self.subTest(distance=distance):
                prefix = [NOP] * 4
                prefix[4 - distance] = ZERO
                self.check(prefix, 'x21_zeroed', zero_index=4 - distance)

    def test_distance_five_is_outside_window(self):
        self.check([ZERO, NOP, NOP, NOP, NOP], 'x21_not_zeroed')

    def test_intervening_writes_invalidate_zero(self):
        # X/W register copies, a move-wide literal, ADD and LDR all write x21.
        for write in (0xaa0003f5, 0x2a0003f5, 0xd2800035, 0x91000415, 0xf9400015):
            with self.subTest(word=hex(write)):
                self.check([NOP, ZERO, write, NOP], 'x21_not_zeroed')

    def test_read_of_x21_does_not_clobber_it(self):
        self.check([NOP, ZERO, 0xaa1503e0, NOP], 'x21_zeroed', zero_index=1)

    def test_later_exact_zero_supersedes_earlier_write(self):
        self.check([ZERO, 0xaa0003f5, NOP, ZERO], 'x21_zeroed', zero_index=3)

    def test_direct_entry_between_zero_and_call_refuses(self):
        self.check([NOP, ZERO, NOP, NOP], 'x21_not_zeroed', entries=(2,))

    def test_missing_entry_scan_is_explicit(self):
        self.check([NOP, ZERO, NOP, NOP], 'precall_entries_unchecked', entries=None)

    def test_missing_entry_scan_without_a_zero_is_not_zeroed(self):
        self.check([NOP, NOP, NOP, NOP, NOP], 'x21_not_zeroed', entries=None)
        self.check([ZERO, 0xaa0003f5, NOP, NOP], 'x21_not_zeroed', entries=None)
        self.check([ZERO, NOP, NOP, NOP, NOP], 'x21_not_zeroed', entries=None)

    def test_window_cannot_borrow_zero_from_previous_caller(self):
        self.check([ZERO, NOP, NOP, NOP], 'precall_window_outside_caller', start=2)

    def test_call_at_caller_start_has_no_predecessor(self):
        self.check([], 'precall_window_outside_caller')

    def test_movz_zero_is_not_the_contracts_exact_mov(self):
        self.check([NOP, NOP, NOP, 0xd2800015], 'x21_not_zeroed')


class CallerRecordTests(unittest.TestCase):
    def assertRecord(self, record, shape):
        self.assertEqual(record['model'], MODEL)
        self.assertEqual(record['shape'], shape)
        self.assertIs(record['claims_callee_behaviour'], False)
        self.assertTrue({'model', 'precall', 'postcall', 'shape',
                         'claims_callee_behaviour'} <= record.keys())

    def test_four_shapes_and_no_callee_claim(self):
        cases = ((ZERO, CBNZ, 'swifterror_idiom'),
                 (NOP, CBNZ, 'postcall_test_only'),
                 (ZERO, RET, 'precall_zero_only'),
                 (NOP, RET, 'none'))
        for pre, post, shape in cases:
            with self.subTest(shape=shape):
                record = fact([NOP, NOP, NOP, pre, BL, post, NOP, RET])
                self.assertRecord(record, shape)
                if post == RET:
                    self.assertEqual(record['postcall']['reason'], 'intervening_instruction_unmodeled')

    def test_cbz_and_cbnz_zero_success_direction(self):
        for instruction, success, error in ((CBZ, 7, 6), (CBNZ, 6, 7)):
            with self.subTest(instruction=hex(instruction)):
                record = fact([NOP, NOP, NOP, ZERO, BL, instruction, NOP, RET])
                self.assertRecord(record, 'swifterror_idiom')
                post = record['postcall']
                self.assertEqual(post['status'], 'recovered_candidate')
                self.assertEqual(post['test_pc'], hex(BASE + 20))
                self.assertEqual(post['tested_register'], 'x21')
                self.assertEqual(post['success_pc'], hex(BASE + 4 * success))
                self.assertEqual(post['error_pc'], hex(BASE + 4 * error))

    def test_alias_copy_and_adjacent_compare_condition(self):
        for condition, success, error in ((0, 9, 8), (1, 8, 9)):
            with self.subTest(condition=condition):
                # MOV X9,X21; SUBS XZR,X9,#0; B.EQ/NE PC+8.
                record = fact([NOP, NOP, NOP, ZERO, BL, 0xaa1503e9,
                               0xf100013f, 0x54000040 | condition, NOP, RET])
                self.assertRecord(record, 'swifterror_idiom')
                post = record['postcall']
                self.assertEqual(post['test_kind'], 'cmp_zero_bcond')
                self.assertEqual(post['comparison_pc'], hex(BASE + 24))
                self.assertEqual(post['test_pc'], hex(BASE + 28))
                self.assertEqual(post['tested_register'], 'x9')
                self.assertEqual(post['success_pc'], hex(BASE + 4 * success))
                self.assertEqual(post['error_pc'], hex(BASE + 4 * error))

    def test_alias_cbz(self):
        record = fact([NOP, NOP, NOP, ZERO, BL, 0xaa1503e9, 0xb4000049, NOP, RET])
        self.assertRecord(record, 'swifterror_idiom')
        self.assertEqual(record['postcall']['tested_register'], 'x9')

    def test_unchanged_postcall_refusal_reasons(self):
        cases = (([0x34000055, NOP, RET], 'narrow_error_test'),
                 ([0xaa0003f5, CBNZ, NOP, RET], 'error_value_clobbered'),
                 ([0xf9400008, CBNZ, NOP, RET], 'intervening_instruction_unmodeled'),
                 ([0xb5000040, NOP, RET], 'not_error_result_test'),
                 ([NOP] * 8 + [CBNZ, NOP, RET], 'postcall_window_exhausted'))
        for suffix, reason in cases:
            with self.subTest(reason=reason):
                record = fact([NOP, NOP, NOP, ZERO, BL, *suffix])
                self.assertRecord(record, 'precall_zero_only')
                self.assertEqual(record['postcall']['reason'], reason)

    def test_test_at_eighth_word_is_inside_window(self):
        record = fact([NOP, NOP, NOP, ZERO, BL, *([NOP] * 7), CBNZ, NOP, RET])
        self.assertRecord(record, 'swifterror_idiom')

    def test_unchecked_entries_cannot_assert_full_idiom(self):
        record = fact([NOP, NOP, NOP, ZERO, BL, CBNZ, NOP, RET], entries=None)
        self.assertRecord(record, 'postcall_test_only')

    def test_c_pointer_and_unrelated_zero_examples(self):
        # C uses x21 as an ordinary callee-saved pointer in the first sequence.
        pointer = fact([NOP, NOP, NOP, 0xaa0003f5, BL, CBNZ, NOP, RET])
        unrelated_zero = fact([NOP, NOP, NOP, ZERO, BL, RET, NOP, RET])
        self.assertRecord(pointer, 'postcall_test_only')
        self.assertRecord(unrelated_zero, 'precall_zero_only')


class OwnedCallerExpectationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads((FIXTURE / 'expected-caller-error-test.json').read_text())

    def test_all_twenty_seven_sites_against_disassembly(self):
        callers = {c['start']: c for c in self.expected['callers']}
        sites = self.expected['sites']
        self.assertEqual(len(sites), 27)
        self.assertEqual(sum(s['demangled_throws'] for s in sites), 7)
        self.assertEqual(sum(s['call_kind'] == 'b' for s in sites), 2)
        self.assertEqual(Counter(s['shape'] for s in sites), {'none': 25, 'postcall_test_only': 2})
        for site in sites:
            with self.subTest(pc=site['call_pc'], symbol=site['callee_symbol']):
                caller = callers[site['caller_start']]
                start = int(caller['start'], 16)
                words = located([int(w, 16) for w in caller['words']], start)
                index = (int(site['call_pc'], 16) - start) // 4
                record = caller_error_test(words, index, 0, len(words), caller['entry_indices'])
                self.assertEqual(record['model'], MODEL)
                self.assertIs(record['claims_callee_behaviour'], False)
                self.assertEqual(record['shape'], site['shape'])
                self.assertEqual(record['precall']['status'], site['precall']['status'])
                if site['postcall']['reason'] is not None:
                    self.assertEqual(record['postcall']['reason'], site['postcall']['reason'])
                else:
                    for key in ('status', 'test_pc', 'tested_register', 'success_pc', 'error_pc'):
                        self.assertEqual(record['postcall'][key], site['postcall'][key])

    def test_selected_import_rows_retain_expected_facts_and_counts(self):
        report = flow((FIXTURE / 'OwnedImports.macho').read_bytes())
        expected = {s['call_pc']: s for s in self.expected['sites']}
        selected = [r for r in report['calls'] if r['call_pc'] in expected]
        actual = {r['call_pc'] for r in selected}
        self.assertTrue({s['call_pc'] for s in expected.values() if s['demangled_throws']} <= actual)
        self.assertTrue(selected)
        shapes, declines = Counter(), Counter()
        for row in selected:
            site = expected[row['call_pc']]
            record = row['caller_error_test']
            self.assertEqual(record['shape'], site['shape'])
            self.assertEqual(record['model'], MODEL)
            self.assertIs(record['claims_callee_behaviour'], False)
            self.assertEqual(row['admission']['reason'], 'imported_callee_abi_unqualified')
            self.assertEqual(row['admission']['status'], 'unresolved')
            if site['postcall']['reason'] is not None:
                self.assertEqual(record['postcall']['reason'], site['postcall']['reason'])
            shapes[record['shape']] += 1
            if record['postcall'].get('reason'):
                declines[record['postcall']['reason']] += 1
        self.assertEqual(Counter(report['caller_error_test_counts']), shapes)
        self.assertEqual(Counter(report['caller_error_test_decline_counts']), declines)
        self.assertEqual(report['reason_counts'].get('declaration_caller_disagreement', 0), 0)


class DeclarationDisagreementTests(unittest.TestCase):
    def report(self, symbol, zero, test, kind):
        prefix = (NOP, NOP, NOP, ZERO if zero else NOP)
        suffix = (CBNZ if test else RET, NOP, RET)
        if kind == 'stub':
            data, _ = build_stub_image(callers=((*prefix, ('bl', ('stub', 0)), *suffix),),
                                       imports=(Import(symbol),))
        else:
            data, _ = build_got_image(callers=((*prefix, *got_call(), *suffix),),
                                      imports=(GotImport(symbol),))
        return flow(data)

    def test_declaration_and_caller_matrix_for_stub_and_got(self):
        for kind in ('stub', 'got'):
            for symbol in (NON_THROWING, THROWING, UNRESOLVED, '_owned_c_function'):
                for zero, test in ((True, True), (True, False), (False, True), (False, False)):
                    with self.subTest(kind=kind, symbol=symbol, zero=zero, test=test):
                        report = self.report(symbol, zero, test, kind)
                        disagreement = symbol == NON_THROWING and zero and test
                        retained = symbol in (THROWING, UNRESOLVED) or disagreement
                        self.assertEqual(len(report['calls']), int(retained))
                        self.assertEqual(report['selected_call_candidates'], int(retained))
                        self.assertEqual(report['reason_counts'].get('declaration_caller_disagreement', 0),
                                         int(disagreement))
                        if retained:
                            row = report['calls'][0]
                            record = row['caller_error_test']
                            shape = ('swifterror_idiom' if zero and test else
                                     'precall_zero_only' if zero else
                                     'postcall_test_only' if test else 'none')
                            self.assertEqual(record['shape'], shape)
                            self.assertIs(record['claims_callee_behaviour'], False)
                            self.assertEqual(row['admission']['status'], 'unresolved')
                            self.assertEqual(row['admission']['reason'], 'declaration_caller_disagreement'
                                             if disagreement else 'imported_callee_abi_unqualified')
                            self.assertEqual(report['caller_error_test_counts'].get(shape), 1)
                            self.assertIsNone(row['candidate'])
                            self.assertIsNone(row['validation'])


class HistoricalIsolationTests(unittest.TestCase):
    def test_frozen_legacy_edge_and_structured_report_bytes(self):
        # Includes the existing edge output, without a private _edges dependency.
        goldens = ROOT / 'broad-goldens'
        for name in ('edge', 'shared', 'unknown'):
            image = parse_macho((goldens / (name + '.macho')).read_bytes())
            for structured in (False, True):
                with self.subTest(name=name, structured=structured):
                    report = recover_swift_error_flow(
                        image, include_error_regions=structured, validate_region_entries=structured,
                        include_structured_presentation=structured)
                    suffix = '.structured.json' if structured else '.default.json'
                    self.assertEqual(dumps(report).encode(), (goldens / (name + suffix)).read_bytes())

    def test_existing_broad_profiles_do_not_gain_caller_evidence(self):
        data, _ = build_stub_image(callers=((NOP, NOP, NOP, ZERO,
                                            ('bl', ('stub', 0)), CBNZ, NOP, RET),))
        for profile in ('broad-v1', 'broad-large-v1', 'broad-extended-v1',
                        'broad-imports-v1', 'broad-imports-got-v1'):
            with self.subTest(profile=profile):
                report = flow(data, profile)
                self.assertNotIn('caller_error_test_counts', report)
                self.assertNotIn('caller_error_test_decline_counts', report)
                for row in report['calls']:
                    self.assertNotIn('caller_error_test', row)
                    self.assertNotIn('caller_error_test', row['admission'])


if __name__ == '__main__':
    unittest.main()
