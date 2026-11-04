"""Bounded parameterless throwing Int declaration recovery."""
import unittest
from airs.swift_error_flow import throwing_declaration, recover_swift_error_flow
from test_swift_error_flow import image

SYMBOL = '_$s4Demo4readSiyKF'

class NoArgIntThrowsTests(unittest.TestCase):
    def test_exact_declaration_and_edge(self):
        value = throwing_declaration(SYMBOL)
        self.assertIsNotNone(value)
        self.assertEqual(value['parameters'], [])
        self.assertEqual(value['result'], 'Swift.Int')
        call = recover_swift_error_flow(image(symbol=SYMBOL))['calls'][0]
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual({key: call['callee'][key] for key in value}, value)

    def test_refuses_nearby_result_and_convention_forms(self):
        for suffix in ('SSyKF', 'SbyKF', 'SiyF', 'SiyYaKF', 'SiyKFTA', 'SiyKFextra', 'SiyAA5FaultOYKF'):
            self.assertIsNone(throwing_declaration('_$s4Demo4read' + suffix), suffix)

    def test_method_and_alias_ambiguity_refuse(self):
        self.assertIsNone(throwing_declaration('_$s4Demo3BoxV4readSiyKF'))
        value = recover_swift_error_flow(image(symbol=SYMBOL, aliases=(('_$s4Demo5otherSiyKF', 32),)))
        self.assertEqual(value['calls'][0]['status'], 'declined')

    def test_width_and_empty_parameter_list_isolation(self):
        value = throwing_declaration(SYMBOL)
        self.assertIsNotNone(value)
        value['parameters'].append('foreign')
        self.assertEqual(throwing_declaration(SYMBOL)['parameters'], [])
        call = recover_swift_error_flow(image((0x34000075,), symbol=SYMBOL))['calls'][0]
        self.assertEqual(call['status'], 'declined')

    def test_handler_and_renderer_preserve_structural_limits(self):
        from test_swift_forward_error_arm import WORDS
        from airs.swift_error_text import render_swift_error_text
        value = recover_swift_error_flow(image(WORDS, symbol=SYMBOL), include_error_regions=True,
            validate_region_entries=True, include_structured_presentation=True)
        call = value['calls'][0]
        self.assertEqual(call['callee']['result'], 'Swift.Int')
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertFalse(call['presentation']['source_reconstruction_allowed'])
        self.assertIn('Swift.Int', render_swift_error_text(value))
