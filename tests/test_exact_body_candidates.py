"""Saved-report exact-body candidate selection; placeholder digests, no hashing."""
from copy import deepcopy
import unittest
from airs.diff import compare_reports
from airs.types import InputError
from test_diff_manual_pairs import pair,second,A,B,C,D


def annotated_pair():
    before,after=pair()
    for report in (before,after):
        report['findings'][0]['function']['body_fingerprint']={
            'kind':'arm64-exact-bytes-v1','sha256':'e'*64,'instruction_count':4}
    return before,after


class ExactBodyCandidateTests(unittest.TestCase):
    def test_opt_in_unique_body_joins_stripped_or_renamed_findings(self):
        for names in (('sub_1000','loc_2000'),('_old_name','_new_name')):
            before,after=annotated_pair()
            before['findings'][0]['function']['name'],after['findings'][0]['function']['name']=names
            result=compare_reports(before,after,match_exact_bodies=True)
            self.assertEqual(result['summary']['matched_count'],1)
            row=result['changes'][0]
            self.assertEqual((row['match_basis'],row['baseline_id'],row['current_id']),('exact_body_candidate',A,B))
            self.assertTrue(any('does not prove' in note for note in row['notes']))
            self.assertTrue(result['comparison']['exact_body_candidates'])

    def test_default_is_off_and_missing_or_changed_fingerprint_never_matches(self):
        before,after=annotated_pair()
        default=compare_reports(before,after)
        self.assertEqual(default['summary']['matched_count'],0)
        self.assertNotIn('exact_body_candidates',default['comparison'])
        for absent in (True,False):
            changed=deepcopy(after)
            if absent:del changed['findings'][0]['function']['body_fingerprint']
            else:changed['findings'][0]['function']['body_fingerprint']['sha256']='f'*64
            self.assertEqual(compare_reports(before,changed,match_exact_bodies=True)['summary']['matched_count'],0)

    def test_nonunique_body_never_selects_arbitrary_endpoint(self):
        before,after=annotated_pair();second(before,C,'sub_1010')
        result=compare_reports(before,after,match_exact_bodies=True)
        self.assertEqual(result['summary']['matched_count'],0)
        self.assertEqual(result['summary']['removed_count'],2)
        self.assertEqual(result['summary']['added_count'],1)
        self.assertTrue(any('not unique' in note for row in result['changes'] for note in row['notes']))

    def test_manual_pair_precedes_body_and_remaining_endpoints_are_not_reused(self):
        before,after=annotated_pair();second(before,C,'sub_1010');second(after,D,'loc_2010')
        result=compare_reports(before,after,manual_pairs=[(A,D)],match_exact_bodies=True)
        self.assertEqual(result['summary']['matched_count'],2)
        self.assertEqual({(row['baseline_id'],row['current_id'],row['match_basis']) for row in result['changes']},
                         {(A,D,'manual_review'),(C,B,'exact_body_candidate')})

    def test_unique_symbol_precedes_crossed_body_evidence(self):
        before,after=annotated_pair();before['findings'][0]['function']['name']='_stable'
        after['findings'][0]['function']['name']='_other'
        second(before,C,'_other');second(after,D,'_stable')
        before['findings'][1]['function']['body_fingerprint']['sha256']='f'*64
        after['findings'][1]['function']['body_fingerprint']['sha256']='f'*64
        result=compare_reports(before,after,match_exact_bodies=True)
        self.assertEqual({(row['baseline_id'],row['current_id'],row['match_basis']) for row in result['changes']},
                         {(A,D,'unique_symbol'),(C,B,'unique_symbol')})

    def test_same_image_offset_matching_precedes_body(self):
        before,after=annotated_pair();after['image']['slice_sha256']=before['image']['slice_sha256']
        after['findings'][0]['function']['body_fingerprint']['sha256']='f'*64
        result=compare_reports(before,after,match_exact_bodies=True)
        self.assertEqual(result['changes'][0]['match_basis'],'exact_image_offset')

    def test_model_and_configuration_mismatch_still_ambiguous(self):
        for fault in ('model','config'):
            before,after=annotated_pair()
            if fault=='model':after['generator']['analysis_model_version']='future-model'
            else:after['analysis_config']={'limits':{}}
            result=compare_reports(before,after,match_exact_bodies=True)
            self.assertEqual(result['summary']['matched_count'],1)
            self.assertEqual(result['summary']['ambiguous_count'],1)
            self.assertEqual(result['summary']['changed_count'],0)
            self.assertEqual(result['summary']['unchanged_count'],0)

    def test_exact_cpu_subtype_required_for_automatic_body_candidate(self):
        before,after=annotated_pair();after['image']['cpu_subtype']=1
        result=compare_reports(before,after,match_exact_bodies=True)
        self.assertEqual(result['summary']['matched_count'],0)

    def test_duplicate_symbol_ambiguity_is_not_silently_resolved(self):
        before,after=annotated_pair()
        for report,fid in ((before,C),(after,D)):
            report['findings'][0]['function']['name']='_duplicate'
            second(report,fid,'_duplicate')
            report['findings'][1]['function']['body_fingerprint']['sha256']='f'*64
        result=compare_reports(before,after,match_exact_bodies=True)
        self.assertEqual(result['summary']['matched_count'],0)
        self.assertEqual(result['summary']['ambiguous_count'],1)

    def test_opt_in_type_is_strict_and_malformed_body_is_rejected(self):
        for value in (None,1,'yes'):
            with self.assertRaises(InputError):compare_reports(*annotated_pair(),match_exact_bodies=value)
        before,after=annotated_pair();after['findings'][0]['function']['body_fingerprint']['kind']='future'
        with self.assertRaises(InputError):compare_reports(before,after,match_exact_bodies=True)

    def test_order_determinism_and_input_preservation(self):
        before,after=annotated_pair();second(before,C,'sub_1010');second(after,D,'loc_2010')
        for report in (before,after):report['findings'][1]['function']['body_fingerprint']['sha256']='f'*64
        originals=deepcopy((before,after))
        result=compare_reports(before,after,match_exact_bodies=True)
        self.assertEqual((before,after),originals)
        before['findings'].reverse();after['findings'].reverse()
        self.assertEqual(compare_reports(before,after,match_exact_bodies=True),result)

    def test_blocked_ambiguous_symbol_members_prevent_false_standalone_uniqueness(self):
        before,after=annotated_pair()
        before['findings'][0]['function']['name']='_duplicate'
        second(before,C,'_duplicate')
        third=deepcopy(before['findings'][0]);third['id']='airsf-'+'9'*64
        third['function'].update(name='sub_1020',address='0x1020',end_address='0x1030',image_offset='0x20')
        third['checked_pcs']=['0x1028'];before['findings'].append(third)
        before['image']['slice_size']=48;before['metadata_ranges'][0]['end']='0x1030'
        before['summary'].update(function_count=3,agreement_count=3,checked_pc_count=3)
        result=compare_reports(before,after,match_exact_bodies=True)
        self.assertEqual(result['summary']['matched_count'],0)
        self.assertEqual(result['summary']['ambiguous_count'],1)
        self.assertEqual(result['summary']['removed_count'],1)
        self.assertEqual(result['summary']['added_count'],1)
        self.assertTrue(any('not unique' in note for row in result['changes'] for note in row['notes']))

    def test_digest_alone_cannot_join_different_instruction_counts(self):
        before,after=annotated_pair()
        first=after['findings'][0]
        first['function'].update(size=20,end_address='0x1014')
        first['function']['body_fingerprint']['instruction_count']=5
        first['instruction_count']=5;after['image']['slice_size']=20
        after['metadata_ranges'][0]['end']='0x1014'
        self.assertEqual(compare_reports(before,after,match_exact_bodies=True)['summary']['matched_count'],0)

    def test_body_equality_does_not_override_changed_checked_scope_signature(self):
        before,after=annotated_pair()
        after['findings'][0]['checked_pcs']=['0x100c']
        result=compare_reports(before,after,match_exact_bodies=True)
        self.assertEqual(result['changes'][0]['match_basis'],'exact_body_candidate')
        self.assertEqual(result['summary']['changed_count'],1)
        self.assertEqual(result['summary']['unchanged_count'],0)
