"""New complete signed-division images; accepted source images are not replayed."""
from pathlib import Path
import struct
import unittest

from airs import ANALYSIS_MODEL_VERSION
from airs.engine import audit_path
from airs.report import dumps, load_report
from test_rbit_x_candidate import NOP
from test_udiv_w_emission import owned_macho

OUTPUT = Path(__file__).resolve().parents[1] / 'local-evidence/w-sdiv-owned-images'


def signed_macho(encoding, *, unknown_numerator=False):
    """Reuse the owned layout, changing only declared arithmetic instructions.

    The unsigned intermediate is assembled in memory, never parsed/audited or
    hashed. Both compact entries, function starts and call target are unchanged.
    """
    data = bytearray(owned_macho(encoding))
    expected = (0x92800000, 0xd2800041, 0x1ac10813)
    if struct.unpack_from('<III', data, 0x1010) != expected:
        raise ValueError('Owned layout changed; review instruction offsets before adapting it')
    struct.pack_into('<III', data, 0x1010,
                     NOP if unknown_numerator else 0x928000c0, 0xd2800061, 0x1ac10c13)
    return bytes(data)


class WSDIVOwnedImageTests(unittest.TestCase):
    def emitted(self, case, encoding, *, unknown_numerator=False):
        OUTPUT.mkdir(parents=True, exist_ok=True)
        stem = f'{ANALYSIS_MODEL_VERSION}-{case}'
        source, target = OUTPUT / (stem + '.macho'), OUTPUT / (stem + '.json')
        self.assertFalse(source.exists() or target.exists(), 'Reuse the first receipt; do not replay an accepted image')
        with source.open('xb') as stream:
            stream.write(signed_macho(encoding, unknown_numerator=unknown_numerator))
        report = audit_path(source)
        self.assertEqual(report['generator']['analysis_model_version'], ANALYSIS_MODEL_VERSION)
        self.assertEqual(report['summary']['function_count'], 2)
        self.assertEqual(report['findings'][0]['function']['boundary_source'], 'lc_function_starts')
        self.assertEqual(report['findings'][1]['verdict'], 'agreement')
        with target.open('x', encoding='utf-8') as stream:
            stream.write(dumps(report))
        self.assertEqual(load_report(target), report)
        return report

    def test_correct_saved_x19_rule_recovers_original_state(self):
        report = self.emitted('correct', 0x04000001)
        self.assertEqual(report['summary']['agreement_count'], 2)
        first = report['findings'][0]
        self.assertEqual((first['verdict'], first['scope'], first['checked_pcs']),
                         ('agreement', 'synchronous_call_sites', ['0x10000101c']))

    def test_missing_x19_rule_has_zero_extended_signed_discrepancy(self):
        report = self.emitted('mismatch', 0x04000000)
        self.assertEqual(report['summary']['inconsistency_count'], 1)
        first = report['findings'][0]
        self.assertEqual((first['verdict'], first['scope'], first['checked_pcs']),
                         ('inconsistency', 'synchronous_call_sites', ['0x10000101c']))
        self.assertTrue(any(e.get('expected') == 'original x19' and
                            e.get('observed') == 'constant 0xfffffffe' for e in first['evidence']))

    def test_unknown_numerator_never_becomes_a_supported_discrepancy(self):
        report = self.emitted('unknown', 0x04000000, unknown_numerator=True)
        self.assertEqual((report['summary']['unresolved_count'], report['summary']['inconsistency_count']), (1, 0))
        first = report['findings'][0]
        self.assertEqual(first['verdict'], 'unresolved')
        self.assertIn('unknown_recovery_value', first['reason_codes'])
        self.assertEqual(first['checked_pcs'], [])
