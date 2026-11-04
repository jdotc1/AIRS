"""Optional development validation of the published comparison schema."""
import json
from pathlib import Path
import unittest
try:
    from jsonschema import Draft202012Validator, ValidationError
except ImportError:
    Draft202012Validator = None
    ValidationError = None
from airs.diff import compare_reports
from test_exact_body_candidates import annotated_pair
from test_diff_manual_pairs import A, B


@unittest.skipIf(Draft202012Validator is None, "Optional development jsonschema validator is unavailable")
class ComparisonSchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = json.loads((Path(__file__).resolve().parents[1] / "schemas/baseline-diff-v1.schema.json").read_text())
        cls.validator = Draft202012Validator(cls.schema)

    def test_manual_producer_output_is_valid(self):
        report = compare_reports(*annotated_pair(), manual_pairs=[(A, B)])
        self.validator.validate(report)

    def ordinary(self):
        return compare_reports(*annotated_pair())

    def manual(self):
        return compare_reports(*annotated_pair(), manual_pairs=[(A, B)])

    def test_default_producer_output_is_valid(self):
        self.validator.validate(self.ordinary())

    def test_body_producer_output_is_valid(self):
        self.validator.validate(compare_reports(*annotated_pair(), match_exact_bodies=True))

    def test_manual_body_producer_output_is_valid(self):
        self.validator.validate(compare_reports(*annotated_pair(), manual_pairs=[(A, B)], match_exact_bodies=True))

    def test_same_image_producer_output_is_valid_in_both_states(self):
        for setting in (False, True):
            before, after = annotated_pair()
            after['image']['slice_sha256'] = before['image']['slice_sha256']
            self.validator.validate(compare_reports(before, after, match_exact_bodies=setting))

    def test_legacy_missing_optional_metadata_remains_valid(self):
        report = self.ordinary()
        report['comparison'].pop('exact_body_candidates')
        report['comparison'].pop('manual_pairs', None)
        self.validator.validate(report)

    def test_unknown_policy_refuses(self):
        report = self.ordinary()
        report['comparison']['matching_policy'] = 'future_policy'
        with self.assertRaises(ValidationError):
            self.validator.validate(report)

    def test_unknown_basis_refuses(self):
        report = self.ordinary()
        report['changes'][0]['match_basis'] = 'future_basis'
        with self.assertRaises(ValidationError):
            self.validator.validate(report)

    def test_body_status_requires_boolean_when_present(self):
        for status in (None, 0, 1, 'false', [], {}):
            with self.subTest(status=status):
                report = self.ordinary()
                report['comparison']['exact_body_candidates'] = status
                with self.assertRaises(ValidationError):
                    self.validator.validate(report)

    def test_manual_metadata_requires_array_when_present(self):
        for pairs in (None, {}, 'pairs', 1):
            with self.subTest(pairs=pairs):
                report = self.manual()
                report['comparison']['manual_pairs'] = pairs
                with self.assertRaises(ValidationError):
                    self.validator.validate(report)

    def test_manual_pair_requires_exact_two_fields(self):
        for pair in ({'baseline_id': A}, {'current_id': B},
                     {'baseline_id': A, 'current_id': B, 'extra': True}):
            with self.subTest(pair=pair):
                report = self.manual()
                report['comparison']['manual_pairs'] = [pair]
                with self.assertRaises(ValidationError):
                    self.validator.validate(report)

    def test_manual_pair_ids_preserve_exact_spelling(self):
        for identifier in (A + '\n', A + ' ', A[:-1], 'airsf-' + 'A' * 64, None, 1):
            for side in ('baseline_id', 'current_id'):
                with self.subTest(identifier=identifier, side=side):
                    report = self.manual()
                    report['comparison']['manual_pairs'][0][side] = identifier
                    with self.assertRaises(ValidationError):
                        self.validator.validate(report)

    def test_manual_pair_collection_cap_is_structural(self):
        report = self.manual()
        entry = report['comparison']['manual_pairs'][0]
        # Endpoint bijection is a semantic host check, not this structural schema.
        report['comparison']['manual_pairs'] = [entry] * 50_000
        self.validator.validate(report)
        report['comparison']['manual_pairs'].append(entry)
        with self.assertRaises(ValidationError):
            self.validator.validate(report)

    def test_schema_is_valid_draft_2020_12(self):
        Draft202012Validator.check_schema(self.schema)
