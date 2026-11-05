"""New opt-in coordinator contracts over tiny owned inputs."""
import unittest
from copy import deepcopy
from unittest.mock import patch
from airs.swift_error_flow import recover_swift_error_flow
from test_swift_error_flow import image
from test_swift_shared_epilogue import WORDS

class IntegrationTests(unittest.TestCase):
    def test_opt_in_adds_validated_witness_without_legacy_changes(self):
        im=image(WORDS)
        options=dict(include_error_regions=True,validate_region_entries=True,include_structured_presentation=True)
        legacy=recover_swift_error_flow(im,**options)
        value=recover_swift_error_flow(im,include_outcome_witnesses=True,**options)
        self.assertTrue(value['outcome_witnesses_complete'])
        self.assertEqual(value['calls'][0]['outcome_witness']['status'],'eligible_structural_only')
        self.assertLessEqual(value['outcome_witness_work_steps'],262144)
        stripped=deepcopy(value)
        for key in ('outcome_witness_model_version','outcome_validation_model_version','outcome_witnesses_complete','outcome_witness_work_steps'):stripped.pop(key)
        for key in list(stripped['summary']):
            if key.startswith(('witness_','outcome_witness')):stripped['summary'].pop(key)
        for call in stripped['calls']:call.pop('outcome_witness')
        self.assertEqual(stripped,legacy)
    def test_aggregate_budget_is_passed_and_incomplete_is_visible(self):
        im=image(WORDS)
        def limited(*args,**kw):
            self.assertEqual(kw['limits'].max_total_work,262144)
            return dict(status='unresolved',reason='witness_total_work_limit',details_complete=False,work_steps=262144)
        with patch('airs.swift_outcome_witness_validation.validate_outcome_witness',side_effect=limited):
            value=recover_swift_error_flow(im,include_outcome_witnesses=True,include_error_regions=True,validate_region_entries=True,include_structured_presentation=True)
        self.assertFalse(value['outcome_witnesses_complete'])
