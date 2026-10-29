"""Exact parameterless ordinary throwing declarations; no runtime identity proof."""
import unittest
from airs.swift_error_flow import throwing_declaration, recover_swift_error_flow
from test_swift_error_flow import image

SYMBOL = '_$s10AIRSNoArgs8validateyyKF'


class NoArgThrowsFirstTests(unittest.TestCase):
    def test_exact_noarg_void_declaration_recovers(self):
        declaration = throwing_declaration(SYMBOL)
        self.assertIsNotNone(declaration)
        self.assertEqual(declaration['parameters'], [])
        self.assertEqual(declaration['result'], 'Swift.Void')
        self.assertEqual(declaration['error_register'], 'x21')
        call = recover_swift_error_flow(image(symbol=SYMBOL))['calls'][0]
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual(call['callee']['parameters'], [])

class NoArgThrowsBoundaryTests(unittest.TestCase):
    def test_optional_macho_underscore_preserves_exact_facts(self):
        self.assertEqual(throwing_declaration(SYMBOL), throwing_declaration(SYMBOL[1:]))

    def test_prior_int_signature_facts_are_preserved(self):
        for symbol, result in (('_$s4Demo5parseyS2iKF', 'Swift.Int'),
                               ('_$s12AIRSValidate8validateyySiKF', 'Swift.Void')):
            value = throwing_declaration(symbol)
            self.assertEqual(value['parameters'], ['Swift.Int'])
            self.assertEqual(value['result'], result)
            self.assertEqual(value['convention'], 'swift_sync_untyped_throws')

    def test_async_typed_nonthrowing_generic_and_thunk_forms_refuse(self):
        prefix = '_$s10AIRSNoArgs8validate'
        for suffix in ('yyF', 'yyYaKF', 'yyAA5FaultOYKF', 'yyKFTA', 'yyKFTj',
                       'yyKF.llvm.1', 'yyKFTu', 'yyxKlF', 'yyYbKF', 'yyYAKF', 'yyKFextra'):
            self.assertIsNone(throwing_declaration(prefix + suffix), suffix)

    def test_other_parameterless_result_types_remain_outside_subset(self):
        prefix = '_$s10AIRSNoArgs8validate'
        for suffix in ('SSyKF', 'SbyKF', 'yKF', 'yyyKF'):
            self.assertIsNone(throwing_declaration(prefix + suffix), suffix)

    def test_context_identifiers_and_control_bytes_stay_refused(self):
        for symbol in ('_$s10AIRSNoArgs3BoxV8validateyyKF', '_$s010AIRSNoArgs8validateyyKF',
                       '_$s10AIRSNoArgs08validateyyKF', '_$s10AIRSNoArgs8validat!yyKF',
                       SYMBOL + '\x00', SYMBOL + '\x01', '_T010AIRSNoArgs8validateyyKF'):
            self.assertIsNone(throwing_declaration(symbol))

    def test_parameter_lists_are_not_shared_between_results(self):
        value = throwing_declaration(SYMBOL); value['parameters'].append('foreign')
        self.assertEqual(throwing_declaration(SYMBOL)['parameters'], [])
        prior = throwing_declaration('_$s4Demo5parseyS2iKF'); prior['parameters'].clear()
        self.assertEqual(throwing_declaration('_$s4Demo5parseyS2iKF')['parameters'], ['Swift.Int'])

    def test_alias_ambiguity_never_supplies_a_declaration(self):
        value = recover_swift_error_flow(image(symbol=SYMBOL, aliases=(('_$s10AIRSNoArgs5otheryyKF', 32),)))
        self.assertEqual(value['calls'][0]['status'], 'declined')
        self.assertEqual(value['summary']['recovered_candidate_count'], 0)

    def test_narrow_or_unrelated_register_tests_do_not_recover(self):
        for test in (0x34000075, 0xb4000060, 0xb400007f):
            self.assertEqual(recover_swift_error_flow(image((test,), symbol=SYMBOL))['calls'][0]['status'], 'declined')

    def test_alias_tracking_remains_width_correct_for_new_declaration(self):
        call = recover_swift_error_flow(image((0xaa1503f3, 0xaa1f03f5, 0xb4000073), symbol=SYMBOL))['calls'][0]
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual(call['tested_register'], 'x19')

    def test_new_signature_composes_with_forward_handler_and_renderer(self):
        from test_swift_forward_error_arm import WORDS
        from airs.swift_error_text import render_swift_error_text
        value = recover_swift_error_flow(image(WORDS, symbol=SYMBOL), include_error_regions=True,
            validate_region_entries=True, include_structured_presentation=True)
        call = value['calls'][0]
        self.assertEqual(call['callee']['parameters'], [])
        self.assertEqual(call['error_region']['layout'], 'success_fallthrough_error_forward')
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertFalse(call['presentation']['source_reconstruction_allowed'])
        self.assertEqual(value['model_version'], 'swift-sync-error-edges-v36')
        self.assertEqual(value['error_region_model_version'], 'swift-sync-error-region-v24')
        self.assertEqual(value['region_incoming_model_version'], 'swift-region-direct-entries-v7')
        self.assertEqual(value['structured_presentation_model_version'], 'swift-structural-presentation-v9')
        self.assertIn('Swift.Void', render_swift_error_text(value))


class NoArgThrowsCLIControls(unittest.TestCase):
    def test_synthetic_cli_json_and_direct_text_report_empty_parameter_list(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        from airs.cli import main
        from fixture_storage import temporary_directory
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'owned-noarg.macho'
            source.write_bytes(image(symbol=SYMBOL).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source)])
            self.assertEqual(status, 0)
            value = json.loads(output.getvalue())
            self.assertEqual(value['calls'][0]['callee']['parameters'], [])
            self.assertEqual(value['model_version'], 'swift-sync-error-edges-v36')
        from test_swift_forward_error_arm import WORDS
        from airs.swift_error_text import render_swift_error_text
        value = recover_swift_error_flow(image(WORDS, symbol=SYMBOL), include_error_regions=True,
            validate_region_entries=True, include_structured_presentation=True)
        self.assertIn('Swift.Void', render_swift_error_text(value))
        self.assertFalse(value['calls'][0]['presentation']['source_reconstruction_allowed'])


if __name__ == '__main__':
    unittest.main()
