import importlib.util
import io
import json
from pathlib import Path
import subprocess
import tempfile
import sys
from unittest.mock import patch
import unittest
import zipfile

SCRIPT = Path(__file__).resolve().parents[1] / 'scripts' / 'publication_gate.py'

class PublicationGateTests(unittest.TestCase):
    def load(self, name='publication_gate'):
        script = SCRIPT.parent / (name + '.py')
        sys.path.insert(0, str(SCRIPT.parent))
        self.addCleanup(lambda: sys.path.remove(str(SCRIPT.parent)))
        spec = importlib.util.spec_from_file_location(name, script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_path_classes_and_credentials_reject_without_echo(self):
        gate = self.load()
        values = [b'/' + b'Users/person/file', b'/' + b'home/person/file',
                  b'~/' + b'Developer/project', b'Developer/' + b'Codex',
                  b'/private/tmp/' + b'claude-501/run', b'-Users-' + b'person-project',
                  b'ghp_' + b'a' * 35, b'sk-' + b'a' * 30,
                  b'-----BEGIN ' + b'PRIVATE KEY-----']
        for value in values:
            with self.subTest(value=value[:3]):
                with self.assertRaises(gate.GateError) as result:
                    gate.inspect_bytes(value, 'input')
                self.assertNotIn(value.decode(), str(result.exception))
        gate.inspect_bytes(b'repository-relative docs/example.md', 'input')
        gate.inspect_bytes(b'/Users/example/Fixtures/test', 'fixture')

    def test_identity_and_trailers_are_separate_checks(self):
        gate = self.load()
        gate.inspect_identity('138259519+jdotc1@users.noreply.github.com')
        gate.inspect_identity('noreply@github.com')
        with self.assertRaises(gate.GateError):
            gate.inspect_identity('private@example.org')
        with self.assertRaises(gate.GateError):
            gate.inspect_message('Change\nCo-' + 'authored-by: Someone')

    def test_archives_are_scanned_recursively_and_traversal_rejects(self):
        gate = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            inner = io.BytesIO()
            with zipfile.ZipFile(inner, 'w') as archive:
                archive.writestr('note.txt', '~/' + 'Developer/private')
            path = root / 'source.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('nested.zip', inner.getvalue())
            with self.assertRaises(gate.GateError): gate.inspect_asset(path)
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('../escape', 'safe')
            with self.assertRaises(gate.GateError): gate.inspect_asset(path)

    def test_archive_symlinks_and_expansion_limit_fail_closed(self):
        gate = self.load()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                entry = zipfile.ZipInfo('alias'); entry.create_system = 3
                entry.external_attr = 0o120777 << 16
                archive.writestr(entry, 'target')
            with self.assertRaises(gate.GateError): gate.inspect_asset(path)
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('large.txt', 'a' * 200)
            with self.assertRaises(gate.GateError): gate.inspect_asset(path, maximum_bytes=100)

    def test_exact_receipt_reuse_and_changed_asset_rejection(self):
        gate = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); path = root / 'note.txt'; receipt = root / 'receipt.json'
            path.write_text('safe')
            first = gate.check_files([path], receipt)
            self.assertEqual(first['inspected'], 1)
            self.assertEqual(gate.check_files([path], receipt)['reused'], 1)
            path.write_text('~/' + 'Developer/private')
            with self.assertRaises(gate.GateError): gate.check_files([path], receipt)

    def test_git_range_sees_intermediate_leak_and_private_author(self):
        gate = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            def git(*args):
                return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()
            git('init'); git('config', 'user.name', 'Maintainer')
            git('config', 'user.email', '138259519+jdotc1@users.noreply.github.com')
            (root / 'file').write_text('safe'); git('add', '.'); git('commit', '-qm', 'base')
            base = git('rev-parse', 'HEAD')
            (root / 'file').write_text('~/' + 'Developer/private'); git('commit', '-qam', 'intermediate')
            (root / 'file').write_text('safe again'); git('commit', '-qam', 'remove')
            with self.assertRaises(gate.GateError): gate.check_git(root, base, 'HEAD')
            git('reset', '--hard', base); git('config', 'user.email', 'private@example.org')
            (root / 'file').write_text('new safe'); git('commit', '-qam', 'identity')
            with self.assertRaises(gate.GateError): gate.check_git(root, base, 'HEAD')

    def test_publication_requires_declared_surface_scope(self):
        gate = self.load()
        with self.assertRaises(gate.GateError): gate.validate_plan({'action': 'release'})
        with self.assertRaises(gate.GateError):
            gate.validate_plan({'action': 'release', 'repository': 'jdotc1/AIRS', 'base': 'main', 'head': 'HEAD',
                                'text': [], 'assets': []})

    def repository(self, root):
        def git(*args):
            return subprocess.check_output(['git', '-C', str(root), *args], stderr=subprocess.DEVNULL).decode().strip()
        git('init'); git('config', 'user.name', 'Maintainer')
        git('config', 'user.email', '138259519+jdotc1@users.noreply.github.com')
        (root / 'file').write_text('safe'); git('add', '.'); git('commit', '-qm', 'accepted base')
        return git, git('rev-parse', 'HEAD')

    def test_source_archive_cannot_hide_a_marker(self):
        gate = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); git, base = self.repository(root)
            with zipfile.ZipFile(root / 'fixture.data', 'w') as archive:
                archive.writestr('note', '~/' + 'Developer/private')
            git('add', '.'); git('commit', '-qm', 'archive')
            with self.assertRaises(gate.GateError): gate.check_git(root, base, 'HEAD')

    def test_semantically_broken_home_path_rejects(self):
        gate = self.load()
        code = b'homeDirectoryFor' + b'CurrentUser' + b'.appendingPath' + b'Component("Work")'
        with self.assertRaises(gate.GateError): gate.inspect_bytes(code, 'source')

    def test_archive_internal_link_and_directory_budget(self):
        gate = self.load()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'source.zip'
            with zipfile.ZipFile(path, 'w') as archive:
                archive.writestr('App/Versions/one/', '')
                entry = zipfile.ZipInfo('App/Versions/Current'); entry.create_system = 3
                entry.external_attr = 0o120777 << 16
                archive.writestr(entry, 'one')
            gate.inspect_asset(path)
            with patch.object(gate, 'MAXIMUM_ENTRIES', 1):
                with self.assertRaises(gate.GateError): gate.inspect_asset(path)

    def test_export_preserves_committed_bytes_and_refuses_changed_leak(self):
        exporter = self.load('export-public-source')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); git, base = self.repository(root)
            output = root / 'out.zip'
            exporter.export(root, base, base, output)
            with zipfile.ZipFile(output) as archive:
                self.assertEqual(archive.read('AIRS-source/file'), b'safe')
            output.unlink()
            (root / 'file').write_text('~/' + 'Developer/private'); git('commit', '-qam', 'bad export')
            with self.assertRaises(ValueError): exporter.export(root, base, 'HEAD', output)
            self.assertFalse(output.exists())

    def test_hook_install_refuses_overwrite_and_binds_exact_baseline(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); git, base = self.repository(root)
            script = SCRIPT.parent / 'configure-publication-gates.py'
            command = [sys.executable, str(script), '--accepted-base', base, '--evidence', 'synthetic acceptance']
            subprocess.run(command, cwd=root, check=True, capture_output=True)
            self.assertEqual(git('config', '--get', 'airs.publicationBaseline'), base)
            hook = root / '.git/hooks/pre-push'
            hook.write_text('#!/bin/sh\nexit 0\n')
            result = subprocess.run(command, cwd=root, capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('exit 0', hook.read_text())

    def test_remote_bindings_fail_closed_without_network(self):
        publish = self.load('publish-public')
        with patch.object(publish.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, 'different\trefs/heads/main\n', '')):
            with self.assertRaises(ValueError): publish.require_remote_head('.', 'main', 'expected')
        with patch.object(publish.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 0)]):
            with self.assertRaises(ValueError): publish.require_new_remote_tag('.', 'v1')
        with patch.object(publish.subprocess, 'run', side_effect=[subprocess.CompletedProcess([], 1), subprocess.CompletedProcess([], 2)]):
            publish.require_new_remote_tag('.', 'v1')

    def test_annotated_tag_identity_is_checked(self):
        gate = self.load()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); git, base = self.repository(root)
            git('config', 'user.email', 'private@example.org')
            git('tag', '-am', 'release', 'v1')
            with self.assertRaises(gate.GateError): gate.check_git(root, base, 'v1')

    def test_zip64_and_false_entry_count_reject_before_zipfile(self):
        import struct
        gate = self.load()
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, 'w') as archive:
            archive.writestr('one', 'safe'); archive.writestr('two', 'safe')
        original = stream.getvalue(); offset = original.rfind(b'PK\x05\x06')
        false_count = bytearray(original)
        struct.pack_into('<2H', false_count, offset + 8, 1, 1)
        with patch.object(gate.zipfile, 'ZipFile', side_effect=AssertionError('must reject before allocation')):
            with self.assertRaises(gate.GateError): gate.inspect_payload(bytes(false_count), 'source.zip')
            locator = b'PK\x06\x07' + b'\x00' * 16
            with self.assertRaises(gate.GateError): gate.inspect_payload(original[:offset] + locator + original[offset:], 'source.zip')

    def test_export_aggregate_bound_removes_partial_output(self):
        exporter = self.load('export-public-source')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); git, base = self.repository(root)
            output = root / 'out.zip'
            with patch.object(exporter, 'MAXIMUM_BYTES', 1):
                with self.assertRaises(ValueError): exporter.export(root, base, base, output)
            self.assertFalse(output.exists())

    def test_installed_hook_checks_source_without_network(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); git, base = self.repository(root)
            git('remote', 'add', 'origin', 'https://github.com/jdotc1/AIRS.git')
            subprocess.run([sys.executable, str(SCRIPT.parent / 'configure-publication-gates.py'),
                            '--accepted-base', base, '--evidence', 'synthetic acceptance'], cwd=root, check=True, capture_output=True)
            (root / 'file').write_text('changed safe'); git('commit', '-qam', 'new source')
            head = git('rev-parse', 'HEAD')
            command = [sys.executable, str(SCRIPT.parent / 'publication-pre-push.py'), 'origin', 'https://github.com/jdotc1/AIRS.git']
            line = 'refs/heads/main ' + head + ' refs/heads/main ' + base + '\n'
            first = subprocess.run(command, cwd=root, input=line, text=True, capture_output=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            (root / 'file').write_text('~/' + 'Developer/private'); git('commit', '-qam', 'unsafe source')
            head = git('rev-parse', 'HEAD')
            bad = subprocess.run(command, cwd=root, input='refs/heads/main ' + head + ' refs/heads/main ' + base + '\n', text=True, capture_output=True)
            self.assertNotEqual(bad.returncode, 0)

    def test_execute_actions_use_inspected_source_and_confirm_remote_metadata(self):
        publish = self.load('publish-public')
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); notes = root / 'notes.md'; notes.write_text('safe notes')
            asset = root / 'app.txt'; asset.write_text('safe asset')
            oid = 'a' * 40
            for action in ('push', 'pull_request', 'release'):
                metadata = {'push': {'destination_ref': 'refs/heads/main'},
                            'pull_request': {'base_branch': 'main', 'head_branch': 'feature', 'title': 'Change'},
                            'release': {'tag': 'v1', 'title': 'Release'}}[action]
                plan = {'action': action, 'repository': 'jdotc1/AIRS', 'base': oid, 'head': oid,
                        'text': [] if action == 'push' else [str(notes)],
                        'assets': [str(asset)] if action == 'release' else [], 'public_metadata': metadata}
                path = root / 'plan.json'; path.write_text(json.dumps(plan))
                def fake_git(checkout, *args):
                    if args[0] == 'status': return b''
                    if args[0] == 'remote': return b'https://github.com/jdotc1/AIRS.git\n'
                    if '--git-common-dir' in args: return str(root / '.git').encode()
                    return oid.encode()
                responses = [b'jdotc1\n', 'https://github.com/jdotc1/AIRS/pull/1' if action == 'pull_request' else '']
                if action == 'pull_request':
                    responses += [json.dumps({'headRefOid': oid, 'baseRefName': 'main', 'title': 'Change', 'body': 'safe notes', 'url': 'public'})]
                if action == 'release':
                    responses += [json.dumps({'tagName': 'v1', 'name': 'Release', 'body': 'safe notes', 'assets': [{'name': 'app.txt', 'size': 10}]}), oid + '\trefs/tags/v1\n']
                with self.subTest(action=action), patch.object(publish.sys, 'argv', ['publish', '--plan', str(path), '--receipt', str(root / '.git/airs-publication-receipt.json'), '--execute']), patch.object(publish, 'git', side_effect=fake_git), patch.object(publish, 'check_git', return_value={'head': oid}), patch.object(publish, 'check_files'), patch.object(publish, 'require_remote_head'), patch.object(publish, 'require_new_remote_tag'), patch.object(publish.subprocess, 'check_output', side_effect=responses) as commands:
                    publish.main()
                    delivered = commands.call_args_list[1].args[0]
                    self.assertIn('jdotc1/AIRS' if action != 'push' else oid + ':refs/heads/main', delivered)

if __name__ == '__main__': unittest.main()
