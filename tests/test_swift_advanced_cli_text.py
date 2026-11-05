"""New option validation and versioned rendering; no target execution."""
import contextlib
import io
import unittest
from copy import deepcopy
from unittest.mock import patch
from airs.cli import main
from airs.swift_error_text import render_swift_error_text
from airs.types import InputError
from test_swift_error_text import report

class AdvancedCLITextTests(unittest.TestCase):
    def test_witness_prerequisites_precede_file_read(self):
        for flags in ([], ['--include-error-regions'], ['--include-error-regions', '--validate-region-entries']):
            with self.subTest(flags=flags), patch('airs.cli.resolve_input', side_effect=AssertionError('read')), contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(main(['swift-error-flow', '/missing', '--include-outcome-witnesses', *flags]), 2)

    def test_method_profile_requires_declaration_marker_and_choice_version(self):
        value = report(); value['model_version'] = 'swift-sync-error-edges-v38'
        with self.assertRaises(InputError): render_swift_error_text(value)
        value['declaration_model_version'] = 'swift-throwing-declarations-v1'
        with self.assertRaises(InputError): render_swift_error_text(value)
        value['return_choice_model_version'] = 'swift-return-choice-v46'
        self.assertIn('swift-sync-error-edges-v38', render_swift_error_text(value))

    def test_witness_rendering_requires_exact_markers(self):
        value=report(); value['calls'][0]['outcome_witness']={'status':'unresolved', 'reason':'missing'}
        with self.assertRaises(InputError): render_swift_error_text(value)
        value.update(outcome_witness_model_version='swift-outcome-witness-v1', outcome_validation_model_version='swift-outcome-validation-v1')
        self.assertIn('recorded validation; current bytes not reread',render_swift_error_text(value))
        value['outcome_validation_model_version']='future'
        with self.assertRaises(InputError): render_swift_error_text(value)

    def test_default_report_not_mutated(self):
        value=report(); before=deepcopy(value); render_swift_error_text(value)
        self.assertEqual(value,before)
