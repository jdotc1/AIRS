import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('log_export_packager', ROOT / 'scripts/package_swift_broad_handback.py')
PACKAGER = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGER)


class CompilerLogExportTests(unittest.TestCase):
    def test_owned_compiler_log_is_retained_as_a_relocated_evidence_view(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'local-evidence/swift-broad') as directory:
            capture = Path(directory)
            for name in ('source-manifest.json', 'compiler-index.json'):
                (capture / name).write_text(json.dumps({'fixture': 'new authored export input'}))
            source = capture / 'Owned.swift'
            source.write_text('public let originalMeasurement = 1\n')
            for name in ('nm-O.txt', 'objdump-O.txt', 'compile-O.log'):
                (capture / name).write_text('/Users/example/original/capture/Owned.swift: recorded diagnostic\n')
            receipt = {'modes': {'O': {'command': ['swiftc', 'Owned.swift', '-o', 'Owned.dylib']}}}
            payload = {}
            PACKAGER.capture_payload('primary', capture, receipt,
                [('/Users/example/original/capture', 'captures/primary')], payload, PACKAGER.EvidenceBudget(), [source])
            exported = payload['captures/primary/compile-O.log'].decode()
            self.assertIn('captures/primary/Owned.swift: recorded diagnostic', exported)
            self.assertNotIn('/Users/example/original', exported)
            self.assertIn('SANITIZED/RELOCATED', exported)


if __name__ == '__main__':
    unittest.main()
