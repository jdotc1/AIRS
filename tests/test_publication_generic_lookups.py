"""Generic upstream lookup literals do not identify a development account."""
import importlib.util
from pathlib import Path
import unittest
spec = importlib.util.spec_from_file_location('lookup_policy', Path(__file__).resolve().parents[1] / 'scripts/publication_gate.py')
policy = importlib.util.module_from_spec(spec)
spec.loader.exec_module(policy)

class GenericLookupTests(unittest.TestCase):
    def test_escaped_quotes_and_case_variants_refuse(self):
        for value in (b'\\"~' + b'/Library/Frameworks\\"', b'\\"~' + b'/Library/Frameworks"',
                      b'"~' + b'/library/Frameworks"', b'"~' + b'/Library/Frameworks\''):
            with self.assertRaises(policy.GateError): policy.inspect_bytes(value, 'owned')

    def test_exact_quoted_defaults(self):
        for literal in (b'~' + b'/Library/Frameworks', b'~' + b'/Library/Preferences/com.apple.LaunchServices/'):
            for quote in (b"'", b'"'):
                policy.inspect_bytes(b'expanduser(' + quote + literal + quote + b')', 'owned')

    def test_other_paths_and_extensions_refuse(self):
        for value in (b'~' + b'/Library/Frameworks/private', b'~' + b'/Library/Preferences/private',
                      b'~' + b'/Developer/project', b'~' + b'/Library/Frameworks',
                      b'"~' + b'/Library/FrameworksExtra"', b'"~' + b'/Library/Frameworks/private"'):
            with self.assertRaises(policy.GateError): policy.inspect_bytes(value, 'owned')

    def test_allowed_literal_cannot_hide_other_markers(self):
        for suffix in (b' /' + b'Users/person/private', b' ~' + b'/Desktop/private',
                       b' ghp_' + b'x' * 31):
            with self.assertRaises(policy.GateError):
                policy.inspect_bytes(b'"~' + b'/Library/Frameworks"' + suffix, 'owned')

if __name__ == '__main__':
    unittest.main()
