"""Staging-only composition of stripping, qualified metadata changes and atomic output."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from test_runtime_staging_sanitizer import load, ROOT
from test_runtime_source_paths import thin, PRIVATE


class RuntimeStagingIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.tool = load()
        parent = ROOT / 'local-evidence/handoff-strict-coverage'
        parent.mkdir(parents=True, exist_ok=True)
        temporary = tempfile.TemporaryDirectory(dir=parent); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.framework = self.root / '.airs-package.owned/AIRS.app/Contents/Frameworks/Python.framework'
        self.version = self.framework / 'Versions/3.15'; (self.version / 'lib/python3.15').mkdir(parents=True)
        self.original = thin(); self.binary = self.version / 'Python'; self.binary.write_bytes(self.original); self.binary.chmod(0o555)
        self.prepared = self.root / 'prepared-original'; self.prepared.write_bytes(self.original)

    def test_qualified_literal_is_written_only_to_staging_and_reported(self):
        with patch.object(self.tool, 'execute_check', return_value={'passed': True}) as strip:
            result = self.tool.sanitize(self.framework)
        strip.assert_called_once_with(['/usr/bin/strip', '-S', '-x', str(self.binary)])
        self.assertEqual(result['normalized_native_source_prefixes'], 1)
        self.assertEqual(result['normalized_native_members'], ['Versions/3.15/Python'])
        self.assertEqual(len(self.binary.read_bytes()), len(self.original))
        self.assertNotIn(PRIVATE, self.binary.read_bytes())
        self.assertEqual(self.binary.stat().st_mode & 0o777, 0o555)
        self.assertEqual(self.prepared.read_bytes(), self.original)
        self.assertFalse(list(self.version.glob('.runtime-code-*')))

    def test_unqualified_metadata_refuses_without_writing_binary(self):
        with patch.object(self.tool, 'execute_check', return_value={'passed': True}):
            with patch.object(self.tool, 'normalize_source_paths', side_effect=ValueError('unmodeled')):
                with self.assertRaises(ValueError): self.tool.sanitize(self.framework)
        self.assertEqual(self.binary.read_bytes(), self.original)
        self.assertEqual(self.binary.stat().st_mode & 0o777, 0o555)
        self.assertEqual(self.prepared.read_bytes(), self.original)
