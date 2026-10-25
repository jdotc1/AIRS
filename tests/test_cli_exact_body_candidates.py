"""Isolated saved-report candidate matching; no binary reads or fingerprint hashes."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_exact_body_candidates import annotated_pair
from test_diff_manual_pairs import A,B

ROOT=Path(__file__).resolve().parents[1]


class ExactBodyCandidateCLITests(unittest.TestCase):
    def invoke(self,extra):
        root=ROOT/'local-evidence/exact-body-cli';root.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temporary:
            before,after=annotated_pair()
            left,right=Path(temporary)/'baseline.json',Path(temporary)/'current.json'
            left.write_text(json.dumps(before));right.write_text(json.dumps(after))
            result=subprocess.run([sys.executable,'-I','-B',str(ROOT/'airs_cli.py'),'diff',
                                   '--baseline',str(left),'--current',str(right),*extra],
                                  cwd=temporary,capture_output=True,text=True,timeout=15)
            self.assertEqual(json.loads(left.read_text()),before)
            self.assertEqual(json.loads(right.read_text()),after)
            return result

    def test_opt_in_json_exposes_candidate_basis_and_selected_ids(self):
        result=self.invoke(['--match-exact-bodies'])
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['summary']['matched_count'],1)
        self.assertEqual(report['changes'][0]['match_basis'],'exact_body_candidate')
        self.assertEqual((report['changes'][0]['baseline_id'],report['changes'][0]['current_id']),(A,B))
        self.assertTrue(report['comparison']['exact_body_candidates'])

    def test_text_exposes_candidate_and_review_limitations(self):
        result=self.invoke(['--match-exact-bodies','--format','text'])
        self.assertEqual(result.returncode,0,result.stderr)
        for text in ('exact_body_candidate',A,B,'does not prove','not authenticated'):
            self.assertIn(text,result.stdout)

    def test_default_keeps_legacy_unmatched_output(self):
        result=self.invoke([])
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['summary']['matched_count'],0)
        self.assertNotIn('exact_body_candidates',report['comparison'])

    def test_manual_pair_retains_precedence_with_flag_enabled(self):
        result=self.invoke(['--match-exact-bodies','--pair',f'{A}={B}'])
        self.assertEqual(result.returncode,0,result.stderr)
        report=json.loads(result.stdout)
        self.assertEqual(report['changes'][0]['match_basis'],'manual_review')
        self.assertEqual(report['comparison']['manual_pairs'],[{'baseline_id':A,'current_id':B}])
