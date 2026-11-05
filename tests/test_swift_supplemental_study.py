import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location('supplemental_study', Path(__file__).resolve().parents[1] / 'scripts/swift_supplemental_study.py')


class SupplementalStudyPlanTests(unittest.TestCase):
    def load(self):
        module = importlib.util.module_from_spec(SPEC)
        SPEC.loader.exec_module(module)
        return module

    def test_first_study_refuses_over_eighteen_physical_units_before_analysis(self):
        module = self.load()
        index = {'role': 'supplemental_challenge_only', 'modes': {'O': {'calls': [
            {'pc': hex(4096 + 4*i), 'owned_target_confirmed': True,
             'caller_function_names': ['supplementNested']} for i in range(19)]}}}
        with self.assertRaises(ValueError):
            module.select_plan(index)

    def test_first_study_selects_only_confirmed_owned_calls_in_declared_callers(self):
        module = self.load()
        base = {'pc': '0x1000', 'owned_target_confirmed': True, 'caller_function_names': ['supplementNested']}
        index = {'role': 'supplemental_challenge_only', 'modes': {'O': {'calls': [
            base, dict(base, pc='0x1004', owned_target_confirmed=False),
            dict(base, pc='0x1008', caller_function_names=['supplementPrimary'])]}}}
        self.assertEqual([(mode, row['pc']) for mode, row in module.select_plan(index)], [('O', '0x1000')])


if __name__ == '__main__':
    unittest.main()
