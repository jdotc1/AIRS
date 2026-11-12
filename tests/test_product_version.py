"""Guard static product-version copies without importing the engine."""
import ast
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ProductVersionTests(unittest.TestCase):
    def test_authority_and_static_copies_agree(self):
        source = (ROOT / 'src/airs/__init__.py').read_text()
        versions = re.findall(r'^__version__ = "([^"]+)"$', source, re.MULTILINE)
        self.assertEqual(len(versions), 1)
        version = versions[0]
        self.assertRegex(version, r'^[0-9]+\.[0-9]+\.[0-9]+$')
        metadata = (ROOT / 'pyproject.toml').read_text()
        self.assertEqual(re.findall(r'^version = "([^"]+)"$', metadata, re.MULTILINE), [version])
        swift = (ROOT / 'native/Sources/AIRSEntitlements/AIRSProductVersion.swift').read_text()
        self.assertEqual(re.findall(r'public static let current = "([^"]+)"', swift), [version])

    def test_generators_read_the_authority_as_text(self):
        version = re.search(r'^__version__ = "([^"]+)"$',
                            (ROOT / 'src/airs/__init__.py').read_text(), re.MULTILINE)[1]
        for kind in ('coverage', 'observation'):
            with self.subTest(kind=kind):
                path = ROOT / f'scripts/generate-producer-{kind}-controls.py'
                source = path.read_text()
                tree = ast.parse(source)
                function = next(node for node in tree.body if isinstance(node, ast.FunctionDef)
                                and node.name == 'product_version')
                namespace = {'ROOT': ROOT, 're': re}
                exec(compile(ast.Module(body=[function], type_ignores=[]), path.name, 'exec'), namespace)
                self.assertEqual(namespace['product_version'](), version)
                self.assertIn('version=product_version()', source)
                self.assertNotRegex(source, r'version\s*=\s*[\'\"][0-9]+\.[0-9]+\.[0-9]+')

    def test_packaging_has_no_hardcoded_product_default(self):
        source = (ROOT / 'scripts/package-app.sh').read_text()
        self.assertNotRegex(source, r'BUNDLE_VERSION=[\'\"][0-9]+\.[0-9]+\.[0-9]+')
        self.assertNotRegex(source, r'CFBundleShortVersionString</key><string>[0-9]+\.[0-9]+\.[0-9]+')
        self.assertIn('src/airs/__init__.py', source)
        self.assertIn('sed -nE', source)
