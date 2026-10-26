"""New bounded release-record boundaries; no real signing or product inspection."""
import importlib.util
from pathlib import Path
import unittest
from fixture_storage import temporary_directory
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

ROOT = Path(__file__).resolve().parents[1]

def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReleaseCandidateInitialTests(unittest.TestCase):
    def test_source_claim_records_exact_identity_and_build(self):
        from unittest.mock import patch
        tool = load('build_provenance')
        with patch.object(tool, 'git_output', side_effect=['a' * 40, '']):
            claim = tool.build_claim(ROOT, 'a' * 40, 'dev.airs.app', '13')
        self.assertEqual(claim['source_commit'], 'a' * 40)
        self.assertEqual(claim['bundle_id'], 'dev.airs.app')
        self.assertEqual(claim['build'], '13')


class ReleaseCandidateBoundaryTests(unittest.TestCase):
    def setUp(self):
        import tempfile
        self.temporary = temporary_directory(ROOT)
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.builder = load('build_provenance')
        self.tool = load('release_preflight')

    def app(self):
        import json, plistlib
        app = self.root / 'Owned.app'
        (app / 'Contents/MacOS').mkdir(parents=True)
        (app / 'Contents/Resources').mkdir()
        (app / 'Contents/Info.plist').write_bytes(plistlib.dumps({'CFBundleExecutable': 'Owned',
            'CFBundleIdentifier': 'dev.airs.app', 'CFBundleShortVersionString': '0.3.3', 'CFBundleVersion': '13'}))
        (app / 'Contents/MacOS/Owned').write_bytes(b'owned executable fixture; not executed')
        (app / 'Contents/Resources/AIRSBuildProvenance.json').write_text(json.dumps({
            'schema': 'airs-source-build-record-v1', 'source_repository': 'jdotc1/AIRS',
            'source_commit': 'a' * 40, 'bundle_id': 'dev.airs.app', 'build': '13',
            'provenance_strength': 'builder_recorded_not_reproducibly_attested'}))
        return app

    def test_source_mismatch_and_dirty_state_refuse(self):
        from unittest.mock import patch
        with patch.object(self.builder, 'git_output', return_value='b' * 40):
            with self.assertRaises(ValueError): self.builder.build_claim(ROOT, 'a' * 40, 'dev.airs.app', '13')
        with patch.object(self.builder, 'git_output', side_effect=['a' * 40, ' M source.py']):
            with self.assertRaises(ValueError): self.builder.build_claim(ROOT, 'a' * 40, 'dev.airs.app', '13')

    def test_invalid_identity_refuses_before_git(self):
        from unittest.mock import patch
        for commit, bundle, build in [('a' * 39, 'dev.airs.app', '13'), ('a' * 40, '../app', '13'),
                                     ('a' * 40, 'dev.airs.app', '0'), ('a' * 40, 'dev.airs.app', '13/1')]:
            with patch.object(self.builder, 'git_output') as git:
                with self.assertRaises(ValueError): self.builder.build_claim(ROOT, commit, bundle, build)
                git.assert_not_called()

    def test_claim_output_is_exclusive_and_refuses_symlink_parent(self):
        target = self.root / 'claim.json'; self.builder.write_exclusive(target, 'first')
        with self.assertRaises(FileExistsError): self.builder.write_exclusive(target, 'second')
        self.assertEqual(target.read_text(), 'first')
        (self.root / 'alias').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): self.builder.write_exclusive(self.root / 'alias/other.json', 'other')

    def test_claim_binds_commit_bundle_build_repository_and_schema(self):
        import json
        app = self.app(); path = app / 'Contents/Resources/AIRSBuildProvenance.json'
        original = json.loads(path.read_text())
        self.assertTrue(self.tool.embedded_provenance(app, 'a' * 40, 'dev.airs.app', '13')['matches_request'])
        for key, changed in [('source_commit', 'b' * 40), ('bundle_id', 'dev.other.app'), ('build', '14'),
                             ('source_repository', 'other/repo'), ('schema', 'unknown'), ('provenance_strength', 'proven')]:
            fields = dict(original); fields[key] = changed; path.write_text(json.dumps(fields))
            self.assertFalse(self.tool.embedded_provenance(app, 'a' * 40, 'dev.airs.app', '13')['matches_request'])

    def test_missing_malformed_and_excessive_claims_never_match(self):
        app = self.app(); path = app / 'Contents/Resources/AIRSBuildProvenance.json'
        path.unlink()
        self.assertFalse(self.tool.embedded_provenance(app, 'a' * 40, 'dev.airs.app', '13')['matches_request'])
        for data in ('not json', '[]', 'x' * 16385):
            path.write_text(data)
            self.assertFalse(self.tool.embedded_provenance(app, 'a' * 40, 'dev.airs.app', '13')['matches_request'])

    def test_symlinked_resources_cannot_supply_claim(self):
        import shutil
        app = self.app(); resources = app / 'Contents/Resources'; moved = self.root / 'resources'
        resources.rename(moved); resources.symlink_to(moved, target_is_directory=True)
        self.assertFalse(self.tool.embedded_provenance(app, 'a' * 40, 'dev.airs.app', '13')['matches_request'])

    def test_principal_traversal_and_parent_symlink_refuse(self):
        import plistlib
        app = self.app(); path = app / 'Contents/Info.plist'; original = plistlib.loads(path.read_bytes())
        for label in ('../Owned', '.', '..', '/Owned'):
            fields = dict(original); fields['CFBundleExecutable'] = label; path.write_bytes(plistlib.dumps(fields))
            with self.assertRaises(ValueError): self.tool.candidate_metadata(app)
        path.write_bytes(plistlib.dumps(original))
        directory = app / 'Contents/MacOS'; directory.rename(self.root / 'executables')
        directory.symlink_to(self.root / 'executables', target_is_directory=True)
        with self.assertRaises(ValueError): self.tool.candidate_metadata(app)

    def test_special_and_oversized_files_refuse(self):
        import os
        path = self.root / 'fifo'; os.mkfifo(path)
        with self.assertRaises(ValueError): self.tool.read_file(path, 20)
        path = self.root / 'large'; path.write_bytes(b'x' * 21)
        with self.assertRaises(ValueError): self.tool.read_file(path, 20)

    def test_identity_mismatch_skips_platform_checks(self):
        from unittest.mock import patch
        app = self.app()
        with patch.object(self.tool, 'execute_check') as check:
            result = self.tool.evaluate(app, 'a' * 40, 'dev.airs.app', '14')
            check.assert_not_called()
        self.assertFalse(result['release_gate_passed'])

    def test_platform_checks_stop_on_first_failure(self):
        from unittest.mock import patch
        app = self.app()
        with patch.object(self.tool.sys, 'platform', 'darwin'), patch.object(self.tool, 'execute_check', return_value={'passed': False}) as check:
            result = self.tool.evaluate(app, 'a' * 40, 'dev.airs.app', '13')
            self.assertEqual(check.call_count, 1)
        self.assertFalse(result['release_gate_passed'])

    def test_all_three_checks_are_required_with_separate_acceptance_limits(self):
        from unittest.mock import patch
        app = self.app()
        with patch.object(self.tool.sys, 'platform', 'darwin'), patch.object(self.tool, 'execute_check', return_value={'passed': True}) as check:
            result = self.tool.evaluate(app, 'a' * 40, 'dev.airs.app', '13')
        self.assertEqual(check.call_count, 3)
        self.assertTrue(result['release_gate_passed'])
        self.assertTrue(any('Clean-host' in line for line in result['limitations']))

    def test_receipt_is_new_outside_app_and_refuses_symlink_ancestors(self):
        app = self.app()
        for destination in (app / 'receipt.json', app / 'Contents/receipt.json'):
            with self.assertRaises(ValueError): self.tool.receipt_destination(destination, app)
        target = self.root / 'receipt.json'; target.write_text('preserve')
        with self.assertRaises(ValueError): self.tool.receipt_destination(target, app)
        (self.root / 'alias').symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): self.tool.receipt_destination(self.root / 'alias/new.json', app)
        self.assertEqual(self.tool.receipt_destination(self.root / 'new.json', app), self.root / 'new.json')

    def test_existing_receipt_refuses_before_evaluate(self):
        import contextlib, io
        from unittest.mock import patch
        app = self.app(); target = self.root / 'receipt.json'; target.write_text('preserve')
        with patch.object(self.tool, 'evaluate') as evaluate, contextlib.redirect_stderr(io.StringIO()):
            status = self.tool.main(['--app', str(app), '--expected-source-commit', 'a' * 40,
                                    '--expected-bundle-id', 'dev.airs.app', '--expected-build', '13', '--json-out', str(target)])
        self.assertEqual(status, 1); evaluate.assert_not_called()
        self.assertEqual(target.read_text(), 'preserve')

    def test_owned_command_output_limit_and_timeout_are_bounded(self):
        from unittest.mock import patch
        result = self.tool.execute_check([sys.executable, '-c', 'print("owned")'])
        self.assertTrue(result['passed'])
        with patch.object(self.tool, 'MAX_CAPTURE_BYTES', 16):
            result = self.tool.execute_check([sys.executable, '-c', 'print("x" * 1024)'])
        self.assertFalse(result['passed']); self.assertEqual(result['failure'], 'output_limit')
        with patch.object(self.tool, 'CHECK_TIMEOUT', 0.02):
            result = self.tool.execute_check([sys.executable, '-c', 'import time; time.sleep(1)'])
        self.assertFalse(result['passed']); self.assertEqual(result['failure'], 'timeout')
