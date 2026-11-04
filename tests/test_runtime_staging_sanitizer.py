"""Fresh-stage runtime sanitation; no original interpreter or real stripping."""
import ast
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from fixture_storage import temporary_directory
from unittest.mock import patch
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))

def load():
    spec = importlib.util.spec_from_file_location('sanitize_runtime_staging', ROOT / 'scripts/sanitize_runtime_staging.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module

PRIVATE = '/' + 'Users' + '/builder/'
NEUTRAL = '/AIRS/runtime-build/'

class RuntimeSanitizerFirstTests(unittest.TestCase):
    def test_generated_json_preserves_nonpath_values_and_replaces_only_home_prefix(self):
        tool = load(); source = {'BUILD': PRIVATE + 'work/src', 'NUMBER': 7, 'FLAGS': [True, None, 'ordinary']}
        encoded, count = tool.sanitize_json(json.dumps(source))
        value = json.loads(encoded)
        self.assertEqual(value, {'BUILD': NEUTRAL + 'work/src', 'NUMBER': 7, 'FLAGS': [True, None, 'ordinary']})
        self.assertEqual(count, 1)


class RuntimeSanitizerBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.tool = load()
        self.temp = temporary_directory(ROOT)
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.stage = self.root / '.airs-package.owned'
        self.framework = self.stage / 'AIRS.app/Contents/Frameworks/Python.framework'
        self.version = self.framework / 'Versions/3.15'
        self.library = self.version / 'lib/python3.15'; self.library.mkdir(parents=True)
        self.config = self.library / '_sysconfigdata_owned.py'
        self.config.write_text('# Owned generated header and license\nbuild_time_vars = ' + repr({'PATH': PRIVATE + 'source', 'NUMBER': 7, 'FLAG': False}) + '\n')
        self.json = self.library / '_sysconfig_vars_owned.json'
        self.json.write_text(json.dumps({'PATH': PRIVATE + 'install', 'NUMBER': 9, 'PLAIN': 'stable'}))

    def literal(self, source): return ast.literal_eval(ast.parse(source).body[-1].value)

    def test_python_literal_preserves_header_and_nonpath_types(self):
        source = '# Owned license\n# Build ' + PRIVATE + 'work\nbuild_time_vars = ' + repr({
            'PATH': PRIVATE + 'src', 'INTEGER': 7, 'FLOAT': 1.25, 'BOOL': True, 'NONE': None,
            'TUPLE': (1, 'plain'), 'LIST': [False, 'plain'], 'BYTES': b'plain', 'SET': {1, 2}}) + ' # owned footer\n'
        output, count = self.tool.sanitize_python(source)
        value = self.literal(output)
        self.assertTrue(output.startswith('# Owned license\n'))
        self.assertTrue(output.endswith('# owned footer\n'))
        self.assertEqual(value['PATH'], NEUTRAL + 'src'); self.assertEqual(count, 2)
        self.assertEqual(value['TUPLE'], (1, 'plain')); self.assertEqual(value['BYTES'], b'plain')
        self.assertIs(value['BOOL'], True); self.assertIsNone(value['NONE']); self.assertEqual(value['SET'], {1, 2})

    def test_home_prefix_replacement_supports_repeated_values_and_bytes(self):
        home = '/' + 'home' + '/builder/'
        source = 'build_time_vars = ' + repr({'X': home + 'one ' + PRIVATE + 'two', 'Y': (home + 'three').encode()})
        output, count = self.tool.sanitize_python(source); value = self.literal(output)
        self.assertEqual(value['X'], NEUTRAL + 'one ' + NEUTRAL + 'two')
        self.assertEqual(value['Y'], (NEUTRAL + 'three').encode()); self.assertEqual(count, 3)

    def test_executable_and_nonliteral_python_are_rejected(self):
        for source in ('import os\nbuild_time_vars = {}', 'build_time_vars = dict()',
                       'build_time_vars = {"X": object()}', 'build_time_vars = {"X": name}',
                       'other = {}', 'build_time_vars = {}\nprint("execute")',
                       'build_time_vars = {"X": set()}', 'build_time_vars = {x: x for x in []}'):
            with self.assertRaises(ValueError): self.tool.sanitize_python(source)

    def test_duplicate_json_keys_and_nonfinite_values_are_rejected(self):
        for source in ('{"X":1,"X":2}', '[]', '{"X":NaN}', '{"X":1e400}'):
            with self.assertRaises(ValueError): self.tool.sanitize_json(source)
        with self.assertRaises(ValueError): self.tool.sanitize_python('build_time_vars = {"X": 1e400}')

    def test_path_keys_refuse_instead_of_changing_mapping_keys(self):
        with self.assertRaises(ValueError): self.tool.sanitize_json(json.dumps({PRIVATE + 'key': 'value'}))
        with self.assertRaises(ValueError): self.tool.sanitize_python('build_time_vars = ' + repr({PRIVATE + 'key': 'value'}))

    def test_non_staging_framework_and_symlink_ancestors_refuse(self):
        new_stage = self.root / 'prepared-runtime'; self.stage.rename(new_stage)
        prepared = new_stage / 'AIRS.app/Contents/Frameworks/Python.framework'
        with self.assertRaises(ValueError): self.tool.sanitize(prepared)
        (self.root / '.airs-package.alias').symlink_to(new_stage, target_is_directory=True)
        alias = self.root / '.airs-package.alias/AIRS.app/Contents/Frameworks/Python.framework'
        with self.assertRaises(ValueError): self.tool.sanitize(alias)
        self.assertIn(PRIVATE, (prepared / 'Versions/3.15/lib/python3.15/_sysconfigdata_owned.py').read_text())

    def test_only_developer_copy_directories_are_removed_and_ordinary_modules_preserved(self):
        doc = self.version / 'share/doc'; doc.mkdir(parents=True); (doc / 'example.txt').write_text('developer')
        config = self.library / 'config-3.15-darwin'; config.mkdir(); (config / 'Makefile').write_text('developer')
        header = self.version / 'include/keep.h'; header.parent.mkdir(); header.write_text('header stays')
        ordinary = self.library / 'ordinary.py'; ordinary.write_text('ordinary = ' + repr(PRIVATE + 'unchanged'))
        before = ordinary.read_bytes()
        with patch.object(self.tool, 'execute_check') as strip:
            result = self.tool.sanitize(self.framework); strip.assert_not_called()
        self.assertFalse(doc.exists()); self.assertFalse(config.exists())
        self.assertEqual(header.read_text(), 'header stays'); self.assertEqual(ordinary.read_bytes(), before)
        self.assertEqual(result['neutralized_home_prefixes'], 2)
        self.assertEqual(len(result['sanitized_configs']), 2)
        self.assertTrue(all(not name.startswith('/') for name in result['sanitized_configs']))

    def test_internal_symlinks_are_not_followed_or_modified(self):
        outside = self.root / 'outside.py'; outside.write_text(PRIVATE + 'unchanged')
        (self.library / '_sysconfigdata_link.py').symlink_to(outside)
        (self.framework / 'Versions/Current').symlink_to('3.15', target_is_directory=True)
        self.tool.sanitize(self.framework)
        self.assertEqual(outside.read_text(), PRIVATE + 'unchanged')
        self.assertTrue((self.framework / 'Versions/Current').is_symlink())

    def test_removal_directory_symlink_refuses_without_following(self):
        outside = self.root / 'developer'; outside.mkdir(); (outside / 'keep').write_text('preserved')
        (self.library / 'config-outside').symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ValueError): self.tool.sanitize(self.framework)
        self.assertEqual((outside / 'keep').read_text(), 'preserved')

    def test_config_and_inventory_bounds_refuse(self):
        with patch.object(self.tool, 'MAX_CONFIG_BYTES', 4):
            with self.assertRaises(ValueError): self.tool.sanitize(self.framework)
        with patch.object(self.tool, 'MAX_ENTRIES', 2):
            with self.assertRaises(ValueError): self.tool.sanitize(self.framework)
        with patch.object(self.tool, 'MAX_CONFIG_FILES', 1):
            with self.assertRaises(ValueError): self.tool.sanitize(self.framework)

    def test_invalid_python_is_rejected_before_any_developer_directory_removal(self):
        doc = self.version / 'share/doc'; doc.mkdir(parents=True)
        self.config.write_text('import os\nbuild_time_vars = {}')
        with self.assertRaises(ValueError): self.tool.sanitize(self.framework)
        self.assertTrue(doc.is_dir())
        self.assertFalse((self.stage / '.runtime-sanitizer-started').exists())

    def test_fresh_stage_is_one_shot_and_config_modes_are_preserved(self):
        self.config.chmod(0o444)
        self.tool.sanitize(self.framework)
        self.assertEqual(self.config.stat().st_mode & 0o777, 0o444)
        with self.assertRaises(FileExistsError): self.tool.sanitize(self.framework)

    def test_strip_is_fixed_owned_tool_and_original_modes_are_restored(self):
        import struct
        binary = self.version / 'Python'
        binary.write_bytes(b'\xcf\xfa\xed\xfe' + b'\x00' * 8 + struct.pack('<I', 6) + b'\x00' * 16)
        binary.chmod(0o555)
        with patch.object(self.tool, 'execute_check', return_value={'passed': True}) as strip:
            result = self.tool.sanitize(self.framework)
        strip.assert_called_once_with(['/usr/bin/strip', '-S', '-x', str(binary)])
        self.assertEqual(binary.stat().st_mode & 0o777, 0o555)
        self.assertEqual(result['stripped_code_count'], 1)
        self.assertEqual(result['stripped_code_members'], ['Versions/3.15/Python'])

    def test_strip_failure_refuses_without_binary_byte_substitution(self):
        import struct
        binary = self.version / 'Python'
        original = b'\xcf\xfa\xed\xfe' + b'\x00' * 8 + struct.pack('<I', 6) + b'\x00' * 16
        binary.write_bytes(original)
        with patch.object(self.tool, 'execute_check', return_value={'passed': False}):
            with self.assertRaises(ValueError): self.tool.sanitize(self.framework)
        self.assertEqual(binary.read_bytes(), original)

    def test_universal_code_header_is_recognized_without_execution(self):
        import struct
        binary = self.version / 'Python'; data = bytearray(96)
        data[:4] = b'\xca\xfe\xba\xbe'; struct.pack_into('>I', data, 4, 1); struct.pack_into('>I', data, 16, 64)
        data[64:68] = b'\xcf\xfa\xed\xfe'; struct.pack_into('<I', data, 76, 6)
        binary.write_bytes(data)
        self.assertEqual(self.tool.code_type(binary), 6)

    def test_special_files_refuse_before_mutation(self):
        import os
        os.mkfifo(self.library / 'pipe')
        with self.assertRaises(ValueError): self.tool.sanitize(self.framework)
        self.assertFalse((self.stage / '.runtime-sanitizer-started').exists())
