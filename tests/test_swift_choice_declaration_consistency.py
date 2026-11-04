"""Reconcile paired return choices with retained callee symbols."""
from copy import deepcopy
import unittest

from airs.swift_error_flow import _return_choice, throwing_declaration, RETURN_CHOICE_MODEL
from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report


class ChoiceDeclarationConsistencyTests(unittest.TestCase):
    def test_all_admitted_declarations_preserve_literal_choices(self):
        self.assertEqual(RETURN_CHOICE_MODEL, 'swift-return-choice-v45')
        for name, layout in LAYOUTS:
            for suffix in ('yS2iKF', 'SiyKF', 'yySiKF', 'yyKF'):
                value=report(layout((0xd2800540,))); call=value['calls'][0]
                symbol='_$s4Demo5parse'+suffix
                call['callee'].update(symbol=symbol, **throwing_declaration(symbol))
                with self.subTest(layout=name, signature=suffix):
                    choice=_return_choice(call)
                    self.assertEqual(choice['status'], 'structural_choice_candidate')
                    self.assertIs(choice['runtime_value_proven'], False)

    def test_register_choice_requires_consistent_int_declaration(self):
        for name, layout in LAYOUTS:
            value=report(layout((0x91001400,))); call=value['calls'][0]
            symbol='_$s4Demo5parseSiyKF';call['callee'].update(symbol=symbol, **throwing_declaration(symbol))
            with self.subTest(layout=name, result='int'):
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
            symbol='_$s4Demo5parseyyKF';call['callee'].update(symbol=symbol, **throwing_declaration(symbol))
            with self.subTest(layout=name, result='void'):
                self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_contradictory_missing_and_unsupported_declarations_refuse(self):
        for name, layout in LAYOUTS:
            for word in (0xd2800540, 0x91001400):
                original=report(layout((word,)))
                for key,bad in (('symbol','_$s4Demo5parseyySiKF'), ('symbol','_$s4Demo5parseyS2iYaKF'),
                                ('symbol',None), ('module','Other'), ('name','other'), ('parameters',[]),
                                ('parameters','Swift.Int'), ('result','Swift.Void'), ('convention','other'),
                                ('error_register','x20'), ('source','other')):
                    value=deepcopy(original);call=value['calls'][0];call['callee'][key]=bad
                    with self.subTest(layout=name, word=word, field=key, bad=bad):
                        choice=_return_choice(call)
                        self.assertEqual(choice['status'], 'unresolved')
                        self.assertEqual(choice['reason'], 'outcome_evidence_inconsistent')
                        self.assertIs(choice['runtime_value_proven'], False)
                        text=render_swift_error_text(value)
                        self.assertNotIn('Recorded literal outcomes (structural; runtime unproven):', text)
                        self.assertNotIn('Recorded adjusted-result/error outcomes (structural; runtime unproven):', text)
                        self.assertIn('Callee declaration (not runtime identity):', text)
                for bad in (None, [], 'callee', 1):
                    value=deepcopy(original);value['calls'][0]['callee']=bad
                    self.assertEqual(_return_choice(value['calls'][0])['status'], 'unresolved')
                value=deepcopy(original);del value['calls'][0]['callee']
                self.assertEqual(_return_choice(value['calls'][0])['status'], 'unresolved')

    def test_preserved_result_pair_rejects_conflicting_symbol(self):
        label='Recorded call-result/error outcomes (structural; runtime unproven):'
        for name, layout in LAYOUTS:
            value=report(layout((0xd503201f,)))
            with self.subTest(layout=name):
                self.assertIn(label, render_swift_error_text(value))
                value['calls'][0]['callee']['symbol']='_$s4Demo5parseyySiKF'
                self.assertNotIn(label, render_swift_error_text(value))
                self.assertEqual(_return_choice(value['calls'][0])['status'], 'unresolved')
