"""New bounded ZIP framework-link resolution controls; nothing is extracted."""
import importlib.util
import io
from pathlib import Path
import stat
import unittest
import zipfile
ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('publication_framework_policy', ROOT / 'scripts/publication_gate.py')
policy = importlib.util.module_from_spec(spec); spec.loader.exec_module(policy)


def archive(files, links=(), directories=()):
    data = io.BytesIO()
    with zipfile.ZipFile(data, 'w') as output:
        for name in directories:
            output.writestr(name.rstrip('/') + '/', b'')
        for name, value in files:
            output.writestr(name, value)
        for name, target in links:
            info = zipfile.ZipInfo(name); info.create_system = 3
            info.external_attr = (stat.S_IFLNK | 0o777) << 16
            output.writestr(info, target)
    return data.getvalue()


class FrameworkLinkFirstTests(unittest.TestCase):
    def test_framework_current_directory_and_root_binary_links(self):
        root = 'AIRS.app/Contents/Frameworks/Python.framework/'
        data = archive([(root + 'Versions/3.15/Python', b'owned binary fixture'),
                        (root + 'Versions/3.15/Resources/Info.plist', b'owned metadata')],
                       [(root + 'Versions/Current', '3.15'),
                        (root + 'Python', 'Versions/Current/Python'),
                        (root + 'Resources', 'Versions/Current/Resources')])
        policy.inspect_payload(data, 'owned.zip')


