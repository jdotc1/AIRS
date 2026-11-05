"""Broad opt-in must never change the established Swift report contracts."""
import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch

from airs.cli import main
from airs.macho import parse_macho
from airs.report import dumps
from airs.swift_error_flow import recover_swift_error_flow
from airs.swift_error_text import render_swift_error_text


GOLDENS = Path(__file__).resolve().parents[1] / 'fixtures/swift-error-flow/broad-goldens'
REQUIRED = ['--include-outcome-witnesses', '--include-error-regions',
            '--validate-region-entries', '--include-structured-presentation']


class SwiftBroadProfileTests(unittest.TestCase):
    def test_profile_registry_preserves_exact_historical_contracts(self):
        from airs.swift_broad_profiles import PROFILES, BROAD_PROFILE
        from airs.swift_outcome_witness_models import PROFILES as old_profiles, WITNESS_MODEL, VALIDATION_MODEL
        self.assertEqual(old_profiles, {
            'legacy': ('swift-sync-error-edges-v37', 'swift-return-choice-v45'),
            'methods': ('swift-sync-error-edges-v38', 'swift-return-choice-v46')})
        for name, models in old_profiles.items():
            self.assertEqual((PROFILES[name].edge_model, PROFILES[name].return_choice_model), models)
            self.assertEqual(PROFILES[name].witness_model, WITNESS_MODEL)
            self.assertEqual(PROFILES[name].validation_model, VALIDATION_MODEL)
        broad = PROFILES[BROAD_PROFILE]
        self.assertEqual(broad.edge_model, 'swift-broad-error-flow-v1')
        self.assertEqual(broad.witness_model, 'swift-outcome-witness-v2')
        self.assertEqual(broad.validation_model, 'swift-outcome-validation-v2')
        with self.assertRaises(TypeError):
            PROFILES['legacy'] = broad

    def test_default_and_structured_outputs_equal_frozen_original_bytes(self):
        # Reuse the capture manifest as provenance; do not rehash sealed goldens.
        for name in ('edge', 'shared', 'unknown'):
            image = parse_macho((GOLDENS / (name + '.macho')).read_bytes())
            for structured in (False, True):
                with self.subTest(name=name, structured=structured):
                    report = recover_swift_error_flow(image,
                        include_error_regions=structured, validate_region_entries=structured,
                        include_structured_presentation=structured)
                    suffix = '.structured' if structured else '.default'
                    self.assertEqual(dumps(report).encode(), (GOLDENS / (name + suffix + '.json')).read_bytes())
                    if structured:
                        self.assertEqual(render_swift_error_text(report).encode(),
                                         (GOLDENS / (name + '.structured.txt')).read_bytes())

    def test_broad_options_refuse_before_resolving_input(self):
        variants = [[], *[[flag for flag in REQUIRED if flag != missing] for missing in REQUIRED],
                    REQUIRED + ['--include-swift-methods']]
        for flags in variants:
            with self.subTest(flags=flags), patch('airs.cli.resolve_input') as resolve:
                errors = io.StringIO()
                with contextlib.redirect_stderr(errors):
                    self.assertEqual(main(['swift-error-flow', 'absent.macho', '--swift-profile', 'broad-v1', *flags]), 2)
                self.assertEqual(json.loads(errors.getvalue())['error']['code'], 'swift_broad_options')
                resolve.assert_not_called()

    def test_broad_text_uses_separate_historical_check_renderer(self):
        report=dict(model_version='swift-broad-error-flow-v1',profile='broad-v1',calls=[],
            word_scan_complete=True,call_details_complete=True,outcome_witnesses_complete=True)
        with patch('airs.cli.resolve_input',return_value=Path('owned.macho')), \
                patch('airs.cli.recover_swift_broad_flow_path',return_value=report), \
                patch('airs.cli.render_swift_error_text') as legacy:
            output=io.StringIO()
            with contextlib.redirect_stdout(output):
                self.assertEqual(main(['swift-error-flow','owned.macho','--swift-profile','broad-v1',
                                       *REQUIRED,'--format','text']),0)
            legacy.assert_not_called()
            self.assertIn('Recorded checks only',output.getvalue())

    def test_broad_dispatch_is_separate_and_requires_admission(self):
        from airs.swift_broad_flow import recover_swift_broad_flow
        from airs.types import InputError
        with patch('airs.swift_error_flow.recover_swift_error_flow') as legacy:
            with self.assertRaises(InputError) as error:
                recover_swift_broad_flow(None)
            self.assertEqual(error.exception.code, 'swift_broad_admission')
            legacy.assert_not_called()

    def test_profile_default_is_none(self):
        from airs.cli import _parser
        self.assertIsNone(_parser().parse_args(['swift-error-flow', 'owned.macho']).swift_profile)

    def test_cli_default_and_structured_outputs_preserve_captured_bytes(self):
        for flags, suffix in (([], '.default.json'), (REQUIRED[1:], '.structured.json'),
                              (REQUIRED[1:] + ['--format', 'text'], '.structured.txt')):
            with self.subTest(suffix=suffix):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(['swift-error-flow', str(GOLDENS / 'edge.macho'), *flags]), 0)
                self.assertEqual(output.getvalue().encode(), (GOLDENS / ('edge' + suffix)).read_bytes())

    def test_cli_broad_dispatch_never_calls_historical_recovery(self):
        from airs.types import InputError
        with patch('airs.cli.resolve_input', return_value=Path('owned.macho')), \
                patch('airs.cli.recover_swift_error_flow_path') as legacy, \
                patch('airs.cli.recover_swift_broad_flow_path',
                      side_effect=InputError('swift_broad_pipeline_pending', 'pending')) as broad:
            errors = io.StringIO()
            with contextlib.redirect_stderr(errors):
                self.assertEqual(main(['swift-error-flow', 'owned.macho', '--swift-profile', 'broad-v1',
                                       *REQUIRED]), 2)
            broad.assert_called_once_with(Path('owned.macho'), requested_arch='auto')
            legacy.assert_not_called()
            self.assertEqual(json.loads(errors.getvalue())['error']['code'], 'swift_broad_pipeline_pending')
