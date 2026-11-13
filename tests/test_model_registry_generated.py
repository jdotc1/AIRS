"""Generated registry freshness, strict source validation, and engine bindings."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from airs import ANALYSIS_MODEL_VERSION
from airs.analysis_models import CURRENT_MODEL, SWIFT_BROAD_PAIRS
from airs.swift_broad_flow import PROFILE_LIMITS, PROFILE_MODELS


ROOT = Path(__file__).resolve().parents[1]
GENERATOR = ROOT / 'scripts/generate-model-registries.py'
OUTPUTS = ('src/airs/analysis_models.py', 'native/Sources/AIRSCore/AnalysisModels.swift')


class ModelRegistryGeneratedTests(unittest.TestCase):
    def check(self, root):
        return subprocess.run([sys.executable, '-I', '-B', str(GENERATOR), '--check',
                               '--root', str(root)], capture_output=True, text=True)

    def copy_tree(self, root):
        for name in ('registry/models.json', *OUTPUTS):
            target = root / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT / name, target)

    def test_generated_files_are_current(self):
        result = self.check(ROOT)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_changed_label_is_stale_without_writes(self):
        for name in OUTPUTS:
            with self.subTest(file=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                self.copy_tree(root)
                target = root / name
                target.write_bytes(target.read_bytes().replace(b'arm64-bounded-cfg-v3',
                                                              b'arm64-bounded-cfg-v3-changed', 1))
                before = {item: (root / item).read_bytes() for item in ('registry/models.json', *OUTPUTS)}
                result = self.check(root)
                self.assertEqual(result.returncode, 1)
                self.assertIn(name, result.stderr)
                self.assertEqual(before, {item: (root / item).read_bytes() for item in before})

    def test_strict_validation_refuses_bad_sources(self):
        source = json.loads((ROOT / 'registry/models.json').read_text())
        cases = []

        def change(name, path, value):
            bad = copy.deepcopy(source)
            target = bad
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            cases.append((name, json.dumps(bad)))

        cases.extend((('root-array', '[]'), ('malformed-json', '{'),
                      ('duplicate-json-key', json.dumps(source).replace(
                          '"cfg_models":', '"cfg_models": [], "cfg_models":', 1))))
        for path in ((), ('linear_models', 0), ('swift_broad_pairs', 0)):
            original = source
            for key in path:
                original = original[key]
            for key in original:
                bad = copy.deepcopy(source)
                target = bad
                for part in path:
                    target = target[part]
                del target[key]
                cases.append((f'missing-{path}-{key}', json.dumps(bad)))
            bad = copy.deepcopy(source)
            target = bad
            for part in path:
                target = target[part]
            target['unexpected'] = True
            cases.append((f'extra-{path}', json.dumps(bad)))
        for key in ('cfg_models', 'linear_models', 'swift_broad_pairs'):
            for wrong in (None, {}, 'label', 1, True):
                change(f'array-type-{key}-{wrong}', (key,), wrong)
        for key in ('linear_models', 'swift_broad_pairs'):
            for wrong in (None, [], 'label', 1, True):
                change(f'object-type-{key}-{wrong}', (key, 0), wrong)
        for path in (('cfg_models', 0), ('linear_models', 0, 'label'), ('current_model',),
                     ('swift_broad_pairs', 0, 'model'), ('swift_broad_pairs', 0, 'profile')):
            for wrong in ('', 'Upper', 'white space', 'under_score', 'trailing\n', 'é',
                          1, True, None, [], {}):
                change(f'string-{path}-{wrong}', path, wrong)
        for path in (('linear_models', 0, 'evaluated_cfi'), ('swift_broad_pairs', 0, 'native_admitted')):
            for wrong in (0, 1, 'true', None, [], {}):
                change(f'boolean-{path}-{wrong}', path, wrong)
        change('duplicate-cfg', ('cfg_models', 1), source['cfg_models'][0])
        change('duplicate-linear', ('linear_models', 1, 'label'), source['linear_models'][0]['label'])
        change('duplicate-cross-label', ('linear_models', 0, 'label'), source['cfg_models'][0])
        change('duplicate-model', ('swift_broad_pairs', 1, 'model'), source['swift_broad_pairs'][0]['model'])
        change('duplicate-cross-model', ('swift_broad_pairs', 0, 'model'), source['cfg_models'][0])
        change('duplicate-profile', ('swift_broad_pairs', 1, 'profile'), source['swift_broad_pairs'][0]['profile'])
        change('current-not-cfg', ('current_model',), source['linear_models'][0]['label'])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_tree(root)
            before = {name: (root / name).read_bytes() for name in OUTPUTS}
            for name, text in cases:
                with self.subTest(case=name):
                    (root / 'registry/models.json').write_text(text)
                    result = self.check(root)
                    self.assertEqual(result.returncode, 1, result.stderr)
                    self.assertIn('model registry:', result.stderr)
                    self.assertEqual(before, {item: (root / item).read_bytes() for item in OUTPUTS})

    def test_engine_tables_match_registry(self):
        self.assertEqual({(PROFILE_MODELS[p], p) for p in PROFILE_LIMITS}, set(SWIFT_BROAD_PAIRS))
        self.assertEqual(ANALYSIS_MODEL_VERSION, CURRENT_MODEL)


if __name__ == '__main__':
    unittest.main()
