"""MacScope-style manual pin validation adapted to saved AIRS findings."""
from copy import deepcopy
import unittest
from airs.diff import compare_reports
from airs.types import InputError
from test_report_v32_admission_candidate import synthetic_report

A='airsf-'+'a'*64
B='airsf-'+'b'*64
C='airsf-'+'c'*64
D='airsf-'+'d'*64


def pair():
    before=synthetic_report();after=deepcopy(before)
    before['findings'][0]['function']['name']='sub_1000'
    after['findings'][0]['function']['name']='loc_2000'
    after['findings'][0]['id']=B
    after['image']['slice_sha256']='3'*64
    return before,after


def second(report,fid,name):
    item=deepcopy(report['findings'][0]);item['id']=fid
    item['function'].update(name=name,address='0x1010',end_address='0x1020',image_offset='0x10')
    item['checked_pcs']=['0x1018'];report['findings'].append(item)
    report['image']['slice_size']=32;report['metadata_ranges'][0]['end']='0x1020'
    report['summary'].update(function_count=2,agreement_count=2,checked_pc_count=2)


class ManualPairTests(unittest.TestCase):
    def test_explicit_pair_joins_stripped_functions_as_review_only(self):
        result=compare_reports(*pair(),manual_pairs=[(A,B)])
        self.assertEqual(result['summary']['matched_count'],1)
        self.assertEqual(result['summary']['unchanged_count'],1)
        row=result['changes'][0]
        self.assertEqual((row['match_basis'],row['baseline_id'],row['current_id']),('manual_review',A,B))
        self.assertTrue(any('does not prove' in note for note in row['notes']))
        self.assertEqual(result['comparison']['manual_pairs'],[{'baseline_id':A,'current_id':B}])
        self.assertEqual(result['comparison']['matching_policy'],'manual_then_unique_symbol')

    def test_duplicate_identical_pairs_are_idempotent_and_canonical(self):
        before,after=pair();second(before,C,'sub_1010');second(after,D,'loc_2010')
        one=compare_reports(before,after,manual_pairs=[(C,D),(A,B),(A,B)])
        two=compare_reports(before,after,manual_pairs=[(A,B),(C,D)])
        self.assertEqual(one,two)
        self.assertEqual(one['summary']['matched_count'],2)

    def test_unknown_endpoints_and_conflicting_pins_reject(self):
        before,after=pair();second(before,C,'sub_1010');second(after,D,'loc_2010')
        for pins in ([(D,B)],[(A,C)],[(A,B),(A,D)],[(A,B),(C,B)]):
            with self.assertRaises(InputError) as caught:compare_reports(before,after,manual_pairs=pins)
            self.assertEqual(caught.exception.code,'invalid_manual_pair')

    def test_malformed_pair_shapes_and_types_reject(self):
        for pins in (None, 'ids',[(A,)],[(A,B,C)],[(None,B)],[(A,7)],[{}]):
            with self.assertRaises(InputError):compare_reports(*pair(),manual_pairs=pins)

    def test_same_image_pair_cannot_override_exact_offset_authority(self):
        before,after=pair();after['image']['slice_sha256']=before['image']['slice_sha256']
        with self.assertRaises(InputError) as caught:compare_reports(before,after,manual_pairs=[(A,B)])
        self.assertEqual(caught.exception.code,'invalid_manual_pair')

    def test_manual_pair_keeps_architecture_model_and_config_ambiguity(self):
        for fault in ('architecture','model','config'):
            before,after=pair()
            if fault=='architecture':
                after['image']['architecture']='arm64e'
                after['generator']['analysis_model_version']='future-model'
            elif fault=='model':after['generator']['analysis_model_version']='future-model'
            else:after['analysis_config']={'limits':{}}
            result=compare_reports(before,after,manual_pairs=[(A,B)])
            self.assertEqual(result['summary']['matched_count'],1)
            self.assertEqual(result['summary']['ambiguous_count'],1)
            self.assertEqual(result['summary']['changed_count'],0)
            self.assertEqual(result['summary']['unchanged_count'],0)

    def test_manual_pair_precedes_symbols_and_automatic_remainder_is_one_to_one(self):
        before,after=pair();before['findings'][0]['function']['name']='_same'
        after['findings'][0]['function']['name']='_different'
        second(before,C,'_different');second(after,D,'_same')
        result=compare_reports(before,after,manual_pairs=[(A,B)])
        self.assertEqual(result['summary']['matched_count'],1)
        self.assertEqual(result['summary']['added_count'],1)
        self.assertEqual(result['summary']['removed_count'],1)
        self.assertEqual(sum(row['match_basis']=='manual_review' for row in result['changes']),1)

    def test_inputs_are_preserved_and_empty_pins_keep_legacy_wire_shape(self):
        before,after=pair();originals=deepcopy((before,after))
        compare_reports(before,after,manual_pairs=[(A,B)])
        self.assertEqual((before,after),originals)
        result=compare_reports(before,after,manual_pairs=[])
        self.assertNotIn('manual_pairs',result['comparison'])
        self.assertEqual(result['comparison']['matching_policy'],'exact_digest_then_unique_symbol')

    def test_raw_pair_cap_is_enforced_before_deduplication(self):
        with self.assertRaises(InputError) as caught:
            compare_reports(*pair(),manual_pairs=[(A,B)]*50_001)
        self.assertEqual(caught.exception.code,'invalid_manual_pair')