class FrameworkLinkBoundaryTests(unittest.TestCase):
    def reject(self, files, links=(), directories=()):
        with self.assertRaises(policy.GateError):
            policy.inspect_payload(archive(files, links, directories), 'owned.zip')

    def test_links_to_implicit_and_explicit_directories(self):
        for dirs in ((), ('AIRS.app/real',)):
            policy.inspect_payload(archive([('AIRS.app/real/file', b'owned')],
                [('AIRS.app/alias', 'real')], dirs), 'owned.zip')

    def test_intermediate_link_parent_and_dot_normalization(self):
        policy.inspect_payload(archive([('AIRS.app/real/file', b'owned'), ('AIRS.app/real/sub/keep', b'owned')],
            [('AIRS.app/alias', 'real/sub'), ('AIRS.app/selected', './alias/../file')]), 'owned.zip')

    def test_link_target_is_relative_to_each_links_own_parent(self):
        policy.inspect_payload(archive([('AIRS.app/real/file', b'owned')],
            [('AIRS.app/links/first', '../alias/file'), ('AIRS.app/alias', 'real')]), 'owned.zip')

    def test_directory_target_trailing_slash_and_ancestor_link(self):
        policy.inspect_payload(archive([('AIRS.app/real/file', b'owned')],
            [('AIRS.app/alias', 'real/'), ('AIRS.app/root', '.')]), 'owned.zip')

    def test_parent_steps_are_applied_after_directory_link_resolution(self):
        policy.inspect_payload(archive([('AIRS.app/real/file', b'owned'), ('AIRS.app/real/sub/data', b'owned')],
            [('AIRS.app/substitute', 'real/sub'), ('AIRS.app/file', 'substitute/../file')]), 'owned.zip')

    def test_missing_directory_and_missing_final_member_refuse(self):
        for target in ('missing/file', 'real/missing'):
            self.reject([('AIRS.app/real/file', b'owned')], [('AIRS.app/link', target)])

    def test_cross_payload_escape_and_escape_then_reentry_refuse(self):
        files = [('AIRS.app/file', b'owned'), ('Other.app/file', b'owned')]
        for target in ('../Other.app/file', '../AIRS.app/file', '../../file'):
            self.reject(files, [('AIRS.app/link', target)])

    def test_absolute_backslash_empty_null_and_invalid_encoding_refuse(self):
        for target in ('/file', 'real\\file', '', 'real\x00file', b'\xff'):
            self.reject([('AIRS.app/file', b'owned')], [('AIRS.app/link', target)])

    def test_self_mutual_and_expanding_cycles_refuse(self):
        for links in ([('AIRS.app/a', 'a')], [('AIRS.app/a', 'b'), ('AIRS.app/b', 'a')],
                      [('AIRS.app/a', 'a/tail')]):
            self.reject([('AIRS.app/file', b'owned')], links)

    def test_exact_thirty_two_hop_bound_and_thirty_three_refusal(self):
        for count in (32, 33):
            links = [('AIRS.app/link%d' % i, 'link%d' % (i + 1) if i + 1 < count else 'file') for i in range(count)]
            data = archive([('AIRS.app/file', b'owned')], links)
            if count == 32: policy.inspect_payload(data, 'owned.zip')
            else:
                with self.assertRaises(policy.GateError): policy.inspect_payload(data, 'owned.zip')

    def test_canonical_directory_duplicates_and_alias_names_refuse(self):
        self.reject([('AIRS.app/dir', b'owned')], directories=('AIRS.app/dir',))
        self.reject([('AIRS.app/dir/file', b'one'), ('AIRS.app/dir/./file', b'two')])

    def test_member_paths_cannot_have_file_or_link_parents(self):
        self.reject([('AIRS.app/file', b'owned'), ('AIRS.app/file/child', b'owned')])
        self.reject([('AIRS.app/real/file', b'owned'), ('AIRS.app/alias/child', b'owned')],
                    [('AIRS.app/alias', 'real')])

    def test_file_target_cannot_be_traversed_or_have_trailing_slash(self):
        for target in ('file/child', 'file/', 'file/.', 'file/../file'):
            self.reject([('AIRS.app/file', b'owned')], [('AIRS.app/link', target)])

    def test_oversized_link_target_refuses_before_resolution(self):
        self.reject([('AIRS.app/file', b'owned')], [('AIRS.app/link', 'x' * 4097)])

    def test_resolution_step_and_implicit_namespace_budgets(self):
        from unittest.mock import patch
        with patch.object(policy, 'MAX_ARCHIVE_LINK_STEPS', 2):
            self.reject([('AIRS.app/real/file', b'owned')], [('AIRS.app/link', 'real/file')])
        with patch.object(policy, 'MAXIMUM_ENTRIES', 2):
            self.reject([('AIRS.app/a/b/c/d/e/file', b'owned')])

    def test_unchanged_archive_entry_and_expansion_limits_still_apply(self):
        from unittest.mock import patch
        data = archive([('AIRS.app/file', b'owned')], [('AIRS.app/link', 'file')])
        with patch.object(policy, 'MAXIMUM_ENTRIES', 1):
            with self.assertRaises(policy.GateError): policy.inspect_payload(data, 'owned.zip')
        output = io.BytesIO()
        with zipfile.ZipFile(output, 'w', compression=zipfile.ZIP_DEFLATED) as zipped:
            zipped.writestr('AIRS.app/file', b'x' * 10000)
        data = output.getvalue()
        with self.assertRaises(policy.GateError): policy.inspect_payload(data, 'owned.zip', maximum_bytes=len(data) + 100)

    def test_nested_framework_archive_keeps_resolving_and_scanning(self):
        inner = archive([('AIRS.app/versions/one/file', b'owned')],
                        [('AIRS.app/versions/current', 'one'), ('AIRS.app/file', 'versions/current/file')])
        policy.inspect_payload(archive([('delivery/owned.zip', inner)]), 'outer.zip')

    def test_link_targets_retain_publication_marker_checks(self):
        target = 'gh' + 'p_' + 'x' * 32
        self.reject([('AIRS.app/file', b'owned')], [('AIRS.app/link', target)])


class FrameworkLinkNamespaceDepthTests(unittest.TestCase):
    def test_member_component_depth_is_bounded_before_parent_expansion(self):
        accepted = '/'.join(['AIRS.app'] + ['d'] * 126 + ['file'])
        policy.inspect_payload(archive([(accepted, b'owned')]), 'owned.zip')
        excessive = '/'.join(['AIRS.app'] + ['d'] * 127 + ['file'])
        with self.assertRaises(policy.GateError):
            policy.inspect_payload(archive([(excessive, b'owned')]), 'owned.zip')
