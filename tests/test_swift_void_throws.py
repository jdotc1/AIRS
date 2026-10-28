"""Exact ordinary Swift Int-to-Void throwing declarations and refusal controls."""
import unittest
from airs.swift_error_flow import throwing_declaration, recover_swift_error_flow
from test_swift_error_flow import image

SYMBOL = '_$s12AIRSValidate8validateyySiKF'


class SwiftVoidThrowsFirstTests(unittest.TestCase):
    def test_compiler_spelling_recovers_void_result_and_x21(self):
        declaration = throwing_declaration(SYMBOL)
        self.assertIsNotNone(declaration)
        self.assertEqual(declaration['parameters'], ['Swift.Int'])
        self.assertEqual(declaration['result'], 'Swift.Void')
        self.assertEqual(declaration['error_register'], 'x21')
        self.assertEqual(declaration['convention'], 'swift_sync_untyped_throws')


class SwiftVoidThrowsBoundaryTests(unittest.TestCase):
    def test_stable_prefix_optional_macho_underscore(self):
        self.assertEqual(throwing_declaration(SYMBOL), throwing_declaration(SYMBOL[1:]))

    def test_current_model_preserves_previous_scalar_declaration_facts(self):
        from airs.swift_error_flow import MODEL
        declaration = throwing_declaration('_$s4Demo5parseyS2iKF')
        self.assertEqual(declaration['parameters'], ['Swift.Int'])
        self.assertEqual(declaration['result'], 'Swift.Int')
        self.assertEqual(MODEL, 'swift-sync-error-edges-v25')

    def test_async_typed_thunk_generic_nonthrowing_and_extra_args_refuse(self):
        prefix = '_$s12AIRSValidate8validate'
        for suffix in ('yySiF', 'yySiYaKF', 'yySiAA5FaultOYKF', 'yySiKFTA',
                       'yySiKF.llvm.1', 'yyxKlF', 'yySi_SitKF', 'yySiKFTj',
                       'ySiKF', 'yySiKFextra', 'yySizKF', 'yySiYaKFTu'):
            self.assertIsNone(throwing_declaration(prefix + suffix), suffix)

    def test_methods_contexts_and_invalid_identifiers_refuse(self):
        for symbol in ('_$s12AIRSValidate3BoxV8validateyySiKF',
                       '_$s012AIRSValidate8validateyySiKF',
                       '_$s12AIRSValidate08validateyySiKF',
                       '_$s12AIRSValidate8validat!yySiKF',
                       '_$s12AIRSValidate8validateyySiKF\x00'):
            self.assertIsNone(throwing_declaration(symbol))

    def test_new_signature_reuses_edge_region_entry_and_text_pipeline(self):
        from airs.swift_error_text import render_swift_error_text
        report = recover_swift_error_flow(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000), symbol=SYMBOL),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        call = report['calls'][0]
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual(call['callee']['result'], 'Swift.Void')
        self.assertEqual(call['presentation']['status'], 'eligible_structural_only')
        self.assertIn('Swift.Void', render_swift_error_text(report))
        self.assertIn('swift-sync-error-edges-v25', render_swift_error_text(report))

    def test_new_signature_alias_ambiguity_remains_declined(self):
        report = recover_swift_error_flow(image(symbol=SYMBOL, aliases=(('_$s4Demo5otheryySiKF', 32),)))
        self.assertEqual(report['calls'][0]['reason'], 'callee_symbol_absent_or_ambiguous')

    def test_void_return_does_not_remove_error_register_width_guard(self):
        report = recover_swift_error_flow(image((0x34000075,), symbol=SYMBOL))
        self.assertEqual(report['calls'][0]['reason'], 'narrow_error_test')

    def test_owned_shape_later_epilogue_jump_stays_declined(self):
        # Match owned error layout: test at+4 jumps+24, error block ends
        # with B at+20 to+28, not the success-entry boundary+24.
        report = recover_swift_error_flow(image((0xb40000b5, 0xaa1503e0, 0x94000005, 0x92800000, 0x14000002), symbol=SYMBOL),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        call = report['calls'][0]
        self.assertEqual(call['status'], 'recovered_candidate')
        self.assertEqual(call['error_region']['reason'], 'error_region_control_flow_unmodeled')
        self.assertEqual(call['presentation']['status'], 'blocked')

    def test_cli_json_and_text_accept_new_declaration(self):
        import contextlib
        import io
        import json
        from pathlib import Path
        import tempfile
        from airs.cli import main
        root = Path(__file__).resolve().parents[1] / 'local-evidence/swift-void-throws'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'void.macho'
            source.write_bytes(image((0xb4000095, 0xaa1503e0, 0x94000005, 0x92800000), symbol=SYMBOL).data)
            options = ['swift-error-flow', str(source), '--include-error-regions', '--validate-region-entries', '--include-structured-presentation']
            output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(main(options), 0)
            self.assertEqual(json.loads(output.getvalue())['calls'][0]['callee']['result'], 'Swift.Void')
            output = io.StringIO()
            with contextlib.redirect_stdout(output): self.assertEqual(main([*options, '--format', 'text']), 0)
            self.assertIn('Swift.Void', output.getvalue())
