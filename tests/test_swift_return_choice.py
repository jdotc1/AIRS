"""Bind existing outcome evidence into a structural choice, not Swift source."""
import unittest
from test_swift_success_result import report, NOP
from test_swift_shared_epilogue import WORDS

class ReturnChoiceFirstTests(unittest.TestCase):
    def test_success_and_error_constants_form_one_bound_choice(self):
        value = report(WORDS)
        choice = value['calls'][0]['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['constant_bits'], '0x0000000000000000')
        self.assertEqual(choice['error']['constant_bits'], '0xffffffffffffffff')
        self.assertFalse(choice['same_constant_bits'])
        self.assertFalse(choice['source_reconstruction_allowed'])
        self.assertEqual(value['return_choice_model_version'], 'swift-return-choice-v11')

class ReturnChoiceBoundaryTests(unittest.TestCase):
    def test_call_result_and_error_literal_are_not_claimed_different(self):
        choice = report(WORDS[:5] + (NOP,) + WORDS[6:])['calls'][0]['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['kind'], 'call_result')
        self.assertIsNone(choice['same_constant_bits'])

    def test_copied_result_can_form_choice(self):
        words = (0xaa0003f3, 0xaa1f03e0) + WORDS[:5] + (0xaa1303e0,) + WORDS[6:]
        choice = report(words)['calls'][0]['return_choice']
        self.assertEqual(choice['success']['candidate_status'], 'copied_register_candidate')

    def test_identical_literal_bits_are_a_scoped_static_fact(self):
        choice = report(WORDS[:5] + (0x92800000,) + WORDS[6:])['calls'][0]['return_choice']
        self.assertTrue(choice['same_constant_bits'])
        self.assertFalse(choice['runtime_value_proven'])

    def test_missing_and_conflicting_outcomes_withhold_choice(self):
        import copy
        from airs.swift_error_flow import _return_choice
        base = report(WORDS)['calls'][0]
        for field in ('error_constant', 'success_constant'):
            call = copy.deepcopy(base); del call[field]
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
        call = copy.deepcopy(base)
        call['success_result']['status'] = 'preserved_register_candidate'
        self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_missing_or_conflicting')

    def test_wrong_call_entry_or_return_binding_withholds_choice(self):
        import copy
        from airs.swift_error_flow import _return_choice
        base = report(WORDS)['calls'][0]
        for field, key in (('success_constant', 'call_pc'), ('error_constant', 'error_pc'),
                           ('success_constant', 'success_pc'), ('error_constant', 'return_pc')):
            call = copy.deepcopy(base); call[field][key] = '0x0'
            self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')

    def test_wrong_literal_width_bits_and_proof_claims_withhold(self):
        import copy
        from airs.swift_error_flow import _return_choice
        base = report(WORDS)['calls'][0]
        for key, value in (('bit_width', 32), ('bit_width', True), ('constant_bits', '0x0'),
                           ('depends_on_call_result', True), ('runtime_value_proven', True)):
            call = copy.deepcopy(base); call['error_constant'][key] = value
            self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')

    def test_forward_layout_preserves_condition_and_all_proof_limits(self):
        from test_swift_forward_error_arm import WORDS as forward
        call = report(forward)['calls'][0]; choice = call['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['condition']['test_pc'], call['test_pc'])
        self.assertEqual(choice['condition']['error_when'], 'nonzero')
        for key in ('runtime_value_proven', 'exclusive_path_proven', 'caller_return_type_proven',
                    'call_return_proven', 'handler_semantics_proven', 'source_reconstruction_allowed'):
            self.assertFalse(choice[key])

    def test_ineligible_presentation_and_missing_error_literal_are_unresolved(self):
        from test_swift_error_constants import error_arm
        value = error_arm((0x92800000, 0x94000100))
        self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')
        value = report(WORDS + (0x17fffffb,))
        self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

class ReturnChoiceEvidenceTests(unittest.TestCase):
    def test_default_absence_and_text_model_binding(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        from airs.swift_error_text import render_swift_error_text
        from airs.types import InputError
        self.assertNotIn('return_choice_model_version', recover_swift_error_flow(image()))
        value = report(WORDS)
        text = render_swift_error_text(value)
        self.assertIn('Return-choice model: "swift-return-choice-v11"', text)
        self.assertIn('structural_choice_candidate', text)
        value['return_choice_model_version'] = 'foreign'
        with self.assertRaises(InputError):
            render_swift_error_text(value)

    def test_cli_exposes_bound_pair_without_source_reconstruction(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'return-choice.macho'
            source.write_bytes(image(WORDS, symbol='_$s4Demo4readSiyKF').data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(options + ['--format', format]), 0)
                if format == 'json':
                    choice = json.loads(output.getvalue())['calls'][0]['return_choice']
                    self.assertEqual(choice['status'], 'structural_choice_candidate')
                    self.assertEqual(choice['success']['kind'], 'constant_bits')
                    self.assertEqual(choice['error']['kind'], 'constant_bits')
                else:
                    self.assertIn('Return choice (structural outcomes; source disabled)', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())

class ReturnChoicePresentationBindingTests(unittest.TestCase):
    def test_condition_plan_entries_and_source_scope_must_match(self):
        import copy
        from airs.swift_error_flow import _return_choice
        base = report(WORDS)['calls'][0]
        self.assertEqual(_return_choice(base)['status'], 'structural_choice_candidate')
        cases = []
        for key, value in (('test_pc', '0x0'), ('tested_register', 'x0')):
            call = copy.deepcopy(base); call[key] = value; cases.append(call)
        call = copy.deepcopy(base); call['presentation']['source_reconstruction_allowed'] = True; cases.append(call)
        call = copy.deepcopy(base); del call['presentation']['display_plan']; cases.append(call)
        call = copy.deepcopy(base); call['presentation']['display_plan']['success_entry_pc'] = '0x0'; cases.append(call)
        call = copy.deepcopy(base); call['presentation']['display_plan']['error_interval']['start_pc'] = '0x0'; cases.append(call)
        call = copy.deepcopy(base); call['presentation']['display_plan']['condition']['error_when'] = 'zero'; cases.append(call)
        for call in cases:
            self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')
