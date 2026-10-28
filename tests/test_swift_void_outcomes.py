"""Caller-assigned literals after admitted throwing Void declarations."""
import unittest
from test_swift_success_result import report
from test_swift_shared_epilogue import WORDS

NOARG = '_$s4Demo8validateyyKF'
INTARG = '_$s4Demo8validateyySiKF'

class VoidOutcomeFirstTests(unittest.TestCase):
    def test_void_validation_call_has_two_caller_assigned_literals(self):
        call = report(WORDS, symbol=NOARG)['calls'][0]
        self.assertEqual(call['success_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['error_constant']['constant_bits'], '0xffffffffffffffff')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['success_result']['reason'], 'callee_result_not_scalar_int')

class VoidOutcomeBoundaryTests(unittest.TestCase):
    def test_int_parameter_void_callee_has_same_literal_scope(self):
        call = report(WORDS, symbol=INTARG)['calls'][0]
        self.assertEqual(call['callee']['parameters'], ['Swift.Int'])
        self.assertEqual(call['callee']['result'], 'Swift.Void')
        self.assertEqual(call['return_choice']['success']['constant_bits'], '0x0000000000000000')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xffffffffffffffff')

    def test_forward_layout_and_proof_flags(self):
        from test_swift_forward_error_arm import WORDS as forward
        call = report(forward, symbol=NOARG)['calls'][0]
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        for outcome in (call['success_constant'], call['error_constant'], call['return_choice']):
            for key in ('runtime_value_proven', 'source_reconstruction_allowed', 'caller_return_type_proven', 'exclusive_path_proven'):
                self.assertFalse(outcome[key])

    def test_void_x0_is_not_a_call_result_or_implicit_literal(self):
        from test_swift_success_result import NOP
        call = report(WORDS[:5] + (NOP,) + WORDS[6:], symbol=NOARG)['calls'][0]
        self.assertEqual(call['success_result']['status'], 'declined')
        self.assertEqual(call['success_constant']['reason'], 'success_x0_constant_not_known')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_nonshared_void_return_does_not_borrow_integer_result_validation(self):
        from test_swift_success_return_tail import WORDS as direct
        call = report(direct, symbol=NOARG)['calls'][0]
        self.assertEqual(call['error_constant']['reason'], 'validated_success_return_tail_missing')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_unsupported_signatures_and_ambiguous_aliases_remain_refused(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        for symbol in ('_$s4Demo8validateyyF', '_$s4Demo8validateyyYaKF', '_$s4Demo8validateSSyKF'):
            call = report(WORDS, symbol=symbol)['calls'][0]
            self.assertEqual(call['return_choice']['status'], 'unresolved')
        value = recover_swift_error_flow(image(WORDS, symbol=NOARG, aliases=(('_$s4Demo5otheryyKF', 64),)),
            include_error_regions=True, validate_region_entries=True, include_structured_presentation=True)
        self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_conflicts_and_incomplete_scan_still_withhold(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for value in (report(WORDS + (0x17fffffb,), symbol=NOARG),
                      report(WORDS, symbol=NOARG, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=10))):
            self.assertEqual(value['calls'][0]['return_choice']['status'], 'unresolved')

    def test_unknown_callee_result_metadata_is_not_admitted(self):
        import copy, struct
        from types import SimpleNamespace
        from airs.swift_error_flow import _path_constant
        from test_swift_error_flow import BASE
        call = copy.deepcopy(report(WORDS, symbol=NOARG)['calls'][0])
        call['callee']['result'] = 'Swift.String'
        result = _path_constant(struct.pack('<11I', 0x94000010, *WORDS), SimpleNamespace(start=BASE, end=BASE+44), call)
        self.assertEqual(result['reason'], 'callee_result_outside_admitted_subset')

class VoidOutcomeEvidenceTests(unittest.TestCase):
    def test_stale_integer_result_cannot_be_attached_to_void_callee(self):
        import copy
        from airs.swift_error_flow import _return_choice
        call = copy.deepcopy(report(WORDS, symbol=NOARG)['calls'][0])
        call['success_result'] = copy.deepcopy(call['success_constant'])
        call['success_result']['status'] = 'preserved_register_candidate'
        call['success_constant']['status'] = 'declined'
        self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')

    def test_default_absence_and_current_model_identities(self):
        from airs.swift_error_flow import recover_swift_error_flow
        from test_swift_error_flow import image
        value = recover_swift_error_flow(image(WORDS, symbol=NOARG))
        self.assertNotIn('return_choice_model_version', value)
        value = report(WORDS, symbol=NOARG)
        self.assertEqual(value['success_constant_model_version'], 'swift-success-constant-v16')
        self.assertEqual(value['error_constant_model_version'], 'swift-error-constant-v18')
        self.assertEqual(value['return_choice_model_version'], 'swift-return-choice-v28')

    def test_cli_reports_caller_literals_without_void_call_result(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'void-outcomes.macho'
            source.write_bytes(image(WORDS, symbol=NOARG).data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(options + ['--format', format]), 0)
                if format == 'json':
                    call = json.loads(output.getvalue())['calls'][0]
                    self.assertEqual(call['callee']['result'], 'Swift.Void')
                    self.assertEqual(call['return_choice']['success']['kind'], 'constant_bits')
                    self.assertEqual(call['success_result']['status'], 'declined')
                else:
                    self.assertIn('Swift.Void', output.getvalue())
                    self.assertIn('structural_choice_candidate', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())
