"""Isolated bootstrap acceptance on fresh synthetic saved reports; no audit run."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_diff_manual_pairs import pair,A,B,C

ROOT=Path(__file__).resolve().parents[1]


class ManualPairCLITests(unittest.TestCase):
    def invoke(self,extra):
        directory=ROOT/'local-evidence/manual-pair-cli';directory.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=directory) as temporary:
            before,after=pair();left=Path(temporary)/'before report.json';right=Path(temporary)/'after report.json'
            left.write_text(json.dumps(before));right.write_text(json.dumps(after))
            result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'airs_cli.py'),'diff',
                                   '--baseline',str(left),'--current',str(right),*extra],
                                  cwd=temporary,capture_output=True,text=True,timeout=15)
            self.assertEqual(json.loads(left.read_text()),before)
            self.assertEqual(json.loads(right.read_text()),after)
            return result

    def test_pair_flag_records_review_basis_in_saved_report_comparison(self):
        result=self.invoke(['--pair',f'{A}={B}'])
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['changes'][0]['match_basis'],'manual_review')
        self.assertEqual(report['comparison']['manual_pairs'],[{'baseline_id':A,'current_id':B}])

    def test_pair_text_output_exposes_basis_ids_and_review_limit(self):
        result=self.invoke(['--pair',f'{A}={B}','--format','text'])
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertIn('manual_review',result.stdout)
        self.assertIn(A,result.stdout);self.assertIn(B,result.stdout)
        self.assertIn('does not prove',result.stdout)

    def test_malformed_pair_has_structured_error_and_no_partial_report(self):
        result=self.invoke(['--pair','missing-separator'])
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stdout,'')
        self.assertEqual(json.loads(result.stderr)['error']['code'],'invalid_manual_pair')

    def test_unknown_endpoint_has_structured_error(self):
        result=self.invoke(['--pair',f'{A}={C}'])
        self.assertEqual(result.returncode,2)
        self.assertEqual(result.stdout,'')
        self.assertEqual(json.loads(result.stderr)['error']['code'],'invalid_manual_pair')

    def test_repeated_identical_pair_flags_canonicalize_to_one_selection(self):
        result=self.invoke(['--pair',f'{A}={B}','--pair',f'{A}={B}'])
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['summary']['matched_count'],1)
        self.assertEqual(len(report['comparison']['manual_pairs']),1)
