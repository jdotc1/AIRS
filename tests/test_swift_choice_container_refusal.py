"""Malformed in-process choice containers remain unresolved."""
from copy import deepcopy
import unittest
from airs.swift_error_flow import _return_choice
from test_swift_literal_outcome_summary import report
from test_swift_return_choice_tail_binding import shared_variants
from test_swift_success_entry_choice_tail import direct_variants

class ChoiceContainerRefusalTests(unittest.TestCase):
    def cases(self):
        for name, words in list(shared_variants()) + list(direct_variants()):
            yield name, report(words)['calls'][0]

    def assert_unresolved(self, call, reason):
        before = deepcopy(call)
        result = _return_choice(call)
        self.assertEqual(result['status'], 'unresolved')
        self.assertEqual(result['reason'], reason)
        for key in ('source_reconstruction_allowed', 'runtime_value_proven', 'exclusive_path_proven',
                    'caller_return_type_proven', 'call_return_proven', 'handler_semantics_proven'):
            self.assertIs(result[key], False)
        self.assertEqual(call, before)

    def test_valid_choices_and_non_dict_calls(self):
        for name, call in self.cases():
            with self.subTest(name=name):
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
        for call in (None, [], 'call', 1, False):
            with self.subTest(call=call): self.assert_unresolved(call, 'outcome_evidence_inconsistent')

    def test_presentation_container_is_unresolved(self):
        for name, original in self.cases():
            for value in (None, [], 'presentation', 1, False):
                with self.subTest(name=name, value=value):
                    call = deepcopy(original); call['presentation'] = value
                    self.assert_unresolved(call, 'structural_presentation_not_eligible')
            call = deepcopy(original); del call['presentation']
            self.assert_unresolved(call, 'structural_presentation_not_eligible')

    def test_outcome_containers_and_missing_outcomes_are_unresolved(self):
        for name, original in self.cases():
            for field in ('error_constant', 'success_constant', 'success_result'):
                for value in (None, [], 'outcome', 1, False):
                    with self.subTest(name=name, field=field, value=value):
                        call = deepcopy(original); call[field] = value
                        self.assert_unresolved(call, 'outcome_evidence_missing_or_conflicting')
            call = deepcopy(original); del call['error_constant']
            self.assert_unresolved(call, 'outcome_evidence_missing_or_conflicting')

    def test_region_and_required_callee_containers_are_unresolved(self):
        for name, original in self.cases():
            for value in (None, [], 'region', 1, False):
                with self.subTest(name=name, field='region', value=value):
                    call = deepcopy(original); call['error_region'] = value
                    self.assert_unresolved(call, 'outcome_evidence_inconsistent')
            call = deepcopy(original); del call['error_region']
            self.assert_unresolved(call, 'outcome_evidence_inconsistent')
            if original['success_result']['status'] not in ('preserved_register_candidate', 'copied_register_candidate', 'adjusted_register_candidate'): continue
            for value in (None, [], 'callee', 1, False):
                with self.subTest(name=name, field='callee', value=value):
                    call = deepcopy(original); call['callee'] = value
                    self.assert_unresolved(call, 'outcome_evidence_inconsistent')
            call = deepcopy(original); del call['callee']
            self.assert_unresolved(call, 'outcome_evidence_inconsistent')

    def test_missing_unselected_outcome_retains_valid_choice(self):
        for name, original in self.cases():
            call = deepcopy(original)
            unselected = ('success_result' if call['success_constant']['status'] == 'constant_register_candidate'
                          else 'success_constant')
            del call[unselected]
            with self.subTest(name=name, missing=unselected):
                self.assertEqual(_return_choice(call)['status'], 'structural_choice_candidate')
