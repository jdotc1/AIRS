"""New representative-source selection checks; never revisit sealed images."""
import importlib.util
from pathlib import Path
import unittest
import re

SPEC = importlib.util.spec_from_file_location('matrix_representative', Path(__file__).parents[1] / 'scripts/swift_fixture_matrix.py')
matrix = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(matrix)

class RepresentativeMatrixTests(unittest.TestCase):
    def test_representative_is_deterministic_bounded_and_stratified(self):
        source, manifest = matrix.generate_representative()
        self.assertEqual((source, manifest), matrix.generate_representative())
        cases = manifest['cases']
        self.assertGreaterEqual(len(cases), 40)
        self.assertLessEqual(len(cases), 80)
        self.assertEqual(len({c['category'] for c in cases}), 8)
        self.assertEqual(len({c['return_family'] for c in cases}), 23)
        self.assertEqual(len({c['parameter_form'] for c in cases}), 12)
        self.assertEqual(len({s['geometry'] for c in cases for s in c['source_callsites']}), 12)
        self.assertEqual(manifest['qualification_role'], 'representative_second_toolchain')
        for case in cases:
            self.assertIn(case['declaration'], source)
        for helper in ('public struct BroadSmall', 'public struct BroadLarge', 'public func broad_cleanup'):
            self.assertTrue(helper in source)
        self.assertEqual(len(re.findall(r'func broad_case_[^\n{]+\{', source)), len(cases))
