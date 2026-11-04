"""First-run distinct owned images qualify producer-to-candidate flow."""
from pathlib import Path
import struct
import unittest
from airs.diff import compare_reports
from airs.engine import audit_path
from airs.report import dumps
from test_udiv_w_emission import owned_macho

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'local-evidence/exact-body-candidates'


def new_image(tag):
    data=bytearray(owned_macho(0x04000001))
    if struct.unpack_from('<III',data,0x1010)!=(0x92800000,0xd2800041,0x1ac10813):
        raise ValueError('Review changed builder before adapting')
    # New body bytes, distinct from previously accepted images; both builds keep them.
    struct.pack_into('<III',data,0x1010,0xd2800520,0xd2800061,0x1ac10813)
    offset=32
    for _ in range(struct.unpack_from('<I',data,16)[0]):
        command,size=struct.unpack_from('<II',data,offset)
        if command==0x1b:
            data[offset+8:offset+24]=bytes([tag])*16
            return bytes(data)
        offset+=size
    raise ValueError('Owned builder requires an explicit UUID command')


class ExactBodyCandidateEmissionTests(unittest.TestCase):
    def test_two_fresh_images_produce_one_unique_body_candidate_without_claiming_sink(self):
        OUTPUT.mkdir(parents=True,exist_ok=True)
        reports=[]
        for label,tag in (('baseline-41',0x91),('current-41',0x92)):
            source,target=OUTPUT/(label+'.macho'),OUTPUT/(label+'.json')
            self.assertFalse(source.exists() or target.exists(),'Reuse accepted evidence; refuse replay before audit')
            with source.open('xb') as stream:stream.write(new_image(tag))
            report=audit_path(source,include_function_fingerprints=True)
            self.assertEqual(report['summary']['agreement_count'],2)
            self.assertEqual(report['findings'][0]['checked_pcs'],['0x10000101c'])
            with target.open('x',encoding='utf-8') as stream:stream.write(dumps(report))
            reports.append(report)
        self.assertNotEqual(reports[0]['image']['slice_sha256'],reports[1]['image']['slice_sha256'])
        comparison=compare_reports(*reports,match_exact_bodies=True)
        self.assertFalse(comparison['comparison']['same_image'])
        self.assertEqual(comparison['summary'],dict(matched_count=1,changed_count=0,unchanged_count=1,
                                                   added_count=1,removed_count=1,ambiguous_count=0))
        row=next(row for row in comparison['changes'] if row['match_basis']=='exact_body_candidate')
        self.assertEqual(row['baseline_id'],reports[0]['findings'][0]['id'])
        self.assertEqual(row['current_id'],reports[1]['findings'][0]['id'])
        self.assertTrue(any('does not prove' in note for note in row['notes']))
        with (OUTPUT/'comparison.json').open('x',encoding='utf-8') as stream:stream.write(dumps(comparison))
