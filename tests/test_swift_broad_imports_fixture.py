"""Owned real-toolchain case for broad-imports-v1.

expected.json was derived from Apple tools (otool -Iv, objdump -d,
swift-demangle) independently of AIRS. These tests compare AIRS stub
attribution and imported-call selection with that record. The binary is
never executed.
"""
import hashlib
import json
import unittest
from pathlib import Path

from airs.macho import parse_macho
from airs.macho_stubs import STUB_MODEL, attribute_import_stubs
from airs.swift_broad_flow import (EXTENDED_BROAD_LIMITS, IMPORTS_BROAD_LIMITS,
                                   recover_swift_broad_flow)

FIXTURE = Path(__file__).resolve().parents[1] / 'fixtures' / 'swift-error-flow' / 'broad-imports'
IMPORT_KEYS = {'import_stub_model', 'import_stubs_complete', 'import_stub_reason', 'import_stub_counts'}


class OwnedImportsFixtureTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.expected = json.loads((FIXTURE / 'expected.json').read_text())
        cls.data = (FIXTURE / cls.expected['binary']).read_bytes()

    def image(self, limits):
        return parse_macho(self.data, 'OwnedImports.macho', limits)

    def test_fixture_bytes_match_recorded_identity(self):
        self.assertLess(len(self.data), 256 * 1024)
        self.assertEqual(hashlib.sha256(self.data).hexdigest(), self.expected['binary_sha256'])

    def test_every_stub_attributes_to_the_otool_symbol_and_slot(self):
        table = attribute_import_stubs(self.image(IMPORTS_BROAD_LIMITS))
        self.assertEqual(table.model, STUB_MODEL)
        self.assertTrue(table.complete)
        self.assertIsNone(table.reason)
        self.assertEqual(dict(table.declined), {})
        self.assertEqual(table.invalid_sections, ())
        self.assertEqual(table.stub_sections, 1)
        expected = {s['address']: (s['symbol'], s['pointer_address']) for s in self.expected['stubs']}
        actual = {a: (s.symbol, s.pointer_address) for a, s in table.attributed.items()}
        self.assertEqual(actual, expected)
        got = self.expected['pointer_sections'][0]
        label = got['segment'] + ',' + got['section']
        self.assertTrue(all(s.pointer_section == label and s.section == '__TEXT,__stubs'
                            for s in table.attributed.values()))

    def test_selected_import_rows_match_toolchain_stub_calls(self):
        report = recover_swift_broad_flow(self.image(IMPORTS_BROAD_LIMITS), profile='broad-imports-v1')
        calls = self.expected['stub_calls']
        swift = [c for c in calls if c['symbol'].lstrip('_').startswith('$s')]
        expectations = self.expected['import_declaration_expectations']
        skipped = [c for c in swift if expectations[c['symbol']]['outcome'] == 'skip_non_throwing']
        retained = [c for c in swift if expectations[c['symbol']]['outcome'] != 'skip_non_throwing']
        self.assertEqual(len({c['symbol'] for c in swift}), 19)
        self.assertEqual(set(expectations), {c['symbol'] for c in swift})
        self.assertEqual(sum(e['outcome'] == 'skip_non_throwing' for e in expectations.values()), 10)
        self.assertEqual((len(swift), len(skipped), len(retained)), (27, 15, 12))
        rows = [c['admission'] for c in report['calls']
                if c['admission'].get('model_version') == 'swift-broad-import-callsite-v1']
        self.assertEqual(sorted((r['call_pc'], r['call_kind'], r['callee_stub_pc'], r['symbol']) for r in rows),
                         sorted((c['call_pc'], c['kind'], c['stub_address'], c['symbol']) for c in retained))
        self.assertTrue({c['call_pc'] for c in swift if c['demangled_throws']} <= {r['call_pc'] for r in rows})
        counts = report['import_stub_counts']
        self.assertEqual(counts['attributed_stubs'], len(self.expected['stubs']))
        self.assertEqual(counts['declined_stubs'], 0)
        self.assertEqual(counts['declined_stub_calls'], 0)
        self.assertEqual(counts['non_swift_import_calls'], len(calls) - len(swift))
        self.assertEqual(counts['selected_import_calls'] + counts['non_throwing_swift_import_calls'], len(swift))
        self.assertEqual(counts['selected_import_calls'], len(rows))
        self.assertEqual(counts['non_throwing_swift_import_calls'], len(skipped))
        self.assertTrue(report['import_stubs_complete'])
        self.assertEqual(report['limitations'][-1], 'imported_callees_attribution_only')
        self.assertEqual(report['reason_counts'].get('imported_callee_abi_unqualified'), len(rows))
        for row in rows:
            self.assertEqual((row['status'], row['reason']), ('unresolved', 'imported_callee_abi_unqualified'))
            self.assertFalse(row['call_return_proven'])
            self.assertTrue(row['import_attribution_admitted'])
            self.assertEqual(row['import_provenance']['stub_model'], STUB_MODEL)
            # Throwing admissions and declined declarations remain attributed rows.
            outcome = expectations[row['symbol']]['outcome']
            self.assertEqual(row['declaration']['status'],
                             'syntax_admitted' if outcome == 'syntax_admitted_throwing' else 'syntax_unresolved')
            if outcome == 'syntax_admitted_throwing':
                self.assertIs(row['declaration']['identity']['throws'], True)
        self.assertTrue(all(c['candidate'] is None and c['validation'] is None for c in report['calls']
                            if c['admission'].get('model_version') == 'swift-broad-import-callsite-v1'))

    def test_extended_profile_ignores_imported_stubs(self):
        report = recover_swift_broad_flow(self.image(EXTENDED_BROAD_LIMITS), profile='broad-extended-v1')
        self.assertFalse(IMPORT_KEYS & set(report))
        self.assertNotIn('imported_callees_attribution_only', report['limitations'])
        self.assertFalse(any(c['admission'].get('model_version') == 'swift-broad-import-callsite-v1'
                             for c in report['calls']))


if __name__ == '__main__':
    unittest.main()
