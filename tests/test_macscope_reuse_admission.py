"""Fresh synthetic admission cases for exact MOVK and compare-branch models."""
import unittest
from airs.report import validate_report
from airs.types import InputError
from test_report_v32_admission_candidate import synthetic_report

MODELS=('arm64-bounded-movk-v48','arm64-bounded-compare-branch-v49')

class MacScopeReuseAdmissionTests(unittest.TestCase):
    def test_exact_models_enforce_architecture_and_boundary(self):
        for model in MODELS:
            validate_report(synthetic_report(model))
            for fault in ('subtype','boundary'):
                report=synthetic_report(model)
                if fault == 'subtype': report['image']['cpu_subtype']=0x80000000
                else: report['findings'][0]['function']['boundary_source']='compact_unwind'
                with self.assertRaises(InputError): validate_report(report)

    def test_future_labels_keep_generic_import_without_claiming_support(self):
        for model in MODELS:
            report=synthetic_report(model+'-future')
            report['image']['cpu_subtype']=0x80000000
            validate_report(report)
