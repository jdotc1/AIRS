"""Reconcile standalone operation declarations with retained symbols."""
from copy import deepcopy
import unittest

from airs.swift_error_text import render_swift_error_text
from test_swift_arithmetic_call_binding import LAYOUTS
from test_swift_literal_outcome_summary import report

OPERATION = 'Success operation (structural; runtime unproven):'


class OperationDeclarationConsistencyTests(unittest.TestCase):
    def test_conflicting_symbols_and_fields_withhold_operation(self):
        for name, layout in LAYOUTS:
            for word in (0x91001400, 0xd1001400):
                original=report(layout((word,)))
                self.assertIn(OPERATION, render_swift_error_text(original))
                for key,bad in (('symbol','_$s4Demo5parseyySiKF'), ('symbol','_$s4Demo5parseyS2iYaKF'),
                                ('symbol',None), ('module','Other'), ('name','other'),
                                ('parameters',[]), ('parameters','Swift.Int'), ('convention','other'),
                                ('error_register','x20'), ('source','other')):
                    value=deepcopy(original);value['calls'][0]['callee'][key]=bad
                    with self.subTest(layout=name, word=word, field=key, bad=bad):
                        text=render_swift_error_text(value)
                        self.assertNotIn(OPERATION,text)
                        self.assertIn('Callee declaration (not runtime identity):',text)
                value=deepcopy(original);del value['calls'][0]['callee']['symbol']
                self.assertNotIn(OPERATION,render_swift_error_text(value))

    def test_valid_noarg_int_and_missing_error_remain_independent(self):
        for name, layout in LAYOUTS:
            value=report(layout((0x91001400,)));callee=value['calls'][0]['callee']
            callee['symbol']='_$s4Demo5parseSiyKF';callee['parameters']=[]
            del value['calls'][0]['error_constant']
            with self.subTest(layout=name):
                self.assertIn(OPERATION,render_swift_error_text(value))

    def test_conflicting_symbol_is_retained_as_raw_declaration(self):
        value=report(LAYOUTS[0][1]((0x91001400,)))
        value['calls'][0]['callee']['symbol']='_$s4Demo5parseyySiKF'
        text=render_swift_error_text(value)
        self.assertNotIn(OPERATION,text)
        self.assertIn('"symbol": "_$s4Demo5parseyySiKF"',text)
