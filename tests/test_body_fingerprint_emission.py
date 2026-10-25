"""Fresh complete images for opt-in annotation; accepted images are not replayed."""
import json
from pathlib import Path
import struct
import subprocess
import sys
import unittest
from airs.engine import audit_path
from airs.report import dumps,load_report
from test_udiv_w_emission import owned_macho

ROOT=Path(__file__).resolve().parents[1]
OUTPUT=ROOT/'local-evidence/body-fingerprint-v1'


def new_image(value,unknown=False):
    data=bytearray(owned_macho(0x04000000 if unknown else 0x04000001))
    if struct.unpack_from('<III',data,0x1010)!=(0x92800000,0xd2800041,0x1ac10813):
        raise ValueError('Review changed builder before adapting')
    struct.pack_into('<III',data,0x1010,0xd503201f if unknown else 0xd2800000|(value<<5),
                     0xd503201f if unknown else 0xd2800041,0x1ac00813 if unknown else 0x1ac10813)
    return bytes(data)


class BodyFingerprintEmissionTests(unittest.TestCase):
    def source(self,label,value,unknown=False):
        OUTPUT.mkdir(parents=True,exist_ok=True)
        path=OUTPUT/(label+'.macho')
        self.assertFalse(path.exists(),'Reuse accepted source; refuse audit replay before writing')
        with path.open('xb') as stream:stream.write(new_image(value,unknown))
        return path

    def record(self,label,report):
        target=OUTPUT/(label+'.json')
        with target.open('x',encoding='utf-8') as stream:stream.write(dumps(report))
        self.assertEqual(load_report(target),report)
        return report

    def test_default_output_omits_body_annotations(self):
        report=self.record('default-23',audit_path(self.source('default-23',23)))
        self.assertEqual(report['summary']['agreement_count'],2)
        self.assertTrue(all('body_fingerprint' not in f['function'] for f in report['findings']))
        self.assertEqual(report['findings'][0]['checked_pcs'],['0x10000101c'])

    def test_opt_in_isolated_cli_emits_only_substantial_supported_body(self):
        source=self.source('opt-in-29',29);target=OUTPUT/'opt-in-29.json'
        self.assertFalse(target.exists(),'Reuse accepted output; refuse replay before CLI audit')
        result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'airs_cli.py'),'audit',str(source),
                               '--include-function-fingerprints','--output',str(target)],
                              cwd=OUTPUT,capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        report=load_report(target);first=report['findings'][0]
        self.assertEqual(report['summary']['agreement_count'],2)
        self.assertEqual(first['checked_pcs'],['0x10000101c'])
        self.assertEqual(first['function']['body_fingerprint']['instruction_count'],first['instruction_count'])
        self.assertEqual(first['function']['body_fingerprint']['instruction_count']*4,first['function']['size'])
        self.assertEqual(first['function']['body_fingerprint']['kind'],'arm64-exact-bytes-v1')
        self.assertNotIn('body_fingerprint',report['findings'][1]['function']) # Two-word sink is insufficient.
        self.assertTrue(any('not source-function identity' in note for note in report['limitations']))

    def test_unresolved_recovery_does_not_receive_body_evidence(self):
        report=self.record('unknown-new',audit_path(self.source('unknown-new',31,True),include_function_fingerprints=True))
        self.assertEqual(report['findings'][0]['verdict'],'unresolved')
        self.assertNotIn('body_fingerprint',report['findings'][0]['function'])
        self.assertEqual(report['findings'][0]['checked_pcs'],[])
