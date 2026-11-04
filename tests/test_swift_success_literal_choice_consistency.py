"""Reconcile success literal choices with bound recorded path words."""
from copy import deepcopy
import unittest
from airs.swift_error_flow import _return_choice, _bind_choice_success_literal
from test_swift_literal_outcome_summary import report
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_success_entry_choice_tail import direct_variants
from test_swift_return_choice_tail_binding import selected_outcomes

class SuccessLiteralChoiceConsistencyTests(unittest.TestCase):
    def test_valid_shared_literal_forms_across_layouts(self):
        arms = ((0xd2800540,), (0x92800000,), (0x12800000,),
                (0xd2800540, 0xf2a00020), (0x12800000, 0x72a00020),
                (0xd2800553, 0xaa1303e0), (0x92800013, 0x2a1303e0), (0xaa1f03e0,))
        for name, layout in LAYOUTS:
            for arm in arms:
                with self.subTest(name=name, arm=arm):
                    call = report(layout(arm))['calls'][0]
                    before = deepcopy(call)
                    self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
                    self.assertEqual(call, before)

    def test_forged_bits_and_false_equality_are_refused(self):
        cases = [(name, layout((0xd2800540,))) for name, layout in LAYOUTS]
        cases += [(name, words) for name, words in direct_variants() if name == 'eq_literal']
        for name, words in cases:
            with self.subTest(name=name):
                call = report(words)['calls'][0]
                call['success_constant']['constant_bits'] = call['error_constant']['constant_bits']
                choice = _return_choice(call)
                self.assertEqual(choice['status'], 'unresolved')
                self.assertFalse(choice['runtime_value_proven'])

    def test_cmp_prefix_register_seed_flows_into_shared_arm(self):
        for name, layout in LAYOUTS:
            if name not in ('eq', 'ne'): continue
            with self.subTest(name=name):
                call = report((0xd2800553, *layout((0xaa1303e0,))))['calls'][0]
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
                self.assertEqual(call['return_choice']['success']['constant_bits'], '0x000000000000002a')

    def test_unknown_seed_and_clobber_do_not_become_literal(self):
        call = report(dict(direct_variants())['eq_literal'])['calls'][0]
        for word in ('0xf2800020', '0xaa1303e0'):
            with self.subTest(word=word):
                changed = deepcopy(call)
                changed['window'][0]['word'] = word
                with self.assertRaisesRegex(ValueError, 'Success literal mismatch'):
                    _bind_choice_success_literal(changed, changed['success_constant'], [])

    def test_forged_synchronized_unknown_prefix_is_refused_by_choice(self):
        original = report(dict(direct_variants())['eq_literal'])['calls'][0]
        for word, kind in (('0xf2800020', 'xmovk'), ('0xaa1303e0', 'mov')):
            with self.subTest(word=word):
                call = deepcopy(original)
                call['window'][0]['word'] = word
                call['window'][0]['kind'] = kind
                success = selected_outcomes(call)[0]
                success['instructions'][0]['word'] = word
                with self.assertRaisesRegex(ValueError, 'Success literal mismatch'):
                    _bind_choice_success_literal(call, success, [])
                self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')

    def test_cmp_branch_only_and_direct_void_literals_remain_choices(self):
        from test_swift_success_result import report as symbol_report
        from test_swift_void_outcomes import NOARG, INTARG
        from test_swift_cmp_success_literals import WORDS
        for symbol in (NOARG, INTARG):
            with self.subTest(symbol=symbol):
                call = symbol_report((*WORDS, 0xd65f03c0), symbol=symbol)['calls'][0]
                self.assertEqual(_return_choice(call)['success']['constant_bits'], '0x000000000000002a')
        call = report((0xd2800540, *dict(LAYOUTS)['ne'](())))['calls'][0]
        self.assertEqual(len(call['error_region']['success_interval']['instructions']), 1)
        self.assertEqual(_return_choice(call)['success']['constant_bits'], '0x000000000000002a')
