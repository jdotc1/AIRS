"""Checks the broad-extended-v3 report on the owned fixture against an independently derived expectation.

The expectation (fixtures/swift-error-flow/broad-imports/expected-indirect-target.json) was derived by hand from the
disassembly and the design alone; its derivation field lists the two places it was corrected.
"""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from airs.macho import parse_macho  # noqa: E402
from airs.swift_broad_flow import PROFILE_LIMITS, recover_swift_broad_flow  # noqa: E402

DIR = Path(__file__).resolve().parents[1] / 'fixtures' / 'swift-error-flow' / 'broad-imports'
PROFILE = 'broad-extended-v3'


class V3FixtureAgainstExpectationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads((DIR / 'expected-indirect-target.json').read_text())
        data = (DIR / 'OwnedImports.macho').read_bytes()
        cls.report = recover_swift_broad_flow(parse_macho(data, limits=PROFILE_LIMITS[PROFILE]), profile=PROFILE)
        cls.rows = {c['call_pc']: c for c in cls.report['calls']}

    def in_report(self):
        return [s for s in self.expected['sites'] if s['in_report']]

    def test_every_expected_site_is_a_row_with_a_shape_and_no_extra_shapes(self):
        shaped = {pc for pc, c in self.rows.items() if c.get('indirect_target_shape')}
        self.assertEqual(shaped, {s['pc'] for s in self.in_report()})

    def test_tier1_class_slot_and_unknown_reason(self):
        for s in self.in_report():
            shape = self.rows[s['pc']]['indirect_target_shape']
            self.assertEqual(shape['class'], s['tier1_class'], s['pc'])
            self.assertEqual(shape['site_kind'], s['site_kind'], s['pc'])
            self.assertEqual(shape['slot_offset'], int(s['slot_offset'], 16), s['pc'])
            self.assertIsNone(shape['unknown_reason'], s['pc'])
            self.assertFalse(shape['claims_callee_behaviour'])

    def test_tier2_admission_and_first_failing_condition(self):
        for s in self.in_report():
            adm = self.rows[s['pc']]['value_witness_admission']
            self.assertEqual(adm['admitted'], s['tier2_admitted'], s['pc'])
            self.assertEqual(adm['first_failing_condition'], s['tier2_failed_condition'], s['pc'])
            self.assertEqual(adm['slot_offset'], int(s['slot_offset'], 16), s['pc'])

    def test_admitted_row_leaves_the_unresolved_set_and_others_stay(self):
        admitted = set(self.expected['summary']['admitted'])
        for s in self.in_report():
            row = self.rows[s['pc']]['admission']
            if s['pc'] in admitted:
                self.assertEqual((row['status'], row['reason']), ('declined', 'value_witness_abi_nonthrowing'))
            else:
                self.assertEqual((row['status'], row['reason']), ('unresolved', 'indirect_target_unresolved'))

    def test_totals(self):
        s = self.expected['summary']
        self.assertEqual(self.report['indirect_target_shape_counts'], {'value_witness': s['in_report_sites']})
        self.assertEqual(self.report['value_witness_admission_counts'],
                         {'admitted': len(s['admitted']), 'refused': len(s['not_admitted_in_report'])})

    def test_out_of_report_got_sites_carry_no_record(self):
        for pc in self.expected['summary']['out_of_report_got_sites']:
            self.assertNotIn(pc, self.rows)
        self.assertEqual(self.report['got_counts']['non_swift_got_calls'], self.expected['summary']['non_swift_got_calls'])


if __name__ == '__main__':
    unittest.main()
