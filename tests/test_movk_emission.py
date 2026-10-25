"""Complete owned-image MOVK evidence without replaying accepted images."""
from pathlib import Path
import struct
import unittest

from airs import ANALYSIS_MODEL_VERSION
from airs.engine import audit_path
from airs.report import dumps, load_report
from test_rbit_x_candidate import NOP
from test_udiv_w_emission import owned_macho
from test_movk import word

OUTPUT = Path(__file__).resolve().parents[1] / 'local-evidence/movk-v48'


def movk_macho(width, encoding, *, unknown=False):
    data = bytearray(owned_macho(encoding))
    if struct.unpack_from('<III', data, 0x1010) != (0x92800000, 0xd2800041, 0x1ac10813):
        raise ValueError('Owned instruction layout changed; review before adapting')
    # Only finalized new MOVK bytes are audited; the builder intermediate is not.
    struct.pack_into('<III', data, 0x1010, NOP if unknown else 0xd2800013, NOP, word(width, 19, 0x1234))
    return bytes(data)


class MOVKEmissionTests(unittest.TestCase):
    def emitted(self, width, case, encoding, *, unknown=False):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stem = f'{ANALYSIS_MODEL_VERSION}-{width}-{case}'
        source, target = OUTPUT / (stem+'.macho'), OUTPUT / (stem+'.json')
        self.assertFalse(source.exists() or target.exists(), 'Reuse accepted evidence; refuse replay before audit')
        with source.open('xb') as stream:
            stream.write(movk_macho(width, encoding, unknown=unknown))
        report = audit_path(source)
        self.assertEqual(report['generator']['analysis_model_version'], ANALYSIS_MODEL_VERSION)
        self.assertEqual(report['summary']['function_count'], 2)
        self.assertEqual(report['findings'][0]['function']['boundary_source'], 'lc_function_starts')
        self.assertEqual(report['findings'][1]['verdict'], 'agreement')
        with target.open('x', encoding='utf-8') as stream:
            stream.write(dumps(report))
        self.assertEqual(load_report(target), report)
        return report

    def test_correct_recovery_for_both_widths_preserves_original_call_pc(self):
        for width in (32, 64):
            report = self.emitted(width, 'correct', 0x04000001)
            self.assertEqual(report['summary']['agreement_count'], 2)
            first = report['findings'][0]
            self.assertEqual((first['verdict'], first['scope'], first['checked_pcs']),
                             ('agreement', 'synchronous_call_sites', ['0x10000101c']))

    def test_missing_recovery_preserves_w_and_x_results(self):
        for width, expected in ((32, 'constant 0x1234'), (64, 'constant 0x1234')):
            report = self.emitted(width, 'mismatch', 0x04000000)
            self.assertEqual(report['summary']['inconsistency_count'], 1)
            first = report['findings'][0]
            self.assertEqual((first['verdict'], first['scope'], first['checked_pcs']),
                             ('inconsistency', 'synchronous_call_sites', ['0x10000101c']))
            self.assertTrue(any(e.get('expected') == 'original x19' and e.get('observed') == expected
                                for e in first['evidence']))

    def test_unknown_for_either_width_does_not_create_supported_evidence(self):
        for width in (32, 64):
            report = self.emitted(width, 'unknown', 0x04000000, unknown=True)
            self.assertEqual((report['summary']['unresolved_count'], report['summary']['inconsistency_count']), (1, 0))
            first = report['findings'][0]
            self.assertEqual(first['verdict'], 'unresolved')
            self.assertIn('unknown_recovery_value', first['reason_codes'])
            self.assertEqual(first['checked_pcs'], [])
