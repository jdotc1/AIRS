"""Synthetic v50 admission preserves exact known-model boundaries."""
import unittest
from airs.report import validate_report
from airs.types import InputError
from test_report_v32_admission_candidate import synthetic_report
MODEL='arm64-bounded-test-bit-branch-v50'

class TestBitBranchAdmissionTests(unittest.TestCase):
    def test_exact_model_enforces_subtype_boundary_and_scope(self):
        validate_report(synthetic_report(MODEL))
        for fault in ('subtype','boundary','scope'):
            report=synthetic_report(MODEL)
            if fault=='subtype':report['image']['cpu_subtype']=0x80000000
            elif fault=='boundary':report['findings'][0]['function']['boundary_source']='compact_unwind'
            else:report['findings'][0]['scope']='modeled_leaf_body'
            with self.assertRaises(InputError):validate_report(report)

    def test_future_model_is_generic_import_only(self):
        report=synthetic_report(MODEL+'-future')
        report['image']['cpu_subtype']=0x80000000
        validate_report(report)
