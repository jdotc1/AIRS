"""Metadata-bound local build reuse; no compiler or content hashes."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

def load():
    spec = importlib.util.spec_from_file_location('reuse_native_build', ROOT / 'scripts/reuse_native_build.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

class NativeBuildReuseFirstTests(unittest.TestCase):
    def test_exact_metadata_reuses_only_recorded_build_directory(self):
        tool = load()
        with tempfile.TemporaryDirectory(dir=ROOT / 'local-evidence/handoff-strict-coverage') as folder:
            root = Path(folder); build = root / 'native/.build/owned/release'; build.mkdir(parents=True)
            (build / 'AIRSApp').write_bytes(b'owned'); (build / 'airs-entitlements').write_bytes(b'owned')
            (build / 'Lumen_LumenUI.bundle').mkdir(); (build / 'Lumen_LumenUI.bundle/theme.json').write_text('{}')
            for product in ('AIRSApp', 'airs-entitlements'): (build / product).chmod(0o755)
            keys = ('native/Sources', 'native/Package.swift', 'native/Vendor')
            receipt = {'schema': 'airs-native-build-reuse-v1', 'source_commit': 'a' * 40,
                'build_path': str(build), 'native_input_oids': dict.fromkeys(keys, 'b' * 40),
                'artifacts': {str(p.relative_to(build)): tool.metadata(p) for p in build.rglob('*') if p.is_file()}}
            target = root / 'receipt.json'; target.write_text(json.dumps(receipt))
            def git(source, *args): return 'b' * 40 if args[0] == 'rev-parse' else ''
            with patch.object(tool, 'git', side_effect=git): self.assertEqual(tool.reuse(root, target), build)


class NativeBuildReuseBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tool = load()
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / 'local-evidence/handoff-strict-coverage')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name); self.build = self.root / 'native/.build/owned/release'
        self.build.mkdir(parents=True)
        for name in ('AIRSApp', 'airs-entitlements'):
            (self.build / name).write_bytes(b'owned'); (self.build / name).chmod(0o755)
        (self.build / 'Lumen_LumenUI.bundle').mkdir()
        (self.build / 'Lumen_LumenUI.bundle/theme.json').write_text('{}')
        self.data = {'schema': 'airs-native-build-reuse-v1', 'source_commit': 'a' * 40,
            'build_path': str(self.build), 'native_input_oids': dict.fromkeys(self.tool.INPUTS, 'b' * 40),
            'artifacts': {str(p.relative_to(self.build)): self.tool.metadata(p) for p in self.build.rglob('*') if p.is_file()}}
        self.receipt = self.root / 'receipt.json'; self.save()

    def save(self): self.receipt.write_text(json.dumps(self.data))
    def git(self, root, *args): return 'b' * 40 if args[0] == 'rev-parse' else ''
    def reuse(self):
        with patch.object(self.tool, 'git', side_effect=self.git): return self.tool.reuse(self.root, self.receipt)

    def test_dirty_and_ignored_compiler_inputs_refuse(self):
        for operation in ('status', 'ls-files'):
            with patch.object(self.tool, 'git', side_effect=lambda root, *args: 'dirty' if args[0] == operation else self.git(root, *args)):
                with self.assertRaises(ValueError): self.tool.reuse(self.root, self.receipt)

    def test_accepted_and_head_source_oids_both_must_match(self):
        for prefix in ('a' * 40, 'HEAD'):
            def git(root, *args):
                return 'c' * 40 if args[0] == 'rev-parse' and args[1].startswith(prefix + ':') else self.git(root, *args)
            with patch.object(self.tool, 'git', side_effect=git):
                with self.assertRaises(ValueError): self.tool.reuse(self.root, self.receipt)

    def test_native_input_map_must_be_complete_and_exact(self):
        for mapping in ({}, {'native/Sources': 'b' * 40}, {**self.data['native_input_oids'], 'other': 'b' * 40}):
            self.data['native_input_oids'] = mapping; self.save()
            with self.assertRaises(ValueError): self.reuse()

    def test_source_commit_oid_and_schema_require_exact_values(self):
        original = dict(self.data)
        for key, value in (('schema', 'unknown'), ('source_commit', 'a' * 39), ('source_commit', 'HEAD')):
            self.data = {**original, key: value}; self.save()
            with self.assertRaises(ValueError): self.reuse()
        self.data = dict(original); self.data['native_input_oids'] = dict.fromkeys(self.tool.INPUTS, 'HEAD'); self.save()
        with self.assertRaises(ValueError): self.reuse()

    def test_build_directory_must_remain_inside_resolved_native_root(self):
        for path in (self.root, Path('native/.build/release'), self.root / 'native/.build'):
            self.data['build_path'] = str(path); self.save()
            with self.assertRaises(ValueError): self.reuse()
        (self.root / 'alias').symlink_to(self.build, target_is_directory=True)
        self.data['build_path'] = str(self.root / 'alias'); self.save()
        with self.assertRaises(ValueError): self.reuse()

    def test_artifact_records_cannot_escape_or_use_boolean_metadata(self):
        original = dict(self.data['artifacts'])
        for name in ('../AIRSApp', '/AIRSApp', 'Lumen_LumenUI.bundle/../other', './other', 'bad\\name'):
            self.data['artifacts'] = {**original, name: original['AIRSApp']}; self.save()
            with self.assertRaises(ValueError): self.reuse()
        self.data['artifacts'] = dict(original); self.data['artifacts']['AIRSApp'] = [True] * 6; self.save()
        with self.assertRaises(ValueError): self.reuse()

    def test_both_products_and_all_resource_files_are_required(self):
        original = dict(self.data['artifacts'])
        for name in original:
            self.data['artifacts'] = {key: value for key, value in original.items() if key != name}; self.save()
            with self.assertRaises(ValueError): self.reuse()

    def test_missing_added_and_changed_resource_artifacts_refuse(self):
        path = self.build / 'Lumen_LumenUI.bundle/theme.json'
        original = path.read_bytes(); path.unlink()
        with self.assertRaises((ValueError, OSError)): self.reuse()
        path.write_bytes(original)
        # Rebind only this new synthetic fixture before testing a different boundary.
        self.data['artifacts'][str(path.relative_to(self.build))] = self.tool.metadata(path); self.save()
        other = path.parent / 'extra.json'; other.write_text('{}')
        with self.assertRaises(ValueError): self.reuse()
        other.unlink(); path.write_text('changed')
        with self.assertRaises(ValueError): self.reuse()

    def test_executable_mode_or_metadata_changes_refuse(self):
        executable = self.build / 'AIRSApp'; executable.chmod(0o644)
        with self.assertRaises(ValueError): self.reuse()
        self.data['artifacts']['AIRSApp'] = self.tool.metadata(executable); self.save()
        with self.assertRaises(ValueError): self.reuse()

    def test_symlinked_resource_file_and_bundle_refuse(self):
        path = self.build / 'Lumen_LumenUI.bundle/theme.json'; path.unlink(); path.symlink_to(self.build / 'AIRSApp')
        with self.assertRaises(ValueError): self.reuse()
        path.unlink(); path.parent.rmdir(); path.parent.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(ValueError): self.reuse()

    def test_receipt_is_bounded_regular_and_non_symlinked(self):
        self.receipt.write_bytes(b'x' * (self.tool.MAX_RECEIPT_BYTES + 1))
        with self.assertRaises(ValueError): self.reuse()
        self.receipt.unlink(); self.receipt.symlink_to(self.build / 'AIRSApp')
        with self.assertRaises(ValueError): self.reuse()

    def test_cli_prints_path_only_after_success(self):
        import contextlib, io
        output = io.StringIO()
        with patch.object(self.tool, 'git', side_effect=self.git), contextlib.redirect_stdout(output):
            self.assertEqual(self.tool.main(['--source', str(self.root), '--receipt', str(self.receipt)]), 0)
        self.assertEqual(output.getvalue(), str(self.build) + '\n')
        output, errors = io.StringIO(), io.StringIO(); self.data['schema'] = 'unknown'; self.save()
        with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors):
            self.assertEqual(self.tool.main(['--source', str(self.root), '--receipt', str(self.receipt)]), 1)
        self.assertEqual(output.getvalue(), '')

    def test_untracked_build_files_outside_copied_products_do_not_change_membership(self):
        (self.build / 'compile.log').write_text('not an app input')
        self.assertEqual(self.reuse(), self.build)

    def test_reuse_never_calls_compiler_or_content_hash(self):
        observed = []
        def git(root, *args): observed.append(args); return self.git(root, *args)
        with patch.object(self.tool, 'git', side_effect=git), patch.object(self.tool.subprocess, 'run') as run:
            self.assertEqual(self.tool.reuse(self.root, self.receipt), self.build)
            run.assert_not_called()
        self.assertEqual(len([args for args in observed if args[0] == 'rev-parse']), 6)


    def test_new_empty_bundle_is_not_silently_copied(self):
        (self.build / 'Extra_Empty.bundle').mkdir()
        with self.assertRaises(ValueError): self.reuse()
