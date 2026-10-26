"""New CLI route and protected export using tiny owned Mach-O bytes."""
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest
from airs.cli import main
from test_swift_error_flow import image

ROOT = Path(__file__).resolve().parents[1]


class SwiftErrorFlowCLITests(unittest.TestCase):
    def invoke(self, args):
        output, errors = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            status = main(args)
        return status, output.getvalue(), errors.getvalue()

    def test_json_command_recovers_owned_edge(self):
        root = ROOT / 'local-evidence/swift-error-flow'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image().data)
            status, output, errors = self.invoke(['swift-error-flow', str(source)])
            self.assertEqual(status, 0, errors)
            report = json.loads(output)
            self.assertEqual(report['report_kind'], 'airs.swift_error_flow')
            self.assertEqual(report['summary']['recovered_candidate_count'], 1)

    def test_export_preserves_input(self):
        root = ROOT / 'local-evidence/swift-error-flow'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source, target = Path(folder) / 'owned.macho', Path(folder) / 'result.json'
            original = image().data; source.write_bytes(original)
            status, _, errors = self.invoke(['swift-error-flow', str(source), '--output', str(target)])
            self.assertEqual(status, 0, errors)
            self.assertEqual(json.loads(target.read_text())['summary']['recovered_candidate_count'], 1)
            self.assertEqual(source.read_bytes(), original)

    def test_input_overwrite_refuses(self):
        root = ROOT / 'local-evidence/swift-error-flow'
        root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; original = image().data; source.write_bytes(original)
            status, _, _ = self.invoke(['swift-error-flow', str(source), '--output', str(source)])
            self.assertEqual(status, 2)
            self.assertEqual(source.read_bytes(), original)
