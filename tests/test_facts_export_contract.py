"""Optional format vectors and schema checks supplied outside this repository."""
import json
import os
from pathlib import Path
import unittest

from airs import facts_export as ex
from airsnav_format_check import check
from test_facts_export import tiny, many_rows, canonical, independent_rules

CONTRACT = os.environ.get('AIRS_NAVIGATOR_CONTRACT_DIR')


@unittest.skipUnless(CONTRACT, 'AIRS_NAVIGATOR_CONTRACT_DIR is unset; external contract unavailable')
class ExternalContractTests(unittest.TestCase):
    def test_import_examples(self):
        root = Path(CONTRACT)/'import'
        expected = json.loads((root/'expected-reports.json').read_text())
        accepted = rejected = 0
        for row in expected['files']:
            if row.get('stage', 2) not in (2, 3, 5):
                continue
            with self.subTest(file=row['file']):
                raw = (root/'examples'/row['file']).read_bytes()
                ok, code, path = check(raw)
                self.assertEqual(ok, row['outcome'] == 'accepted')
                if ok:
                    accepted += 1
                    document = json.loads(raw)
                    self.assertEqual(len(document['results']), row['resultCount'])
                    for result in document['results']:
                        independent_rules(self, result)
                else:
                    rejected += 1
                    self.assertEqual(code, row['code'])
                    if 'path' in row:
                        self.assertEqual(path, row['path'])
        self.assertEqual(accepted, 4)
        self.assertEqual(rejected, 11)

    def test_exported_record_ids(self):
        reports = [tiny(), many_rows(520), tiny()]
        reports[-1].update(import_stubs_complete=False, import_stub_reason='stub_limit', calls=[])
        for report in reports:
            files, _ = ex.export_bytes(canonical(report), tool_version='test')
            for raw in files.values():
                document = json.loads(raw)
                expected = 'producerRefusal' if document['run']['refusalCount'] else None
                self.assertEqual(check(raw)[1], expected)
                for result in document['results']:
                    independent_rules(self, result)

    def test_schema_exported_results(self):
        try:
            import jsonschema
        except ImportError:
            self.skipTest('jsonschema is not importable; external schema validation unavailable')
        validator = jsonschema.Draft202012Validator(json.loads((Path(CONTRACT)/'navigator-engine.schema.json').read_text()))
        reports = [tiny(), many_rows(65), tiny()]
        reports[0].update(omitted_calls=1, word_scan_complete=False)
        reports[2].update(import_stubs_complete=False, import_stub_reason='stub_limit', calls=[])
        for report in reports:
            documents, _ = ex.export_report(report, tool_version='test')
            for document in documents:
                for result in document['results']:
                    validator.validate(result)
                    independent_rules(self, result)

    def test_vocabulary(self):
        vocabulary = json.loads((Path(CONTRACT)/'vocabulary.json').read_text())
        report = tiny()
        report.update(omitted_calls=1, word_scan_complete=False)
        documents, _ = ex.export_report(report, tool_version='test')
        for document in documents:
            for result in document['results']:
                for fact in result['facts']:
                    self.assertEqual(vocabulary['predicates'][fact['predicate']]['value'], 'string')
                    self.assertIn(fact['status'], vocabulary['statuses'])
                    for p in fact['provenance']:
                        self.assertIn(p['kind'], vocabulary['provenanceKinds'])
                for gap in result['frontier']:
                    self.assertIn(gap['gap'], vocabulary['gaps'])
