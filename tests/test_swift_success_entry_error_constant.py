"""Error literal paired with an already validated success-entry return tail."""
import unittest
from test_swift_success_result import report
from test_swift_success_return_tail import WORDS

class SuccessEntryErrorConstantFirstTests(unittest.TestCase):
    def test_direct_success_tail_can_pair_with_error_literal(self):
        call = report(WORDS)['calls'][0]
        self.assertEqual(call['error_constant']['status'], 'constant_register_candidate')
        self.assertEqual(call['error_constant']['constant_bits'], '0xffffffffffffffff')
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertEqual(call['return_choice']['success']['kind'], 'call_result')
        self.assertIsNone(call['return_choice']['same_constant_bits'])

class SuccessEntryErrorConstantBoundaryTests(unittest.TestCase):
    def test_error_literal_after_opaque_call_joins_validated_tail(self):
        words = (0xb4000095, 0xaa1503e0, 0x94000100, 0x92800000,
                 0xa9427bfd, 0xa94157f6, 0x9100c3ff, 0xd65f03c0)
        call = report(words)['calls'][0]
        self.assertEqual(call['return_choice']['status'], 'structural_choice_candidate')
        self.assertEqual(call['error_constant']['opaque_call_count'], 1)
        self.assertFalse(call['error_constant']['call_return_proven'])

    def test_side_entry_withholds_error_literal_and_join(self):
        call = report(WORDS + (0x17ffffff,))['calls'][0]
        self.assertEqual(call['success_result']['reason'], 'unexpected_return_tail_entry')
        self.assertEqual(call['error_constant']['reason'], 'validated_success_return_tail_missing')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_missing_tail_words_and_wrong_return_binding_are_rejected(self):
        import copy, struct
        from types import SimpleNamespace
        from airs.swift_error_flow import _path_constant
        from test_swift_error_flow import BASE
        base = report(WORDS)['calls'][0]
        data = struct.pack('<5I', 0x94000008, *WORDS)
        function = SimpleNamespace(start=BASE, end=BASE + len(data))
        for change in ('instructions', 'return_pc', 'call_pc', 'success_pc', 'proof'):
            call = copy.deepcopy(base)
            if change == 'instructions':
                call['success_result']['instructions'] = []
            elif change == 'proof':
                call['success_result']['runtime_value_proven'] = True
            else:
                call['success_result'][change] = '0x0'
            self.assertEqual(_path_constant(data, function, call, error=True)['reason'],
                             'validated_success_return_tail_inconsistent')

    def test_constant_before_opaque_error_call_is_not_retained(self):
        words = (0xb4000095, 0x92800000, 0x94000100, 0xd503201f, 0xd65f03c0)
        call = report(words)['calls'][0]
        self.assertEqual(call['error_constant']['reason'], 'error_x0_constant_not_known')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_copy_result_path_and_error_literal_remain_separate(self):
        words = (0xaa0003f3, 0xaa1f03e0, 0xaa1303e0) + WORDS
        call = report(words)['calls'][0]
        self.assertEqual(call['return_choice']['success']['candidate_status'], 'copied_register_candidate')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0xffffffffffffffff')

    def test_unknown_error_register_and_partial_scan_withhold(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for value in (report((WORDS[0], 0xaa1303e0) + WORDS[2:]),
                      report(WORDS, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=5))):
            self.assertEqual(value['calls'][0]['error_constant']['status'], 'declined')

class SuccessEntryErrorConstantEvidenceTests(unittest.TestCase):
    def test_exact_error_and_tail_bounds_and_each_overflow(self):
        from test_swift_success_result import NOP
        def words(error_count, tail_count):
            test = 0xb4000015 | ((error_count + 1) << 5)
            return (test,) + (NOP,) * (error_count - 1) + (0x92800000,) + (NOP,) * (tail_count - 1) + (0xd65f03c0,)
        result = report(words(16, 8))['calls'][0]['error_constant']
        self.assertEqual(result['status'], 'constant_register_candidate')
        self.assertEqual(len(result['instructions']), 24)
        for sizes in ((17, 8), (16, 9)):
            self.assertEqual(report(words(*sizes))['calls'][0]['error_constant']['status'], 'declined')

    def test_cli_exposes_call_result_or_error_literal(self):
        import contextlib, io, json
        from pathlib import Path
        from fixture_storage import temporary_directory
        from test_swift_error_flow import image
        from airs.cli import main
        with temporary_directory(Path(__file__).resolve().parents[1]) as folder:
            source = Path(folder) / 'success-tail-error-literal.macho'
            source.write_bytes(image(WORDS, symbol='_$s4Demo4readSiyKF').data)
            options = ['swift-error-flow', str(source), '--include-error-regions',
                       '--validate-region-entries', '--include-structured-presentation']
            for format in ('json', 'text'):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    self.assertEqual(main(options + ['--format', format]), 0)
                if format == 'json':
                    value = json.loads(output.getvalue())
                    choice = value['calls'][0]['return_choice']
                    self.assertEqual(choice['success']['kind'], 'call_result')
                    self.assertEqual(choice['error']['constant_bits'], '0xffffffffffffffff')
                    self.assertEqual(value['return_choice_model_version'], 'swift-return-choice-v7')
                else:
                    self.assertIn('structural_choice_candidate', output.getvalue())
                    self.assertIn('swift-error-constant-v7', output.getvalue())
                    self.assertIn('Source reconstruction: disabled', output.getvalue())

class SuccessEntryErrorConstantBindingTests(unittest.TestCase):
    def test_mixed_or_foreign_layout_summary_source_is_rejected(self):
        import copy
        from airs.swift_error_flow import _return_choice
        base = report(WORDS)['calls'][0]
        self.assertEqual(_return_choice(base)['status'], 'structural_choice_candidate')
        call = copy.deepcopy(base); call['success_result']['return_tail_layout'] = 'foreign'
        self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')
        call = copy.deepcopy(base)
        call['success_constant'] = copy.deepcopy(call['error_constant'])
        call['success_constant']['success_pc'] = call['success_pc']
        call['success_result']['status'] = 'declined'
        self.assertEqual(_return_choice(call)['reason'], 'outcome_evidence_inconsistent')

    def test_wrong_result_register_cannot_supply_error_tail_binding(self):
        import copy, struct
        from types import SimpleNamespace
        from airs.swift_error_flow import _path_constant
        from test_swift_error_flow import BASE
        call = copy.deepcopy(report(WORDS)['calls'][0])
        call['success_result']['register'] = 'x1'
        data = struct.pack('<5I', 0x94000008, *WORDS)
        result = _path_constant(data, SimpleNamespace(start=BASE, end=BASE + len(data)), call, error=True)
        self.assertEqual(result['reason'], 'validated_success_return_tail_inconsistent')
