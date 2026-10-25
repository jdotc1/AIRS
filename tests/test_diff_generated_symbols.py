"""MacScope generated-name guard adapted to AIRS saved-report comparison.

Synthetic report objects only; no sealed report/image is loaded or reverified.
"""
from copy import deepcopy
import unittest
from airs.diff import compare_reports
from test_report_v32_admission_candidate import synthetic_report


def pair(name, *, same_image=False):
    before=synthetic_report()
    before['findings'][0]['function']['name']=name
    after=deepcopy(before)
    after['image']['display_name']='different-build'
    if not same_image: after['image']['slice_sha256']='3'*64
    return before,after


class GeneratedSymbolComparisonTests(unittest.TestCase):
    def test_donor_generated_labels_never_join_different_builds(self):
        for name in ('_entry','__text','loc_1000','loc_0x1000','loc_0XABCD',
                     'unk_dead','off_0xABCD','nullsub_1000','nullsub_0x00af'):
            with self.subTest(name=name):
                result=compare_reports(*pair(name))
                self.assertEqual(result['summary']['matched_count'],0)
                self.assertEqual(result['summary']['added_count'],1)
                self.assertEqual(result['summary']['removed_count'],1)
                self.assertTrue(all(row['match_basis']=='unmatched' for row in result['changes']))

    def test_existing_generated_and_address_name_refusals_are_preserved(self):
        for name in ('','sub_1000','sub_real_name','<unknown>','0x1000','0X1000'):
            self.assertEqual(compare_reports(*pair(name))['summary']['matched_count'],0,name)

    def test_real_symbol_names_and_nonhex_prefix_suffixes_still_join(self):
        for name in ('_work','loc_handler','unk_value','off_table','nullsub_cleanup','location',
                     'loc_','nullsub_','my_sub_1000'):
            result=compare_reports(*pair(name))
            self.assertEqual(result['summary']['matched_count'],1,name)
            self.assertEqual(result['changes'][0]['match_basis'],'unique_symbol')
            self.assertTrue(any('review candidate' in note for note in result['changes'][0]['notes']))

    def test_exact_image_offsets_match_even_when_name_is_generated(self):
        for name in ('_entry','loc_1000','nullsub_0x1000','sub_1000',''):
            before,after=pair(name,same_image=True)
            after['findings'][0]['function']['name']='loc_renamed'
            result=compare_reports(before,after)
            self.assertTrue(result['comparison']['same_image'])
            self.assertEqual(result['summary']['matched_count'],1)
            self.assertEqual(result['changes'][0]['match_basis'],'exact_image_offset')

    def test_incompatible_models_or_configuration_never_create_supported_change(self):
        for fault in ('model','configuration'):
            before,after=pair('_work')
            if fault=='model':after['generator']['analysis_model_version']='future-model'
            else:after['analysis_config']={'limits':{}}
            result=compare_reports(before,after)
            self.assertEqual(result['summary']['matched_count'],1)
            self.assertEqual(result['summary']['ambiguous_count'],1)
            self.assertEqual(result['summary']['changed_count'],0)

    def test_order_is_deterministic_and_input_reports_unchanged(self):
        before,after=pair('loc_1000')
        originals=deepcopy((before,after))
        result=compare_reports(before,after)
        self.assertEqual((before,after),originals)
        self.assertEqual([row['key'] for row in result['changes']],sorted(row['key'] for row in result['changes']))
        self.assertEqual(sum(result['summary'][key] for key in ('added_count','removed_count')),2)

    def test_duplicate_real_symbols_remain_ambiguous_without_selecting_a_pair(self):
        before,after=pair('_duplicate')
        for report in (before,after):
            second=deepcopy(report['findings'][0])
            second['id']='airsf-'+'b'*64
            second['function'].update(address='0x1010',end_address='0x1020',image_offset='0x10')
            second['checked_pcs']=['0x1018']
            report['findings'].append(second)
            report['image']['slice_size']=32
            report['metadata_ranges'][0]['end']='0x1020'
            report['summary'].update(function_count=2,agreement_count=2,checked_pc_count=2)
        result=compare_reports(before,after)
        self.assertEqual(result['summary']['matched_count'],0)
        self.assertEqual(result['summary']['ambiguous_count'],1)
        self.assertNotIn('baseline_id',result['changes'][0])
        self.assertNotIn('current_id',result['changes'][0])

    def test_malformed_symbol_types_are_rejected_by_report_validation(self):
        from airs.types import InputError
        for name in (None,17,[]):
            with self.assertRaises(InputError):compare_reports(*pair(name))
