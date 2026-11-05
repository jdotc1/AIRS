"""Generator/index checks only: never compile or revisit a sealed corpus."""
import importlib.util
from pathlib import Path
import tempfile
import sys
import time
import unittest

SPEC = importlib.util.spec_from_file_location('swift_fixture_matrix', Path(__file__).parents[1] / 'scripts/swift_fixture_matrix.py')
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)

class BroadCorpusTests(unittest.TestCase):
    def test_deterministic_diverse_owned_declarations(self):
        source, manifest = matrix.generate()
        self.assertEqual((source, manifest), matrix.generate())
        self.assertGreaterEqual(len(manifest['cases']), 420)
        self.assertGreaterEqual(len({tuple(c['feature_vector']) for c in manifest['cases']}), 420)
        self.assertGreaterEqual(len({c['signature_shape'] for c in manifest['cases']}), 80)
        # Threshold constants and spelling cannot establish source diversity.
        self.assertGreaterEqual(len({tuple(c['feature_vector'][:9] + c['feature_vector'][10:]) for c in manifest['cases']}), 420)
        for category, minimum in matrix.MINIMUMS.items():
            self.assertGreaterEqual(sum(c['category'] == category for c in manifest['cases']), minimum)
        for case in manifest['cases']:
            self.assertEqual(len(case['source_callsites']), 2)
            self.assertIn(case['declaration'], source)
            self.assertTrue(case['body_semantic'])
        self.assertGreaterEqual(sum(c['owner'] != 'module' for c in manifest['cases']), 340)
        self.assertIn('rethrows', source)
        self.assertIn('throws(BroadError)', source)
        self.assertIn('async throws', source)

    def test_index_uses_words_and_raw_symbols(self):
        dump = '''0000000000001000 <_$sBroad_broad_caller_0000_0>:\n    1000: 00 04 00 94  bl 0x2000 <_$sBroad_broad_case_0000>\n    1004: 20 00 3f d6  blr x1\n    1008: c0 03 5f d6  ret\n'''
        rows = matrix.parse_disassembly(dump)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['instruction_word'], '0x94000400')
        self.assertEqual(rows[0]['pc'], '0x1000')
        self.assertEqual(rows[0]['target_pc'], '0x2000')
        self.assertEqual(rows[1]['call_kind'], 'indirect')
        self.assertIsNone(rows[1]['target_pc'])

    def test_output_refuses_overwrite_and_has_explicit_source_status(self):
        with tempfile.TemporaryDirectory() as path:
            matrix.write_sources(Path(path))
            with self.assertRaises(FileExistsError):
                matrix.write_sources(Path(path))
            import json
            manifest = json.loads((Path(path) / 'manifest.json').read_text())
            self.assertEqual(manifest['evidence_state'], 'source_only_uncompiled')
            self.assertEqual(manifest['emitted_observations'], 0)

    def test_bounded_runner_refuses_partial_oversize_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            with self.assertRaisesRegex(RuntimeError, 'bound|Bound'):
                matrix.run_bounded([sys.executable, '-c', 'print("x" * 1024)'],
                                   root / 'command.log', time.monotonic() + 5, root, limit=32)
            self.assertGreater((root / 'command.log').stat().st_size, 32)
            self.assertTrue((root / 'compiler-tmp').is_dir())
            self.assertTrue((root / 'module-cache').is_dir())

    def test_run_name_resolves_inside_existing_root_and_rejects_escape(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.assertEqual(matrix.resolve_run_output(root, 'broad-swift-initial-v1'), root.resolve() / 'broad-swift-initial-v1')
            for bad in ('', '.', '..', '../escape', '/absolute', 'a/b', 'a\\b'):
                with self.assertRaises(ValueError):
                    matrix.resolve_run_output(root, bad)
            outside = root / 'outside'
            outside.symlink_to(root.parent, target_is_directory=True)
            with self.assertRaises(ValueError):
                matrix.resolve_run_output(root, 'outside')

    def test_v2_has_real_return_parameter_and_nominal_breadth(self):
        source, manifest = matrix.generate_v2()
        cases = manifest['cases']
        self.assertEqual(len(cases), 420)
        self.assertGreaterEqual(len({c['return_family'] for c in cases}), 23)
        self.assertGreaterEqual(len({c['signature_shape'] for c in cases}), 80)
        self.assertEqual(len({tuple(c['feature_vector']) for c in cases}), 420)
        self.assertEqual(len({c['parameter_form'] for c in cases}), 12)
        self.assertEqual(len({s['geometry'] for c in cases for s in c['source_callsites']}), 12)
        self.assertIn('mutating func', source)
        self.assertIn('public final class', source)
        self.assertIn('borrowing BroadReference', source)
        self.assertIn('consuming BroadSmall', source)
        self.assertIn('inout Int', source)
        self.assertIn('-> any BroadValue', source)
        self.assertEqual(manifest['generator_version'], 'owned-swift-broad-v2-fixed')
        for category, minimum in matrix.MINIMUMS.items():
            self.assertEqual(sum(c['category'] == category for c in cases), minimum)

    def test_v2_optional_try_respects_optional_flattening(self):
        source, manifest = matrix.generate_v2()
        for case in manifest['cases']:
            if case['return_family'] == 'Int?':
                for site in case['source_callsites']:
                    if site['geometry'] == 'optional_try':
                        function = source.split('func ' + site['caller'] + '(', 1)[1].split('\n}', 1)[0]
                        self.assertNotIn('result ??', function)

    def test_v2_geometry_labels_follow_attributes_and_cleanup_escapes(self):
        source, manifest = matrix.generate_v2()
        self.assertTrue('@inline(never) public func broad_cleanup' in source)
        for case in manifest['cases']:
            for site in case['source_callsites']:
                if site['geometry'] == 'inline_absence_challenge':
                    self.assertTrue(case['inline_absence_challenge'])
                function = source.split('func ' + site['caller'] + '(', 1)[1].split('\n}', 1)[0]
                if site['geometry'] == 'defer_cleanup':
                    self.assertIn('broad_cleanup(&cleanup)', function)
                    self.assertIn('_ cleanup: inout Int', function)
                    self.assertTrue(site['cleanup_observable_caller_inout'])

    def test_v2_shared_consuming_calls_use_distinct_owned_values(self):
        source, manifest = matrix.generate_v2()
        checked = 0
        for case in manifest['cases']:
            if case['parameter_form'] == 'consuming_aggregate':
                for site in case['source_callsites']:
                    if site['geometry'] == 'shared_handler_multiple_calls':
                        function = source.split('func ' + site['caller'] + '(', 1)[1].split('\n}', 1)[0]
                        self.assertIn('let firstOwned = BroadSmall(owned.value, owned.other)', function)
                        self.assertIn('firstOwned)', function)
                        self.assertEqual(function.count('(owned)'), 1)
                        self.assertEqual(site['multiple_call_copy'], 'explicit_field_copy_before_consumption')
                        checked += 1
        self.assertEqual(checked, 4)

    def test_first_library_digest_binds_single_read_to_file_custody(self):
        from unittest.mock import patch
        import hashlib
        with tempfile.TemporaryDirectory() as directory:
            library = Path(directory).resolve() / 'new-owned.dylib'
            library.write_bytes(b'new owned bytes')
            real_sha = hashlib.sha256
            with patch.object(matrix.hashlib, 'sha256', wraps=real_sha) as digest:
                record = matrix.capture_library_identity(library)
            self.assertEqual(digest.call_count, 1)
            self.assertEqual(record['custody_before'], record['custody_after'])
            self.assertEqual(record['library_path'], str(library.resolve()))
            self.assertEqual(record['bytes'], 15)
            self.assertEqual(set(record['custody_before']), {'dev', 'ino', 'size', 'mtime_ns', 'ctime_ns'})
