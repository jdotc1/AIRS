import unittest
from pathlib import Path
from security_delta_fixture_support import owned_temporary_directory
class SecurityDeltaFixtureSupportTests(unittest.TestCase):
    def test_missing_fixture_root_is_created_and_owned_temporary_data_is_removed(self):
        with owned_temporary_directory() as outer:
            root=Path(outer)/'previously-absent'/'fixtures'
            with owned_temporary_directory(root) as inner:
                self.assertTrue(Path(inner).is_dir())
                temporary=Path(inner)
            self.assertFalse(temporary.exists())
            self.assertTrue(root.is_dir())
