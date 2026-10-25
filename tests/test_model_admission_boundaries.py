"""Historical and unknown-label decoder boundaries using synthetic reports only."""
import unittest

from airs.report import validate_report
from airs.types import InputError
from test_report_v32_admission_candidate import synthetic_report, replace_mode


class ModelAdmissionBoundaryTests(unittest.TestCase):
    def test_historical_compact_policy_keeps_masked_subtype_admission(self):
        for model in ('arm64-linear-v1', 'arm64-linear-dwarf-v2'):
            for subtype in (0x80000000, 0x80000001):
                with self.subTest(model=model, subtype=subtype):
                    report = synthetic_report(model)
                    report['image']['cpu_subtype'] = subtype
                    self.assertIs(validate_report(report), report)
                    report['image']['cpu_subtype'] = 0x80000002
                    with self.assertRaises(InputError):
                        validate_report(report)

    def test_v1_refuses_evaluated_cfi_while_v2_requires_exact_subtype(self):
        for model in ('arm64-linear-v1', 'arm64-linear-dwarf-v2'):
            report = synthetic_report(model)
            replace_mode(report, mode='dwarf', scope='synchronous_call_sites', encoding='0x3000004', coverage='dwarf_evaluated')
            with self.subTest(model=model):
                if model == 'arm64-linear-v1':
                    with self.assertRaises(InputError):
                        validate_report(report)
                else:
                    self.assertIs(validate_report(report), report)
                    report['image']['cpu_subtype'] = 0x80000000
                    with self.assertRaises(InputError):
                        validate_report(report)

    def test_unknown_labels_keep_generic_import_without_bypassing_structure(self):
        for model in ('arm64-bounded-cls-v48', 'arm64-bounded-cls-v47-future', 'ARM64-bounded-cls-v47'):
            with self.subTest(model=model):
                report = synthetic_report(model)
                report['image']['cpu_subtype'] = 0x80000000
                self.assertIs(validate_report(report), report)
                report['findings'][0]['checked_pcs'] = ['0x2000']
                with self.assertRaises(InputError):
                    validate_report(report)
