import contextlib
import io
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from airs.cli import main

class SwiftBroadNativeOutputTests(unittest.TestCase):
    def test_broad_output_path_returns_success_without_legacy_report_kind(self):
        report = dict(model_version='swift-broad-error-flow-v1', word_scan_complete=True, call_details_complete=True, outcome_witnesses_complete=True, calls=[])
        output = io.StringIO()
        args = ['swift-error-flow', '--swift-profile', 'broad-v1', '--include-outcome-witnesses', '--include-error-regions', '--validate-region-entries', '--include-structured-presentation', '--output', '/owned/native-output.json', '/owned/input']
        with patch('airs.cli.resolve_input', return_value=Path('/owned/input')), patch('airs.cli.recover_swift_broad_flow_path', return_value=report), patch('airs.cli.atomic_write') as write, contextlib.redirect_stdout(output), contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(args), 0)
        self.assertEqual(json.loads(write.call_args.args[1]), report)
        self.assertEqual(json.loads(output.getvalue())['report_kind'], 'swift-broad-error-flow-v1')
