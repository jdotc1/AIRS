"""First-run complete owned TBZ/TBNZ images; never replay sealed inputs."""
from pathlib import Path
import struct
import unittest
from airs import ANALYSIS_MODEL_VERSION
from airs.engine import audit_path
from airs.report import dumps,load_report
from test_udiv_w_emission import owned_macho
from test_test_bit_branch import branch

OUTPUT=Path(__file__).resolve().parents[1]/'local-evidence/test-bit-branch-v50'


def test_bit_macho(bit,nonzero,encoding,unknown=False):
    data=bytearray(owned_macho(encoding))
    if struct.unpack_from('<III',data,0x1010)!=(0x92800000,0xd2800041,0x1ac10813):
        raise ValueError('Review changed owned layout before adaptation')
    # Force a false predicate so the X19 write reaches the original BL.
    initial=0xd2800000 if nonzero else (0xd2800020 if bit==0 else 0xd2f00000)
    struct.pack_into('<III',data,0x1010,0xd503201f if unknown else initial,
                     branch(bit,offset=8,nonzero=nonzero),0xd2800033)
    return bytes(data)


class TestBitBranchEmissionTests(unittest.TestCase):
    def emitted(self,bit,nz,case,encoding):
        OUTPUT.mkdir(parents=True,exist_ok=True)
        op='tbnz' if nz else 'tbz'
        stem=f'{ANALYSIS_MODEL_VERSION}-{op}-{bit}-{case}'
        source,target=OUTPUT/(stem+'.macho'),OUTPUT/(stem+'.json')
        self.assertFalse(source.exists() or target.exists(),'Reuse prior result; refuse replay before audit')
        with source.open('xb') as stream:stream.write(test_bit_macho(bit,nz,encoding,case=='unknown'))
        report=audit_path(source)
        with target.open('x',encoding='utf-8') as stream:stream.write(dumps(report))
        self.assertEqual(load_report(target),report)
        self.assertEqual(report['generator']['analysis_model_version'],'arm64-bounded-test-bit-branch-v50')
        self.assertEqual(report['summary']['function_count'],2)
        self.assertEqual(report['findings'][0]['function']['boundary_source'],'lc_function_starts')
        self.assertEqual(report['findings'][1]['verdict'],'agreement')
        return report['findings'][0]

    def test_correct_recovery_for_both_operations_and_widths(self):
        for bit in (0,63):
            for nz in (False,True):
                first=self.emitted(bit,nz,'correct',0x04000001)
                self.assertEqual((first['verdict'],first['scope'],first['checked_pcs']),
                                 ('agreement','synchronous_call_sites',['0x10000101c']))

    def test_missing_recovery_for_both_operations_and_widths(self):
        for bit in (0,63):
            for nz in (False,True):
                first=self.emitted(bit,nz,'mismatch',0x04000000)
                self.assertEqual((first['verdict'],first['checked_pcs']),('inconsistency',['0x10000101c']))
                self.assertTrue(any(e.get('expected')=='original x19' and e.get('observed')=='constant 0x1' for e in first['evidence']))

    def test_unknown_predicate_does_not_support_possible_discrepancy(self):
        for bit in (0,63):
            for nz in (False,True):
                first=self.emitted(bit,nz,'unknown',0x04000000)
                self.assertEqual((first['verdict'],first['checked_pcs']),('unresolved',[]))
                self.assertIn('cfg_path_feasibility_unknown',first['reason_codes'])
