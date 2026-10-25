"""Synthetic optional body evidence admission; no bytes or receipts are hashed."""
from copy import deepcopy
import unittest
from airs.diff import compare_reports
from airs.report import validate_report,dumps
from airs.types import InputError
from test_report_v32_admission_candidate import synthetic_report


def report():
    value=synthetic_report()
    value['findings'][0]['function']['body_fingerprint']={
        'kind':'arm64-exact-bytes-v1','sha256':'e'*64,'instruction_count':4}
    return value


class BodyFingerprintAdmissionTests(unittest.TestCase):
    def test_exact_shape_accepts_and_roundtrips(self):
        import json
        value=report();validate_report(value)
        self.assertEqual(json.loads(dumps(value)),value)

    def test_malformed_digest_kind_count_and_extra_fields_reject(self):
        for key,raw in (('sha256','E'*64),('sha256','e'*63),('kind','future-v2'),
                        ('instruction_count',True),('instruction_count',2),
                        ('instruction_count',5),('instruction_count',16385),('extra','unbound')):
            value=report();value['findings'][0]['function']['body_fingerprint'][key]=raw
            with self.assertRaises(InputError):validate_report(value)
        for raw in (None,[],{},'body'):
            value=report();value['findings'][0]['function']['body_fingerprint']=raw
            with self.assertRaises(InputError):validate_report(value)

    def test_provenance_architecture_and_unresolved_contexts_cannot_claim_body_evidence(self):
        for fault in ('architecture','subtype','boundary','unresolved','count'):
            value=report();first=value['findings'][0]
            if fault=='architecture':value['image']['architecture']='arm64e'
            elif fault=='subtype':value['image']['cpu_subtype']=2
            elif fault=='boundary':first['function']['boundary_source']='compact_unwind'
            elif fault=='count':first['instruction_count']=3
            else:
                first.update(verdict='unresolved',scope='metadata_only',checked_pcs=[])
                value['summary'].update(agreement_count=0,unresolved_count=1,checked_pc_count=0)
            with self.assertRaises(InputError):validate_report(value)

    def test_optional_annotation_changes_neither_comparison_nor_inputs(self):
        annotated=report();plain=deepcopy(annotated)
        del plain['findings'][0]['function']['body_fingerprint']
        originals=deepcopy((plain,annotated))
        result=compare_reports(plain,annotated)
        self.assertEqual(result['summary']['unchanged_count'],1)
        self.assertEqual(result['changes'][0]['match_basis'],'exact_image_offset')
        self.assertEqual((plain,annotated),originals)
