"""Three new complete owned REV32 images; no accepted image is replayed."""
from pathlib import Path
import struct
import unittest

from airs import ANALYSIS_MODEL_VERSION
from airs.engine import audit_path
from airs.report import dumps, load_report
from test_rbit_x_candidate import NOP
from test_udiv_w_emission import owned_macho
from test_rev32 import word

OUTPUT = Path(__file__).resolve().parents[1] / 'local-evidence/rev32-v46'


def rev32_macho(encoding, *, unknown=False):
    data = bytearray(owned_macho(encoding))
    if struct.unpack_from('<III', data, 0x1010) != (0x92800000, 0xd2800041, 0x1ac10813):
        raise ValueError('Owned instruction layout changed; review before adapting')
    struct.pack_into('<III', data, 0x1010, NOP if unknown else 0x92824680, NOP, word(19, 0))
    return bytes(data)


class REV32EmissionTests(unittest.TestCase):
    def emitted(self, case, encoding, *, unknown=False):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stem = f'{ANALYSIS_MODEL_VERSION}-{case}'
        source, target = OUTPUT / (stem+'.macho'), OUTPUT / (stem+'.json')
        self.assertFalse(source.exists() or target.exists(), 'Reuse accepted evidence; refuse replay before audit')
        with source.open('xb') as stream:
            stream.write(rev32_macho(encoding, unknown=unknown))
        report = audit_path(source)
        self.assertEqual(report['generator']['analysis_model_version'], ANALYSIS_MODEL_VERSION)
        self.assertEqual(report['summary']['function_count'], 2)
        self.assertEqual(report['findings'][0]['function']['boundary_source'], 'lc_function_starts')
        self.assertEqual(report['findings'][1]['verdict'], 'agreement')
        with target.open('x', encoding='utf-8') as stream:
            stream.write(dumps(report))
        self.assertEqual(load_report(target), report)
        return report

    def test_correct_recovery_preserves_original_call_pc(self):
        report = self.emitted('correct', 0x04000001)
        self.assertEqual(report['summary']['agreement_count'], 2)
        first = report['findings'][0]
        self.assertEqual((first['verdict'], first['scope'], first['checked_pcs']),
                         ('agreement', 'synchronous_call_sites', ['0x10000101c']))

    def test_missing_recovery_keeps_lane_local_concrete_discrepancy(self):
        report = self.emitted('mismatch', 0x04000000)
        self.assertEqual(report['summary']['inconsistency_count'], 1)
        first = report['findings'][0]
        self.assertEqual((first['verdict'], first['scope'], first['checked_pcs']),
                         ('inconsistency', 'synchronous_call_sites', ['0x10000101c']))
        self.assertTrue(any(e.get('expected') == 'original x19' and
                            e.get('observed') == 'constant 0xffffffffcbedffff' for e in first['evidence']))

    def test_unknown_source_does_not_produce_supported_checked_pcs(self):
        report = self.emitted('unknown', 0x04000000, unknown=True)
        self.assertEqual((report['summary']['unresolved_count'], report['summary']['inconsistency_count']), (1, 0))
        first = report['findings'][0]
        self.assertEqual(first['verdict'], 'unresolved')
        self.assertIn('unknown_recovery_value', first['reason_codes'])
        self.assertEqual(first['checked_pcs'], [])
