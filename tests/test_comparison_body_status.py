"""Explicit producer option metadata; saved synthetic reports only."""
from copy import deepcopy
import json
import unittest
from airs.diff import compare_reports
from airs.types import InputError
from test_diff_manual_pairs import A, B
from test_exact_body_candidates import annotated_pair


class ComparisonBodyStatusTests(unittest.TestCase):
    def test_default_records_explicit_false(self):
        report = compare_reports(*annotated_pair())
        self.assertIs(report['comparison'].get('exact_body_candidates'), False)
        self.assertEqual(report['summary']['matched_count'], 0)

    def test_explicit_false_matches_default_output(self):
        before, after = annotated_pair()
        default = compare_reports(before, after)
        disabled = compare_reports(before, after, match_exact_bodies=False)
        self.assertEqual(default, disabled)
        self.assertIs(disabled['comparison']['exact_body_candidates'], False)

    def test_true_records_enabled_candidate_setting(self):
        report = compare_reports(*annotated_pair(), match_exact_bodies=True)
        self.assertIs(report['comparison']['exact_body_candidates'], True)
        self.assertEqual(report['changes'][0]['match_basis'], 'exact_body_candidate')
        self.assertEqual(report['comparison']['matching_policy'].count('_then_exact_body_candidate'), 1)

    def test_same_image_default_records_false_without_changing_offset_authority(self):
        before, after = annotated_pair()
        after['image']['slice_sha256'] = before['image']['slice_sha256']
        report = compare_reports(before, after)
        self.assertIs(report['comparison']['exact_body_candidates'], False)
        self.assertEqual(report['changes'][0]['match_basis'], 'exact_image_offset')
        self.assertEqual(report['comparison']['matching_policy'], 'exact_digest_then_unique_symbol')

    def test_same_image_true_records_request_even_when_body_phase_is_bypassed(self):
        before, after = annotated_pair()
        after['image']['slice_sha256'] = before['image']['slice_sha256']
        report = compare_reports(before, after, match_exact_bodies=True)
        self.assertIs(report['comparison']['exact_body_candidates'], True)
        self.assertEqual(report['changes'][0]['match_basis'], 'exact_image_offset')
        self.assertTrue(report['comparison']['matching_policy'].endswith('_then_exact_body_candidate'))

    def test_manual_default_records_false_with_plain_manual_policy(self):
        report = compare_reports(*annotated_pair(), manual_pairs=[(A, B)])
        self.assertIs(report['comparison']['exact_body_candidates'], False)
        self.assertEqual(report['comparison']['matching_policy'], 'manual_then_unique_symbol')
        self.assertEqual(report['changes'][0]['match_basis'], 'manual_review')

    def test_manual_true_preserves_recorded_opt_in(self):
        report = compare_reports(*annotated_pair(), manual_pairs=[(A, B)], match_exact_bodies=True)
        self.assertIs(report['comparison']['exact_body_candidates'], True)
        self.assertEqual(report['comparison']['matching_policy'], 'manual_then_unique_symbol_then_exact_body_candidate')
        self.assertEqual(report['changes'][0]['match_basis'], 'manual_review')

    def test_non_boolean_settings_remain_invalid(self):
        for value in (None, 0, 1, 0.0, 'false', [], {}):
            with self.subTest(value=value):
                with self.assertRaises(InputError):
                    compare_reports(*annotated_pair(), match_exact_bodies=value)

    def test_option_metadata_does_not_mutate_source_reports(self):
        before, after = annotated_pair()
        original = deepcopy((before, after))
        for setting in (False, True):
            report = compare_reports(before, after, match_exact_bodies=setting)
            self.assertIs(report['comparison']['exact_body_candidates'], setting)
            self.assertNotIn('exact_body_candidates', report)
        self.assertEqual((before, after), original)

    def test_false_does_not_add_body_policy_or_limitations(self):
        report = compare_reports(*annotated_pair(), match_exact_bodies=False)
        self.assertEqual(report['comparison']['matching_policy'], 'exact_digest_then_unique_symbol')
        self.assertFalse(any(text.startswith('Exact-body candidates require') for text in report['limitations']))
        self.assertEqual({row['match_basis'] for row in report['changes']}, {'unmatched'})

    def test_wire_status_is_boolean_in_both_states(self):
        for setting in (False, True):
            report = json.loads(json.dumps(compare_reports(*annotated_pair(), match_exact_bodies=setting)))
            self.assertIs(report['comparison']['exact_body_candidates'], setting)
            self.assertIs(type(report['comparison']['exact_body_candidates']), bool)
