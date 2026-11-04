"""CMP/B.NE selected-path choice with an Int result and error literal."""
import unittest
from test_swift_cmp_ne_handler import report
from test_swift_cmp_ne_success_result import PRESERVED
from test_swift_error_flow import BASE


class NeReturnChoiceFirstTests(unittest.TestCase):
    def test_bound_result_and_error_literal_form_structural_choice(self):
        call = report(PRESERVED)['calls'][0]
        choice = call['return_choice']
        self.assertEqual(choice['status'], 'structural_choice_candidate')
        self.assertEqual(choice['success']['kind'], 'call_result')
        self.assertEqual(choice['error']['constant_bits'], '0xffffffffffffffff')
        self.assertEqual(choice['condition']['test_condition'], 'ne')
        self.assertEqual(choice['condition']['comparison_pc'], hex(BASE+4))
        for key in ('runtime_value_proven', 'call_return_proven', 'exclusive_path_proven',
                    'caller_return_type_proven', 'handler_semantics_proven', 'source_reconstruction_allowed'):
            self.assertFalse(choice[key])
        self.assertEqual(call['success_constant']['status'], 'declined')


class NeReturnChoiceBoundaryTests(unittest.TestCase):
    def test_full_width_restored_copy_and_word_error_literal(self):
        words = (0xaa0003f3, 0xaa1f03e0, *PRESERVED[:2], 0xaa1303e0, *PRESERVED[3:5], 0x12800000, PRESERVED[6])
        call = report(words)['calls'][0]
        self.assertEqual(call['return_choice']['success']['candidate_status'], 'copied_register_candidate')
        self.assertEqual(call['return_choice']['error']['constant_bits'], '0x00000000ffffffff')

    def test_clobbered_or_narrow_result_cannot_become_choice(self):
        from test_swift_cmp_ne_handler import WORDS
        self.assertEqual(report(WORDS)['calls'][0]['return_choice']['success']['kind'], 'constant_bits')
        self.assertEqual(report((0x2a0003e0, *PRESERVED))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_error_literal_before_opaque_call_is_not_choice(self):
        words = (*PRESERVED[:4], 0x92800000, 0x94000010, PRESERVED[6])
        call = report(words)['calls'][0]
        self.assertEqual(call['success_result']['status'], 'preserved_register_candidate')
        self.assertEqual(call['error_constant']['status'], 'declined')
        self.assertEqual(call['return_choice']['status'], 'unresolved')

    def test_unexpected_entries_unknown_and_partial_caller_withhold(self):
        from dataclasses import replace
        from airs.swift_error_flow import DEFAULT_LIMITS
        for target in (4, 8, 12, 16, 20, 24, 28):
            branch = 0x14000000 | (((target-32)//4) & 0x3ffffff)
            self.assertEqual(report((*PRESERVED, branch))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report((*PRESERVED, 0xffffffff))['calls'][0]['return_choice']['status'], 'unresolved')
        self.assertEqual(report(PRESERVED, limits=replace(DEFAULT_LIMITS, max_instructions_per_function=7))['calls'][0]['return_choice']['status'], 'unresolved')

    def test_outcomes_require_same_call_path_return_and_false_proofs(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report(PRESERVED)['calls'][0]
        for section, key, value in (('success_result', 'return_pc', '0x0'), ('error_constant', 'return_pc', '0x0'),
            ('success_result', 'call_pc', '0x0'), ('error_constant', 'error_pc', '0x0'),
            ('success_result', 'success_pc', '0x0'), ('success_result', 'return_tail_layout', 'success_entry'),
            ('success_result', 'runtime_value_proven', True), ('error_constant', 'handler_semantics_proven', True),
            ('error_constant', 'constant_bits', '0x1'), ('error_constant', 'bit_width', 32)):
            call = deepcopy(original); call[section][key] = value
            self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_condition_and_forward_layout_must_remain_bound(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report(PRESERVED)['calls'][0]
        for key, value in (('comparison_pc', hex(BASE)), ('test_condition', 'eq'), ('register', 'x20')):
            call = deepcopy(original); call['presentation']['display_plan']['condition'][key] = value
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
        call = deepcopy(original); call['error_region']['layout'] = 'other'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_success_literal_and_conflicting_sources_remain_refused(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        call = deepcopy(report(PRESERVED)['calls'][0])
        call['success_constant'] = {'status': 'constant_register_candidate'}
        self.assertEqual(_return_choice(call)['status'], 'unresolved')
        call['success_result']['status'] = 'declined'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')

    def test_text_and_cli_keep_choice_structural(self):
        import contextlib, io, json, tempfile
        from pathlib import Path
        from airs.cli import main
        from airs.swift_error_text import render_swift_error_text
        from test_swift_error_flow import image
        text = render_swift_error_text(report(PRESERVED))
        for expected in ('structural_choice_candidate', '0xffffffffffffffff', 'Source reconstruction: disabled'):
            self.assertIn(expected, text)
        root = Path('local-evidence/swift-cmp-ne-return-choice'); root.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as folder:
            source = Path(folder) / 'owned.macho'; source.write_bytes(image(PRESERVED).data)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                status = main(['swift-error-flow', str(source), '--include-error-regions',
                    '--validate-region-entries', '--include-structured-presentation'])
            self.assertEqual(status, 0)
            call = json.loads(output.getvalue())['calls'][0]
            self.assertEqual(call['return_choice']['condition']['test_condition'], 'ne')
            self.assertFalse(call['return_choice']['runtime_value_proven'])

    def test_all_condition_fields_and_proof_flags_are_bound(self):
        from copy import deepcopy
        from airs.swift_error_flow import _return_choice
        original = report(PRESERVED)['calls'][0]
        for key in ('test_pc', 'comparison_pc', 'test_kind', 'test_condition', 'register', 'error_when'):
            call = deepcopy(original); call['presentation']['display_plan']['condition'][key] = 'other'
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
        for section in ('success_result', 'error_constant'):
            for key in ('source_reconstruction_allowed', 'runtime_value_proven', 'exclusive_path_proven', 'caller_return_type_proven'):
                call = deepcopy(original); call[section][key] = True
                self.assertEqual(_return_choice(call)['status'], 'unresolved')
        for key in ('call_return_proven', 'handler_semantics_proven'):
            call = deepcopy(original); call['error_constant'][key] = True
            self.assertEqual(_return_choice(call)['status'], 'unresolved')
        call = deepcopy(original); del call['error_region']['shared_epilogue']
        self.assertEqual(_return_choice(call)['status'], 'unresolved')
        call = deepcopy(original); call['error_constant']['status'] = 'declined'
        self.assertEqual(_return_choice(call)['status'], 'unresolved')
