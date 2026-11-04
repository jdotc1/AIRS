"""Fresh-clone fixture storage does not depend on private execution directories."""
from pathlib import Path
import tempfile
import unittest
from fixture_storage import temporary_directory


class FixtureStorageTests(unittest.TestCase):
    def test_missing_parents_are_created_and_fixture_is_cleaned(self):
        with tempfile.TemporaryDirectory() as root:
            missing = Path(root) / 'fresh-checkout'
            with temporary_directory(missing) as folder:
                fixture = Path(folder)
                self.assertEqual(fixture.parent, missing / 'build/test-fixtures')
                self.assertTrue(fixture.is_dir())
            self.assertFalse(fixture.exists())

    def test_existing_parent_keeps_unrelated_files_and_unique_fixtures(self):
        with tempfile.TemporaryDirectory() as root:
            parent = Path(root) / 'build/test-fixtures'
            parent.mkdir(parents=True)
            retained = parent / 'retained'; retained.write_text('owned')
            with temporary_directory(root) as first, temporary_directory(root) as second:
                self.assertNotEqual(first, second)
                self.assertTrue(Path(first).is_dir() and Path(second).is_dir())
            self.assertEqual(retained.read_text(), 'owned')

if __name__ == '__main__':
    unittest.main()
